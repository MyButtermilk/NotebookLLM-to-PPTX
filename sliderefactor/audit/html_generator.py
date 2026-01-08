"""
Generate audit HTML reports for QA.

Overlays detected blocks and generated elements on slide images
for visual verification of extraction quality.
"""

import base64
from pathlib import Path
from typing import List, Optional
from jinja2 import Template

from sliderefactor.models import Slide, SlideElements, Block, Element, TextBoxElement


class AuditHTMLGenerator:
    """
    Generate interactive HTML audit reports.

    Features:
    - Side-by-side view of original PDF pages and detected blocks
    - Bounding box overlays for blocks and elements
    - Confidence scores and provenance information
    - Toggle layers for different extraction engines
    """

    HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SlideRefactor Audit Report</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }

        .header {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .header h1 {
            color: #333;
            margin-bottom: 10px;
        }

        .header .meta {
            color: #666;
            font-size: 14px;
        }

        .controls {
            background: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .controls label {
            margin-right: 20px;
            cursor: pointer;
        }

        .controls input[type="checkbox"] {
            margin-right: 5px;
        }

        .slide-container {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .slide-header {
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #eee;
        }

        .slide-header h2 {
            color: #333;
        }

        .slide-stats {
            color: #666;
            font-size: 14px;
            margin-top: 5px;
        }

        .slide-view {
            position: relative;
            display: inline-block;
            margin: 10px 0;
        }

        .slide-image {
            max-width: 100%;
            border: 1px solid #ddd;
            display: block;
        }

        .overlay-canvas {
            position: absolute;
            top: 0;
            left: 0;
            pointer-events: none;
        }

        .block-info {
            margin-top: 20px;
            font-size: 13px;
        }

        .block-item {
            padding: 10px;
            margin: 5px 0;
            background: #f9f9f9;
            border-left: 3px solid #4CAF50;
            border-radius: 3px;
        }

        .block-item.image {
            border-left-color: #2196F3;
        }

        .block-item.table {
            border-left-color: #FF9800;
        }

        .block-text {
            margin: 5px 0;
            font-family: monospace;
            background: white;
            padding: 5px;
            border-radius: 3px;
        }

        .confidence {
            display: inline-block;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 11px;
            font-weight: bold;
        }

        .confidence.high {
            background: #4CAF50;
            color: white;
        }

        .confidence.medium {
            background: #FF9800;
            color: white;
        }

        .confidence.low {
            background: #f44336;
            color: white;
        }

        .element-info {
            margin-top: 20px;
            padding-top: 20px;
            border-top: 2px solid #eee;
        }

        .element-item {
            padding: 10px;
            margin: 5px 0;
            background: #f0f8ff;
            border-left: 3px solid #9C27B0;
            border-radius: 3px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 SlideRefactor Audit Report</h1>
        <div class="meta">
            <strong>Source:</strong> {{ meta.source }} |
            <strong>Pages:</strong> {{ meta.total_pages }} |
            <strong>DPI:</strong> {{ meta.dpi }} |
            <strong>Engines:</strong> {{ meta.extraction_engines|join(', ') }} |
            <strong>Created:</strong> {{ meta.created_at }}
        </div>
    </div>

    <div class="controls">
        <label>
            <input type="checkbox" id="toggle-blocks" checked onchange="toggleLayer('blocks')">
            Show Blocks (OCR)
        </label>
        <label>
            <input type="checkbox" id="toggle-elements" checked onchange="toggleLayer('elements')">
            Show Elements (PPTX)
        </label>
        <label>
            <input type="checkbox" id="toggle-text" checked onchange="toggleInfo('text')">
            Show Text Details
        </label>
    </div>

    {% for slide_data in slides %}
    <div class="slide-container">
        <div class="slide-header">
            <h2>Slide {{ slide_data.slide.page_index + 1 }}</h2>
            <div class="slide-stats">
                Dimensions: {{ slide_data.slide.width_px|int }}×{{ slide_data.slide.height_px|int }}px |
                Blocks: {{ slide_data.slide.blocks|length }} |
                Elements: {{ slide_data.elements.elements|length if slide_data.elements else 0 }}
            </div>
        </div>

        <div class="slide-view">
            <img src="data:image/png;base64,{{ slide_data.image_b64 }}"
                 class="slide-image"
                 id="slide-{{ slide_data.slide.page_index }}"
                 width="{{ slide_data.slide.width_px|int }}">
            <canvas class="overlay-canvas blocks-layer"
                    id="blocks-canvas-{{ slide_data.slide.page_index }}"
                    width="{{ slide_data.slide.width_px|int }}"
                    height="{{ slide_data.slide.height_px|int }}"></canvas>
            <canvas class="overlay-canvas elements-layer"
                    id="elements-canvas-{{ slide_data.slide.page_index }}"
                    width="{{ slide_data.slide.width_px|int }}"
                    height="{{ slide_data.slide.height_px|int }}"></canvas>
        </div>

        <div class="block-info info-section" id="text-info-{{ slide_data.slide.page_index }}">
            <h3>Detected Blocks (OCR)</h3>
            {% for block in slide_data.slide.blocks %}
            <div class="block-item {{ block.type }}">
                <strong>{{ block.id }}</strong> |
                Type: <code>{{ block.type }}</code> |
                Confidence: <span class="confidence {{ 'high' if block.confidence >= 0.9 else 'medium' if block.confidence >= 0.7 else 'low' }}">
                    {{ (block.confidence * 100)|round(1) }}%
                </span> |
                Engine: {{ block.provenance[0].engine if block.provenance else 'unknown' }}
                {% if block.text %}
                <div class="block-text">{{ block.text }}</div>
                {% endif %}
            </div>
            {% endfor %}
        </div>

        {% if slide_data.elements %}
        <div class="element-info info-section" id="element-info-{{ slide_data.slide.page_index }}">
            <h3>Generated Elements (PPTX)</h3>
            {% for element in slide_data.elements.elements %}
            <div class="element-item">
                <strong>{{ element.kind }}</strong> |
                {% if element.kind == 'textbox' %}
                Role: <code>{{ element.role }}</code> |
                Structure: {{ element.structure.type }} ({{ element.structure.items|length }} items)
                {% elif element.kind == 'image' %}
                Image: {{ element.image_ref }}
                {% elif element.kind == 'shape' %}
                Shape: {{ element.shape_type }}
                {% endif %}
            </div>
            {% endfor %}
        </div>
        {% endif %}
    </div>

    <script>
        // Draw blocks
        {% for slide_data in slides %}
        (function() {
            const canvas = document.getElementById('blocks-canvas-{{ slide_data.slide.page_index }}');
            const ctx = canvas.getContext('2d');

            {% for block in slide_data.slide.blocks %}
            ctx.strokeStyle = '{{ "#4CAF50" if block.type == "text" else "#2196F3" if block.type == "image" else "#FF9800" }}';
            ctx.lineWidth = 2;
            ctx.strokeRect(
                {{ block.bbox.x0 }},
                {{ block.bbox.y0 }},
                {{ block.bbox.width }},
                {{ block.bbox.height }}
            );

            ctx.fillStyle = 'rgba(76, 175, 80, 0.1)';
            ctx.fillRect(
                {{ block.bbox.x0 }},
                {{ block.bbox.y0 }},
                {{ block.bbox.width }},
                {{ block.bbox.height }}
            );

            ctx.font = '12px sans-serif';
            ctx.fillStyle = '#000';
            ctx.fillText('{{ block.id }}', {{ block.bbox.x0 + 5 }}, {{ block.bbox.y0 + 15 }});
            {% endfor %}
        })();

        {% if slide_data.elements %}
        (function() {
            const canvas = document.getElementById('elements-canvas-{{ slide_data.slide.page_index }}');
            const ctx = canvas.getContext('2d');

            {% for element in slide_data.elements.elements %}
            ctx.strokeStyle = '#9C27B0';
            ctx.lineWidth = 3;
            ctx.setLineDash([5, 5]);
            ctx.strokeRect(
                {{ element.bbox.x0 }},
                {{ element.bbox.y0 }},
                {{ element.bbox.width }},
                {{ element.bbox.height }}
            );
            ctx.setLineDash([]);
            {% endfor %}
        })();
        {% endif %}
        {% endfor %}

        // Toggle functions
        function toggleLayer(layerName) {
            const elements = document.querySelectorAll('.' + layerName + '-layer');
            const checkbox = document.getElementById('toggle-' + layerName);
            elements.forEach(el => {
                el.style.display = checkbox.checked ? 'block' : 'none';
            });
        }

        function toggleInfo(infoName) {
            const elements = document.querySelectorAll('.info-section');
            const checkbox = document.getElementById('toggle-' + infoName);
            elements.forEach(el => {
                el.style.display = checkbox.checked ? 'block' : 'none';
            });
        }
    </script>
    {% endfor %}
</body>
</html>
"""

    def generate(
        self,
        slides: List[Slide],
        elements_list: List[SlideElements],
        images_dir: Path,
        output_path: Path,
        meta: dict,
    ) -> Path:
        """
        Generate audit HTML report.

        Args:
            slides: List of Slide objects with blocks
            elements_list: List of SlideElements (PPTX elements)
            images_dir: Directory containing slide images
            output_path: Path to save HTML file
            meta: Metadata dictionary

        Returns:
            Path to generated HTML file
        """
        print(f"[Audit] Generating HTML report for {len(slides)} slides")

        template = Template(self.HTML_TEMPLATE)

        slides_data = []
        for i, slide in enumerate(slides):
            # Load slide image
            image_path = images_dir / f"page_{slide.page_index}.png"
            if not image_path.exists():
                # Try alternative naming
                image_path = images_dir / f"slide{slide.page_index}_full.png"

            image_b64 = ""
            if image_path.exists():
                with open(image_path, "rb") as f:
                    image_b64 = base64.b64encode(f.read()).decode("utf-8")

            # Find corresponding elements
            elements = None
            for elem in elements_list:
                if elem.slide_index == slide.page_index:
                    elements = elem
                    break

            slides_data.append(
                {
                    "slide": slide,
                    "elements": elements,
                    "image_b64": image_b64,
                }
            )

        html_content = template.render(
            meta=meta,
            slides=slides_data,
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"[Audit] Saved HTML report to {output_path}")
        return output_path
