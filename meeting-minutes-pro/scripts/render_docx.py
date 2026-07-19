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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from format_spec import pdf_required_markers, pdf_substitute_alerts  # noqa: E402

# PostScript names as they appear inside the exported PDF. 方正小标宋 is not
# listed: its license flag (fsType=2) forbids embedding, so Word outputs the
# title as vector outlines — visually faithful but absent from the font list.
REQUIRED_FONT_MARKERS = pdf_required_markers()  # ("KaiTi_GB2312", "FangSong_GB2312")

# Bare PostScript names whose presence proves a GB2312 face was silently
# substituted: system 楷体/仿宋 ("KaiTi"/"FangSong", no _GB2312 suffix) and WPS
# cloud clones ("KSOF…", handled separately below).
SUBSTITUTE_ALERTS = pdf_substitute_alerts()  # ("KaiTi", "FangSong")


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


# Footer glyphs are dashes and digits only (`-1-`); CJK body text never matches.
_FOOTER_TOKEN = re.compile(r"^[-‐-―\d\s]+$")


def is_footer_token(text: str) -> bool:
    return bool(text.strip()) and _FOOTER_TOKEN.match(text) is not None


def page_side(xs: list[float], width: float) -> str | None:
    """Which side of the page the footer glyphs (x positions) sit on."""
    if not xs:
        return None
    return "right" if (min(xs) + max(xs)) / 2 > width / 2 else "left"


def footer_xs(candidates: list[tuple[float, float]], body_ys: list[float],
              page_height: float) -> list[float]:
    """x positions of the page-number glyphs, from (y, x) dash/digit candidates.

    The footer is derived from the page's own content instead of a hard-coded
    margin: it is the dash/digit cluster lying below every line of body text, so
    the check survives a different footer distance, bottom margin or page size.
    Only the lowest text line is kept — the page number is a single line, so a
    numeric table row sitting low on the page cannot contaminate it. Falls back
    to a low band when the page carries no body text at all.
    """
    cutoff = min(body_ys) if body_ys else page_height * 0.11
    below = [(y, x) for y, x in candidates if y < cutoff]
    if not below:
        return []
    baseline = min(y for y, _ in below)
    return [x for y, x in below if y <= baseline + 5]


def expected_side(page_number: int) -> str:
    """1-indexed: odd pages carry the number on the right, even on the left."""
    return "right" if page_number % 2 == 1 else "left"


def page_number_sides(pdf: Path) -> dict:
    """Confirm the page-number footer sits on the right of odd pages and the
    left of even pages. Best-effort: returns ``available: False`` when pypdf is
    missing or no footer glyphs can be located, so it never blocks a render."""
    try:
        from pypdf import PdfReader
    except ImportError:
        return {"available": False, "reason": "pypdf 不可用，页码位置需人工核对"}

    reader = PdfReader(str(pdf))
    pages_report: list[dict] = []
    for index, page in enumerate(reader.pages, start=1):
        try:
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
        except (TypeError, ValueError):
            continue
        candidates: list[tuple[float, float]] = []   # dash/digit runs: (y, x)
        body_ys: list[float] = []                    # everything else: y

        def visitor(text, cm, tm, font_dict, font_size,
                    _c=candidates, _b=body_ys):
            # y <= 1 skips pypdf's matrix-less artefacts (wrapped runs reported
            # at x=y=0), which would otherwise drag the footer centre sideways.
            y = float(tm[5])
            if not text.strip() or y <= 1:
                return
            if is_footer_token(text):
                _c.append((y, float(tm[4])))
            else:
                _b.append(y)

        try:
            page.extract_text(visitor_text=visitor)
        except Exception:  # noqa: BLE001 - a parse hiccup must not fail the render
            pass
        want = expected_side(index)
        detected = page_side(footer_xs(candidates, body_ys, height), width)
        entry = {"page": index, "expected": want, "detected": detected}
        if detected is not None:
            entry["ok"] = detected == want
        pages_report.append(entry)

    detected_pages = [p for p in pages_report if p.get("detected")]
    return {
        "available": True,
        "ok": all(p["ok"] for p in detected_pages) if detected_pages else None,
        "pages": pages_report,
    }


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
    page_numbers = page_number_sides(pdf)
    page_number_note = ""
    if page_numbers.get("ok") is False:
        wrong = "、".join(
            f"第 {p['page']} 页（实为{p['detected']}，应为{p['expected']}）"
            for p in page_numbers["pages"] if p.get("ok") is False
        )
        page_number_note = f" 页码位置异常：{wrong}，需修正后重新生成。"
    print(json.dumps({
        "ok": True,
        "renderer": renderer,
        "pdf": str(pdf),
        "pages": pages,
        "embedded_fonts": fonts,
        "missing_required_fonts": missing_markers,
        "substituted_fonts": substituted,
        "page_number_check": page_numbers,
        "note": "逐页检查 PDF：标题、缩进、分页；"
                "missing_required_fonts 或 substituted_fonts 非空说明发生了字体替换，不得交付。"
                "页码奇右偶左已自动核验（page_number_check.ok 为 false 即位置有误）。"
                "标题字体方正小标宋许可禁止嵌入，PDF 中以轮廓输出属正常，须目检标题字形是否为小标宋。"
                + page_number_note,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
