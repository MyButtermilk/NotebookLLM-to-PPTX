"""
Datalab Convert API integration (Marker backend).

Datalab provides SOTA extraction with precise bounding boxes,
layout detection, and auditability via citations.
"""

import os
import json
import time
import requests
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

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


class DatalabExtractor:
    """
    Extract slide content using Datalab Convert API (Marker backend).

    Datalab provides:
    - Precise bounding boxes for all elements
    - Layout detection (columns, titles, figures)
    - Table and formula handling
    - Citation-level auditability
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        dpi: int = 400,
        timeout: int = 300,
    ):
        self.api_key = api_key or os.getenv("DATALAB_API_KEY")
        self.api_url = api_url or os.getenv(
            "DATALAB_API_URL", "https://api.datalab.to/v1/convert"
        )
        self.dpi = dpi
        self.timeout = timeout
        self.name = "datalab"

        if not self.api_key:
            raise ValueError(
                "Datalab API key required. Set DATALAB_API_KEY env var or pass api_key parameter."
            )

    def extract(self, pdf_path: Path, output_dir: Path) -> SlideGraph:
        """
        Extract all pages from a PDF using Datalab API.

        Args:
            pdf_path: Path to the input PDF
            output_dir: Directory to save extracted images and metadata

        Returns:
            SlideGraph with all pages
        """
        pdf_path = Path(pdf_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"[Datalab] Uploading PDF: {pdf_path.name}")

        # Upload PDF to Datalab
        with open(pdf_path, "rb") as f:
            files = {"file": (pdf_path.name, f, "application/pdf")}
            headers = {"Authorization": f"Bearer {self.api_key}"}
            data = {
                "output_format": "json",
                "extract_images": "true",
                "include_bboxes": "true",
                "dpi": str(self.dpi),
            }

            response = requests.post(
                self.api_url, headers=headers, files=files, data=data, timeout=self.timeout
            )

        if response.status_code != 200:
            raise RuntimeError(
                f"Datalab API error: {response.status_code} - {response.text}"
            )

        result = response.json()

        # Save raw response for debugging
        raw_output_path = output_dir / "datalab_response.json"
        with open(raw_output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"[Datalab] Saved raw response to {raw_output_path}")

        # Parse response into SlideGraph
        slide_graph = self._parse_datalab_response(result, output_dir)

        print(f"[Datalab] Extracted {len(slide_graph.slides)} slides")
        return slide_graph

    def _parse_datalab_response(
        self, response: Dict[str, Any], output_dir: Path
    ) -> SlideGraph:
        """
        Parse Datalab API response into SlideGraph format.

        Datalab response structure (simplified):
        {
            "pages": [
                {
                    "page_num": 0,
                    "width": 1920,
                    "height": 1080,
                    "blocks": [
                        {
                            "type": "text",
                            "bbox": [x0, y0, x1, y1],
                            "text": "...",
                            "lines": [{"text": "...", "bbox": [...]}],
                            "confidence": 0.95
                        },
                        {
                            "type": "image",
                            "bbox": [...],
                            "image_url": "...",
                            "image_id": "img_001"
                        }
                    ]
                }
            ],
            "images": { "img_001": "base64..." }
        }
        """
        meta = SlideGraphMeta(
            source="notebooklm_flattened_pdf",
            dpi=self.dpi,
            version="1.0",
            created_at=datetime.utcnow().isoformat() + "Z",
            total_pages=len(response.get("pages", [])),
            extraction_engines=["datalab"],
        )

        slides = []
        images = response.get("images", {})

        for page_data in response.get("pages", []):
            page_index = page_data.get("page_num", 0)
            width = page_data.get("width", 1920)
            height = page_data.get("height", 1080)

            blocks = []
            for i, block_data in enumerate(page_data.get("blocks", [])):
                block = self._parse_block(
                    block_data, page_index, i, images, output_dir
                )
                if block:
                    blocks.append(block)

            slide = Slide(
                page_index=page_index,
                width_px=float(width),
                height_px=float(height),
                background=BackgroundConfig(mode="blank"),
                blocks=blocks,
                dpi=self.dpi,
            )
            slides.append(slide)

        return SlideGraph(meta=meta, slides=slides)

    def _parse_block(
        self,
        block_data: Dict[str, Any],
        page_index: int,
        block_index: int,
        images: Dict[str, str],
        output_dir: Path,
    ) -> Optional[Block]:
        """Parse a single block from Datalab response."""
        block_type = block_data.get("type", "text")
        bbox_data = block_data.get("bbox", [0, 0, 100, 100])

        try:
            bbox = BBox(coords=bbox_data)
        except ValueError:
            # Invalid bbox, skip this block
            return None

        block_id = f"p{page_index}_b{block_index}"
        confidence = block_data.get("confidence", 1.0)

        provenance = [
            Provenance(
                engine="datalab",
                ref=block_data.get("id", block_id),
                timestamp=datetime.utcnow().isoformat() + "Z",
                metadata={"block_type": block_type},
            )
        ]

        if block_type == "text":
            text = block_data.get("text", "")
            lines_data = block_data.get("lines", [])
            lines = []

            for line_data in lines_data:
                try:
                    line_bbox = BBox(coords=line_data.get("bbox", bbox_data))
                    line = Line(
                        text=line_data.get("text", ""),
                        bbox=line_bbox,
                        confidence=line_data.get("confidence", confidence),
                    )
                    lines.append(line)
                except ValueError:
                    continue

            return Block(
                id=block_id,
                type="text",
                bbox=bbox,
                text=text,
                lines=lines,
                confidence=confidence,
                provenance=provenance,
            )

        elif block_type == "image":
            image_id = block_data.get("image_id", f"img_{block_id}")
            image_ref = None

            # Save image if base64 data is available
            if image_id in images:
                import base64

                image_data = images[image_id]
                if image_data.startswith("data:"):
                    # Strip data URL prefix
                    image_data = image_data.split(",", 1)[1]

                image_bytes = base64.b64decode(image_data)
                image_filename = f"slide{page_index}_{image_id}.png"
                image_path = output_dir / image_filename

                with open(image_path, "wb") as f:
                    f.write(image_bytes)

                image_ref = image_filename
            elif "image_url" in block_data:
                # External URL - download it
                image_ref = self._download_image(
                    block_data["image_url"], output_dir, page_index, block_index
                )

            return Block(
                id=block_id,
                type="image",
                bbox=bbox,
                image_ref=image_ref,
                confidence=confidence,
                provenance=provenance,
            )

        elif block_type == "table":
            # For now, treat tables as images (as per PRD)
            # TODO: Handle structured table data if available
            return Block(
                id=block_id,
                type="table",
                bbox=bbox,
                text=block_data.get("text", ""),
                confidence=confidence,
                provenance=provenance,
                metadata={"table_data": block_data.get("cells", [])},
            )

        return None

    def _download_image(
        self, url: str, output_dir: Path, page_index: int, block_index: int
    ) -> str:
        """Download an image from a URL."""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            image_filename = f"slide{page_index}_img{block_index}.png"
            image_path = output_dir / image_filename

            with open(image_path, "wb") as f:
                f.write(response.content)

            return image_filename
        except Exception as e:
            print(f"[Datalab] Warning: Failed to download image from {url}: {e}")
            return None

    def extract_page(self, pdf_path: Path, page_num: int, output_dir: Path) -> Slide:
        """
        Extract a single page (not commonly used with Datalab which processes entire PDFs).

        This is a simplified implementation that extracts the whole PDF
        and returns the requested page.
        """
        slide_graph = self.extract(pdf_path, output_dir)

        for slide in slide_graph.slides:
            if slide.page_index == page_num:
                return slide

        raise ValueError(f"Page {page_num} not found in PDF")
