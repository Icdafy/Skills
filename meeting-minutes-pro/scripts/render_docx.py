#!/usr/bin/env python3
"""Render a minutes DOCX to PDF so every page can be inspected before delivery.

Uses Microsoft Word via COM on Windows when available, otherwise LibreOffice
(soffice --headless). The JSON result reports the page count and which of the
required font families are actually embedded in the PDF — an empty or partial
font list means Word/LibreOffice substituted fonts and the DOCX must not be
delivered as-is.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

# PostScript names as they appear inside the exported PDF. 方正小标宋 is not
# listed: its license flag (fsType=2) forbids embedding, so Word outputs the
# title as vector outlines — visually faithful but absent from the font list.
REQUIRED_FONT_MARKERS = (
    "KaiTi_GB2312",     # 楷体_GB2312
    "FangSong_GB2312",  # 仿宋_GB2312
)

# Fonts whose presence proves a GB2312 face was silently substituted: system
# 楷体/仿宋 (PostScript "KaiTi"/"FangSong", no _GB2312 suffix) and WPS cloud
# clones ("KSOF…").
SUBSTITUTE_ALERTS = ("KaiTi", "FangSong")


def render_with_word(docx: Path, pdf: Path) -> bool:
    if sys.platform != "win32":
        return False
    # Word occasionally drops the RPC channel on Quit after a successful
    # conversion, so Quit failures are tolerated and success is judged by
    # whether the PDF file was produced.
    script = f"""
$ErrorActionPreference = 'Stop'
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {{
  $doc = $word.Documents.Open('{docx}', $false, $true)
  $doc.SaveAs2('{pdf}', 17)
  $doc.Close($false)
}} finally {{
  try {{ $word.Quit() }} catch {{}}
}}
"""
    with tempfile.NamedTemporaryFile("w", suffix=".ps1", delete=False, encoding="utf-8-sig") as handle:
        handle.write(script)
        script_path = handle.name
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script_path],
            capture_output=True, text=True, check=False, timeout=180,
        )
    finally:
        Path(script_path).unlink(missing_ok=True)
    return pdf.is_file()


def find_soffice() -> str | None:
    found = shutil.which("soffice") or shutil.which("libreoffice")
    if found:
        return found
    for candidate in (
        Path("C:/Program Files/LibreOffice/program/soffice.exe"),
        Path("C:/Program Files (x86)/LibreOffice/program/soffice.exe"),
        Path("/Applications/LibreOffice.app/Contents/MacOS/soffice"),
    ):
        if candidate.is_file():
            return str(candidate)
    return None


def render_with_soffice(docx: Path, pdf: Path) -> bool:
    soffice = find_soffice()
    if not soffice:
        return False
    with tempfile.TemporaryDirectory(prefix="mmp-render-") as temp_dir:
        proc = subprocess.run(
            [soffice, "--headless", "--norestore", "--convert-to", "pdf",
             "--outdir", temp_dir, str(docx)],
            capture_output=True, text=True, check=False, timeout=180,
        )
        produced = Path(temp_dir) / (docx.stem + ".pdf")
        if proc.returncode != 0 or not produced.is_file():
            return False
        pdf.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(produced, pdf)
    return True


def inspect_pdf(pdf: Path) -> tuple[int, list[str]]:
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(pdf))
        fonts: set[str] = set()
        for page in reader.pages:
            resources = page.get("/Resources") or {}
            font_dict = resources.get("/Font")
            if not font_dict:
                continue
            for font in font_dict.values():
                font = font.get_object()
                base = font.get("/BaseFont")
                if base:
                    fonts.add(str(base).lstrip("/"))
                descendants = font.get("/DescendantFonts")
                if descendants:
                    for item in descendants:
                        base = item.get_object().get("/BaseFont")
                        if base:
                            fonts.add(str(base).lstrip("/"))
        return len(reader.pages), sorted(fonts)
    except ImportError:
        # Crude fallback: misses fonts stored inside compressed object streams.
        data = pdf.read_bytes()
        pages = len(re.findall(rb"/Type\s*/Page(?![a-zA-Z])", data))
        fonts_found = sorted({
            match.decode("ascii", "replace")
            for match in re.findall(rb"/BaseFont\s*/([#\w+~.-]+)", data)
        })
        return pages, fonts_found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="DOCX file to render")
    parser.add_argument("--output", type=Path, default=None,
                        help="destination PDF (default: alongside the DOCX)")
    args = parser.parse_args()

    docx = args.input.expanduser().resolve()
    if not docx.is_file():
        print(json.dumps({"ok": False, "error": f"找不到 DOCX：{docx}"}, ensure_ascii=False))
        return 2
    pdf = (args.output or docx.with_suffix(".pdf")).expanduser().resolve()
    # A stale PDF from an earlier render must not masquerade as this run's output.
    pdf.unlink(missing_ok=True)

    renderer = None
    if render_with_word(docx, pdf):
        renderer = "word"
    elif render_with_soffice(docx, pdf):
        renderer = "libreoffice"
    else:
        print(json.dumps({
            "ok": False,
            "error": "无可用渲染器：需要本机安装 Microsoft Word 或 LibreOffice",
        }, ensure_ascii=False, indent=2))
        return 1

    pages, fonts = inspect_pdf(pdf)
    fonts_blob = " ".join(fonts)
    missing_markers = [m for m in REQUIRED_FONT_MARKERS if m.casefold() not in fonts_blob.casefold()]
    bare_names = {font.split("+")[-1] for font in fonts}
    substituted = sorted(
        name for name in bare_names
        if name in SUBSTITUTE_ALERTS or name.startswith("KSOF")
    )
    print(json.dumps({
        "ok": True,
        "renderer": renderer,
        "pdf": str(pdf),
        "pages": pages,
        "embedded_fonts": fonts,
        "missing_required_fonts": missing_markers,
        "substituted_fonts": substituted,
        "note": "逐页检查 PDF：标题、缩进、分页、页码位置；"
                "missing_required_fonts 或 substituted_fonts 非空说明发生了字体替换，不得交付。"
                "标题字体方正小标宋许可禁止嵌入，PDF 中以轮廓输出属正常，须目检标题字形是否为小标宋。",
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
