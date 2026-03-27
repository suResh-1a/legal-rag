import google.generativeai as genai
import PIL.Image
from pdf2image import convert_from_path
import json
import os
import re
from dotenv import load_dotenv

# 1. SETUP API
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    raise ValueError("GOOGLE_API_KEY not found in environment or .env file")

genai.configure(api_key=api_key)

# 2. CONFIGURATION
PDF_PATH = "scripts/lex/seed_act_nepal.pdf"
DPI = 300
ACT_NAME = "मुलुकी अपराध संहिता"
ACT_YEAR = "२०७४"
SOURCE_URL = "https://lawcommission.gov.np"

def extract_from_image(image_path, page_num):
    print(f"[{page_num}] Sending {image_path} to Gemini...")
    model = genai.GenerativeModel(model_name="gemini-2.0-flash")
    img = PIL.Image.open(image_path)
    
    prompt = f"""
    Analyze this image of a Nepalese Legal document (Page {page_num}) very carefully.
    
    VISUAL IDENTIFICATION TASK:
    1. Identify all Dafa (Sections) and their Titles. A Dafa usually starts with a number followed by a dot (e.g., २२., २३.) or a title.
    2. MANDATORY ORPHAN CHECK: Look at the very top of the page (below any website headers). If there is ANY text (sentences, sub-clauses, or fragments) appearing BEFORE the first numbered Dafa, extract it as an independent object with `is_orphan: true`.
    3. TABLE HANDLING: If you see a table, extract all its data and format it as a valid GitHub Markdown table in the `content` field.
    4. SYMBOLS & FOOTNOTES: 
        - Find geometric symbols (diamond, star, square, cross) before Dafa numbers.
        - Return their SPATIAL COORDINATES in [ymin, xmin, ymax, xmax] format (0-1000 scale).
        - Find any footnotes at the bottom explaining these symbols. 
        - Return the SPATIAL COORDINATES for the entire footnote area as well.

    EXTRACT TO JSON:
    [
      {{
        "act_name": "{ACT_NAME}",
        "act_year": "{ACT_YEAR}",
        "source": "{SOURCE_URL}",
        "page_num": {page_num},
        "dafa_no": "Number (null for orphans)",
        "title": "Title (null for orphans)",
        "symbol_found": "Shape name",
        "symbol_coords": [ymin, xmin, ymax, xmax],
        "footnote_coords": [ymin, xmin, ymax, xmax],
        "amendment_history": "Full text from the footnote explaining the symbol",
        "content": "Full text or Markdown Table",
        "is_complete": boolean (True if it ends with a Purna Biram ।),
        "is_orphan": boolean (True if it's top-of-page continuation)
      }}
    ]
    Return ONLY JSON.
    """
    
    response = model.generate_content([prompt, img])
    return response.text

# --- RUN TEST ---
if __name__ == "__main__":
    TEST_PAGES = [7, 8]
    all_results = []
    
    for PAGE_NUM in TEST_PAGES:
        print(f"\n--- Processing Page {PAGE_NUM} ---")
        try:
            images = convert_from_path(PDF_PATH, first_page=PAGE_NUM, last_page=PAGE_NUM, dpi=DPI)
            if not images:
                print(f"Error: No images generated for Page {PAGE_NUM}.")
                continue
                
            temp_image = f"temp_page_{PAGE_NUM}.png"
            images[0].save(temp_image, "PNG")
            
            raw_result = extract_from_image(temp_image, PAGE_NUM)
            
            # Clean JSON markdown blocks if present
            clean_json = re.sub(r'```json\s*|```', '', raw_result).strip()
            
            try:
                batch_data = json.loads(clean_json)
                all_results.extend(batch_data)
                print(f"Successfully extracted {len(batch_data)} sections from Page {PAGE_NUM}.")
            except json.JSONDecodeError:
                print(f"Error: Could not parse JSON for Page {PAGE_NUM}.")
                print("Raw response:", raw_result[:200])
            
            # os.remove(temp_image)
        except Exception as e:
            print(f"An error occurred on Page {PAGE_NUM}: {e}")

    # Save all results to a single file for assembly
    output_file = "multi_page_extraction_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\nAll results saved to {output_file}")
