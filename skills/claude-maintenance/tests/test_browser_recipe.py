"""Exercise the documented launcher with a recorder, never with real Chrome."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BrowserRecipeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        text = (ROOT / "references" / "browser-setup.md").read_text(encoding="utf-8")
        blocks = re.findall(r"```bash\n(.*?)\n```", text, re.S)
        self.assertEqual(len(blocks), 1)
        self.launcher = self.root / "launch.sh"
        self.launcher.write_text(blocks[0] + "\n", encoding="utf-8")
        self.chrome = self.root / "Mock Chrome"
        self.chrome.write_text(
            '#!/bin/sh\nexec "$TEST_PYTHON" -c '
            "'import json,sys; print(json.dumps(sys.argv[1:]))' \"$@\"\n",
            encoding="utf-8")
        self.chrome.chmod(0o700)
        self.env = {"PATH": os.defpath, "TEST_PYTHON": sys.executable,
                    "CLAUDE_CHROME_BIN": str(self.chrome),
                    "CLAUDE_CHROME_PROFILE": str(self.root / "Dedicated Profile"),
                    "CLAUDE_CHROME_PROXY": "http://127.0.0.1:12345"}

    def run_launcher(self, args=(), env=None):
        return subprocess.run(["/bin/sh", str(self.launcher), *args],
                              env=self.env if env is None else env,
                              capture_output=True, text=True, timeout=5)

    def test_shell_syntax(self):
        result = subprocess.run(["/bin/sh", "-n", str(self.launcher)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_profile_and_proxy_remain_single_arguments(self):
        result = self.run_launcher()
        self.assertEqual(result.returncode, 0, result.stderr)
        args = json.loads(result.stdout)
        self.assertIn("--user-data-dir=" + self.env["CLAUDE_CHROME_PROFILE"], args)
        self.assertIn("--proxy-server=" + self.env["CLAUDE_CHROME_PROXY"], args)
        self.assertEqual(sum(x.startswith("--proxy-server=") for x in args), 1)
        self.assertEqual(args[-1], "https://claude.ai/")
        self.assertFalse((self.root / "Dedicated Profile").exists())

    def test_literal_loopback_and_udp_flags(self):
        result = self.run_launcher()
        args = json.loads(result.stdout)
        self.assertIn("--proxy-bypass-list=<-loopback>;localhost;127.0.0.1;[::1]", args)
        self.assertIn("--disable-quic", args)
        self.assertIn("--force-webrtc-ip-handling-policy=disable_non_proxied_udp", args)
        self.assertIn("--no-default-browser-check", args)

    def test_synthetic_oauth_url_is_not_split_by_shell(self):
        url = "http://localhost:54321/callback?code=TEST_ONLY&state=TEST_ONLY"
        result = self.run_launcher([url])
        self.assertEqual(result.returncode, 0, result.stderr)
        args = json.loads(result.stdout)
        self.assertEqual(args[-1], url)
        self.assertNotIn("https://claude.ai/", args)

    def test_missing_parameters_stop_before_recorder(self):
        for key in ("CLAUDE_CHROME_BIN", "CLAUDE_CHROME_PROFILE", "CLAUDE_CHROME_PROXY"):
            with self.subTest(key=key):
                env = dict(self.env)
                env.pop(key)
                result = self.run_launcher(env=env)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
