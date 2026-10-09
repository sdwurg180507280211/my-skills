#!/usr/bin/env python3
"""Read-only macOS TUN detector. Never dumps subscriptions, secrets or URLs."""
import json
import os
from pathlib import Path
import re
import subprocess


def command(args):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=5)
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
        text = path.read_text()
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


def classify(core_running, configured, route_interface, system_proxy_enabled):
    route_is_tun = bool(route_interface and route_interface.startswith("utun"))
    if core_running and configured is True and route_is_tun:
        return "tun"
    if configured is True:
        return "tun_configured_unconfirmed"
    if system_proxy_enabled:
        return "system_proxy"
    return "unknown"


def detect():
    processes = command(["ps", "-axo", "comm="])
    core = any(re.search(r"(?:^|/)(?:verge-mihomo|mihomo|clash(?:-meta)?)(?:\s|$)", p, re.I)
               for p in processes.splitlines())
    home = Path.home()
    roots = [home / "Library/Application Support/io.github.clash-verge-rev.clash-verge-rev",
             home / ".config/clash", home / ".config/mihomo"]
    flags = []
    for root in roots:
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
    proxy_state = command(["scutil", "--proxy"])
    system_proxy = bool(re.search(r"(?:HTTPEnable|HTTPSEnable|SOCKSEnable|ProxyAutoConfigEnable)\s*:\s*1\b", proxy_state))
    # A route lookup is local; it does not send a request to this address.
    probe_ip = "1.1.1.1"
    route = command(["route", "-n", "get", probe_ip])
    m = re.search(r"interface:\s*(\S+)", route)
    interface = m.group(1) if m else None
    iface = command(["ifconfig", interface]) if interface and interface.startswith("utun") else ""
    up = bool(re.search(r"flags=.*<[^>]*\bUP\b", iface))
    mode = classify(core, configured, interface if up else None, system_proxy)
    return {
        "mode": mode,
        "core_running": core,
        "tun_configured": configured,
        "route_probe": {"ip": probe_ip, "interface": interface, "interface_up": up,
                        "through_utun": bool(interface and interface.startswith("utun") and up)},
        "system_proxy_enabled": system_proxy,
        "explicit_proxy_env_present": any(os.environ.get(k) for k in
            ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy")),
        "config_evidence": flags,
        "scope": "Known Clash/Mihomo configuration + running core + local route evidence; not a live controller query or proof of every destination's proxy rule.",
    }


if __name__ == "__main__":
    print(json.dumps(detect(), ensure_ascii=False, indent=2))
