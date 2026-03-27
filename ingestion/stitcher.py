from typing import List, Dict

def stitch_sections(all_pages_data: List[List[Dict]]) -> List[Dict]:
    """
    Implements a 'Stitcher' function that merges sections where 
    is_incomplete is true on Page N with the first 'orphan' text on Page N+1.
    """
    final_sections = []
    
    for page_idx, page_data in enumerate(all_pages_data):
        if not page_data:
            continue
            
        current_page_sections = []
        
        # If the first item on this page has no dafa_no, it might be a continuation from Page N
        first_item = page_data[0]
        has_orphan_start = first_item.get("dafa_no") is None or first_item.get("dafa_no") == ""
        
        if has_orphan_start and final_sections:
            last_section = final_sections[-1]
            if last_section.get("is_incomplete"):
                # Merge with the last section of the previous pages
                last_section["content"] = f"{last_section.get('content', '')} {first_item.get('content', '')}"
                last_section["is_incomplete"] = first_item.get("is_incomplete", False)
                # If the orphan has amendment history, append or update
                if first_item.get("amendment_history"):
                    prev_hist = last_section.get("amendment_history")
                    new_hist = first_item.get("amendment_history")
                    last_section["amendment_history"] = f"{prev_hist} | {new_hist}" if prev_hist else new_hist
                
                # We skip adding the first_item to current_page_sections because it's merged
                current_page_sections = page_data[1:]
            else:
                # If the last section wasn't marked incomplete, but this looks like an orphan,
                # we still treat it as a new section (or maybe a missed segment)
                current_page_sections = page_data
        else:
            current_page_sections = page_data
            
        final_sections.extend(current_page_sections)
        
    return final_sections

if __name__ == "__main__":
    # Test Stitcher mock
    mock_data = [
        [
            {"dafa_no": "१", "title": "Section 1", "content": "This is part 1", "is_incomplete": True, "page_num": 1}
        ],
        [
            {"dafa_no": None, "title": None, "content": "continuation of part 1.", "is_incomplete": False, "page_num": 2},
            {"dafa_no": "२", "title": "Section 2", "content": "This is Section 2.", "is_incomplete": False, "page_num": 2}
        ]
    ]
    stitched = stitch_sections(mock_data)
    print("Stitched Data:")
    for s in stitched:
        print(s)
