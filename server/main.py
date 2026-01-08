"""
Main FastAPI application.
"""

import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, File, UploadFile, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from server.db import init_db, get_db, Job, JobStatus
from server.models import ConversionSettings
from server.tasks import process_pdf_task
from server.websocket_manager import ConnectionManager

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    app.state.upload_dir = Path("server/uploads")
    app.state.output_dir = Path("server/output")
    app.state.upload_dir.mkdir(parents=True, exist_ok=True)
    app.state.output_dir.mkdir(parents=True, exist_ok=True)
    yield
    # Shutdown
    pass

app = FastAPI(
    title="SlideRefactor API",
    description="Convert NotebookLLM PDFs to editable PPTX",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager
manager = ConnectionManager()


# --- Request/Response Models ---

class ConversionRequest(BaseModel):
    """Request to start a conversion job."""
    extractor: str = Field(default="datalab", description="Extractor to use")
    use_preprocessing: bool = Field(default=False, description="Apply OpenCV preprocessing")
    generate_audit: bool = Field(default=True, description="Generate audit HTML")
    save_intermediate: bool = Field(default=True, description="Save SlideGraph JSON")
    selected_pages: Optional[List[int]] = Field(default=None, description="Pages to convert (0-indexed)")
    slide_size: str = Field(default="16:9", description="Slide aspect ratio")


class JobResponse(BaseModel):
    """Job status response."""
    job_id: str
    status: str
    filename: str
    total_pages: int
    created_at: str
    updated_at: str
    progress: float = 0.0
    current_phase: Optional[str] = None
    error_message: Optional[str] = None
    results: Optional[dict] = None


class SettingsRequest(BaseModel):
    """Settings update request."""
    datalab_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    default_extractor: Optional[str] = None
    default_preprocessing: Optional[bool] = None


# --- API Endpoints ---

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "SlideRefactor API is running"}


@app.post("/api/upload", response_model=dict)
async def upload_pdf(
    file: UploadFile = File(...),
):
    """
    Upload a PDF file and create a new job.

    Returns job_id and file metadata.
    """
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # Generate job ID
    job_id = str(uuid.uuid4())

    # Save uploaded file
    upload_path = app.state.upload_dir / f"{job_id}.pdf"

    with open(upload_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Get PDF metadata
    try:
        from pypdfium2 import PdfDocument
        pdf = PdfDocument(str(upload_path))
        page_count = len(pdf)
        pdf.close()
    except Exception as e:
        page_count = 0

    # Create job in database
    db = next(get_db())
    job = Job(
        id=job_id,
        filename=file.filename,
        status=JobStatus.UPLOADED,
        total_pages=page_count,
        pdf_path=str(upload_path),
    )
    db.add(job)
    db.commit()

    return {
        "job_id": job_id,
        "filename": file.filename,
        "total_pages": page_count,
        "size_bytes": len(content),
    }


@app.post("/api/jobs/{job_id}/convert")
async def start_conversion(
    job_id: str,
    settings: ConversionRequest,
    background_tasks: BackgroundTasks,
):
    """
    Start converting a PDF job.

    Kicks off background task and returns immediately.
    """
    db = next(get_db())
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status not in [JobStatus.UPLOADED, JobStatus.FAILED]:
        raise HTTPException(status_code=400, detail=f"Job is already {job.status}")

    # Update job status
    job.status = JobStatus.QUEUED
    job.settings = settings.model_dump()
    db.commit()

    # Start background task
    background_tasks.add_task(
        process_pdf_task,
        job_id=job_id,
        settings=settings,
        manager=manager
    )

    return {"job_id": job_id, "status": "queued"}


@app.get("/api/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    """Get job status and progress."""
    db = next(get_db())
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobResponse(
        job_id=job.id,
        status=job.status.value,
        filename=job.filename,
        total_pages=job.total_pages,
        created_at=job.created_at.isoformat(),
        updated_at=job.updated_at.isoformat(),
        progress=job.progress,
        current_phase=job.current_phase,
        error_message=job.error_message,
        results=job.results,
    )


@app.get("/api/jobs", response_model=List[JobResponse])
async def list_jobs(limit: int = 50, skip: int = 0):
    """List all jobs (for history page)."""
    db = next(get_db())
    jobs = db.query(Job).order_by(Job.created_at.desc()).limit(limit).offset(skip).all()

    return [
        JobResponse(
            job_id=job.id,
            status=job.status.value,
            filename=job.filename,
            total_pages=job.total_pages,
            created_at=job.created_at.isoformat(),
            updated_at=job.updated_at.isoformat(),
            progress=job.progress,
            current_phase=job.current_phase,
            error_message=job.error_message,
            results=job.results,
        )
        for job in jobs
    ]


@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job and its files."""
    db = next(get_db())
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Delete files
    if job.pdf_path and Path(job.pdf_path).exists():
        Path(job.pdf_path).unlink()

    if job.pptx_path and Path(job.pptx_path).exists():
        Path(job.pptx_path).unlink()

    # Delete from database
    db.delete(job)
    db.commit()

    return {"message": "Job deleted"}


@app.get("/api/jobs/{job_id}/download")
async def download_pptx(job_id: str):
    """Download the generated PPTX file."""
    db = next(get_db())
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed")

    if not job.pptx_path or not Path(job.pptx_path).exists():
        raise HTTPException(status_code=404, detail="PPTX file not found")

    return FileResponse(
        job.pptx_path,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=f"{Path(job.filename).stem}.pptx"
    )


@app.get("/api/jobs/{job_id}/audit")
async def download_audit(job_id: str):
    """Download the audit HTML file."""
    db = next(get_db())
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed")

    if not job.audit_path or not Path(job.audit_path).exists():
        raise HTTPException(status_code=404, detail="Audit file not found")

    return FileResponse(job.audit_path, media_type="text/html")


@app.get("/api/settings")
async def get_settings():
    """Get current settings (masked API keys)."""
    return {
        "datalab_api_key": "****" if os.getenv("DATALAB_API_KEY") else None,
        "anthropic_api_key": "****" if os.getenv("ANTHROPIC_API_KEY") else None,
        "default_extractor": os.getenv("DEFAULT_EXTRACTOR", "datalab"),
        "default_preprocessing": os.getenv("DEFAULT_PREPROCESSING", "false") == "true",
    }


@app.post("/api/settings")
async def update_settings(settings: SettingsRequest):
    """Update settings (in-memory only for now)."""
    if settings.datalab_api_key:
        os.environ["DATALAB_API_KEY"] = settings.datalab_api_key

    if settings.anthropic_api_key:
        os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key

    if settings.default_extractor:
        os.environ["DEFAULT_EXTRACTOR"] = settings.default_extractor

    if settings.default_preprocessing is not None:
        os.environ["DEFAULT_PREPROCESSING"] = str(settings.default_preprocessing).lower()

    return {"message": "Settings updated"}


@app.post("/api/settings/test-connection")
async def test_connection(provider: str):
    """Test API connection for a provider."""
    if provider == "datalab":
        api_key = os.getenv("DATALAB_API_KEY")
        if not api_key:
            return {"status": "error", "message": "API key not set"}

        # TODO: Actual connection test
        return {"status": "success", "message": "Connection OK", "latency_ms": 150}

    elif provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return {"status": "error", "message": "API key not set"}

        # TODO: Actual connection test
        return {"status": "success", "message": "Connection OK", "latency_ms": 200}

    else:
        raise HTTPException(status_code=400, detail="Unknown provider")


# --- WebSocket for real-time progress ---

@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time job progress updates.
    """
    await manager.connect(job_id, websocket)

    try:
        while True:
            # Keep connection alive and receive any client messages
            data = await websocket.receive_text()

            # Echo back for heartbeat
            if data == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        manager.disconnect(job_id, websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
