"""
Advanced usage examples for SlideRefactor.

Shows how to:
- Use PaddleOCR fallback
- Apply preprocessing
- Resume from SlideGraph JSON
- Customize components
"""

from pathlib import Path
from sliderefactor import SlideRefactorPipeline
from sliderefactor.extractors.paddleocr_extractor import PaddleOCRExtractor
from sliderefactor.preprocessors import OpenCVPreprocessor


def example_with_paddleocr():
    """Use PaddleOCR instead of Datalab (no API key required)."""
    print("\n[Example 1] Using PaddleOCR fallback")

    pipeline = SlideRefactorPipeline(
        extractor="paddleocr",  # Open-source OCR
        use_preprocessing=True,  # Apply OpenCV preprocessing
        generate_audit=True,
        save_intermediate=True,
    )

    result = pipeline.process(
        pdf_path=Path("examples/sample_deck.pdf"),
        output_dir=Path("output/sample_deck_paddleocr"),
    )

    print(f"✓ PPTX: {result['pptx']}")


def example_with_preprocessing():
    """Apply OpenCV preprocessing for better OCR quality."""
    print("\n[Example 2] With preprocessing")

    # Customize preprocessing
    preprocessor = OpenCVPreprocessor(
        deskew=True,  # Correct rotation
        denoise=True,  # Remove artifacts
        sharpen=True,  # Enhance text edges
        normalize_contrast=True,  # Improve visibility
        detect_margins=True,  # Crop to content
    )

    pipeline = SlideRefactorPipeline(
        extractor="datalab",
        use_preprocessing=True,
        generate_audit=True,
    )

    result = pipeline.process(
        pdf_path=Path("examples/scanned_deck.pdf"),
        output_dir=Path("output/scanned_deck"),
    )

    print(f"✓ PPTX: {result['pptx']}")


def example_resume_from_slidegraph():
    """Resume processing from a saved SlideGraph JSON."""
    print("\n[Example 3] Resume from SlideGraph")

    # This is useful for re-processing with different settings
    # without re-running expensive OCR
    result = SlideRefactorPipeline.from_slidegraph(
        slidegraph_path=Path("output/sample_deck/sample_deck.slidegraph.json"),
        output_dir=Path("output/sample_deck_reprocessed"),
        generate_audit=True,
    )

    print(f"✓ PPTX: {result['pptx']}")


def example_batch_processing():
    """Process multiple PDFs in batch."""
    print("\n[Example 4] Batch processing")

    pipeline = SlideRefactorPipeline(
        extractor="datalab",
        generate_audit=True,
        save_intermediate=True,
    )

    pdf_files = Path("examples").glob("*.pdf")

    for pdf_path in pdf_files:
        print(f"\nProcessing: {pdf_path.name}")
        try:
            result = pipeline.process(
                pdf_path=pdf_path,
                output_dir=Path("output") / pdf_path.stem,
            )
            print(f"  ✓ {result['pptx']}")
        except Exception as e:
            print(f"  ✗ Error: {e}")


if __name__ == "__main__":
    # Run examples
    # example_with_paddleocr()
    # example_with_preprocessing()
    # example_resume_from_slidegraph()
    # example_batch_processing()

    print("\nUncomment the example you want to run in advanced_usage.py")
