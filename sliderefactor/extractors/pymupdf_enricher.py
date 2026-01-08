"""
Enrich SlideGraph with font metadata and background images using PyMuPDF.
"""

from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from sliderefactor.models import BackgroundConfig, SlideGraph, BBox


class PyMuPDFEnricher:
    """Augment SlideGraph slides with font hints and background images."""

    def __init__(self, background_area_threshold: float = 0.85) -> None:
        self.background_area_threshold = background_area_threshold

    def enrich(self, pdf_path: Path, slide_graph: SlideGraph, images_dir: Path) -> None:
        """Populate font metadata and background images on SlideGraph slides."""
        import fitz

        pdf_path = Path(pdf_path)
        images_dir = Path(images_dir)
        images_dir.mkdir(parents=True, exist_ok=True)

        with fitz.open(pdf_path) as doc:
            for slide in slide_graph.slides:
                if slide.page_index >= doc.page_count:
                    continue

                page = doc.load_page(slide.page_index)
                page_dict = page.get_text("dict")
                page_area = page.rect.width * page.rect.height

                spans = self._collect_text_spans(page_dict)
                scale_x, scale_y = self._scale_factors(page, slide)
                for block in slide.blocks:
                    if block.type != "text":
                        continue
                    block_bbox = self._scale_bbox(block.bbox, scale_x, scale_y)
                    font_name, font_size = self._match_font(block_bbox, spans)
                    if font_name:
                        block.metadata["font_name"] = font_name
                    if font_size:
                        block.metadata["font_size"] = font_size

                background_candidate = self._find_background_image_block(
                    page_dict, page_area
                )
                if background_candidate:
                    image_ref = self._save_background_image(
                        page, background_candidate, images_dir, slide.page_index
                    )
                    if image_ref:
                        slide.background = BackgroundConfig(
                            mode="image", image_ref=image_ref
                        )

    def _collect_text_spans(self, page_dict: Dict) -> List[Dict]:
        spans = []
        for block in page_dict.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    spans.append(
                        {
                            "bbox": span.get("bbox"),
                            "font": span.get("font"),
                            "size": span.get("size"),
                        }
                    )
        return spans

    def _match_font(
        self, block_bbox: BBox, spans: List[Dict]
    ) -> Tuple[Optional[str], Optional[int]]:
        font_weights: Dict[str, float] = defaultdict(float)
        size_weights: Dict[int, float] = defaultdict(float)
        for span in spans:
            span_bbox = span.get("bbox")
            if not span_bbox:
                continue
            overlap = self._intersection_area(block_bbox, span_bbox)
            if overlap <= 0:
                continue
            font_name = span.get("font")
            font_size = span.get("size")
            if font_name:
                font_weights[font_name] += overlap
            if font_size:
                size_weights[int(round(font_size))] += overlap

        if not font_weights:
            return None, None

        dominant_font = max(font_weights.items(), key=lambda item: item[1])[0]
        dominant_size = None
        if size_weights:
            dominant_size = max(size_weights.items(), key=lambda item: item[1])[0]

        return dominant_font, dominant_size

    def _find_background_image_block(
        self, page_dict: Dict, page_area: float
    ) -> Optional[Dict]:
        best_block = None
        best_area = 0.0
        for block in page_dict.get("blocks", []):
            if block.get("type") != 1:
                continue
            bbox = block.get("bbox")
            if not bbox:
                continue
            area = self._bbox_area(bbox)
            if area > best_area:
                best_area = area
                best_block = block

        if best_block and best_area / page_area >= self.background_area_threshold:
            return best_block
        return None

    def _save_background_image(
        self, page, image_block: Dict, images_dir: Path, page_index: int
    ) -> Optional[str]:
        image_bytes = image_block.get("image")
        if not image_bytes:
            bbox = image_block.get("bbox")
            if not bbox:
                return None
            pixmap = page.get_pixmap(clip=fitz.Rect(bbox), alpha=False)
            image_bytes = pixmap.tobytes("png")

        image_ref = f"slide{page_index}_background.png"
        image_path = images_dir / image_ref
        image_path.write_bytes(image_bytes)
        return image_ref

    @staticmethod
    def _scale_factors(page, slide) -> Tuple[float, float]:
        return page.rect.width / slide.width_px, page.rect.height / slide.height_px

    @staticmethod
    def _scale_bbox(bbox: BBox, scale_x: float, scale_y: float) -> BBox:
        return BBox(
            coords=[
                bbox.x0 * scale_x,
                bbox.y0 * scale_y,
                bbox.x1 * scale_x,
                bbox.y1 * scale_y,
            ]
        )

    @staticmethod
    def _bbox_area(bbox: List[float]) -> float:
        return max(0.0, (bbox[2] - bbox[0])) * max(0.0, (bbox[3] - bbox[1]))

    @staticmethod
    def _intersection_area(block_bbox: BBox, span_bbox: List[float]) -> float:
        x0 = max(block_bbox.x0, span_bbox[0])
        y0 = max(block_bbox.y0, span_bbox[1])
        x1 = min(block_bbox.x1, span_bbox[2])
        y1 = min(block_bbox.y1, span_bbox[3])
        if x1 <= x0 or y1 <= y0:
            return 0.0
        return (x1 - x0) * (y1 - y0)
