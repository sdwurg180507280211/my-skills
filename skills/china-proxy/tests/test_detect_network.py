"""Offline checks for the read-only TUN detector, using synthetic configuration."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/detect_network.py"
spec = importlib.util.spec_from_file_location("detect_network", SCRIPT)
detector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(detector)


class ClassifyTests(unittest.TestCase):
    def test_tun_requires_core_config_and_utun_route(self):
        self.assertEqual(detector.classify(True, True, "utun4", False), "tun")
        self.assertEqual(detector.classify(False, True, "utun4", False), "tun_configured_unconfirmed")
        self.assertEqual(detector.classify(True, True, "en0", False), "tun_configured_unconfirmed")

    def test_system_proxy_and_unknown(self):
        self.assertEqual(detector.classify(True, False, "en0", True), "system_proxy")
        self.assertEqual(detector.classify(True, None, "utun4", False), "unknown")


class ConfigFlagTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)

    def test_reads_only_expected_booleans(self):
        path = self.dir / "clash-verge.yaml"
        path.write_text(
            "proxies:\n  - name: synthetic\n    password: synthetic-secret\n"
            "tun:\n  enable: true\n  auto-route: false\n"
            "enable_system_proxy: false\n"
        )
        flags = detector.config_flags(path)
        self.assertIs(flags["tun_config_enabled"], True)
        self.assertIs(flags["auto_route"], False)
        self.assertIs(flags["system_proxy_enabled"], False)
        self.assertNotIn("synthetic-secret", repr(flags))

    def test_missing_file_returns_none(self):
        self.assertIsNone(detector.config_flags(self.dir / "absent.yaml"))

    def test_detect_prefers_generated_config_over_stale_base(self):
        verge = self.dir / "Library/Application Support/io.github.clash-verge-rev.clash-verge-rev"
        verge.mkdir(parents=True)
        (verge / "config.yaml").write_text("tun:\n  enable: false\n")
        (verge / "clash-verge.yaml").write_text("tun:\n  enable: true\n")

        def fake_command(args):
            return {
                "ps": "/Applications/Clash Verge.app/Contents/MacOS/verge-mihomo\n",
                "route": "interface: utun7\n",
                "ifconfig": "utun7: flags=8051<UP,POINTOPOINT,RUNNING,MULTICAST> mtu 9000\n",
            }.get(args[0], "")

        with patch.object(detector.Path, "home", return_value=self.dir), \
                patch.object(detector, "command", side_effect=fake_command), \
                patch.dict(detector.os.environ, {}, clear=True):
            result = detector.detect()
        self.assertEqual(result["mode"], "tun")
        self.assertIs(result["tun_configured"], True)
        self.assertFalse(result["explicit_proxy_env_present"])


if __name__ == "__main__":
    unittest.main()
