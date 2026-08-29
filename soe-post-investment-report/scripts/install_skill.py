#!/usr/bin/env python3
"""Install this skill locally or build a portable skill ZIP.

Supported locations:

* user level: Codex, Claude and Qoder;
* project level: Trae IDE, Trae CLI and WorkBuddy/CodeBuddy;
* portable: a ZIP whose top-level directory is the skill slug.

Destinations are never replaced unless ``--force`` is supplied.  Even with
``--force``, an existing destination is renamed to a timestamped backup so the
operation remains recoverable.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fnmatch
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import uuid
from zipfile import ZIP_DEFLATED, ZipFile


SKILL_ROOT = Path(__file__).resolve().parent.parent
EXCLUDED_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".DS_Store",
    "Thumbs.db",
    # Local full-page render QA is intentionally excluded from portable skill
    # packages. The public asset is the single sanitized preview.png only.
    "reference-render",
}
EXCLUDED_PATTERNS = ("*.pyc", "*.pyo", "*.swp", "*~", "~$*")
FORBIDDEN_PACKAGE_SUFFIXES = {
    ".ttf", ".otf", ".ttc", ".woff", ".woff2",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".pdf",
    ".zip", ".7z", ".rar", ".pem", ".key", ".pfx", ".p12",
}
FORBIDDEN_PACKAGE_NAMES = {".env", "id_rsa", "id_ed25519", "credentials.json"}
MAX_PACKAGE_FILE_BYTES = 25 * 1024 * 1024
USER_TARGETS = {"codex", "claude", "qoder"}
PROJECT_TARGETS = {"trae", "trae-cli", "workbuddy"}


class InstallError(RuntimeError):
    """A user-actionable installation failure."""


def configure_utf8_stdio() -> None:
    """Prefer readable Unicode CLI output without affecting module imports."""

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass


def _emit(payload: dict[str, object], *, stream: object = sys.stdout) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2), file=stream)


def _skill_name() -> str:
    skill_md = SKILL_ROOT / "SKILL.md"
    if not skill_md.is_file():
        raise InstallError(f"SKILL.md not found: {skill_md}")
    text = skill_md.read_text(encoding="utf-8")
    match = re.search(r"(?m)^name:\s*([a-z0-9-]+)\s*$", text)
    if not match:
        raise InstallError("SKILL.md must declare a lowercase-hyphen 'name' field")
    name = match.group(1)
    if name != SKILL_ROOT.name:
        raise InstallError(f"Skill folder '{SKILL_ROOT.name}' does not match SKILL.md name '{name}'")
    return name


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _excluded(relative: Path) -> bool:
    return any(part in EXCLUDED_NAMES for part in relative.parts) or any(
        fnmatch.fnmatch(relative.name, pattern) for pattern in EXCLUDED_PATTERNS
    )


def package_files() -> list[Path]:
    files: list[Path] = []
    for path in sorted(SKILL_ROOT.rglob("*")):
        relative = path.relative_to(SKILL_ROOT)
        if _excluded(relative):
            continue
        if path.is_symlink():
            raise InstallError(f"Symbolic links are refused in portable skill packages: {path}")
        if path.is_file():
            if path.stat().st_size > MAX_PACKAGE_FILE_BYTES:
                raise InstallError(f"Oversized file refused from portable skill package: {relative}")
            suffix = path.suffix.casefold()
            if path.name.casefold() in FORBIDDEN_PACKAGE_NAMES:
                raise InstallError(f"Sensitive filename refused from portable skill package: {relative}")
            if suffix in FORBIDDEN_PACKAGE_SUFFIXES:
                if relative.as_posix() != "assets/reference-template.docx":
                    raise InstallError(f"Sensitive or raw artifact refused from portable skill package: {relative}")
            files.append(path)
    if SKILL_ROOT / "SKILL.md" not in files:
        raise InstallError("The package would not contain SKILL.md")
    return files


def target_base(target: str, project: Path | None) -> Path:
    if target in USER_TARGETS:
        if project is not None:
            raise InstallError(f"--project is not valid for the user-level target '{target}'")
        home = Path.home()
        if target == "codex":
            codex_home = Path(os.environ.get("CODEX_HOME", str(home / ".codex"))).expanduser()
            return (codex_home / "skills").resolve()
        if target == "claude":
            claude_home = Path(os.environ.get("CLAUDE_CONFIG_DIR", str(home / ".claude"))).expanduser()
            return (claude_home / "skills").resolve()
        qoder_home = Path(os.environ.get("QODER_HOME", str(home / ".qoder"))).expanduser()
        return (qoder_home / "skills").resolve()

    if project is None:
        raise InstallError(f"--project is required for the project-level target '{target}'")
    project = project.expanduser().resolve()
    if not project.is_dir():
        raise InstallError(f"Project directory not found: {project}")
    relative = {
        "trae": Path(".trae") / "skills",
        "trae-cli": Path(".traecli") / "skills",
        "workbuddy": Path(".codebuddy") / "skills",
    }[target]
    return (project / relative).resolve()


def _validate_destination(destination: Path, skill_name: str) -> None:
    if destination.name != skill_name:
        raise InstallError(f"Unsafe destination name: {destination}")
    resolved = destination.resolve()
    if resolved == Path(resolved.anchor) or resolved == Path.home().resolve():
        raise InstallError(f"Refusing broad destination: {resolved}")
    if _is_relative_to(resolved, SKILL_ROOT.resolve()):
        raise InstallError("Refusing to install the skill inside its own source directory")


def _backup_path(destination: Path, *, backup_root: Path | None = None) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    root = backup_root or destination.parent
    candidate = root / f"{destination.name}.backup-{stamp}"
    index = 1
    while candidate.exists():
        candidate = root / f"{destination.name}.backup-{stamp}-{index}"
        index += 1
    return candidate


def _copy_package(staged: Path, files: list[Path]) -> None:
    for source in files:
        relative = source.relative_to(SKILL_ROOT)
        destination = staged / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def install(target: str, project: Path | None, force: bool, dry_run: bool) -> dict[str, object]:
    skill_name = _skill_name()
    files = package_files()
    base = target_base(target, project)
    destination = base / skill_name
    _validate_destination(destination, skill_name)
    if destination.exists() and not force:
        raise InstallError(f"Destination already exists; rerun with --force to replace it: {destination}")
    if dry_run:
        return {
            "ok": True,
            "operation": "install",
            "dry_run": True,
            "target": target,
            "destination": str(destination),
            "files": len(files),
            "would_backup_existing": destination.exists(),
        }

    base.mkdir(parents=True, exist_ok=True)
    temp_parent = Path(tempfile.mkdtemp(prefix=f".{skill_name}.stage-", dir=base))
    staged = temp_parent / skill_name
    backup: Path | None = None
    try:
        staged.mkdir()
        _copy_package(staged, files)
        if destination.exists():
            backup_root = base.parent / "skill-backups"
            backup_root.mkdir(parents=True, exist_ok=True)
            backup = _backup_path(destination, backup_root=backup_root)
            destination.rename(backup)
        try:
            staged.rename(destination)
        except Exception:
            if backup is not None and backup.exists() and not destination.exists():
                backup.rename(destination)
            raise
    finally:
        shutil.rmtree(temp_parent, ignore_errors=True)
    return {
        "ok": True,
        "operation": "install",
        "dry_run": False,
        "target": target,
        "destination": str(destination),
        "files": len(files),
        "backup": str(backup) if backup else None,
    }


def build_zip(output: Path, force: bool, dry_run: bool) -> dict[str, object]:
    skill_name = _skill_name()
    files = package_files()
    output = output.expanduser().resolve()
    if output.suffix.casefold() != ".zip":
        raise InstallError("--zip output must use the .zip extension")
    if _is_relative_to(output, SKILL_ROOT.resolve()):
        raise InstallError("Refusing to write the ZIP inside the skill source directory")
    if output.exists() and not force:
        raise InstallError(f"ZIP already exists; rerun with --force to replace it: {output}")
    if dry_run:
        return {
            "ok": True,
            "operation": "zip",
            "dry_run": True,
            "zip": str(output),
            "files": len(files),
            "would_backup_existing": output.exists(),
        }

    output.parent.mkdir(parents=True, exist_ok=True)
    temp_output = output.parent / f".{output.name}.tmp-{uuid.uuid4().hex}"
    backup: Path | None = None
    try:
        with ZipFile(temp_output, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
            for source in files:
                relative = source.relative_to(SKILL_ROOT).as_posix()
                archive.write(source, f"{skill_name}/{relative}")
        with ZipFile(temp_output) as archive:
            if f"{skill_name}/SKILL.md" not in archive.namelist():
                raise InstallError("ZIP verification failed: SKILL.md is missing")
            bad_member = archive.testzip()
            if bad_member is not None:
                raise InstallError(f"ZIP verification failed at member: {bad_member}")
        if output.exists():
            backup = _backup_path(output)
            output.rename(backup)
        try:
            os.replace(temp_output, output)
        except Exception:
            if backup is not None and backup.exists() and not output.exists():
                backup.rename(output)
            raise
    finally:
        temp_output.unlink(missing_ok=True)
    return {
        "ok": True,
        "operation": "zip",
        "dry_run": False,
        "zip": str(output),
        "files": len(files),
        "size_bytes": output.stat().st_size,
        "backup": str(backup) if backup else None,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--target",
        choices=sorted(USER_TARGETS | PROJECT_TARGETS),
        help="install to a supported user-level or project-level skill directory",
    )
    mode.add_argument("--zip", dest="zip_path", type=Path, help="build a portable ZIP package")
    parser.add_argument("--project", type=Path, help="project root for Trae, Trae CLI or WorkBuddy")
    parser.add_argument("--force", action="store_true", help="replace while retaining a timestamped backup")
    parser.add_argument("--dry-run", action="store_true", help="validate and report paths without writing")
    return parser.parse_args()


def main() -> int:
    configure_utf8_stdio()
    args = parse_args()
    try:
        if args.zip_path is not None:
            if args.project is not None:
                raise InstallError("--project cannot be combined with --zip")
            result = build_zip(args.zip_path, args.force, args.dry_run)
        else:
            result = install(args.target, args.project, args.force, args.dry_run)
        _emit(result)
        return 0
    except (InstallError, OSError) as exc:
        _emit({"ok": False, "error": str(exc)}, stream=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
