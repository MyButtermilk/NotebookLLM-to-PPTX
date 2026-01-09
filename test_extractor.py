"""
Test the PaddleOCR extractor directly.
"""
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from sliderefactor.extractors.paddleocr_extractor import PaddleOCRExtractor

# Find a test PDF
import os
test_pdf_dir = "server/uploads"
pdf_files = [f for f in os.listdir(test_pdf_dir) if f.endswith('.pdf')]
if not pdf_files:
    print("No PDF files found in server/uploads")
    sys.exit(1)

pdf_path = Path(test_pdf_dir) / pdf_files[0]
output_dir = Path("test_output/paddleocr_test")
output_dir.mkdir(parents=True, exist_ok=True)

print(f"Testing with PDF: {pdf_path}")
print(f"Output dir: {output_dir}")

# Initialize extractor
print("\nInitializing PaddleOCRExtractor...")
extractor = PaddleOCRExtractor(lang="en", use_gpu=False)

# Extract
print("\nExtracting...")
slide_graph = extractor.extract(pdf_path, output_dir)

# Print results
print("\n" + "="*60)
print("EXTRACTION RESULTS")
print("="*60)
print(f"Total slides: {len(slide_graph.slides)}")

for slide in slide_graph.slides:
    print(f"\n--- Slide {slide.page_index} ---")
    print(f"Dimensions: {slide.width_px} x {slide.height_px}")
    print(f"Blocks: {len(slide.blocks)}")
    
    text_blocks = [b for b in slide.blocks if b.type == "text"]
    image_blocks = [b for b in slide.blocks if b.type == "image"]
    
    print(f"  Text blocks: {len(text_blocks)}")
    print(f"  Image blocks: {len(image_blocks)}")
    
    # Show first few text blocks
    for i, block in enumerate(text_blocks[:3]):
        text_preview = block.text[:80] + "..." if block.text and len(block.text) > 80 else block.text
        print(f"  [{i}] {block.metadata.get('original_label', 'text')}: {text_preview}")

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)
