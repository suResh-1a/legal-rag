import os
import sys
# Allow running as a script from the root directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
from database.manager import DatabaseManager

def load_json_to_db(json_path: str):
    """
    Loads extracted legal data from a JSON file into MongoDB and Qdrant.
    """
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found")
        return
        
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    db_manager = DatabaseManager()
    
    print(f"Loading {len(data)} sections into knowledge base...")
    for i, section in enumerate(data):
        try:
            mongo_id = db_manager.upsert_to_knowledge_base(section)
            print(f"[{i+1}/{len(data)}] Upserted Section {section.get('dafa_no')} (ID: {mongo_id})")
        except Exception as e:
            print(f"Error upserting section {i+1}: {e}")
            
    print("Done loading data.")

if __name__ == "__main__":
    JSON_PATH = "data/raw_extracted_legal_data.json"
    load_json_to_db(JSON_PATH)
