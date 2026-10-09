"""Offline configuration and credential privacy checks, using synthetic tokens."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/netdisk_mcp.py"
spec = importlib.util.spec_from_file_location("netdisk_mcp", SCRIPT)
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)


class ConnectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.url = "https://mcp-pan.baidu.com/sse?access_token=synthetic-private-token"

    def write_config(self, name, **changes):
        path = self.home / name / (".mcp.json" if name == ".codebuddy" else "mcp.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        server = {"url": self.url, "type": "sse", **changes}
        path.write_text(json.dumps({"mcpServers": {"baidu-netdisk": server}}))
        return path

    def test_default_prefers_enabled_workbuddy(self):
        expected = self.write_config(".workbuddy")
        self.write_config(".codebuddy", url=self.url + "-other-account")
        with patch.object(client.Path, "home", return_value=self.home):
            self.assertEqual(client.load_connection(), (expected, self.url))

    def test_disabled_workbuddy_uses_codebuddy(self):
        self.write_config(".workbuddy", disabled=True)
        expected = self.write_config(".codebuddy")
        with patch.object(client.Path, "home", return_value=self.home):
            self.assertEqual(client.load_connection(), (expected, self.url))

    def test_explicit_missing_config_does_not_fallback(self):
        self.write_config(".workbuddy")
        with self.assertRaises(client.InputError):
            client.load_connection(self.home / "missing.json")

    def test_rejects_non_official_endpoint_without_leaking_token(self):
        path = self.write_config(".workbuddy", url=self.url.replace("mcp-pan.baidu.com", "example.org"))
        with self.assertRaises(client.InputError) as caught:
            client.load_connection(path)
        self.assertNotIn("synthetic-private-token", str(caught.exception))

    def test_output_and_nested_errors_do_not_expose_credentials(self):
        text = client.redact(json.dumps({"url": self.url, "token": "synthetic-private-token"}), self.url)
        self.assertNotIn("synthetic-private-token", text)
        class NestedError(Exception):
            exceptions = (ValueError(self.url), RuntimeError(self.url))
        self.assertNotIn("synthetic-private-token", client.error_summary(NestedError()))

    def test_arguments_must_be_json_object(self):
        path = self.home / "args.json"
        path.write_text('["not", "an", "object"]')
        with self.assertRaises(client.InputError):
            client.read_arguments(str(path))
        path.write_text('{"path": "/项目"}')
        self.assertEqual(client.read_arguments(str(path)), {"path": "/项目"})


if __name__ == "__main__":
    unittest.main()
