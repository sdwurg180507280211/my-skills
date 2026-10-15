#!/usr/bin/env python3
"""Fixed-exit guard for a dedicated Claude Chrome profile and Claude Code CLI.

One local HTTP proxy forwards every request to a Clash listener that is bound
to a fixed exit node. It verifies the public exit IP through that listener and
closes all connections when the IP differs or cannot be confirmed. It never
connects to a destination directly, never edits Clash and never selects nodes.

Subcommands:
  browser          start or reuse the guard, then open the dedicated Chrome
  serve            run the guard only (started by the CLI entry when needed)
  cli [ARGS...]    run official Claude Code through the guard
  open-url URL...  open login URLs in the dedicated Chrome (BROWSER helper)
  status           print the running guard's status JSON
  install-wrappers --bin-dir DIR
                   write claude-safe and OAuth helper wrappers for this OS

Runs on macOS, Linux and Windows with Python 3.9+; chain checks need PyYAML.
"""
import argparse
import html
import ipaddress
import json
import os
from pathlib import Path
import select
import signal
import socket
import socketserver
import subprocess
import sys
import threading
import time
import urllib.request
from urllib.parse import urlsplit

IS_WINDOWS = os.name == "nt"
CREATE_NO_WINDOW = 0x08000000  # subprocess.CREATE_NO_WINDOW, defined on Windows only
SERVICE = "claude-exit-guard"
VERSION = 3
STATUS_PATH = "/__claude_guard_status"
LOOPBACK_NO_PROXY = "localhost,127.0.0.1,::1"
PROXY_KEYS = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy")
PROVIDER_KEYS = ("CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY")
PROBES = (("IPify", "https://api.ipify.org"),
          ("Cloudflare", "https://www.cloudflare.com/cdn-cgi/trace"))
REQUIRED = ("expected_ip", "listen_port", "upstream_port", "exit_node", "clash_config",
            "profile", "state_dir", "chrome")
DEFAULTS = {
    "listen_host": "127.0.0.1",
    "upstream_host": "127.0.0.1",
    "claude_bin": "",
    "check_interval_seconds": 20,
    "new_connection_check_age_seconds": 10,
    "max_verified_age_seconds": 40,
    "probe_timeout_seconds": 8,
    "idle_exit_seconds": 60,
    "strip_api_env": True,
    "chrome_lang": "en-US",
}


# ---------------------------------------------------------------- config

def default_config_path():
    if IS_WINDOWS:
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "Claude Dedicated Guard" / "config.json"


def load_config(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    missing = [key for key in REQUIRED if key not in data]
    if missing:
        raise ValueError("配置缺少：" + ", ".join(missing))
    config = dict(DEFAULTS, **data)
    config["expected_ip"] = str(ipaddress.ip_address(config["expected_ip"]))
    for key in ("listen_port", "upstream_port"):
        config[key] = int(config[key])
    return config


def guard_url(config):
    return "http://{}:{}".format(config["listen_host"], config["listen_port"])


def cli_settings(config):
    """Proxy env for the CLI, derived from the guard address so it lives in one place."""
    env = {key: guard_url(config) for key in PROXY_KEYS}
    env.update(NO_PROXY=LOOPBACK_NO_PROXY, no_proxy=LOOPBACK_NO_PROXY)
    return {"env": env}


# ---------------------------------------------------------------- platform

def pid_alive(pid):
    if pid <= 0:
        return False
    if IS_WINDOWS:
        # os.kill(pid, 0) would terminate the process on Windows; query it instead.
        import ctypes
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return ctypes.get_last_error() == 5  # access denied: exists, owned by someone else
        try:
            code = ctypes.c_ulong()
            return bool(kernel32.GetExitCodeProcess(handle, ctypes.byref(code))) and code.value == 259
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def try_lock(path):
    """Return an open handle holding an exclusive lock, or None when another guard owns it."""
    handle = open(path, "a+")
    try:
        if IS_WINDOWS:
            import msvcrt
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return None
    return handle


def alert(message):
    title = "Claude 专用"
    try:
        if IS_WINDOWS:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, message, title, 0x10)
            return
        if sys.platform == "darwin":
            script = 'on run argv\ndisplay alert "{}" message (item 1 of argv) as critical\nend run'.format(title)
            subprocess.run(["/usr/bin/osascript", "-e", script, message], check=False, timeout=120)
            return
    except (OSError, subprocess.SubprocessError):
        pass
    print(title + "：" + message, file=sys.stderr)


def spawn_detached(command):
    kwargs = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if IS_WINDOWS:
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    return subprocess.Popen(command, **kwargs)


def process_command_lines():
    if IS_WINDOWS:
        script = ("Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | "
                  "ForEach-Object { $_.CommandLine }")
        command = ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]
    else:
        command = ["ps", "-axo", "args="] if sys.platform == "darwin" else ["ps", "-eo", "args="]
    try:
        # Under pythonw every console child (powershell) would flash its own window.
        flags = {"creationflags": CREATE_NO_WINDOW} if IS_WINDOWS else {}
        result = subprocess.run(command, capture_output=True, text=True, timeout=15, **flags)
    except (OSError, subprocess.SubprocessError):
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def dedicated_browser_lines(config, lines):
    """Main Chrome processes of the dedicated profile (child processes carry --type=)."""
    fold = str.lower if IS_WINDOWS else str
    profile = fold(config["profile"])
    chrome_name = fold(Path(config["chrome"]).name)
    return [line for line in lines
            if chrome_name in fold(line) and profile in fold(line) and "--type=" not in line]


# ---------------------------------------------------------------- verification

def chain_check(config):
    """Confirm the listener is bound to the exit node and the node has a real front proxy."""
    try:
        import yaml
    except ImportError:
        return {"ok": False, "reason": "缺少 PyYAML，无法确认 Clash 专用链路（pip install pyyaml）。"}
    try:
        data = yaml.safe_load(Path(config["clash_config"]).read_text(encoding="utf-8")) or {}
    except (OSError, ValueError, yaml.YAMLError):
        return {"ok": False, "reason": "无法读取 Clash 生成配置。"}
    proxies = data.get("proxies") or []
    groups = data.get("proxy-groups") or []
    node = next((p for p in proxies if p.get("name") == config["exit_node"]), None)
    listener = next((x for x in data.get("listeners") or []
                     if int(x.get("port", -1)) == config["upstream_port"]), None)
    front = node.get("dialer-proxy") if node else None
    names = {x.get("name") for x in proxies + groups}
    ok = (node is not None and listener is not None and listener.get("proxy") == config["exit_node"]
          and front and front != config["exit_node"]
          and front not in ("DIRECT", "REJECT", "GLOBAL") and front in names)
    if not ok:
        return {"ok": False, "reason": "Clash 的专用落地、前置关联或专用入口缺失。"}
    return {"ok": True, "front": front}


def probe(config, name, url):
    upstream = "http://{}:{}".format(config["upstream_host"], config["upstream_port"])
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({"http": upstream, "https": upstream}))
    try:
        with opener.open(url, timeout=config["probe_timeout_seconds"]) as response:
            body = response.read(4096).decode("utf-8", "replace").strip()
        address = next((line[3:] for line in body.splitlines() if line.startswith("ip=")), body)
        return {"name": name, "ok": True, "ip": str(ipaddress.ip_address(address.strip()))}
    except ValueError:
        return {"name": name, "ok": False, "reason": "未取得有效公网 IP"}
    except Exception as error:  # Any probe failure counts as unconfirmed, never as allowed.
        reason = getattr(error, "reason", error)
        return {"name": name, "ok": False, "reason": "检测失败：{}".format(type(reason).__name__)}


def verify(config, probe_fn=probe, chain_fn=chain_check):
    chain = chain_fn(config)
    if not chain["ok"]:
        return {"ok": False, "reason": chain["reason"], "probes": []}
    results = [None] * len(PROBES)

    def run(index):
        results[index] = probe_fn(config, *PROBES[index])

    threads = [threading.Thread(target=run, args=(i,)) for i in range(len(PROBES))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    unexpected = sorted({p["ip"] for p in results if p["ok"] and p["ip"] != config["expected_ip"]})
    matched = [p for p in results if p["ok"] and p["ip"] == config["expected_ip"]]
    if unexpected:
        reason = "出口发生变化：检测到 {}，要求 {}。".format(", ".join(unexpected), config["expected_ip"])
    elif not matched:
        reason = "两个检测服务都未能确认指定出口。"
    elif len(matched) < len(results):
        reason = "已确认指定出口（一个检测服务失败，检测降级）。"
    else:
        reason = "已确认指定出口。"
    return {"ok": bool(matched) and not unexpected, "reason": reason,
            "front": chain["front"], "probes": results}


class Health:
    def __init__(self, config, verifier=verify, clock=time.monotonic, on_change=None):
        self.config = config
        self.verifier = verifier
        self.clock = clock
        self.on_change = on_change
        self.lock = threading.RLock()
        self.check_lock = threading.Lock()
        self.allowed = False
        self.verified_at = 0.0
        self.last_result = {"ok": False, "reason": "等待出口检查。", "probes": []}
        self.pairs = set()

    def publish(self, result):
        with self.lock:
            changed = result["ok"] != self.allowed or result["reason"] != self.last_result["reason"]
            self.allowed = result["ok"]
            self.last_result = result
            if self.allowed:
                self.verified_at = self.clock()
            else:
                for pair in list(self.pairs):
                    self.close_pair(pair)
            if changed and self.on_change:
                self.on_change(result)

    def check(self, force=False):
        with self.check_lock:
            if not force and self.is_allowed(self.config["new_connection_check_age_seconds"]):
                return True
            try:
                result = self.verifier(self.config)
            except Exception:
                result = {"ok": False, "reason": "出口检查程序异常，已阻断。", "probes": []}
            self.publish(result)
            return result["ok"]

    def is_allowed(self, age=None):
        age = self.config["max_verified_age_seconds"] if age is None else age
        with self.lock:
            return self.allowed and self.clock() - self.verified_at <= age

    def register(self, pair):
        with self.lock:
            if not self.is_allowed():
                self.close_pair(pair)
                return False
            self.pairs.add(pair)
            return True

    @staticmethod
    def close_pair(pair):
        for sock in pair:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass

    def unregister(self, pair):
        with self.lock:
            self.pairs.discard(pair)
        self.close_pair(pair)

    def status(self):
        with self.lock:
            result = dict(self.last_result)
            result["ok"] = self.is_allowed()
            if self.allowed and not result["ok"]:
                result["reason"] = "出口检查结果已过期，等待重新确认。"
            result.update(expected_ip=self.config["expected_ip"],
                          active_connections=len(self.pairs),
                          check_interval_seconds=self.config["check_interval_seconds"],
                          verified_age_seconds=round(self.clock() - self.verified_at, 1)
                          if self.verified_at else None)
            return result


# ---------------------------------------------------------------- proxy server

class Gateway(socketserver.ThreadingTCPServer):
    # SO_REUSEADDR on Windows lets another process bind the same port; use exclusive binding.
    allow_reuse_address = not IS_WINDOWS
    daemon_threads = True

    def __init__(self, address, health):
        self.health = health
        super().__init__(address, Handler)

    def server_bind(self):
        if IS_WINDOWS and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def status_page(data):
    rows = "".join("<tr><td>{}</td><td>{}</td></tr>".format(
        html.escape(p["name"]), html.escape(p.get("ip") or p.get("reason", "未确认")))
        for p in data["probes"])
    color = "#155947" if data["ok"] else "#a12c2c"
    return ('<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="5">'
            '<title>Claude 专用出口状态</title><style>'
            'body{{font:17px/1.8 system-ui;max-width:760px;margin:7vh auto;padding:24px}}'
            'td{{padding:8px 24px 8px 0}}h1{{color:' + color + '}}</style>'
            '<h1>{}</h1><p>{}</p><p>指定出口：<b>{}</b><br>前置线路：{}<br>距上次确认：{} 秒<br>'
            '当前代理连接数：{}</p><table>{}</table><p>页面每 5 秒刷新，出口每 {} 秒检查。'
            '检测到不同 IP 或无法确认时关闭连接，重新确认后恢复。</p>'
            '<p><a href="https://claude.ai/">打开 Claude</a></p>').format(
                "指定出口已确认" if data["ok"] else "专用连接已阻断",
                html.escape(data["reason"]), html.escape(data["expected_ip"]),
                html.escape(str(data.get("front", "未确认"))), data["verified_age_seconds"],
                data["active_connections"], rows, data["check_interval_seconds"])


class Handler(socketserver.BaseRequestHandler):
    def reply(self, code, body, content_type="text/plain; charset=utf-8"):
        data = body.encode("utf-8")
        head = ("HTTP/1.1 {}\r\nContent-Type: {}\r\nContent-Length: {}\r\n"
                "Cache-Control: no-store\r\nConnection: close\r\n\r\n").format(code, content_type, len(data))
        try:
            self.request.sendall(head.encode("ascii") + data)
        except OSError:
            pass

    def handle(self):
        client = self.request
        client.settimeout(10)
        head = b""
        try:
            while b"\r\n\r\n" not in head:
                chunk = client.recv(8192)
                if not chunk:
                    return
                head += chunk
                if len(head) > 65536:
                    self.reply("431 Request Header Fields Too Large", "请求头过长。")
                    return
            method, target, version = head.split(b"\r\n", 1)[0].decode("ascii").split(" ", 2)
        except (OSError, ValueError, UnicodeError):
            return
        health = self.server.health
        path = urlsplit(target).path if target.startswith("http://") else target
        local_target = not target.startswith("http://") or urlsplit(target).port == health.config["listen_port"]
        if method == "GET" and local_target and path in (STATUS_PATH + ".json", STATUS_PATH):
            data = health.status()
            if path.endswith(".json"):
                data.update(service=SERVICE, version=VERSION, pid=os.getpid())
                self.reply("200 OK", json.dumps(data, ensure_ascii=False), "application/json")
            else:
                self.reply("200 OK", status_page(data), "text/html; charset=utf-8")
            return
        if version not in ("HTTP/1.0", "HTTP/1.1") or (method != "CONNECT" and urlsplit(target).scheme != "http"):
            self.reply("400 Bad Request", "只接受 HTTP 代理请求。")
            return
        if not health.check():
            self.reply("503 Service Unavailable", "Claude 专用连接已阻断：" + health.status()["reason"])
            return
        self.forward(client, head, health)

    @staticmethod
    def forward(client, head, health):
        upstream = None
        pair = None
        try:
            upstream = socket.create_connection(
                (health.config["upstream_host"], health.config["upstream_port"]), timeout=4)
            pair = (client, upstream)
            if not health.register(pair):
                return
            upstream.sendall(head)
            client.setblocking(False)
            upstream.setblocking(False)
            # Both HTTP bodies and CONNECT tunnels are opaque bytes after the headers.
            buffers = {client: bytearray(), upstream: bytearray()}
            peers = {client: upstream, upstream: client}
            open_reads = set(pair)
            open_writes = set(pair)
            while health.is_allowed():
                readable = [s for s in open_reads if len(buffers[peers[s]]) < 262144]
                writable = [s for s in pair if buffers[s]]
                if not readable and not writable:
                    break
                ready_read, ready_write, exceptional = select.select(readable, writable, list(pair), 1)
                if exceptional:
                    break
                for sock in ready_read:
                    try:
                        chunk = sock.recv(65536)
                    except (BlockingIOError, InterruptedError):
                        continue
                    if not chunk:
                        open_reads.discard(sock)
                    else:
                        buffers[peers[sock]].extend(chunk)
                for sock in ready_write:
                    try:
                        count = sock.send(buffers[sock])
                    except (BlockingIOError, InterruptedError):
                        continue
                    del buffers[sock][:count]
                for sock in pair:
                    if peers[sock] not in open_reads and not buffers[sock] and sock in open_writes:
                        sock.shutdown(socket.SHUT_WR)
                        open_writes.discard(sock)
        except (OSError, ValueError):
            pass
        finally:
            if pair:
                health.unregister(pair)
            elif upstream:
                upstream.close()


# ---------------------------------------------------------------- browser, leases, status

def chrome_command(config, urls=None):
    return [config["chrome"], "--user-data-dir=" + config["profile"],
            "--proxy-server=" + guard_url(config),
            # OAuth returns to the CLI's local listener; only literal loopback bypasses the guard.
            "--proxy-bypass-list=<-loopback>;localhost;127.0.0.1;[::1]",
            "--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1, EXCLUDE localhost",
            "--force-webrtc-ip-handling-policy=disable_non_proxied_udp", "--disable-quic",
            "--disable-background-networking", "--disable-sync", "--no-first-run",
            "--no-default-browser-check", "--new-window",
            *language_flags(config.get("chrome_lang", "")),
            *(urls or [guard_url(config) + STATUS_PATH])]


def language_flags(lang):
    """UI language (ignored by Chrome on macOS) and Accept-Language; "" keeps Chrome's own choice."""
    if not lang:
        return []
    primary = lang.split("-")[0]
    accept = lang if primary == lang else "{},{}".format(lang, primary)
    return ["--lang=" + lang, "--accept-lang=" + accept]


class BrowserWatch:
    """Cached check for the dedicated Chrome; process listing is slow on Windows."""

    def __init__(self, config, ttl=5 if IS_WINDOWS else 1, lister=process_command_lines):
        self.config, self.ttl, self.lister = config, ttl, lister
        self.at, self.value = -1e9, False

    def running(self):
        if time.monotonic() - self.at >= self.ttl:
            self.value = bool(dedicated_browser_lines(self.config, self.lister()))
            self.at = time.monotonic()
        return self.value


def cli_running(state_dir, alive=pid_alive):
    running = False
    for lease in Path(state_dir).glob("cli-*.lease"):
        try:
            pid = int(lease.read_text())
        except (OSError, ValueError):
            continue
        if not alive(pid):
            lease.unlink(missing_ok=True)  # Wrapper was killed before its cleanup ran.
            continue
        try:
            if time.time() - lease.stat().st_mtime < 45:
                running = True
        except OSError:
            pass
    return running


def read_status(config, timeout=2):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(guard_url(config) + STATUS_PATH + ".json", timeout=timeout) as response:
            data = json.load(response)
    except (OSError, ValueError):
        return None
    return data if data.get("service") == SERVICE else None


def serve(config, open_browser):
    if open_browser:
        stale = [line for line in dedicated_browser_lines(config, process_command_lines())
                 if "--proxy-server=" + guard_url(config) not in line]
        if stale:
            alert("专用 Chrome 仍在用旧参数运行。请完整退出该专用实例后再打开，已有窗口未被关闭。")
            return 1
    state_dir = Path(config["state_dir"])
    state_dir.mkdir(parents=True, exist_ok=True)
    if not IS_WINDOWS:
        os.chmod(state_dir, 0o700)
    lock = try_lock(state_dir / "guard.lock")
    if lock is None:
        # The existing guard owns the listener and the leases; never replace it.
        if open_browser:
            spawn_detached(chrome_command(config))
        return 0
    log_path = state_dir / "guard.log"

    def log(result):
        entry = dict(time=time.strftime("%Y-%m-%d %H:%M:%S"), **result)
        with open(log_path, "a", encoding="utf-8") as stream:
            stream.write(json.dumps(entry, ensure_ascii=False) + "\n")

    health = Health(config, on_change=log)
    try:
        server = Gateway((config["listen_host"], config["listen_port"]), health)
    except OSError:
        alert("本机保护端口 {} 已被其他程序占用，未启动。".format(config["listen_port"]))
        return 1
    if not health.check(force=True) and open_browser:
        status = health.status()
        detail = "；".join(p["name"] + "：" + (p.get("ip") or p.get("reason", "失败")) for p in status["probes"])
        alert("已阻止启动。" + status["reason"] + "\n" + detail + "\n请在 Clash 链式页面检查前置和落地；不会回落直连。")
        server.server_close()
        return 1
    stop = threading.Event()
    threading.Thread(target=server.serve_forever, daemon=True).start()

    def shutdown(*_):
        stop.set()
        health.publish({"ok": False, "reason": "专用保护入口已停止。", "probes": []})

    for name in ("SIGTERM", "SIGINT", "SIGHUP", "SIGBREAK"):
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), shutdown)
    browser = BrowserWatch(config)
    try:
        if open_browser:
            spawn_detached(chrome_command(config))
            deadline = time.monotonic() + 15
            while not stop.wait(0.5) and time.monotonic() < deadline and not browser.running():
                pass
            if not browser.running():
                alert("出口检查通过，但专用 Chrome 未成功启动。请检查配置中的 Chrome 路径。")
                return 1
        next_check = time.monotonic() + config["check_interval_seconds"]
        last_used = time.monotonic()
        while not stop.wait(1):
            if browser.running() or cli_running(state_dir):
                last_used = time.monotonic()
            if time.monotonic() - last_used > config["idle_exit_seconds"]:
                break
            if time.monotonic() >= next_check:
                health.check(force=True)
                next_check = time.monotonic() + config["check_interval_seconds"]
    finally:
        shutdown()
        server.shutdown()
        server.server_close()
        lock.close()
    return 0


# ---------------------------------------------------------------- CLI entry

def cli_environment(config, base_env, helper):
    env = dict(base_env)
    if config["strip_api_env"]:
        # Official subscription login: drop inherited third-party auth and routing.
        for key in list(env):
            if key.startswith("ANTHROPIC_") or key in PROVIDER_KEYS:
                env.pop(key)
    env.update(cli_settings(config)["env"])
    if helper:
        env["BROWSER"] = str(helper)
    return env


def run_cli(config, config_path, args):
    if any(arg == "--settings" or arg.startswith("--settings=") for arg in args):
        print("受保护入口不接受 --settings 覆盖；请在用户或项目设置里配置其他选项。", file=sys.stderr)
        return 2
    if not config["claude_bin"]:
        print("配置缺少 claude_bin（官方 Claude Code 可执行文件）。", file=sys.stderr)
        return 2
    state_dir = Path(config["state_dir"])
    state_dir.mkdir(parents=True, exist_ok=True)
    settings_path = state_dir / "cli-network-settings.json"
    settings_path.write_text(json.dumps(cli_settings(config), indent=2), encoding="utf-8")
    lease = state_dir / "cli-{}.lease".format(os.getpid())
    lease.write_text(str(os.getpid()))
    child = None
    try:
        if read_status(config) is None:
            spawn_detached([sys.executable, str(Path(__file__).resolve()), "--config", str(config_path), "serve"])
        deadline = time.monotonic() + 45
        ready = None
        while time.monotonic() < deadline:
            os.utime(lease, None)
            ready = read_status(config)
            if ready and ready.get("ok"):
                break
            time.sleep(0.5)
        if not ready or not ready.get("ok"):
            print("Claude CLI 已阻止启动：" + (ready or {}).get("reason", "保护入口未就绪。"), file=sys.stderr)
            return 1
        helper = config.get("browser_helper") or ""
        env = cli_environment(config, os.environ, helper)
        child = subprocess.Popen([config["claude_bin"], "--settings", str(settings_path), *args], env=env)

        def forward(signum, _frame):
            if child.poll() is None:
                child.send_signal(signum)

        for name in ("SIGTERM", "SIGHUP"):  # SIGHUP: closing the terminal still cleans up the lease.
            if hasattr(signal, name):
                signal.signal(getattr(signal, name), forward)
        signal.signal(signal.SIGINT, lambda *_: None)  # The terminal delivers Ctrl+C to the child itself.
        while child.poll() is None:
            os.utime(lease, None)
            time.sleep(1)
        return child.returncode if child.returncode >= 0 else 128 - child.returncode
    finally:
        lease.unlink(missing_ok=True)


def open_url(config, urls):
    if not urls or any(urlsplit(url).scheme not in ("https", "http") for url in urls):
        return 2
    spawn_detached(chrome_command(config, urls))
    return 0


# ---------------------------------------------------------------- wrappers

def wrapper_files(config_path, script=None, python=None, windows=IS_WINDOWS):
    script = str(script or Path(__file__).resolve())
    python = str(python or sys.executable)
    config_path = str(config_path)
    if windows:
        def cmd(sub):
            return '@echo off\r\n"{}" "{}" --config "{}" {} %*\r\n'.format(python, script, config_path, sub)
        return {"claude-safe.cmd": cmd("cli"), "claude-oauth-browser.cmd": cmd("open-url")}

    def sh(sub):
        quote = lambda value: "'" + value.replace("'", "'\\''") + "'"
        return '#!/bin/sh\nexec {} {} --config {} {} "$@"\n'.format(quote(python), quote(script), quote(config_path), sub)
    return {"claude-safe": sh("cli"), "claude-oauth-browser": sh("open-url")}


def install_wrappers(config_path, bin_dir):
    bin_dir = Path(bin_dir)
    bin_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name, content in wrapper_files(config_path).items():
        path = bin_dir / name
        path.write_text(content, encoding="utf-8", newline="")
        if not IS_WINDOWS:
            path.chmod(0o700)
        written.append(str(path))
    print("\n".join(written))
    print("把 claude-oauth-browser 的完整路径写入配置的 browser_helper。")
    return 0


# ---------------------------------------------------------------- main

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", type=Path, default=Path(os.environ.get("CLAUDE_GUARD_CONFIG", default_config_path())))
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("browser")
    sub.add_parser("serve")
    sub.add_parser("status")
    cli = sub.add_parser("cli")
    cli.add_argument("args", nargs=argparse.REMAINDER)
    url = sub.add_parser("open-url")
    url.add_argument("urls", nargs="*")
    wrap = sub.add_parser("install-wrappers")
    wrap.add_argument("--bin-dir", required=True)
    options = parser.parse_args(argv)
    command = options.command or "browser"
    if command == "install-wrappers":
        return install_wrappers(options.config.resolve(), options.bin_dir)
    try:
        config = load_config(options.config)
    except (OSError, ValueError) as error:
        print("无法读取守护配置 {}：{}".format(options.config, error), file=sys.stderr)
        return 2
    if command == "status":
        data = read_status(config)
        print(json.dumps(data or {"running": False}, ensure_ascii=False, indent=2))
        return 0 if data and data.get("ok") else 1
    if command == "cli":
        return run_cli(config, options.config.resolve(), options.args)
    if command == "open-url":
        return open_url(config, options.urls)
    return serve(config, open_browser=command == "browser")


if __name__ == "__main__":
    sys.exit(main())
