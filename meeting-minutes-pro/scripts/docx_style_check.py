#!/usr/bin/env python3
"""Read a generated minutes DOCX back and confirm every run carries the font,
size and weight the layout spec prescribes — without rendering to PDF.

The content-fidelity check in ``check_all.py`` proves the DOCX carries the right
*text*; this proves it carries the right *formatting*. Each body paragraph's
expected face is re-derived from ``format_spec.paragraph_role`` (the same
function the renderer uses), western runs must be Times New Roman, and the
centred title/subtitle are checked against their fixed faces. Any drift between
the spec and the emitted runs is reported, so a formatting regression is caught
here instead of only by a human eyeballing the PDF.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from format_spec import (  # noqa: E402  (needs the path shim above)
    BODY_SIZE,
    KAI_FONT,
    NUMBER_FONT,
    SUBTITLE_SIZE,
    TITLE_FONT,
    TITLE_SIZE,
    WESTERN_SEGMENT,
    paragraph_role,
)


def _east_asia(run) -> str | None:
    rpr = run._element.rPr
    if rpr is None or rpr.rFonts is None:
        return None
    return rpr.rFonts.get(qn("w:eastAsia"))


def _is_western(text: str) -> bool:
    return WESTERN_SEGMENT.fullmatch(text) is not None


def _expected(paragraph, center_seen: int) -> tuple[str, int, bool] | None:
    """Return (east-asia font, size pt, bold) expected for this paragraph, or
    None to skip it (blank line / spacer)."""
    text = paragraph.text.strip()
    if not text:
        return None
    if paragraph.alignment == WD_ALIGN_PARAGRAPH.CENTER:
        # First centred line is the title; any later centred line is the subtitle.
        if center_seen == 0:
            return TITLE_FONT, TITLE_SIZE, False
        return KAI_FONT, SUBTITLE_SIZE, False
    _role, font, bold = paragraph_role(text)
    return font, BODY_SIZE, bold


def check_docx_style(path: Path) -> list[str]:
    document = Document(str(path))
    problems: list[str] = []
    center_seen = 0
    for paragraph in document.paragraphs:
        expected = _expected(paragraph, center_seen)
        if paragraph.alignment == WD_ALIGN_PARAGRAPH.CENTER and paragraph.text.strip():
            center_seen += 1
        if expected is None:
            continue
        ea_font, size, bold = expected
        preview = paragraph.text.strip()[:20]
        for run in paragraph.runs:
            if not run.text.strip():
                continue
            want_font = NUMBER_FONT if _is_western(run.text) else ea_font
            if run.font.name != want_font:
                problems.append(
                    f"「{preview}」中「{run.text[:12]}」字体为 {run.font.name}，应为 {want_font}"
                )
            if not _is_western(run.text) and _east_asia(run) != ea_font:
                problems.append(
                    f"「{preview}」中「{run.text[:12]}」东亚字体为 {_east_asia(run)}，应为 {ea_font}"
                )
            if run.font.size != Pt(size):
                got = None if run.font.size is None else round(run.font.size.pt, 1)
                problems.append(
                    f"「{preview}」中「{run.text[:12]}」字号为 {got} 磅，应为 {size} 磅"
                )
            if bool(run.bold) != bold:
                problems.append(
                    f"「{preview}」中「{run.text[:12]}」加粗为 {bool(run.bold)}，应为 {bold}"
                )
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("docx", type=Path, help="generated minutes DOCX")
    args = parser.parse_args()
    if not args.docx.is_file():
        print(f"找不到 DOCX：{args.docx}")
        return 2
    problems = check_docx_style(args.docx)
    if problems:
        print("DOCX 样式回读未通过：")
        for problem in problems:
            print(f"- {problem}")
        return 1
    print("DOCX 样式回读通过：字体、字号、加粗均符合规约。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
