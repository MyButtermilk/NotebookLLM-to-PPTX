"""
Basic usage example for SlideRefactor.

This example shows how to convert a NotebookLLM PDF to PPTX
using the Python API.
"""

from pathlib import Path
from sliderefactor import SlideRefactorPipeline


def main():
    # Initialize pipeline with default settings (Datalab extractor)
    pipeline = SlideRefactorPipeline(
        extractor="datalab",  # Use Datalab API (requires DATALAB_API_KEY)
        use_preprocessing=False,  # No preprocessing needed for clean PDFs
        generate_audit=True,  # Generate audit HTML for QA
        save_intermediate=True,  # Save SlideGraph JSON
        debug=False,  # Disable debug mode
    )

    # Process the PDF
    pdf_path = Path("examples/sample_deck.pdf")
    output_dir = Path("output/sample_deck")

    result = pipeline.process(pdf_path=pdf_path, output_dir=output_dir)

    print("\n✓ Conversion complete!")
    print(f"  PPTX: {result['pptx']}")
    print(f"  SlideGraph: {result['slidegraph']}")
    print(f"  Audit HTML: {result['audit']}")


if __name__ == "__main__":
    main()
