#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_docx.py —— 立项报告章节 Word 生成器（三技能统一公文排版 v3）

本脚本是 hangye-fenxi / zhuying-yewu-fenxi / gongsi-qingkuang 三个技能共用的
排版渲染器。技能自包含、可独立分发，故不能跨技能 import，三份必须各自留物理
副本且内容完全一致。改动流程：改 gongsi-qingkuang 下的基准副本，然后运行
    python tools/check_shared_scripts.py --sync
把改动同步到另外两份；提交前用 `python tools/check_shared_scripts.py` 校验一致
（不带 --sync 时发现漂移即退出码 1）。不要手工逐份修改。
统一公文版式基准（与 yiti-skill 的 references/format-rules.md 一致，依据集团
《关于规范行文格式的通知》所附模板）：

- A4 页面（上 3.7cm、下 3.5cm、左 2.8cm、右 2.6cm）
- 封面主标题（方正小标宋简体二号 22pt、居中、固定行距 30 磅）；默认不生成封面
- 正文（仿宋_GB2312 三号 16pt、两端对齐、首行缩进 2 字符、固定行距 28 磅，段前段后 0）
- 四级编号标题（一、/（一）/ 1. /（1））均首行缩进 2 字符、与段落平齐、固定行距 30 磅：
  一级黑体三号不加粗；二级楷体_GB2312 三号加粗；三级仿宋_GB2312 三号加粗；
  四级仿宋_GB2312 三号加粗（序号"（1）"随标题用仿宋加粗，其余括注适用括注规则）
- 核心结论/段首论点句：整段加粗（type=p, bold=true）
- 字体按四步设置：①中文字体按角色；②圆括号及其内文字改楷体_GB2312，字号随所在
  位置（封面标题二号、正文三号、表格与表注五号），保留加粗；③页脚 -1- 四号宋体；
  ④最后全文（不含页脚）西文字体统一 Times New Roman，中文字体不变
- 全角数字、字母和％先转半角，保证第④步能作用到它们
- 表格（统一表格规范）：
    * 全表统一五号 10.5pt：括号外仿宋_GB2312，括号及括号内楷体_GB2312
    * 仅首行（表头）加粗，无底纹；其余单元格不加粗
    * 所有单元格内容水平居中 + 垂直居中，单倍行距
    * 黑色单线全框线
    * 表头行跨页重复（tblHeader），各行不跨页断开（cantSplit）
    * 表宽铺满版心（pct 100% + tblLayout=autofit）；列宽按内容分配，
      table 块给出 widths 时按其比例（转百分比）
    * 表格前一段（引导句）与表格同页
- 表注（type=tnote）："单位：万元""注：……"等，仿宋_GB2312 五号、不缩进，
  align 可选 left/right/center（默认 left；"单位"行惯例放表格上方右对齐）
- 页脚页码（奇偶页不同，奇数页居右、偶数页居左，完整 -1- 四号宋体）
- 附件说明：正文下空一行，"附件："左空二字；多份为"附件：1.XXX"，"2."与"1."对齐，
  回行悬挂对齐到名称首字（按实际字宽计算，关闭中西文自动间距）
- 落款（可选 signature）：附件说明下空两行，署名右空四字，成文日期在署名下居中
- 字体嵌入：保存后自动把随附的仿宋_GB2312、楷体_GB2312 嵌入 DOCX，使文件在未
  安装这两款字体的机器上仍忠实呈现（方正小标宋许可禁止嵌入，自动跳过）；
  嵌入经反混淆校验，失败则保留未嵌入版本，绝不影响正常生成
- 封面 / 目录：默认关闭（章节通常并入整份立项报告）；独立成文时在 content
  里给 cover 或把 toc 设为 true

数据缺口纪律：资料包、会议纪要、权威网络检索均无法获得的数据，一律不进入
本脚本渲染的报告正文与表格（也不要用 note 块写"待核查"占位）；全部缺口在
对话回复中以"资料缺口与待核查清单"形式提示用户。note 块仅在用户明确要求
在文中标注缺口时使用。

设计原则：脚本只管"排版"，不管"写作"。调用方负责把写好的章节内容按下面的
BLOCK 结构组织好传进来，脚本对内容零编造。

生成前先运行 `python scripts/ensure_fonts.py` 确保公文字体已安装。

依赖：python-docx  →  pip install python-docx --break-system-packages

用法：
    python build_docx.py content.json out.docx
或在 python 中：
    from build_docx import build
    build(content_dict, "out.docx")

content 结构（dict）：
{
  "cover": {                              # 可选，默认不生成封面
     "title_lines": ["关于投资XX公司的", "立项报告"],
     "org": "XX投资管理有限公司",
     "date": "2026年7月"
  },
  "toc": false,                           # 是否插入目录域，默认 false
  "summary": "要点概述正文（可选，多段用 \\n 分隔）",
  "summary_title": "要点概述",            # 可选，默认"要点概述"
  "blocks": [ ...见下... ],               # 章节正文，按顺序渲染
  "attachments": ["实施方案（试行）", "测算表"],  # 可选；单份无序号，多份阿拉伯数字
  "signature": {"issuer": "XX投资管理有限公司", "date": "2026年9月1日"}  # 可选落款
}

blocks 里每个元素是一个 dict，type 决定渲染方式：
  {"type":"h1","text":"二、所属行业分析"}          # 一级标题（自带"二、"前缀）
  {"type":"h2","text":"（一）行业发展现状"}          # 二级
  {"type":"h3","text":"1.市场规模与增长趋势"}        # 三级
  {"type":"h4","text":"（1）政策驱动"}              # 四级（加粗）
  {"type":"p","text":"正文段落……"}                 # 普通段落
  {"type":"p","text":"……","bold":true}            # 加粗段落（核心结论/段首论点句）
  {"type":"p","lead":"段首判断句。","text":"其后证据……"}  # 仅段首判断句加粗，其余同段不加粗
  {"type":"bullet","items":["要点1","要点2"]}       # 项目符号列表
  {"type":"tnote","text":"单位：万元","align":"right"}   # 表注，仿宋五号
  {"type":"table","header":["列1","列2"],           # 表格；header 可省略（无表头）
      "rows":[["a","b"],["c","d"]]}                 # 铺满版心，列宽按内容分配
  {"type":"table","header":[...],"rows":[...],
      "widths":[3,6]}                               # 可选：列宽比例（随窗口缩放）
  {"type":"image","path":"photos/product.jpg",      # 插图（如产品实物照片），居中；
      "width_cm":12,"caption":"图1 核心产品实物"}     # 相对路径按 content.json 所在目录解析
  {"type":"note","text":"【待进一步核实】"}          # 灰色提示；默认不使用（见缺口纪律）
  {"type":"pagebreak"}                             # 分页
  {"type":"_注","text":"骨架注释，不会渲染"}          # "_"开头的类型视为模板注释，跳过

标题层级与编号：脚本不自动编号，"二、""（一）"等前缀由你写在 text 里。
"""

import sys, json, re
from pathlib import Path

from docx import Document
from docx.shared import Pt, RGBColor, Twips, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

sys.path.insert(0, str(Path(__file__).resolve().parent))
from embed_fonts import embed_bundled_fonts  # 随技能分发的字体嵌入器
from docx_format_helpers import parenthesized_spans, normalize_attachment_name

# ---------- 版式常量（与 yiti-skill 统一的公文格式） ----------
FONT_TITLE = "方正小标宋简体"
FONT_BODY = "仿宋_GB2312"
FONT_H1 = "黑体"            # 使用系统原本黑体，不随技能打包替换
FONT_H2 = "楷体_GB2312"
FONT_FOOTER = "宋体"
FONT_EN = "Times New Roman"
BODY_SZ = 16               # 三号
H1_SZ = 16                 # 一级标题黑体三号，不加粗
H2_SZ = 16                 # 二级标题楷体_GB2312 三号，加粗
H3_SZ = 16                 # 三级标题仿宋_GB2312 三号，加粗
H4_SZ = 16                 # 四级标题仿宋_GB2312 三号，加粗
COVER_TITLE_SZ = 22        # 二号方正小标宋简体
COVER_ORG_SZ = 16          # 落款/机构三号仿宋_GB2312
FOOTER_SZ = 14             # 四号宋体
BODY_LINE_PT = 28
TITLE_LINE_PT = 30         # 主标题及各级编号标题
TABLE_BORDER = "auto"      # 表格黑色单线全框线
CONTENT_WIDTH = 8844       # A4：21cm - 2.8cm - 2.6cm ≈ 15.6cm（DXA≈8844）
CONTENT_WIDTH_PT = CONTENT_WIDTH / 20
TABLE_SZ = 10.5            # 表格统一五号，所有单元格；表注同
TWO_CHAR_INDENT_PT = BODY_SZ * 2
SIGNATURE_RIGHT_INDENT_PT = BODY_SZ * 4  # 落款右空四字

# 四级标题序号"（1）"随标题用仿宋_GB2312加粗，不按括号规则改楷体。
H4_SERIAL = re.compile(r'^\s*[（(]\d+[）)]')
# 全角数字、字母和百分号转半角，保证最后一轮 Times New Roman 能作用到它们。
FULLWIDTH = {code: code - 0xFEE0 for code in range(0xFF10, 0xFF1A)}
FULLWIDTH.update({code: code - 0xFEE0 for code in range(0xFF21, 0xFF3B)})
FULLWIDTH.update({code: code - 0xFEE0 for code in range(0xFF41, 0xFF5B)})
FULLWIDTH[0xFF05] = ord('%')
# Times New Roman 字宽（em），用于附件说明悬挂缩进与落款居中。
TNR_EM = {'.': 0.25, ',': 0.25, ':': 0.278, '-': 0.333, ' ': 0.25, '/': 0.278, '%': 0.833}


def _text_width_pt(text, size=BODY_SZ):
    """中文字体 + Times New Roman 混排时一行文字的宽度（磅）。"""
    width = 0.0
    for char in str(text):
        if ord(char) < 128:
            width += (0.5 if char.isdigit() else TNR_EM.get(char, 0.5)) * size
        else:
            width += size
    return width


def _set_run_font(run, size=BODY_SZ, bold=False, color=None, font_name=FONT_BODY,
                  western_font=FONT_EN, east_asia_hint=True):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.name = western_font
    # 中文字体需要单独设 eastAsia
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn('w:rFonts'))
    if rfonts is None:
        rfonts = OxmlElement('w:rFonts')
        rpr.insert(0, rfonts)
    rfonts.set(qn('w:ascii'), western_font)
    rfonts.set(qn('w:hAnsi'), western_font)
    rfonts.set(qn('w:cs'), western_font)
    rfonts.set(qn('w:eastAsia'), font_name)
    if east_asia_hint:
        # 中文引号、破折号、省略号按中文字体排；数字、字母、% 属 ASCII，仍用 Times New Roman。
        rfonts.set(qn('w:hint'), 'eastAsia')
    if color:
        run.font.color.rgb = RGBColor.from_string(color)
    sz_cs = rpr.find(qn('w:szCs'))
    if sz_cs is None:
        sz_cs = OxmlElement('w:szCs')
        rpr.append(sz_cs)
    sz_cs.set(qn('w:val'), str(int(size * 2)))
    lang = rpr.find(qn('w:lang'))
    if lang is None:
        lang = OxmlElement('w:lang')
        rpr.append(lang)
    lang.set(qn('w:eastAsia'), 'zh-CN')


def _add_text_runs(paragraph, text, size=BODY_SZ, bold=False, color=None,
                   font_name=FONT_BODY, heading4=False):
    """括号及括号内文字用楷体_GB2312，字号与所在位置一致（标题二号、正文三号、
    表格/表注五号），保留所在位置的加粗；四级标题序号"（1）"随标题。"""
    text = str(text).translate(FULLWIDTH)
    cursor = 0
    prefix = H4_SERIAL.match(text) if heading4 else None
    for start, end in parenthesized_spans(text):
        if cursor < start:
            _set_run_font(paragraph.add_run(text[cursor:start]), size, bold, color, font_name)
        if prefix is not None and start < prefix.end():
            # 序号与后续括注合并成一个区间时，序号部分仍随标题字体。
            serial_end = prefix.end()
            _set_run_font(paragraph.add_run(text[start:serial_end]), size, bold, color, font_name)
            start = serial_end
        if start < end:
            _set_run_font(paragraph.add_run(text[start:end]), size, bold, color, FONT_H2)
        cursor = end
    if cursor < len(text):
        _set_run_font(paragraph.add_run(text[cursor:]), size, bold, color, font_name)


def _add_para(doc, text, size=BODY_SZ, bold=False, align=None, color=None,
              space_before=0, space_after=0, outline=None, line=None,
              font_name=FONT_BODY):
    p = doc.add_paragraph()
    if align is not None:
        p.alignment = align
    pf = p.paragraph_format
    pf.space_before = Pt(space_before)
    pf.space_after = Pt(space_after)
    if line:
        if isinstance(line, (int, float)) and line > 5:
            pf.line_spacing = Pt(line)
            pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
        else:
            pf.line_spacing = line
    _add_text_runs(p, text, size=size, bold=bold, color=color, font_name=font_name,
                   heading4=outline == 3)
    if outline is not None:
        _set_outline_level(p, outline)
    return p


def _set_outline_level(paragraph, level):
    """给段落打 outlineLevel，使其能进 TOC（0=H1,1=H2,...）。"""
    pPr = paragraph._p.get_or_add_pPr()
    ol = pPr.find(qn('w:outlineLvl'))
    if ol is None:
        ol = OxmlElement('w:outlineLvl')
        pPr.append(ol)
    ol.set(qn('w:val'), str(level))


def _indent_first_line(paragraph, chars=2):
    """正文段落及各级标题首行缩进 2 字符（标题与段落平齐）。"""
    pPr = paragraph._p.get_or_add_pPr()
    ind = pPr.find(qn('w:ind'))
    if ind is None:
        ind = OxmlElement('w:ind')
        pPr.append(ind)
    ind.set(qn('w:firstLineChars'), str(chars * 100))


def _style_cell(cell, fill=None, color=TABLE_BORDER, sz=4,
                margins=(60, 60, 100, 100), valign='center'):
    """一次性构建 tcPr 的子元素，严格按 OOXML schema 顺序：
       tcBorders → shd → tcMar → vAlign 。顺序错了 Word 校验会报错。
       valign 默认 center：单元格内容垂直居中（配合段落水平居中，实现表格内容整体居中）。"""
    tcPr = cell._tc.get_or_add_tcPr()
    for tag in ('w:tcBorders', 'w:shd', 'w:tcMar', 'w:vAlign'):
        for e in tcPr.findall(qn(tag)):
            tcPr.remove(e)
    # 1) 边框
    borders = OxmlElement('w:tcBorders')
    for edge in ('top', 'left', 'bottom', 'right'):
        el = OxmlElement(f'w:{edge}')
        el.set(qn('w:val'), 'single')
        el.set(qn('w:sz'), str(sz))
        el.set(qn('w:space'), '0')
        el.set(qn('w:color'), color)
        borders.append(el)
    tcPr.append(borders)
    # 2) 底色
    if fill:
        shd = OxmlElement('w:shd')
        shd.set(qn('w:val'), 'clear')
        shd.set(qn('w:color'), 'auto')
        shd.set(qn('w:fill'), fill)
        tcPr.append(shd)
    # 3) 内边距
    top, bottom, left, right = margins
    m = OxmlElement('w:tcMar')
    for edge, val in (('top', top), ('start', left), ('bottom', bottom), ('end', right)):
        el = OxmlElement(f'w:{edge}')
        el.set(qn('w:w'), str(val))
        el.set(qn('w:type'), 'dxa')
        m.append(el)
    tcPr.append(m)
    # 4) 垂直居中（水平居中在 _fill_cell 的段落上设置）
    if valign:
        v = OxmlElement('w:vAlign')
        v.set(qn('w:val'), valign)
        tcPr.append(v)


def _fill_cell(cell, text, bold=False, header=False, size=TABLE_SZ):
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER  # 水平居中；垂直居中见 _style_cell
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.first_line_indent = Pt(0)
    # 表格用单倍行距，不套用正文 28 磅固定行距。
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    _add_text_runs(p, str(text) if text is not None else "",
                   size=TABLE_SZ, bold=bold or header, font_name=FONT_BODY)
    _style_cell(cell)


def _mark_header_row(row):
    """表头行设 tblHeader：表格跨页时每页重复表头。"""
    trPr = row._tr.get_or_add_trPr()
    if trPr.find(qn('w:tblHeader')) is None:
        th = OxmlElement('w:tblHeader')
        th.set(qn('w:val'), 'true')
        trPr.append(th)


def _mark_cant_split(row):
    """行不跨页断开。cantSplit 在 CT_TrPr 中位于 tblHeader 之前。"""
    trPr = row._tr.get_or_add_trPr()
    if trPr.find(qn('w:cantSplit')) is None:
        trPr.insert(0, OxmlElement('w:cantSplit'))


def _column_widths(all_rows, ncols, total=CONTENT_WIDTH_PT):
    """按内容分配列宽并铺满版心（与 yiti-skill 相同的算法）。

    序号、数字、"（工作日）"等不超过 6 个汉字宽的短文字不折行，决定该列最小宽度；
    剩余宽度按各列最长一行超出最小宽度的部分成比例分配。
    """
    padding = 10.0  # 单元格左右内边距（100 + 100 twips）
    short_limit = TABLE_SZ * 6
    minimum, maximum = [], []
    for c_idx in range(ncols):
        widths = [_text_width_pt(line, TABLE_SZ)
                  for row in all_rows if c_idx < len(row)
                  for line in str(row[c_idx] if row[c_idx] is not None else "").splitlines()]
        short = [w for w in widths if w <= short_limit]
        low = max(short + [TABLE_SZ * 2]) + padding
        minimum.append(low)
        maximum.append(max(max(widths + [0.0]) + padding, low))
    if sum(maximum) <= total:
        extra = total - sum(maximum)
        return [w + extra * w / sum(maximum) for w in maximum]
    stretch = [hi - lo for lo, hi in zip(minimum, maximum)]
    free = total - sum(minimum)
    if free <= 0 or not sum(stretch):
        return [total * lo / sum(minimum) for lo in minimum]
    return [lo + free * s / sum(stretch) for lo, s in zip(minimum, stretch)]


def _add_table(doc, header, rows, widths=None):
    ncols = len(header) if header else (len(rows[0]) if rows else 1)
    if not widths or len(widths) != ncols:
        # 未给出列宽比例时按内容分配（序号等短列定宽，长文字列分得剩余宽度）
        widths = _column_widths(([header] if header else []) + list(rows), ncols)
    nrows = (1 if header else 0) + len(rows)
    table = doc.add_table(rows=nrows, cols=ncols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True                 # 根据窗口自动调整表格
    _set_tbl_autofit(table)              # 表宽=窗口 100%（pct）+ tblLayout=autofit
    r = 0
    if header:
        for j, h in enumerate(header):
            _fill_cell(table.rows[0].cells[j], h, header=True, size=TABLE_SZ)
        _mark_header_row(table.rows[0])
        r = 1
    for i, row in enumerate(rows):
        for j in range(ncols):
            val = row[j] if j < len(row) else ""
            _fill_cell(table.rows[r + i].cells[j], val, size=TABLE_SZ)
    for row in table.rows:
        _mark_cant_split(row)
    # 列宽用百分比：保持列宽比例，随窗口宽度整体缩放
    total = sum(widths) or 1
    col_pct = [max(1, round(w / total * 5000)) for w in widths]  # 5000 = 100.00%
    for row in table.rows:
        for j, pct in enumerate(col_pct):
            _set_cell_width_pct(row.cells[j], pct)
    return table


def _set_tbl_autofit(table):
    """表格宽度设为窗口（页面内容区）宽度的 100%，并启用 autofit 布局，
       实现 Word『根据窗口自动调整表格』。tblW 由 add_table 生成，改其属性即可，
       位置天然合法（tblStyle 之后、jc 之前）。"""
    tblPr = table._tbl.tblPr
    tblW = tblPr.find(qn('w:tblW'))
    if tblW is None:
        tblW = OxmlElement('w:tblW')
        tblPr.append(tblW)
    tblW.set(qn('w:w'), '5000')          # 5000 = 100.00%
    tblW.set(qn('w:type'), 'pct')
    layout = tblPr.find(qn('w:tblLayout'))
    if layout is None:
        layout = OxmlElement('w:tblLayout')
        tblPr.append(layout)
    layout.set(qn('w:type'), 'autofit')


def _set_cell_width_pct(cell, pct):
    """单元格首选宽度用百分比（tcW type=pct），配合表格 autofit 随窗口缩放。
       tcW 在 CT_TcPr 中须位于最前，故先清已有再 insert(0)。"""
    tcPr = cell._tc.get_or_add_tcPr()
    for e in tcPr.findall(qn('w:tcW')):
        tcPr.remove(e)
    tcW = OxmlElement('w:tcW')
    tcW.set(qn('w:w'), str(pct))
    tcW.set(qn('w:type'), 'pct')
    tcPr.insert(0, tcW)


def _add_toc(doc):
    """插入 Word 原生 TOC 域；打开文档后需手动/自动更新（右键→更新域）。"""
    _add_para(doc, "目录", size=H1_SZ, bold=False, align=WD_ALIGN_PARAGRAPH.CENTER,
              line=TITLE_LINE_PT, font_name=FONT_H1)
    p = doc.add_paragraph()
    run = p.add_run()
    fldChar1 = OxmlElement('w:fldChar'); fldChar1.set(qn('w:fldCharType'), 'begin')
    instr = OxmlElement('w:instrText'); instr.set(qn('xml:space'), 'preserve')
    instr.text = 'TOC \\o "1-3" \\h \\z \\u'
    fldChar2 = OxmlElement('w:fldChar'); fldChar2.set(qn('w:fldCharType'), 'separate')
    t = OxmlElement('w:t'); t.text = "（打开文档后右键此处『更新域』生成目录与页码）"
    fldChar3 = OxmlElement('w:fldChar'); fldChar3.set(qn('w:fldCharType'), 'end')
    for el in (fldChar1, instr, fldChar2, t, fldChar3):
        run._r.append(el)
    _set_run_font(run, font_name=FONT_H2, western_font=FONT_H2)


def _add_page_number_footer(section):
    _add_footer_page_field(section.footer.paragraphs[0], WD_ALIGN_PARAGRAPH.RIGHT)
    try:
        _add_footer_page_field(section.even_page_footer.paragraphs[0], WD_ALIGN_PARAGRAPH.LEFT)
    except Exception:
        pass


def _add_footer_page_field(p, align):
    """页码 -1-：两个短横线、PAGE 域及其显示结果全部四号宋体（四个字体槽均为宋体），
    不参与最后的 Times New Roman 统一。"""
    p.alignment = align

    def songti(run):
        _set_run_font(run, size=FOOTER_SZ, font_name=FONT_FOOTER,
                      western_font=FONT_FOOTER, east_asia_hint=False)

    songti(p.add_run("-"))
    run = p.add_run()
    songti(run)
    f1 = OxmlElement('w:fldChar'); f1.set(qn('w:fldCharType'), 'begin')
    instr = OxmlElement('w:instrText'); instr.set(qn('xml:space'), 'preserve'); instr.text = 'PAGE'
    separate = OxmlElement('w:fldChar'); separate.set(qn('w:fldCharType'), 'separate')
    result = OxmlElement('w:t'); result.text = '1'
    f2 = OxmlElement('w:fldChar'); f2.set(qn('w:fldCharType'), 'end')
    for el in (f1, instr, separate, result, f2):
        run._r.append(el)
    songti(p.add_run("-"))
    # 段落标记同为四号宋体，页脚行高随页码。
    mark = OxmlElement('w:rPr')
    fonts = OxmlElement('w:rFonts')
    for slot in ('ascii', 'hAnsi', 'eastAsia', 'cs'):
        fonts.set(qn('w:' + slot), FONT_FOOTER)
    size = OxmlElement('w:sz')
    size.set(qn('w:val'), str(FOOTER_SZ * 2))
    mark.extend([fonts, size])
    p._p.get_or_add_pPr().append(mark)


def _enable_odd_even_footers(doc):
    settings = doc.settings.element
    even = settings.find(qn('w:evenAndOddHeaders'))
    if even is None:
        settings.append(OxmlElement('w:evenAndOddHeaders'))


def _set_a4_page(section):
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(3.7)
    section.bottom_margin = Cm(3.5)
    section.left_margin = Cm(2.8)
    section.right_margin = Cm(2.6)
    section.header_distance = Cm(1.5)
    section.footer_distance = Cm(2.35)


def _set_chinese_language(doc):
    """中文排版默认语言，替换 python-docx 模板里的 en-US/ja-JP。"""
    defaults = doc.styles.element.find(qn('w:docDefaults'))
    lang = defaults.find('.//' + qn('w:lang')) if defaults is not None else None
    if lang is not None:
        lang.set(qn('w:eastAsia'), 'zh-CN')
    theme_lang = doc.settings.element.find(qn('w:themeFontLang'))
    if theme_lang is not None:
        theme_lang.set(qn('w:eastAsia'), 'zh-CN')


# CT_PPr 中位于 autoSpaceDE/autoSpaceDN 之后的子元素（按 schema 顺序插入）。
_AUTO_SPACE_SUCCESSORS = (
    'w:bidi', 'w:adjustRightInd', 'w:snapToGrid', 'w:spacing', 'w:ind',
    'w:contextualSpacing', 'w:mirrorIndents', 'w:suppressOverlap', 'w:jc',
    'w:textDirection', 'w:textAlignment', 'w:textboxTightWrap', 'w:outlineLvl',
    'w:divId', 'w:cnfStyle', 'w:rPr', 'w:sectPr', 'w:pPrChange',
)


def _disable_auto_spacing(paragraph):
    """关闭中西文自动间距，使悬挂缩进与落款居中按字宽精确对齐。"""
    pPr = paragraph._p.get_or_add_pPr()
    for tag, successors in (('w:autoSpaceDE', ('w:autoSpaceDN',) + _AUTO_SPACE_SUCCESSORS),
                            ('w:autoSpaceDN', _AUTO_SPACE_SUCCESSORS)):
        element = pPr.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            pPr.insert_element_before(element, *successors)
        element.set(qn('w:val'), '0')


def _plain_para(doc, text, *, first_line_pt=0.0, left_pt=0.0, right_pt=0.0,
                align=WD_ALIGN_PARAGRAPH.JUSTIFY):
    """附件说明、落款用段落：三号仿宋、固定 28 磅、磅值缩进、关闭中西文自动间距。"""
    p = doc.add_paragraph()
    p.alignment = align
    pf = p.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    pf.line_spacing = Pt(BODY_LINE_PT)
    pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    pf.first_line_indent = Pt(first_line_pt)
    if left_pt:
        pf.left_indent = Pt(left_pt)
    if right_pt:
        pf.right_indent = Pt(right_pt)
    _disable_auto_spacing(p)
    if text:
        _add_text_runs(p, text, font_name=FONT_BODY)
    return p


def _add_attachments(doc, attachments, keep_with_body=False):
    """附件说明：正文下空一行，左空二字写"附件："。

    单份：附件：名称（回行与名称首字对齐）。
    多份：附件：1.名称 / 2.名称……，"2."与"1."对齐，每份回行与序号后的名称首字对齐。
    """
    names = [name for source in attachments or [] if (name := normalize_attachment_name(source))]
    if not names:
        return
    if keep_with_body and doc.paragraphs:
        # 有落款时，正文末段随附件说明、落款同页。
        doc.paragraphs[-1].paragraph_format.keep_with_next = True
    _plain_para(doc, "").paragraph_format.keep_with_next = keep_with_body
    label = "附件："
    label_start = TWO_CHAR_INDENT_PT
    number_start = label_start + _text_width_pt(label)
    if len(names) == 1:
        _plain_para(doc, label + names[0], first_line_pt=label_start - number_start,
                    left_pt=number_start)
        return
    lines = []
    for idx, name in enumerate(names, start=1):
        number = f"{idx}."
        text_start = number_start + _text_width_pt(number)
        if idx == 1:
            lines.append(_plain_para(doc, f"{label}{number}{name}",
                                     first_line_pt=label_start - text_start, left_pt=text_start))
        else:
            lines.append(_plain_para(doc, f"{number}{name}",
                                     first_line_pt=number_start - text_start, left_pt=text_start))
    for line in lines[:-1]:
        line.paragraph_format.keep_with_next = True  # 多份附件说明不跨页拆开


def _add_signature(doc, signature):
    """落款：附件说明下空两行；署名右空四字，成文日期在署名下居中对齐。"""
    issuer = str((signature or {}).get("issuer", "")).strip()
    date = str((signature or {}).get("date", "")).strip()
    if not issuer and not date:
        return
    if doc.paragraphs:
        doc.paragraphs[-1].paragraph_format.keep_with_next = True
    for _ in range(2):
        _plain_para(doc, "").paragraph_format.keep_with_next = True
    width = max(_text_width_pt(issuer), _text_width_pt(date))
    for text in (issuer, date):
        if not text:
            continue
        p = _plain_para(doc, text, align=WD_ALIGN_PARAGRAPH.RIGHT,
                        right_pt=SIGNATURE_RIGHT_INDENT_PT + (width - _text_width_pt(text)) / 2)
        p.paragraph_format.keep_with_next = text == issuer and bool(date)


def _fix_zoom(doc):
    """python-docx 默认 settings.xml 里的 w:zoom 可能缺 percent 属性，补上。"""
    try:
        settings = doc.settings.element
        zoom = settings.find(qn('w:zoom'))
        if zoom is not None and zoom.get(qn('w:percent')) is None:
            zoom.set(qn('w:percent'), '100')
    except Exception:
        pass


def _finalize_western_fonts(doc):
    """最后统一西文字体，保留中文字体、字号、加粗及域结构。

    覆盖正文、嵌套表格、页眉和样式；清除西文主题覆盖，避免打开 Word
    或刷新域时又恢复主题字体。所有字符（含数字、%和短横线）的西文字体槽
    均为 Times New Roman，eastAsia 不变。页脚 -1- 不参与这一步，保持四号宋体。
    """
    roots = [doc.element, doc.styles.element]
    for part in doc.part.package.parts:
        if part.partname.startswith('/word/header'):
            roots.append(part.element)
    for root in roots:
        # 空 run 和域 run 也设置，避免继承了不同的西文字体。
        for run in root.iter(qn('w:r')):
            rpr = run.get_or_add_rPr()
            if rpr.find(qn('w:rFonts')) is None:
                rpr.insert(0, OxmlElement('w:rFonts'))
        for fonts in root.iter(qn('w:rFonts')):
            for slot in ('ascii', 'hAnsi', 'cs'):
                fonts.set(qn('w:' + slot), FONT_EN)
            for slot in ('asciiTheme', 'hAnsiTheme', 'cstheme', 'csTheme'):
                fonts.attrib.pop(qn('w:' + slot), None)


def build(content, out_path):
    if "report_template" in content:
        from stage_template import validate
        validate(content, root=Path(__file__).resolve().parents[1])
    doc = Document()
    _fix_zoom(doc)
    _set_chinese_language(doc)
    _enable_odd_even_footers(doc)
    sec = doc.sections[0]
    _set_a4_page(sec)
    _add_page_number_footer(sec)

    # 设置 Normal 默认字体
    normal = doc.styles['Normal']
    normal.font.name = FONT_EN
    normal.font.size = Pt(BODY_SZ)
    normal.element.rPr.rFonts.set(qn('w:eastAsia'), FONT_BODY)
    normal.paragraph_format.line_spacing = Pt(BODY_LINE_PT)
    normal.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY

    # ---------- 封面（可选，默认不生成） ----------
    cover = content.get("cover")
    if cover:
        for _ in range(6):
            doc.add_paragraph()
        for line in cover.get("title_lines", ["立项报告"]):
            _add_para(doc, line, size=COVER_TITLE_SZ, bold=False,
                      align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10,
                      line=TITLE_LINE_PT, font_name=FONT_TITLE)
        for _ in range(6):
            doc.add_paragraph()
        if cover.get("org"):
            _add_para(doc, cover["org"], size=COVER_ORG_SZ, bold=False,
                      align=WD_ALIGN_PARAGRAPH.CENTER, space_after=8,
                      line=BODY_LINE_PT, font_name=FONT_BODY)
        if cover.get("date"):
            _add_para(doc, cover["date"], size=COVER_ORG_SZ, bold=False,
                      align=WD_ALIGN_PARAGRAPH.CENTER, line=BODY_LINE_PT,
                      font_name=FONT_BODY)
        doc.add_page_break()

    # ---------- 目录（可选，默认关闭） ----------
    if content.get("toc", False):
        _add_toc(doc)
        doc.add_page_break()

    # ---------- 要点概述（可选） ----------
    if content.get("summary"):
        _add_para(doc, content.get("summary_title", "要点概述"),
                  size=H1_SZ, bold=False, align=WD_ALIGN_PARAGRAPH.CENTER,
                  outline=0, line=TITLE_LINE_PT,
                  font_name=FONT_H1)
        for para in str(content["summary"]).split("\n"):
            if para.strip():
                p = _add_para(doc, para.strip(), align=WD_ALIGN_PARAGRAPH.JUSTIFY,
                              line=BODY_LINE_PT, font_name=FONT_BODY)
                _indent_first_line(p)
        doc.add_page_break()

    # ---------- 章节正文 ----------
    ALIGN = {"left": WD_ALIGN_PARAGRAPH.LEFT, "right": WD_ALIGN_PARAGRAPH.RIGHT,
             "center": WD_ALIGN_PARAGRAPH.CENTER}
    # 各级标题：固定行距 30 磅、段前段后 0、与下段同页（标题不单独留在页末）。
    HEADINGS = {
        "h1": (H1_SZ, False, FONT_H1, 0),     # 一、黑体不加粗
        "h2": (H2_SZ, True, FONT_H2, 1),      # （一）楷体_GB2312加粗
        "h3": (H3_SZ, True, FONT_BODY, 2),    # 1.仿宋_GB2312加粗
        "h4": (H4_SZ, True, FONT_BODY, 3),    # （1）仿宋_GB2312加粗
    }
    for blk in content.get("blocks", []):
        t = blk.get("type")
        if t in HEADINGS:
            size, bold, font, level = HEADINGS[t]
            p = _add_para(doc, blk["text"], size=size, bold=bold, outline=level,
                          align=WD_ALIGN_PARAGRAPH.JUSTIFY, line=TITLE_LINE_PT,
                          font_name=font)
            p.paragraph_format.keep_with_next = True
            _indent_first_line(p)
        elif t == "p":
            if blk.get("lead"):
                # 段首判断句加粗、其后证据不加粗，同在一段（终稿范式的节首写法）
                p = _add_para(doc, blk["lead"], bold=True,
                              align=WD_ALIGN_PARAGRAPH.JUSTIFY, line=BODY_LINE_PT,
                              font_name=FONT_BODY)
                if blk.get("text"):
                    _add_text_runs(p, blk["text"], bold=False, font_name=FONT_BODY)
            else:
                p = _add_para(doc, blk["text"], bold=blk.get("bold", False),
                              align=WD_ALIGN_PARAGRAPH.JUSTIFY, line=BODY_LINE_PT,
                              font_name=FONT_BODY)
            _indent_first_line(p)
        elif t == "bullet":
            for item in blk.get("items", []):
                p = doc.add_paragraph(style=None)
                p.paragraph_format.left_indent = Twips(480)
                p.paragraph_format.line_spacing = Pt(BODY_LINE_PT)
                p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
                _add_text_runs(p, "• " + str(item), size=BODY_SZ, font_name=FONT_BODY)
        elif t == "tnote":
            # 表注："单位：万元""注：……"，仿宋五号、不缩进；单位行惯例右对齐
            _add_para(doc, blk["text"], size=TABLE_SZ, bold=False,
                      align=ALIGN.get(blk.get("align", "left")),
                      space_before=0, space_after=2, line=18,
                      font_name=FONT_BODY)
        elif t == "table":
            if doc.paragraphs and doc.paragraphs[-1].text.strip():
                # 表格前的引导句（或"单位："表注）与表格同页
                doc.paragraphs[-1].paragraph_format.keep_with_next = True
            _add_table(doc, blk.get("header"), blk.get("rows", []), blk.get("widths"))
            doc.add_paragraph()  # 表后空行
        elif t == "image":
            # 产品实物照片等插图：居中，宽度按厘米给定（默认12cm，不超过版心），图名放图下方
            img = Path(blk["path"])
            if not img.is_absolute():
                img = Path(content.get("_base_dir", ".")) / img
            if not img.is_file():
                raise FileNotFoundError(f"image 块引用的图片不存在：{img}")
            width = min(float(blk.get("width_cm", 12)), 15.6)
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.keep_with_next = bool(blk.get("caption"))
            p.add_run().add_picture(str(img), width=Cm(width))
            if blk.get("caption"):
                _add_para(doc, blk["caption"], size=TABLE_SZ, bold=False,
                          align=WD_ALIGN_PARAGRAPH.CENTER, space_before=2,
                          space_after=6, line=18, font_name=FONT_BODY)
        elif t == "note":
            # 灰色提示：默认不使用——缺口一律在对话中提示，不写入报告（见文件头"数据缺口纪律"）
            _add_para(doc, blk["text"], color="808080", line=BODY_LINE_PT,
                      font_name=FONT_BODY)
        elif t == "pagebreak":
            doc.add_page_break()
        elif t and str(t).startswith("_"):
            # 下划线开头的块类型（"_注" "_说明" 等）是骨架/模板注释，不渲染
            continue
        else:
            # 未知类型，按普通段落处理，避免内容丢失
            if blk.get("text"):
                _add_para(doc, blk["text"], align=WD_ALIGN_PARAGRAPH.JUSTIFY,
                          line=BODY_LINE_PT, font_name=FONT_BODY)

    signature = content.get("signature") or {}
    _add_attachments(doc, content.get("attachments", []),
                     keep_with_body=bool(signature.get("issuer") or signature.get("date")))
    _add_signature(doc, signature)

    _finalize_western_fonts(doc)
    doc.save(out_path)
    # 嵌入随附的可嵌入字体，使交付件在未装 仿宋_GB2312/楷体_GB2312 的机器上
    # 不掉字；校验不过时保留未嵌入版本，不影响生成结果。
    embed_bundled_fonts(out_path)
    return out_path


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python build_docx.py content.json out.docx")
        sys.exit(1)
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        data = json.load(f)
    # image 块的相对路径按 content.json 所在目录解析
    data.setdefault("_base_dir", str(Path(sys.argv[1]).resolve().parent))
    path = build(data, sys.argv[2])
    print("已生成:", path)
