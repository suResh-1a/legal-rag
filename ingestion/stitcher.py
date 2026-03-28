from typing import List, Dict
import re


def _strip_dafa(dafa_no: str) -> str:
    """Strip parens, dots and whitespace to get the bare identifier.
    '(ञ)' -> 'ञ', '३.' -> '३', '(२)' -> '२'
    """
    return re.sub(r"[().\s]", "", dafa_no)


def _get_type(dafa_no: str) -> str:
    if not dafa_no:
        return "content"
    text = str(dafa_no).strip()
    # Section: 1. or 2 or Dafa 1
    if re.match(r"^[0-9०-९]+\.?$", text) or "दफा" in text:
        return "section"
    # Clause: (क), (ञ), (ढ) - Letters in parens
    if re.match(r"^\([क-ह][क-ह०-९]*\)$", text):
        return "clause"
    # Sub-clause: (1), (2), (1क) - Numbers in parens
    if re.match(r"^\([0-9०-९]+[क-ह]?\)$", text):
        return "sub_clause"
    return "other"


def _build_hierarchy_path(section: str | None, clause: str | None, sub_clause: str | None) -> str | None:
    """Build a compact machine-friendly path like '३-ञ-२'."""
    parts = []
    if section:
        parts.append(_strip_dafa(section))
    if clause:
        parts.append(_strip_dafa(clause))
    if sub_clause:
        parts.append(_strip_dafa(sub_clause))
    return "-".join(parts) if parts else None


def stitch_sections(all_pages_data: List[List[Dict]]) -> List[Dict]:
    """
    Implements a 'Stitcher' that:
    1. Merges continuations across pages.
    2. Tracks 3-layer hierarchical context: Section -> Clause -> Sub-clause.
    3. Generates a compact `hierarchy_path` for unique identification.
    """
    final_sections = []
    current_section = None
    current_clause = None

    for page_idx, page_data in enumerate(all_pages_data):
        if not page_data:
            continue

        transformed_page_data = []

        for i, item in enumerate(page_data):
            dafa_no = str(item.get("dafa_no") or "").strip()
            item_type = _get_type(dafa_no)
            content = str(item.get("content") or "").strip()

            # Detect list starters at the end of content
            if content.endswith(":-") or content.endswith(":- ") or content.endswith(":"):
                item["is_list_starter"] = True
            else:
                item["is_list_starter"] = False

            # 1. Hierarchical Tracking Logic + hierarchy_path
            if item_type == "section":
                current_section = dafa_no
                current_clause = None
                item["full_reference"] = f"Section {dafa_no}"
                item["hierarchy_path"] = _build_hierarchy_path(dafa_no, None, None)
            elif item_type == "clause":
                current_clause = dafa_no
                ref = f"Section {current_section}" if current_section else ""
                item["full_reference"] = f"{ref}, Clause {dafa_no}".strip(", ")
                item["hierarchy_path"] = _build_hierarchy_path(current_section, dafa_no, None)
            elif item_type == "sub_clause":
                ref = f"Section {current_section}" if current_section else ""
                clause_ref = f", Clause {current_clause}" if current_clause else ""
                item["full_reference"] = f"{ref}{clause_ref}, Sub-clause {dafa_no}".strip(", ")
                item["hierarchy_path"] = _build_hierarchy_path(current_section, current_clause, dafa_no)
            else:
                # Fallback for "content" or "other"
                if dafa_no:
                    ref = f"Section {current_section}" if current_section else ""
                    clause_ref = f", Clause {current_clause}" if current_clause else ""
                    item["full_reference"] = f"{ref}{clause_ref} {dafa_no}".strip(", ")
                    item["hierarchy_path"] = _build_hierarchy_path(current_section, current_clause, dafa_no)
                else:
                    item["full_reference"] = None
                    item["hierarchy_path"] = _build_hierarchy_path(current_section, current_clause, None)

            # 2. Logic for Stitching continuations
            if i == 0 and not item.get("dafa_no") and final_sections:
                last_section = final_sections[-1]
                if last_section.get("is_incomplete"):
                    last_section["content"] = f"{last_section.get('content', '')} {item.get('content', '')}"
                    last_section["is_incomplete"] = item.get("is_incomplete", False)
                    # Propagate list starter flag if the continuation completes it
                    if not last_section.get("is_incomplete") and (content.endswith(":-") or content.endswith(":")):
                        last_section["is_list_starter"] = True

                    if item.get("amendment_history"):
                        prev_hist = last_section.get("amendment_history")
                        new_hist = item.get("amendment_history")
                        last_section["amendment_history"] = f"{prev_hist} | {new_hist}" if prev_hist else new_hist
                    continue  # Skip adding this as a new item

            transformed_page_data.append(item)

        final_sections.extend(transformed_page_data)

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
