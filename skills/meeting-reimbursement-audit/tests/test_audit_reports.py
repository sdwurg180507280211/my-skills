from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_reports as audit

HEADER = ("用户ID", "姓名", "医院", "科室", "首次进入时间", "最后离开时间", "在线时长（分钟）")


def participant(index, minutes=20, name=None, hospital="合成医院", department="合成科室", user_id=None):
    return (f"id-{index}" if user_id is None else user_id, name or f"合成人员{index}", hospital, department, "09:51", "10:26", minutes)


def report(name, records):
    parsed = audit.parse_rows([("会议时间", "10:00-10:30"), HEADER, *records], f"/{name}/参会明细.xlsx", "参会报告", name)
    return audit.summarize(parsed, Decimal(20), 10)


class AttendanceTests(unittest.TestCase):
    def test_duration_boundary_and_ten_people_pass(self):
        result = report("A", [participant(i) for i in range(10)] + [participant(10, 19)])
        self.assertEqual(result["eligible_count"], 10)
        self.assertEqual(result["below_threshold_count"], 1)
        self.assertEqual(result["headcount_status"], "pass")

    def test_nine_people_fail(self):
        self.assertEqual(report("A", [participant(i) for i in range(9)])["headcount_status"], "fail")

    def test_reported_duration_ignores_entry_exit_and_poster(self):
        records = [participant(i, 25) for i in range(10)]
        records[0] = ("staff", "工作人员", "拜耳", "合成部门", "22:00", "00:01", 25)
        result = report("A", records)
        self.assertEqual(result["eligible_count"], 10)
        self.assertEqual(result["headcount_status"], "pass")
        self.assertFalse(result["data_issues"])

    def test_numeric_text_and_unknown_are_not_zero(self):
        for value in (20, 20.0, "２０", "20 分钟", "20.00"):
            self.assertEqual(audit.parse_minutes(value), Decimal(20))
        for value in (None, "", "未知", "=G3+1", True, -1, "NaN", "Infinity", "00:20:00"):
            self.assertIsNone(audit.parse_minutes(value))
        result = report("A", [participant(i) for i in range(9)] + [participant(9, None)])
        self.assertEqual(result["eligible_count"], 9)
        self.assertEqual(result["possible_eligible_count"], 10)
        self.assertEqual(result["headcount_status"], "needs_review")

    def test_same_person_is_not_counted_twice_or_summed(self):
        result = report("A", [participant(i) for i in range(9)] + [participant(0)])
        self.assertEqual(result["record_count"], 10)
        self.assertEqual(result["unique_participant_count"], 9)
        self.assertEqual(result["headcount_status"], "fail")
        short = report("A", [participant(0, 11), participant(0, 11)])
        self.assertEqual(short["eligible_count"], 0)

    def test_conflicting_duplicate_is_not_arbitrarily_maximized(self):
        result = report("A", [participant(i) for i in range(9)] + [participant(9, 19), participant(9, 25)])
        self.assertEqual(result["headcount_status"], "needs_review")
        self.assertEqual(result["eligible_count"], 9)

    def test_incomplete_identity_does_not_inflate_certain_headcount(self):
        result = report("A", [participant(i) for i in range(9)] + [participant(9, user_id="")])
        self.assertFalse(result["identity_complete"])
        self.assertEqual(result["headcount_status"], "needs_review")

    def test_known_ten_pass_despite_extra_unknown_record(self):
        result = report("A", [participant(i) for i in range(10)] + [participant(10, None)])
        self.assertEqual(result["headcount_status"], "pass")

    def test_header_detection_blank_rows_and_source_row_numbers(self):
        parsed = audit.parse_rows([("metadata",), (), HEADER, participant(0), (), HEADER, participant(1)], "/synthetic.xlsx", "Synthetic", "A")
        self.assertEqual(parsed["header_row"], 3)
        self.assertEqual([record["row"] for record in parsed["records"]], [4, 7])
        with self.assertRaises(ValueError):
            audit.parse_rows([("姓名", "医院", "科室", "在线时长（秒）")], "/x", "s", "A")

    def test_optional_hospital_and_department_do_not_block_counting(self):
        parsed = audit.parse_rows([("用户ID", "姓名", "在线时长（分钟）"), ("id-0", "合成人员", 20)], "/synthetic.xlsx", "s", "A")
        self.assertEqual(parsed["records"][0]["key"], ("id-0", "合成人员"))
        self.assertFalse(parsed["data_issues"])

    def test_same_id_different_names_in_one_report_require_review(self):
        result = report("A", [participant(0), participant(0, name="另一个合成姓名")])
        self.assertFalse(result["identity_complete"])
        self.assertEqual(result["eligible_count"], 0)
        self.assertTrue(any(item["type"] == "id_name_conflict" for item in result["data_issues"]))


class OverlapTests(unittest.TestCase):
    def test_full_rosters_and_asymmetric_denominators(self):
        a = report("A", [participant(i, 19 if i == 0 else 20) for i in range(12)])
        b = report("B", [participant(i) for i in range(6)] + [participant(i) for i in range(20, 25)])
        pair = audit.compare_pairs([a, b], "larger-ratio", Decimal("0.5"))[0]
        self.assertEqual(pair["common_count"], 6)
        self.assertEqual((pair["size_a"], pair["size_b"]), (12, 11))
        self.assertEqual((pair["percent_a"], pair["percent_b"]), ("50.00%", "54.55%"))
        self.assertEqual(pair["status"], "fail")
        self.assertEqual(audit.compare_pairs([a, b], "smaller-ratio", Decimal("0.5"))[0]["status"], "pass")

    def test_fifty_percent_passes_and_all_pairs_checked(self):
        a = report("A", [participant(i) for i in range(10)])
        b = report("B", [participant(i) for i in range(5)] + [participant(i) for i in range(20, 25)])
        c = report("C", [participant(i) for i in range(30, 40)])
        pairs = audit.compare_pairs([a, b, c], "larger-ratio", Decimal("0.5"))
        self.assertEqual(len(pairs), 3)
        self.assertEqual(pairs[0]["status"], "pass")
        self.assertEqual(pairs[0]["common_count"], 5)

    def test_masked_names_are_literal_composite_keys(self):
        a = report("A", [participant(0, name="李**"), participant(1, name="李**", hospital="另一合成医院")])
        b = report("B", [participant(0, name=" 李＊＊ "), participant(3, name="李某某")])
        pair = audit.compare_pairs([a, b], "larger-ratio", Decimal("0.5"))[0]
        self.assertEqual(a["unique_participant_count"], 2)
        self.assertEqual(pair["common_count"], 1)

    def test_same_name_hospital_department_but_different_ids_are_not_repeats(self):
        a = report("A", [participant(i) for i in range(12)])
        b = report("B", [participant(i, user_id=f"other-id-{i}") for i in range(6)] + [participant(i) for i in range(20, 25)])
        pair = audit.compare_pairs([a, b], "larger-ratio", Decimal("0.5"))[0]
        self.assertEqual((pair["size_a"], pair["size_b"]), (12, 11))
        self.assertEqual(pair["common_count"], 0)
        self.assertEqual((pair["percent_a"], pair["percent_b"]), ("0.00%", "0.00%"))
        self.assertEqual(pair["status"], "pass")

    def test_same_id_and_name_match_despite_changed_hospital_department(self):
        a = report("A", [participant(0)])
        b = report("B", [participant(0, hospital="另一合成医院", department="另一合成科室")])
        self.assertEqual(audit.compare_pairs([a, b], "larger-ratio", Decimal("0.5"))[0]["common_count"], 1)

    def test_same_id_different_name_across_meetings_requires_review(self):
        a = report("A", [participant(0)])
        b = report("B", [participant(0, name="另一个合成姓名")])
        pair = audit.compare_pairs([a, b], "larger-ratio", Decimal("0.5"))[0]
        self.assertEqual(pair["common_count"], 0)
        self.assertEqual(pair["id_name_conflicts"], ["id-0"])
        self.assertEqual(pair["status"], "needs_review")

    def test_ids_are_case_sensitive(self):
        a = report("A", [participant(0, user_id="Case-ID")])
        b = report("B", [participant(0, user_id="case-id")])
        self.assertEqual(audit.compare_pairs([a, b], "larger-ratio", Decimal("0.5"))[0]["common_count"], 0)

    def test_missing_identity_or_empty_roster_cannot_look_like_zero_overlap_pass(self):
        a = report("A", [participant(0, user_id="")])
        b = report("B", [])
        pair = audit.compare_pairs([a, b], "larger-ratio", Decimal("0.5"))[0]
        self.assertEqual(pair["status"], "needs_review")
        self.assertIsNone(pair["ratio_a"])

    def test_unrounded_threshold_comparison(self):
        a = report("A", [participant(i) for i in range(3)])
        b = report("B", [participant(0), participant(20), participant(21)])
        pair = audit.compare_pairs([a, b], "larger-ratio", Decimal("0.3333"))[0]
        self.assertEqual(pair["percent_a"], "33.33%")
        self.assertEqual(pair["status"], "fail")


class IOTests(unittest.TestCase):
    def test_reader_uses_readonly_and_rejects_ambiguous_sheets(self):
        class Sheet:
            def __init__(self, title):
                self.title = title

            def iter_rows(self, values_only):
                return iter([HEADER, participant(0)])

        class Book:
            worksheets = [Sheet("一"), Sheet("二")]
            sheetnames = ["一", "二"]
            closed = False

            def close(self):
                self.closed = True

        book = Book()
        with patch("openpyxl.load_workbook", return_value=book) as loader:
            with self.assertRaises(ValueError):
                audit.read_report(Path("/synthetic.xlsx"))
            loader.assert_called_once_with(Path("/synthetic.xlsx"), read_only=True, data_only=False)
        self.assertTrue(book.closed)

    def test_cli_deduplicates_paths_ignores_lock_and_never_writes_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "合成参会明细.xlsx"
            lock = root / "~$合成参会明细.xlsx"
            source.touch()
            lock.touch()
            parsed = audit.parse_rows([HEADER, *[participant(i) for i in range(10)]], str(source), "参会报告", "A")
            output = io.StringIO()
            with patch.object(audit, "read_report", return_value=parsed), contextlib.redirect_stdout(output):
                code = audit.main([directory, str(source)])
            data = json.loads(output.getvalue())
            self.assertEqual(code, 0)
            self.assertEqual(data["discovered_files"], [str(source.resolve())])
            self.assertEqual(data["headcount_failure_count"], 0)
            self.assertFalse(data["screenshots_checked"])
            self.assertEqual(set(root.iterdir()), {source, lock})

    def test_missing_input_returns_error_not_healthy_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = audit.main([directory])
            data = json.loads(output.getvalue())
            self.assertEqual(code, 2)
            self.assertTrue(data["errors"])
            self.assertEqual(data["reports"], [])


if __name__ == "__main__":
    unittest.main()
