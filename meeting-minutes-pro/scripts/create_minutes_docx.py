#!/usr/bin/env python3
"""Create a fixed-format Chinese meeting-minutes DOCX from validated plain text.

Layout knowledge (heading grammar, role→font mapping, western-run rule, sizes,
geometry, fonts) is imported from ``format_spec`` — the same module the text
validator uses — so the rendered DOCX can never disagree with what
``quality_check`` accepted. After saving, the bundled GB2312 faces are embedded
into the package (see ``embed_fonts``) so the file renders faithfully on
machines that lack 仿宋_GB2312 / 楷体_GB2312; pass ``--no-embed`` to skip.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION_START
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from format_spec import (  # noqa: E402  (needs the path shim above)
    BODY_LINE_SPACING,
    BODY_SIZE,
    BOTTOM_MARGIN_CM,
    FIRST_LINE_INDENT_CHARS,
    FIRST_LINE_INDENT_PT,
    INDENT,
    HEADING_LINE_SPACING,
    KAI_FONT,
    LEFT_MARGIN_CM,
    NUMBER_FONT,
    PAGE_HEIGHT_CM,
    PAGE_NUMBER_FONT,
    PAGE_NUMBER_FONT_HINT,
    PAGE_NUMBER_FONT_SLOTS,
    PAGE_NUMBER_PREFIX,
    PAGE_NUMBER_SIZE,
    PAGE_NUMBER_SUFFIX,
    PAGE_WIDTH_CM,
    RIGHT_MARGIN_CM,
    SUBTITLE_LINE_SPACING,
    SUBTITLE_SIZE,
    TABLE_FONT,
    TABLE_SIZE,
    TITLE_FONT,
    TITLE_LINE_SPACING,
    TITLE_SIZE,
    TOP_MARGIN_CM,
    WESTERN_SEGMENT,
    is_table_row,
    is_table_separator,
    level_number,
    paragraph_role,
    table_cells,
)
from embed_fonts import (  # noqa: E402
    default_font_paths,
    embed_fonts_into_docx,
    verify_embedded_fonts,
)
from font_preflight import required_font_status  # noqa: E402
from quality_check import validate  # noqa: E402
from docx_format_helpers import parenthesized_spans  # noqa: E402

# Page-number text, face and size come from format_spec so the renderer and
# delivery-time readback enforce the same explicit footer rule.


def _set_page_number_properties(properties) -> None:
    """Write the complete four-slot font and both size properties.

    ``w:hint=eastAsia`` keeps ASCII dashes and field results on SimSun, while
    the style/paragraph defaults protect a PAGE result run that Word rebuilds
    during field refresh. Theme attributes are removed so they cannot override
    the explicit localised family name.
    """
    fonts = properties.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        properties.insert(0, fonts)
    for attribute in PAGE_NUMBER_FONT_SLOTS:
        fonts.set(qn(f"w:{attribute}"), PAGE_NUMBER_FONT)
    fonts.set(qn("w:hint"), PAGE_NUMBER_FONT_HINT)
    for attribute in ("asciiTheme", "hAnsiTheme", "eastAsiaTheme", "cstheme"):
        fonts.attrib.pop(qn(f"w:{attribute}"), None)
    for tag in ("w:sz", "w:szCs"):
        size = properties.find(qn(tag))
        if size is None:
            size = OxmlElement(tag)
            properties.append(size)
        size.set(qn("w:val"), str(PAGE_NUMBER_SIZE * 2))


def _set_page_number_run(run) -> None:
    _set_page_number_properties(run._element.get_or_add_rPr())


def _set_page_number_paragraph_defaults(paragraph) -> None:
    paragraph_properties = paragraph._p.get_or_add_pPr()
    run_properties = paragraph_properties.find(qn("w:rPr"))
    if run_properties is None:
        run_properties = OxmlElement("w:rPr")
        paragraph_properties.append(run_properties)
    _set_page_number_properties(run_properties)


def configure_footer_style(document: Document) -> None:
    footer_style = document.styles["Footer"]
    run_properties = footer_style._element.find(qn("w:rPr"))
    if run_properties is None:
        run_properties = OxmlElement("w:rPr")
        footer_style._element.append(run_properties)
    _set_page_number_properties(run_properties)


def enable_field_updates(document: Document) -> None:
    settings = document.settings._element
    update = settings.find(qn("w:updateFields"))
    if update is None:
        update = OxmlElement("w:updateFields")
        settings.append(update)
    update.set(qn("w:val"), "true")


def set_east_asia_font(run, font_name: str, size: float, bold: bool = False) -> None:
    """Chinese characters use ``font_name``; the Western slots are Times New
    Roman so digits, letters and % in the run never fall back to the CJK face."""
    run.font.name = NUMBER_FONT
    run.font.size = Pt(size)
    run.bold = bold
    run._element.rPr.rFonts.set(qn("w:eastAsia"), font_name)
    run._element.rPr.rFonts.set(qn("w:cs"), NUMBER_FONT)


def set_western_font(run, east_asia_font: str, size: float, bold: bool = False) -> None:
    """Latin letters and Arabic numerals are set in Times New Roman; the
    surrounding East Asian face is kept as the CJK fallback."""
    run.font.name = NUMBER_FONT
    run.font.size = Pt(size)
    run.bold = bold
    run._element.rPr.rFonts.set(qn("w:eastAsia"), east_asia_font)
    run._element.rPr.rFonts.set(qn("w:cs"), NUMBER_FONT)


def add_text_runs(paragraph, text: str, font_name: str, size: float, bold: bool = False,
                  paren_size: float = BODY_SIZE) -> None:
    """Round-parenthesized spans use 楷体_GB2312 (三号; 五号 inside tables) for
    Chinese, with digits/letters/% inside still in Times New Roman."""
    cursor = 0
    for start, end in parenthesized_spans(text):
        _add_unparenthesized_runs(paragraph, text[cursor:start], font_name, size, bold)
        set_east_asia_font(paragraph.add_run(text[start:end]), KAI_FONT, paren_size, bold)
        cursor = end
    _add_unparenthesized_runs(paragraph, text[cursor:], font_name, size, bold)


def _add_unparenthesized_runs(paragraph, text, font_name, size, bold=False):
    """Outside parentheses, preserve the usual Times New Roman western runs."""
    cursor = 0
    for match in WESTERN_SEGMENT.finditer(text):
        if match.start() > cursor:
            run = paragraph.add_run(text[cursor:match.start()])
            set_east_asia_font(run, font_name, size, bold)
        run = paragraph.add_run(match.group())
        set_western_font(run, font_name, size, bold)
        cursor = match.end()
    if cursor < len(text):
        run = paragraph.add_run(text[cursor:])
        set_east_asia_font(run, font_name, size, bold)


def set_exact_line_spacing(paragraph, points: float) -> None:
    paragraph.paragraph_format.line_spacing = Pt(points)
    paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)


def set_first_line_indent(paragraph) -> None:
    """Indent the first line by two characters. w:firstLineChars scales with the
    font size (the public-document convention); the absolute w:firstLine is kept
    as a fallback for renderers that ignore the character measure."""
    paragraph.paragraph_format.first_line_indent = Pt(FIRST_LINE_INDENT_PT)
    indent = paragraph._p.get_or_add_pPr().get_or_add_ind()
    indent.set(qn("w:firstLineChars"), str(FIRST_LINE_INDENT_CHARS * 100))


def set_body_layout(paragraph, line_spacing: float = BODY_LINE_SPACING) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    set_first_line_indent(paragraph)
    paragraph.paragraph_format.widow_control = True
    set_exact_line_spacing(paragraph, line_spacing)


def append_page_field(paragraph) -> None:
    leading = paragraph.add_run(PAGE_NUMBER_PREFIX)
    _set_page_number_run(leading)
    field = OxmlElement("w:fldSimple")
    field.set(qn("w:instr"), "PAGE")
    field_run = OxmlElement("w:r")
    properties = OxmlElement("w:rPr")
    _set_page_number_properties(properties)
    field_run.append(properties)
    text = OxmlElement("w:t")
    text.text = "1"
    field_run.append(text)
    field.append(field_run)
    paragraph._p.append(field)
    trailing = paragraph.add_run(PAGE_NUMBER_SUFFIX)
    _set_page_number_run(trailing)


def format_footer(footer, alignment: WD_ALIGN_PARAGRAPH) -> None:
    paragraph = footer.paragraphs[0]
    paragraph.clear()
    paragraph.style = "Footer"
    paragraph.alignment = alignment
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.line_spacing = 1.0
    _set_page_number_paragraph_defaults(paragraph)
    append_page_field(paragraph)


def clear_header(header) -> None:
    """Keep the header part present but remove all visible header content."""
    for paragraph in header.paragraphs:
        paragraph.clear()


def configure_document(document: Document) -> None:
    section = document.sections[0]
    section.page_width = Cm(PAGE_WIDTH_CM)
    section.page_height = Cm(PAGE_HEIGHT_CM)
    section.top_margin = Cm(TOP_MARGIN_CM)
    section.bottom_margin = Cm(BOTTOM_MARGIN_CM)
    section.left_margin = Cm(LEFT_MARGIN_CM)
    section.right_margin = Cm(RIGHT_MARGIN_CM)
    section.start_type = WD_SECTION_START.NEW_PAGE
    document.settings.odd_and_even_pages_header_footer = True
    configure_footer_style(document)
    enable_field_updates(document)
    section.different_first_page_header_footer = False
    clear_header(section.header)
    clear_header(section.even_page_header)
    format_footer(section.footer, WD_ALIGN_PARAGRAPH.RIGHT)
    format_footer(section.even_page_footer, WD_ALIGN_PARAGRAPH.LEFT)


def add_title(document: Document, title: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.first_line_indent = Pt(0)
    paragraph.paragraph_format.keep_together = True
    paragraph.paragraph_format.keep_with_next = True
    set_exact_line_spacing(paragraph, TITLE_LINE_SPACING)
    add_text_runs(paragraph, title, TITLE_FONT, TITLE_SIZE)


def add_subtitle(document: Document, subtitle: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.first_line_indent = Pt(0)
    paragraph.paragraph_format.keep_together = True
    paragraph.paragraph_format.keep_with_next = True
    set_exact_line_spacing(paragraph, SUBTITLE_LINE_SPACING)
    add_text_runs(paragraph, subtitle, KAI_FONT, SUBTITLE_SIZE)
    blank = document.add_paragraph()
    blank.paragraph_format.keep_with_next = True
    set_exact_line_spacing(blank, BODY_LINE_SPACING)


def add_content_paragraph(document: Document, text: str) -> None:
    paragraph = document.add_paragraph()
    content = text.removeprefix(INDENT).strip()
    role, font_name, bold = paragraph_role(content)
    line_spacing = HEADING_LINE_SPACING if role != "body" else BODY_LINE_SPACING
    set_body_layout(paragraph, line_spacing)
    if role != "body":
        paragraph.paragraph_format.keep_together = True
        paragraph.paragraph_format.keep_with_next = True
    add_text_runs(paragraph, content, font_name, BODY_SIZE, bold)


def _set_table_cell_margins(table, top_bottom_pt: float = 2, left_right_pt: float = 4) -> None:
    margins = OxmlElement("w:tblCellMar")
    for side, value in (("top", top_bottom_pt), ("left", left_right_pt),
                        ("bottom", top_bottom_pt), ("right", left_right_pt)):
        node = OxmlElement(f"w:{side}")
        node.set(qn("w:w"), str(int(value * 20)))
        node.set(qn("w:type"), "dxa")
        margins.append(node)
    table._tbl.tblPr.append(margins)


def add_table(document: Document, rows: list[list[str]]) -> None:
    """表格内全部文字固定五号仿宋_GB2312、不加粗；括号片段五号楷体_GB2312；
    数字、字母和 % 用 Times New Roman。单倍行距、无首行缩进、水平垂直居中。"""
    rows = [row for row in rows if row]
    if not rows:
        return
    columns = max(len(row) for row in rows)
    table = document.add_table(rows=len(rows), cols=columns)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    _set_table_cell_margins(table)
    for r, row in enumerate(rows):
        for c in range(columns):
            cell = table.cell(r, c)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            paragraph = cell.paragraphs[0]
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            fmt = paragraph.paragraph_format
            fmt.first_line_indent = Pt(0)
            fmt.line_spacing_rule = WD_LINE_SPACING.SINGLE
            fmt.space_before = Pt(0)
            fmt.space_after = Pt(0)
            add_text_runs(paragraph, row[c] if c < len(row) else "", TABLE_FONT,
                          TABLE_SIZE, False, paren_size=TABLE_SIZE)


def _iter_body_paragraphs(document: Document):
    """Body and table-cell paragraphs (nested tables too); headers/footers excluded."""
    def walk(tables):
        for table in tables:
            for row in table.rows:
                for cell in row.cells:
                    yield from cell.paragraphs
                    yield from walk(cell.tables)
    yield from document.paragraphs
    yield from walk(document.tables)


def apply_western_font_pass(document: Document) -> None:
    """全文最后一步：在方正小标宋简体、黑体、楷体_GB2312、仿宋_GB2312 与页脚
    四号宋体设置完成后，再对全文统一选择一次 Times New Roman——每个 run 的
    ascii/hAnsi/cs 设为 Times New Roman，eastAsia 保持不变，因此数字、字母、%
    等改用 Times New Roman，汉字不受影响。页脚 -1- 不在处理范围内，保持四号宋体。"""
    for paragraph in _iter_body_paragraphs(document):
        for run in paragraph.runs:
            properties = run._element.get_or_add_rPr()
            fonts = properties.find(qn("w:rFonts"))
            if fonts is None:
                fonts = OxmlElement("w:rFonts")
                properties.insert(0, fonts)
            for slot in ("ascii", "hAnsi", "cs"):
                fonts.set(qn(f"w:{slot}"), NUMBER_FONT)


def add_qa_separator(document: Document) -> None:
    """Blank spacer line rendered between consecutive Q/A groups."""
    paragraph = document.add_paragraph()
    set_exact_line_spacing(paragraph, BODY_LINE_SPACING)


def add_minutes_content(document: Document, lines: list[str], title: str) -> None:
    """Render source lines while preserving the QA blank-line contract."""
    title_consumed = False
    pending_blank = False
    previous_content = ""
    table_rows: list[list[str]] = []

    def flush_table() -> None:
        if table_rows:
            add_table(document, list(table_rows))
            table_rows.clear()

    for line in lines:
        if not line.strip():
            flush_table()
            pending_blank = title_consumed
            continue
        if not title_consumed and line.strip() == title:
            title_consumed = True
            continue
        content = line.removeprefix(INDENT).strip()
        if title_consumed and is_table_row(content):
            if not is_table_separator(content):
                table_rows.append(table_cells(content))
            pending_blank = False
            previous_content = content
            continue
        flush_table()
        starts_qa_group = content.startswith("问：")
        starts_qa_subheading = (
            level_number(content) == 2 and previous_content.startswith("答：")
        )
        if pending_blank and (starts_qa_group or starts_qa_subheading):
            add_qa_separator(document)
        pending_blank = False
        add_content_paragraph(document, line)
        previous_content = content
    flush_table()


def missing_font_families() -> list[str]:
    return [item["family"] for item in required_font_status() if not item["installed"]]


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8-sig").splitlines()


def embed_bundled_fonts(output: Path) -> dict:
    """Embed the bundled GB2312 faces into ``output`` and verify the result.

    Embeds into a temp file and only replaces ``output`` once verification
    passes, so a failed embedding never leaves a modified DOCX on disk — the
    caller still hard-fails, but on the intact un-embedded file rather than a
    half-written one.
    """
    tmp = output.with_suffix(output.suffix + ".embed.tmp")
    try:
        report = embed_fonts_into_docx(output, default_font_paths(), tmp)
        report["verify"] = verify_embedded_fonts(tmp)
        if report["verify"]["ok"]:
            os.replace(tmp, output)
            report["docx"] = str(output)
            report["verify"]["docx"] = str(output)
    finally:
        Path(tmp).unlink(missing_ok=True)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Create fixed-format meeting minutes DOCX.")
    parser.add_argument("--input", type=Path, required=True, help="validated UTF-8 plain-text minutes")
    parser.add_argument("--output", type=Path, required=True, help="destination .docx path")
    parser.add_argument("--subtitle", default=None, help="optional centered department or subtitle line")
    parser.add_argument(
        "--mode", choices=("auto", "minutes", "qa", "qa-summary"), default="auto"
    )
    parser.add_argument(
        "--no-embed",
        action="store_true",
        help="不把随附字体嵌入 DOCX（默认嵌入，使文件在未装字体的机器上仍忠实呈现）",
    )
    parser.add_argument(
        "--allow-line",
        type=int,
        action="append",
        default=[],
        metavar="行号",
        help="与 quality_check.py 一致：放行该行经确认属转录稿真实内容的表述",
    )
    args = parser.parse_args()

    if not args.input.is_file():
        parser.error(f"找不到输入文件：{args.input}")
    validation_errors = validate(args.input, args.mode, frozenset(args.allow_line))
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

    add_minutes_content(document, lines, title)
    apply_western_font_pass(document)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    document.save(args.output)
    print(f"已生成：{args.output}")

    if not args.no_embed:
        report = embed_bundled_fonts(args.output)
        embedded = "、".join(item["font"] for item in report["embedded"]) or "无"
        print(f"已嵌入字体：{embedded}")
        for item in report["skipped"]:
            print(f"未嵌入 {item['font']}：{item['reason']}")
        if not report["verify"]["ok"]:
            parser.error(
                "字体嵌入校验未通过，请勿交付该 DOCX：\n"
                + "\n".join(
                    f"- {font['font']}：{font.get('error', '未知')}"
                    for font in report["verify"]["fonts"]
                    if not font.get("valid")
                )
                or "- 未设置 w:embedTrueTypeFonts"
            )


if __name__ == "__main__":
    main()
