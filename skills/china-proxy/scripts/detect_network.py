#!/usr/bin/env python3
"""Read-only TUN detector for macOS and Windows. Never dumps subscriptions, secrets or URLs."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

IS_WINDOWS = os.name == "nt"
PROBE_IP = "1.1.1.1"
CORE_NAMES = re.compile(r"^(?:verge-mihomo(?:-alpha)?|mihomo|clash(?:-meta)?)$", re.I)
TUN_HINT = re.compile(r"mihomo|meta|clash|wintun|\btun\b", re.I)
VERGE_ID = "io.github.clash-verge-rev.clash-verge-rev"


def command(args):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=10)
        return p.stdout if p.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def scalar(text, key):
    pattern = r"(?m)^" + re.escape(key) + r"\s*:\s*([^\n#]*)"
    m = re.search(pattern, text)
    if not m:
        return None
    v = m.group(1).strip().strip("\"'")
    if v.lower() in ("true", "false"):
        return v.lower() == "true"
    return v


def config_flags(path):
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    tun = re.search(r"(?m)^tun:\s*(?:#.*)?$([\s\S]*?)(?=^\S|\Z)", text)
    # Parse only expected booleans; never expose other YAML values.
    return {
        "file": str(path),
        "tun_enabled": scalar(text, "enable_tun_mode"),
        "system_proxy_enabled": scalar(text, "enable_system_proxy"),
        "tun_config_enabled": scalar(re.sub(r"(?m)^\s+", "", tun.group(1)), "enable") if tun else None,
        "auto_route": scalar(re.sub(r"(?m)^\s+", "", tun.group(1)), "auto-route") if tun else None,
    }


def is_tun_interface(name, description=""):
    if not name:
        return False
    return name.startswith("utun") or bool(TUN_HINT.search("{} {}".format(name, description or "")))


def classify(core_running, configured, route_is_tun, system_proxy_enabled):
    if core_running and configured is True and route_is_tun:
        return "tun"
    if configured is True:
        return "tun_configured_unconfirmed"
    if system_proxy_enabled:
        return "system_proxy"
    return "unknown"


def process_names():
    if IS_WINDOWS:
        rows = command(["tasklist", "/fo", "csv", "/nh"]).splitlines()
        names = [row.split('","', 1)[0].strip('"') for row in rows if row.startswith('"')]
    else:
        names = command(["ps", "-axo", "comm="]).splitlines()
    result = []
    for name in names:
        base = re.split(r"[\\/]", name.strip())[-1]
        result.append(base[:-4] if base.lower().endswith(".exe") else base)
    return result


def config_roots():
    home = Path.home()
    if IS_WINDOWS:
        appdata = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
        verge = appdata / VERGE_ID
    else:
        verge = home / "Library/Application Support" / VERGE_ID
    return [verge, home / ".config/clash", home / ".config/mihomo"]


def system_proxy_enabled():
    if IS_WINDOWS:
        out = command(["reg", "query", r"HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings"])
        manual = re.search(r"ProxyEnable\s+REG_DWORD\s+0x0*1\b", out)
        pac = re.search(r"AutoConfigURL\s+REG_SZ\s+\S", out)
        return bool(manual or pac)
    out = command(["scutil", "--proxy"])
    return bool(re.search(r"(?:HTTPEnable|HTTPSEnable|SOCKSEnable|ProxyAutoConfigEnable)\s*:\s*1\b", out))


def route_probe():
    """Local route lookup for PROBE_IP; it does not send traffic to that address."""
    if IS_WINDOWS:
        script = ("$r = Find-NetRoute -RemoteIPAddress {} -ErrorAction SilentlyContinue | Select-Object -First 1; "
                  "if ($r) {{ $a = Get-NetAdapter -InterfaceIndex $r.InterfaceIndex -ErrorAction SilentlyContinue; "
                  "[pscustomobject]@{{alias=$r.InterfaceAlias; status=[string]$a.Status; "
                  "description=$a.InterfaceDescription}} | ConvertTo-Json -Compress }}").format(PROBE_IP)
        out = command(["powershell", "-NoProfile", "-NonInteractive", "-Command", script])
        try:
            data = json.loads(out) if out.strip() else {}
        except ValueError:
            data = {}
        interface = data.get("alias")
        up = str(data.get("status", "")).lower() == "up"
        return interface, up, is_tun_interface(interface, data.get("description", "")) and up
    m = re.search(r"interface:\s*(\S+)", command(["route", "-n", "get", PROBE_IP]))
    interface = m.group(1) if m else None
    iface = command(["ifconfig", interface]) if interface and interface.startswith("utun") else ""
    up = bool(re.search(r"flags=.*<[^>]*\bUP\b", iface))
    return interface, up, bool(interface and interface.startswith("utun") and up)


def detect():
    core = any(CORE_NAMES.match(name) for name in process_names())
    flags = []
    for root in config_roots():
        for name in ["verge.yaml", "clash-verge.yaml", "config.yaml"]:
            item = config_flags(root / name)
            if item is not None:
                flags.append(item)
    # Prefer Verge's UI state and generated config over its base config, which
    # may still contain tun.enable=false even while the running TUN is enabled.
    configured = None
    for name, key in [("clash-verge.yaml", "tun_config_enabled"), ("verge.yaml", "tun_enabled"), ("config.yaml", "tun_config_enabled")]:
        candidates = [f[key] for f in flags if Path(f["file"]).name == name and isinstance(f[key], bool)]
        if candidates:
            configured = candidates[0]
            break
    system_proxy = system_proxy_enabled()
    interface, up, through_tun = route_probe()
    return {
        "platform": "windows" if IS_WINDOWS else sys.platform,
        "mode": classify(core, configured, through_tun, system_proxy),
        "core_running": core,
        "tun_configured": configured,
        "route_probe": {"ip": PROBE_IP, "interface": interface, "interface_up": up, "through_tun": through_tun},
        "system_proxy_enabled": system_proxy,
        "explicit_proxy_env_present": any(os.environ.get(k) for k in
            ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy")),
        "config_evidence": flags,
        "scope": "Known Clash/Mihomo configuration + running core + local route evidence; not a live controller query or proof of every destination's proxy rule.",
    }


if __name__ == "__main__":
    print(json.dumps(detect(), ensure_ascii=False, indent=2))
