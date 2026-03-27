import google.generativeai as genai
import time
import json
import os
import re

# 1. SETUP API
# API Key is loaded from .env or environment variables
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    try:
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv("GOOGLE_API_KEY")
    except ImportError:
        pass

if not api_key:
    raise ValueError("GOOGLE_API_KEY not found in environment or .env file")

genai.configure(api_key=api_key)

# 2. CONFIGURATION
PDF_FILE_PATH = "scripts/lex/seed_act_nepal.pdf" # Put your PDF file name here
START_PAGE = 7
END_PAGE = 8
BATCH_SIZE = 1  # Small batches (2-3 pages) are SAFER to prevent text cutoff

def upload_to_gemini(path):
    print(f"Uploading {path} to Gemini...")
    file = genai.upload_file(path=path)
    while file.state.name == "PROCESSING":
        time.sleep(2)
        file = genai.get_file(file.name)
    print("Upload complete.")
    return file

def extract_legal_batch(file_handle, start, end):
    # Using gemini-2.0-flash as it is confirmed to be available
    model = genai.GenerativeModel(model_name="gemini-2.0-flash")
    
    # SYSTEM PROMPT - Very specific for Nepal Law Commission PDFs
    prompt = f"""
    Analyze pages {start} to {end} of the provided Nepal Law PDF.
    
    TASK: 
    Convert the legal text into a structured JSON list.
    
    CRITICAL RULES FOR NEPALESE LAW:
    1. SYMBOLS: If a Dafa (Section) starts with symbols like '⊓', 'Σ', '*', diamonds, boxes, stars,etc symbol can bw weird stranger but these are Amendment markers not noise or mistake.You must NOT skip them.
    2. FOOTNOTES: Look at the very bottom of the page. Find the legend for these symbols. 
       - e.g., if '⊓' is at the bottom as 'बीउ बिजन (दोस्रो संशोधन) ऐन, २०७९', map that text to the section.
    3. HIERARCHY: Identify 'Dafa' (Section), 'Upadafa' (Sub-section), and 'Khanda' (Clause).
    4. LANGUAGE: Use standard Nepali Unicode. Fix common OCR typos (like 'तफा' to 'दफा').

    TASK:
    1. Scan the start of every Dafa and Upadafa. 
    2. If you see ANY visual symbol (even a small diamond shape), capture it.
    3. Read the FOOTNOTES at the bottom of the page to find what that symbol means (which Amendment Act it refers to).
    4. Format the output into JSON.
    
    OUTPUT FORMAT (Return ONLY JSON):
    [
      {{
        "dafa_no": "The number (e.g., 9 or 10ka)",
        "title": "The heading of the section",
        "symbol": "The character found (e.g., ⊓)",
        "amendment_history": "The full text from the footnote explaining this symbol",
        "content": "The full text of the law in this section",
        "page_ref": {start}-{end}
      }}
    ]
    """
    
    response = model.generate_content([prompt, file_handle])
    return response.text

# --- MAIN TEST EXECUTION ---

# Upload once
legal_file = upload_to_gemini(PDF_FILE_PATH)

final_output = []

print(f"Starting Test Extraction: Pages {START_PAGE} to {END_PAGE}")

for current_page in range(START_PAGE, END_PAGE + 1, BATCH_SIZE):
    batch_end = min(current_page + BATCH_SIZE - 1, END_PAGE)
    print(f"--- Processing Batch: Pages {current_page} to {batch_end} ---")
    
    raw_response = None
    try:
        raw_response = extract_legal_batch(legal_file, current_page, batch_end)
        
        # Clean JSON markdown blocks if present
        clean_json = re.sub(r'```json\s*|```', '', raw_response).strip()
        
        batch_data = json.loads(clean_json)
        final_output.extend(batch_data)
        
        # Save temporary progress so you don't lose data if it fails
        with open("test_extraction_results.json", "w", encoding="utf-8") as f:
            json.dump(final_output, f, ensure_ascii=False, indent=2)
            
        print(f"Successfully extracted {len(batch_data)} sections.")
        
    except Exception as e:
        print(f"Error on Pages {current_page}-{batch_end}: {e}")
        # Print the raw response to debug if JSON parsing failed
        if raw_response:
            print("Raw Response was:", raw_response[:500] + "...")
        else:
            print("No response received from API.")

    time.sleep(4) # Respect API limits

print("\nTEST COMPLETE. Check 'test_extraction_results.json'")