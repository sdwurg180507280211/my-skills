#!/usr/bin/env python3
"""Read selected Claude settings/environment without emitting their values."""
from __future__ import annotations

import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit

MAX_BYTES = 2 * 1024 * 1024
NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")
NONEMPTY_FLAGS = {
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC", "DISABLE_TELEMETRY",
    "DISABLE_ERROR_REPORTING",
}
BOOLEAN_FLAGS = {"DISABLE_GROWTHBOOK", "DO_NOT_TRACK", "CLAUDE_CODE_DISABLE_AGENT_VIEW",
                 "CLAUDE_CODE_DISABLE_FEEDBACK_SURVEY"}
FEATURE_FLAG_FETCH_BLOCKERS = {
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC", "DISABLE_TELEMETRY",
    "DISABLE_GROWTHBOOK", "DO_NOT_TRACK",
}
PROXIES = {"http_proxy", "https_proxy", "all_proxy"}
TOP_LEVEL = {"apiKeyHelper", "forceLoginMethod", "hooks", "model", "env"}


def relevant(key: object) -> bool:
    return isinstance(key, str) and bool(NAME.fullmatch(key)) and (
        key.lower() in PROXIES | {"no_proxy"}
        or key.startswith(("ANTHROPIC_", "CLAUDE_"))
        or key in NONEMPTY_FLAGS | BOOLEAN_FLAGS
    )


def loopback(host: str | None) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host or "").is_loopback
    except ValueError:
        return False


def describe(key: str, value: object) -> dict:
    row = {"key": key, "configured": isinstance(value, str) and bool(value)}
    if not isinstance(value, str):
        return {**row, "category": "invalid_env_value", "valid_string": False}
    if key in NONEMPTY_FLAGS:
        row.update(category="nonempty_flag", enabled=bool(value))
        if key in FEATURE_FLAG_FETCH_BLOCKERS:
            row["disables_feature_flag_fetching"] = bool(value)
        return row
    if key in BOOLEAN_FLAGS:
        enabled = {"1": True, "true": True, "yes": True, "on": True,
                   "0": False, "false": False, "no": False, "off": False, "": False}
        row.update(category="boolean_flag", enabled=enabled.get(value.lower()))
        if key in FEATURE_FLAG_FETCH_BLOCKERS:
            row["disables_feature_flag_fetching"] = row["enabled"]
        return row
    if key.lower() in PROXIES or key == "ANTHROPIC_BASE_URL":
        category = "proxy" if key.lower() in PROXIES else "api_endpoint"
        row.update(category=category)
        if not value:
            return row
        try:
            parsed = urlsplit(value)
            valid = parsed.scheme in {"http", "https", "socks", "socks5", "socks5h"} and bool(parsed.hostname)
            parsed.port  # Validate without printing the port or URL.
            row.update(valid_url=bool(valid), loopback_host=loopback(parsed.hostname),
                       credential_fields_present=parsed.username is not None or parsed.password is not None)
            if category == "api_endpoint":
                row["official_api_host"] = valid and parsed.scheme == "https" and parsed.hostname == "api.anthropic.com"
        except ValueError:
            row["valid_url"] = False
        return row
    if key.lower() == "no_proxy":
        entries = [x.strip() for x in value.split(",") if x.strip()]
        def local(entry: str) -> bool:
            if entry in {"localhost", "127.0.0.1", "::1", "[::1]"}:
                return True
            try:
                parsed = urlsplit("http://" + entry)
                parsed.port
                return loopback(parsed.hostname) and not parsed.path and not parsed.username
            except ValueError:
                return False
        return {**row, "category": "proxy_bypass", "entry_count": len(entries),
                "wildcard_present": "*" in entries,
                "non_loopback_or_unrecognized_entries": any(not local(x) for x in entries)}
    if key.startswith("ANTHROPIC_") and any(x in key for x in ("KEY", "TOKEN", "HEADERS")):
        return {**row, "category": "authentication_or_headers"}
    if key.startswith("CLAUDE_CODE_USE_"):
        return {**row, "category": "provider_selector"}
    return {**row, "category": "claude_environment"}


def audit_env(env: dict) -> list[dict]:
    return [describe(k, v) for k, v in sorted(env.items()) if relevant(k)]


def audit_file(path: Path, label: str) -> dict:
    result = {"source": label}
    try:
        if not path.is_file():
            return {**result, "status": "missing_or_not_file"}
        with path.open("rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            return {**result, "status": "too_large"}
        data = json.loads(raw)
    except (ValueError, UnicodeError):
        return {**result, "status": "invalid_json"}
    except OSError:
        return {**result, "status": "unreadable"}
    if not isinstance(data, dict):
        return {**result, "status": "invalid_root"}
    env = data.get("env", {})
    if not isinstance(env, dict):
        return {**result, "status": "invalid_env"}
    return {**result, "status": "ok", "related_top_level_keys": sorted(TOP_LEVEL & data.keys()),
            "env": audit_env(env)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--settings", action="append", type=Path, default=[])
    parser.add_argument("--include-process-env", action="store_true")
    args = parser.parse_args(argv)
    if not args.settings and not args.include_process_env:
        parser.error("provide --settings or --include-process-env; no automatic scan")
    sources = [audit_file(path, f"settings[{i}]") for i, path in enumerate(args.settings, 1)]
    if args.include_process_env:
        sources.append({"source": "inherited_process_environment", "status": "ok",
                        "env": audit_env(dict(os.environ))})
    print(json.dumps({"read_only": True, "effective_configuration_verified": False,
                      "sources": sources}, ensure_ascii=False, indent=2))
    return 0 if all(s["status"] == "ok" for s in sources) else 1


if __name__ == "__main__":
    raise SystemExit(main())
