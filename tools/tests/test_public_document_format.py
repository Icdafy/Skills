"""Saved-document regression tests for the three investment-report skills."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from docx import Document
from docx.enum.text import WD_LINE_SPACING
from docx.oxml.ns import qn

REPO = Path(__file__).resolve().parents[2]
SKILLS = ('gongsi-qingkuang', 'hangye-fenxi', 'zhuying-yewu-fenxi')


class PublicDocumentFormatTests(unittest.TestCase):
    def assert_font(self, run, font, size):
        for attribute in ('ascii', 'hAnsi', 'cs', 'eastAsia'):
            self.assertEqual(run._r.rPr.rFonts.get(qn('w:' + attribute)), font)
        self.assertEqual(run.font.size.pt, size)

    def test_saved_format_in_every_report_skill(self):
        content = {
            'cover': {'title_lines': ['立项报告（试行2026）']},
            'blocks': [
                {'type': 'h1', 'text': '一、公司情况'},
                {'type': 'h2', 'text': '（一）基本信息'},
                {'type': 'h3', 'text': '1.经营情况'},
                {'type': 'h4', 'text': '（1）业务说明'},
                {'type': 'p', 'text': '正文ABC（口径(123)说明）结束', 'bold': True},
                {'type': 'bullet', 'items': ['经营资质（有效期2026）']},
                {'type': 'tnote', 'text': '单位（万元）'},
                {'type': 'table', 'header': ['项目（2026）'], 'rows': [['数值(ABC 123)']]},
            ],
            'attachments': ['附件一：《实施方案（试行）》；', '附件2.测算表！'],
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
                paragraphs = doc.paragraphs + [p for table in doc.tables for row in table.rows
                                               for cell in row.cells for p in cell.paragraphs]
                expected_spans = {'（试行2026）', '（一）', '（1）', '（口径(123)说明）',
                                  '（有效期2026）', '（万元）', '（2026）', '(ABC 123)', '（试行）'}
                found = set()
                for paragraph in paragraphs:
                    for run in paragraph.runs:
                        if run.text.startswith(('（', '(')):
                            found.add(run.text)
                            self.assert_font(run, '楷体_GB2312', 16)
                self.assertEqual(found, expected_spans)
                body = next(p for p in doc.paragraphs if p.text.startswith('正文ABC'))
                self.assertTrue(all(run.bold for run in body.runs))
                self.assertEqual(body.runs[0]._r.rPr.rFonts.get(qn('w:ascii')), 'Times New Roman')
                self.assertEqual(body.runs[0]._r.rPr.rFonts.get(qn('w:eastAsia')), '仿宋_GB2312')
                for paragraph in doc.paragraphs:
                    if not paragraph.text or paragraph.text.startswith('单位'):
                        continue
                    spacing = 30 if paragraph.text.startswith('立项报告') else 28
                    self.assertEqual(paragraph.paragraph_format.line_spacing_rule, WD_LINE_SPACING.EXACTLY)
                    self.assertEqual(paragraph.paragraph_format.line_spacing.pt, spacing)
                self.assertEqual([p.text for p in doc.paragraphs if p.text.startswith('附件')],
                                 ['附件1.实施方案（试行）', '附件2.测算表'])
                for footer in (doc.sections[0].footer, doc.sections[0].even_page_footer):
                    paragraph = footer.paragraphs[0]
                    self.assertEqual(paragraph.text, '-1-')
                    self.assertEqual(len(paragraph.runs), 3)
                    for run in paragraph.runs:
                        self.assert_font(run, '宋体', 14)
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
