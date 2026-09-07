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
    private = set(names) - {"README.md", "industry"} if Path(_directory).name == "glossary" else set()
    return private | {name for name in names if name in {"__pycache__", ".DS_Store", ".git"}
                      or name.endswith(".pyc") or (Path(_directory) / name).is_symlink()}


def install_to(source: Path, destination: Path, force: bool = False) -> str:
    source = source.resolve()
    resolved = destination.resolve()
    if source == resolved:
        return "already installed; source and destination are identical"
    if source in resolved.parents or resolved in source.parents:
        raise ValueError("安装源和目标不能互相包含")
    if destination.is_symlink() or (destination.exists() and not destination.is_dir()):
        raise ValueError("目标必须为真实目录，不覆盖文件或符号链接")
    if destination.exists() and not force:
        return "exists; use --force"
    # No whole-directory deletion: project glossaries and banned phrases are
    # user data. Refuse destination links so updates cannot escape the target.
    if destination.exists():
        for path in destination.rglob("*"):
            if path.is_symlink():
                raise ValueError(f"目标内含符号链接，需先明确处理：{path}")
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination, dirs_exist_ok=True, ignore=ignore)
    return "installed; local user data preserved"


def main() -> int:
    args = parse_args()
    requested = set(args.target or ["all"])
    selected = list(destinations()) if "all" in requested else sorted(requested)
    results: list[dict[str, str]] = []
    for target in selected:
        destination = destinations()[target]
        status = "planned" if args.dry_run else "installed"
        if not args.dry_run:
            status = install_to(SKILL_DIR, destination, args.force)
        results.append({"target": target, "path": str(destination), "status": status})
    print(json.dumps({"skill": SKILL_NAME, "results": results}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
