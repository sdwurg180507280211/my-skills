#!/usr/bin/env python3
"""Read-only batch and live-list checks; no HTTP calls or file mutations."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import unquote, urlsplit

CATEGORIES = {
    "A": "最终会议议程",
    "B": "参会者签到表/线上会议参会报告",
    "C": "付费服务提供者照片/截屏（例如：主席/讲者/讨论嘉宾等）",
    "D": "会场照片/截屏",
}
CONTENT_TYPES = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
UPLOAD_FIELDS = (
    "finalMeetingAgendaUpload", "signTable", "paidServicePhoto", "venuePhoto",
)


def nonempty(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}: expected non-empty string")
    return value


def make_object_key(name: str, timestamp: int, record_id: str) -> str:
    nonempty(name, "name")
    nonempty(record_id, "recordId")
    if "/" in name or "\\" in name or "/" in record_id or "\\" in record_id:
        raise ValueError("name and recordId must not contain path separators")
    if type(timestamp) is not int or timestamp <= 0:
        raise ValueError("timestampMs: expected positive integer")
    path = Path(name)
    ext = path.suffix[1:]
    if ext.lower() not in CONTENT_TYPES:
        raise ValueError(f"unsupported extension: {ext}")
    return f"{path.stem}_{timestamp}_{record_id}.{ext}"


def url_matches(url: str, key: str, prefix: str, host: str) -> bool:
    parsed = urlsplit(url)
    expected = "/" + prefix.strip("/") + "/" + key
    return (
        parsed.scheme == "https"
        and bool(host)
        and parsed.netloc == host
        and parsed.username is None
        and parsed.password is None
        and not parsed.fragment
        and unquote(parsed.path) == expected
    )


def validate_batch(batch: dict, base_dir: Path) -> dict:
    if not isinstance(batch, dict):
        raise ValueError("batch: expected object")
    batch_id = nonempty(batch.get("batchId"), "batchId")
    project_id = nonempty(batch.get("projectId"), "projectId")
    record_ids = batch.get("recordIds")
    if not isinstance(record_ids, list) or not record_ids:
        raise ValueError("recordIds: expected non-empty list")
    for rid in record_ids:
        nonempty(rid, "recordId")
    if len(set(record_ids)) != len(record_ids):
        raise ValueError("recordIds: duplicates")
    files = batch.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("files: expected non-empty list")
    prefix = nonempty(batch.get("storagePrefix", "op2-event"), "storagePrefix")
    issues, keys, covered = [], set(), set()
    for index, item in enumerate(files):
        try:
            if not isinstance(item, dict):
                raise ValueError("file: expected object")
            if item.get("batchId") != batch_id or item.get("projectId") != project_id:
                raise ValueError("batch/project mismatch")
            rid = nonempty(item.get("recordId"), "recordId")
            if rid not in record_ids:
                raise ValueError("recordId outside batch whitelist")
            category = nonempty(item.get("category"), "category")
            if category not in CATEGORIES:
                raise ValueError("unknown category")
            if item.get("documentType", CATEGORIES[category]) != CATEGORIES[category]:
                raise ValueError("documentType must match full category label")
            name = nonempty(item.get("name"), "name")
            key = make_object_key(name, item.get("timestampMs"), rid)
            if item.get("objectKey") != key:
                raise ValueError("objectKey mismatch")
            if key in keys:
                raise ValueError("duplicate objectKey")
            keys.add(key)
            ext = Path(name).suffix[1:].lower()
            if item.get("contentType") != CONTENT_TYPES[ext]:
                raise ValueError("contentType mismatch")
            path = Path(nonempty(item.get("path"), "path"))
            if not path.is_absolute():
                path = base_dir / path
            if not path.is_file() or path.stat().st_size == 0:
                raise ValueError("source missing or empty")
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            if item.get("sha256") != digest.hexdigest():
                raise ValueError("source hash mismatch")
            if "putUrl" in item:
                if not url_matches(
                    nonempty(item["putUrl"], "putUrl"), key, prefix,
                    nonempty(batch.get("storageHost"), "storageHost"),
                ):
                    raise ValueError("presigned URL path/host mismatch")
            covered.add(rid)
        except (ValueError, OSError, TypeError) as exc:
            issues.append({"fileIndex": index, "error": str(exc)})
    for rid in sorted(set(record_ids) - covered):
        issues.append({"recordId": rid, "error": "no validated files for recordId"})
    return {"batchId": batch_id, "recordCount": len(record_ids),
            "fileCount": len(files), "ok": not issues, "issues": issues}


def unwrap_rows(data: dict) -> list[dict]:
    if not isinstance(data, dict):
        raise ValueError("live list: expected successful response object")
    if "actions" in data:
        actions = data["actions"]
        if not isinstance(actions, list) or len(actions) != 1:
            raise ValueError("select exactly one captured list action")
        action = actions[0]
        if not isinstance(action, dict) or action.get("state") != "SUCCESS":
            raise ValueError("Aura list action failed")
        rows = action.get("returnValue")
        for _ in range(4):
            if not isinstance(rows, dict) or "returnValue" not in rows:
                break
            rows = rows["returnValue"]
    else:
        if data.get("state") != "SUCCESS":
            raise ValueError("normalized list response failed")
        rows = data.get("rows")
    if not isinstance(rows, list):
        raise ValueError("live list: missing rows")
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("live list: invalid row")
        nonempty(row.get("meetingId"), "meetingId")
    return rows


def verify_targets(target_ids: list[str], data: dict) -> dict:
    if not isinstance(target_ids, list) or not target_ids:
        raise ValueError("targets: expected non-empty list")
    for rid in target_ids:
        nonempty(rid, "targetId")
    if len(set(target_ids)) != len(target_ids):
        raise ValueError("targets: duplicates")
    rows = unwrap_rows(data)
    counts = Counter(row["meetingId"] for row in rows)
    duplicates = sorted(rid for rid, count in counts.items() if count > 1)
    by_id = {row["meetingId"]: row for row in rows}
    target_rows = [by_id[rid] for rid in target_ids if rid in by_id]
    missing = [rid for rid in target_ids if rid not in by_id]
    incomplete = [
        {"recordId": row["meetingId"], "missingFields": [
            field for field in UPLOAD_FIELDS if row.get(field) not in ("✔️", "✔")
        ]} for row in target_rows
        if any(row.get(field) not in ("✔️", "✔") for field in UPLOAD_FIELDS)
    ]

    def status_counts(selected: list[dict]) -> dict:
        return dict(Counter(row.get("supportFileCheckStatus") or "UNKNOWN" for row in selected))

    return {
        "projectRowCount": len(rows), "targetCount": len(target_ids),
        "targetPresentCount": len(target_rows),
        "targetRegistrationCompleteCount": len(target_rows) - len(incomplete),
        "projectApprovalStatuses": status_counts(rows),
        "targetApprovalStatuses": status_counts(target_rows),
        "missingCurrentTargetIds": missing, "incompleteTargetRows": incomplete,
        "duplicateMeetingIds": duplicates,
        "ok": not (missing or incomplete or duplicates),
        "meaning": "registration columns only; verify PUT/object/card evidence separately",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    batch_parser = sub.add_parser("batch")
    batch_parser.add_argument("manifest", type=Path)
    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("targets", type=Path)
    verify_parser.add_argument("live_list", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "batch":
            result = validate_batch(json.loads(args.manifest.read_text(encoding="utf-8")),
                                    args.manifest.resolve().parent)
        else:
            result = verify_targets(json.loads(args.targets.read_text(encoding="utf-8")),
                                    json.loads(args.live_list.read_text(encoding="utf-8")))
    except (ValueError, OSError, TypeError) as exc:
        # JSON parser messages omit source contents; never print raw session/URL input.
        result = {"ok": False, "error": str(exc)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    sys.exit(main())
