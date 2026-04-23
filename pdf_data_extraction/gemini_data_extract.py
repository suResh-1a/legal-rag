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
    # Using gemini-2.5-flash-lite as it is confirmed to be available
    model = genai.GenerativeModel(model_name="gemini-2.5-flash-lite")
    
    # SYSTEM PROMPT - Very specific for Nepal Law Commission PDFs
    prompt = f
    """
            ### Revised Prompt

            **System Role:** You are a specialized Legal Document Parser for the Nepal Law Commission. Your expertise is in identifying Amendment Markers (Footnote Symbols) that indicate legislative history.

            **Task:** Analyze pages {start} to {end} of the provided PDF and convert the text into a structured JSON list.

            **CRITICAL PARSING LOGIC:**
            1.  **FOOTNOTE LEGEND (DO THIS FIRST):** Look at the footer (bottom area) of every page. Create a mental map of symbols/markers to their corresponding Amendment Act. Symbols include Greek letters ($\rho, \tau, \Sigma, \nabla, \kappa$), Devanagari numbers ($१, २, ३$), or icons (✂, *, $\square$).
                *   *Example:* If the footer says "$\rho$ दोश्रो संशोधनद्वारा थप," then every time you see $\rho$ in the body, the `amendment_history` is "Added by the Second Amendment."

            2.  **NUMBER INTEGRITY (MANDATORY):** Do NOT merge Section/Sub-section numbers with footnote markers.
                *   *Example:* If you see "८७", look at the context. It is likely Section **८** (8) with Footnote **७** (7). Do not output "87".

            3.  **HIERARCHY & CLEANING:**
                *   **Dafa (Section):** The main bold numbers.
                *   **Upadafa (Sub-section):** Numbers in brackets like (१), (२).
                *   **Khanda (Clause):** Letters like (क), (ख).
                *   **Typos:** Correct OCR errors (e.g., 'तफा' -> 'दफा', 'पठारी' -> 'पैठारी', 'उच्चोग' -> 'उद्योग').

            4.  **AMENDMENT MARKERS:** Do not delete symbols found next to section headings. Capture them in the `symbol` field.

            ---

            **OUTPUT JSON SCHEMA:**
            Return **ONLY** a JSON array. Each object must follow this structure:

            ```json
            [
            {
                "section_id": "Pure number only, e.g., 4 or 5ka",
                "title": "Full title of the Section in Nepali",
                "symbol_found": "The marker found next to the number (e.g., ρ, Σ, or 7)",
                "amendment_history": "The specific text from the footnote legend matching the symbol",
                "content": {
                "full_text": "The main text of the section",
                "sub_sections": [
                    {
                    "number": "(1)",
                    "text": "Text of sub-section",
                    "sub_symbol": "If a specific sub-section has its own marker",
                    "sub_amendment": "Amendment history for this specific sub-section"
                    }
                ]
                },
                "page_ref": "{start}"
            }
            ]
            ```

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