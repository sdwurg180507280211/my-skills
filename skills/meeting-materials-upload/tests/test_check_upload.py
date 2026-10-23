from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import quote

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_upload.py"
SPEC = importlib.util.spec_from_file_location("check_upload", SCRIPT)
checks = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checks)


class BatchChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        content = b"synthetic image placeholder, not actual meeting evidence"
        (self.base / "sample.v2.jpg").write_bytes(content)
        self.item = {
            "batchId": "run-example", "projectId": "PROJECT_EXAMPLE",
            "recordId": "MEETING_EXAMPLE", "path": "sample.v2.jpg",
            "name": "sample.v2.jpg", "category": "C", "timestampMs": 1001,
            "objectKey": "sample.v2_1001_MEETING_EXAMPLE.jpg",
            "contentType": "image/jpeg", "sha256": hashlib.sha256(content).hexdigest(),
        }
        self.batch = {
            "batchId": "run-example", "projectId": "PROJECT_EXAMPLE",
            "recordIds": ["MEETING_EXAMPLE"], "files": [self.item],
        }

    def test_correct_batch_and_no_source_mutation(self):
        before = (self.base / "sample.v2.jpg").read_bytes()
        self.assertTrue(checks.validate_batch(self.batch, self.base)["ok"])
        self.assertEqual(before, (self.base / "sample.v2.jpg").read_bytes())

    def test_object_key_removes_only_last_extension(self):
        self.assertEqual(checks.make_object_key("sample.v2.jpg", 1001, "MEETING_EXAMPLE"),
                         self.item["objectKey"])
        for name in ("parent/sample.jpg", "parent\\sample.jpg", "sample.gif"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                checks.make_object_key(name, 1001, "MEETING_EXAMPLE")

    def test_cross_batch_project_record_and_key_rejected(self):
        for field, value in (
            ("batchId", "old-run"), ("projectId", "OTHER_PROJECT"),
            ("recordId", "OTHER_MEETING"),
            ("objectKey", "sample.v2_999_OLD_MEETING.jpg"),
            ("timestampMs", True),
        ):
            with self.subTest(field=field):
                batch = copy.deepcopy(self.batch)
                batch["files"][0][field] = value
                self.assertFalse(checks.validate_batch(batch, self.base)["ok"])

    def test_category_requires_full_parenthetical_label(self):
        batch = copy.deepcopy(self.batch)
        batch["files"][0]["documentType"] = "付费服务提供者照片/截屏"
        self.assertFalse(checks.validate_batch(batch, self.base)["ok"])
        batch["files"][0]["documentType"] = checks.CATEGORIES["C"]
        self.assertTrue(checks.validate_batch(batch, self.base)["ok"])

    def test_source_hash_content_type_and_nonempty_source(self):
        batch = copy.deepcopy(self.batch)
        batch["files"][0]["contentType"] = "image/png"
        self.assertFalse(checks.validate_batch(batch, self.base)["ok"])
        (self.base / "sample.v2.jpg").write_bytes(b"new version")
        self.assertFalse(checks.validate_batch(self.batch, self.base)["ok"])
        (self.base / "sample.v2.jpg").write_bytes(b"")
        self.assertFalse(checks.validate_batch(self.batch, self.base)["ok"])

    def test_duplicate_object_key_rejected(self):
        batch = copy.deepcopy(self.batch)
        batch["files"].append(copy.deepcopy(self.item))
        self.assertFalse(checks.validate_batch(batch, self.base)["ok"])

    def test_presigned_url_exact_path_and_host(self):
        key = "讲者截图_1001_MEETING_EXAMPLE.jpg"
        url = "https://storage.example.test/op2-event/" + quote(key) + "?signature=synthetic"
        self.assertTrue(checks.url_matches(url, key, "op2-event", "storage.example.test"))
        for bad in (
            "https://storage.example.test/wrong?key=" + quote(key),
            url.replace("op2-event/", "op2-event/extra/"),
            url.replace(".jpg?", ".jpg.old?"),
            url.replace("https:", "http:"),
            url.replace("storage.example.test", "other.example.test"),
            url + "#fragment",
        ):
            with self.subTest(url=bad):
                self.assertFalse(checks.url_matches(bad, key, "op2-event", "storage.example.test"))

    def test_batch_url_requires_captured_host(self):
        batch = copy.deepcopy(self.batch)
        batch["files"][0]["putUrl"] = (
            "https://storage.example.test/op2-event/" + self.item["objectKey"]
        )
        self.assertFalse(checks.validate_batch(batch, self.base)["ok"])
        batch["storageHost"] = "storage.example.test"
        self.assertTrue(checks.validate_batch(batch, self.base)["ok"])

    def test_cli_reports_correct_exit_code(self):
        manifest = self.base / "batch.json"
        manifest.write_text(json.dumps(self.batch), encoding="utf-8")
        good = subprocess.run([sys.executable, "-B", str(SCRIPT), "batch", str(manifest)],
                              capture_output=True, text=True)
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertTrue(json.loads(good.stdout)["ok"])
        self.batch["files"][0]["recordId"] = "OTHER_MEETING"
        manifest.write_text(json.dumps(self.batch), encoding="utf-8")
        bad = subprocess.run([sys.executable, "-B", str(SCRIPT), "batch", str(manifest)],
                             capture_output=True, text=True)
        self.assertEqual(bad.returncode, 2)
        self.assertFalse(json.loads(bad.stdout)["ok"])


class LiveListChecks(unittest.TestCase):
    def row(self, rid, status, missing=None):
        row = {"meetingId": rid, "supportFileCheckStatus": status,
               "meetingStatus": "已提供支持文件"}
        row.update({field: "✔️" for field in checks.UPLOAD_FIELDS})
        if missing:
            row[missing] = ""
        return row

    def test_project_total_is_separate_from_task_targets(self):
        data = {"state": "SUCCESS", "rows": [
            self.row("M1", "未审核所有支持文件"),
            self.row("M2", "审批完成", "signTable"),
            self.row("OTHER", "已驳回"),
        ]}
        result = checks.verify_targets(["M1", "M2", "MISSING"], data)
        self.assertEqual(result["projectRowCount"], 3)
        self.assertEqual(result["targetPresentCount"], 2)
        self.assertEqual(result["targetRegistrationCompleteCount"], 1)
        self.assertEqual(result["missingCurrentTargetIds"], ["MISSING"])
        self.assertEqual(result["projectApprovalStatuses"]["已驳回"], 1)
        self.assertNotIn("已驳回", result["targetApprovalStatuses"])
        self.assertEqual(result["incompleteTargetRows"][0]["missingFields"], ["signTable"])
        self.assertFalse(result["ok"])
        self.assertIn("evidence separately", result["meaning"])

    def test_supported_aura_wrapper(self):
        row = self.row("M1", "审批中")
        response = {"actions": [{"state": "SUCCESS", "returnValue": {"returnValue": [row]}}]}
        result = checks.verify_targets(["M1"], response)
        self.assertTrue(result["ok"])
        self.assertEqual(result["projectApprovalStatuses"], {"审批中": 1})

    def test_failed_or_unstructured_responses_are_not_success(self):
        for response in (
            {"state": "ERROR", "rows": []},
            {"actions": [{"state": "ERROR", "returnValue": []}]},
            {"state": "SUCCESS", "rows": None},
            {"actions": []},
            {"state": "SUCCESS", "rows": [{}]},
        ):
            with self.subTest(response=response), self.assertRaises(ValueError):
                checks.verify_targets(["M1"], response)

    def test_duplicate_live_ids_and_targets(self):
        row = self.row("M1", "审批完成")
        data = {"state": "SUCCESS", "rows": [row, row]}
        result = checks.verify_targets(["M1"], data)
        self.assertFalse(result["ok"])
        self.assertEqual(result["duplicateMeetingIds"], ["M1"])
        with self.assertRaises(ValueError):
            checks.verify_targets(["M1", "M1"], data)

    def test_empty_success_list_is_missing_not_deleted(self):
        result = checks.verify_targets(["M1"], {"state": "SUCCESS", "rows": []})
        self.assertFalse(result["ok"])
        self.assertEqual(result["missingCurrentTargetIds"], ["M1"])
        self.assertNotIn("deleted", json.dumps(result))

    def test_booleans_do_not_silently_replace_page_tick_values(self):
        row = self.row("M1", None)
        row["venuePhoto"] = True
        result = checks.verify_targets(["M1"], {"state": "SUCCESS", "rows": [row]})
        self.assertFalse(result["ok"])
        self.assertEqual(result["projectApprovalStatuses"], {"UNKNOWN": 1})


if __name__ == "__main__":
    unittest.main()
