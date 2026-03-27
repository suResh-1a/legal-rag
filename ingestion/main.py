import os
import sys
# Allow running as a script from the root directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
from ingestion.pdf_processor import convert_pdf_to_images
from ingestion.gemini_extractor import GeminiExtractor
from ingestion.stitcher import stitch_sections
from typing import List, Dict

def run_ingestion(pdf_path: str, output_json: str):
    """
    Runs the full ingestion pipeline.
    """
    # 1. Convert PDF to images
    temp_folder = "uploads/temp_images"
    image_paths = convert_pdf_to_images(pdf_path, temp_folder)
    
    # 2. Extract data from each image
    extractor = GeminiExtractor()
    all_pages_raw_data = []
    
    for i, path in enumerate(image_paths):
        print(f"Processing Page {i+1}...")
        page_data = extractor.extract_legal_data(path, i+1)
        all_pages_raw_data.append(page_data)
        
    # 3. Stitch sections across pages
    stitched_data = stitch_sections(all_pages_raw_data)
    
    # 4. Save results
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(stitched_data, f, ensure_ascii=False, indent=2)
        
    print(f"Ingestion complete! Results saved to {output_json}")
    return stitched_data

if __name__ == "__main__":
    PDF_PATH = "/home/suresh/Desktop/trash/legal-rag/pdf_data_extraction/seed_act_nepal.pdf"
    OUTPUT_FILE = "data/raw_extracted_legal_data.json"
    
    if not os.path.exists("data"):
        os.makedirs("data")
        
    if os.path.exists(PDF_PATH):
        run_ingestion(PDF_PATH, OUTPUT_FILE)
    else:
        print(f"Error: PDF not found at {PDF_PATH}")
