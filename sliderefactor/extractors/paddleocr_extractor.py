"""
PaddleOCR fallback extractor using PP-StructureV3.

Uses the latest PaddleOCR 3.x PP-StructureV3 pipeline for layout analysis
and text extraction. Based on the pdf2slides reference implementation.
"""

import os
from pathlib import Path
from typing import Optional, List
from datetime import datetime
import numpy as np

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
    OCR extractor using PaddleOCR PP-StructureV3 pipeline.
    
    PP-StructureV3 (PaddleOCR 3.x) provides:
    - Layout detection with block labels (text, figure, table, etc.)
    - Text recognition with content extraction
    - Reading order detection
    - Table structure recognition
    
    Note: Requires paddleocr[all]>=3.0.0 and paddlepaddle>=3.0.0
    """

    def __init__(
        self,
        lang: str = "en",
        use_gpu: bool = False,
        dpi: int = 400,
        use_table_recognition: bool = True,
        use_formula_recognition: bool = False,  # Disabled by default for speed
    ):
        try:
            from paddleocr import PPStructureV3
        except ImportError:
            raise ImportError(
                "PaddleOCR 3.x not installed. Install with: pip install 'paddleocr[all]>=3.0.0' 'paddlepaddle>=3.0.0'"
            )

        # Determine text recognition model based on language
        # PP-OCRv5 supports: ch, en, fr, de, japan, korean, chinese_cht, etc.
        text_rec_model = None
        if lang == "en":
            text_rec_model = "en_PP-OCRv4_mobile_rec"
        # For other languages, PP-StructureV3 uses default Chinese+English model
        
        # Initialize PP-StructureV3 pipeline
        # Disable preprocessing modules for speed on already-clean PDF slides
        init_kwargs = {
            "use_doc_orientation_classify": False,  # Skip orientation detection
            "use_doc_unwarping": False,             # Skip de-warping
            "use_textline_orientation": False,       # Skip textline orientation
            "use_table_recognition": use_table_recognition,
            "use_formula_recognition": use_formula_recognition,
            "use_chart_recognition": False,          # Skip chart recognition
            "use_seal_recognition": False,           # Skip seal recognition
        }
        
        # Set device
        if use_gpu:
            init_kwargs["device"] = "gpu:0"
        else:
            init_kwargs["device"] = "cpu"
        
        # Set text recognition model if specified
        if text_rec_model:
            init_kwargs["text_recognition_model_name"] = text_rec_model
        
        print(f"[PaddleOCR] Initializing PP-StructureV3 with: {init_kwargs}")
        self.pipeline = PPStructureV3(**init_kwargs)
        self.dpi = dpi
        self.name = "paddleocr_v3"

    def extract(self, pdf_path: Path, output_dir: Path) -> SlideGraph:
        """
        Extract all pages from a PDF using PP-StructureV3.

        Args:
            pdf_path: Path to the input PDF
            output_dir: Directory to save extracted images

        Returns:
            SlideGraph with all pages
        """
        pdf_path = Path(pdf_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"[PaddleOCR] Processing PDF with PP-StructureV3: {pdf_path.name}")
        
        # PP-StructureV3 can process PDF files directly
        # It handles page-by-page processing internally
        output = self.pipeline.predict(input=str(pdf_path))
        
        # Convert to list if generator
        results = list(output)
        total_pages = len(results)
        
        print(f"[PaddleOCR] Found {total_pages} pages")

        meta = SlideGraphMeta(
            source="notebooklm_flattened_pdf",
            dpi=self.dpi,
            version="1.0",
            created_at=datetime.utcnow().isoformat() + "Z",
            total_pages=total_pages,
            extraction_engines=["paddleocr_v3"],
        )

        # Also convert PDF to images for cropping figure regions
        page_images = self._pdf_to_pil_images(pdf_path)

        slides = []
        for page_index, res in enumerate(results):
            print(f"[PaddleOCR] Processing page {page_index + 1}/{total_pages}")
            
            # Get page dimensions from the image
            if page_index < len(page_images):
                page_img = page_images[page_index]
                width, height = page_img.size
            else:
                # Fallback dimensions
                width, height = 1920, 1080
            
            # Save page image for reference
            page_image_path = output_dir / f"page_{page_index}.png"
            if page_index < len(page_images):
                page_images[page_index].save(page_image_path)
            
            # Process result
            slide = self._process_page_result(
                res, page_index, width, height, 
                page_images[page_index] if page_index < len(page_images) else None,
                output_dir
            )
            slides.append(slide)

        return SlideGraph(meta=meta, slides=slides)

    def _process_page_result(
        self, 
        res, 
        page_index: int, 
        width: int, 
        height: int,
        page_image,  # PIL Image
        output_dir: Path
    ) -> Slide:
        """Process a single page result from PP-StructureV3."""
        from PIL import Image
        
        blocks = []
        
        # Get the JSON result
        try:
            result_dict = res.json
        except AttributeError:
            # If .json is not available, try accessing as dict
            result_dict = res if isinstance(res, dict) else {}
        
        # PP-StructureV3 nests results under 'res' key
        # Structure: res.json['res']['parsing_res_list']
        inner_res = result_dict.get("res", result_dict)
        if isinstance(inner_res, dict):
            parsing_res_list = inner_res.get("parsing_res_list", [])
            overall_ocr_res = inner_res.get("overall_ocr_res", {})
        else:
            # Fallback to top-level access
            parsing_res_list = result_dict.get("parsing_res_list", [])
            overall_ocr_res = result_dict.get("overall_ocr_res", {})
        
        image_counter = 0
        
        for i, block_info in enumerate(parsing_res_list):
            # Extract block properties
            block_bbox_raw = block_info.get("block_bbox")
            block_label = block_info.get("block_label", "text").lower()
            block_content = block_info.get("block_content", "")
            block_id_raw = block_info.get("block_id", i)
            
            # Convert bbox
            if block_bbox_raw is None:
                continue
            
            # block_bbox is typically a numpy array [x0, y0, x1, y1]
            if hasattr(block_bbox_raw, 'tolist'):
                bbox_list = block_bbox_raw.tolist()
            elif isinstance(block_bbox_raw, (list, tuple)):
                bbox_list = list(block_bbox_raw)
            else:
                continue
            
            # Ensure we have 4 coordinates
            if len(bbox_list) != 4:
                continue
            
            x0, y0, x1, y1 = [float(c) for c in bbox_list]
            
            # Validate bbox (ensure x0 < x1 and y0 < y1)
            if x0 >= x1 or y0 >= y1:
                # Try to fix by swapping if reversed
                if x0 > x1:
                    x0, x1 = x1, x0
                if y0 > y1:
                    y0, y1 = y1, y0
                if x0 >= x1 or y0 >= y1:
                    continue
            
            try:
                bbox = BBox(coords=[x0, y0, x1, y1])
            except ValueError as e:
                print(f"[PaddleOCR] Warning: Invalid bbox for block {i}: {e}")
                continue
            
            # Map label to block type
            block_type = "text"  # Default
            image_ref = None
            
            if block_label in ["figure", "image", "chart"]:
                block_type = "image"
                
                # Crop and save image region
                if page_image is not None:
                    try:
                        # Crop the image region
                        crop_box = (int(x0), int(y0), int(x1), int(y1))
                        cropped = page_image.crop(crop_box)
                        
                        # Save cropped image
                        image_filename = f"page_{page_index}_img_{image_counter}.png"
                        image_path = output_dir / image_filename
                        cropped.save(image_path)
                        image_ref = str(image_path)
                        image_counter += 1
                    except Exception as e:
                        print(f"[PaddleOCR] Warning: Failed to crop image region: {e}")
                        
            elif block_label == "table":
                # Tables can be rendered as images or as structured tables
                # For now, treat as image (easier to render correctly)
                block_type = "image"
                
                if page_image is not None:
                    try:
                        crop_box = (int(x0), int(y0), int(x1), int(y1))
                        cropped = page_image.crop(crop_box)
                        
                        image_filename = f"page_{page_index}_table_{image_counter}.png"
                        image_path = output_dir / image_filename
                        cropped.save(image_path)
                        image_ref = str(image_path)
                        image_counter += 1
                    except Exception as e:
                        print(f"[PaddleOCR] Warning: Failed to crop table region: {e}")
            
            # For text blocks, use block_content
            text_content = ""
            if block_type == "text" and block_content:
                text_content = str(block_content).strip()
            
            block_id = f"p{page_index}_b{i}_{block_label}"
            
            block = Block(
                id=block_id,
                type=block_type,
                bbox=bbox,
                text=text_content if block_type == "text" else None,
                image_ref=image_ref if block_type == "image" else None,
                lines=[],  # PP-StructureV3 provides block-level content, not line-level
                confidence=1.0,  # PP-StructureV3 doesn't provide per-block confidence
                provenance=[
                    Provenance(
                        engine=f"paddleocr_v3_{block_label}",
                        ref=block_id,
                        timestamp=datetime.utcnow().isoformat() + "Z",
                    )
                ],
                metadata={"original_label": block_label},
            )
            blocks.append(block)
        
        # If no blocks from parsing_res_list, try fallback to overall_ocr_res
        if not blocks and overall_ocr_res:
            blocks = self._extract_from_overall_ocr(overall_ocr_res, page_index, width, height)
        
        print(f"[PaddleOCR] Page {page_index}: Extracted {len(blocks)} blocks")

        slide = Slide(
            page_index=page_index,
            width_px=float(width),
            height_px=float(height),
            background=BackgroundConfig(mode="blank"),
            blocks=blocks,
            dpi=self.dpi,
        )

        return slide

    def _extract_from_overall_ocr(
        self, 
        overall_ocr_res: dict, 
        page_index: int,
        width: int,
        height: int
    ) -> List[Block]:
        """Fallback: Extract blocks from overall OCR results when parsing_res_list is empty."""
        blocks = []
        
        rec_texts = overall_ocr_res.get("rec_texts", [])
        rec_polys = overall_ocr_res.get("rec_polys", [])
        rec_scores = overall_ocr_res.get("rec_scores", [])
        
        for i, (text, poly, score) in enumerate(zip(rec_texts, rec_polys, rec_scores)):
            if not text or not text.strip():
                continue
            
            # Convert polygon to bounding box
            if hasattr(poly, 'tolist'):
                poly = poly.tolist()
            
            if len(poly) >= 4:
                # poly is typically [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                if isinstance(poly[0], (list, tuple)):
                    xs = [p[0] for p in poly]
                    ys = [p[1] for p in poly]
                    x0, y0 = min(xs), min(ys)
                    x1, y1 = max(xs), max(ys)
                else:
                    # Flat list [x0, y0, x1, y1]
                    x0, y0, x1, y1 = poly[0], poly[1], poly[2], poly[3]
            else:
                continue
            
            if x0 >= x1 or y0 >= y1:
                continue
            
            try:
                bbox = BBox(coords=[float(x0), float(y0), float(x1), float(y1)])
            except ValueError:
                continue
            
            block_id = f"p{page_index}_ocr_{i}"
            
            block = Block(
                id=block_id,
                type="text",
                bbox=bbox,
                text=str(text).strip(),
                confidence=float(score) if score else 1.0,
                provenance=[
                    Provenance(
                        engine="paddleocr_v3_ocr",
                        ref=block_id,
                        timestamp=datetime.utcnow().isoformat() + "Z",
                    )
                ],
            )
            blocks.append(block)
        
        return blocks

    def _pdf_to_pil_images(self, pdf_path: Path, page_indices: Optional[List[int]] = None) -> List:
        """Convert PDF pages to PIL images using PyMuPDF."""
        import fitz
        from PIL import Image

        doc = fitz.open(str(pdf_path))
        images = []
        
        iterator = page_indices if page_indices is not None else range(len(doc))
        
        # Calculate zoom for DPI (default PDF is 72 DPI)
        zoom = self.dpi / 72
        mat = fitz.Matrix(zoom, zoom)

        for idx in iterator:
            if idx < 0 or idx >= len(doc):
                continue
            page = doc[idx]
            pix = page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            images.append(img)
            
        doc.close()
        return images

    def extract_page(self, pdf_path: Path, page_num: int, output_dir: Path) -> Slide:
        """Extract a single page from the PDF."""
        # For single page, still use the full pipeline but filter results
        pdf_path = Path(pdf_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Get the specific page image
        images = self._pdf_to_pil_images(pdf_path, page_indices=[page_num])
        
        if not images:
            raise ValueError(f"Could not extract page {page_num} from PDF")
        
        page_image = images[0]
        width, height = page_image.size
        
        # Process just this page with PP-StructureV3
        # Note: PP-StructureV3 can take a numpy array directly
        import numpy as np
        image_np = np.array(page_image)
        
        output = self.pipeline.predict(input=image_np)
        results = list(output)
        
        if not results:
            # Return empty slide
            return Slide(
                page_index=page_num,
                width_px=float(width),
                height_px=float(height),
                background=BackgroundConfig(mode="blank"),
                blocks=[],
                dpi=self.dpi,
            )
        
        return self._process_page_result(
            results[0], page_num, width, height, page_image, output_dir
        )
