import google.generativeai as genai
import PIL.Image
import json
import os
import re
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

class GeminiExtractor:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY NOT FOUND")
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash")

    def extract_legal_data(self, image_path: str, page_num: int) -> List[Dict]:
        """
        Extract legal sections from a single page image.
        """
        img = PIL.Image.open(image_path)
        
        system_prompt = """You are a Legal Digitizer. Extract every Dafa (Section) and Upadafa. Pay extreme attention to visual symbols (Diamonds, ⊓, Σ, *, +) before section numbers. These are Amendment Markers. Look at the bottom of the page for footnotes to map these symbols to specific Amendment Acts. Capture the text in pure Nepali Unicode. If a section is cut off at the bottom, mark it with "is_incomplete": true.

Output must be a strictly typed JSON list of objects:
[
  {
    "dafa_no": "Section Number in Nepali",
    "title": "Section Title in Nepali",
    "content": "Full section text in Nepali",
    "symbol_found": "The symbol found (e.g., Diamond, ⊓, Σ, *, +) or null",
    "amendment_history": "Extracted amendment act from footnotes mapping the symbol or null",
    "page_num": integer,
    "is_incomplete": boolean
  }
]
"""
        user_prompt = f"Analyze Page {page_num} of the provided legal document scan."
        
        import time
        from google.api_core import exceptions
        
        max_retries = 5
        base_delay = 5 # Start with 5 seconds for 429
        
        for attempt in range(max_retries):
            try:
                response = self.model.generate_content([system_prompt, user_prompt, img])
                break # Success
            except exceptions.ResourceExhausted as e:
                if attempt == max_retries - 1:
                    print(f"Max retries exceeded for page {page_num}: {e}")
                    raise e
                delay = base_delay * (2 ** attempt)
                print(f"429 Resource Exhausted for page {page_num}. Retrying in {delay}s... (Attempt {attempt+1}/{max_retries})")
                time.sleep(delay)
            except Exception as e:
                print(f"Unexpected error for page {page_num}: {e}")
                raise e
        
        # Extract JSON from response
        try:
            # Clean response text from markdown blocks and control characters
            content = response.text
            match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
            json_str = match.group(1) if match else content
            
            # Robust cleaning for JSON: 
            # 1. Remove control characters except for newline
            json_str = "".join(c for c in json_str if ord(c) >= 32 or c in "\n\r\t")
            # 2. Fix unescaped backslashes (but keep them for valid escape sequences)
            # This is a common issue with Gemini in Nepali text
            json_str = json_str.replace('\\', '\\\\') # Escape all backslashes
            json_str = json_str.replace('\\\\"', '\\"') # Re-fix escaped quotes
            json_str = json_str.replace('\\\\n', '\\n')  # Re-fix escaped newlines
            
            data = json.loads(json_str)
            
            # Ensure page_num and source_image_path are consistent
            for item in data:
                item["page_num"] = page_num
                item["source_image_path"] = image_path
            return data
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"Error parsing Gemini response for page {page_num}: {e}")
            print(f"Raw response: {response.text}")
            return []

if __name__ == "__main__":
    extractor = GeminiExtractor()
    # Test with a dummy image if exists or just mock
    # results = extractor.extract_legal_data("uploads/temp_images/page_7.png", 7)
    # print(json.dumps(results, indent=2, ensure_ascii=False))
