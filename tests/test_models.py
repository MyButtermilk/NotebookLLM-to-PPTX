"""
Tests for SlideGraph data models.
"""

import pytest
from sliderefactor.models import (
    BBox,
    Block,
    Slide,
    SlideGraph,
    SlideGraphMeta,
    Provenance,
)


def test_bbox_validation():
    """Test BBox validation."""
    # Valid bbox
    bbox = BBox(coords=[0, 0, 100, 100])
    assert bbox.x0 == 0
    assert bbox.y0 == 0
    assert bbox.x1 == 100
    assert bbox.y1 == 100
    assert bbox.width == 100
    assert bbox.height == 100

    # Invalid bbox (x0 > x1)
    with pytest.raises(ValueError):
        BBox(coords=[100, 0, 0, 100])


def test_block_creation():
    """Test Block creation."""
    bbox = BBox(coords=[10, 20, 110, 120])
    provenance = Provenance(engine="datalab", ref="test_ref")

    block = Block(
        id="b1",
        type="text",
        bbox=bbox,
        text="Test text",
        confidence=0.95,
        provenance=[provenance],
    )

    assert block.id == "b1"
    assert block.type == "text"
    assert block.text == "Test text"
    assert block.confidence == 0.95
    assert len(block.provenance) == 1


def test_slide_creation():
    """Test Slide creation."""
    bbox = BBox(coords=[0, 0, 100, 50])
    block = Block(
        id="b1",
        type="text",
        bbox=bbox,
        text="Test",
        confidence=0.9,
    )

    slide = Slide(
        page_index=0,
        width_px=1920,
        height_px=1080,
        blocks=[block],
    )

    assert slide.page_index == 0
    assert slide.width_px == 1920
    assert slide.height_px == 1080
    assert len(slide.blocks) == 1


def test_slidegraph_serialization():
    """Test SlideGraph JSON serialization."""
    meta = SlideGraphMeta(
        source="test",
        dpi=400,
        total_pages=1,
    )

    bbox = BBox(coords=[0, 0, 100, 50])
    block = Block(
        id="b1",
        type="text",
        bbox=bbox,
        text="Test",
    )

    slide = Slide(
        page_index=0,
        width_px=1920,
        height_px=1080,
        blocks=[block],
    )

    slide_graph = SlideGraph(meta=meta, slides=[slide])

    # Serialize to dict
    data = slide_graph.to_dict()
    assert "meta" in data
    assert "slides" in data
    assert len(data["slides"]) == 1

    # Deserialize from dict
    slide_graph2 = SlideGraph.from_dict(data)
    assert slide_graph2.meta.source == "test"
    assert len(slide_graph2.slides) == 1
    assert slide_graph2.slides[0].page_index == 0
