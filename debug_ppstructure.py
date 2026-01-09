"""
Debug script to fully explore PP-StructureV3 output structure.
"""
import sys
import json

print("Importing PPStructureV3...")
from paddleocr import PPStructureV3

print("Initializing PPStructureV3...")
pipeline = PPStructureV3(
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
    use_formula_recognition=False,
    use_chart_recognition=False,
    device="cpu",
)

# Find a test PDF
import os
test_pdf = "server/uploads"
pdf_files = [f for f in os.listdir(test_pdf) if f.endswith('.pdf')]
if not pdf_files:
    print("No PDF files found in server/uploads")
    sys.exit(1)

pdf_path = os.path.join(test_pdf, pdf_files[0])
print(f"Using PDF: {pdf_path}")

# Run PP-StructureV3 on the PDF
print("Running PP-StructureV3 analysis...")
output = pipeline.predict(input=pdf_path)

# Convert to list
results = list(output)
print(f"Got {len(results)} pages")

# Analyze first page
if results:
    res = results[0]
    print("\n" + "="*60)
    print("RESULT TYPE:", type(res))
    print("="*60)
    
    # List all public attributes
    attrs = [x for x in dir(res) if not x.startswith('_')]
    print(f"\nPublic attributes: {attrs}")
    
    # Try .json
    try:
        result_dict = res.json
        print(f"\n.json type: {type(result_dict)}")
        print(f".json keys: {list(result_dict.keys())}")
        
        # Check 'res' key
        if 'res' in result_dict:
            res_value = result_dict['res']
            print(f"\n.json['res'] type: {type(res_value)}")
            if isinstance(res_value, dict):
                print(f".json['res'] keys: {list(res_value.keys())}")
                
                # Check for parsing_res_list inside res
                if 'parsing_res_list' in res_value:
                    prl = res_value['parsing_res_list']
                    print(f"\nparsing_res_list has {len(prl)} blocks")
                    if prl:
                        print("\n--- First block ---")
                        block = prl[0]
                        if isinstance(block, dict):
                            for k, v in block.items():
                                if isinstance(v, str) and len(v) > 100:
                                    print(f"  {k}: {v[:100]}...")
                                else:
                                    print(f"  {k}: {v}")
            elif isinstance(res_value, list):
                print(f".json['res'] is a list with {len(res_value)} items")
                if res_value:
                    print(f"First item type: {type(res_value[0])}")
                    first = res_value[0]
                    if isinstance(first, dict):
                        print(f"First item keys: {list(first.keys())}")
    except Exception as e:
        print(f"Error accessing .json: {e}")
    
    # Try other attributes
    for attr in ['parsing_res_list', 'overall_ocr_res', 'layout_det_res', 'markdown']:
        if hasattr(res, attr):
            val = getattr(res, attr)
            if val is not None:
                print(f"\n.{attr} exists, type: {type(val)}")
                if isinstance(val, dict) and val:
                    print(f"  Keys: {list(val.keys())[:10]}")
                elif isinstance(val, list):
                    print(f"  Length: {len(val)}")

print("\n" + "="*60)
print("DEBUG COMPLETE")
print("="*60)
