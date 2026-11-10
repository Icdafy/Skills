"""Regression checks for typography in the saved DOCX (stdlib unittest)."""

import tempfile
import unittest
from pathlib import Path

from docx import Document
from docx.enum.text import WD_LINE_SPACING
from docx.oxml.ns import qn

import create_official_docx as generator


class OfficialFormatTests(unittest.TestCase):
    def assert_font(self, run, font, size):
        fonts = run._r.rPr.rFonts
        for script in ('ascii', 'hAnsi', 'cs', 'eastAsia'):
            self.assertEqual(fonts.get(qn('w:' + script)), font)
        self.assertEqual(run.font.size.pt, size)

    def assert_mixed_font(self, run, east_asia, size):
        """中文用 ``east_asia``，数字、字母、% 等用 Times New Roman。"""
        fonts = run._r.rPr.rFonts
        self.assertEqual(fonts.get(qn('w:eastAsia')), east_asia)
        for script in ('ascii', 'hAnsi', 'cs'):
            self.assertEqual(fonts.get(qn('w:' + script)), generator.WESTERN_FONT)
        self.assertEqual(run.font.size.pt, size)

    def test_parentheses_preserve_text_and_surrounding_format(self):
        doc = Document()
        p = doc.add_paragraph()
        text = '正文ABC（外层(内层123)说明）后文(ABC 2)末尾（未闭合'
        generator.add_formatted_text(p, text, generator.BODY_FONT, 16, True)
        self.assertEqual(p.text, text)
        for run in p.runs:
            if run.text.startswith(('（外层', '(ABC')):
                self.assert_mixed_font(run, generator.KAITI_FONT, 16)
            else:
                self.assertEqual(run._r.rPr.rFonts.get(qn('w:eastAsia')),
                                 generator.BODY_FONT)
                self.assertEqual(run._r.rPr.rFonts.get(qn('w:ascii')),
                                 generator.WESTERN_FONT)
            self.assertTrue(run.bold)

    def test_attachment_names_and_counts(self):
        cases = {
            '附件1.《实施方案（试行）》。': '实施方案（试行）',
            '附件：一、申报表；': '申报表',
            '附件二：测算表！': '测算表',
            '（三）《2026年度计划》？': '2026年度计划',
            '2026年度计划': '2026年度计划',
            '关于《实施方案》的说明：': '关于实施方案的说明',
            '附件2026年度说明': '附件2026年度说明',
        }
        for source, expected in cases.items():
            with self.subTest(source=source):
                self.assertEqual(generator.normalize_attachment_name(source), expected)
        doc = Document()
        generator.configure_styles(doc)
        generator.add_attachments(doc, ['附件1.《实施方案（试行）》。', '《》'])
        self.assertEqual([p.text for p in doc.paragraphs if p.text],
                         ['附件：实施方案（试行）'])
        doc = Document()
        generator.configure_styles(doc)
        generator.add_attachments(doc, ['附件一：申报表；', '附件2.测算表！'])
        items = [p for p in doc.paragraphs if p.text]
        self.assertEqual([p.text for p in items], ['附件：1.申报表', '2.测算表'])
        # 名称起点 = 左空2字 + "附件："3字 + "1."（Times New Roman 实际字宽 0.75 字）。
        name_col = 32 + 48 + generator.text_width_pt('1.')
        self.assertAlmostEqual(items[0].paragraph_format.left_indent.pt, name_col, places=1)
        self.assertAlmostEqual(items[0].paragraph_format.first_line_indent.pt, 32 - name_col, places=1)
        # "2."与"1."左对齐：首行从 32+48 磅起排，回行悬挂在名称首字。
        self.assertAlmostEqual(items[1].paragraph_format.left_indent.pt
                               + items[1].paragraph_format.first_line_indent.pt, 80, places=1)
        for item in items:
            self.assertEqual(item._p.pPr.find(qn('w:autoSpaceDE')).get(qn('w:val')), '0')

    def test_saved_document_spacing_parentheses_and_whole_page_field(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'format.docx'
            generator.build_docx({
                'title': '关于工作安排的通知（试行2026）',
                'issuer_title': '公司文件',
                'subtitle': '业务部门',
                'recipient': '各部门（含子公司）：',
                'body': ['正文（说明ＡＢＣ １２３）结束'],
                'sections': [{'heading': '（1）工作要求', 'level': 4,
                              'paragraphs': [{'table': [['项目', '占比（%）'],
                                                        ['研发投入（2026年）', '12.5%']]}]}],
                'attachments': ['附件1.《工作计划（试行）》；'],
                'issuer': '某某公司（集团）',
                'date': '2026年9月14日',
            }, path)
            doc = Document(path)
            parenthetical_runs = []
            title_styles = (generator.STYLE_TITLE, generator.STYLE_SUBTITLE,
                            generator.STYLE_H1, generator.STYLE_H2,
                            generator.STYLE_H3, generator.STYLE_H4)
            for paragraph in doc.paragraphs:
                expected_spacing = 30 if paragraph.style.name in title_styles else 28
                self.assertEqual(paragraph.paragraph_format.line_spacing.pt,
                                 expected_spacing)
                self.assertEqual(paragraph.paragraph_format.line_spacing_rule,
                                 WD_LINE_SPACING.EXACTLY)
                for run in paragraph.runs:
                    if run.text.startswith(('（', '(')) and not run.text.startswith('（1）'):
                        parenthetical_runs.append(run.text)
                        # 括号字号随所在位置：主标题内二号，其余三号。
                        size = 22 if paragraph.style.name == generator.STYLE_TITLE else 16
                        self.assert_mixed_font(run, generator.KAITI_FONT, size)
                    else:
                        self.assertEqual(run._r.rPr.rFonts.get(qn('w:ascii')),
                                         generator.WESTERN_FONT)
            self.assertEqual(len(parenthetical_runs), 5)
            heading4 = next(p for p in doc.paragraphs if p.text == '（1）工作要求')
            self.assertTrue(all(run.bold for run in heading4.runs))
            # 四级标题序号"（1）"随标题用仿宋_GB2312加粗，不改楷体。
            self.assertEqual(heading4.runs[0].text, '（1）工作要求')
            self.assert_mixed_font(heading4.runs[0], generator.BODY_FONT, 16)
            body = next(p for p in doc.paragraphs if p.text.startswith('正文'))
            self.assertEqual(body.text, '正文（说明ABC 123）结束')  # 全角已转半角
            cells = [p for row in doc.tables[0].rows for c in row.cells
                     for p in c.paragraphs]
            self.assertEqual([p.text for p in cells],
                             ['项目', '占比（%）', '研发投入（2026年）', '12.5%'])
            for index, paragraph in enumerate(cells):
                for run in paragraph.runs:
                    east = (generator.KAITI_FONT if run.text.startswith('（')
                            else generator.BODY_FONT)
                    self.assert_mixed_font(run, east, 10.5)
                    self.assertEqual(bool(run.bold), index < 2)  # 仅表头加粗
            header_row = doc.tables[0].rows[0]._tr.trPr
            self.assertIsNotNone(header_row.find(qn('w:tblHeader')))
            self.assertIsNotNone(header_row.find(qn('w:cantSplit')))
            issuer = next(p for p in doc.paragraphs if p.text == '某某公司（集团）')
            date = next(p for p in doc.paragraphs if p.text == '2026年9月14日')
            self.assertAlmostEqual(issuer.paragraph_format.right_indent.pt, 64, places=1)
            # 日期以署名为准居中：右缩进 = 4字 + (署名宽 − 日期宽) / 2。
            expected = 64 + (generator.text_width_pt('某某公司（集团）')
                             - generator.text_width_pt('2026年9月14日')) / 2
            self.assertAlmostEqual(date.paragraph_format.right_indent.pt, expected, places=1)
            title = next(p for p in doc.paragraphs if p.text.startswith('关于'))
            self.assertEqual(title.runs[0].font.size.pt, 22)
            section = doc.sections[0]
            for footer in (section.footer, section.even_page_footer):
                paragraph = footer.paragraphs[0]
                # 页码写作"- 1 -"：短横线与数字之间各一个半角空格。
                self.assertEqual(paragraph.text, '- 1 -')
                self.assertEqual([run.text for run in paragraph.runs], ['- ', '1', ' -'])
                self.assertEqual(len(paragraph.runs), 3)
                for run in paragraph.runs:
                    self.assert_font(run, generator.SONGTI_FONT, 14)
                instructions = paragraph._p.xpath('.//w:instrText')
                self.assertEqual([node.text.strip() for node in instructions], ['PAGE'])

    def test_thousands_separators_for_quantities_only(self):
        cases = {
            # 数量：整数部分满四位即每三位加半角逗号，小数部分不分节。
            '投资总额不超过1500万元，其中出资 1300 万元': '投资总额不超过1,500万元，其中出资 1,300 万元',
            '资产总额780541.79万元': '资产总额780,541.79万元',
            '贷款共1695笔，本金合计146.62亿元': '贷款共1,695笔，本金合计146.62亿元',
            '建筑面积合计4793平方米，共计2612套': '建筑面积合计4,793平方米，共计2,612套',
            '2026年度计划投资10000万元，带动就业2000人': '2026年度计划投资10,000万元，带动就业2,000人',
            '１２３４５元': '12,345元',
            '3000.00': '3,000.00',
            '12000': '12,000',
            '增长1234.5%': '增长1,234.5%',
            '100000000元': '100,000,000元',
            '已有3,000万元': '已有3,000万元',
            # 标识：年份、日期、文号、电话、代码、标准号等保持原样。
            '2026年4月29日': '2026年4月29日',
            '未城控股字〔2025〕32号': '未城控股字〔2025〕32号',
            '未国资发[2025]1234号': '未国资发[2025]1234号',
            '勤信陕审字【2025】第0097号': '勤信陕审字【2025】第0097号',
            '2023-2025年营收增长': '2023-2025年营收增长',
            '填表时间:2026/4/29': '填表时间:2026/4/29',
            '联系人：张某　联系方式：15300001234': '联系人：张某　联系方式：15300001234',
            '联系电话：029-86001234': '联系电话：029-86001234',
            'ISO9001国际质量体系认证': 'ISO9001国际质量体系认证',
            'GB/T 9704-2012': 'GB/T 9704-2012',
            '证券代码：600519': '证券代码：600519',
            '示例公司（600519）': '示例公司（600519）',
            '某某路2488弄218号': '某某路2488弄218号',
            '第1200次会议': '第1200次会议',
            '关于工作安排的通知（试行2026）': '关于工作安排的通知（试行2026）',
            'v1.0.2 与 12:30': 'v1.0.2 与 12:30',
        }
        for source, expected in cases.items():
            with self.subTest(source=source):
                self.assertEqual(generator.add_thousands_separators(source), expected)

    def test_saved_document_applies_thousands_and_note(self):
        spec = {
            'title': '关于2026年度投资计划的请示',
            'recipient': '集团公司：',
            'body': ['基金总规模为3960万元，我司出资1980万元。',
                     {'table': [['项目', '金额（万元）'], ['资产总额', '705482.17']]}],
            'attachments': ['2026年度投资计划表'],
            'issuer': '某某公司', 'date': '2026年9月14日',
            'note': '联系人：张某　联系方式：15300001234',
        }
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'numbers.docx'
            generator.build_docx(dict(spec), path)
            doc = Document(path)
            texts = [p.text for p in doc.paragraphs]
            self.assertIn('基金总规模为3,960万元，我司出资1,980万元。', texts)
            self.assertIn('关于2026年度投资计划的请示', texts)
            self.assertIn('附件：2026年度投资计划表', texts)
            self.assertEqual(doc.tables[0].rows[1].cells[1].text, '705,482.17')
            # 附注加圆括号，居左空二字，排在成文日期下一行，电话不分节。
            date_index = texts.index('2026年9月14日')
            note = doc.paragraphs[date_index + 1]
            self.assertEqual(note.text, '（联系人：张某　联系方式：15300001234）')
            self.assertAlmostEqual(note.paragraph_format.first_line_indent.pt, 32, places=1)
            # "thousands": false 时原样输出。
            raw = Path(temp) / 'raw.docx'
            generator.build_docx(dict(spec, thousands=False), raw)
            self.assertIn('基金总规模为3960万元，我司出资1980万元。',
                          [p.text for p in Document(raw).paragraphs])


if __name__ == '__main__':
    unittest.main()
