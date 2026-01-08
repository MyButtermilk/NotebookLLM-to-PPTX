"""
Preprocessing utilities for improving OCR quality.

Uses OpenCV for:
- Deskewing
- Contrast normalization
- Denoising
- Sharpening
- Margin detection
"""

from sliderefactor.preprocessors.opencv_utils import OpenCVPreprocessor

__all__ = ["OpenCVPreprocessor"]
