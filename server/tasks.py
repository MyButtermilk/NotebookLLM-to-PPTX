"""
Background task processing for PDF conversion.
"""

import json
import traceback
from pathlib import Path
from datetime import datetime

from server.db import SessionLocal, JobStatus
from server.db import Job as JobModel
from server.models import ConversionSettings
from server.websocket_manager import ConnectionManager

# Import sliderefactor
from sliderefactor import SlideRefactorPipeline


async def send_progress(manager: ConnectionManager, job_id: str, data: dict):
    """Send progress update via WebSocket."""
    await manager.broadcast(job_id, json.dumps(data))


def process_pdf_task(
    job_id: str,
    settings: ConversionSettings,
    manager: ConnectionManager,
):
    """
    Background task to process a PDF conversion.

    This runs in a background thread and updates the database
    and sends WebSocket updates as it progresses.
    """
    db = SessionLocal()

    try:
        # Get job
        job = db.query(JobModel).filter(JobModel.id == job_id).first()
        if not job:
            return

        # Update status to processing
        job.status = JobStatus.PROCESSING
        job.current_phase = "Initializing"
        job.progress = 0.0
        db.commit()

        # Send initial progress
        import asyncio
        asyncio.run(send_progress(manager, job_id, {
            "status": "processing",
            "phase": "Initializing",
            "progress": 0.0
        }))

        # Create output directory
        output_dir = Path("server/output") / job_id
        output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize pipeline
        job.current_phase = "Setting up pipeline"
        job.progress = 5.0
        db.commit()

        asyncio.run(send_progress(manager, job_id, {
            "status": "processing",
            "phase": "Setting up pipeline",
            "progress": 5.0
        }))

        pipeline = SlideRefactorPipeline(
            extractor=settings.extractor,
            use_preprocessing=settings.use_preprocessing,
            generate_audit=settings.generate_audit,
            save_intermediate=settings.save_intermediate,
        )

        # Phase 1: Extraction
        job.current_phase = "Extracting content"
        job.progress = 20.0
        db.commit()

        asyncio.run(send_progress(manager, job_id, {
            "status": "processing",
            "phase": "Extracting content from PDF",
            "progress": 20.0
        }))

        # Phase 2: LLM Processing
        job.current_phase = "Processing with AI"
        job.progress = 50.0
        db.commit()

        asyncio.run(send_progress(manager, job_id, {
            "status": "processing",
            "phase": "Processing layout with AI",
            "progress": 50.0
        }))

        # Phase 3: Rendering
        job.current_phase = "Generating PPTX"
        job.progress = 75.0
        db.commit()

        asyncio.run(send_progress(manager, job_id, {
            "status": "processing",
            "phase": "Rendering PowerPoint",
            "progress": 75.0
        }))

        # Run the actual conversion
        pdf_path = Path(job.pdf_path)
        result = pipeline.process(
            pdf_path=pdf_path,
            output_dir=output_dir,
        )

        # Update job with results
        job.status = JobStatus.COMPLETED
        job.current_phase = "Completed"
        job.progress = 100.0
        job.pptx_path = str(result.get("pptx"))
        job.audit_path = str(result.get("audit")) if result.get("audit") else None
        job.slidegraph_path = str(result.get("slidegraph")) if result.get("slidegraph") else None
        job.results = {
            "slides_created": job.total_pages,
            "completed_at": datetime.utcnow().isoformat(),
        }
        db.commit()

        # Send completion
        asyncio.run(send_progress(manager, job_id, {
            "status": "completed",
            "phase": "Completed",
            "progress": 100.0,
            "results": job.results
        }))

    except Exception as e:
        # Handle errors
        error_msg = str(e)
        traceback_str = traceback.format_exc()

        job.status = JobStatus.FAILED
        job.current_phase = "Failed"
        job.error_message = error_msg
        db.commit()

        import asyncio
        asyncio.run(send_progress(manager, job_id, {
            "status": "failed",
            "phase": "Failed",
            "error": error_msg,
            "traceback": traceback_str
        }))

    finally:
        db.close()
