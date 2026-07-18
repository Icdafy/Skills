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
import shutil
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

# Hardware tiers drive the dual-engine strategy. The tier is advisory and
# degrades gracefully — no tier ever blocks producing the minutes; it only
# changes how deep the dual-engine assurance goes and how long it takes.
TIER_ADVICE = {
    "T0": "仅用 funasr 引擎完成主转录；确需双引擎复核时加 --budget-minutes 10 "
          "严控重转耗时，避免 qwen 引擎的 --timestamps（对齐模型内存占用高）。",
    "T1": "默认档：funasr 主转录＋refine_transcript.py 定向复核（Qwen3-ASR-0.6B）；"
          "录音很长时加 --budget-minutes 控制复核耗时。",
    "T2": "可在征得用户同意后改用 --model Qwen/Qwen3-ASR-1.7B，扩大复核覆盖，"
          "或启用 --voter sensevoice 第三引擎三取二投票。",
    "T3": "可全量双引擎转录（refine_transcript.py --all 或 fact_check.py --compare），"
          "并启用 --voter sensevoice 三取二投票获得最高保障。",
}


def total_ram_gb() -> float | None:
    """Physical RAM in GiB via stdlib only; None when undetectable."""
    try:
        if os.name == "nt":
            import ctypes

            class MemoryStatusEx(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MemoryStatusEx()
            status.dwLength = ctypes.sizeof(MemoryStatusEx)
            if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return None
            return status.ullTotalPhys / 2**30
        if sys.platform == "darwin":
            proc = subprocess.run(["sysctl", "-n", "hw.memsize"],
                                  capture_output=True, text=True, timeout=10, check=False)
            return int(proc.stdout.strip()) / 2**30 if proc.returncode == 0 else None
        with open("/proc/meminfo", encoding="ascii") as handle:
            for line in handle:
                if line.startswith("MemTotal:"):
                    return int(line.split()[1]) / 2**20
    except Exception:
        return None
    return None


def cuda_vram_gb() -> tuple[float | None, str | None]:
    """Largest NVIDIA GPU's VRAM in GiB via nvidia-smi; (None, None) without CUDA."""
    try:
        proc = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total,name",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return None, None
        best_gb, best_name = 0.0, None
        for line in proc.stdout.strip().splitlines():
            memory_mb, _, name = line.partition(",")
            gigabytes = float(memory_mb.strip()) / 1024
            if gigabytes > best_gb:
                best_gb, best_name = gigabytes, name.strip()
        return (best_gb, best_name) if best_name else (None, None)
    except Exception:
        return None, None


def classify_tier(ram_gb: float | None, vram_gb: float | None) -> tuple[str, str]:
    """Map hardware to a tier. Unknown RAM defaults to T1, never to a block."""
    if vram_gb is not None and vram_gb >= 16:
        return "T3", f"CUDA 显存 {vram_gb:.0f}GB"
    if vram_gb is not None and vram_gb >= 8:
        return "T2", f"CUDA 显存 {vram_gb:.0f}GB"
    if ram_gb is None:
        return "T1", "无法探测内存，按默认档处理"
    if ram_gb >= 12:
        return "T1", f"内存 {ram_gb:.0f}GB，无充足 CUDA 显存"
    return "T0", f"内存 {ram_gb:.0f}GB 偏小"


def hardware_report() -> dict:
    ram = total_ram_gb()
    vram, gpu_name = cuda_vram_gb()
    disk_free = None
    try:
        disk_free = shutil.disk_usage(Path.home()).free / 2**30
    except Exception:
        pass
    return {
        "ram_gb": round(ram, 1) if ram is not None else None,
        "cpu_cores": os.cpu_count(),
        "cuda": vram is not None,
        "gpu_name": gpu_name,
        "vram_gb": round(vram, 1) if vram is not None else None,
        "disk_free_gb": round(disk_free, 1) if disk_free is not None else None,
    }


def attach_tier(result: dict) -> None:
    """Add hardware facts and the T0–T3 recommendation to a probe/install result."""
    hardware = hardware_report()
    tier, reason = classify_tier(hardware.get("ram_gb"), hardware.get("vram_gb"))
    advice = TIER_ADVICE[tier]
    engines = result.get("engines") or {}
    if tier != "T0" and not engines.get("qwen"):
        advice += " 当前未安装 qwen 引擎：执行双引擎复核前先 --install --engine qwen。"
    result["hardware"] = hardware
    result["tier"] = tier
    result["tier_reason"] = reason
    result["tier_advice"] = advice


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
        "runtime_dir": str(python.parent.parent.parent),
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
    attach_tier(result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ready") else 2


if __name__ == "__main__":
    raise SystemExit(main())
