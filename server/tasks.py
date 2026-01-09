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
    
    print(f"\n[TASK] Starting conversion for job_id={job_id}")

    try:
        # Get job
        job = db.query(JobModel).filter(JobModel.id == job_id).first()
        if not job:
            print(f"[TASK] Job {job_id} not found in database!")
            return
        
        print(f"[TASK] Found job: {job.id}, pdf_path={job.pdf_path}")

        # Update status to processing
        job.status = JobStatus.PROCESSING
        job.current_phase = "Initializing"
        job.progress = 0.0
        db.commit()
        print(f"[TASK] Updated job status to PROCESSING")

        # Note: WebSocket updates happen asynchronously via polling from frontend
        # The frontend polls the job status endpoint, so we just need to update the DB

        # Create output directory
        output_dir = Path("server/output") / job_id
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"[TASK] Created output dir: {output_dir}")

        # Initialize pipeline
        print(f"[TASK] Initializing pipeline...")
        job.current_phase = "Setting up pipeline"
        job.progress = 5.0
        db.commit()

        pipeline = SlideRefactorPipeline(
            extractor=settings.extractor,
            use_preprocessing=settings.use_preprocessing,
            generate_audit=settings.generate_audit,
            save_intermediate=settings.save_intermediate,
            render_background=settings.render_background,
            skip_llm=settings.skip_llm,
        )

        # Phase 1: Extraction
        print(f"[TASK] Starting extraction...")
        job.current_phase = "Extracting content from PDF"
        job.progress = 20.0
        db.commit()

        # Define progress callback
        def update_progress(progress: float, phase: str):
            try:
                # Update DB
                job.progress = min(progress, 99.0)
                job.current_phase = phase
                db.commit()
                
                # Broadcast WS
                import asyncio
                asyncio.run(manager.broadcast(job_id, json.dumps({
                    "status": "processing",
                    "phase": phase,
                    "progress": progress
                })))
            except Exception as e:
                print(f"[TASK] Progress update failed: {e}")

        # Run the actual conversion (this handles all stages)
        pdf_path = Path(job.pdf_path)
        result = pipeline.process(
            pdf_path=pdf_path,
            output_dir=output_dir,
            progress_callback=update_progress
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
        
        print(f"[TASK] ✓ Conversion completed successfully! PPTX: {job.pptx_path}")

        # Send completion message via WebSocket
        try:
            import asyncio
            asyncio.run(manager.broadcast(job_id, json.dumps({
                "status": "completed",
                "phase": "Completed",
                "progress": 100.0,
                "results": job.results
            })))
        except Exception as e:
            print(f"[TASK] WebSocket broadcast failed (non-critical): {e}")

    except Exception as e:
        # Handle errors
        error_msg = str(e)
        traceback_str = traceback.format_exc()
        
        print(f"[TASK] ✗ Conversion FAILED: {error_msg}")
        print(f"[TASK] Traceback:\n{traceback_str}")

        try:
            job.status = JobStatus.FAILED
            job.current_phase = "Failed"
            job.error_message = error_msg
            db.commit()
        except:
            pass

        # Try to send failure message via WebSocket
        try:
            import asyncio
            asyncio.run(manager.broadcast(job_id, json.dumps({
                "status": "failed",
                "phase": "Failed",
                "error": error_msg
            })))
        except Exception as ws_error:
            print(f"[TASK] WebSocket broadcast failed (non-critical): {ws_error}")

    finally:
        db.close()
