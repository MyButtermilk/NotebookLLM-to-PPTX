"""
Datalab Convert API integration (Marker backend).

Datalab provides SOTA extraction with precise bounding boxes,
layout detection, and auditability via citations.

API Documentation: https://documentation.datalab.to/docs/welcome/api
"""

import os
import json
import re
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

    # Correct API endpoint per documentation
    DEFAULT_API_URL = "https://www.datalab.to/api/v1/marker"

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        dpi: int = 400,
        timeout: int = 300,
        poll_interval: int = 2,
    ):
        self.api_key = api_key or os.getenv("DATALAB_API_KEY")
        self.api_url = api_url or os.getenv("DATALAB_API_URL", self.DEFAULT_API_URL)
        self.dpi = dpi
        self.timeout = timeout
        self.poll_interval = poll_interval
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

        # Step 1: Submit PDF to Datalab API
        with open(pdf_path, "rb") as f:
            files = {"file": (pdf_path.name, f, "application/pdf")}
            # Correct auth header per documentation: X-API-Key
            headers = {"X-API-Key": self.api_key}
            data = {
                "output_format": "json",  # Request JSON with bounding boxes
                "mode": "accurate",  # accurate mode for best quality
                "paginate": "true",  # Get per-page results
                "add_block_ids": "true",  # Include block IDs for tracking
                "extract_images": "true",  # Extract images with base64 data
                "disable_image_captions": "true",  # Don't generate image captions
            }

            response = requests.post(
                self.api_url, headers=headers, files=files, data=data, timeout=60
            )

        if response.status_code != 200:
            raise RuntimeError(
                f"Datalab API error: {response.status_code} - {response.text}"
            )

        initial_result = response.json()
        
        # Step 2: Get the check URL for polling
        check_url = initial_result.get("request_check_url")
        if not check_url:
            # If no check_url, the result might be inline (for small files)
            if initial_result.get("status") == "complete":
                result = initial_result
            else:
                raise RuntimeError(
                    f"Datalab API error: No request_check_url in response: {initial_result}"
                )
        else:
            # Step 3: Poll until processing is complete
            print(f"[Datalab] Processing started, polling for results...")
            result = self._poll_for_results(check_url)

        # Save raw response for debugging
        raw_output_path = output_dir / "datalab_response.json"
        with open(raw_output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"[Datalab] Saved raw response to {raw_output_path}")

        # Parse response into SlideGraph
        slide_graph = self._parse_datalab_response(result, output_dir)

        print(f"[Datalab] Extracted {len(slide_graph.slides)} slides")
        return slide_graph

    def _poll_for_results(self, check_url: str) -> Dict[str, Any]:
        """
        Poll the check URL until processing is complete.
        
        Per API docs:
        - Poll every 2 seconds
        - Wait for status == "complete"
        """
        headers = {"X-API-Key": self.api_key}
        start_time = time.time()
        
        while True:
            elapsed = time.time() - start_time
            if elapsed > self.timeout:
                raise RuntimeError(f"Datalab API timeout after {self.timeout}s")
            
            response = requests.get(check_url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                raise RuntimeError(
                    f"Datalab polling error: {response.status_code} - {response.text}"
                )
            
            result = response.json()
            status = result.get("status", "")
            
            if status == "complete":
                print(f"[Datalab] Processing complete after {elapsed:.1f}s")
                return result
            elif status == "failed":
                error = result.get("error", "Unknown error")
                raise RuntimeError(f"Datalab processing failed: {error}")
            else:
                # Status is "processing" - continue polling
                print(f"[Datalab] Status: {status}, waiting...")
                time.sleep(self.poll_interval)

    def _parse_datalab_response(
        self, response: Dict[str, Any], output_dir: Path
    ) -> SlideGraph:
        """
        Parse Datalab API response into SlideGraph format.
        Handles the Marker-style JSON structure with nested children.
        """
        # Get metadata
        metadata = response.get("metadata", {})
        page_count = metadata.get("page_count", 0)
        
        # Get JSON data - structure varies based on output_format
        json_data = response.get("json", {})
        
        # In Marker, the root 'json' object has 'children' which are the pages
        pages_data = json_data.get("children", [])
        
        # If no children but markdown exists, fallback to markdown parsing
        if not pages_data and response.get("markdown"):
            pages_data = self._parse_markdown_pages(response.get("markdown", ""), page_count)
            # Normalize markdown pages to match the structure we expect
            pages = pages_data
        else:
            pages = []
            for i, page_item in enumerate(pages_data):
                # In Marker JSON, each page item has block_type: "Page"
                if page_item.get("block_type") == "Page":
                    pages.append(page_item)
                else:
                    # If it's not explicitly a Page block, but we have no better options,
                    # treat it as a page if it's top-level
                    pages.append(page_item)

        if not pages:
            # Absolute fallback if nothing else works
            print(f"[Datalab] Warning: No pages found in response, creating dummy page.")
            pages = [{
                "page": 0,
                "bbox": [0, 0, 1920, 1080],
                "children": []
            }]

        meta = SlideGraphMeta(
            source="notebooklm_flattened_pdf",
            dpi=self.dpi,
            version="1.0",
            created_at=datetime.utcnow().isoformat() + "Z",
            total_pages=len(pages),
            extraction_engines=["datalab"],
        )

        slides = []
        images = response.get("images", {})
        
        for i, page_data in enumerate(pages):
            page_index = page_data.get("page", i)
            # BBox in Datalab is often [x0, y0, x1, y1] for pages too
            bbox_coords = page_data.get("bbox", [0, 0, 1920, 1080])
            width = bbox_coords[2] - bbox_coords[0]
            height = bbox_coords[3] - bbox_coords[1]

            # Flatten nested children into flat blocks list
            blocks = []
            # Marker calls them 'children', SlideRefactor calls them 'blocks'
            raw_blocks = page_data.get("children", []) or page_data.get("blocks", [])
            
            # Recursively parse all blocks (including nested children)
            self._parse_blocks_recursive(
                raw_blocks, page_index, blocks, images, output_dir, counter=[0]
            )

            slide = Slide(
                page_index=page_index,
                width_px=float(width) if width > 0 else 1920.0,
                height_px=float(height) if height > 0 else 1080.0,
                background=BackgroundConfig(mode="blank"),
                blocks=blocks,
                dpi=self.dpi,
            )
            slides.append(slide)

        return SlideGraph(meta=meta, slides=slides)

    def _parse_blocks_recursive(
        self,
        blocks_data: List[Dict],
        page_index: int,
        result_blocks: List[Block],
        images: Dict[str, str],
        output_dir: Path,
        counter: List[int],
    ) -> None:
        """
        Recursively parse blocks and their children.

        Marker's JSON structure has nested children - we need to flatten them
        while preserving bounding boxes and types.
        """
        for block_data in blocks_data:
            block_type_raw = block_data.get("block_type") or block_data.get("type", "")

            # Skip container types that don't have content themselves
            container_types = {"Page", "Document", "Group"}

            if block_type_raw not in container_types:
                # Parse this block
                parsed_block = self._parse_block(
                    block_data, page_index, counter[0], images, output_dir
                )
                if parsed_block:
                    result_blocks.append(parsed_block)
                    counter[0] += 1

            # Recursively process children
            children = block_data.get("children", [])
            if children:
                self._parse_blocks_recursive(
                    children, page_index, result_blocks, images, output_dir, counter
                )

    def _parse_markdown_pages(self, markdown: str, page_count: int) -> List[Dict]:
        """Parse markdown content into page structures."""
        # Simple parsing: split by page markers if present, or create one page
        # Datalab markdown uses "---" or page markers
        pages = []
        
        # Split by common page separators
        page_texts = markdown.split("\n---\n")
        if len(page_texts) == 1:
            page_texts = [markdown]
        
        for i, text in enumerate(page_texts):
            if not text.strip():
                continue
            pages.append({
                "page_num": i,
                "width": 1920,
                "height": 1080,
                "blocks": [{
                    "type": "text",
                    "bbox": [50, 50, 1870, 1030],
                    "text": text.strip(),
                    "confidence": 1.0,
                    "lines": [{"text": line, "bbox": [50, 50 + j*30, 1870, 80 + j*30], "confidence": 1.0} 
                              for j, line in enumerate(text.strip().split("\n")) if line.strip()]
                }]
            })
        
        return pages

    def _parse_block(
        self,
        block_data: Dict[str, Any],
        page_index: int,
        block_index: int,
        images: Dict[str, str],
        output_dir: Path,
    ) -> Optional[Block]:
        """Parse a single block from Datalab response."""
        # Marker uses 'block_type' instead of 'type'
        block_type_raw = block_data.get("block_type") or block_data.get("type", "")

        # Skip empty or unknown block types
        if not block_type_raw:
            return None

        # Map Marker types to SlideRefactor types
        type_mapping = {
            "Text": "text",
            "TextInlineMath": "text",
            "SectionHeader": "text",
            "ListItem": "text",
            "ListGroup": None,  # Container, skip
            "Table": "table",
            "TableCell": None,  # Part of table, skip
            "Picture": "image",
            "Figure": "image",
            "FigureGroup": None,  # Container, skip
            "Caption": None,  # Skip captions per user request
            "Footnote": "text",
            "PageFooter": "text",
            "PageHeader": "text",
            "Code": "text",
            "Equation": "text",
            "Line": None,  # Low-level element, skip
            "Span": None,  # Low-level element, skip
        }

        block_type = type_mapping.get(block_type_raw)
        if block_type is None:
            # Skip this block type
            return None

        bbox_data = block_data.get("bbox", [0, 0, 100, 100])

        try:
            bbox = BBox(coords=bbox_data)
        except (ValueError, TypeError):
            return None

        # Validate bbox has non-zero size
        if bbox_data[2] <= bbox_data[0] or bbox_data[3] <= bbox_data[1]:
            return None

        block_id = block_data.get("id", f"/page/{page_index}/block/{block_index}")
        confidence = block_data.get("confidence", 1.0)

        provenance = [
            Provenance(
                engine="datalab",
                ref=block_id,
                timestamp=datetime.utcnow().isoformat() + "Z",
                metadata={"block_type": block_type_raw},
            )
        ]

        if block_type == "text":
            # Marker uses 'html' or 'text' - prefer text if available
            text = block_data.get("text", "")
            if not text:
                # Fall back to html and strip tags
                html = block_data.get("html", "")
                text = self._strip_html_tags(html)

            # Skip empty text blocks
            if not text or not text.strip():
                return None

            lines = [Line(text=text.strip(), bbox=bbox, confidence=confidence)]

            return Block(
                id=block_id,
                type="text",
                bbox=bbox,
                text=text.strip(),
                lines=lines,
                confidence=confidence,
                provenance=provenance,
            )

        elif block_type == "image":
            # Marker uses 'src' for image file name in children
            image_src = block_data.get("src")
            image_id = None
            if image_src:
                image_id = image_src
            else:
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

            # For flat PDFs: if no image data available, mark for later cropping
            # The image will be cropped from the page screenshot during enrichment
            if not image_ref:
                image_ref = f"crop_p{page_index}_b{block_index}.png"
                print(f"[Datalab] Image block {block_id} has no image data - will crop from page image")

            return Block(
                id=block_id,
                type="image",
                bbox=bbox,
                image_ref=image_ref,
                confidence=confidence,
                provenance=provenance,
                metadata={"needs_crop": image_ref.startswith("crop_")},
            )

        elif block_type == "table":
            # Treat tables as images - will be cropped from page screenshot
            image_ref = f"table_p{page_index}_b{block_index}.png"
            print(f"[Datalab] Table block {block_id} - will crop from page image")

            return Block(
                id=block_id,
                type="image",  # Treat as image for rendering
                bbox=bbox,
                image_ref=image_ref,
                confidence=confidence,
                provenance=provenance,
                metadata={
                    "original_type": "table",
                    "needs_crop": True,
                    "table_data": block_data.get("cells", []),
                },
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

    @staticmethod
    def _strip_html_tags(html: str) -> str:
        """Strip HTML tags from text and convert common entities."""
        if not html:
            return ""
        # Replace <br> tags with spaces
        text = re.sub(r'<br\s*/?>', ' ', html)
        # Remove all HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Convert common HTML entities
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")
        # Normalize whitespace
        text = ' '.join(text.split())
        return text.strip()

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
