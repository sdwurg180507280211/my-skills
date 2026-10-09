#!/usr/bin/env python3
"""Link this repository's skills into local AI tool skill directories.

The repository is the single source of truth. Each tool directory only holds
symlinks back to ``skills/<name>``. The default run is a read-only check;
``--apply`` creates missing links and replaces identical copies after moving
them to a timestamped backup. Copies that differ from the repository and links
pointing elsewhere are left alone unless ``--force`` is given.
"""
from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
HOME = Path.home()

# Directories that load skills. Codex reads ~/.agents/skills.
DEFAULT_TARGETS = [
    HOME / ".claude/skills",
    HOME / ".agents/skills",
    HOME / ".workbuddy/skills",
]
# Legacy locations where repository skills should no longer be copied.
DEFAULT_RETIRE = [HOME / ".codex/skills"]
IGNORED = {".DS_Store", "__pycache__"}


def repo_skills() -> dict[str, Path]:
    return {
        p.name: p
        for p in sorted(SKILLS_DIR.iterdir())
        if p.is_dir() and (p / "SKILL.md").is_file()
    }


def same_tree(a: Path, b: Path) -> bool:
    cmp = filecmp.dircmp(a, b, ignore=list(IGNORED))
    if cmp.left_only or cmp.right_only or cmp.funny_files:
        return False
    _, mismatch, errors = filecmp.cmpfiles(a, b, cmp.common_files, shallow=False)
    if mismatch or errors:
        return False
    return all(same_tree(a / d, b / d) for d in cmp.common_dirs)


def state(entry: Path, source: Path) -> str:
    if entry.is_symlink():
        return "linked" if entry.resolve() == source.resolve() else "foreign-link"
    if not entry.exists():
        return "missing"
    if entry.is_dir():
        return "copy-same" if same_tree(source, entry) else "copy-diff"
    return "foreign-file"


def local_only(target: Path, names: set[str]) -> list[str]:
    if not target.is_dir():
        return []
    return sorted(
        p.name
        for p in target.iterdir()
        if p.name not in names and not p.name.startswith(".") and (p / "SKILL.md").is_file()
    )


def backup(entry: Path, backup_root: Path) -> Path:
    dest = backup_root / str(entry.parent).lstrip("/").replace("/", "_") / entry.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(entry), str(dest))
    return dest


def run(targets: list[Path], retire: list[Path], only: set[str], apply: bool,
        force: bool, backup_root: Path) -> int:
    skills = repo_skills()
    unknown = only - skills.keys()
    if unknown:
        print(f"unknown skills: {', '.join(sorted(unknown))}", file=sys.stderr)
        return 2
    selected = {n: p for n, p in skills.items() if not only or n in only}
    pending = 0

    for target in targets:
        print(f"\n== {target}")
        if apply:
            target.mkdir(parents=True, exist_ok=True)
        for name, source in selected.items():
            entry = target / name
            st = state(entry, source)
            action = ""
            if apply and st != "linked":
                replace = st == "copy-same" or (force and st != "missing")
                if st == "missing" or replace:
                    if replace:
                        action = f" (backup -> {backup(entry, backup_root)})"
                    entry.symlink_to(source)
                    st, action = "linked", " created" + action
                else:
                    action = " skipped: use --force after reviewing the difference"
            if st != "linked":
                pending += 1
            print(f"  {st:<13} {name}{action}")
        extra = local_only(target, set(skills))
        if extra:
            print(f"  local-only    {', '.join(extra)}")

    for legacy in retire:
        print(f"\n== {legacy} (retire repository copies)")
        for name, source in selected.items():
            entry = legacy / name
            if not entry.exists() and not entry.is_symlink():
                continue
            st = state(entry, source)
            action = ""
            if apply and (st in ("linked", "copy-same") or force):
                action = f" moved to backup -> {backup(entry, backup_root)}"
            else:
                pending += 1
            print(f"  {st:<13} {name}{action}")

    if not apply:
        print("\nRead-only check. Re-run with --apply to create links.")
    return 1 if pending and not apply else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("skills", nargs="*", help="limit to these skill names")
    parser.add_argument("--apply", action="store_true", help="create links and back up replaced copies")
    parser.add_argument("--force", action="store_true", help="also replace differing copies and foreign links")
    parser.add_argument("--target", action="append", type=Path, help="override target directories")
    parser.add_argument("--retire", action="append", type=Path, help="override legacy directories")
    parser.add_argument("--backup-root", type=Path,
                        default=HOME / ".skill-backups" / datetime.now().strftime("%Y%m%d-%H%M%S"))
    args = parser.parse_args()
    targets = [p.expanduser() for p in args.target] if args.target else DEFAULT_TARGETS
    retire = [p.expanduser() for p in args.retire] if args.retire is not None else DEFAULT_RETIRE
    return run(targets, retire, set(args.skills), args.apply, args.force, args.backup_root.expanduser())


if __name__ == "__main__":
    raise SystemExit(main())
