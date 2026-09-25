#!/usr/bin/env python
"""Create a 投委会议题 DOCX from a JSON spec, using the company officialese format.

Font order mirrors the manual workflow: first give every run its Chinese font
(方正小标宋简体 / 黑体 / 楷体_GB2312 / 仿宋_GB2312), then set parentheses and their
contents to 楷体_GB2312 (三号 in text, 五号 in tables), then the footer `-1-` to
四号宋体, and finally apply Times New Roman to the whole body so every digit,
Latin letter and symbol such as % is Times New Roman while Chinese characters
keep their fonts. The footer is excluded from that last pass. Inline bold uses
**...**.

Two kinds of 议题 share one spec format:
- kind "meeting" (default): 股东会/合伙人会议参会表决议题, recipient `投委会：`,
  no signature.
- kind "exit": 投资项目退出议题, no recipient line, two-paragraph intro, signature
  and an attachment document (退出方案) on a new page.

JSON spec example (exit):
{
  "kind": "exit",
  "title": "审议关于XX科技有限公司\\n投资项目退出的议题",
  "submit_line": "提交子公司：投管公司",
  "intro": ["2024年3月，……。", "投资后，……现提请投委会审议。具体如下："],
  "blocks": [
    {"type": "h1", "text": "一、项目基本情况"},
    {"type": "h2", "text": "（一）投资尽调和决策"},
    {"type": "h3", "text": "1.立项与尽调"},
    {"type": "h4", "text": "（1）法律尽调"},
    {"type": "para", "text": "……"},
    {"type": "table", "caption": "……如下：", "header": ["序号", "事项"], "rows": [["1", "……"]]}
  ],
  "attachments": ["XX科技有限公司项目退出方案"],
  "signature": {"issuer": "XX投资管理有限公司", "date": "2026年9月X日"},
  "appendices": [{"title": "XX科技有限公司项目\\n退出方案", "blocks": []}]
}
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from embed_fonts import embed_bundled_fonts  # noqa: E402  随技能分发的字体嵌入器
from check_yiti_text import scan_spec  # noqa: E402  议题语言扫描

TITLE_FONT = "方正小标宋简体"
BODY_FONT = "仿宋_GB2312"
KAITI_FONT = "楷体_GB2312"
HEITI_FONT = "黑体"
SONGTI_FONT = "宋体"
WESTERN_FONT = "Times New Roman"

TITLE_SIZE = 22  # 二号
BODY_SIZE = 16  # 三号
PAGE_NUMBER_SIZE = 14  # 四号
TABLE_SIZE = 10.5  # 五号
BODY_LINE_PT = 28
TITLE_LINE_PT = 30
TWO_CHAR_INDENT_PT = BODY_SIZE * 2
SIGNATURE_RIGHT_INDENT_PT = BODY_SIZE * 4  # 落款右空四字

KIND_DEFAULTS = {
    "meeting": {"submit_line": "提交部门/子公司：投管公司", "recipient": "投委会："},
    "exit": {"submit_line": "提交子公司：投管公司", "recipient": ""},
}

BOLD_PATTERN = re.compile(r"\*\*(.+?)\*\*", re.S)
# 四级标题序号"（1）"随标题用仿宋_GB2312加粗，不按括号规则改楷体。
H4_SERIAL = re.compile(r"^[（(]\d+[）)]")
# 全角数字、字母和百分号转半角，保证最后一轮 Times New Roman 能作用到它们。
FULLWIDTH = {code: code - 0xFEE0 for code in range(0xFF10, 0xFF1A)}
FULLWIDTH.update({code: code - 0xFEE0 for code in range(0xFF21, 0xFF3B)})
FULLWIDTH.update({code: code - 0xFEE0 for code in range(0xFF41, 0xFF5B)})
FULLWIDTH[0xFF05] = ord("%")

# Times New Roman advance widths in em, for hanging-indent alignment.
TNR_EM = {".": 0.25, ",": 0.25, ":": 0.278, "-": 0.333, " ": 0.25, "/": 0.278, "%": 0.833}


def text_width_pt(text: str, size_pt: float = BODY_SIZE) -> float:
    """Width of a line set in Chinese font + Times New Roman at size_pt."""
    width = 0.0
    for char in text:
        if ord(char) < 128:
            width += (0.5 if char.isdigit() else TNR_EM.get(char, 0.5)) * size_pt
        else:
            width += size_pt
    return width


def set_run_font(run, east_asia_font: str, size_pt: float, bold: bool = False,
                 *, western_font: str = WESTERN_FONT, east_asia_hint: bool = True) -> None:
    """Set all font slots explicitly; the footer passes 宋体 for every slot."""
    run.font.name = western_font
    run.font.size = Pt(size_pt)
    run.bold = bold
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.get_or_add_rFonts()
    rfonts.set(qn("w:ascii"), western_font)
    rfonts.set(qn("w:hAnsi"), western_font)
    rfonts.set(qn("w:cs"), western_font)
    rfonts.set(qn("w:eastAsia"), east_asia_font)
    if east_asia_hint:
        # 中文引号、破折号、省略号按中文字体排；数字、字母、% 属 ASCII，仍用 Times New Roman。
        rfonts.set(qn("w:hint"), "eastAsia")
    sz_cs = rpr.find(qn("w:szCs"))
    if sz_cs is None:
        sz_cs = OxmlElement("w:szCs")
        rpr.append(sz_cs)
    sz_cs.set(qn("w:val"), str(int(size_pt * 2)))
    lang = rpr.find(qn("w:lang"))
    if lang is None:
        lang = OxmlElement("w:lang")
        rpr.append(lang)
    lang.set(qn("w:eastAsia"), "zh-CN")


def parenthesis_mask(text: str) -> list[bool]:
    """True for every character inside a matched pair of round parentheses."""
    mask = [False] * len(text)
    stack = []
    for index, char in enumerate(text):
        if char in "（(":
            stack.append((index, char))
        elif char in "）)" and stack:
            if stack[-1][1] == {"）": "（", ")": "("}[char]:
                start, _ = stack.pop()
                mask[start:index + 1] = [True] * (index - start + 1)
    return mask


def add_runs_with_inline_bold(paragraph, text: str, east_asia_font: str, size_pt: float,
                              bold: bool = False, *, paren_size: float = BODY_SIZE,
                              keep_serial: bool = False) -> None:
    text = text.translate(FULLWIDTH)
    segments = []
    pos = 0
    for match in BOLD_PATTERN.finditer(text):
        if match.start() > pos:
            segments.append((text[pos:match.start()], bold))
        segments.append((match.group(1), True))
        pos = match.end()
    if pos < len(text):
        segments.append((text[pos:], bold))

    # Match nested full-/half-width round parentheses across bold boundaries.
    plain = "".join(part for part, _ in segments)
    in_parentheses = parenthesis_mask(plain)
    serial = H4_SERIAL.match(plain) if keep_serial else None
    if serial:
        in_parentheses[:serial.end()] = [False] * serial.end()

    offset = 0
    for part, is_bold in segments:
        start = 0
        while start < len(part):
            special = in_parentheses[offset + start]
            end = start + 1
            while end < len(part) and in_parentheses[offset + end] == special:
                end += 1
            set_run_font(
                paragraph.add_run(part[start:end]),
                KAITI_FONT if special else east_asia_font,
                paren_size if special else size_pt,
                is_bold,
            )
            start = end
        offset += len(part)


def set_paragraph_format(
    paragraph,
    *,
    line_pt: int = BODY_LINE_PT,
    first_indent_pt: float = TWO_CHAR_INDENT_PT,
    alignment=WD_ALIGN_PARAGRAPH.JUSTIFY,
    left_indent_pt: float = 0,
    right_indent_pt: float = 0,
) -> None:
    fmt = paragraph.paragraph_format
    fmt.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    fmt.line_spacing = Pt(line_pt)
    fmt.space_before = Pt(0)
    fmt.space_after = Pt(0)
    fmt.first_line_indent = Pt(first_indent_pt)
    if left_indent_pt:
        fmt.left_indent = Pt(left_indent_pt)
    if right_indent_pt:
        fmt.right_indent = Pt(right_indent_pt)
    paragraph.alignment = alignment


def add_paragraph(
    doc: Document,
    text: str,
    *,
    font: str = BODY_FONT,
    size: float = BODY_SIZE,
    bold: bool = False,
    line_pt: int = BODY_LINE_PT,
    first_indent: bool = True,
    alignment=WD_ALIGN_PARAGRAPH.JUSTIFY,
    keep_serial: bool = False,
):
    p = doc.add_paragraph()
    set_paragraph_format(
        p,
        line_pt=line_pt,
        first_indent_pt=TWO_CHAR_INDENT_PT if first_indent else 0,
        alignment=alignment,
    )
    add_runs_with_inline_bold(p, text, font, size, bold, keep_serial=keep_serial)
    return p


def add_blank_line(doc: Document, line_pt: int = BODY_LINE_PT):
    p = doc.add_paragraph()
    set_paragraph_format(p, line_pt=line_pt, first_indent_pt=0)
    return p


def disable_auto_spacing(paragraph) -> None:
    """Stop Word adding CJK/Latin gaps so hanging indents align to the character."""
    ppr = paragraph._p.get_or_add_pPr()
    for tag in ("w:autoSpaceDE", "w:autoSpaceDN"):
        element = OxmlElement(tag)
        element.set(qn("w:val"), "0")
        ppr.append(element)


def add_page_field(paragraph) -> None:
    def songti(run):
        set_run_font(run, SONGTI_FONT, PAGE_NUMBER_SIZE, western_font=SONGTI_FONT, east_asia_hint=False)

    songti(paragraph.add_run("-"))
    field_run = paragraph.add_run()
    songti(field_run)
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    result = OxmlElement("w:t")
    result.text = "1"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    for element in (begin, instr, separate, result, end):
        field_run._r.append(element)
    songti(paragraph.add_run("-"))
    # Paragraph mark in 四号宋体 too, so the footer line height follows the page number.
    mark = OxmlElement("w:rPr")
    fonts = OxmlElement("w:rFonts")
    for slot in ("ascii", "hAnsi", "eastAsia", "cs"):
        fonts.set(qn("w:" + slot), SONGTI_FONT)
    size = OxmlElement("w:sz")
    size.set(qn("w:val"), str(PAGE_NUMBER_SIZE * 2))
    mark.extend([fonts, size])
    paragraph._p.get_or_add_pPr().append(mark)


def setup_document(doc: Document, page_numbers: bool) -> None:
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

    if page_numbers:
        # 奇偶页不同：奇数页居右，偶数页居左。
        doc.settings.odd_and_even_pages_header_footer = True
        odd_footer = section.footer.paragraphs[0]
        odd_footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        add_page_field(odd_footer)
        even_footer = section.even_page_footer.paragraphs[0]
        even_footer.alignment = WD_ALIGN_PARAGRAPH.LEFT
        add_page_field(even_footer)


def set_chinese_language(doc: Document) -> None:
    """Chinese typography defaults instead of python-docx's en-US/ja-JP template."""
    defaults = doc.styles.element.find(qn("w:docDefaults"))
    lang = defaults.find(".//" + qn("w:lang")) if defaults is not None else None
    if lang is not None:
        lang.set(qn("w:eastAsia"), "zh-CN")
    theme_lang = doc.settings.element.find(qn("w:themeFontLang"))
    if theme_lang is not None:
        theme_lang.set(qn("w:eastAsia"), "zh-CN")


def column_widths_pt(all_rows: list, n_cols: int, total_pt: float) -> list[float]:
    """Content-based column widths that fill the text width, like Word's autofit.

    Short labels (序号、数字、"（工作日）"，不超过6个汉字宽) never wrap, so they set a
    column's minimum; the width left over is shared in proportion to how much
    longer each column's longest line is than its minimum.
    """
    padding = 12.0  # left + right cell margins
    short_limit = TABLE_SIZE * 6
    minimum, maximum = [], []
    for c_idx in range(n_cols):
        widths = [text_width_pt(line, TABLE_SIZE)
                  for row in all_rows if c_idx < len(row)
                  for line in str(row[c_idx]).replace("**", "").splitlines()]
        short = [w for w in widths if w <= short_limit]
        low = max(short + [TABLE_SIZE * 2]) + padding
        minimum.append(low)
        maximum.append(max(widths + [0.0]) + padding if widths else low)
        maximum[-1] = max(maximum[-1], low)
    if sum(maximum) <= total_pt:
        extra = total_pt - sum(maximum)
        return [w + extra * w / sum(maximum) for w in maximum]
    stretch = [hi - lo for lo, hi in zip(minimum, maximum)]
    free = total_pt - sum(minimum)
    if free <= 0 or not sum(stretch):
        return [total_pt * lo / sum(minimum) for lo in minimum]
    return [lo + free * s / sum(stretch) for lo, s in zip(minimum, stretch)]


def add_table(doc: Document, block: dict) -> None:
    caption = block.get("caption")
    if caption:
        add_paragraph(doc, caption).paragraph_format.keep_with_next = True

    header = block.get("header") or []
    rows = block.get("rows") or []
    all_rows = ([header] if header else []) + rows
    if not all_rows:
        return
    n_cols = max(len(r) for r in all_rows)

    table = doc.add_table(rows=len(all_rows), cols=n_cols)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True

    # Fill the window width so the table never overflows the text area; columns
    # start from content-based widths and Word may still autofit them.
    tbl_pr = table._tbl.tblPr
    tbl_w = tbl_pr.find(qn("w:tblW"))
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.append(tbl_w)
    tbl_w.set(qn("w:type"), "pct")
    tbl_w.set(qn("w:w"), "5000")
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "autofit")
    tbl_pr.append(layout)
    section = doc.sections[-1]
    text_width = section.page_width.pt - section.left_margin.pt - section.right_margin.pt
    widths = column_widths_pt(all_rows, n_cols, text_width)
    for grid_col, width in zip(table._tbl.tblGrid.findall(qn("w:gridCol")), widths):
        grid_col.set(qn("w:w"), str(round(width * 20)))
    for row in table.rows:
        for cell, width in zip(row.cells, widths):
            cell.width = Pt(width)

    for r_idx, row_data in enumerate(all_rows):
        is_header = bool(header) and r_idx == 0
        tr_pr = table.rows[r_idx]._tr.get_or_add_trPr()
        tr_pr.append(OxmlElement("w:cantSplit"))  # 行不跨页断开
        if is_header:
            tr_pr.append(OxmlElement("w:tblHeader"))  # 跨页重复表头
        for c_idx in range(n_cols):
            cell = table.rows[r_idx].cells[c_idx]
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            text = str(row_data[c_idx]) if c_idx < len(row_data) else ""
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            fmt = p.paragraph_format
            fmt.space_before = Pt(0)
            fmt.space_after = Pt(0)
            fmt.first_line_indent = Pt(0)
            # 表格内一律五号：括号外仿宋_GB2312，括号内楷体_GB2312。
            add_runs_with_inline_bold(p, text, BODY_FONT, TABLE_SIZE, bold=is_header,
                                      paren_size=TABLE_SIZE)


def normalize_attachment_name(name: str) -> str:
    """The JSON supplies names only; remove title marks and trailing punctuation."""
    return name.translate(str.maketrans("", "", "《》〈〉")).rstrip(" \t\r\n。，、；：！？.,;:!?…")


def add_attachment_line(doc: Document, text: str, text_start_pt: float, first_line_start_pt: float):
    """One attachment paragraph whose wrapped lines start at text_start_pt."""
    p = doc.add_paragraph()
    set_paragraph_format(
        p,
        first_indent_pt=first_line_start_pt - text_start_pt,
        left_indent_pt=text_start_pt,
    )
    disable_auto_spacing(p)
    add_runs_with_inline_bold(p, text, BODY_FONT, BODY_SIZE)
    return p


def add_attachments(doc: Document, attachments: list[str], *, keep_with_body: bool = False) -> None:
    """附件说明：正文下空一行，左空二字写"附件："。

    单份：附件：名称（回行与名称首字对齐）。
    多份：附件：1.名称 / 2.名称……，"2."与"1."对齐，每份回行与序号后的名称首字对齐。
    """
    if not attachments:
        return
    attachments = [normalize_attachment_name(name) for name in attachments]
    if keep_with_body:
        # 有落款时，正文末段随附件说明、落款同页，落款页不只剩附件和署名。
        doc.paragraphs[-1].paragraph_format.keep_with_next = True
    add_blank_line(doc).paragraph_format.keep_with_next = keep_with_body
    label = "附件："
    label_start = TWO_CHAR_INDENT_PT
    number_start = label_start + text_width_pt(label)
    if len(attachments) == 1:
        add_attachment_line(doc, label + attachments[0], number_start, label_start)
        return
    lines = []
    for idx, name in enumerate(attachments, start=1):
        number = f"{idx}."
        text_start = number_start + text_width_pt(number)
        if idx == 1:
            lines.append(add_attachment_line(doc, f"{label}{number}{name}", text_start, label_start))
        else:
            lines.append(add_attachment_line(doc, f"{number}{name}", text_start, number_start))
    for line in lines[:-1]:
        line.paragraph_format.keep_with_next = True  # 多份附件说明不跨页拆开


def add_signature(doc: Document, signature: dict) -> None:
    """落款：附件说明下空两行；署名右空四字，成文日期在署名下居中对齐。"""
    issuer = str(signature.get("issuer", "")).strip()
    date = str(signature.get("date", "")).strip()
    if not issuer and not date:
        return
    # 落款不单独成页：附件说明（或正文末段）、两行空行与署名连在一起。
    doc.paragraphs[-1].paragraph_format.keep_with_next = True
    for _ in range(2):
        add_blank_line(doc).paragraph_format.keep_with_next = True
    width = max(text_width_pt(issuer), text_width_pt(date))
    for text in (issuer, date):
        if not text:
            continue
        p = doc.add_paragraph()
        set_paragraph_format(
            p,
            first_indent_pt=0,
            alignment=WD_ALIGN_PARAGRAPH.RIGHT,
            right_indent_pt=SIGNATURE_RIGHT_INDENT_PT + (width - text_width_pt(text)) / 2,
        )
        disable_auto_spacing(p)
        add_runs_with_inline_bold(p, text, BODY_FONT, BODY_SIZE)
        p.paragraph_format.keep_with_next = text == issuer and bool(date)


def add_title_lines(doc: Document, title: str) -> None:
    for line in str(title).splitlines():
        add_paragraph(
            doc,
            line,
            font=TITLE_FONT,
            size=TITLE_SIZE,
            line_pt=TITLE_LINE_PT,
            first_indent=False,
            alignment=WD_ALIGN_PARAGRAPH.CENTER,
        )


def add_appendices(doc: Document, appendices: list[dict]) -> None:
    """附件正文另起一页：左上角顶格"附件："，二号方正小标宋标题，空一行后接正文。"""
    for idx, appendix in enumerate(appendices, start=1):
        default_label = "附件：" if len(appendices) == 1 else f"附件{idx}："
        label = add_paragraph(doc, appendix.get("label", default_label), first_indent=False)
        label.paragraph_format.page_break_before = True
        label.paragraph_format.keep_with_next = True
        add_title_lines(doc, appendix.get("title", ""))
        add_blank_line(doc, TITLE_LINE_PT)
        for block in appendix.get("blocks", []):
            add_block(doc, block)


HEADING_FONTS = {
    "h1": (HEITI_FONT, False),  # 一、黑体
    "h2": (KAITI_FONT, True),  # （一）楷体_GB2312加粗
    "h3": (BODY_FONT, True),  # 1.仿宋_GB2312加粗
    "h4": (BODY_FONT, True),  # （1）仿宋_GB2312加粗
}


def add_block(doc: Document, block: dict) -> None:
    kind = block.get("type", "para")
    text = block.get("text", "")
    if kind in HEADING_FONTS:
        font, bold = HEADING_FONTS[kind]
        p = add_paragraph(doc, text, font=font, bold=bold, line_pt=TITLE_LINE_PT,
                          keep_serial=kind == "h4")
        p.paragraph_format.keep_with_next = True  # 标题不单独留在页末
    elif kind == "table":
        add_table(doc, block)
    elif kind == "blank":
        add_blank_line(doc)
    else:
        add_paragraph(doc, text)


def apply_western_font_pass(doc: Document) -> None:
    """最后一轮：全文（不含页脚）西文槽位统一 Times New Roman，中文字体不变。"""
    for run in doc.element.body.iter(qn("w:r")):
        rfonts = run.get_or_add_rPr().get_or_add_rFonts()
        for slot in ("ascii", "hAnsi", "cs"):
            rfonts.set(qn("w:" + slot), WESTERN_FONT)


def build_docx(data: dict, output: Path) -> None:
    kind = data.get("kind", "meeting")
    defaults = KIND_DEFAULTS.get(kind, KIND_DEFAULTS["meeting"])

    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = WESTERN_FONT
    normal.font.size = Pt(BODY_SIZE)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), BODY_FONT)
    set_chinese_language(doc)
    # 页脚固定为"-1-"四号宋体、奇偶页不同；仅在明确传 false 时关闭。
    setup_document(doc, page_numbers=bool(data.get("page_numbers", True)))

    add_title_lines(doc, data.get("title", "审议关于XXXX的议题"))

    submit_line = data.get("submit_line", defaults["submit_line"])
    if submit_line:
        add_paragraph(
            doc,
            submit_line,
            font=KAITI_FONT,
            line_pt=TITLE_LINE_PT,
            first_indent=False,
            alignment=WD_ALIGN_PARAGRAPH.CENTER,
        )

    add_blank_line(doc)

    recipient = data.get("recipient", defaults["recipient"])
    if recipient:
        add_paragraph(doc, recipient, first_indent=False)

    intro = data.get("intro")
    for paragraph in [intro] if isinstance(intro, str) else (intro or []):
        add_paragraph(doc, paragraph)

    for block in data.get("blocks", []):
        add_block(doc, block)

    signature = data.get("signature") or {}
    add_attachments(doc, data.get("attachments", []),
                    keep_with_body=bool(signature.get("issuer") or signature.get("date")))
    add_signature(doc, signature)
    add_appendices(doc, data.get("appendices") or [])

    apply_western_font_pass(doc)
    doc.save(output)
    # 嵌入随附的可嵌入字体（仿宋_GB2312、楷体_GB2312），使交付件在未装这两款
    # 字体的机器上不掉字；方正小标宋许可禁止嵌入，自动跳过。校验不过则保留
    # 未嵌入版本，不影响生成。
    embed_bundled_fonts(output)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a 投委会议题 DOCX from a JSON spec.")
    parser.add_argument("input", type=Path, help="JSON spec path")
    parser.add_argument("output", type=Path, help="Output .docx path")
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8-sig"))
    build_docx(data, args.output)
    print(f"Saved: {args.output}")
    hard, warn = scan_spec(data)
    if hard or warn:
        print("文本检查（硬规则须改掉后重新生成）：", file=sys.stderr)
        for line in hard + warn:
            print("  " + line, file=sys.stderr)


if __name__ == "__main__":
    main()
