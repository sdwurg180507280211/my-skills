#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp>=1.16,<2"]
# ///
"""Call Baidu's SSE MCP using existing local credentials, without printing them."""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit


class InputError(ValueError):
    """A credential-free diagnostic written by this script."""


def load_connection(config: Path | None = None) -> tuple[Path, str]:
    candidates = [config] if config else [
        Path.home() / ".workbuddy/mcp.json",
        Path.home() / ".codebuddy/.mcp.json",
    ]
    for path in candidates:
        if not path.is_file():
            if config:
                raise InputError("指定配置文件不存在")
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            server = data.get("mcpServers", {}).get("baidu-netdisk")
            if not isinstance(server, dict):
                continue
            if server.get("disabled") is True or server.get("enabled") is False:
                continue
            url = server.get("url", "")
            try:
                parts = urlsplit(url)
            except ValueError:
                raise InputError("配置中的服务 URL 无效") from None
            if (parts.scheme != "https" or parts.netloc != "mcp-pan.baidu.com"
                    or parts.path != "/sse" or parts.fragment):
                raise InputError("配置不是百度官方 HTTPS SSE 地址")
            if not parse_qs(parts.query).get("access_token"):
                raise InputError("配置缺少 access_token，请在所属客户端重新连接")
            return path, url
        except (OSError, json.JSONDecodeError, AttributeError, TypeError):
            raise InputError("无法读取 MCP 配置，请检查 JSON 格式和文件权限") from None
    raise InputError("未找到已启用的 baidu-netdisk，请配置 WorkBuddy 或 CodeBuddy")


def read_arguments(path: str) -> dict:
    try:
        text = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
        arguments = json.loads(text)
    except (OSError, json.JSONDecodeError):
        raise InputError("参数文件必须是可读取的 JSON 对象") from None
    if not isinstance(arguments, dict):
        raise InputError("工具参数必须是 JSON 对象")
    return arguments


def redact(value: str, url: str) -> str:
    value = value.replace(url, "https://mcp-pan.baidu.com/sse?[REDACTED]")
    for token in parse_qs(urlsplit(url).query).get("access_token", []):
        value = value.replace(token, "[REDACTED]")
    return value


async def invoke(url: str, args: argparse.Namespace, arguments: dict | None):
    from mcp import ClientSession
    from mcp.client.sse import sse_client

    async with sse_client(url, timeout=min(args.timeout, 15),
                          sse_read_timeout=args.timeout) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            if args.action == "tools":
                tools, cursor, seen = [], None, set()
                while True:
                    page = await session.list_tools(cursor=cursor)
                    tools.extend(tool.model_dump(mode="json", exclude_none=True)
                                 for tool in page.tools)
                    cursor = page.nextCursor
                    if not cursor:
                        return {"tools": tools}
                    if cursor in seen:
                        raise InputError("服务重复返回分页游标，已停止")
                    seen.add(cursor)
            result = await session.call_tool(args.tool, arguments=arguments)
            return result.model_dump(mode="json", exclude_none=True)


def error_summary(exc: BaseException) -> str:
    """Expose HTTP status, never exception messages that may contain a token URL."""
    nested = getattr(exc, "exceptions", None)
    if nested:
        return "; ".join(dict.fromkeys(error_summary(item) for item in nested))
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    if status in (401, 403):
        return f"HTTP {status}：认证失败，请在选定客户端重新连接百度网盘"
    if status:
        return f"HTTP {status}：百度网盘服务请求失败"
    if isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
        return "请求超时；写操作请先核对状态，再决定是否重试"
    return f"连接或调用失败（{type(exc).__name__}），请检查认证及网络"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, help="客户端私有 MCP JSON 配置")
    parser.add_argument("--timeout", type=float, default=45)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("config", help="离线检查配置，只输出脱敏端点")
    sub.add_parser("tools", help="连接并列出真实工具 schema")
    call = sub.add_parser("call", help="调用实际工具；操作授权由调用者确认")
    call.add_argument("tool")
    call.add_argument("--args-file", required=True, help="私有 JSON 参数文件，- 表示 stdin")
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    try:
        if args.timeout <= 0:
            raise InputError("timeout 必须大于零")
        path, url = load_connection(args.config)
        if args.action == "config":
            result = {"config": str(path), "server": "baidu-netdisk",
                      "endpoint": "https://mcp-pan.baidu.com/sse", "authenticated": "not_checked"}
        else:
            arguments = read_arguments(args.args_file) if args.action == "call" else None
            async def bounded():
                return await asyncio.wait_for(invoke(url, args, arguments), args.timeout)
            result = asyncio.run(bounded())
        print(redact(json.dumps(result, ensure_ascii=False, indent=2), url))
        return 1 if result.get("isError") else 0
    except InputError as exc:
        print(str(exc), file=sys.stderr)
    except ImportError:
        print("缺少 MCP SDK；请用 uv run 执行此脚本", file=sys.stderr)
    except Exception as exc:
        print(error_summary(exc), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
