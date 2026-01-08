# SlideRefactor 📊

> **Prompt-driven pipeline to convert NotebookLLM flattened slide PDFs into editable PPTX**

Transform NotebookLLM slide exports into fully editable PowerPoint presentations with SOTA accuracy. SlideRefactor combines commercial-grade extraction (Datalab), AI-powered layout reconstruction (Claude), and deterministic PPTX rendering (python-pptx).

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 Features

- **SOTA Extraction**: Datalab Convert API (Marker backend) with precise bounding boxes
- **AI Layout Recovery**: Claude-powered intelligent block merging and structure inference
- **Fallback OCR**: PaddleOCR for open-source/privacy-sensitive workflows
- **Preprocessing**: OpenCV utilities for deskew, denoise, and sharpening
- **Full Editability**: Text becomes real text boxes, not images
- **Audit Trail**: Interactive HTML reports for QA and debugging
- **Canonical Format**: SlideGraph JSON intermediate representation

## 📦 Installation

### Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/NotebookLLM-to-PPTX.git
cd NotebookLLM-to-PPTX

# Install dependencies
pip install -r requirements.txt

# Or use Poetry
poetry install
```

### With PaddleOCR (Optional)

```bash
# Install OCR fallback support
pip install paddleocr paddlepaddle
```

### API Keys

SlideRefactor requires two API keys:

1. **Datalab API** - For SOTA extraction ([get key](https://datalab.to))
2. **Anthropic API** - For Claude LLM processing ([get key](https://console.anthropic.com))

Create a `.env` file:

```bash
cp .env.example .env
# Edit .env and add your keys
```

Or export them:

```bash
export DATALAB_API_KEY="your_datalab_key"
export ANTHROPIC_API_KEY="your_anthropic_key"
```

## 🚀 Usage

### Command Line

```bash
# Basic usage
sliderefactor input.pdf

# Use PaddleOCR instead of Datalab
sliderefactor input.pdf --extractor paddleocr

# Enable preprocessing
sliderefactor input.pdf --preprocess

# Custom output directory
sliderefactor input.pdf --output ./my_output

# Resume from SlideGraph JSON
sliderefactor --from-slidegraph output/deck.slidegraph.json
```

### Python API

```python
from pathlib import Path
from sliderefactor import SlideRefactorPipeline

# Initialize pipeline
pipeline = SlideRefactorPipeline(
    extractor="datalab",        # or "paddleocr"
    use_preprocessing=False,    # OpenCV preprocessing
    generate_audit=True,        # HTML audit report
    save_intermediate=True,     # Save SlideGraph JSON
    debug=False                 # Debug mode
)

# Process PDF
result = pipeline.process(
    pdf_path=Path("input.pdf"),
    output_dir=Path("output/my_deck")
)

print(f"PPTX: {result['pptx']}")
print(f"SlideGraph: {result['slidegraph']}")
print(f"Audit: {result['audit']}")
```

## 📊 Architecture

```
┌──────────────┐
│   PDF Input  │
└──────┬───────┘
       │
       v
┌──────────────────────┐
│  1. Preprocessing    │  OpenCV (optional)
│  - Deskew            │
│  - Denoise           │
│  - Sharpen           │
└──────┬───────────────┘
       │
       v
┌──────────────────────┐
│  2. Extraction       │  Datalab API (primary)
│  - Layout detection  │  or PaddleOCR (fallback)
│  - OCR with bboxes   │
│  - Image extraction  │
└──────┬───────────────┘
       │
       v
┌──────────────────────┐
│  SlideGraph JSON     │  Canonical intermediate format
│  (Auditable)         │
└──────┬───────────────┘
       │
       v
┌──────────────────────┐
│  3. LLM Processing   │  Claude (Anthropic)
│  - Block merging     │
│  - Bullet inference  │
│  - Role detection    │
│  - Layout recovery   │
└──────┬───────────────┘
       │
       v
┌──────────────────────┐
│  4. PPTX Rendering   │  python-pptx
│  - Text boxes        │
│  - Images            │
│  - Styling           │
└──────┬───────────────┘
       │
       v
┌──────────────────────┐
│  Output Artifacts    │
│  - deck.pptx         │
│  - deck.slidegraph   │
│  - audit.html        │
└──────────────────────┘
```

## 🧩 Components

### 1. Extractors

- **DatalabExtractor** (Primary): Commercial API with SOTA accuracy
- **PaddleOCRExtractor** (Fallback): Open-source OCR for privacy-sensitive workloads

### 2. Preprocessors

- **OpenCVPreprocessor**: Deskew, denoise, sharpen, margin detection

### 3. Prompt System

- **BlockToElementConverter**: Claude-powered intelligent layout reconstruction
- Infers bullets, columns, roles (title/body/caption)
- Preserves reading order and structure

### 4. Renderers

- **PPTXRenderer**: Deterministic python-pptx generation
- Real text boxes (editable, selectable)
- Images with positioning
- Style preservation

### 5. Audit

- **AuditHTMLGenerator**: Interactive QA reports
- Bounding box overlays
- Confidence scores
- Provenance tracking

## 📝 Output Artifacts

### 1. `deck.pptx`

Editable PowerPoint presentation with:
- Text as real text boxes (not images)
- Preserved layout and structure
- Bullet lists with proper nesting
- Images with original positioning

### 2. `deck.slidegraph.json`

Canonical intermediate format:
```json
{
  "meta": {
    "source": "notebooklm_flattened_pdf",
    "dpi": 400,
    "total_pages": 10,
    "extraction_engines": ["datalab"]
  },
  "slides": [
    {
      "page_index": 0,
      "width_px": 1920,
      "height_px": 1080,
      "blocks": [
        {
          "id": "p0_b1",
          "type": "text",
          "bbox": [100, 50, 800, 120],
          "text": "Slide Title",
          "confidence": 0.95,
          "provenance": [{"engine": "datalab"}]
        }
      ]
    }
  ]
}
```

### 3. `audit.html`

Interactive HTML report with:
- Bounding box overlays (blocks and elements)
- Toggle layers (OCR blocks vs PPTX elements)
- Confidence scores
- Text extraction details
- Provenance information

## 🎨 SlideGraph Schema

The canonical intermediate format that all extractors normalize into:

```python
from sliderefactor.models import SlideGraph, Slide, Block

slide_graph = SlideGraph(
    meta=SlideGraphMeta(
        source="notebooklm_flattened_pdf",
        dpi=400,
        total_pages=5
    ),
    slides=[
        Slide(
            page_index=0,
            width_px=1920,
            height_px=1080,
            blocks=[
                Block(
                    id="p0_b1",
                    type="text",
                    bbox=BBox(coords=[x0, y0, x1, y1]),
                    text="Content",
                    confidence=0.95
                )
            ]
        )
    ]
)
```

## 🔧 Advanced Usage

### Resume from SlideGraph

Re-process without re-running expensive OCR:

```python
result = SlideRefactorPipeline.from_slidegraph(
    slidegraph_path=Path("output/deck.slidegraph.json"),
    output_dir=Path("output/reprocessed")
)
```

### Custom Components

```python
from sliderefactor.extractors import DatalabExtractor
from sliderefactor.prompt import BlockToElementConverter
from sliderefactor.renderers import PPTXRenderer

# Custom extractor settings
extractor = DatalabExtractor(api_key="...", dpi=600)

# Custom LLM model
converter = BlockToElementConverter(
    api_key="...",
    model="claude-3-5-sonnet-20241022",
    max_tokens=4096
)

# Custom renderer dimensions
renderer = PPTXRenderer(
    slide_width_inches=10.0,
    slide_height_inches=7.5
)
```

### Batch Processing

```python
from pathlib import Path
from sliderefactor import SlideRefactorPipeline

pipeline = SlideRefactorPipeline()

for pdf_path in Path("input").glob("*.pdf"):
    print(f"Processing: {pdf_path.name}")
    result = pipeline.process(
        pdf_path=pdf_path,
        output_dir=Path("output") / pdf_path.stem
    )
```

## 📊 Success Metrics

Per the PRD, SlideRefactor tracks:

1. **Editability Rate**: % of characters in PPTX text boxes (not images)
2. **Text Accuracy**: Character/word error rate vs ground truth
3. **Layout Fidelity**: IoU overlap of bboxes (detected vs reconstructed)
4. **Human Fix Time**: Median minutes to polish to final deck

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open a Pull Request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Built on top of excellent open-source projects:

- **Datalab**: SOTA document extraction with Marker backend
- **PaddleOCR**: Open-source multilingual OCR
- **python-pptx**: Python library for creating/updating PowerPoint files
- **OpenCV**: Computer vision and image preprocessing
- **Anthropic Claude**: LLM for intelligent layout reconstruction

## 🐛 Troubleshooting

### API Key Errors

```bash
# Ensure API keys are set
echo $DATALAB_API_KEY
echo $ANTHROPIC_API_KEY

# Or use .env file
cp .env.example .env
# Edit .env with your keys
```

### PaddleOCR Installation Issues

```bash
# CPU version
pip install paddlepaddle paddleocr

# GPU version (CUDA)
pip install paddlepaddle-gpu paddleocr
```

### Memory Issues

For large PDFs (>50 pages), process in batches:

```python
# Split PDF first, then process each chunk
pipeline = SlideRefactorPipeline()
result = pipeline.process(pdf_path, output_dir)
```

## 📚 Documentation

- [Examples](examples/README.md) - Code examples
- [API Reference](docs/api.md) - Full API documentation
- [Architecture](docs/architecture.md) - System design details
- [PRD](docs/prd.md) - Original product requirements

## 🚦 Status

- ✅ Core extraction (Datalab + PaddleOCR)
- ✅ LLM prompt system (Claude)
- ✅ PPTX rendering (python-pptx)
- ✅ Audit HTML generation
- ✅ OpenCV preprocessing
- ✅ CLI interface
- ✅ Python API
- 🚧 LayoutParser integration (optional)
- 🚧 DocLayout-YOLO support (optional)
- 🚧 PptxGenJS alternative renderer (JavaScript)

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/NotebookLLM-to-PPTX/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/NotebookLLM-to-PPTX/discussions)
- **Email**: support@example.com

---

**Made with ❤️ by the SlideRefactor Team**
