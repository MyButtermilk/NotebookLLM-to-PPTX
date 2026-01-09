"""
Test script to verify PP-StructureV3 import and initialization.
"""
import sys

print("Testing PaddleOCR 3.x imports...")

try:
    from paddleocr import PPStructureV3
    print("✓ Successfully imported PPStructureV3")
except ImportError as e:
    print(f"✗ Failed to import PPStructureV3: {e}")
    print("\nMake sure you have installed PaddleOCR 3.x:")
    print("  pip install 'paddleocr[all]>=3.0.0' 'paddlepaddle>=3.0.0'")
    sys.exit(1)

print("\nInitializing PPStructureV3 (this may take a moment to download models)...")
try:
    pipeline = PPStructureV3(
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        use_formula_recognition=False,
        device="cpu",
    )
    print("✓ PPStructureV3 initialized successfully!")
    print("\nThe extractor is ready to use.")
except Exception as e:
    print(f"✗ Failed to initialize PPStructureV3: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
