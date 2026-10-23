"""Offline tests: synthetic configuration only; never use live Claude data."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_settings.py"
spec = importlib.util.spec_from_file_location("audit_settings", SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class AuditTests(unittest.TestCase):
    def run_file(self, body):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "SYNTHETIC_ORG_ID.json"
            path.write_text(body, encoding="utf-8")
            before = path.read_bytes()
            result = subprocess.run([sys.executable, str(SCRIPT), "--settings", str(path)],
                                    capture_output=True, text=True, check=False)
            self.assertEqual(path.read_bytes(), before)
            self.assertNotIn(directory, result.stdout + result.stderr)
            self.assertNotIn(path.name, result.stdout + result.stderr)
            return result, json.loads(result.stdout)

    def test_nonempty_flags_including_zero_and_false(self):
        for value in ("1", "0", "false", " "):
            with self.subTest(value=value):
                self.assertTrue(audit.describe("CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC", value)["enabled"])
        self.assertFalse(audit.describe("DISABLE_TELEMETRY", "")["enabled"])

    def test_flags_do_not_share_truth_rules(self):
        self.assertFalse(audit.describe("DISABLE_GROWTHBOOK", "0")["enabled"])
        self.assertFalse(audit.describe("DO_NOT_TRACK", "false")["enabled"])
        self.assertIsNone(audit.describe("DISABLE_GROWTHBOOK", "unexpected")["enabled"])

    def test_reporting_controls_and_feature_fetching_are_distinct(self):
        for key in ("DISABLE_TELEMETRY", "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"):
            for value in ("1", "0", "false"):
                self.assertTrue(audit.describe(key, value)["disables_feature_flag_fetching"])
            self.assertFalse(audit.describe(key, "")["disables_feature_flag_fetching"])
        for key in ("DISABLE_GROWTHBOOK", "DO_NOT_TRACK"):
            self.assertTrue(audit.describe(key, "1")["disables_feature_flag_fetching"])
            self.assertFalse(audit.describe(key, "0")["disables_feature_flag_fetching"])
        for key in ("DISABLE_ERROR_REPORTING", "CLAUDE_CODE_DISABLE_FEEDBACK_SURVEY"):
            self.assertTrue(audit.describe(key, "1")["enabled"])
            self.assertNotIn("disables_feature_flag_fetching", audit.describe(key, "1"))
        self.assertFalse(audit.describe("CLAUDE_CODE_DISABLE_FEEDBACK_SURVEY", "0")["enabled"])

    def test_values_and_identity_are_not_emitted(self):
        sentinel = "SYNTHETIC_SECRET_NEVER_PRINT"
        result, report = self.run_file(json.dumps({
            "env": {"ANTHROPIC_API_KEY": sentinel,
                    "HTTPS_PROXY": f"http://user:{sentinel}@127.0.0.1:12345",
                    "ANTHROPIC_BASE_URL": f"https://example.invalid/{sentinel}",
                    "CLAUDE_CONFIG_DIR": f"/synthetic/{sentinel}",
                    "ANTHROPIC_CUSTOM_HEADERS": sentinel,
                    "IGNORED": sentinel},
            "apiKeyHelper": sentinel, "email": sentinel, "orgId": sentinel,
            "hooks": {"SessionStart": sentinel}}))
        self.assertEqual(result.returncode, 0)
        self.assertNotIn(sentinel, result.stdout + result.stderr)
        rows = {r["key"]: r for r in report["sources"][0]["env"]}
        self.assertTrue(rows["HTTPS_PROXY"]["loopback_host"])
        self.assertTrue(rows["HTTPS_PROXY"]["credential_fields_present"])
        self.assertFalse(rows["ANTHROPIC_BASE_URL"]["official_api_host"])
        self.assertFalse(report["effective_configuration_verified"])

    def test_proxy_bypass_classification(self):
        for value in ("localhost,127.0.0.1,::1", "localhost:12345,[::1]:54321"):
            self.assertFalse(audit.describe("NO_PROXY", value)["non_loopback_or_unrecognized_entries"])
        self.assertTrue(audit.describe("no_proxy", "*")["wildcard_present"])
        self.assertTrue(audit.describe("NO_PROXY", "example.invalid")["non_loopback_or_unrecognized_entries"])

    def test_invalid_json_does_not_echo_input(self):
        result, report = self.run_file('{"SYNTHETIC_SECRET_NEVER_PRINT":')
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("SYNTHETIC_SECRET_NEVER_PRINT", result.stdout + result.stderr)
        self.assertEqual(report["sources"][0]["status"], "invalid_json")

    def test_root_and_env_types(self):
        for body, status in (("[]", "invalid_root"), ('{"env":[]}', "invalid_env")):
            self.assertEqual(self.run_file(body)[1]["sources"][0]["status"], status)
        result, report = self.run_file('{"env":{"DISABLE_TELEMETRY":false}}')
        self.assertEqual(report["sources"][0]["env"][0]["category"], "invalid_env_value")

    def test_missing_and_size_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.json"
            self.assertEqual(audit.audit_file(path, "test")["status"], "missing_or_not_file")
            path.write_bytes(b" " * (audit.MAX_BYTES + 1))
            self.assertEqual(audit.audit_file(path, "test")["status"], "too_large")

    def test_process_env_requires_explicit_flag(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text("{}", encoding="utf-8")
            child_env = {"ANTHROPIC_API_KEY": "SYNTHETIC_ENV_SECRET"}
            a = subprocess.run([sys.executable, str(SCRIPT), "--settings", str(path)],
                               env=child_env, capture_output=True, text=True)
            self.assertNotIn("ANTHROPIC_API_KEY", a.stdout)
            b = subprocess.run([sys.executable, str(SCRIPT), "--include-process-env"],
                               env=child_env, capture_output=True, text=True)
            self.assertIn("ANTHROPIC_API_KEY", b.stdout)
            self.assertNotIn("SYNTHETIC_ENV_SECRET", b.stdout + b.stderr)

    def test_malformed_urls_and_key_names_are_safe(self):
        self.assertFalse(audit.describe("HTTPS_PROXY", "http://[SYNTHETIC_SECRET")["valid_url"])
        self.assertEqual(audit.audit_env({"ANTHROPIC_BAD\nSYNTHETIC_SECRET": "x"}), [])


if __name__ == "__main__":
    unittest.main()
