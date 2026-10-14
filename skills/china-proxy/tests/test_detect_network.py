"""Offline checks for the read-only TUN detector, using synthetic configuration."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/detect_network.py"
spec = importlib.util.spec_from_file_location("detect_network", SCRIPT)
detector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(detector)


class ClassifyTests(unittest.TestCase):
    def test_tun_requires_core_config_and_tun_route(self):
        self.assertEqual(detector.classify(True, True, True, False), "tun")
        self.assertEqual(detector.classify(False, True, True, False), "tun_configured_unconfirmed")
        self.assertEqual(detector.classify(True, True, False, False), "tun_configured_unconfirmed")

    def test_system_proxy_and_unknown(self):
        self.assertEqual(detector.classify(True, False, False, True), "system_proxy")
        self.assertEqual(detector.classify(True, None, True, False), "unknown")

    def test_tun_interface_names(self):
        self.assertTrue(detector.is_tun_interface("utun4"))
        self.assertTrue(detector.is_tun_interface("Mihomo", "Mihomo Tunnel"))
        self.assertTrue(detector.is_tun_interface("Ethernet 3", "Wintun Userspace Tunnel"))
        self.assertFalse(detector.is_tun_interface("Wi-Fi", "Intel(R) Wi-Fi 6E AX211"))
        self.assertFalse(detector.is_tun_interface(None))


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
                patch.object(detector, "IS_WINDOWS", False), \
                patch.object(detector, "command", side_effect=fake_command), \
                patch.dict(detector.os.environ, {}, clear=True):
            result = detector.detect()
        self.assertEqual(result["mode"], "tun")
        self.assertIs(result["tun_configured"], True)
        self.assertTrue(result["route_probe"]["through_tun"])
        self.assertFalse(result["explicit_proxy_env_present"])

    def run_windows(self, route_json, reg_out):
        verge = self.dir / "Roaming" / detector.VERGE_ID
        verge.mkdir(parents=True)
        (verge / "verge.yaml").write_text("enable_tun_mode: true\nenable_system_proxy: false\n")

        def fake_command(args):
            return {
                "tasklist": '"System","4","Services","0","1,234 K"\r\n'
                            '"verge-mihomo.exe","4321","Console","1","50,000 K"\r\n',
                "reg": reg_out,
                "powershell": route_json,
            }.get(args[0], "")

        env = {"APPDATA": str(self.dir / "Roaming")}
        with patch.object(detector, "IS_WINDOWS", True), \
                patch.object(detector.Path, "home", return_value=self.dir), \
                patch.object(detector, "command", side_effect=fake_command), \
                patch.dict(detector.os.environ, env, clear=True):
            return detector.detect()

    def test_windows_tun_detected_from_tasklist_config_and_route(self):
        result = self.run_windows(
            '{"alias":"Mihomo","status":"Up","description":"Mihomo Tunnel"}',
            "    ProxyEnable    REG_DWORD    0x0\r\n")
        self.assertEqual(result["platform"], "windows")
        self.assertTrue(result["core_running"])
        self.assertEqual(result["mode"], "tun")
        self.assertFalse(result["system_proxy_enabled"])

    def test_windows_physical_route_and_system_proxy(self):
        result = self.run_windows(
            '{"alias":"Wi-Fi","status":"Up","description":"Intel(R) Wi-Fi 6E AX211"}',
            "    ProxyEnable    REG_DWORD    0x1\r\n    ProxyServer    REG_SZ    127.0.0.1:7890\r\n")
        self.assertEqual(result["mode"], "tun_configured_unconfirmed")
        self.assertFalse(result["route_probe"]["through_tun"])
        self.assertTrue(result["system_proxy_enabled"])
        self.assertNotIn("7890", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
