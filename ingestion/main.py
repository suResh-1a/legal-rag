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
    
    # 2. Extract data from each image or Load from checkpoint
    extractor = GeminiExtractor()
    raw_output = output_json.replace("raw_extracted_legal_data.json", "per_page_raw_data.json")
    
    all_pages_raw_data = []
    processed_pages = set()
    
    if os.path.exists(raw_output):
        try:
            with open(raw_output, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                # Map existing data back to its page structure for stitching
                p_map = {}
                for item in existing_data:
                    p_num = item.get("page_num")
                    if p_num not in p_map: p_map[p_num] = []
                    p_map[p_num].append(item)
                
                # Pre-fill all_pages_raw_data for already processed pages
                for p_num in sorted(p_map.keys()):
                    all_pages_raw_data.append(p_map[p_num])
                    processed_pages.add(p_num)
                print(f"Resuming ingestion from Page {len(processed_pages) + 1}. ({len(processed_pages)} pages loaded from {raw_output})")
        except Exception as e:
            print(f"Warning: Could not load checkpoint from {raw_output}: {e}. Starting fresh.")
    
    import time
    for i, path in enumerate(image_paths):
        page_num = i + 1
        if page_num in processed_pages:
            continue # Skip already processed
            
        print(f"Processing Page {page_num}...")
        try:
            page_data = extractor.extract_legal_data(path, page_num)
            all_pages_raw_data.append(page_data)
            
            # Incremental save to raw_output after each page
            flat_raw_data = [item for sublist in all_pages_raw_data for item in sublist]
            with open(raw_output, "w", encoding="utf-8") as f:
                json.dump(flat_raw_data, f, ensure_ascii=False, indent=2)
            
            time.sleep(1) # Small delay
        except Exception as e:
            print(f"FATAL: Page {page_num} failed: {e}. Progress saved to {raw_output}. Restart the script to resume.")
            break # Stop processing but keep what we have
        
    # 3. Stitch sections across pages
    print("Stitching sections...")
    stitched_data = stitch_sections(all_pages_raw_data)
    
    # 4. Save Final Results
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(stitched_data, f, ensure_ascii=False, indent=2)
        
    print(f"Ingestion complete! Results saved to {output_json} and {raw_output}")
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
