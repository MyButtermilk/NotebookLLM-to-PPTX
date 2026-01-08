"""
Pydantic models for API requests/responses.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class JobStatus(BaseModel):
    """Status of a job."""
    status: str
    message: Optional[str] = None
    progress: float = 0.0

class Job(BaseModel):
    """A conversion job."""
    id: str
    filename: str
    status: str
    created_at: str
    settings: Optional['ConversionSettings'] = None

class ConversionSettings(BaseModel):
    """Settings for a conversion job."""
    extractor: str = Field(default="datalab", description="Extractor: datalab or paddleocr")
    use_preprocessing: bool = Field(default=False, description="Apply OpenCV preprocessing")
    generate_audit: bool = Field(default=True, description="Generate audit HTML")
    save_intermediate: bool = Field(default=True, description="Save SlideGraph JSON")
    selected_pages: Optional[List[int]] = Field(default=None, description="Pages to convert")
    slide_size: str = Field(default="16:9", description="Slide aspect ratio")
    dpi: int = Field(default=400, description="DPI for image extraction")

    model_config = {
        "json_schema_extra": {
            "example": {
                "extractor": "datalab",
                "use_preprocessing": False,
                "generate_audit": True,
                "save_intermediate": True,
                "selected_pages": None,
                "slide_size": "16:9",
                "dpi": 400
            }
        }
    }
