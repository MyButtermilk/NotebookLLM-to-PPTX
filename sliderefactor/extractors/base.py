"""
Base extractor interface.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
from sliderefactor.models import SlideGraph


class BaseExtractor(ABC):
    """Abstract base class for all extraction engines."""

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.name = self.__class__.__name__.replace("Extractor", "").lower()

    @abstractmethod
    def extract(self, pdf_path: Path, output_dir: Path) -> SlideGraph:
        """
        Extract slide content from a PDF into SlideGraph format.

        Args:
            pdf_path: Path to the input PDF file
            output_dir: Directory to save extracted images and intermediate files

        Returns:
            SlideGraph object containing all extracted content
        """
        pass

    @abstractmethod
    def extract_page(
        self, pdf_path: Path, page_num: int, output_dir: Path
    ) -> "sliderefactor.models.Slide":
        """
        Extract a single page from the PDF.

        Args:
            pdf_path: Path to the input PDF file
            page_num: Page number (0-indexed)
            output_dir: Directory to save extracted images

        Returns:
            Slide object for the page
        """
        pass
