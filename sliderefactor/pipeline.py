"""
Main orchestration pipeline for SlideRefactor.

Coordinates extraction, LLM processing, and PPTX generation.
"""

import json
import os
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from sliderefactor.models import SlideGraph, SlideElements
from sliderefactor.extractors.datalab import DatalabExtractor
from sliderefactor.extractors.paddleocr_extractor import PaddleOCRExtractor
from sliderefactor.extractors.pymupdf_enricher import PyMuPDFEnricher
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
    ):
        """
        Initialize pipeline.

        Args:
            extractor: "datalab" or "paddleocr"
            use_preprocessing: Apply OpenCV preprocessing before OCR
            generate_audit: Generate audit HTML report
            save_intermediate: Save SlideGraph JSON
            debug: Enable debug mode (saves prompts and responses)
        """
        self.extractor_name = extractor
        self.use_preprocessing = use_preprocessing
        self.generate_audit = generate_audit
        self.save_intermediate = save_intermediate
        self.debug = debug

        # Initialize components
        if extractor == "datalab":
            self.extractor = DatalabExtractor()
        elif extractor == "paddleocr":
            self.extractor = PaddleOCRExtractor()
        else:
            raise ValueError(f"Unknown extractor: {extractor}")

        self.preprocessor = OpenCVPreprocessor() if use_preprocessing else None
        self.converter = BlockToElementConverter()
        self.renderer = PPTXRenderer()
        self.audit_generator = AuditHTMLGenerator() if generate_audit else None
        self.enricher = PyMuPDFEnricher()

    def process(
        self,
        pdf_path: Path,
        output_dir: Optional[Path] = None,
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
        print(f"\n[Stage 2/4] Preparing slide images")
        self._prepare_slide_images(pdf_path, images_dir, slide_graph)

        # Stage 2.5: Enrich with fonts/backgrounds
        print(f"\n[Stage 2.5/4] Enriching fonts and backgrounds")
        self.enricher.enrich(pdf_path, slide_graph, images_dir)

        # Stage 3: LLM processing - convert blocks to elements
        print(f"\n[Stage 3/4] LLM processing ({len(slide_graph.slides)} slides)")
        elements_list: List[SlideElements] = []

        for slide in slide_graph.slides:
            print(f"  → Processing slide {slide.page_index + 1}/{len(slide_graph.slides)}")
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

        If using Datalab, we need to convert PDF pages to images separately.
        If using PaddleOCR, images are already created during extraction.
        """
        # Check if images already exist
        existing_images = list(images_dir.glob("page_*.png"))
        if len(existing_images) >= len(slide_graph.slides):
            print(f"[Stage 2/4] Using existing {len(existing_images)} slide images")
            return

        # Convert PDF to images
        try:
            from pdf2image import convert_from_path

            print(f"[Stage 2/4] Converting PDF to images (DPI={slide_graph.meta.dpi})")
            images = convert_from_path(str(pdf_path), dpi=slide_graph.meta.dpi)

            for i, image in enumerate(images):
                image_path = images_dir / f"page_{i}.png"
                image.save(image_path)

            print(f"[Stage 2/4] Saved {len(images)} slide images")

        except ImportError:
            print("[Stage 2/4] Warning: pdf2image not available, skipping image generation")
        except Exception as e:
            print(f"[Stage 2/4] Warning: Failed to convert PDF to images: {e}")

    @classmethod
    def from_slidegraph(
        cls,
        slidegraph_path: Path,
        output_dir: Optional[Path] = None,
        generate_audit: bool = True,
    ) -> dict:
        """
        Resume pipeline from a saved SlideGraph JSON.

        Useful for re-processing with different LLM prompts or PPTX settings
        without re-running expensive OCR extraction.

        Args:
            slidegraph_path: Path to SlideGraph JSON file
            output_dir: Output directory
            generate_audit: Generate audit HTML

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
        renderer = PPTXRenderer()
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
