#!/usr/bin/env python3
"""Embed the bundled GB2312 fonts into a generated DOCX so it renders faithfully
on machines that do not have 仿宋_GB2312 / 楷体_GB2312 installed.

Self-contained (no cross-skill imports); a byte-identical copy lives in each
公文-DOCX skill because skills are independently distributable. Change the
gongsi-qingkuang copy, then run ``python tools/check_shared_scripts.py --sync``
to propagate it; ``python tools/check_shared_scripts.py`` fails on drift.
Uses the ECMA-376 obfuscated-font mechanism (content type
``application/vnd.openxmlformats-officedocument.obfuscatedFont``), which is
renderer-independent — Word and LibreOffice both honour it, no COM/soffice
round-trip. Only faces whose OS/2 fsType permits embedding are included;
方正小标宋简体 (fsType=2, restricted) is never embedded — consistent with it being
outlined rather than embedded in a PDF. ``verify_embedded_fonts`` reverses the
obfuscation and checks a valid sfnt header comes back, so a broken embedding
never ships silently; ``embed_bundled_fonts`` embeds via a temp file and only
replaces the original when verification passes.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import struct
import uuid
import zipfile

SCRIPT_DIR = Path(__file__).resolve().parent
FONT_DIR = SCRIPT_DIR.parent / "assets" / "fonts"

OBFUSCATED_FONT_CT = "application/vnd.openxmlformats-officedocument.obfuscatedFont"
FONT_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/font"
_SFNT_SIGNATURES = (b"\x00\x01\x00\x00", b"OTTO", b"true", b"ttcf")

# Fonts the 公文 DOCX uses that MIGHT be embeddable, mapped to the bundled TTF
# filenames seen across the skills (仿宋 is always simfang.ttf; 楷体 is either
# 楷体_GB2312.ttf or KaiTi_GB2312.ttf; 方正小标宋 varies but is fsType-restricted
# so it is always skipped by the fsType gate). The run name is the w:eastAsia
# value the generators write, so the embedded w:font w:name matches.
EMBED_TARGETS: dict[str, tuple[str, ...]] = {
    "仿宋_GB2312": ("simfang.ttf", "仿宋_GB2312.ttf", "FangSong_GB2312.ttf"),
    "楷体_GB2312": ("楷体_GB2312.ttf", "KaiTi_GB2312.ttf"),
    "方正小标宋简体": ("方正小标宋简体.ttf", "FZXiaoBiaoSongJT.ttf",
                 "FZXiaoBiaoSong-B05S.ttf"),
}


# --- Font-file inspection --------------------------------------------------
def read_fs_type(font: bytes) -> int | None:
    if len(font) < 12 or font[:4] not in _SFNT_SIGNATURES:
        return None
    num_tables = struct.unpack(">H", font[4:6])[0]
    offset = 12
    for _ in range(num_tables):
        if offset + 16 > len(font):
            break
        tag = font[offset:offset + 4]
        table_offset = struct.unpack(">I", font[offset + 8:offset + 12])[0]
        if tag == b"OS/2":
            if table_offset + 10 <= len(font):
                return struct.unpack(">H", font[table_offset + 8:table_offset + 10])[0]
            return None
        offset += 16
    return None


def is_embeddable(fs_type: int | None) -> bool:
    return fs_type is not None and not (fs_type & 0x0002)


def is_sfnt(data: bytes) -> bool:
    return data[:4] in _SFNT_SIGNATURES


# --- ECMA-376 §17.8.1 obfuscation (symmetric) ------------------------------
def _key_bytes(guid: str) -> bytes:
    hex_digits = re.sub(r"[^0-9A-Fa-f]", "", guid)
    if len(hex_digits) != 32:
        raise ValueError(f"字体 GUID 应为 128 位：{guid!r}")
    return bytes.fromhex(hex_digits)[::-1]


def obfuscate(font: bytes, guid: str) -> bytes:
    key = _key_bytes(guid)
    data = bytearray(font)
    for i in range(min(32, len(data))):
        data[i] ^= key[i % 16]
    return bytes(data)


deobfuscate = obfuscate


def new_font_key() -> str:
    return "{" + str(uuid.uuid4()).upper() + "}"


# --- Package surgery -------------------------------------------------------
def _add_content_type_default(content_types: str) -> str:
    if 'Extension="odttf"' in content_types:
        return content_types
    default = f'<Default Extension="odttf" ContentType="{OBFUSCATED_FONT_CT}"/>'
    return re.sub(r"(<Types[^>]*>)", r"\1" + default, content_types, count=1)


def _enable_font_embedding(settings: str) -> str:
    if "<w:embedTrueTypeFonts" in settings:
        return settings
    flags = '<w:embedTrueTypeFonts/><w:saveSubsetFonts w:val="false"/>'
    zoom = re.search(r"<w:zoom\b[^>]*/>", settings)
    if zoom:
        return settings[:zoom.end()] + flags + settings[zoom.end():]
    return re.sub(r"(<w:settings[^>]*>)", r"\1" + flags, settings, count=1)


def _font_table_entries(existing: str, embeds: list[tuple[str, str, str]]) -> str:
    additions: list[str] = []
    for name, rel_id, guid in embeds:
        if f'w:name="{name}"' in existing:
            continue
        additions.append(
            f'<w:font w:name="{name}">'
            f'<w:embedRegular r:id="{rel_id}" w:fontKey="{guid}"/>'
            f"</w:font>"
        )
    if not additions:
        return existing
    return existing.replace("</w:fonts>", "".join(additions) + "</w:fonts>", 1)


def _font_table_rels(existing: str | None, rels: list[tuple[str, str]]) -> str:
    entries = "".join(
        f'<Relationship Id="{rel_id}" Type="{FONT_REL_TYPE}" '
        f'Target="fonts/{target}"/>'
        for rel_id, target in rels
    )
    if existing and "</Relationships>" in existing:
        return existing.replace("</Relationships>", entries + "</Relationships>", 1)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
        'relationships">' + entries + "</Relationships>"
    )


def embed_fonts_into_docx(
    docx_path: Path, fonts: dict[str, Path], out_path: Path | None = None
) -> dict:
    """Embed each {run_name: ttf_path} that permits it; return a report."""
    docx_path = Path(docx_path)
    out_path = Path(out_path) if out_path else docx_path
    with zipfile.ZipFile(docx_path) as archive:
        parts = {info.filename: archive.read(info.filename)
                 for info in archive.infolist()}

    embedded: list[dict] = []
    skipped: list[dict] = []
    embeds: list[tuple[str, str, str]] = []
    rels: list[tuple[str, str]] = []
    index = 0
    for name, ttf_path in fonts.items():
        ttf_path = Path(ttf_path)
        if not ttf_path.is_file():
            skipped.append({"font": name, "reason": f"缺少字体文件：{ttf_path}"})
            continue
        raw = ttf_path.read_bytes()
        fs_type = read_fs_type(raw)
        if not is_embeddable(fs_type):
            skipped.append({"font": name, "reason": f"fsType={fs_type} 不允许嵌入"})
            continue
        index += 1
        guid = new_font_key()
        rel_id = f"rIdEmbed{index}"
        odttf = f"font{index}.odttf"
        parts[f"word/fonts/{odttf}"] = obfuscate(raw, guid)
        embeds.append((name, rel_id, guid))
        rels.append((rel_id, odttf))
        embedded.append({"font": name, "part": f"word/fonts/{odttf}",
                         "fs_type": fs_type, "font_key": guid})

    if embedded:
        parts["[Content_Types].xml"] = _add_content_type_default(
            parts["[Content_Types].xml"].decode("utf-8")).encode("utf-8")
        parts["word/settings.xml"] = _enable_font_embedding(
            parts["word/settings.xml"].decode("utf-8")).encode("utf-8")
        parts["word/fontTable.xml"] = _font_table_entries(
            parts["word/fontTable.xml"].decode("utf-8"), embeds).encode("utf-8")
        existing_rels = parts.get("word/_rels/fontTable.xml.rels")
        parts["word/_rels/fontTable.xml.rels"] = _font_table_rels(
            existing_rels.decode("utf-8") if existing_rels else None,
            rels).encode("utf-8")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in parts.items():
            archive.writestr(name, data)

    return {"ok": True, "embedded": embedded, "skipped": skipped,
            "docx": str(out_path)}


def verify_embedded_fonts(docx_path: Path) -> dict:
    docx_path = Path(docx_path)
    with zipfile.ZipFile(docx_path) as archive:
        names = set(archive.namelist())
        font_table = (archive.read("word/fontTable.xml").decode("utf-8")
                      if "word/fontTable.xml" in names else "")
        rels = (archive.read("word/_rels/fontTable.xml.rels").decode("utf-8")
                if "word/_rels/fontTable.xml.rels" in names else "")
        settings = (archive.read("word/settings.xml").decode("utf-8")
                    if "word/settings.xml" in names else "")
        results: list[dict] = []
        rel_targets = dict(re.findall(r'Id="([^"]+)"[^>]*Target="fonts/([^"]+)"', rels))
        for name, rel_id, guid in re.findall(
                r'<w:font w:name="([^"]+)">\s*<w:embedRegular '
                r'r:id="([^"]+)" w:fontKey="([^"]+)"', font_table):
            target = rel_targets.get(rel_id)
            entry = {"font": name, "part": f"word/fonts/{target}" if target else None}
            if not target or f"word/fonts/{target}" not in names:
                entry["valid"] = False
                entry["error"] = "字体部件缺失或未在 fontTable.xml.rels 中登记"
            else:
                restored = deobfuscate(archive.read(f"word/fonts/{target}"), guid)
                entry["valid"] = is_sfnt(restored)
                if not entry["valid"]:
                    entry["error"] = "反混淆后不是有效字体（sfnt 头无效）"
            results.append(entry)
    return {
        "docx": str(docx_path),
        "embed_flag": "<w:embedTrueTypeFonts" in settings,
        "fonts": results,
        "ok": bool(results) and all(f.get("valid") for f in results)
        and "<w:embedTrueTypeFonts" in settings,
    }


def resolve_bundled_fonts(font_dir: Path | None = None) -> dict[str, Path]:
    """{run_name: bundled TTF path} for the fonts present in this skill's
    assets/fonts (by candidate filename)."""
    font_dir = Path(font_dir) if font_dir else FONT_DIR
    resolved: dict[str, Path] = {}
    for run_name, candidates in EMBED_TARGETS.items():
        for filename in candidates:
            candidate = font_dir / filename
            if candidate.is_file():
                resolved[run_name] = candidate
                break
    return resolved


def embed_bundled_fonts(docx_path: Path, font_dir: Path | None = None) -> dict:
    """Embed this skill's embeddable bundled fonts into ``docx_path`` in place.

    Safe: embeds into a temp file and only replaces the original when
    verification passes, so the delivered DOCX is never left worse than the
    valid un-embedded one. Never raises for font/verify issues — embedding is an
    additive enhancement and must not break generation."""
    docx_path = Path(docx_path)
    fonts = resolve_bundled_fonts(font_dir)
    if not fonts:
        print("未找到可嵌入的随附字体，跳过嵌入。")
        return {"ok": None, "embedded": [], "skipped": [],
                "reason": "assets/fonts 中未找到目标字体"}
    tmp: Path | None = None
    try:
        # 临时路径的计算也放进 try：任何异常都不得外泄破坏正常生成。
        tmp = docx_path.with_suffix(docx_path.suffix + ".embed.tmp")
        report = embed_fonts_into_docx(docx_path, fonts, out_path=tmp)
        report["verify"] = verify_embedded_fonts(tmp)
        if report["verify"]["ok"]:
            os.replace(tmp, docx_path)
            report["docx"] = str(docx_path)
            report["verify"]["docx"] = str(docx_path)
            embedded = "、".join(e["font"] for e in report["embedded"]) or "无"
            skipped = "；".join(f"{s['font']}（{s['reason']}）" for s in report["skipped"])
            print(f"已嵌入字体：{embedded}" + (f"；未嵌入：{skipped}" if skipped else ""))
            report["ok"] = True
        else:
            Path(tmp).unlink(missing_ok=True)
            print("字体嵌入校验未通过，保留未嵌入版本。")
            report["ok"] = False
    except Exception as exc:  # noqa: BLE001 - embedding must never break generation
        if tmp is not None:
            Path(tmp).unlink(missing_ok=True)
        print(f"字体嵌入跳过（{exc}），保留原文件。")
        return {"ok": False, "error": str(exc)}
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docx", type=Path, required=True, help="target DOCX")
    parser.add_argument("--verify", action="store_true",
                        help="only verify existing embedded fonts")
    args = parser.parse_args()
    if not args.docx.is_file():
        print(json.dumps({"ok": False, "error": f"找不到 DOCX：{args.docx}"},
                         ensure_ascii=False))
        return 2
    if args.verify:
        report = verify_embedded_fonts(args.docx)
    else:
        report = embed_bundled_fonts(args.docx)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
