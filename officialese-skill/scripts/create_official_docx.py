#!/usr/bin/env python
"""Create a starter DOCX using the uploaded SOE official-document format."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt


TITLE_FONT = "方正小标宋简体"
BODY_FONT = "仿宋_GB2312"
BODY_FALLBACK = "仿宋"
KAITI_FONT = "楷体_GB2312"
HEITI_FONT = "黑体"
SONGTI_FONT = "宋体"


def set_run_font(run, font_name: str, size_pt: int, bold: bool = False) -> None:
    run.font.name = font_name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), font_name)
    run.font.size = Pt(size_pt)
    run.bold = bold


def set_paragraph_format(paragraph, line_pt: int = 28, first_indent: bool = True) -> None:
    fmt = paragraph.paragraph_format
    fmt.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    fmt.line_spacing = Pt(line_pt)
    fmt.space_before = Pt(0)
    fmt.space_after = Pt(0)
    if first_indent:
        fmt.first_line_indent = Pt(32)
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY


def add_text_paragraph(doc: Document, text: str, font: str = BODY_FONT, bold: bool = False) -> None:
    p = doc.add_paragraph()
    set_paragraph_format(p)
    run = p.add_run(text)
    set_run_font(run, font, 16, bold)


def add_center_line(doc: Document, text: str, font: str, size: int, line_pt: int = 30, bold: bool = False) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    p.paragraph_format.line_spacing = Pt(line_pt)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    run = p.add_run(text)
    set_run_font(run, font, size, bold)


def add_page_field(paragraph) -> None:
    run = paragraph.add_run("-")
    set_run_font(run, SONGTI_FONT, 14)

    field_begin = OxmlElement("w:fldChar")
    field_begin.set(qn("w:fldCharType"), "begin")

    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "

    field_end = OxmlElement("w:fldChar")
    field_end.set(qn("w:fldCharType"), "end")

    run = paragraph.add_run()
    run._r.append(field_begin)
    run._r.append(instr)
    run._r.append(field_end)

    run = paragraph.add_run("-")
    set_run_font(run, SONGTI_FONT, 14)


def setup_document(doc: Document) -> None:
    section = doc.sections[0]
    section.orientation = WD_ORIENT.PORTRAIT
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(3.7)
    section.bottom_margin = Cm(3.5)
    section.left_margin = Cm(2.8)
    section.right_margin = Cm(2.6)
    section.header_distance = Cm(1.5)
    section.footer_distance = Cm(2.35)

    doc.settings.odd_and_even_pages_header_footer = True

    odd_footer = section.footer.paragraphs[0]
    odd_footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    add_page_field(odd_footer)

    even_footer = section.even_page_footer.paragraphs[0]
    even_footer.alignment = WD_ALIGN_PARAGRAPH.LEFT
    add_page_field(even_footer)


def add_heading(doc: Document, text: str, level: int) -> None:
    if level == 1:
        add_text_paragraph(doc, text, HEITI_FONT, bold=False)
    elif level == 2:
        add_text_paragraph(doc, text, KAITI_FONT, bold=True)
    elif level == 3:
        add_text_paragraph(doc, text, BODY_FONT, bold=True)
    else:
        add_text_paragraph(doc, text, BODY_FONT, bold=False)


def add_sections(doc: Document, sections: list[dict]) -> None:
    for section in sections:
        title = section.get("heading") or section.get("title")
        if title:
            add_heading(doc, title, int(section.get("level", 1)))
        for para in section.get("paragraphs", []):
            add_text_paragraph(doc, para)
        children = section.get("children", [])
        if children:
            add_sections(doc, children)


def build_docx(data: dict, output: Path) -> None:
    doc = Document()
    setup_document(doc)

    issuer_title = data.get("issuer_title")
    if issuer_title:
        add_center_line(doc, issuer_title, TITLE_FONT, 22)

    add_center_line(doc, data.get("title", "关于XXXX的通知"), TITLE_FONT, 22)

    subtitle = data.get("subtitle")
    if subtitle:
        add_center_line(doc, subtitle, KAITI_FONT, 16, line_pt=28)

    doc.add_paragraph()

    recipient = data.get("recipient")
    if recipient:
        p = doc.add_paragraph()
        set_paragraph_format(p, first_indent=False)
        run = p.add_run(recipient)
        set_run_font(run, BODY_FONT, 16)

    for para in data.get("body", []):
        add_text_paragraph(doc, para)

    add_sections(doc, data.get("sections", []))

    attachments = data.get("attachments", [])
    if attachments:
        doc.add_paragraph()
        if len(attachments) == 1:
            add_text_paragraph(doc, f"附件：{attachments[0]}")
        else:
            add_text_paragraph(doc, f"附件：1.{attachments[0]}")
            for idx, attachment in enumerate(attachments[1:], start=2):
                add_text_paragraph(doc, f"      {idx}.{attachment}", first_font())

    issuer = data.get("issuer")
    date = data.get("date")
    if issuer or date:
        doc.add_paragraph()
        doc.add_paragraph()
    if issuer:
        p = doc.add_paragraph()
        set_paragraph_format(p)
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p.paragraph_format.right_indent = Pt(64)
        run = p.add_run(issuer)
        set_run_font(run, BODY_FONT, 16)
    if date:
        p = doc.add_paragraph()
        set_paragraph_format(p)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(date)
        set_run_font(run, BODY_FONT, 16)

    doc.save(output)


def first_font() -> str:
    return BODY_FONT


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create an SOE-style Chinese official DOCX starter.")
    parser.add_argument("output", type=Path, help="Output .docx path")
    parser.add_argument("--input", type=Path, help="JSON document specification")
    parser.add_argument("--title", help="Main title")
    parser.add_argument("--issuer-title", help="Issuing unit line above title")
    parser.add_argument("--subtitle", help="Centered subtitle or department line")
    parser.add_argument("--recipient", help="Recipient line, ending with Chinese colon")
    parser.add_argument("--body", action="append", default=[], help="Body paragraph; repeat as needed")
    parser.add_argument("--attachment", action="append", default=[], help="Attachment name; repeat as needed")
    parser.add_argument("--issuer", help="Signature unit")
    parser.add_argument("--date", help="Chinese date, e.g. 2026年6月8日")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.input:
        data = json.loads(args.input.read_text(encoding="utf-8"))
    else:
        data = {}
    for key in ["title", "issuer_title", "subtitle", "recipient", "issuer", "date"]:
        value = getattr(args, key)
        if value:
            data[key] = value
    if args.body:
        data["body"] = args.body
    if args.attachment:
        data["attachments"] = args.attachment
    build_docx(data, args.output)


if __name__ == "__main__":
    main()
