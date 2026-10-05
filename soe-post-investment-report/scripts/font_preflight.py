#!/usr/bin/env python3
"""Read-only preflight for the six font families used by the report template.

No font is installed, copied, downloaded or modified.  On Windows the script
reads the per-user and machine font registries plus standard font directories;
on Linux/macOS it queries fontconfig when available and falls back to the usual
font directories.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unicodedata
from typing import Iterable


@dataclass(frozen=True)
class FontSpec:
    family: str
    role: str
    aliases: tuple[str, ...]


FONT_SPECS = (
    FontSpec(
        "方正小标宋简体",
        "official-document title",
        ("方正小标宋简体", "方正小标宋", "FZXiaoBiaoSong-B05S", "FZXBSJW", "FZXBSJW--GB1-0"),
    ),
    FontSpec(
        "仿宋_GB2312",
        "Chinese body text",
        ("仿宋_GB2312", "仿宋GB2312", "FangSong_GB2312", "FangSongGB2312"),
    ),
    FontSpec(
        "楷体_GB2312",
        "secondary headings and notes",
        ("楷体_GB2312", "楷体GB2312", "KaiTi_GB2312", "KaiTiGB2312"),
    ),
    FontSpec("黑体", "primary headings", ("黑体", "SimHei")),
    FontSpec("宋体", "page numbers and selected labels", ("宋体", "SimSun")),
    FontSpec("Times New Roman", "Latin letters and Arabic numerals", ("Times New Roman",)),
)

FONT_SUFFIXES = (
    "regular",
    "roman",
    "normal",
    "book",
    "medium",
    "bold",
    "italic",
    "bolditalic",
    "standard",
    "常规",
    "标准",
    "粗体",
    "斜体",
)


def configure_utf8_stdio() -> None:
    """Prefer readable Unicode CLI output without affecting module imports."""

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass


@dataclass(frozen=True)
class CatalogRecord:
    name: str
    source: str


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"[^0-9a-z\u3400-\u9fff]+", "", value)


def _name_matches(alias: str, candidate: str) -> bool:
    wanted = normalize(alias)
    actual = normalize(candidate)
    if not wanted or not actual:
        return False
    if actual == wanted:
        return True
    if actual.startswith(wanted):
        suffix = actual[len(wanted) :]
        return suffix in {normalize(item) for item in FONT_SUFFIXES}
    return False


def _font_files(directories: Iterable[Path]) -> list[CatalogRecord]:
    records: list[CatalogRecord] = []
    seen: set[Path] = set()
    for directory in directories:
        directory = directory.expanduser()
        if not directory.is_dir():
            continue
        try:
            candidates = directory.rglob("*")
            for path in candidates:
                if path.suffix.casefold() not in {".ttf", ".ttc", ".otf", ".otc"}:
                    continue
                try:
                    resolved = path.resolve()
                except OSError:
                    resolved = path
                if resolved in seen:
                    continue
                seen.add(resolved)
                records.append(CatalogRecord(path.stem, f"font file: {path}"))
        except OSError:
            continue
    return records


def windows_catalog() -> list[CatalogRecord]:
    import winreg

    records: list[CatalogRecord] = []
    locations = (
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows NT\CurrentVersion\Fonts", "HKCU"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts", "HKLM"),
    )
    for hive, key_path, label in locations:
        try:
            with winreg.OpenKey(hive, key_path) as key:
                index = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, index)
                    except OSError:
                        break
                    clean_name = re.sub(r"\s*\([^)]*\)\s*$", "", str(name)).strip()
                    records.append(CatalogRecord(clean_name, f"{label} registry: {name}"))
                    value_path = Path(str(value))
                    records.append(CatalogRecord(value_path.stem, f"{label} registry file: {value}"))
                    index += 1
        except OSError:
            continue
    windir = Path(os.environ.get("WINDIR", "C:/Windows"))
    local = os.environ.get("LOCALAPPDATA")
    directories = [windir / "Fonts"]
    if local:
        directories.append(Path(local) / "Microsoft" / "Windows" / "Fonts")
    records.extend(_font_files(directories))
    return records


def fontconfig_catalog() -> list[CatalogRecord]:
    command = shutil.which("fc-list")
    if not command:
        return []
    proc = subprocess.run(
        [command, "-f", "%{family}\t%{fullname}\t%{file}\n"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        check=False,
    )
    if proc.returncode != 0:
        return []
    records: list[CatalogRecord] = []
    for line in proc.stdout.splitlines():
        family, _, remainder = line.partition("\t")
        fullname, _, filename = remainder.partition("\t")
        for name in family.split(","):
            if name.strip():
                records.append(CatalogRecord(name.strip(), f"fontconfig family: {filename}"))
        if fullname.strip():
            records.append(CatalogRecord(fullname.strip(), f"fontconfig full name: {filename}"))
        if filename.strip():
            records.append(CatalogRecord(Path(filename.strip()).stem, f"fontconfig file: {filename}"))
    return records


def portable_catalog() -> list[CatalogRecord]:
    records = fontconfig_catalog()
    directories = [
        Path("/usr/share/fonts"),
        Path("/usr/local/share/fonts"),
        Path.home() / ".local" / "share" / "fonts",
        Path.home() / ".fonts",
    ]
    if sys.platform == "darwin":
        directories.extend(
            [Path("/System/Library/Fonts"), Path("/Library/Fonts"), Path.home() / "Library" / "Fonts"]
        )
    records.extend(_font_files(directories))
    return records


def deduplicate(records: Iterable[CatalogRecord]) -> list[CatalogRecord]:
    result: list[CatalogRecord] = []
    seen: set[tuple[str, str]] = set()
    for record in records:
        key = (record.name, record.source)
        if key not in seen:
            seen.add(key)
            result.append(record)
    return result


def check_fonts() -> tuple[list[dict[str, object]], int]:
    records = deduplicate(windows_catalog() if os.name == "nt" else portable_catalog())
    results: list[dict[str, object]] = []
    for spec in FONT_SPECS:
        matches = [
            record
            for record in records
            if any(_name_matches(alias, record.name) for alias in spec.aliases)
        ]
        results.append(
            {
                "family": spec.family,
                "role": spec.role,
                "installed": bool(matches),
                "evidence": [record.source for record in matches[:8]],
                "matched_names": sorted({record.name for record in matches})[:8],
            }
        )
    return results, len(records)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    return parser.parse_args()


def main() -> int:
    configure_utf8_stdio()
    args = parse_args()
    fonts, catalog_size = check_fonts()
    missing = [str(item["family"]) for item in fonts if not item["installed"]]
    payload = {
        "ready": not missing,
        "read_only": True,
        "platform": sys.platform,
        "catalog_records_examined": catalog_size,
        "fonts": fonts,
        "missing": missing,
        "note": (
            "All required families were detected. Restart Office if fonts were installed after it opened."
            if not missing
            else "Install properly licensed missing fonts, restart the renderer, and rerun this read-only check."
        ),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=None if args.compact else 2))
    return 0 if not missing else 2


if __name__ == "__main__":
    raise SystemExit(main())
