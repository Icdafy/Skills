#!/usr/bin/env python3
"""Create a fixed-format Chinese meeting-minutes DOCX from validated plain text."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION_START
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

from font_preflight import required_font_status
from quality_check import validate

# Localized family names: Chinese-UI Word resolves East Asian fonts by their
# localized names, while the English names (KaiTi_GB2312 etc.) fall through to
# the registry FontSubstitutes table and get replaced by system KaiTi/FangSong.
TITLE_FONT = "方正小标宋简体"
KAI_FONT = "楷体_GB2312"
FANGSONG_FONT = "仿宋_GB2312"
SONG_FONT = "SimSun"
INDENT = "　　"

FIRST_LEVEL = re.compile(r"^[一二三四五六七八九十]+、")
SECOND_LEVEL = re.compile(r"^（[一二三四五六七八九十]+）")
THIRD_LEVEL = re.compile(r"^\d+\.")
FOURTH_LEVEL = re.compile(r"^（\d+）")


def set_east_asia_font(run, font_name: str, size: float, bold: bool = False) -> None:
    run.font.name = font_name
    run.font.size = Pt(size)
    run.bold = bold
    run._element.rPr.rFonts.set(qn("w:eastAsia"), font_name)


def set_exact_line_spacing(paragraph, points: float) -> None:
    paragraph.paragraph_format.line_spacing = Pt(points)
    paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)


def set_body_layout(paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    paragraph.paragraph_format.first_line_indent = Pt(32.4)
    paragraph.paragraph_format.widow_control = True
    set_exact_line_spacing(paragraph, 28)


def paragraph_role(text: str) -> tuple[str, str, bool]:
    if FIRST_LEVEL.match(text):
        return "first", "SimHei", False
    if SECOND_LEVEL.match(text):
        return "second", KAI_FONT, True
    if THIRD_LEVEL.match(text):
        return "third", FANGSONG_FONT, True
    if FOURTH_LEVEL.match(text):
        return "fourth", FANGSONG_FONT, False
    return "body", FANGSONG_FONT, False


def append_page_field(paragraph) -> None:
    leading = paragraph.add_run("-")
    set_east_asia_font(leading, SONG_FONT, 14)
    field = OxmlElement("w:fldSimple")
    field.set(qn("w:instr"), "PAGE")
    field_run = OxmlElement("w:r")
    properties = OxmlElement("w:rPr")
    fonts = OxmlElement("w:rFonts")
    fonts.set(qn("w:ascii"), SONG_FONT)
    fonts.set(qn("w:hAnsi"), SONG_FONT)
    fonts.set(qn("w:eastAsia"), SONG_FONT)
    properties.append(fonts)
    size = OxmlElement("w:sz")
    size.set(qn("w:val"), "28")
    properties.append(size)
    field_run.append(properties)
    text = OxmlElement("w:t")
    text.text = "1"
    field_run.append(text)
    field.append(field_run)
    paragraph._p.append(field)
    trailing = paragraph.add_run("-")
    set_east_asia_font(trailing, SONG_FONT, 14)


def format_footer(footer, alignment: WD_ALIGN_PARAGRAPH) -> None:
    paragraph = footer.paragraphs[0]
    paragraph.alignment = alignment
    set_exact_line_spacing(paragraph, 14)
    append_page_field(paragraph)


def configure_document(document: Document) -> None:
    section = document.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(3.7)
    section.bottom_margin = Cm(3.5)
    section.left_margin = Cm(2.8)
    section.right_margin = Cm(2.6)
    section.start_type = WD_SECTION_START.NEW_PAGE
    document.settings.odd_and_even_pages_header_footer = True
    format_footer(section.footer, WD_ALIGN_PARAGRAPH.RIGHT)
    format_footer(section.even_page_footer, WD_ALIGN_PARAGRAPH.LEFT)


def add_title(document: Document, title: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.first_line_indent = Pt(0)
    paragraph.paragraph_format.keep_together = True
    paragraph.paragraph_format.keep_with_next = True
    set_exact_line_spacing(paragraph, 30)
    run = paragraph.add_run(title)
    set_east_asia_font(run, TITLE_FONT, 22)


def add_subtitle(document: Document, subtitle: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.first_line_indent = Pt(0)
    paragraph.paragraph_format.keep_together = True
    paragraph.paragraph_format.keep_with_next = True
    set_exact_line_spacing(paragraph, 28)
    run = paragraph.add_run(subtitle)
    set_east_asia_font(run, KAI_FONT, 16)
    blank = document.add_paragraph()
    blank.paragraph_format.keep_with_next = True
    set_exact_line_spacing(blank, 28)


def add_content_paragraph(document: Document, text: str) -> None:
    paragraph = document.add_paragraph()
    set_body_layout(paragraph)
    content = text.removeprefix(INDENT).strip()
    role, font_name, bold = paragraph_role(content)
    if role != "body":
        paragraph.paragraph_format.keep_together = True
        paragraph.paragraph_format.keep_with_next = True
    run = paragraph.add_run(content)
    set_east_asia_font(run, font_name, 16, bold)


def missing_font_families() -> list[str]:
    return [item["family"] for item in required_font_status() if not item["installed"]]


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8-sig").splitlines()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create fixed-format meeting minutes DOCX.")
    parser.add_argument("--input", type=Path, required=True, help="validated UTF-8 plain-text minutes")
    parser.add_argument("--output", type=Path, required=True, help="destination .docx path")
    parser.add_argument("--subtitle", default=None, help="optional centered department or subtitle line")
    parser.add_argument(
        "--mode", choices=("auto", "minutes", "qa", "qa-summary"), default="auto"
    )
    args = parser.parse_args()

    if not args.input.is_file():
        parser.error(f"找不到输入文件：{args.input}")
    validation_errors = validate(args.input, args.mode)
    if validation_errors:
        parser.error("输入文本未通过校验：\n- " + "\n- ".join(validation_errors))
    missing_fonts = missing_font_families()
    if missing_fonts:
        parser.error(
            "缺少固定版式所需字体："
            + "、".join(missing_fonts)
            + "。先运行 font_preflight.py --check；取得用户许可后可运行 "
            "font_preflight.py --install-user 安装随技能提供的字体。"
        )
    lines = read_lines(args.input)
    title = next((line.strip() for line in lines if line.strip()), None)
    if not title:
        parser.error("输入文件不包含标题。")

    document = Document()
    configure_document(document)
    add_title(document, title)
    if args.subtitle:
        add_subtitle(document, args.subtitle)

    title_consumed = False
    for line in lines:
        if not line.strip():
            continue
        if not title_consumed and line.strip() == title:
            title_consumed = True
            continue
        add_content_paragraph(document, line)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    document.save(args.output)
    print(f"已生成：{args.output}")


if __name__ == "__main__":
    main()
