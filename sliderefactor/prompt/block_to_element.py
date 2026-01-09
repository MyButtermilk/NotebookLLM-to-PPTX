"""
LLM-powered block-to-element conversion.

Uses Google Gemini to intelligently convert OCR blocks into structured PPTX elements.
"""

import os
import json
from typing import List, Optional, Dict, Any
from pathlib import Path

from google import genai
from google.genai import types

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
    FontHints,
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
    - Classify roles (title/body/caption)
    - Preserve layout fidelity
    """

    SYSTEM_PROMPT = """You convert flattened slide OCR blocks into an editable PowerPoint plan.

Priorities:
1) Do not invent text or numbers. Use OCR output verbatim.
2) Maximize editability: text must become textboxes, not images.
3) Preserve layout: grouping, columns, bullets, titles.
4) MANDATORY: Include ALL blocks of type 'image' or 'Picture' as image elements. Do not skip icons or logos.
5) Use font metadata hints when available.

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
      "font_hints": {{
        "name": "Font name if available",
        "size": 18
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
- When block metadata provides font_name or font_size, include font_hints for the textbox.
- CRITICAL: You MUST include every block with type="image" as a "kind": "image" element. Do not filter them out.

Output ONLY the JSON object. Do not include markdown formatting, code blocks, or explanatory text."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.0-flash",
        max_tokens: int = 16384,
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Google API key required. Set GEMINI_API_KEY or GOOGLE_API_KEY env var or pass api_key parameter."
            )

        self.client = genai.Client(api_key=self.api_key)
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
                if block.metadata.get("font_name"):
                    block_dict["font_name"] = block.metadata["font_name"]
                if block.metadata.get("font_size"):
                    block_dict["font_size"] = block.metadata["font_size"]
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
        print(f"[LLM] User Prompt Length: {len(user_prompt)}")

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=self.SYSTEM_PROMPT,
                    max_output_tokens=self.max_tokens,
                    temperature=0.1,
                ),
            )
            response_text = response.text
        except Exception as e:
            print(f"[LLM] Gemini API Error: {e}")
            if hasattr(e, 'details'):
                print(f"[LLM] Error Details: {e.details}")
            # Reraise or return empty
            raise e

        if debug:
            with open(debug_dir / f"response_slide_{slide.page_index}.txt", "w") as f:
                f.write(response_text)

        # Parse response
        elements = []
        llm_success = False

        try:
            # Clean response (remove markdown code blocks if present)
            response_text = response_text.strip()

            # Use regex to find the JSON object (first { to last })
            import re
            match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if match:
                response_text = match.group(0)
            else:
                 # Fallback to simple stripping if regex fails (unlikely for valid JSON)
                if response_text.startswith("```json"):
                    response_text = response_text[7:]
                if response_text.startswith("```"):
                    response_text = response_text[3:]
                if response_text.endswith("```"):
                    response_text = response_text[:-3]
                response_text = response_text.strip()

            elements_data = json.loads(response_text)

            # Convert to Pydantic models
            for elem_dict in elements_data.get("elements", []):
                element = self._parse_element(elem_dict)
                if element:
                    elements.append(element)

            block_lookup = {block.id: block for block in slide.blocks}
            for element in elements:
                if isinstance(element, TextBoxElement) and element.font_hints is None:
                    font_name, font_size = self._infer_font_hints(
                        element, block_lookup
                    )
                    if font_name or font_size:
                        element.font_hints = FontHints(name=font_name, size=font_size)

            print(f"[LLM] Generated {len(elements)} elements for slide {slide.page_index}")
            llm_success = True

        except json.JSONDecodeError as e:
            print(f"[LLM] Error parsing JSON response: {e}")
            print(f"[LLM] Response: {response_text[:500]}")
            print(f"[LLM] Using fallback: direct block conversion")
            # Fallback: convert blocks directly without LLM
            elements = self._fallback_convert_blocks(slide)

        # ALWAYS run recovery: Force-include images that may have been skipped
        # This runs whether LLM succeeded or fallback was used
        for block in slide.blocks:
            if block.type == "image":
                # Check if this block is already represented in the elements
                is_covered = False
                for elem in elements:
                    # Check provenance
                    if hasattr(elem, 'provenance') and block.id in elem.provenance.block_ids:
                        is_covered = True
                        break
                    # Check bbox overlap (approximate)
                    if isinstance(elem, ImageElement):
                        # If centers are close
                        c1 = [(elem.bbox.coords[0] + elem.bbox.coords[2])/2, (elem.bbox.coords[1] + elem.bbox.coords[3])/2]
                        c2 = [(block.bbox.coords[0] + block.bbox.coords[2])/2, (block.bbox.coords[1] + block.bbox.coords[3])/2]
                        dist = ((c1[0]-c2[0])**2 + (c1[1]-c2[1])**2)**0.5
                        if dist < 50:  # within 50 pixels
                            is_covered = True
                            break

                if not is_covered:
                    print(f"[LLM] Recovering skipped image block: {block.id}")
                    # Use the image_ref from the block (should be set during extraction/enrichment)
                    ref = block.image_ref or f"recovered_{block.id.replace('/', '_')}.png"

                    new_elem = ImageElement(
                        bbox=block.bbox,
                        image_ref=ref,
                        crop_mode="fit",
                        provenance=ElementProvenance(
                            block_ids=[block.id],
                            engines=["recovery"],
                            min_confidence=block.confidence
                        )
                    )
                    elements.append(new_elem)

        print(f"[LLM] Final element count for slide {slide.page_index}: {len(elements)}")
        return SlideElements(slide_index=slide.page_index, elements=elements)

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
                                        font_size=run_data.get("font_size"),
                                        font_name=run_data.get("font_name"),
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
                    font_hints=elem_dict.get("font_hints"),
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

    @staticmethod
    def _infer_font_hints(
        element: TextBoxElement, block_lookup: Dict[str, Block]
    ) -> tuple:
        font_names = []
        font_sizes = []
        for block_id in element.provenance.block_ids:
            block = block_lookup.get(block_id)
            if not block:
                continue
            font_name = block.metadata.get("font_name")
            font_size = block.metadata.get("font_size")
            if font_name:
                font_names.append(font_name)
            if font_size:
                font_sizes.append(int(round(font_size)))

        dominant_name = None
        dominant_size = None
        if font_names:
            dominant_name = max(set(font_names), key=font_names.count)
        if font_sizes:
            dominant_size = max(set(font_sizes), key=font_sizes.count)

        return dominant_name, dominant_size

    def _fallback_convert_blocks(self, slide: Slide) -> List[Any]:
        """
        Direct block-to-element conversion when LLM fails.

        This is a simple fallback that converts each block directly
        without intelligent merging or layout analysis.
        """
        elements = []

        for block in slide.blocks:
            if block.type == "text":
                # Create a simple textbox for each text block
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

                # Get font info from metadata
                font_hints = None
                if block.metadata.get("font_name") or block.metadata.get("font_size"):
                    font_hints = FontHints(
                        name=block.metadata.get("font_name"),
                        size=int(round(block.metadata.get("font_size", 12)))
                    )

                element = TextBoxElement(
                    bbox=block.bbox,
                    role=role,
                    structure=structure,
                    style_hints=StyleHints(
                        align="left",
                        weight="regular",
                        size="md",
                        vertical_align="top"
                    ),
                    font_hints=font_hints,
                    provenance=ElementProvenance(
                        block_ids=[block.id],
                        engines=["fallback"],
                        min_confidence=block.confidence
                    )
                )
                elements.append(element)

            elif block.type == "image":
                # Create image element
                ref = block.image_ref or f"fallback_{block.id.replace('/', '_')}.png"
                element = ImageElement(
                    bbox=block.bbox,
                    image_ref=ref,
                    crop_mode="fit",
                    provenance=ElementProvenance(
                        block_ids=[block.id],
                        engines=["fallback"],
                        min_confidence=block.confidence
                    )
                )
                elements.append(element)

        print(f"[LLM] Fallback created {len(elements)} elements from {len(slide.blocks)} blocks")
        return elements
