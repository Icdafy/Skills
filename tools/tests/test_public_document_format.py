"""Saved-document regression tests for the three investment-report skills."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from docx import Document
from docx.enum.text import WD_LINE_SPACING, WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt

REPO = Path(__file__).resolve().parents[2]
SKILLS = ('gongsi-qingkuang', 'hangye-fenxi', 'zhuying-yewu-fenxi')


class PublicDocumentFormatTests(unittest.TestCase):
    def assert_font(self, run, font, size):
        for attribute in ('ascii', 'hAnsi', 'cs'):
            self.assertEqual(run._r.rPr.rFonts.get(qn('w:' + attribute)), 'Times New Roman')
        self.assertEqual(run._r.rPr.rFonts.get(qn('w:eastAsia')), font)
        self.assertEqual(run.font.size.pt, size)

    def test_final_western_pass_preserves_chinese_and_field_format(self):
        spec = importlib.util.spec_from_file_location(
            'report_builder', REPO / SKILLS[0] / 'scripts/build_docx.py')
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        doc = Document()
        places = [doc.add_paragraph(), doc.sections[0].header.paragraphs[0],
                  doc.add_table(rows=1, cols=1).cell(0, 0).add_table(rows=1, cols=1).cell(0, 0).paragraphs[0]]
        footer = doc.sections[0].footer.paragraphs[0]
        for paragraph in places + [footer]:
            run = paragraph.add_run('中文123%（测试）-')
            builder._set_run_font(run, size=14, bold=True, font_name='宋体', western_font='Calibri')
            run._r.rPr.rFonts.set(qn('w:asciiTheme'), 'minorHAnsi')
            run._r.rPr.rFonts.set(qn('w:hAnsiTheme'), 'minorHAnsi')
        doc.styles['Normal'].font.name = 'Calibri'
        doc.styles['Normal'].font.size = Pt(16)
        doc.styles['Normal'].element.rPr.rFonts.set(qn('w:eastAsia'), '仿宋_GB2312')
        builder._finalize_western_fonts(doc)
        # 页脚不参与最后的 Times New Roman 统一（与 yiti-skill 一致）。
        self.assertEqual(footer.runs[0]._r.rPr.rFonts.get(qn('w:ascii')), 'Calibri')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'final.docx'
            doc.save(path)
            saved = Document(path)
            for part in saved.part.package.parts:
                if not str(part.partname).startswith(('/word/document', '/word/header', '/word/styles')):
                    continue
                if not hasattr(part, 'element'):
                    continue
                for fonts in part.element.iter(qn('w:rFonts')):
                    for slot in ('ascii', 'hAnsi', 'cs'):
                        self.assertEqual(fonts.get(qn('w:' + slot)), 'Times New Roman')
                    self.assertIsNone(fonts.get(qn('w:asciiTheme')))
                    self.assertIsNone(fonts.get(qn('w:hAnsiTheme')))
            for paragraph in places:
                self.assertEqual(paragraph.text, '中文123%（测试）-')
                self.assert_font(paragraph.runs[0], '宋体', 14)
                self.assertTrue(paragraph.runs[0].bold)

    def test_saved_format_in_every_report_skill(self):
        content = {
            'cover': {'title_lines': ['立项报告（试行2026）']},
            'blocks': [
                {'type': 'h1', 'text': '一、公司情况'},
                {'type': 'h2', 'text': '（一）基本信息'},
                {'type': 'h3', 'text': '1.经营情况'},
                {'type': 'h4', 'text': '（1）业务说明（量产2026）'},
                {'type': 'p', 'text': '正文ABC（口径(123)说明）结束５０％', 'bold': True},
                {'type': 'bullet', 'items': ['经营资质（有效期2026）']},
                {'type': 'tnote', 'text': '单位（万元）'},
                {'type': 'table', 'header': ['项目（2026）'], 'rows': [['数值(ABC 123%)']]},
            ],
            'attachments': ['附件一：《实施方案（试行）》；', '附件2.测算表！'],
            'signature': {'issuer': '某某投资管理有限公司', 'date': '2026年9月1日'},
        }
        for skill in SKILLS:
            with self.subTest(skill=skill), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp)
                source, output = path / 'input.json', path / 'output.docx'
                source.write_text(json.dumps(content, ensure_ascii=False), encoding='utf-8')
                result = subprocess.run([sys.executable, '-X', 'utf8',
                                         str(REPO / skill / 'scripts/build_docx.py'),
                                         str(source), str(output)], capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', errors='replace'))
                doc = Document(output)
                table_paragraphs = [p for table in doc.tables for row in table.rows
                                    for cell in row.cells for p in cell.paragraphs]
                paragraphs = doc.paragraphs + table_paragraphs
                expected_spans = {'（试行2026）', '（一）', '（1）', '（口径(123)说明）',
                                  '（有效期2026）', '（万元）', '（2026）', '(ABC 123%)',
                                  '（试行）', '（量产2026）'}
                found = set()
                cover = next(p for p in doc.paragraphs if p.text.startswith('立项报告'))
                tnote = next(p for p in doc.paragraphs if p.text.startswith('单位'))
                for paragraph in paragraphs:
                    for run in paragraph.runs:
                        if run.text.startswith(('（', '(')):
                            found.add(run.text)
                            font = '仿宋_GB2312' if run.text == '（1）' else '楷体_GB2312'
                            # 括注字号随所在位置：封面标题二号、表格与表注五号、其余三号。
                            if paragraph is cover or paragraph._p is cover._p:
                                size = 22
                            elif paragraph in table_paragraphs or paragraph._p is tnote._p:
                                size = 10.5
                            else:
                                size = 16
                            self.assert_font(run, font, size)
                self.assertEqual(found, expected_spans)
                h4 = next(p for p in doc.paragraphs if p.text.startswith('（1）'))
                self.assertTrue(all(run.bold for run in h4.runs))
                self.assert_font(h4.runs[1], '仿宋_GB2312', 16)
                for row in doc.tables[0].rows:
                    self.assertIsNotNone(row._tr.trPr.find(qn('w:cantSplit')))
                    for cell in row.cells:
                        # 表头不加浅蓝底，全表无底纹。
                        self.assertIsNone(cell._tc.tcPr.find(qn('w:shd')))
                        for paragraph in cell.paragraphs:
                            self.assertEqual(paragraph.paragraph_format.line_spacing_rule,
                                             WD_LINE_SPACING.SINGLE)
                            for run in paragraph.runs:
                                if run.text:
                                    self.assertEqual(run.font.size.pt, 10.5)
                self.assertTrue(all(run.bold for run in doc.tables[0].rows[0].cells[0].paragraphs[0].runs
                                    if run.text))
                body = next(p for p in doc.paragraphs if p.text.startswith('正文ABC'))
                self.assertTrue(body.text.endswith('结束50%'))  # 全角数字和％已转半角
                self.assertTrue(all(run.bold for run in body.runs))
                self.assertEqual(body.runs[0]._r.rPr.rFonts.get(qn('w:ascii')), 'Times New Roman')
                self.assertEqual(body.runs[0]._r.rPr.rFonts.get(qn('w:eastAsia')), '仿宋_GB2312')
                headings = ('一、', '（一）', '1.', '（1）', '立项报告')
                for paragraph in doc.paragraphs:
                    if not paragraph.text or paragraph.text.startswith('单位'):
                        continue
                    spacing = 30 if paragraph.text.startswith(headings) else 28
                    self.assertEqual(paragraph.paragraph_format.line_spacing_rule, WD_LINE_SPACING.EXACTLY)
                    self.assertEqual(paragraph.paragraph_format.line_spacing.pt, spacing)
                    if paragraph.text.startswith(headings[:4]):
                        self.assertEqual(paragraph.paragraph_format.space_before.pt, 0)
                        self.assertEqual(paragraph.paragraph_format.space_after.pt, 0)
                texts = [p.text for p in doc.paragraphs]
                first = texts.index('附件：1.实施方案（试行）')
                self.assertEqual(texts[first - 1], '')  # 附件说明前空一行
                self.assertEqual(texts[first + 1], '2.测算表')
                # "2."与"1."对齐：第二条首行起点 = 第一条首行起点 + "附件："宽度。
                item1, item2 = doc.paragraphs[first], doc.paragraphs[first + 1]
                start1 = item1.paragraph_format.left_indent.pt + item1.paragraph_format.first_line_indent.pt
                start2 = item2.paragraph_format.left_indent.pt + item2.paragraph_format.first_line_indent.pt
                self.assertAlmostEqual(start1, 32, places=1)
                self.assertAlmostEqual(start2, 32 + 48, places=1)
                self.assertEqual(texts[first + 2:first + 4], ['', ''])  # 落款前空两行
                issuer = doc.paragraphs[first + 4]
                date = doc.paragraphs[first + 5]
                self.assertEqual((issuer.text, date.text), ('某某投资管理有限公司', '2026年9月1日'))
                self.assertEqual(issuer.alignment, WD_ALIGN_PARAGRAPH.RIGHT)
                self.assertAlmostEqual(issuer.paragraph_format.right_indent.pt, 64, places=1)
                self.assertGreater(date.paragraph_format.right_indent.pt, 64)
                self.assertTrue(doc.settings.odd_and_even_pages_header_footer)
                self.assertNotEqual(doc.sections[0].footer.part.partname,
                                    doc.sections[0].even_page_footer.part.partname)
                for footer, align in ((doc.sections[0].footer, WD_ALIGN_PARAGRAPH.RIGHT),
                                      (doc.sections[0].even_page_footer, WD_ALIGN_PARAGRAPH.LEFT)):
                    paragraph = footer.paragraphs[0]
                    self.assertEqual(paragraph.alignment, align)
                    self.assertEqual(paragraph.text, '-1-')
                    self.assertEqual(len(paragraph.runs), 3)
                    for run in paragraph.runs:
                        # 完整 -1- 四个字体槽均为宋体、四号。
                        for slot in ('ascii', 'hAnsi', 'cs', 'eastAsia'):
                            self.assertEqual(run._r.rPr.rFonts.get(qn('w:' + slot)), '宋体')
                        self.assertEqual(run.font.size.pt, 14)
                    self.assertEqual([n.text for n in paragraph._p.xpath('.//w:instrText')], ['PAGE'])

    def test_text_helpers_and_single_attachment(self):
        spec = importlib.util.spec_from_file_location('helpers', REPO / SKILLS[0] / 'scripts/docx_format_helpers.py')
        helpers = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helpers)
        self.assertEqual(helpers.attachment_lines(['附件1.《工作方案（试行）》。', '《》']),
                         ['附件：工作方案（试行）'])
        self.assertEqual(helpers.normalize_attachment_name('2026年度计划'), '2026年度计划')
        self.assertEqual(helpers.normalize_attachment_name('附件2026年度说明'), '附件2026年度说明')
        self.assertEqual(helpers.parenthesized_spans('正文（未闭合'), [])
        self.assertEqual(helpers.parenthesized_spans('a（b(c)d）e'), [(1, 8)])


if __name__ == '__main__':
    unittest.main()
