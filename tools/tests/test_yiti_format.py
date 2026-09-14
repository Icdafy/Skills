"""Validate yiti's generated DOCX font slots, spacing, attachments and fields."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from docx import Document
from docx.oxml.ns import qn

REPO = Path(__file__).resolve().parents[2]


class YitiFormatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="yiti-format-", dir=REPO.parent)
        cls.addClassCleanup(cls.tmp.cleanup)
        data = {
            "title": "审议关于示例公司（有限合伙ABC123）的议题",
            "intro": "正文2026（含**加粗ABC12**及(嵌套34)内容）恢复正文56。",
            "page_numbers": True,
            "blocks": [
                {"type": "h1", "text": "一、基本信息"},
                {"type": "h2", "text": "（一）议案"},
                {"type": "h3", "text": "1.依据"},
                {"type": "h4", "text": "（1）条款"},
                {"type": "para", "text": "英文括号(ABC123)后文。未闭合（保留原文"},
                {"type": "table", "caption": "指标（单位元）：",
                 "header": ["名称", "金额"], "rows": [["利润（万元123）", "123.45"]]},
            ],
        }
        cls.docs = []
        for index, names in enumerate((
            ["《通知》。", "关于《议案》的说明；", "表决票（修订版ABC2）。"],
            ["《会议通知》。"], [],
        )):
            spec = Path(cls.tmp.name) / f"input{index}.json"
            out = spec.with_suffix('.docx')
            spec.write_text(json.dumps({**data, "attachments": names}, ensure_ascii=False), encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(REPO / 'yiti-skill/scripts/create_yiti_docx.py'), str(spec), str(out)],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
            )
            if proc.returncode:
                raise AssertionError(proc.stdout + proc.stderr)
            cls.docs.append(Document(out))

    def assert_font(self, run, east_asia, western, size):
        fonts = run._r.rPr.rFonts
        for slot in ('ascii', 'hAnsi', 'cs'):
            self.assertEqual(fonts.get(qn('w:' + slot)), western, run.text)
        self.assertEqual(fonts.get(qn('w:eastAsia')), east_asia, run.text)
        self.assertEqual(run.font.size.pt, size, run.text)
        self.assertEqual(run._r.rPr.find(qn('w:szCs')).get(qn('w:val')), str(size * 2))

    def test_parentheses_across_bold_nested_and_roles(self):
        doc = self.docs[0]
        paragraphs = list(doc.paragraphs)
        paragraphs += [p for t in doc.tables for row in t.rows for c in row.cells for p in c.paragraphs]
        for paragraph in paragraphs:
            # Test every character against the visible paired span, independently
            # of how the generator chose to split the runs.
            text = paragraph.text
            opener = next((i for i, ch in enumerate(text) if ch in '（('), -1)
            closer = max(text.rfind('）'), text.rfind(')'))
            offset = 0
            for run in paragraph.runs:
                if opener >= 0 and closer > opener and offset <= closer and offset + len(run.text) > opener:
                    self.assert_font(run, '楷体_GB2312', '楷体_GB2312', 16)
                offset += len(run.text)
        intro = next(p for p in doc.paragraphs if p.text.startswith('正文2026'))
        self.assertEqual(intro.text, '正文2026（含加粗ABC12及(嵌套34)内容）恢复正文56。')
        self.assertTrue(next(r for r in intro.runs if r.text == '加粗ABC12').bold)
        self.assert_font(intro.runs[-1], '仿宋_GB2312', 'Times New Roman', 16)
        self.assert_font(doc.paragraphs[0].runs[0], '方正小标宋简体', 'Times New Roman', 22)
        self.assertEqual(doc.tables[0].cell(1, 1).paragraphs[0].runs[0].font.size.pt, 10.5)

    def test_fixed_title_and_body_spacing(self):
        heading_texts = {'一、基本信息', '（一）议案', '1.依据', '（1）条款'}
        for index, paragraph in enumerate(self.docs[0].paragraphs):
            spacing = paragraph._p.pPr.find(qn('w:spacing'))
            expected = 600 if index < 2 or paragraph.text in heading_texts else 560
            self.assertEqual(spacing.get(qn('w:lineRule')), 'exact')
            self.assertEqual(spacing.get(qn('w:line')), str(expected), paragraph.text)

    def test_attachment_labels_names_and_count(self):
        expected = [
            ['附件1.通知', '附件2.关于议案的说明', '附件3.表决票（修订版ABC2）'],
            ['附件：会议通知'], [],
        ]
        for doc, names in zip(self.docs, expected):
            self.assertEqual([p.text for p in doc.paragraphs if p.text.startswith('附件')], names)

    def test_complete_footer_font_and_dynamic_field(self):
        section = self.docs[0].sections[0]
        for footer in (section.footer, section.even_page_footer):
            p = footer.paragraphs[0]
            self.assertEqual(p.text, '-1-')
            for run in p.runs:
                self.assert_font(run, '宋体', '宋体', 14)
            self.assertEqual([e.text.strip() for e in p._p.iter(qn('w:instrText'))], ['PAGE'])
            self.assertEqual([e.get(qn('w:fldCharType')) for e in p._p.iter(qn('w:fldChar'))],
                             ['begin', 'separate', 'end'])


if __name__ == '__main__':
    unittest.main()
