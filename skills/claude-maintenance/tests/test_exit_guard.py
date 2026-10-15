"""Offline tests for exit_guard.py with synthetic configs and local sockets only."""
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "exit_guard.py"
spec = importlib.util.spec_from_file_location("exit_guard", SCRIPT)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

EXPECTED = "192.0.2.10"
OTHER = "198.51.100.20"


def make_config(root, **extra):
    data = {"expected_ip": EXPECTED, "listen_port": 0, "upstream_port": 0,
            "exit_node": "fixed-exit", "clash_config": str(root / "clash.yaml"),
            "profile": str(root / "Dedicated Profile"), "state_dir": str(root / "state"),
            "chrome": str(root / "Google Chrome")}
    data.update(extra)
    path = root / "config.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return guard.load_config(path)


def ok(ip):
    return {"name": "probe", "ok": True, "ip": ip}


FAIL = {"name": "probe", "ok": False, "reason": "timeout"}
CHAIN_OK = lambda config: {"ok": True, "front": "front-node"}


class Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = make_config(self.root)


class ConfigTests(Base):
    def test_defaults_and_derived_cli_settings(self):
        self.assertEqual(self.config["check_interval_seconds"], 20)
        config = make_config(self.root, listen_port=17890)
        env = guard.cli_settings(config)["env"]
        self.assertEqual(env["HTTPS_PROXY"], "http://127.0.0.1:17890")
        self.assertEqual(env["https_proxy"], env["ALL_PROXY"])
        self.assertEqual(env["NO_PROXY"], "localhost,127.0.0.1,::1")

    def test_missing_keys_and_bad_ip_rejected(self):
        path = self.root / "bad.json"
        path.write_text(json.dumps({"expected_ip": EXPECTED}), encoding="utf-8")
        with self.assertRaises(ValueError):
            guard.load_config(path)
        data = json.loads((self.root / "config.json").read_text(encoding="utf-8"))
        data["expected_ip"] = "not-an-ip"
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(ValueError):
            guard.load_config(path)


class VerifyTests(Base):
    def run_verify(self, *results):
        queue = list(results)
        return guard.verify(self.config, probe_fn=lambda *_: queue.pop(0), chain_fn=CHAIN_OK)

    def test_both_expected_allows(self):
        self.assertTrue(self.run_verify(ok(EXPECTED), ok(EXPECTED))["ok"])

    def test_any_unexpected_ip_blocks(self):
        result = self.run_verify(ok(EXPECTED), ok(OTHER))
        self.assertFalse(result["ok"])
        self.assertIn(OTHER, result["reason"])

    def test_both_unconfirmed_blocks(self):
        self.assertFalse(self.run_verify(FAIL, FAIL)["ok"])

    def test_one_confirmed_one_failed_allows_and_reports_degraded(self):
        result = self.run_verify(ok(EXPECTED), FAIL)
        self.assertTrue(result["ok"])
        self.assertIn("降级", result["reason"])

    def test_chain_failure_blocks_without_probing(self):
        result = guard.verify(self.config, probe_fn=lambda *_: self.fail("probed"),
                              chain_fn=lambda c: {"ok": False, "reason": "chain"})
        self.assertFalse(result["ok"])


@unittest.skipUnless(importlib.util.find_spec("yaml"), "PyYAML not installed")
class ChainTests(Base):
    def write(self, front="front-node", listener_proxy="fixed-exit"):
        import yaml
        data = {"proxies": [{"name": "front-node", "type": "ss"},
                            {"name": "fixed-exit", "type": "socks5", "dialer-proxy": front}],
                "proxy-groups": [{"name": "Proxy", "type": "select", "proxies": ["front-node"]}],
                "listeners": [{"name": "dedicated", "type": "http", "port": 0, "proxy": listener_proxy}]}
        Path(self.config["clash_config"]).write_text(yaml.safe_dump(data), encoding="utf-8")

    def test_bound_listener_with_real_front_passes(self):
        self.write()
        self.assertEqual(guard.chain_check(self.config), {"ok": True, "front": "front-node"})

    def test_direct_front_or_wrong_listener_fails(self):
        for kwargs in ({"front": "DIRECT"}, {"front": None}, {"listener_proxy": "Proxy"}):
            with self.subTest(**{k: str(v) for k, v in kwargs.items()}):
                self.write(**kwargs)
                self.assertFalse(guard.chain_check(self.config)["ok"])


class HealthTests(Base):
    def test_blocking_closes_registered_pairs_and_expires(self):
        now = [100.0]
        health = guard.Health(self.config, verifier=lambda c: {"ok": True, "reason": "ok", "probes": []},
                              clock=lambda: now[0])
        self.assertTrue(health.check(force=True))
        a, b = socket.socketpair()
        self.assertTrue(health.register((a, b)))
        health.publish({"ok": False, "reason": "changed", "probes": []})
        self.assertEqual(a.fileno(), -1)
        self.assertFalse(health.is_allowed())
        health.publish({"ok": True, "reason": "ok", "probes": []})
        now[0] += self.config["max_verified_age_seconds"] + 1
        self.assertFalse(health.is_allowed())
        self.assertIn("过期", health.status()["reason"])

    def test_verifier_exception_blocks(self):
        def boom(_):
            raise RuntimeError("x")
        health = guard.Health(self.config, verifier=boom)
        self.assertFalse(health.check(force=True))


class GatewayTests(Base):
    def start_upstream(self):
        server = socket.socket()
        server.bind(("127.0.0.1", 0))
        server.listen()
        self.addCleanup(server.close)
        seen = []

        def serve():
            try:
                conn, _ = server.accept()
            except OSError:  # Tests that never reach the upstream close it unaccepted.
                return
            with conn:
                data = b""
                while b"\r\n\r\n" not in data:
                    data += conn.recv(4096)
                seen.append(data)
                conn.sendall(b"HTTP/1.1 200 Connection established\r\n\r\ntunnel-ok")
        threading.Thread(target=serve, daemon=True).start()
        return server.getsockname()[1], seen

    def start_gateway(self, allowed=True):
        port, seen = self.start_upstream()
        self.config["upstream_port"] = port
        health = guard.Health(self.config, verifier=lambda c: {"ok": allowed, "reason": "test", "probes": []})
        health.check(force=True)
        gateway = guard.Gateway(("127.0.0.1", 0), health)
        self.config["listen_port"] = gateway.server_address[1]
        threading.Thread(target=gateway.serve_forever, daemon=True).start()
        self.addCleanup(gateway.server_close)
        self.addCleanup(gateway.shutdown)
        return gateway.server_address[1], seen

    def request(self, port, payload):
        with socket.create_connection(("127.0.0.1", port), timeout=5) as client:
            client.sendall(payload)
            data = b""
            while True:
                chunk = client.recv(4096)
                if not chunk:
                    break
                data += chunk
                if b"tunnel-ok" in data:
                    break
            return data

    def test_connect_is_forwarded_only_to_upstream(self):
        port, seen = self.start_gateway()
        data = self.request(port, b"CONNECT claude.ai:443 HTTP/1.1\r\nHost: claude.ai:443\r\n\r\n")
        self.assertIn(b"tunnel-ok", data)
        self.assertTrue(seen[0].startswith(b"CONNECT claude.ai:443"))

    def test_blocked_guard_returns_503(self):
        port, seen = self.start_gateway(allowed=False)
        data = self.request(port, b"CONNECT claude.ai:443 HTTP/1.1\r\n\r\n")
        self.assertTrue(data.startswith(b"HTTP/1.1 503"))
        self.assertEqual(seen, [])

    def test_status_json_and_read_status(self):
        port, _ = self.start_gateway()
        data = guard.read_status(self.config)
        self.assertEqual(data["service"], "claude-exit-guard")
        self.assertTrue(data["ok"])
        page = self.request(port, b"GET /__claude_guard_status HTTP/1.1\r\n\r\n")
        self.assertIn("指定出口已确认".encode("utf-8"), page)

    def test_non_proxy_request_rejected(self):
        port, _ = self.start_gateway()
        self.assertTrue(self.request(port, b"GET /other HTTP/1.1\r\n\r\n").startswith(b"HTTP/1.1 400"))


class LeaseAndProcessTests(Base):
    def test_pid_alive(self):
        self.assertTrue(guard.pid_alive(os.getpid()))
        child = subprocess.Popen([sys.executable, "-c", "pass"])
        child.wait()
        self.assertFalse(guard.pid_alive(child.pid))
        self.assertFalse(guard.pid_alive(0))

    def test_dead_leases_removed_live_kept(self):
        state = Path(self.config["state_dir"])
        state.mkdir()
        (state / "cli-1001.lease").write_text("1001")
        (state / "cli-1002.lease").write_text("1002")
        stale = state / "cli-1003.lease"
        stale.write_text("1003")
        os.utime(stale, (0, 0))
        alive = {1002, 1003}.__contains__
        self.assertTrue(guard.cli_running(state, alive=alive))
        self.assertEqual(sorted(p.name for p in state.iterdir()), ["cli-1002.lease", "cli-1003.lease"])
        (state / "cli-1002.lease").unlink()
        self.assertFalse(guard.cli_running(state, alive=alive))

    def test_dedicated_browser_lines_skip_children_and_other_profiles(self):
        chrome, profile = self.config["chrome"], self.config["profile"]
        lines = ['{} --user-data-dir={} --proxy-server=http://127.0.0.1:1'.format(chrome, profile),
                 '{} --type=renderer --user-data-dir={}'.format(chrome, profile),
                 '{} --user-data-dir=/other/profile'.format(chrome)]
        self.assertEqual(guard.dedicated_browser_lines(self.config, lines), lines[:1])

    def test_windows_process_listing_opens_no_console_window(self):
        from unittest import mock
        done = mock.Mock(stdout="chrome.exe --user-data-dir=x\n")
        with mock.patch.object(guard, "IS_WINDOWS", True), \
                mock.patch.object(guard.subprocess, "run", return_value=done) as run:
            self.assertEqual(guard.process_command_lines(), ["chrome.exe --user-data-dir=x"])
        self.assertEqual(run.call_args.args[0][0], "powershell")
        self.assertEqual(run.call_args.kwargs["creationflags"], 0x08000000)

    def test_browser_watch_caches(self):
        calls = []
        watch = guard.BrowserWatch(self.config, ttl=60, lister=lambda: calls.append(1) or [])
        self.assertFalse(watch.running())
        self.assertFalse(watch.running())
        self.assertEqual(len(calls), 1)


class CliAndBrowserTests(Base):
    def test_cli_environment_strips_api_routing_and_sets_guard(self):
        base = {"ANTHROPIC_API_KEY": "SYNTHETIC", "ANTHROPIC_BASE_URL": "https://gateway.invalid",
                "CLAUDE_CODE_USE_BEDROCK": "1", "PATH": "/bin", "HTTPS_PROXY": "http://other:1"}
        env = guard.cli_environment(self.config, base, "/helper")
        self.assertNotIn("ANTHROPIC_API_KEY", env)
        self.assertNotIn("ANTHROPIC_BASE_URL", env)
        self.assertNotIn("CLAUDE_CODE_USE_BEDROCK", env)
        self.assertEqual(env["HTTPS_PROXY"], guard.guard_url(self.config))
        self.assertEqual(env["BROWSER"], "/helper")
        self.assertEqual(env["PATH"], "/bin")
        kept = guard.cli_environment(dict(self.config, strip_api_env=False), base, "")
        self.assertEqual(kept["ANTHROPIC_API_KEY"], "SYNTHETIC")
        self.assertNotIn("BROWSER", kept)

    def test_cli_refuses_settings_override(self):
        self.assertEqual(guard.run_cli(dict(self.config, claude_bin="x"), self.root / "config.json",
                                       ["--settings", "other.json"]), 2)

    def test_chrome_command_flags_and_urls(self):
        args = guard.chrome_command(self.config, ["https://claude.ai/oauth?x=1&y=2"])
        self.assertEqual(args[0], self.config["chrome"])
        self.assertIn("--user-data-dir=" + self.config["profile"], args)
        self.assertIn("--proxy-server=" + guard.guard_url(self.config), args)
        self.assertIn("--proxy-bypass-list=<-loopback>;localhost;127.0.0.1;[::1]", args)
        self.assertIn("--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1, EXCLUDE localhost", args)
        for flag in ("--disable-quic", "--disable-background-networking", "--disable-sync",
                     "--force-webrtc-ip-handling-policy=disable_non_proxied_udp"):
            self.assertIn(flag, args)
        self.assertEqual(args[-1], "https://claude.ai/oauth?x=1&y=2")
        self.assertTrue(guard.chrome_command(self.config)[-1].endswith("/__claude_guard_status"))

    def test_open_url_rejects_non_http(self):
        self.assertEqual(guard.open_url(self.config, ["file:///etc/passwd"]), 2)
        self.assertEqual(guard.open_url(self.config, []), 2)


class WrapperTests(unittest.TestCase):
    def test_posix_wrappers_quote_paths(self):
        files = guard.wrapper_files("/cfg dir/it's.json", script="/s/exit_guard.py", python="/py", windows=False)
        self.assertEqual(set(files), {"claude-safe", "claude-oauth-browser"})
        self.assertIn("'/cfg dir/it'\\''s.json' cli \"$@\"", files["claude-safe"])
        self.assertTrue(files["claude-oauth-browser"].startswith("#!/bin/sh\nexec "))

    def test_windows_wrappers_are_cmd_files(self):
        files = guard.wrapper_files(r"C:\Users\u\cfg.json", script=r"C:\s\exit_guard.py",
                                    python=r"C:\Py\pythonw.exe", windows=True)
        self.assertEqual(set(files), {"claude-safe.cmd", "claude-oauth-browser.cmd"})
        self.assertIn(r'"C:\Py\pythonw.exe" "C:\s\exit_guard.py" --config "C:\Users\u\cfg.json" open-url %*',
                      files["claude-oauth-browser.cmd"])
        self.assertIn("\r\n", files["claude-safe.cmd"])

    @unittest.skipIf(guard.IS_WINDOWS, "POSIX wrapper execution")
    def test_posix_wrapper_runs_and_passes_arguments(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            recorder = root / "record.py"
            recorder.write_text("import json,sys; print(json.dumps(sys.argv[1:]))", encoding="utf-8")
            files = guard.wrapper_files(root / "c.json", script=recorder, python=sys.executable, windows=False)
            wrapper = root / "claude-oauth-browser"
            wrapper.write_text(files["claude-oauth-browser"], encoding="utf-8")
            wrapper.chmod(0o700)
            url = "http://localhost:5/callback?code=TEST_ONLY&state=TEST_ONLY"
            out = subprocess.run([str(wrapper), url], capture_output=True, text=True, timeout=10)
            self.assertEqual(json.loads(out.stdout), ["--config", str(root / "c.json"), "open-url", url])


if __name__ == "__main__":
    unittest.main()
