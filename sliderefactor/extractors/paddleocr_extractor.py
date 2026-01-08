"""
PaddleOCR fallback extractor.

Open-source OCR engine for when Datalab is unavailable
or for privacy-sensitive workloads.
"""

import os
from pathlib import Path
from typing import Optional, List
from datetime import datetime
import json

from sliderefactor.models import (
    SlideGraph,
    SlideGraphMeta,
    Slide,
    Block,
    Line,
    BBox,
    Provenance,
    BackgroundConfig,
)


class PaddleOCRExtractor:
    """
    Fallback OCR extractor using PaddleOCR (open-source).

    Note: Requires paddleocr and paddlepaddle packages.
    Install with: pip install paddleocr paddlepaddle
    """

    def __init__(self, lang: str = "en", use_gpu: bool = False, dpi: int = 400):
        try:
            from paddleocr import PaddleOCR
        except ImportError:
            raise ImportError(
                "PaddleOCR not installed. Install with: pip install paddleocr paddlepaddle"
            )

        self.ocr = PaddleOCR(use_angle_cls=True, lang=lang, use_gpu=use_gpu)
        self.dpi = dpi
        self.name = "paddleocr"

    def extract(self, pdf_path: Path, output_dir: Path) -> SlideGraph:
        """
        Extract all pages from a PDF using PaddleOCR.

        Args:
            pdf_path: Path to the input PDF
            output_dir: Directory to save extracted images

        Returns:
            SlideGraph with all pages
        """
        pdf_path = Path(pdf_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Convert PDF to images first
        from pdf2image import convert_from_path
        from PIL import Image

        print(f"[PaddleOCR] Converting PDF to images: {pdf_path.name}")
        images = convert_from_path(str(pdf_path), dpi=self.dpi)

        meta = SlideGraphMeta(
            source="notebooklm_flattened_pdf",
            dpi=self.dpi,
            version="1.0",
            created_at=datetime.utcnow().isoformat() + "Z",
            total_pages=len(images),
            extraction_engines=["paddleocr"],
        )

        slides = []
        for page_index, image in enumerate(images):
            print(f"[PaddleOCR] Processing page {page_index + 1}/{len(images)}")

            # Save page image
            page_image_path = output_dir / f"page_{page_index}.png"
            image.save(page_image_path)

            # Run OCR
            slide = self._process_page_image(image, page_index, output_dir)
            slides.append(slide)

        return SlideGraph(meta=meta, slides=slides)

    def _process_page_image(
        self, image, page_index: int, output_dir: Path
    ) -> Slide:
        """Process a single page image with PaddleOCR."""
        import numpy as np
        from PIL import Image

        # Convert PIL image to numpy array
        if isinstance(image, Image.Image):
            image_np = np.array(image)
        else:
            image_np = image

        height, width = image_np.shape[:2]

        # Run OCR
        result = self.ocr.ocr(image_np, cls=True)

        blocks = []
        if result and result[0]:
            for i, line_data in enumerate(result[0]):
                if not line_data:
                    continue

                # PaddleOCR returns: [bbox_points, (text, confidence)]
                bbox_points = line_data[0]  # [[x0,y0], [x1,y1], [x2,y2], [x3,y3]]
                text_info = line_data[1]  # (text, confidence)

                if not text_info or len(text_info) < 2:
                    continue

                text, confidence = text_info[0], text_info[1]

                # Convert bbox points to [x0, y0, x1, y1]
                x_coords = [p[0] for p in bbox_points]
                y_coords = [p[1] for p in bbox_points]
                x0, y0 = min(x_coords), min(y_coords)
                x1, y1 = max(x_coords), max(y_coords)

                try:
                    bbox = BBox(coords=[x0, y0, x1, y1])
                except ValueError:
                    continue

                block_id = f"p{page_index}_b{i}"
                line = Line(text=text, bbox=bbox, confidence=float(confidence))

                block = Block(
                    id=block_id,
                    type="text",
                    bbox=bbox,
                    text=text,
                    lines=[line],
                    confidence=float(confidence),
                    provenance=[
                        Provenance(
                            engine="paddleocr",
                            ref=block_id,
                            timestamp=datetime.utcnow().isoformat() + "Z",
                        )
                    ],
                )
                blocks.append(block)

        slide = Slide(
            page_index=page_index,
            width_px=float(width),
            height_px=float(height),
            background=BackgroundConfig(mode="blank"),
            blocks=blocks,
            dpi=self.dpi,
        )

        return slide

    def extract_page(self, pdf_path: Path, page_num: int, output_dir: Path) -> Slide:
        """Extract a single page from the PDF."""
        from pdf2image import convert_from_path

        images = convert_from_path(
            str(pdf_path), dpi=self.dpi, first_page=page_num + 1, last_page=page_num + 1
        )

        if not images:
            raise ValueError(f"Could not extract page {page_num} from PDF")

        return self._process_page_image(images[0], page_num, output_dir)
