"""
Enrich SlideGraph with font metadata, detect images/icons, and background images using PyMuPDF.
"""

from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np

from sliderefactor.models import BackgroundConfig, SlideGraph, BBox, Block, Provenance


class PyMuPDFEnricher:
    """Augment SlideGraph slides with font hints and background images."""

    def __init__(self, background_area_threshold: float = 0.85) -> None:
        self.background_area_threshold = background_area_threshold

    def enrich(self, pdf_path: Path, slide_graph: SlideGraph, images_dir: Path) -> None:
        """Populate font metadata, detect images/icons, crop images, and detect background images."""
        import fitz
        from PIL import Image

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

                # Process each block for font metadata
                for block in slide.blocks:
                    if block.type == "text":
                        block_bbox = self._scale_bbox(block.bbox, scale_x, scale_y)
                        font_info = self._match_font(block_bbox, spans)
                        # Store all extracted font styling info
                        if font_info.get("font_name"):
                            block.metadata["font_name"] = font_info["font_name"]
                        if font_info.get("font_size"):
                            block.metadata["font_size"] = font_info["font_size"]
                        if font_info.get("font_bold"):
                            block.metadata["font_bold"] = True
                        if font_info.get("font_italic"):
                            block.metadata["font_italic"] = True
                        if font_info.get("font_color"):
                            block.metadata["font_color"] = font_info["font_color"]

                    elif block.type == "image" and block.metadata.get("needs_crop"):
                        # Crop image from page screenshot
                        self._crop_image_from_page(
                            slide, block, images_dir, slide_graph.meta.dpi
                        )

                # Detect visual regions (icons/images) that weren't detected by OCR
                # This is critical for flat PDFs where Datalab only finds text
                detected_images = self._detect_visual_regions(
                    slide, images_dir, slide_graph.meta.dpi
                )
                if detected_images:
                    print(f"[Enricher] Detected {len(detected_images)} visual regions on slide {slide.page_index}")
                    slide.blocks.extend(detected_images)

                # Check for full-page background (skip if we detected separate images)
                if not detected_images:
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
        """Collect text spans with font, size, flags (bold/italic), and color."""
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
                            "flags": span.get("flags", 0),  # Bit field: 1=superscript, 2=italic, 4=serifed, 8=monospace, 16=bold
                            "color": span.get("color"),  # Integer RGB value
                        }
                    )
        return spans

    def _match_font(
        self, block_bbox: BBox, spans: List[Dict]
    ) -> Dict:
        """
        Match font styling from overlapping spans.
        
        Returns dict with:
        - font_name: dominant font name
        - font_size: dominant font size
        - font_bold: True if dominant spans are bold
        - font_italic: True if dominant spans are italic
        - font_color: hex color string (e.g. "#FF0000")
        """
        font_weights: Dict[str, float] = defaultdict(float)
        size_weights: Dict[int, float] = defaultdict(float)
        bold_weight = 0.0
        non_bold_weight = 0.0
        italic_weight = 0.0
        non_italic_weight = 0.0
        color_weights: Dict[int, float] = defaultdict(float)
        
        total_overlap = 0.0
        
        for span in spans:
            span_bbox = span.get("bbox")
            if not span_bbox:
                continue
            overlap = self._intersection_area(block_bbox, span_bbox)
            if overlap <= 0:
                continue
                
            total_overlap += overlap
            
            font_name = span.get("font")
            font_size = span.get("size")
            flags = span.get("flags", 0)
            color = span.get("color")
            
            if font_name:
                font_weights[font_name] += overlap
            if font_size:
                size_weights[int(round(font_size))] += overlap
            
            # Check bold flag (bit 4, value 16)
            if flags & 16:
                bold_weight += overlap
            else:
                non_bold_weight += overlap
            
            # Check italic flag (bit 1, value 2)
            if flags & 2:
                italic_weight += overlap
            else:
                non_italic_weight += overlap
            
            # Track color
            if color is not None:
                color_weights[color] += overlap

        if not font_weights and total_overlap == 0:
            return {}

        result = {}
        
        if font_weights:
            result["font_name"] = max(font_weights.items(), key=lambda item: item[1])[0]
        if size_weights:
            result["font_size"] = max(size_weights.items(), key=lambda item: item[1])[0]
        
        # Bold if majority of text is bold
        if bold_weight > non_bold_weight:
            result["font_bold"] = True
        
        # Italic if majority of text is italic
        if italic_weight > non_italic_weight:
            result["font_italic"] = True
        
        # Dominant color (convert int to hex)
        if color_weights:
            dominant_color = max(color_weights.items(), key=lambda item: item[1])[0]
            if dominant_color != 0:  # Skip black (default)
                # PyMuPDF color is RGB int: 0xRRGGBB
                r = (dominant_color >> 16) & 0xFF
                g = (dominant_color >> 8) & 0xFF
                b = dominant_color & 0xFF
                result["font_color"] = f"#{r:02X}{g:02X}{b:02X}"
        
        return result

    def _find_background_image_block(
        self, page_dict: Dict, page_area: float
    ) -> Optional[Dict]:
        """
        Find a genuine embedded background image (not a rendered page).

        Only returns an image block if it has actual embedded image data,
        not just a reference that would require rendering the page.
        """
        best_block = None
        best_area = 0.0
        for block in page_dict.get("blocks", []):
            if block.get("type") != 1:
                continue
            # Only consider blocks with actual embedded image data
            if not block.get("image"):
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
        """Save a genuine embedded background image."""
        import fitz

        image_bytes = image_block.get("image")
        if not image_bytes:
            # Don't render the page as background - this causes double content
            # Only save if there's actual embedded image data
            return None

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

    def _crop_image_from_page(
        self, slide, block, images_dir: Path, dpi: int
    ) -> None:
        """Crop an image region from the page screenshot."""
        from PIL import Image

        page_image_path = images_dir / f"page_{slide.page_index}.png"
        if not page_image_path.exists():
            print(f"[Enricher] Warning: Page image not found for cropping: {page_image_path}")
            return

        try:
            with Image.open(page_image_path) as img:
                # Block bbox is in slide coordinate system (which matches Datalab output)
                # Page image is at the specified DPI
                # We need to convert bbox coordinates to image pixel coordinates

                # Calculate scale factor: image pixels per slide unit
                scale_x = img.width / slide.width_px
                scale_y = img.height / slide.height_px

                # Get crop box in image coordinates
                x0 = int(block.bbox.x0 * scale_x)
                y0 = int(block.bbox.y0 * scale_y)
                x1 = int(block.bbox.x1 * scale_x)
                y1 = int(block.bbox.y1 * scale_y)

                # Ensure valid crop box
                x0 = max(0, min(x0, img.width - 1))
                y0 = max(0, min(y0, img.height - 1))
                x1 = max(x0 + 1, min(x1, img.width))
                y1 = max(y0 + 1, min(y1, img.height))

                if x1 <= x0 or y1 <= y0:
                    print(f"[Enricher] Warning: Invalid crop box for block {block.id}")
                    return

                # Crop and save
                cropped = img.crop((x0, y0, x1, y1))
                output_path = images_dir / block.image_ref
                cropped.save(output_path, "PNG")

                # Clear the needs_crop flag
                block.metadata["needs_crop"] = False
                print(f"[Enricher] Cropped image {block.image_ref} ({x1-x0}x{y1-y0}px)")

        except Exception as e:
            print(f"[Enricher] Error cropping image {block.id}: {e}")

    def _detect_visual_regions(
        self, slide, images_dir: Path, dpi: int
    ) -> List[Block]:
        """
        Detect visual regions (icons, images) that weren't found by OCR.

        For flat PDFs, Datalab only detects text. This method finds non-text
        regions that contain visual content and creates image blocks for them.
        """
        from PIL import Image
        from datetime import datetime
        import cv2

        page_image_path = images_dir / f"page_{slide.page_index}.png"
        if not page_image_path.exists():
            return []

        try:
            # Load page image
            img = cv2.imread(str(page_image_path))
            if img is None:
                return []

            img_height, img_width = img.shape[:2]

            # Calculate scale factors between slide coordinates and image pixels
            scale_x = img_width / slide.width_px
            scale_y = img_height / slide.height_px

            # Create mask of text regions (areas to exclude)
            text_mask = np.zeros((img_height, img_width), dtype=np.uint8)

            for block in slide.blocks:
                if block.type == "text":
                    # Convert block bbox to image coordinates with padding
                    x0 = max(0, int(block.bbox.x0 * scale_x) - 5)
                    y0 = max(0, int(block.bbox.y0 * scale_y) - 5)
                    x1 = min(img_width, int(block.bbox.x1 * scale_x) + 5)
                    y1 = min(img_height, int(block.bbox.y1 * scale_y) + 5)
                    text_mask[y0:y1, x0:x1] = 255

            # Detect the dominant background color (most common color)
            # Reshape image to list of pixels
            pixels = img.reshape(-1, 3)
            # Find the most common color (simple approach: mode of rounded values)
            pixels_rounded = (pixels // 16) * 16  # Round to reduce color variations
            unique, counts = np.unique(pixels_rounded, axis=0, return_counts=True)
            bg_color = unique[np.argmax(counts)]

            # Create mask of pixels that differ significantly from background
            color_diff = np.abs(img.astype(np.int16) - bg_color.astype(np.int16))
            color_distance = np.sum(color_diff, axis=2)
            content_mask = (color_distance > 30).astype(np.uint8) * 255

            # Also detect edges for icons/graphics that might be similar to background color
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            content_mask = cv2.bitwise_or(content_mask, edges)

            # Remove text regions from content mask
            non_text_content = cv2.bitwise_and(content_mask, cv2.bitwise_not(text_mask))

            # Morphological operations to clean up and connect nearby regions
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (10, 10))
            non_text_content = cv2.morphologyEx(non_text_content, cv2.MORPH_CLOSE, kernel)
            non_text_content = cv2.morphologyEx(non_text_content, cv2.MORPH_OPEN, kernel)

            # Find contours (connected regions)
            contours, _ = cv2.findContours(
                non_text_content, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            detected_blocks = []
            min_area = 400  # Minimum area in pixels (20x20)
            max_area_ratio = 0.7  # Max 70% of slide area (to avoid detecting the whole slide)
            max_area = img_width * img_height * max_area_ratio
            
            # Collect existing image block bboxes (in image pixel coordinates)
            existing_image_bboxes = []
            for block in slide.blocks:
                if block.type == "image":
                    # Convert to image coordinates
                    ex0 = int(block.bbox.x0 * scale_x)
                    ey0 = int(block.bbox.y0 * scale_y)
                    ex1 = int(block.bbox.x1 * scale_x)
                    ey1 = int(block.bbox.y1 * scale_y)
                    existing_image_bboxes.append((ex0, ey0, ex1, ey1))

            for i, contour in enumerate(contours):
                x, y, w, h = cv2.boundingRect(contour)
                area = w * h

                # Filter by size
                if area < min_area or area > max_area:
                    continue

                # Filter out very thin regions (likely lines/borders)
                aspect_ratio = max(w, h) / max(min(w, h), 1)
                if aspect_ratio > 15:  # Very elongated
                    continue

                # Check if region has actual content (not just noise)
                region = img[y:y+h, x:x+w]
                region_diff = np.abs(region.astype(np.int16) - bg_color.astype(np.int16))
                region_distance = np.sum(region_diff, axis=2)
                content_ratio = np.sum(region_distance > 30) / (w * h)
                if content_ratio < 0.05:  # Less than 5% has content
                    continue

                # Check overlap with existing image blocks to avoid duplicates
                detected_bbox = (x, y, x + w, y + h)
                skip_due_to_overlap = False
                for ex0, ey0, ex1, ey1 in existing_image_bboxes:
                    # Calculate intersection
                    ix0 = max(detected_bbox[0], ex0)
                    iy0 = max(detected_bbox[1], ey0)
                    ix1 = min(detected_bbox[2], ex1)
                    iy1 = min(detected_bbox[3], ey1)
                    
                    if ix1 > ix0 and iy1 > iy0:
                        intersection_area = (ix1 - ix0) * (iy1 - iy0)
                        detected_area = area
                        existing_area = (ex1 - ex0) * (ey1 - ey0)
                        
                        # Skip if >40% of either region overlaps
                        if intersection_area > 0.4 * detected_area or intersection_area > 0.4 * existing_area:
                            print(f"[Enricher] Skipping overlapping region at ({x},{y}) - already detected")
                            skip_due_to_overlap = True
                            break
                
                if skip_due_to_overlap:
                    continue

                # Convert back to slide coordinates
                bbox_x0 = x / scale_x
                bbox_y0 = y / scale_y
                bbox_x1 = (x + w) / scale_x
                bbox_y1 = (y + h) / scale_y

                # Create image reference and crop
                image_ref = f"detected_p{slide.page_index}_r{i}.png"

                # Crop and save the region
                with Image.open(page_image_path) as pil_img:
                    cropped = pil_img.crop((x, y, x + w, y + h))
                    output_path = images_dir / image_ref
                    cropped.save(output_path, "PNG")

                # Create block
                block = Block(
                    id=f"detected_p{slide.page_index}_r{i}",
                    type="image",
                    bbox=BBox(coords=[bbox_x0, bbox_y0, bbox_x1, bbox_y1]),
                    image_ref=image_ref,
                    confidence=0.8,
                    provenance=[
                        Provenance(
                            engine="visual_detection",
                            ref=f"detected_p{slide.page_index}_r{i}",
                            timestamp=datetime.utcnow().isoformat() + "Z",
                            metadata={"method": "contour_detection", "area": area},
                        )
                    ],
                    metadata={"detected": True},
                )
                detected_blocks.append(block)
                print(f"[Enricher] Detected visual region: {image_ref} ({w}x{h}px at {x},{y})")

            return detected_blocks

        except Exception as e:
            print(f"[Enricher] Error detecting visual regions: {e}")
            import traceback
            traceback.print_exc()
            return []
