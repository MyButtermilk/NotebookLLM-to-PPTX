# SlideRefactor Examples

This directory contains example scripts demonstrating how to use SlideRefactor.

## Examples

### Basic Usage

```python
from pathlib import Path
from sliderefactor import SlideRefactorPipeline

# Initialize pipeline
pipeline = SlideRefactorPipeline(extractor="datalab")

# Convert PDF to PPTX
result = pipeline.process(
    pdf_path=Path("input.pdf"),
    output_dir=Path("output/my_deck")
)

print(f"PPTX: {result['pptx']}")
```

### With PaddleOCR (no API key)

```python
pipeline = SlideRefactorPipeline(extractor="paddleocr")
result = pipeline.process(pdf_path=Path("input.pdf"))
```

### Resume from SlideGraph

```python
# Re-process without re-running OCR
result = SlideRefactorPipeline.from_slidegraph(
    slidegraph_path=Path("output/deck.slidegraph.json")
)
```

## Files

- `basic_usage.py` - Simple conversion example
- `advanced_usage.py` - Advanced features (preprocessing, batch, etc.)

## Running Examples

```bash
# Set API keys
export DATALAB_API_KEY="your_key_here"
export ANTHROPIC_API_KEY="your_key_here"

# Run basic example
python examples/basic_usage.py

# Run advanced examples
python examples/advanced_usage.py
```

## Sample PDFs

Place your NotebookLLM PDF exports in this directory to test the examples.
