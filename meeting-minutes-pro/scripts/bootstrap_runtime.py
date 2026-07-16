#!/usr/bin/env python3
"""Create or inspect the isolated runtime used by meeting-minutes-pro.

The runtime hosts a shared base (ffmpeg wrapper + python-docx) plus one or
both ASR engines: funasr (default; Paraformer pipeline from ModelScope) and
qwen (Qwen3-ASR Transformers backend). Select engines with --engine.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import venv


SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
REQUIREMENTS_BASE = SCRIPTS_DIR / "requirements-runtime.txt"
REQUIREMENTS_ENGINE = {
    "funasr": SCRIPTS_DIR / "requirements-funasr.txt",
    "qwen": SCRIPTS_DIR / "requirements-qwen.txt",
}

BASE_MODULES = ("imageio_ffmpeg", "docx")
ENGINE_MODULES = {"funasr": "funasr", "qwen": "qwen_asr"}


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
    modules = list(BASE_MODULES) + ["torch"] + list(ENGINE_MODULES.values())
    code = (
        "import json, importlib.util; "
        f"mods={modules!r}; "
        "print(json.dumps({m: importlib.util.find_spec(m) is not None for m in mods}))"
    )
    proc = subprocess.run(
        [str(python), "-c", code], capture_output=True, text=True, check=False
    )
    if proc.returncode != 0:
        result["reason"] = proc.stderr.strip() or "runtime probe failed"
        return result
    modules_found = json.loads(proc.stdout.strip())
    result["modules"] = modules_found
    result["engines"] = {
        name: modules_found.get(module, False) for name, module in ENGINE_MODULES.items()
    }
    base_ready = all(modules_found.get(m, False) for m in BASE_MODULES)
    any_engine = any(result["engines"].values())
    result["ready"] = base_ready and modules_found.get("torch", False) and any_engine
    if not result["ready"]:
        if not base_ready:
            result["reason"] = "base runtime modules are missing"
        elif not any_engine:
            result["reason"] = (
                "no ASR engine installed; rerun with --install --engine funasr (or qwen)"
            )
        else:
            result["reason"] = "torch is missing"
    return result


def install(root: Path, upgrade: bool, engines: list[str]) -> dict[str, object]:
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
    requirement_files = [REQUIREMENTS_BASE] + [REQUIREMENTS_ENGINE[e] for e in engines]
    pip_command = [
        str(python),
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--no-input",
    ]
    if upgrade:
        pip_command.append("--upgrade")
    for requirements in requirement_files:
        pip_command += ["-r", str(requirements)]
    subprocess.run(pip_command, check=True)
    result = probe(python)
    installed_engines = result.get("engines", {})
    missing = [e for e in engines if not installed_engines.get(e)]
    if not result.get("ready") or missing:
        raise RuntimeError(f"runtime installation did not validate: {result}")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true", help="inspect the isolated runtime")
    action.add_argument("--install", action="store_true", help="create and populate the runtime")
    parser.add_argument(
        "--engine",
        choices=("funasr", "qwen", "all"),
        default="funasr",
        help="ASR engine(s) to install (default: funasr)",
    )
    parser.add_argument("--upgrade", action="store_true", help="upgrade pinned-compatible dependencies")
    parser.add_argument("--runtime-dir", type=Path, help="override the runtime cache directory")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = (args.runtime_dir or cache_root()).expanduser().resolve()
    python = runtime_python(root)
    engines = list(ENGINE_MODULES) if args.engine == "all" else [args.engine]
    try:
        result = install(root, args.upgrade, engines) if args.install else probe(python)
    except Exception as exc:
        print(json.dumps({"ready": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ready") else 2


if __name__ == "__main__":
    raise SystemExit(main())
