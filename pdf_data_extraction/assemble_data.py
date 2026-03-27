import json
import os

def stitch_sections(data):
    """
    Stitches sections that are marked as incomplete or are orphans.
    """
    stitched_data = []
    
    for i, entry in enumerate(data):
        # If it's an orphan, it belongs to the previous entry
        if entry.get("is_orphan") and stitched_data:
            previous = stitched_data[-1]
            # Merge content
            previous["content"] = previous.get("content", "") + "\n" + entry.get("content", "")
            # Inherit completeness from the orphan
            previous["is_complete"] = entry.get("is_complete", True)
            # Merge amendment history
            if entry.get("amendment_history"):
                prev_hist = previous.get("amendment_history")
                new_hist = entry.get("amendment_history")
                if prev_hist and new_hist != prev_hist:
                    previous["amendment_history"] = f"{prev_hist} | {new_hist}"
                else:
                    previous["amendment_history"] = new_hist
            continue

        # Check if we should merge with previous even if not explicitly marked as orphan
        # (e.g. if the previous was incomplete and this one has no dafa_no)
        if stitched_data and not stitched_data[-1].get("is_complete") and not entry.get("dafa_no"):
            previous = stitched_data[-1]
            previous["content"] = previous.get("content", "") + "\n" + entry.get("content", "")
            previous["is_complete"] = entry.get("is_complete", True)
            continue
            
        # Otherwise, add as a new section
        stitched_data.append(entry)
        
    return stitched_data

def main():
    input_file = "multi_page_extraction_results.json"
    output_file = "final_legal_data.json"
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return
        
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    print(f"Loaded {len(data)} fragments.")
    assembled = stitch_sections(data)
    print(f"Assembled into {len(assembled)} complete sections.")
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(assembled, f, ensure_ascii=False, indent=2)
    print(f"Saved to {output_file}")

if __name__ == "__main__":
    main()
