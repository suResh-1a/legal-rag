import os
import base64
import json
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
from pdf2image import convert_from_path

# --- CONFIGURATION ---
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
PDF_PATH = "seed_act_nepal.pdf"
OUTPUT_FOLDER = "extracted_data"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

DEFAULT_LEGAL_PROMPT = """
    You are a professional Nepalese Legal Digitizer. 
    Analyze this page from the Nepal Gazette (Rajpatra). 
    
    TASKS:
    1. Identify the 'Footnote Legend' at the bottom (e.g., what symbols like ⊓, Σ, *, + mean).
    2. Extract all Dafa (Sections) and Upadafa (Sub-sections).
    3. For each Dafa, check if it starts with a symbol. Map that symbol to the Amendment name found in the footnotes.
    4. Convert all text to standard Nepali Unicode. Fix any visual OCR artifacts.
    5. Output the data in a STRICT JSON format.

    JSON STRUCTURE:
    {
      "page_number": int,
      "footnotes": [{"symbol": "string", "meaning": "full text of amendment info"}],
      "sections": [
        {
          "dafa_no": "string (e.g. 9 or 10ka)",
          "title": "string",
          "symbol_attached": "string",
          "amendment_info": "string from footnote mapping",
          "sub_sections": [
             {"upadafa_no": "string", "content": "text body"}
          ]
        }
      ]
    }
    """

def extract_legal_data(image_path, prompt=DEFAULT_LEGAL_PROMPT, model="gpt-4o"):

    try:
        base64_image = encode_image(image_path)
        print(f"DEBUG: Using model {model}. Base64 length: {len(base64_image)}")
        
        # Determine if we should use json_object mode
        # OpenAI requires the word "json" in the prompt for this mode
        use_json_mode = "json" in prompt.lower()
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                    ],
                }
            ],
            response_format={ "type": "json_object" } if use_json_mode else None
        )
        
        if response.choices[0].message.refusal:
            print(f"ERROR: Model refused to process the image: {response.choices[0].message.refusal}")
            return json.dumps({"error": "refusal", "message": response.choices[0].message.refusal})

        content = response.choices[0].message.content
        if not content:
            print(f"DEBUG: Empty content. Finish reason: {response.choices[0].finish_reason}")
            return json.dumps({"error": "empty_content"})
            
        return content
    except Exception as e:
        print(f"API Error: {e}")
        return json.dumps({"error": "exception", "message": str(e)})

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    # 1. Convert PDF to images
    # Use absolute path to avoid I/O error when imported from different directory
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    FULL_PDF_PATH = os.path.join(BASE_DIR, PDF_PATH)
    
    images = convert_from_path(FULL_PDF_PATH, dpi=300)

    all_pages_data = []

    for i, image in enumerate(images):
        img_path = f"temp_page_{i}.jpg"
        image.save(img_path, "JPEG")
        
        print(f"Processing Page {i+1}...")
        try:
            page_json = extract_legal_data(img_path)
            all_pages_data.append(json.loads(page_json))
            
            # Save individual page JSON
            with open(f"{OUTPUT_FOLDER}/page_{i+1}.json", "w", encoding="utf-8") as f:
                f.write(page_json)
                
        except Exception as e:
            print(f"Error on page {i+1}: {e}")
        finally:
            if os.path.exists(img_path):
                os.remove(img_path) # Clean up image

    # 2. Save combined result
    with open("final_legal_data.json", "w", encoding="utf-8") as f:
        json.dump(all_pages_data, f, ensure_ascii=False, indent=2)

    print("Extraction Complete! Check 'final_legal_data.json'")