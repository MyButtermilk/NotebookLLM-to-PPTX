"""
Command-line interface for SlideRefactor.
"""

import sys
import argparse
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from sliderefactor import __version__
from sliderefactor.pipeline import SlideRefactorPipeline


def main() -> int:
    """Main CLI entry point."""
    load_dotenv()  # Load .env file if present

    parser = argparse.ArgumentParser(
        description="SlideRefactor: Convert NotebookLLM flattened slide PDFs into editable PPTX",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with Datalab
  sliderefactor input.pdf

  # Use PaddleOCR instead of Datalab
  sliderefactor input.pdf --extractor paddleocr

  # Enable preprocessing and disable audit HTML
  sliderefactor input.pdf --preprocess --no-audit

  # Process from saved SlideGraph JSON
  sliderefactor --from-slidegraph output/deck.slidegraph.json

  # Specify custom output directory
  sliderefactor input.pdf --output ./my_output

Environment Variables:
  DATALAB_API_KEY     API key for Datalab extraction
  ANTHROPIC_API_KEY   API key for Claude LLM processing
  OUTPUT_DIR          Default output directory
        """,
    )

    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        help="Input PDF file or SlideGraph JSON (with --from-slidegraph)",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"SlideRefactor {__version__}",
    )

    parser.add_argument(
        "--extractor",
        choices=["datalab", "paddleocr"],
        default="datalab",
        help="Extraction engine (default: datalab)",
    )

    parser.add_argument(
        "--preprocess",
        action="store_true",
        help="Apply OpenCV preprocessing (deskew, denoise, sharpen)",
    )

    parser.add_argument(
        "--no-audit",
        action="store_true",
        help="Skip audit HTML generation",
    )

    parser.add_argument(
        "--no-intermediate",
        action="store_true",
        help="Don't save intermediate SlideGraph JSON",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output directory (default: ./output/<pdf_name>)",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode (save prompts and responses)",
    )

    parser.add_argument(
        "--from-slidegraph",
        action="store_true",
        help="Process from saved SlideGraph JSON instead of PDF",
    )

    parser.add_argument(
        "--no-background",
        action="store_true",
        help="Disable background image rendering (avoids 'double text' issue)",
    )

    args = parser.parse_args()

    # Validate input
    if not args.input:
        parser.print_help()
        return 1

    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        return 1

    try:
        if args.from_slidegraph:
            # Process from SlideGraph JSON
            result = SlideRefactorPipeline.from_slidegraph(
                slidegraph_path=args.input,
                output_dir=args.output,
                generate_audit=not args.no_audit,
                render_background=not args.no_background,
            )
        else:
            # Full pipeline from PDF
            pipeline = SlideRefactorPipeline(
                extractor=args.extractor,
                use_preprocessing=args.preprocess,
                generate_audit=not args.no_audit,
                save_intermediate=not args.no_intermediate,
                debug=args.debug,
                render_background=not args.no_background,
            )

            result = pipeline.process(
                pdf_path=args.input,
                output_dir=args.output,
            )

        return 0

    except KeyboardInterrupt:
        print("\n\nInterrupted by user", file=sys.stderr)
        return 130

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
