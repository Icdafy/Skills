#!/usr/bin/env python3
"""Install this skill into Codex, Claude Code, and/or Tencent WorkBuddy."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil


SKILL_DIR = Path(__file__).resolve().parent.parent
SKILL_NAME = SKILL_DIR.name


def destinations() -> dict[str, Path]:
    home = Path.home()
    codex_root = Path(os.environ.get("CODEX_HOME", home / ".codex")).expanduser()
    claude_root = Path(os.environ.get("CLAUDE_CONFIG_DIR", home / ".claude")).expanduser()
    return {
        "codex": codex_root / "skills" / SKILL_NAME,
        "claude": claude_root / "skills" / SKILL_NAME,
        "workbuddy": home / ".workbuddy" / "skills" / SKILL_NAME,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        choices=["codex", "claude", "workbuddy", "all"],
        action="append",
        default=[],
        help="repeat to install more than one target; default is all",
    )
    parser.add_argument("--force", action="store_true", help="replace an existing installation")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def ignore(_directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name in {"__pycache__", ".DS_Store"} or name.endswith(".pyc")}


def main() -> int:
    args = parse_args()
    requested = set(args.target or ["all"])
    selected = list(destinations()) if "all" in requested else sorted(requested)
    results: list[dict[str, str]] = []
    for target in selected:
        destination = destinations()[target]
        status = "planned" if args.dry_run else "installed"
        if not args.dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.resolve() == SKILL_DIR.resolve():
                results.append({
                    "target": target,
                    "path": str(destination),
                    "status": "already installed; source and destination are identical",
                })
                continue
            if destination.exists() or destination.is_symlink():
                if not args.force:
                    results.append({"target": target, "path": str(destination), "status": "exists; use --force"})
                    continue
                if destination.is_symlink() or destination.is_file():
                    destination.unlink()
                else:
                    shutil.rmtree(destination)
            shutil.copytree(SKILL_DIR, destination, ignore=ignore)
        results.append({"target": target, "path": str(destination), "status": status})
    print(json.dumps({"skill": SKILL_NAME, "results": results}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
