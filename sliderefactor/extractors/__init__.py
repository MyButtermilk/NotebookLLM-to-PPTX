"""
Extraction engines for converting PDFs to SlideGraph format.

Supports multiple backends:
- Datalab (primary, SOTA)
- PaddleOCR (fallback)
- LayoutParser (layout detection)
"""

from sliderefactor.extractors.base import BaseExtractor
from sliderefactor.extractors.datalab import DatalabExtractor

__all__ = ["BaseExtractor", "DatalabExtractor"]
