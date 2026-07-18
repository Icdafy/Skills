#!/usr/bin/env python3
"""Check or install fonts required by the fixed meeting-minutes DOCX format."""

from __future__ import annotations

import argparse
import ctypes
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any


SKILL_DIR = Path(__file__).resolve().parent.parent
FONT_DIR = SKILL_DIR / "assets" / "fonts"

FONT_SPECS: tuple[dict[str, Any], ...] = (
    {
        "family": "FZXiaoBiaoSong-B05S",
        "aliases": ("FZXiaoBiaoSong-B05S", "方正小标宋简体"),
        "asset": "方正小标宋简体.ttf",
        "registry_name": "方正小标宋简体 (TrueType)",
    },
    {
        "family": "KaiTi_GB2312",
        "aliases": ("KaiTi_GB2312", "楷体_GB2312"),
        "asset": "楷体_GB2312.ttf",
        "registry_name": "楷体_GB2312 (TrueType)",
    },
    {
        "family": "FangSong_GB2312",
        "aliases": ("FangSong_GB2312", "仿宋_GB2312"),
        "asset": "simfang.ttf",
        "registry_name": "仿宋_GB2312 (TrueType)",
    },
    {
        "family": "SimHei",
        "aliases": ("SimHei", "simhei.ttf"),
        "asset": None,
        "registry_name": None,
    },
    {
        # Arabic numerals throughout the minutes are set in Times New Roman.
        "family": "Times New Roman",
        "aliases": ("Times New Roman", "times.ttf", "timesnewroman"),
        "asset": None,
        "registry_name": None,
    },
)


def _windows_catalog() -> str:
    import winreg

    records: list[str] = []
    locations = (
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows NT\CurrentVersion\Fonts"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"),
    )
    for hive, path in locations:
        try:
            with winreg.OpenKey(hive, path) as key:
                index = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, index)
                    except OSError:
                        break
                    records.append(f"{name} {value}")
                    index += 1
        except OSError:
            continue
    return "\n".join(records).casefold()


def _portable_catalog() -> str:
    command = shutil.which("fc-list")
    if command:
        proc = subprocess.run(
            [command, ":", "family", "file"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if proc.returncode == 0:
            return proc.stdout.casefold()

    candidates = [Path.home() / ".local" / "share" / "fonts"]
    if sys.platform == "darwin":
        candidates.append(Path.home() / "Library" / "Fonts")
    files: list[str] = []
    for directory in candidates:
        if directory.is_dir():
            files.extend(str(path) for path in directory.glob("*"))
    return "\n".join(files).casefold()


def required_font_status() -> list[dict[str, Any]]:
    catalog = _windows_catalog() if os.name == "nt" else _portable_catalog()
    status: list[dict[str, Any]] = []
    for spec in FONT_SPECS:
        aliases = tuple(alias.casefold() for alias in spec["aliases"])
        asset = spec["asset"]
        installed = any(alias in catalog for alias in aliases)
        status.append(
            {
                "family": spec["family"],
                "installed": installed,
                "bundled_asset": asset,
            }
        )
    return status


def _install_windows(specs: list[dict[str, Any]]) -> list[str]:
    import winreg

    destination_dir = Path(os.environ["LOCALAPPDATA"]) / "Microsoft" / "Windows" / "Fonts"
    destination_dir.mkdir(parents=True, exist_ok=True)
    installed: list[str] = []
    registry_path = r"Software\Microsoft\Windows NT\CurrentVersion\Fonts"
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, registry_path) as key:
        for spec in specs:
            source = FONT_DIR / spec["asset"]
            if not source.is_file():
                raise FileNotFoundError(f"找不到字体资源：{source}")
            destination = destination_dir / source.name
            if not destination.exists() or source.read_bytes() != destination.read_bytes():
                shutil.copy2(source, destination)
            winreg.SetValueEx(
                key,
                spec["registry_name"],
                0,
                winreg.REG_SZ,
                str(destination),
            )
            ctypes.windll.gdi32.AddFontResourceExW(str(destination), 0x10, 0)
            installed.append(spec["family"])

    result = ctypes.c_ulong()
    ctypes.windll.user32.SendMessageTimeoutW(
        0xFFFF, 0x001D, 0, 0, 0x0002, 1000, ctypes.byref(result)
    )
    return installed


def _install_portable(specs: list[dict[str, Any]]) -> list[str]:
    destination_dir = (
        Path.home() / "Library" / "Fonts"
        if sys.platform == "darwin"
        else Path.home() / ".local" / "share" / "fonts"
    )
    destination_dir.mkdir(parents=True, exist_ok=True)
    installed: list[str] = []
    for spec in specs:
        source = FONT_DIR / spec["asset"]
        if not source.is_file():
            raise FileNotFoundError(f"找不到字体资源：{source}")
        shutil.copy2(source, destination_dir / source.name)
        installed.append(spec["family"])
    cache_command = shutil.which("fc-cache")
    if cache_command:
        subprocess.run([cache_command, "-f", str(destination_dir)], check=False)
    return installed


def install_user_fonts() -> list[str]:
    status_by_family = {item["family"]: item for item in required_font_status()}
    specs = [
        spec
        for spec in FONT_SPECS
        if spec["asset"] and not status_by_family[spec["family"]]["installed"]
    ]
    if not specs:
        return []
    return _install_windows(specs) if os.name == "nt" else _install_portable(specs)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true", help="check required fonts without changes")
    action.add_argument(
        "--install-user",
        action="store_true",
        help="install bundled fonts for the current user; obtain permission first",
    )
    args = parser.parse_args()

    installed_now: list[str] = []
    if args.install_user:
        installed_now = install_user_fonts()
    status = required_font_status()
    ready = all(item["installed"] for item in status)
    print(
        json.dumps(
            {
                "ready": ready,
                "platform": sys.platform,
                "installed_now": installed_now,
                "fonts": status,
                "restart_office_apps": bool(installed_now),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
