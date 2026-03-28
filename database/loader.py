import os
import sys
# Allow running as a script from the root directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
from database.manager import DatabaseManager

def load_json_to_db(json_path: str, collection: str):
    """
    Loads extracted legal data from a JSON file into MongoDB and Qdrant.
    """
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found")
        return
        
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    db_manager = DatabaseManager()
    
    print(f"Loading {len(data)} items into {collection}...")
    for i, section in enumerate(data):
        try:
            mongo_id = db_manager.upsert_to_knowledge_base(section, collection=collection)
            print(f"[{i+1}/{len(data)}] Upserted to {collection}: {section.get('dafa_no')} (ID: {mongo_id})")
        except Exception as e:
            print(f"Error upserting item {i+1} to {collection}: {e}")
            
    print(f"Done loading {collection}.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Reset database before loading")
    parser.add_argument("--restitch", action="store_true", help="Re-run stitcher on raw page data before loading")
    args = parser.parse_args()
    
    db_manager = DatabaseManager()
    if args.reset:
        db_manager.reset_database()
    
    STITCHED_PATH = "data/raw_extracted_legal_data.json"
    RAW_PAGE_PATH = "data/per_page_raw_data.json"
    
    # Re-stitch if requested (e.g., after stitcher.py changes)
    if args.restitch:
        import json
        from ingestion.stitcher import stitch_sections
        
        print("Re-stitching from per_page_raw_data.json...")
        with open(RAW_PAGE_PATH, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        
        # Group raw data by page_num into list-of-lists
        page_map = {}
        for item in raw_data:
            p_num = item.get("page_num")
            if p_num not in page_map:
                page_map[p_num] = []
            page_map[p_num].append(item)
        
        all_pages = [page_map[p] for p in sorted(page_map.keys())]
        stitched = stitch_sections(all_pages)
        
        with open(STITCHED_PATH, "w", encoding="utf-8") as f:
            json.dump(stitched, f, ensure_ascii=False, indent=2)
        print(f"Re-stitched {len(stitched)} sections -> {STITCHED_PATH}")
    
    # 1. Load Stitched Sections
    load_json_to_db(STITCHED_PATH, "legal_sections_vectors")
    
    # 2. Load Raw Per-Page Sections
    load_json_to_db(RAW_PAGE_PATH, "legal_pages_vectors")
