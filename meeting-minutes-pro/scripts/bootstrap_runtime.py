#!/usr/bin/env python3
"""Create or inspect the isolated runtime used by meeting-minutes-pro."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import venv


SKILL_DIR = Path(__file__).resolve().parent.parent
REQUIREMENTS = Path(__file__).resolve().parent / "requirements-runtime.txt"


def cache_root() -> Path:
    override = os.environ.get("QWEN3_ASR_SKILL_HOME")
    if override:
        return Path(override).expanduser().resolve()
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        # Keep this deliberately short. PyTorch wheels contain deeply nested
        # license paths that can still hit WinError 206 on Windows.
        return base / "q3asr06"
    return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "meeting-minutes-pro"


def runtime_python(root: Path) -> Path:
    if os.name == "nt":
        return root / "venv" / "Scripts" / "python.exe"
    return root / "venv" / "bin" / "python"


def probe(python: Path) -> dict[str, object]:
    result: dict[str, object] = {
        "skill_dir": str(SKILL_DIR),
        "runtime_dir": str(python.parent.parent),
        "python": str(python),
        "ready": False,
    }
    if not python.exists():
        result["reason"] = "runtime Python does not exist"
        return result
    code = (
        "import json, importlib.util; "
        "mods=['qwen_asr','torch','imageio_ffmpeg','docx']; "
        "print(json.dumps({m: importlib.util.find_spec(m) is not None for m in mods}))"
    )
    proc = subprocess.run(
        [str(python), "-c", code], capture_output=True, text=True, check=False
    )
    if proc.returncode != 0:
        result["reason"] = proc.stderr.strip() or "runtime probe failed"
        return result
    modules = json.loads(proc.stdout.strip())
    result["modules"] = modules
    result["ready"] = all(modules.values())
    if not result["ready"]:
        result["reason"] = "one or more runtime modules are missing"
    return result


def install(root: Path, upgrade: bool) -> dict[str, object]:
    if sys.version_info < (3, 10):
        raise RuntimeError("Python 3.10 or newer is required")
    if os.name == "nt" and len(str(root)) > 80:
        raise RuntimeError(
            "the Windows runtime path is too long for PyTorch; omit --runtime-dir "
            "or choose a path shorter than 80 characters"
        )
    root.mkdir(parents=True, exist_ok=True)
    python = runtime_python(root)
    if not python.exists():
        venv.EnvBuilder(with_pip=True, clear=False).create(root / "venv")
    pip_command = [
        str(python),
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--no-input",
        "-r",
        str(REQUIREMENTS),
    ]
    if upgrade:
        pip_command.insert(4, "--upgrade")
    subprocess.run(pip_command, check=True)
    result = probe(python)
    if not result.get("ready"):
        raise RuntimeError(f"runtime installation did not validate: {result}")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true", help="inspect the isolated runtime")
    action.add_argument("--install", action="store_true", help="create and populate the runtime")
    parser.add_argument("--upgrade", action="store_true", help="upgrade pinned-compatible dependencies")
    parser.add_argument("--runtime-dir", type=Path, help="override the runtime cache directory")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = (args.runtime_dir or cache_root()).expanduser().resolve()
    python = runtime_python(root)
    try:
        result = install(root, args.upgrade) if args.install else probe(python)
    except Exception as exc:
        print(json.dumps({"ready": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ready") else 2


if __name__ == "__main__":
    raise SystemExit(main())
