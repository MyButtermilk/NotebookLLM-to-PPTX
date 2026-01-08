"""
Database models and setup.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class JobStatus(str, Enum):
    """Job status enum."""
    UPLOADED = "uploaded"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Job(Base):
    """Job model for tracking conversions."""
    __tablename__ = "jobs"

    id = Column(String, primary_key=True)
    filename = Column(String, nullable=False)
    status = Column(SQLEnum(JobStatus), default=JobStatus.UPLOADED, nullable=False)
    total_pages = Column(Integer, default=0)
    progress = Column(Float, default=0.0)
    current_phase = Column(String, nullable=True)
    error_message = Column(String, nullable=True)

    # File paths
    pdf_path = Column(String, nullable=True)
    pptx_path = Column(String, nullable=True)
    audit_path = Column(String, nullable=True)
    slidegraph_path = Column(String, nullable=True)

    # Settings and results
    settings = Column(JSON, nullable=True)
    results = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# Database connection
DATABASE_URL = "sqlite:///server/sliderefactor.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
