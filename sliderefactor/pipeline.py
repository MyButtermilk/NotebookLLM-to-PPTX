"""
Main orchestration pipeline for SlideRefactor.

Coordinates extraction, LLM processing, and PPTX generation.
"""

import json
import os
from pathlib import Path
from typing import Optional, List, Callable
from datetime import datetime

from sliderefactor.models import (
    SlideGraph, SlideElements, Slide, TextBoxElement, ImageElement,
    BBox, TextStructure, StyleHints, FontHints, ElementProvenance
)
from sliderefactor.extractors.datalab import DatalabExtractor
from sliderefactor.extractors.paddleocr_extractor import PaddleOCRExtractor
from sliderefactor.preprocessors import OpenCVPreprocessor
from sliderefactor.prompt import BlockToElementConverter
from sliderefactor.renderers import PPTXRenderer
from sliderefactor.audit import AuditHTMLGenerator


class SlideRefactorPipeline:
    """
    End-to-end pipeline for converting flattened slide PDFs to editable PPTX.

    Pipeline stages:
    1. (Optional) Preprocessing: deskew, denoise, sharpen
    2. Extraction: Datalab API (primary) or PaddleOCR (fallback)
    3. LLM Processing: Convert blocks to PPTX elements
    4. PPTX Rendering: Generate editable PowerPoint
    5. (Optional) Audit: Generate HTML QA report
    """

    def __init__(
        self,
        extractor: str = "datalab",
        use_preprocessing: bool = False,
        generate_audit: bool = True,
        save_intermediate: bool = True,
        debug: bool = False,
        render_background: bool = True,
        skip_llm: bool = False,
    ):
        """
        Initialize pipeline.

        Args:
            extractor: "datalab" or "paddleocr"
            use_preprocessing: Apply OpenCV preprocessing before OCR
            generate_audit: Generate audit HTML report
            save_intermediate: Save SlideGraph JSON
            debug: Enable debug mode (saves prompts and responses)
            render_background: Whether to render background images (disable to avoid "double text")
            skip_llm: Skip LLM processing and use direct block-to-element conversion
        """
        self.extractor_name = extractor
        self.use_preprocessing = use_preprocessing
        self.generate_audit = generate_audit
        self.save_intermediate = save_intermediate
        self.debug = debug
        self.render_background = render_background
        self.skip_llm = skip_llm

        # Initialize components
        if extractor == "datalab":
            self.extractor = DatalabExtractor()
        elif extractor == "paddleocr":
            self.extractor = PaddleOCRExtractor()
        else:
            raise ValueError(f"Unknown extractor: {extractor}")

        self.preprocessor = OpenCVPreprocessor() if use_preprocessing else None
        self.converter = BlockToElementConverter() if not skip_llm else None
        self.renderer = PPTXRenderer(render_background=render_background)
        self.audit_generator = AuditHTMLGenerator() if generate_audit else None

    def process(
        self,
        pdf_path: Path,
        output_dir: Optional[Path] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> dict:
        """
        Process a PDF through the full pipeline.

        Args:
            pdf_path: Path to input PDF file
            output_dir: Output directory (default: ./output/<pdf_name>)

        Returns:
            Dictionary with paths to generated files:
            {
                "pptx": Path to PPTX file,
                "slidegraph": Path to SlideGraph JSON (if enabled),
                "audit": Path to audit HTML (if enabled)
            }
        """
        pdf_path = Path(pdf_path)

        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        # Set up output directory
        if output_dir is None:
            output_dir = Path("output") / pdf_path.stem

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        images_dir = output_dir / "images"
        images_dir.mkdir(exist_ok=True)

        print(f"\n{'='*60}")
        print(f"SlideRefactor Pipeline")
        print(f"{'='*60}")
        print(f"Input: {pdf_path}")
        print(f"Output: {output_dir}")
        print(f"Extractor: {self.extractor_name}")
        print(f"Preprocessing: {self.use_preprocessing}")
        print(f"{'='*60}\n")

        # Stage 1: Extract slides using Datalab or PaddleOCR
        if progress_callback:
            progress_callback(20.0, f"Extracting content with {self.extractor_name}")
        print(f"[Stage 1/4] Extraction with {self.extractor_name}")
        slide_graph = self.extractor.extract(pdf_path, images_dir)

        # Save intermediate SlideGraph
        slidegraph_path = None
        if self.save_intermediate:
            slidegraph_path = output_dir / f"{pdf_path.stem}.slidegraph.json"
            with open(slidegraph_path, "w", encoding="utf-8") as f:
                json.dump(slide_graph.to_dict(), f, indent=2, ensure_ascii=False)
            print(f"[Stage 1/4] Saved SlideGraph to {slidegraph_path}")

        # Stage 2: Convert slides to images for audit (if using Datalab)
        if progress_callback:
            progress_callback(40.0, "Preparing slide images")
        print(f"\n[Stage 2/4] Preparing slide images")
        self._prepare_slide_images(pdf_path, images_dir, slide_graph)

        # Stage 2.5: Crop images that need it (from page screenshots)
        if progress_callback:
            progress_callback(50.0, "Cropping images from pages")
        print(f"\n[Stage 2.5/4] Cropping images from page screenshots")
        self._crop_images_from_pages(slide_graph, images_dir)

        # Stage 3: Convert blocks to elements (LLM or direct)
        if self.skip_llm:
            print(f"\n[Stage 3/4] Direct block conversion ({len(slide_graph.slides)} slides) - LLM skipped")
        else:
            print(f"\n[Stage 3/4] LLM processing ({len(slide_graph.slides)} slides)")
        elements_list: List[SlideElements] = []

        for i, slide in enumerate(slide_graph.slides):
            print(f"  → Processing slide {slide.page_index + 1}/{len(slide_graph.slides)}")
            if progress_callback:
                p = 60.0 + (30.0 * (i / len(slide_graph.slides)))
                if self.skip_llm:
                    progress_callback(p, f"Converting: Slide {i+1}/{len(slide_graph.slides)}")
                else:
                    progress_callback(p, f"LLM Processing: Slide {i+1}/{len(slide_graph.slides)}")

            if self.skip_llm:
                elements = self._direct_convert_blocks(slide)
            else:
                elements = self.converter.convert(slide, debug=self.debug)
            elements_list.append(elements)

        # Save elements JSON
        elements_json_path = output_dir / f"{pdf_path.stem}.elements.json"
        with open(elements_json_path, "w", encoding="utf-8") as f:
            json.dump(
                [elem.to_dict() for elem in elements_list],
                f,
                indent=2,
                ensure_ascii=False,
            )
        print(f"[Stage 3/4] Saved elements to {elements_json_path}")

        # Stage 4: Render PPTX
        if progress_callback:
            progress_callback(90.0, "Rendering PPTX")
        print(f"\n[Stage 4/4] Rendering PPTX")
        pptx_path = output_dir / f"{pdf_path.stem}.pptx"
        self.renderer.render(elements_list, slide_graph.slides, pptx_path, images_dir)

        # Generate audit HTML
        audit_path = None
        if self.generate_audit and self.audit_generator:
            print(f"\n[Audit] Generating QA report")
            audit_path = output_dir / f"{pdf_path.stem}.audit.html"
            self.audit_generator.generate(
                slide_graph.slides,
                elements_list,
                images_dir,
                audit_path,
                meta=slide_graph.meta.model_dump(),
            )

        # Summary
        print(f"\n{'='*60}")
        print(f"✓ Pipeline Complete")
        print(f"{'='*60}")
        print(f"PPTX: {pptx_path}")
        if slidegraph_path:
            print(f"SlideGraph JSON: {slidegraph_path}")
        if audit_path:
            print(f"Audit HTML: {audit_path}")
        print(f"{'='*60}\n")

        return {
            "pptx": pptx_path,
            "slidegraph": slidegraph_path,
            "audit": audit_path,
            "elements": elements_json_path,
        }

    def _prepare_slide_images(
        self, pdf_path: Path, images_dir: Path, slide_graph: SlideGraph
    ) -> None:
        """
        Ensure slide images exist for audit HTML.

        Uses PyMuPDF (fitz) for PDF to image conversion since it doesn't
        require external dependencies like Poppler.
        """
        # Check if images already exist
        existing_images = list(images_dir.glob("page_*.png"))
        if len(existing_images) >= len(slide_graph.slides):
            print(f"[Stage 2/4] Using existing {len(existing_images)} slide images")
            return

        # Use PyMuPDF for PDF to image conversion (no external dependencies)
        try:
            import fitz  # PyMuPDF

            print(f"[Stage 2/4] Converting PDF to images using PyMuPDF (DPI={slide_graph.meta.dpi})")
            doc = fitz.open(str(pdf_path))
            
            # Calculate zoom factor for desired DPI (72 is base DPI)
            zoom = slide_graph.meta.dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)

            for i, page in enumerate(doc):
                pix = page.get_pixmap(matrix=mat)
                image_path = images_dir / f"page_{i}.png"
                pix.save(str(image_path))

            print(f"[Stage 2/4] Saved {len(doc)} slide images")
            doc.close()

        except ImportError:
            print("[Stage 2/4] Warning: PyMuPDF not available, trying pdf2image...")
            # Fallback to pdf2image if PyMuPDF is not available
            try:
                from pdf2image import convert_from_path
                print(f"[Stage 2/4] Converting PDF to images using pdf2image")
                images = convert_from_path(str(pdf_path), dpi=slide_graph.meta.dpi)
                for i, image in enumerate(images):
                    image_path = images_dir / f"page_{i}.png"
                    image.save(image_path)
                print(f"[Stage 2/4] Saved {len(images)} slide images")
            except Exception as e:
                print(f"[Stage 2/4] Warning: Failed to convert PDF to images: {e}")
        except Exception as e:
            print(f"[Stage 2/4] Warning: Failed to convert PDF to images: {e}")

    def _crop_images_from_pages(self, slide_graph: SlideGraph, images_dir: Path) -> None:
        """
        Crop images from page screenshots for blocks that need it.

        This handles blocks where Datalab detected an image region but
        couldn't extract the actual image data (common with flat PDFs).
        """
        try:
            from PIL import Image
        except ImportError:
            print("[Stage 2.5/4] Warning: PIL not available, skipping image cropping")
            return

        for slide in slide_graph.slides:
            page_image_path = images_dir / f"page_{slide.page_index}.png"
            if not page_image_path.exists():
                continue

            try:
                page_img = Image.open(page_image_path)
                img_width, img_height = page_img.size

                # Calculate scale factors
                scale_x = img_width / slide.width_px
                scale_y = img_height / slide.height_px

                for block in slide.blocks:
                    # Check if this block needs cropping
                    if block.type == "image" and block.metadata.get("needs_crop"):
                        image_ref = block.image_ref
                        if not image_ref:
                            continue

                        output_path = images_dir / image_ref
                        if output_path.exists():
                            continue  # Already cropped

                        # Get bbox and scale to image coordinates
                        x0, y0, x1, y1 = block.bbox.coords
                        crop_box = (
                            int(x0 * scale_x),
                            int(y0 * scale_y),
                            int(x1 * scale_x),
                            int(y1 * scale_y)
                        )

                        # Validate crop box
                        if crop_box[2] <= crop_box[0] or crop_box[3] <= crop_box[1]:
                            print(f"[Crop] Invalid crop box for {image_ref}: {crop_box}")
                            continue

                        # Crop and save
                        try:
                            cropped = page_img.crop(crop_box)
                            cropped.save(output_path)
                            print(f"[Crop] Saved {image_ref} ({cropped.width}x{cropped.height}px)")
                        except Exception as e:
                            print(f"[Crop] Error cropping {image_ref}: {e}")

                page_img.close()
            except Exception as e:
                print(f"[Stage 2.5/4] Error processing page {slide.page_index}: {e}")

    def _direct_convert_blocks(self, slide: Slide) -> SlideElements:
        """
        Convert blocks directly to elements without LLM.

        This is a simple, reliable conversion that uses OCR coordinates directly.
        """
        elements = []

        for block in slide.blocks:
            if block.type == "text":
                # Create a textbox for each text block
                text_content = block.text or ""
                if not text_content and block.lines:
                    text_content = "\n".join(line.text for line in block.lines if line.text)

                if not text_content.strip():
                    continue

                # Determine role based on position and size
                bbox = block.bbox.coords
                height = bbox[3] - bbox[1]
                y_pos = bbox[1]

                # Simple heuristics for role
                if y_pos < slide.height_px * 0.15 and height > 30:
                    role = "title"
                elif y_pos > slide.height_px * 0.85:
                    role = "footer"
                else:
                    role = "body"

                # Build structure as paragraphs
                structure = TextStructure(
                    type="paragraphs",
                    items=[text_content]
                )

                # Get font info from metadata (populated by PyMuPDF enricher)
                font_hints = None
                if (block.metadata.get("font_name") or block.metadata.get("font_size") or
                    block.metadata.get("font_bold") or block.metadata.get("font_italic") or
                    block.metadata.get("font_color")):
                    font_hints = FontHints(
                        name=block.metadata.get("font_name"),
                        size=int(round(block.metadata.get("font_size", 12))) if block.metadata.get("font_size") else None,
                        bold=block.metadata.get("font_bold"),
                        italic=block.metadata.get("font_italic"),
                        color=block.metadata.get("font_color"),
                    )

                # Determine style weight from font hints
                style_weight = "bold" if block.metadata.get("font_bold") else "regular"

                element = TextBoxElement(
                    bbox=block.bbox,
                    role=role,
                    structure=structure,
                    style_hints=StyleHints(
                        align="left",
                        weight=style_weight,
                        size="md",
                        vertical_align="top"
                    ),
                    font_hints=font_hints,
                    provenance=ElementProvenance(
                        block_ids=[block.id],
                        engines=["direct"],
                        min_confidence=block.confidence
                    )
                )
                elements.append(element)

            elif block.type == "image":
                # Create image element
                ref = block.image_ref or f"direct_{block.id.replace('/', '_')}.png"
                element = ImageElement(
                    bbox=block.bbox,
                    image_ref=ref,
                    crop_mode="fit",
                    provenance=ElementProvenance(
                        block_ids=[block.id],
                        engines=["direct"],
                        min_confidence=block.confidence
                    )
                )
                elements.append(element)

        print(f"[Direct] Created {len(elements)} elements from {len(slide.blocks)} blocks")
        return SlideElements(slide_index=slide.page_index, elements=elements)

    @classmethod
    def from_slidegraph(
        cls,
        slidegraph_path: Path,
        output_dir: Optional[Path] = None,
        generate_audit: bool = True,
        render_background: bool = True,
    ) -> dict:
        """
        Resume pipeline from a saved SlideGraph JSON.

        Useful for re-processing with different LLM prompts or PPTX settings
        without re-running expensive OCR extraction.

        Args:
            slidegraph_path: Path to SlideGraph JSON file
            output_dir: Output directory
            generate_audit: Generate audit HTML
            render_background: Whether to render background images (disable to avoid "double text")

        Returns:
            Dictionary with paths to generated files
        """
        slidegraph_path = Path(slidegraph_path)

        if not slidegraph_path.exists():
            raise FileNotFoundError(f"SlideGraph not found: {slidegraph_path}")

        # Load SlideGraph
        with open(slidegraph_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        slide_graph = SlideGraph.from_dict(data)

        # Set up output directory
        if output_dir is None:
            output_dir = slidegraph_path.parent

        output_dir = Path(output_dir)
        images_dir = output_dir / "images"

        print(f"\n{'='*60}")
        print(f"SlideRefactor Pipeline (from SlideGraph)")
        print(f"{'='*60}")
        print(f"SlideGraph: {slidegraph_path}")
        print(f"Output: {output_dir}")
        print(f"{'='*60}\n")

        # Initialize components
        converter = BlockToElementConverter()
        renderer = PPTXRenderer(render_background=render_background)
        audit_generator = AuditHTMLGenerator() if generate_audit else None

        # LLM processing
        print(f"[Stage 1/2] LLM processing ({len(slide_graph.slides)} slides)")
        elements_list: List[SlideElements] = []

        for slide in slide_graph.slides:
            print(f"  → Processing slide {slide.page_index + 1}/{len(slide_graph.slides)}")
            elements = converter.convert(slide)
            elements_list.append(elements)

        # Render PPTX
        print(f"\n[Stage 2/2] Rendering PPTX")
        pptx_path = output_dir / f"{slidegraph_path.stem.replace('.slidegraph', '')}.pptx"
        renderer.render(elements_list, slide_graph.slides, pptx_path, images_dir)

        # Generate audit HTML
        audit_path = None
        if generate_audit and audit_generator:
            print(f"\n[Audit] Generating QA report")
            audit_path = output_dir / f"{slidegraph_path.stem.replace('.slidegraph', '')}.audit.html"
            audit_generator.generate(
                slide_graph.slides,
                elements_list,
                images_dir,
                audit_path,
                meta=slide_graph.meta.model_dump(),
            )

        print(f"\n{'='*60}")
        print(f"✓ Pipeline Complete")
        print(f"{'='*60}")
        print(f"PPTX: {pptx_path}")
        if audit_path:
            print(f"Audit HTML: {audit_path}")
        print(f"{'='*60}\n")

        return {
            "pptx": pptx_path,
            "audit": audit_path,
        }
