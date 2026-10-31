#!/usr/bin/env python3
"""方法二：读回复核网页里的“有问题”和备注，只输出被标记的场次。

来源二选一：
- 网页导出的 CSV（--csv），最可靠；
- Chrome 的 localStorage（默认）。只读解析各 Profile 下 Local Storage/leveldb/*.log，
  不修改浏览器数据。刚写入的标注在 .log 里；被 Chrome 压缩进 .ldb 后读不到，此时改用 CSV。
"""
from __future__ import annotations

import argparse
import csv
import json
import struct
import sys
from pathlib import Path

CHROME = Path("~/Library/Application Support/Google/Chrome").expanduser()


def varint(b: bytes, i: int) -> tuple[int, int]:
    result = shift = 0
    while True:
        c = b[i]
        i += 1
        result |= (c & 0x7F) << shift
        shift += 7
        if c < 0x80:
            return result, i


def decode(raw: bytes) -> str:
    # Chrome localStorage 值/键首字节：0 表示 UTF-16LE，1 表示 Latin-1
    if not raw:
        return ""
    return raw[1:].decode("utf-16-le" if raw[0] == 0 else "latin-1", "replace")


def log_records(data: bytes) -> list[bytes]:
    records, buf, pos = [], b"", 0
    while pos + 7 <= len(data):
        left = 32768 - pos % 32768
        if left < 7:
            pos += left
            continue
        _, length, kind = struct.unpack("<IHB", data[pos:pos + 7])
        frag = data[pos + 7:pos + 7 + length]
        pos += 7 + length
        if kind == 1:
            records.append(frag)
        elif kind == 2:
            buf = frag
        elif kind == 3:
            buf += frag
        elif kind == 4:
            records.append(buf + frag)
            buf = b""
    return records


def parse_log(data: bytes, prefix: str) -> list[tuple[str, str | None]]:
    """按写入顺序返回 (键, 值)；值为 None 表示删除。"""
    out = []
    for rec in log_records(data):
        if len(rec) < 12:
            continue
        count, i = struct.unpack("<I", rec[8:12])[0], 12
        try:
            for _ in range(count):
                tag = rec[i]
                i += 1
                klen, i = varint(rec, i)
                k = rec[i:i + klen]
                i += klen
                v = None
                if tag == 1:
                    vlen, i = varint(rec, i)
                    v = rec[i:i + vlen]
                    i += vlen
                if not k.startswith(b"_") or b"\x00" not in k:
                    continue
                key = decode(k[k.index(b"\x00") + 1:])
                if key.startswith(prefix):
                    out.append((key[len(prefix):], None if v is None else decode(v)))
        except IndexError:
            continue  # 末尾半条记录(浏览器正在写)
    return out


def from_chrome(prefix: str, root: Path) -> tuple[dict[str, str], list[str]]:
    kv: dict[str, str] = {}
    used = []
    logs = sorted(root.glob("*/Local Storage/leveldb/*.log"), key=lambda p: (p.parent, p.name))
    for log in logs:
        entries = parse_log(log.read_bytes(), prefix)
        if entries:
            used.append(str(log))
        for key, value in entries:
            if value is None:
                kv.pop(key, None)
            else:
                kv[key] = value
    return kv, used


def from_csv(path: Path) -> dict[str, str]:
    kv = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            name = row.get("会议", "")
            kv[f"{name}|有问题"] = "1" if row.get("有问题") in ("是", "1") else "0"
            kv[f"{name}|备注"] = row.get("备注", "")
    return kv


def flagged(kv: dict[str, str]) -> list[dict]:
    meetings: dict[str, dict] = {}
    for key, value in kv.items():
        name, _, field = key.rpartition("|")
        meetings.setdefault(name, {})[field] = value
    return [{"会议": name, "有问题": v.get("有问题") == "1", "备注": v.get("备注", "")}
            for name, v in sorted(meetings.items()) if v.get("有问题") == "1" or v.get("备注", "").strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--key", help="生成网页时的键前缀(build_review_html.py 输出的 storage_key，末尾冒号可省)")
    parser.add_argument("--csv", help="网页导出的 截图复核结果.csv")
    parser.add_argument("--chrome-dir", default=str(CHROME), help="Chrome 用户数据目录")
    args = parser.parse_args(argv)
    if args.csv:
        kv, sources = from_csv(Path(args.csv).expanduser()), [args.csv]
    elif args.key:
        prefix = args.key if args.key.endswith(":") else args.key + ":"
        kv, sources = from_chrome(prefix, Path(args.chrome_dir).expanduser())
    else:
        parser.error("需要 --key 或 --csv")
    result = {"sources": sources, "flagged": flagged(kv), "stored_entries": len(kv)}
    if not sources:
        result["note"] = "Chrome .log 中没有找到该键前缀的标注；可能已被压缩进 .ldb 或用的不是 Chrome，请在网页点“导出”后用 --csv 读取"
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if sources else 2


if __name__ == "__main__":
    sys.exit(main())
