"""
PPTX renderer using python-pptx.

Converts SlideElements into editable PowerPoint slides.
"""

from pathlib import Path
from typing import List, Dict, Tuple, Optional
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, PP_PARAGRAPH_ALIGNMENT
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor
from PIL import Image

from sliderefactor.models import (
    SlideElements,
    TextBoxElement,
    ImageElement,
    ShapeElement,
    BulletItem,
    Slide,
)


class PPTXRenderer:
    """
    Render SlideElements into a PowerPoint presentation using python-pptx.

    Features:
    - Text boxes with editable content
    - Bullet lists with proper nesting
    - Images with positioning
    - Style preservation (alignment, fonts, etc.)
    """

    # Style size mapping (relative to slide height)
    SIZE_MAP = {
        "xs": 0.02,  # 2% of slide height
        "sm": 0.03,  # 3%
        "md": 0.04,  # 4%
        "lg": 0.06,  # 6%
        "xl": 0.08,  # 8%
    }

    # Role-based default sizes
    ROLE_SIZE_MAP = {
        "title": "xl",
        "subtitle": "lg",
        "body": "md",
        "caption": "sm",
        "footer": "xs",
    }

    def __init__(
        self,
        slide_width_inches: float = 10.0,
        slide_height_inches: float = 7.5,
        dpi: int = 96,
    ):
        """
        Initialize renderer.

        Args:
            slide_width_inches: Slide width in inches
            slide_height_inches: Slide height in inches
            dpi: DPI for pixel-to-inch conversion
        """
        self.slide_width_inches = slide_width_inches
        self.slide_height_inches = slide_height_inches
        self.dpi = dpi

    def render(
        self,
        elements_list: List[SlideElements],
        slides_info: List[Slide],
        output_path: Path,
        images_dir: Path,
    ) -> Path:
        """
        Render all slides to a PPTX file.

        Args:
            elements_list: List of SlideElements for each slide
            slides_info: List of original Slide objects (for dimensions)
            output_path: Path to save the PPTX file
            images_dir: Directory containing extracted images

        Returns:
            Path to the generated PPTX file
        """
        prs = Presentation()

        # Set slide dimensions
        prs.slide_width = Inches(self.slide_width_inches)
        prs.slide_height = Inches(self.slide_height_inches)

        print(f"[PPTX] Rendering {len(elements_list)} slides")

        for i, (elements, slide_info) in enumerate(zip(elements_list, slides_info)):
            print(
                f"[PPTX] Rendering slide {i + 1}/{len(elements_list)} ({len(elements.elements)} elements)"
            )

            # Use blank slide layout
            slide_layout = prs.slide_layouts[6]  # Blank layout
            slide = prs.slides.add_slide(slide_layout)

            # Render each element
            for element in elements.elements:
                if isinstance(element, TextBoxElement):
                    self._render_textbox(element, slide, slide_info)
                elif isinstance(element, ImageElement):
                    self._render_image(element, slide, slide_info, images_dir)
                elif isinstance(element, ShapeElement):
                    self._render_shape(element, slide, slide_info)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        prs.save(str(output_path))

        print(f"[PPTX] Saved presentation to {output_path}")
        return output_path

    def _render_textbox(
        self, element: TextBoxElement, slide, slide_info: Slide
    ) -> None:
        """Render a text box element."""
        # Convert bbox from pixels to inches
        left, top, width, height = self._bbox_to_inches(
            element.bbox.to_list(),
            slide_info.width_px,
            slide_info.height_px,
        )

        # Add text box
        textbox = slide.shapes.add_textbox(
            Inches(left), Inches(top), Inches(width), Inches(height)
        )
        text_frame = textbox.text_frame
        text_frame.word_wrap = True

        # Set vertical alignment
        if element.style_hints.vertical_align == "middle":
            text_frame.vertical_anchor = 1  # MSO_ANCHOR.MIDDLE
        elif element.style_hints.vertical_align == "bottom":
            text_frame.vertical_anchor = 2  # MSO_ANCHOR.BOTTOM
        else:
            text_frame.vertical_anchor = 0  # MSO_ANCHOR.TOP

        # Determine font size
        size_key = element.style_hints.size or self.ROLE_SIZE_MAP.get(element.role, "md")
        font_size = int(self.SIZE_MAP[size_key] * slide_info.height_px)

        # Add content
        if element.structure.type == "bullets":
            self._add_bullets(
                text_frame, element.structure.items, element.style_hints, font_size
            )
        else:  # paragraphs
            self._add_paragraphs(
                text_frame, element.structure.items, element.style_hints, font_size
            )

    def _add_bullets(
        self, text_frame, items: List[BulletItem], style_hints, font_size: int
    ) -> None:
        """Add bullet points to text frame."""
        text_frame.clear()  # Remove default paragraph

        for i, item in enumerate(items):
            if isinstance(item, str):
                # Simple string bullet
                p = text_frame.paragraphs[0] if i == 0 else text_frame.add_paragraph()
                p.text = item
                p.level = 0
            elif isinstance(item, BulletItem):
                p = text_frame.paragraphs[0] if i == 0 else text_frame.add_paragraph()
                p.level = item.level

                # Add runs
                if item.runs:
                    for run_data in item.runs:
                        run = p.add_run()
                        run.text = run_data.text

                        if run_data.bold:
                            run.font.bold = True
                        if run_data.italic:
                            run.font.italic = True
                        if run_data.underline:
                            run.font.underline = True
                        if run_data.font_size:
                            run.font.size = Pt(run_data.font_size)
                        else:
                            run.font.size = Pt(font_size)
                else:
                    # No runs, just set text
                    p.text = item.text

            # Apply paragraph-level styling
            if style_hints.align == "center":
                p.alignment = PP_PARAGRAPH_ALIGNMENT.CENTER
            elif style_hints.align == "right":
                p.alignment = PP_PARAGRAPH_ALIGNMENT.RIGHT
            else:
                p.alignment = PP_PARAGRAPH_ALIGNMENT.LEFT

            # Set font size for the paragraph
            if not item.runs if isinstance(item, BulletItem) else True:
                for run in p.runs:
                    if run.font.size is None:
                        run.font.size = Pt(font_size)

            # Apply weight
            if style_hints.weight == "bold":
                for run in p.runs:
                    run.font.bold = True

    def _add_paragraphs(
        self, text_frame, items: List[str], style_hints, font_size: int
    ) -> None:
        """Add paragraphs to text frame."""
        text_frame.clear()

        for i, text in enumerate(items):
            p = text_frame.paragraphs[0] if i == 0 else text_frame.add_paragraph()
            p.text = str(text)

            # Apply styling
            if style_hints.align == "center":
                p.alignment = PP_PARAGRAPH_ALIGNMENT.CENTER
            elif style_hints.align == "right":
                p.alignment = PP_PARAGRAPH_ALIGNMENT.RIGHT
            else:
                p.alignment = PP_PARAGRAPH_ALIGNMENT.LEFT

            for run in p.runs:
                run.font.size = Pt(font_size)
                if style_hints.weight == "bold":
                    run.font.bold = True

    def _render_image(
        self, element: ImageElement, slide, slide_info: Slide, images_dir: Path
    ) -> None:
        """Render an image element."""
        # Find image file
        image_path = images_dir / element.image_ref

        if not image_path.exists():
            print(f"[PPTX] Warning: Image not found: {image_path}")
            return

        # Convert bbox from pixels to inches
        left, top, width, height = self._bbox_to_inches(
            element.bbox.to_list(),
            slide_info.width_px,
            slide_info.height_px,
        )

        try:
            # Add picture
            slide.shapes.add_picture(
                str(image_path),
                Inches(left),
                Inches(top),
                width=Inches(width),
                height=Inches(height),
            )
        except Exception as e:
            print(f"[PPTX] Warning: Failed to add image {image_path}: {e}")

    def _render_shape(
        self, element: ShapeElement, slide, slide_info: Slide
    ) -> None:
        """Render a shape element."""
        # Convert bbox from pixels to inches
        left, top, width, height = self._bbox_to_inches(
            element.bbox.to_list(),
            slide_info.width_px,
            slide_info.height_px,
        )

        # Map shape type
        shape_type_map = {
            "rectangle": MSO_SHAPE.RECTANGLE,
            "circle": MSO_SHAPE.OVAL,
            "line": MSO_SHAPE.ROUNDED_RECTANGLE,  # Placeholder
            "arrow": MSO_SHAPE.RIGHT_ARROW,
        }

        shape_type = shape_type_map.get(element.shape_type, MSO_SHAPE.RECTANGLE)

        # Add shape
        shape = slide.shapes.add_shape(
            shape_type,
            Inches(left),
            Inches(top),
            Inches(width),
            Inches(height),
        )

        # Apply fill color
        if element.fill_color:
            color = self._parse_hex_color(element.fill_color)
            if color:
                shape.fill.solid()
                shape.fill.fore_color.rgb = color

        # Apply border
        if element.border_color:
            color = self._parse_hex_color(element.border_color)
            if color:
                shape.line.color.rgb = color
                shape.line.width = Pt(element.border_width)

    def _bbox_to_inches(
        self, bbox: List[float], slide_width_px: float, slide_height_px: float
    ) -> Tuple[float, float, float, float]:
        """
        Convert bounding box from pixels to inches.

        Args:
            bbox: [x0, y0, x1, y1] in pixels
            slide_width_px: Slide width in pixels
            slide_height_px: Slide height in pixels

        Returns:
            (left, top, width, height) in inches
        """
        x0, y0, x1, y1 = bbox

        # Convert to relative coordinates (0-1)
        x0_rel = x0 / slide_width_px
        y0_rel = y0 / slide_height_px
        x1_rel = x1 / slide_width_px
        y1_rel = y1 / slide_height_px

        # Convert to inches
        left = x0_rel * self.slide_width_inches
        top = y0_rel * self.slide_height_inches
        width = (x1_rel - x0_rel) * self.slide_width_inches
        height = (y1_rel - y0_rel) * self.slide_height_inches

        return left, top, width, height

    @staticmethod
    def _parse_hex_color(hex_color: str) -> Optional[RGBColor]:
        """Parse hex color string to RGBColor."""
        try:
            hex_color = hex_color.lstrip("#")
            if len(hex_color) == 6:
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                return RGBColor(r, g, b)
        except ValueError:
            pass
        return None
