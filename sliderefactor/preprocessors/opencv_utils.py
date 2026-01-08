"""
OpenCV-based image preprocessing for better OCR quality.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Tuple, Optional
from PIL import Image


class OpenCVPreprocessor:
    """
    Image preprocessing using OpenCV to improve OCR accuracy.

    Provides:
    - Deskewing: Correct rotated/skewed scans
    - Contrast normalization: Improve text visibility
    - Denoising: Remove compression artifacts
    - Sharpening: Enhance text edges
    - Margin detection: Crop to content area
    """

    def __init__(
        self,
        deskew: bool = True,
        denoise: bool = True,
        sharpen: bool = True,
        normalize_contrast: bool = True,
        detect_margins: bool = True,
    ):
        self.deskew = deskew
        self.denoise = denoise
        self.sharpen = sharpen
        self.normalize_contrast = normalize_contrast
        self.detect_margins = detect_margins

    def preprocess(
        self, image: np.ndarray, save_path: Optional[Path] = None
    ) -> np.ndarray:
        """
        Apply all enabled preprocessing steps.

        Args:
            image: Input image as numpy array (BGR or RGB)
            save_path: Optional path to save preprocessed image

        Returns:
            Preprocessed image as numpy array
        """
        result = image.copy()

        if self.normalize_contrast:
            result = self._normalize_contrast(result)

        if self.denoise:
            result = self._denoise(result)

        if self.deskew:
            result = self._deskew(result)

        if self.detect_margins:
            result = self._crop_margins(result)

        if self.sharpen:
            result = self._sharpen(result)

        if save_path:
            cv2.imwrite(str(save_path), result)

        return result

    def preprocess_file(self, input_path: Path, output_path: Path) -> Path:
        """
        Preprocess an image file.

        Args:
            input_path: Path to input image
            output_path: Path to save preprocessed image

        Returns:
            Path to output file
        """
        image = cv2.imread(str(input_path))
        if image is None:
            raise ValueError(f"Could not read image: {input_path}")

        preprocessed = self.preprocess(image)
        cv2.imwrite(str(output_path), preprocessed)

        return output_path

    def _normalize_contrast(self, image: np.ndarray) -> np.ndarray:
        """
        Normalize contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization).
        """
        # Convert to LAB color space
        if len(image.shape) == 3:
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l_channel, a, b = cv2.split(lab)
        else:
            l_channel = image

        # Apply CLAHE to L channel
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_channel = clahe.apply(l_channel)

        # Merge back
        if len(image.shape) == 3:
            lab = cv2.merge([l_channel, a, b])
            result = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        else:
            result = l_channel

        return result

    def _denoise(self, image: np.ndarray) -> np.ndarray:
        """
        Remove noise using Non-local Means Denoising.
        """
        if len(image.shape) == 3:
            result = cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)
        else:
            result = cv2.fastNlMeansDenoising(image, None, 10, 7, 21)

        return result

    def _deskew(self, image: np.ndarray) -> np.ndarray:
        """
        Detect and correct skew angle.
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Threshold to binary
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Find contours
        coords = np.column_stack(np.where(binary > 0))

        if len(coords) < 10:
            # Not enough points to determine angle
            return image

        # Find minimum area rectangle
        angle = cv2.minAreaRect(coords)[-1]

        # Normalize angle
        if angle < -45:
            angle = 90 + angle
        elif angle > 45:
            angle = angle - 90

        # Only correct if angle is significant (> 0.5 degrees)
        if abs(angle) < 0.5:
            return image

        # Rotate image
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        result = cv2.warpAffine(
            image,
            M,
            (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )

        return result

    def _sharpen(self, image: np.ndarray) -> np.ndarray:
        """
        Sharpen image to enhance text edges.
        """
        kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
        result = cv2.filter2D(image, -1, kernel)
        return result

    def _crop_margins(self, image: np.ndarray, margin_threshold: int = 50) -> np.ndarray:
        """
        Detect and crop white margins around the content.

        Args:
            image: Input image
            margin_threshold: Pixel value threshold for detecting margins (0-255)

        Returns:
            Cropped image
        """
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Threshold to find content
        _, binary = cv2.threshold(gray, 245, 255, cv2.THRESH_BINARY_INV)

        # Find all non-zero points
        coords = cv2.findNonZero(binary)

        if coords is None:
            # No content detected, return original
            return image

        # Get bounding rectangle
        x, y, w, h = cv2.boundingRect(coords)

        # Add small padding (5% of dimensions)
        pad_x = int(w * 0.05)
        pad_y = int(h * 0.05)

        x = max(0, x - pad_x)
        y = max(0, y - pad_y)
        w = min(image.shape[1] - x, w + 2 * pad_x)
        h = min(image.shape[0] - y, h + 2 * pad_y)

        # Crop
        result = image[y : y + h, x : x + w]

        return result

    @staticmethod
    def pil_to_cv2(pil_image: Image.Image) -> np.ndarray:
        """Convert PIL Image to OpenCV format (numpy array)."""
        return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

    @staticmethod
    def cv2_to_pil(cv2_image: np.ndarray) -> Image.Image:
        """Convert OpenCV image (numpy array) to PIL Image."""
        return Image.fromarray(cv2.cvtColor(cv2_image, cv2.COLOR_BGR2RGB))
