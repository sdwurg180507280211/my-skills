#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"

FORBIDDEN_PARTS = {
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    "output",
    "dist",
    "build",
}
FORBIDDEN_SUFFIXES = {".pyc", ".pyo"}
GIT_BLOB_RE = re.compile(r"^[0-9a-f]{40}$")


def repository_files() -> list[Path]:
    """Tracked files plus untracked ones Git would add; ignored caches stay local."""
    try:
        out = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            capture_output=True, check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return list(ROOT.rglob("*"))
    return [ROOT / rel for rel in out.decode().split("\0") if rel]


def parse_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("missing YAML frontmatter")
    end = text.find("\n---", 4)
    if end < 0:
        raise ValueError("unterminated YAML frontmatter")
    block = text[4:end]
    data: dict[str, str] = {}
    for line in block.splitlines():
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if match:
            data[match.group(1)] = match.group(2).strip().strip('"\'')
    return data


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def validate_upstream_locks(errors: list[str]) -> None:
    for lock_path in sorted(SKILLS_DIR.glob("*/UPSTREAM.lock.json")):
        rel_lock = lock_path.relative_to(ROOT)
        try:
            lock = json.loads(lock_path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"{rel_lock}: invalid upstream lock: {exc}")
            continue

        files = lock.get("files")
        if lock.get("schema_version") != 1 or not isinstance(files, list) or not files:
            errors.append(f"{rel_lock}: expected schema_version=1 and non-empty files")
            continue

        for index, item in enumerate(files, start=1):
            if not isinstance(item, dict):
                errors.append(f"{rel_lock}: files[{index}] must be an object")
                continue

            item_path = item.get("path")
            expected = item.get("vendored_blob")
            source_commit = item.get("source_commit")
            source_blob = item.get("source_blob")
            if not isinstance(item_path, str) or not item_path:
                errors.append(f"{rel_lock}: files[{index}] missing path")
                continue
            if not isinstance(expected, str) or not GIT_BLOB_RE.fullmatch(expected):
                errors.append(f"{rel_lock}: files[{index}] invalid vendored_blob")
                continue
            if not isinstance(source_commit, str) or not GIT_BLOB_RE.fullmatch(source_commit):
                errors.append(f"{rel_lock}: files[{index}] invalid source_commit")
            if not isinstance(source_blob, str) or not GIT_BLOB_RE.fullmatch(source_blob):
                errors.append(f"{rel_lock}: files[{index}] invalid source_blob")

            target = (ROOT / item_path).resolve()
            try:
                target.relative_to(ROOT.resolve())
            except ValueError:
                errors.append(f"{rel_lock}: locked path escapes repo: {item_path}")
                continue
            if not target.is_file():
                errors.append(f"{rel_lock}: locked file missing: {item_path}")
                continue

            actual = git_blob_sha1(target)
            if actual != expected:
                errors.append(
                    f"{rel_lock}: vendored file drifted: {item_path} "
                    f"expected {expected}, got {actual}"
                )


def main() -> int:
    errors: list[str] = []

    if not SKILLS_DIR.is_dir():
        errors.append("missing skills/ directory")
        skill_dirs: list[Path] = []
    else:
        skill_dirs = sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir())

    names: set[str] = set()
    for skill_dir in skill_dirs:
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            errors.append(f"{skill_dir.relative_to(ROOT)}: missing SKILL.md")
            continue
        try:
            meta = parse_frontmatter(skill_md)
        except Exception as exc:
            errors.append(f"{skill_md.relative_to(ROOT)}: {exc}")
            continue
        name = meta.get("name", "")
        description = meta.get("description", "")
        if not name:
            errors.append(f"{skill_md.relative_to(ROOT)}: missing frontmatter name")
        elif name != skill_dir.name:
            errors.append(
                f"{skill_md.relative_to(ROOT)}: name '{name}' != directory '{skill_dir.name}'"
            )
        if not description:
            errors.append(f"{skill_md.relative_to(ROOT)}: missing frontmatter description")
        if name in names:
            errors.append(f"duplicate skill name: {name}")
        names.add(name)

    for path in repository_files():
        rel = path.relative_to(ROOT)
        if any(part in FORBIDDEN_PARTS for part in rel.parts):
            errors.append(f"forbidden generated/cache path committed: {rel}")
        if path.is_file() and path.suffix in FORBIDDEN_SUFFIXES:
            errors.append(f"forbidden generated file committed: {rel}")
        if path.name == ".DS_Store":
            errors.append(f"forbidden OS metadata committed: {rel}")

    if MARKETPLACE.is_file():
        try:
            market = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
            referenced: set[str] = set()
            for plugin in market.get("plugins", []):
                for item in plugin.get("skills", []):
                    path = (ROOT / item).resolve()
                    try:
                        path.relative_to(ROOT.resolve())
                    except ValueError:
                        errors.append(f"marketplace path escapes repo: {item}")
                        continue
                    if not path.is_dir():
                        errors.append(f"marketplace references missing skill: {item}")
                        continue
                    referenced.add(path.name)
            missing = sorted(names - referenced)
            if missing:
                errors.append(f"skills missing from marketplace: {', '.join(missing)}")
        except Exception as exc:
            errors.append(f"invalid marketplace.json: {exc}")
    else:
        errors.append("missing .claude-plugin/marketplace.json")

    validate_upstream_locks(errors)

    if errors:
        print("Skill repository validation failed:\n", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"OK: validated {len(skill_dirs)} skills")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
