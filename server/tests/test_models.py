
import pytest
from server.models import Job, JobStatus, ConversionSettings

def test_job_status_model():
    status = JobStatus(status="processing", message="working...", progress=0.5)
    assert status.status == "processing"
    assert status.message == "working..."
    assert status.progress == 0.5

def test_job_model():
    job = Job(id="123", filename="test.pdf", status="pending", created_at="now")
    assert job.id == "123"
    assert job.filename == "test.pdf"
    assert job.settings is None

def test_conversion_settings_model():
    settings = ConversionSettings()
    assert settings.extractor == "datalab"
    assert settings.dpi == 400
