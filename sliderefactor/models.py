"""
Core data models for SlideRefactor.

Defines the canonical SlideGraph JSON schema using Pydantic for validation.
"""

from typing import List, Optional, Literal, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator


class BBox(BaseModel):
    """Bounding box in [x0, y0, x1, y1] format (top-left to bottom-right)."""

    coords: List[float] = Field(..., min_length=4, max_length=4)

    @field_validator("coords")
    @classmethod
    def validate_coords(cls, v: List[float]) -> List[float]:
        if not (v[0] < v[2] and v[1] < v[3]):
            raise ValueError("Invalid bbox: x0 < x2 and y0 < y2 required")
        return v

    def __getitem__(self, index: int) -> float:
        return self.coords[index]

    def __iter__(self):
        return iter(self.coords)

    def to_list(self) -> List[float]:
        return self.coords

    @property
    def x0(self) -> float:
        return self.coords[0]

    @property
    def y0(self) -> float:
        return self.coords[1]

    @property
    def x1(self) -> float:
        return self.coords[2]

    @property
    def y1(self) -> float:
        return self.coords[3]

    @property
    def width(self) -> float:
        return self.coords[2] - self.coords[0]

    @property
    def height(self) -> float:
        return self.coords[3] - self.coords[1]


class Provenance(BaseModel):
    """Track which extraction engine produced this data."""

    engine: str = Field(..., description="Engine name (datalab, paddleocr, layoutparser)")
    ref: Optional[str] = Field(None, description="Reference ID for auditability")
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Line(BaseModel):
    """A single line of text with its bounding box."""

    text: str
    bbox: BBox
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)


class Block(BaseModel):
    """
    A detected block from OCR/layout detection.
    Can be text, image, table, or shape_hint.
    """

    id: str
    type: Literal["text", "image", "table", "shape_hint"]
    bbox: BBox
    text: Optional[str] = None
    lines: List[Line] = Field(default_factory=list)
    image_ref: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    provenance: List[Provenance] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional engine-specific data"
    )


class BackgroundConfig(BaseModel):
    """Slide background configuration."""

    mode: Literal["blank", "color", "image"] = "blank"
    color: Optional[str] = None  # Hex color code
    image_ref: Optional[str] = None


class Slide(BaseModel):
    """A single slide with its blocks."""

    page_index: int = Field(ge=0)
    width_px: float = Field(gt=0)
    height_px: float = Field(gt=0)
    background: BackgroundConfig = Field(default_factory=lambda: BackgroundConfig(mode="blank"))
    blocks: List[Block] = Field(default_factory=list)
    dpi: int = Field(default=400, gt=0)


class SlideGraphMeta(BaseModel):
    """Metadata for the entire slide graph."""

    source: str = "notebooklm_flattened_pdf"
    dpi: int = Field(default=400, gt=0)
    version: str = "1.0"
    created_at: Optional[str] = None
    total_pages: int = Field(ge=0, default=0)
    extraction_engines: List[str] = Field(default_factory=list)


class SlideGraph(BaseModel):
    """
    The canonical intermediate representation of a slide deck.
    All extraction engines normalize into this format.
    """

    meta: SlideGraphMeta
    slides: List[Slide] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Export to dict for JSON serialization."""
        return self.model_dump(mode="json", exclude_none=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SlideGraph":
        """Load from dict."""
        return cls.model_validate(data)


# --- Element models (output of LLM prompt) ---


class TextRun(BaseModel):
    """A run of text with styling."""

    text: str
    bold: bool = False
    italic: bool = False
    underline: bool = False
    font_size: Optional[int] = None
    font_name: Optional[str] = None
    color: Optional[str] = None  # Hex color


class FontHints(BaseModel):
    """Font hints for a text box."""

    name: Optional[str] = None
    size: Optional[int] = None
    bold: Optional[bool] = None
    italic: Optional[bool] = None
    color: Optional[str] = None  # Hex color (e.g. "#FF0000")


class BulletItem(BaseModel):
    """A bullet point with optional nesting."""

    text: str
    level: int = Field(ge=0, default=0)
    runs: List[TextRun] = Field(default_factory=list)


class TextStructure(BaseModel):
    """Structure of text content (bullets or paragraphs)."""

    type: Literal["bullets", "paragraphs"]
    items: List[Union[BulletItem, str]] = Field(default_factory=list)


class StyleHints(BaseModel):
    """Styling hints for text boxes."""

    align: Literal["left", "center", "right"] = "left"
    weight: Literal["regular", "bold"] = "regular"
    size: Literal["xs", "sm", "md", "lg", "xl"] = "md"
    vertical_align: Literal["top", "middle", "bottom"] = "top"


class ElementProvenance(BaseModel):
    """Provenance for a PPTX element."""

    block_ids: List[str] = Field(default_factory=list)
    engines: List[str] = Field(default_factory=list)
    min_confidence: float = Field(ge=0.0, le=1.0, default=1.0)


class TextBoxElement(BaseModel):
    """A text box element for PPTX."""

    kind: Literal["textbox"] = "textbox"
    bbox: BBox
    role: Literal["title", "subtitle", "body", "caption", "footer"]
    structure: TextStructure
    style_hints: StyleHints = Field(default_factory=StyleHints)
    font_hints: Optional[FontHints] = None
    provenance: ElementProvenance = Field(default_factory=ElementProvenance)


class ImageElement(BaseModel):
    """An image element for PPTX."""

    kind: Literal["image"] = "image"
    bbox: BBox
    image_ref: str
    crop_mode: Literal["fill", "fit", "stretch"] = "fit"
    provenance: ElementProvenance = Field(default_factory=ElementProvenance)


class ShapeElement(BaseModel):
    """A shape element for PPTX (rectangles, circles, etc.)."""

    kind: Literal["shape"] = "shape"
    bbox: BBox
    shape_type: Literal["rectangle", "circle", "line", "arrow"]
    fill_color: Optional[str] = None
    border_color: Optional[str] = None
    border_width: float = 1.0
    provenance: ElementProvenance = Field(default_factory=ElementProvenance)


class TableCell(BaseModel):
    """A single cell in a table."""

    text: str = ""
    row_span: int = 1
    col_span: int = 1
    is_header: bool = False
    bold: bool = False
    align: Literal["left", "center", "right"] = "left"


class TableElement(BaseModel):
    """A table element for PPTX."""

    kind: Literal["table"] = "table"
    bbox: BBox
    rows: List[List[TableCell]] = Field(default_factory=list)
    header_rows: int = 0
    provenance: ElementProvenance = Field(default_factory=ElementProvenance)


Element = Union[TextBoxElement, ImageElement, ShapeElement, TableElement]


class SlideElements(BaseModel):
    """
    Output of the LLM prompt: a plan for PPTX elements.
    """

    slide_index: int
    elements: List[Element] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Export to dict for JSON serialization."""
        return self.model_dump(mode="json", exclude_none=True)
