"""
LLM-powered block-to-element conversion.

Uses Claude to intelligently convert OCR blocks into structured PPTX elements.
"""

import os
import json
from typing import List, Optional, Dict, Any
from pathlib import Path

from anthropic import Anthropic

from sliderefactor.models import (
    Slide,
    Block,
    SlideElements,
    TextBoxElement,
    ImageElement,
    ShapeElement,
    BBox,
    TextStructure,
    StyleHints,
    ElementProvenance,
    BulletItem,
    TextRun,
)


class BlockToElementConverter:
    """
    Converts SlideGraph blocks into PPTX-ready elements using LLM prompting.

    The LLM analyzes blocks to:
    - Determine reading order and column layouts
    - Merge related blocks into coherent text boxes
    - Infer bullet structure and nesting
    - Classify roles (title, subtitle, body, caption)
    - Preserve layout fidelity
    """

    SYSTEM_PROMPT = """You convert flattened slide OCR blocks into an editable PowerPoint plan.

Priorities:
1) Do not invent text or numbers. Use OCR output verbatim.
2) Maximize editability: text must become textboxes, not images.
3) Preserve layout: grouping, columns, bullets, titles.
4) If uncertain about a graphic element, keep it as an image.

Return valid JSON only. No extra text, no markdown code blocks, no explanations."""

    USER_PROMPT_TEMPLATE = """Slide dimensions:
- width_px: {width}
- height_px: {height}

Detected blocks:
{blocks_json}

Tasks:
A) Determine reading order. Support 2-column layouts.
B) Merge blocks into textboxes when they align and belong together (e.g., title spans, body paragraphs, bullet lists).
C) Infer bullets:
   - Use line indentation and leading glyphs (•, -, *, numbers).
   - Preserve nesting levels (0=top level, 1=first indent, etc.).
D) Classify each textbox role: "title" (slide title), "subtitle" (under title), "body" (main content), "caption" (small text near images), or "footer" (bottom of slide).

Output structure:
{{
  "elements": [
    {{
      "kind": "textbox",
      "bbox": [x0, y0, x1, y1],
      "role": "title|subtitle|body|caption|footer",
      "structure": {{
        "type": "bullets|paragraphs",
        "items": [
          // For bullets: {{"text": "...", "level": 0, "runs": [{{"text": "...", "bold": false}}]}}
          // For paragraphs: "plain text string"
        ]
      }},
      "style_hints": {{
        "align": "left|center|right",
        "weight": "regular|bold",
        "size": "xs|sm|md|lg|xl",
        "vertical_align": "top|middle|bottom"
      }},
      "provenance": {{
        "block_ids": ["p0_b1", "p0_b2"],
        "engines": ["datalab"],
        "min_confidence": 0.95
      }}
    }},
    {{
      "kind": "image",
      "bbox": [x0, y0, x1, y1],
      "image_ref": "slide0_img3.png",
      "crop_mode": "fit|fill|stretch",
      "provenance": {{
        "block_ids": ["p0_b5"],
        "engines": ["datalab"],
        "min_confidence": 0.99
      }}
    }}
  ]
}}

Rules:
- Never add missing words. Keep OCR text verbatim.
- Keep tables as images unless the OCR provides clear cell structure.
- Create shapes only if a block has type="shape_hint" with confidence >= 0.9.
- Ensure all bboxes are within slide bounds.
- For bullets, detect indentation by comparing bbox.x0 values.
- Leading glyphs: •, -, *, >, numbers followed by . or )

Output ONLY the JSON object. Do not include markdown formatting, code blocks, or explanatory text."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-5-sonnet-20241022",
        max_tokens: int = 4096,
    ):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Anthropic API key required. Set ANTHROPIC_API_KEY env var or pass api_key parameter."
            )

        self.client = Anthropic(api_key=self.api_key)
        self.model = model
        self.max_tokens = max_tokens

    def convert(self, slide: Slide, debug: bool = False) -> SlideElements:
        """
        Convert a slide's blocks into PPTX elements using LLM.

        Args:
            slide: Slide with OCR blocks
            debug: If True, save prompt and response to files

        Returns:
            SlideElements with textboxes, images, and shapes
        """
        # Prepare blocks JSON
        blocks_data = []
        for block in slide.blocks:
            block_dict = {
                "id": block.id,
                "type": block.type,
                "bbox": block.bbox.to_list(),
                "confidence": block.confidence,
            }

            if block.type == "text":
                block_dict["text"] = block.text
                block_dict["lines"] = [
                    {
                        "text": line.text,
                        "bbox": line.bbox.to_list(),
                        "confidence": line.confidence,
                    }
                    for line in block.lines
                ]
            elif block.type == "image":
                block_dict["image_ref"] = block.image_ref
            elif block.type == "shape_hint":
                block_dict["shape_type"] = block.metadata.get("shape_type", "rectangle")

            blocks_data.append(block_dict)

        blocks_json = json.dumps(blocks_data, indent=2, ensure_ascii=False)

        # Build prompt
        user_prompt = self.USER_PROMPT_TEMPLATE.format(
            width=slide.width_px,
            height=slide.height_px,
            blocks_json=blocks_json,
        )

        if debug:
            debug_dir = Path("output/debug")
            debug_dir.mkdir(parents=True, exist_ok=True)
            with open(debug_dir / f"prompt_slide_{slide.page_index}.txt", "w") as f:
                f.write(f"SYSTEM:\n{self.SYSTEM_PROMPT}\n\nUSER:\n{user_prompt}")

        # Call LLM
        print(f"[LLM] Processing slide {slide.page_index} with {len(slide.blocks)} blocks")

        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        response_text = response.content[0].text

        if debug:
            with open(debug_dir / f"response_slide_{slide.page_index}.txt", "w") as f:
                f.write(response_text)

        # Parse response
        try:
            # Clean response (remove markdown code blocks if present)
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()

            elements_data = json.loads(response_text)

            # Convert to Pydantic models
            elements = []
            for elem_dict in elements_data.get("elements", []):
                element = self._parse_element(elem_dict)
                if element:
                    elements.append(element)

            slide_elements = SlideElements(
                slide_index=slide.page_index,
                elements=elements,
            )

            print(f"[LLM] Generated {len(elements)} elements for slide {slide.page_index}")
            return slide_elements

        except json.JSONDecodeError as e:
            print(f"[LLM] Error parsing JSON response: {e}")
            print(f"[LLM] Response: {response_text[:500]}")
            # Return empty elements as fallback
            return SlideElements(slide_index=slide.page_index, elements=[])

    def _parse_element(self, elem_dict: Dict[str, Any]) -> Optional[Any]:
        """Parse a single element from LLM response."""
        kind = elem_dict.get("kind")

        try:
            bbox = BBox(coords=elem_dict["bbox"])

            if kind == "textbox":
                # Parse structure
                structure_data = elem_dict.get("structure", {})
                structure_type = structure_data.get("type", "paragraphs")
                items_data = structure_data.get("items", [])

                items = []
                if structure_type == "bullets":
                    for item_data in items_data:
                        if isinstance(item_data, str):
                            items.append(BulletItem(text=item_data, level=0, runs=[]))
                        elif isinstance(item_data, dict):
                            runs = []
                            for run_data in item_data.get("runs", []):
                                runs.append(
                                    TextRun(
                                        text=run_data.get("text", ""),
                                        bold=run_data.get("bold", False),
                                        italic=run_data.get("italic", False),
                                    )
                                )
                            items.append(
                                BulletItem(
                                    text=item_data.get("text", ""),
                                    level=item_data.get("level", 0),
                                    runs=runs,
                                )
                            )
                else:  # paragraphs
                    items = [str(item) for item in items_data]

                structure = TextStructure(type=structure_type, items=items)

                # Parse style hints
                style_data = elem_dict.get("style_hints", {})
                style_hints = StyleHints(
                    align=style_data.get("align", "left"),
                    weight=style_data.get("weight", "regular"),
                    size=style_data.get("size", "md"),
                    vertical_align=style_data.get("vertical_align", "top"),
                )

                # Parse provenance
                prov_data = elem_dict.get("provenance", {})
                provenance = ElementProvenance(
                    block_ids=prov_data.get("block_ids", []),
                    engines=prov_data.get("engines", []),
                    min_confidence=prov_data.get("min_confidence", 1.0),
                )

                return TextBoxElement(
                    bbox=bbox,
                    role=elem_dict.get("role", "body"),
                    structure=structure,
                    style_hints=style_hints,
                    provenance=provenance,
                )

            elif kind == "image":
                prov_data = elem_dict.get("provenance", {})
                provenance = ElementProvenance(
                    block_ids=prov_data.get("block_ids", []),
                    engines=prov_data.get("engines", []),
                    min_confidence=prov_data.get("min_confidence", 1.0),
                )

                return ImageElement(
                    bbox=bbox,
                    image_ref=elem_dict["image_ref"],
                    crop_mode=elem_dict.get("crop_mode", "fit"),
                    provenance=provenance,
                )

            elif kind == "shape":
                prov_data = elem_dict.get("provenance", {})
                provenance = ElementProvenance(
                    block_ids=prov_data.get("block_ids", []),
                    engines=prov_data.get("engines", []),
                    min_confidence=prov_data.get("min_confidence", 1.0),
                )

                return ShapeElement(
                    bbox=bbox,
                    shape_type=elem_dict.get("shape_type", "rectangle"),
                    fill_color=elem_dict.get("fill_color"),
                    border_color=elem_dict.get("border_color"),
                    border_width=elem_dict.get("border_width", 1.0),
                    provenance=provenance,
                )

        except (KeyError, ValueError) as e:
            print(f"[LLM] Warning: Failed to parse element: {e}")
            return None

        return None
