import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion.stitcher import stitch_sections, _strip_dafa, _get_type, _build_hierarchy_path


class TestStripDafa:
    def test_strips_parens(self):
        assert _strip_dafa("(ञ)") == "ञ"

    def test_strips_dots(self):
        assert _strip_dafa("३.") == "३"

    def test_strips_parens_number(self):
        assert _strip_dafa("(२)") == "२"

    def test_plain_text(self):
        assert _strip_dafa("क") == "क"


class TestGetType:
    def test_section_nepali(self):
        assert _get_type("३.") == "section"

    def test_section_ascii(self):
        assert _get_type("3") == "section"

    def test_clause(self):
        assert _get_type("(ञ)") == "clause"

    def test_sub_clause(self):
        assert _get_type("(२)") == "sub_clause"

    def test_content_empty(self):
        assert _get_type("") == "content"

    def test_content_none(self):
        assert _get_type(None) == "content"


class TestBuildHierarchyPath:
    def test_section_only(self):
        assert _build_hierarchy_path("३.", None, None) == "३"

    def test_section_clause(self):
        assert _build_hierarchy_path("३.", "(ञ)", None) == "३-ञ"

    def test_full_path(self):
        assert _build_hierarchy_path("३.", "(ञ)", "(२)") == "३-ञ-२"

    def test_none_all(self):
        assert _build_hierarchy_path(None, None, None) is None


class TestStitchSections:
    def test_hierarchy_path_section(self):
        data = [[
            {"dafa_no": "१.", "title": "Section 1", "content": "text", "page_num": 1}
        ]]
        result = stitch_sections(data)
        assert result[0]["hierarchy_path"] == "१"
        assert result[0]["full_reference"] == "Section १."

    def test_hierarchy_path_clause(self):
        data = [[
            {"dafa_no": "२.", "title": "Section 2", "content": "parent:", "page_num": 1},
            {"dafa_no": "(क)", "title": None, "content": "clause text", "page_num": 1},
        ]]
        result = stitch_sections(data)
        assert result[1]["hierarchy_path"] == "२-क"
        assert result[1]["full_reference"] == "Section २., Clause (क)"

    def test_hierarchy_path_sub_clause(self):
        data = [[
            {"dafa_no": "३.", "title": "Section 3", "content": "root", "page_num": 1},
            {"dafa_no": "(ञ)", "title": None, "content": "clause", "page_num": 1},
            {"dafa_no": "(२)", "title": None, "content": "sub-clause text", "page_num": 1},
        ]]
        result = stitch_sections(data)
        assert result[2]["hierarchy_path"] == "३-ञ-२"
        assert result[2]["full_reference"] == "Section ३., Clause (ञ), Sub-clause (२)"

    def test_list_starter_detection(self):
        data = [[
            {"dafa_no": "४.", "title": "Section 4", "content": "enumeration follows:-", "page_num": 1},
        ]]
        result = stitch_sections(data)
        assert result[0]["is_list_starter"] is True

    def test_continuation_stitching(self):
        data = [
            [{"dafa_no": "१.", "title": "S1", "content": "Part 1", "is_incomplete": True, "page_num": 1}],
            [{"dafa_no": None, "title": None, "content": "Part 2.", "is_incomplete": False, "page_num": 2}]
        ]
        result = stitch_sections(data)
        assert len(result) == 1
        assert "Part 1 Part 2." in result[0]["content"]
        assert result[0]["is_incomplete"] is False

    def test_continuation_preserves_amendment(self):
        data = [
            [{"dafa_no": "१.", "title": "S1", "content": "Part 1", "is_incomplete": True, "page_num": 1,
              "amendment_history": "Act A"}],
            [{"dafa_no": None, "title": None, "content": "Part 2.", "is_incomplete": False, "page_num": 2,
              "amendment_history": "Act B"}]
        ]
        result = stitch_sections(data)
        assert "Act A" in result[0]["amendment_history"]
        assert "Act B" in result[0]["amendment_history"]

    def test_no_confusion_section_vs_subclause(self):
        """Key test: Section 3 and Sub-clause (3) within Section 3 must have different hierarchy_paths."""
        data = [[
            {"dafa_no": "३.", "title": "Section 3", "content": "root", "page_num": 1},
            {"dafa_no": "(ञ)", "title": None, "content": "clause", "page_num": 1},
            {"dafa_no": "(३)", "title": None, "content": "sub-clause 3", "page_num": 1},
        ]]
        result = stitch_sections(data)
        section_3 = result[0]
        sub_clause_3 = result[2]
        # These must be DIFFERENT
        assert section_3["hierarchy_path"] != sub_clause_3["hierarchy_path"]
        assert section_3["hierarchy_path"] == "३"
        assert sub_clause_3["hierarchy_path"] == "३-ञ-३"
