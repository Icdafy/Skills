#!/usr/bin/env python3
"""Embed the bundled GB2312 fonts into a minutes DOCX.

A delivered DOCX must render identically on a machine that does not have
仿宋_GB2312 / 楷体_GB2312 installed. This module embeds those faces directly
into the package using the ECMA-376 obfuscated-font mechanism (content type
``application/vnd.openxmlformats-officedocument.obfuscatedFont``), which is
renderer-independent — Word and LibreOffice both honour it, no COM/soffice
round-trip required.

Only faces whose OS/2 ``fsType`` permits embedding are included. 方正小标宋简体
(fsType=2, restricted-license) is never embedded — consistent with it being
outlined rather than embedded in the PDF. The obfuscation is symmetric XOR of
the first 32 bytes of the font with a key derived from the part's font-key
GUID (per ECMA-376 §17.8.1); ``verify_embedded_fonts`` reverses it and checks
that a valid sfnt header comes back, so a broken embedding never ships silently.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import struct
import sys
import uuid
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from format_spec import embeddable_fonts  # noqa: E402  (needs path shim)

SKILL_DIR = Path(__file__).resolve().parent.parent
FONT_DIR = SKILL_DIR / "assets" / "fonts"

OBFUSCATED_FONT_CT = "application/vnd.openxmlformats-officedocument.obfuscatedFont"
FONT_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/font"
_SFNT_SIGNATURES = (b"\x00\x01\x00\x00", b"OTTO", b"true", b"ttcf")


# OS/2 ulCodePageRange1 bit -> w:charset value, written the way Word writes it.
_CODEPAGE_CHARSETS: tuple[tuple[int, str], ...] = (
    (0x00040000, "86"),  # bit18 GB2312 简体中文
    (0x00100000, "88"),  # bit20 Big5 繁体中文
    (0x00020000, "80"),  # bit17 Shift-JIS 日文
    (0x00080000, "81"),  # bit19 Wansung 韩文
    (0x00200000, "82"),  # bit21 Johab 韩文
)


# --- Font-file inspection --------------------------------------------------
def _os2_offset(font: bytes) -> int | None:
    """Byte offset of the OS/2 table, or None."""
    if len(font) < 12 or font[:4] not in _SFNT_SIGNATURES:
        return None
    num_tables = struct.unpack(">H", font[4:6])[0]
    offset = 12
    for _ in range(num_tables):
        if offset + 16 > len(font):
            break
        if font[offset:offset + 4] == b"OS/2":
            return struct.unpack(">I", font[offset + 8:offset + 12])[0]
        offset += 16
    return None


def read_fs_type(font: bytes) -> int | None:
    """Return the OS/2 fsType word, or None when it cannot be read."""
    table = _os2_offset(font)
    if table is None or table + 10 > len(font):
        return None
    return struct.unpack(">H", font[table + 8:table + 10])[0]


def font_descriptor(font: bytes) -> str:
    """The `<w:font>` descriptor children (panose1/charset/family/pitch/sig).

    Word will only use an embedded face once it knows which charset the face
    serves: without `w:charset` it ignores the embedded font entirely and falls
    back to a system font. Verified against Word: embedding 仿宋 under a name
    that is not installed renders as SimSun/雅黑 when the descriptor is absent,
    and as `___WRD_EMBED_SUB_*` (i.e. the embedded face) once it is present.
    Returns "" when the OS/2 table cannot be read — the font is still embedded,
    just without the hint.
    """
    table = _os2_offset(font)
    if table is None or table + 86 > len(font):
        return ""
    panose = "".join(f"{b:02X}" for b in font[table + 32:table + 42])
    usb = struct.unpack(">IIII", font[table + 42:table + 58])
    version = struct.unpack(">H", font[table:table + 2])[0]
    csb = struct.unpack(">II", font[table + 78:table + 86]) if version >= 1 else (0, 0)
    charset = "00"
    for mask, value in _CODEPAGE_CHARSETS:
        if csb[0] & mask:
            charset = value
            break
    return (
        f'<w:panose1 w:val="{panose}"/>'
        f'<w:charset w:val="{charset}"/>'
        '<w:family w:val="auto"/><w:pitch w:val="variable"/>'
        f'<w:sig w:usb0="{usb[0]:08X}" w:usb1="{usb[1]:08X}" '
        f'w:usb2="{usb[2]:08X}" w:usb3="{usb[3]:08X}" '
        f'w:csb0="{csb[0]:08X}" w:csb1="{csb[1]:08X}"/>'
    )


def is_embeddable(fs_type: int | None) -> bool:
    """fsType permits embedding unless the restricted-license bit (0x0002) is set."""
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
    """XOR the first 32 bytes of ``font`` with the GUID-derived key."""
    key = _key_bytes(guid)
    data = bytearray(font)
    for i in range(min(32, len(data))):
        data[i] ^= key[i % 16]
    return bytes(data)


# de-obfuscation is the identical XOR
deobfuscate = obfuscate


def new_font_key() -> str:
    return "{" + str(uuid.uuid4()).upper() + "}"


# --- Package surgery -------------------------------------------------------
def _add_content_type_default(content_types: str) -> str:
    if 'Extension="odttf"' in content_types:
        return content_types
    default = (
        f'<Default Extension="odttf" ContentType="{OBFUSCATED_FONT_CT}"/>'
    )
    return re.sub(r"(<Types[^>]*>)", r"\1" + default, content_types, count=1)


def _enable_font_embedding(settings: str) -> str:
    if "<w:embedTrueTypeFonts" in settings:
        return settings
    flags = '<w:embedTrueTypeFonts/><w:saveSubsetFonts w:val="false"/>'
    # CT_Settings order: embedTrueTypeFonts sits just after w:zoom and before
    # w:proofState. Insert after the (self-closed) zoom element when present.
    zoom = re.search(r"<w:zoom\b[^>]*/>", settings)
    if zoom:
        return settings[:zoom.end()] + flags + settings[zoom.end():]
    return re.sub(r"(<w:settings[^>]*>)", r"\1" + flags, settings, count=1)


def _font_table_entries(existing: str, embeds: list[tuple[str, str, str, str]]) -> str:
    """Append a <w:font> for each (name, rel_id, guid, descriptor).

    The descriptor must precede <w:embedRegular> (CT_Font element order) and is
    what makes Word actually use the embedded face — see ``font_descriptor``.
    """
    additions: list[str] = []
    for name, rel_id, guid, descriptor in embeds:
        if f'w:name="{name}"' in existing:
            continue  # already declared (idempotent re-run)
        additions.append(
            f'<w:font w:name="{name}">'
            f"{descriptor}"
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
    embeds: list[tuple[str, str, str, str]] = []  # (name, rel_id, guid, descriptor)
    rels: list[tuple[str, str]] = []               # (rel_id, odttf filename)
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
        embeds.append((name, rel_id, guid, font_descriptor(raw)))
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


_FONT_BLOCK = re.compile(r'<w:font\s+w:name="([^"]+)"\s*>(.*?)</w:font>', re.S)
_EMBED_REGULAR = re.compile(r"<w:embedRegular\b([^>]*)/>")


def embedded_font_entries(font_table: str) -> list[tuple[str, str, str]]:
    """(font name, relationship id, font key) for every embedded regular face.

    Parses per <w:font> block rather than assuming <w:embedRegular> follows the
    opening tag immediately: a real fontTable carries panose/charset/family/
    pitch/sig in between, and the attributes may appear in any order (Word also
    writes w:subsetted). A stricter pattern silently finds nothing — which would
    report a perfectly good file, including Word's own, as unverified.
    """
    entries: list[tuple[str, str, str]] = []
    for name, block in _FONT_BLOCK.findall(font_table):
        match = _EMBED_REGULAR.search(block)
        if not match:
            continue
        attrs = match.group(1)
        rel_id = re.search(r'r:id="([^"]+)"', attrs)
        guid = re.search(r'w:fontKey="([^"]+)"', attrs)
        if rel_id and guid:
            entries.append((name, rel_id.group(1), guid.group(1)))
    return entries


def verify_embedded_fonts(docx_path: Path) -> dict:
    """Reopen the DOCX, de-obfuscate each embedded face and confirm it is a
    valid sfnt font referenced from the font table."""
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
        # Map rel-id -> target and font-name -> (rel-id, guid).
        rel_targets = dict(re.findall(r'Id="([^"]+)"[^>]*Target="fonts/([^"]+)"', rels))
        for name, rel_id, guid in embedded_font_entries(font_table):
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


def default_font_paths() -> dict[str, Path]:
    """{run_name: bundled TTF path} for the embeddable bundled faces."""
    return {name: FONT_DIR / asset for name, asset in embeddable_fonts().items()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docx", type=Path, required=True, help="target DOCX")
    parser.add_argument("--output", type=Path, default=None,
                        help="write to a different DOCX (default: in place)")
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
        report = embed_fonts_into_docx(args.docx, default_font_paths(), args.output)
        report["verify"] = verify_embedded_fonts(args.output or args.docx)
        report["ok"] = report["verify"]["ok"]
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
