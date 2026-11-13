"""Validate yiti's generated DOCX font slots, spacing, attachments, signature, fields and text checks."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from docx import Document
from docx.oxml.ns import qn

REPO = Path(__file__).resolve().parents[2]
SKILL = REPO / 'yiti-skill'
GENERATOR = SKILL / 'scripts/create_yiti_docx.py'
CHECKER = SKILL / 'scripts/check_yiti_text.py'
EXIT_SPEC = SKILL / 'assets/examples/exit-yiti-spec.json'


def run_generator(spec: Path, out: Path) -> None:
    proc = subprocess.run(
        [sys.executable, str(GENERATOR), str(spec), str(out)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode:
        raise AssertionError(proc.stdout + proc.stderr)


def twips(paragraph, attr):
    ind = paragraph._p.pPr.find(qn('w:ind'))
    value = ind.get(qn('w:' + attr)) if ind is not None else None
    return int(value) if value is not None else 0


class YitiFormatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="yiti-format-", dir=REPO.parent)
        cls.addClassCleanup(cls.tmp.cleanup)
        data = {
            "title": "审议关于示例公司（有限合伙ABC123）的议题",
            "intro": "正文2026（含**加粗ABC12**及(嵌套34)内容）恢复正文56。",
            "blocks": [
                {"type": "h1", "text": "一、基本信息"},
                {"type": "h2", "text": "（一）议案"},
                {"type": "h3", "text": "1.依据"},
                {"type": "h4", "text": "（1）条款（修订）"},
                {"type": "para", "text": "英文括号(ABC123)后文。未闭合（保留原文，全角２０２６％"},
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
            run_generator(spec, out)
            cls.docs.append(Document(out))
        cls.exit_out = Path(cls.tmp.name) / 'exit.docx'
        run_generator(EXIT_SPEC, cls.exit_out)
        cls.exit_doc = Document(cls.exit_out)

    def assert_font(self, run, east_asia, western, size, bold=None):
        fonts = run._r.rPr.rFonts
        for slot in ('ascii', 'hAnsi', 'cs'):
            self.assertEqual(fonts.get(qn('w:' + slot)), western, run.text)
        self.assertEqual(fonts.get(qn('w:eastAsia')), east_asia, run.text)
        self.assertEqual(run.font.size.pt, size, run.text)
        self.assertEqual(run._r.rPr.find(qn('w:szCs')).get(qn('w:val')), str(int(size * 2)))
        if bold is not None:
            self.assertEqual(bool(run.bold), bold, run.text)

    def test_parentheses_kaiti_with_times_new_roman_digits(self):
        doc = self.docs[0]
        # 主标题内括号与标题同为二号，其余表格外括号三号，表格内五号。
        body = [(p, 22 if index == 0 else 16) for index, p in enumerate(doc.paragraphs)]
        body += [(p, 10.5) for t in doc.tables for row in t.rows for c in row.cells for p in c.paragraphs]
        checked = 0
        for paragraph, size in body:
            # Test every run against the visible paired span, independently
            # of how the generator chose to split the runs.
            text = paragraph.text
            opener = next((i for i, ch in enumerate(text) if ch in '（('), -1)
            closer = max(text.rfind('）'), text.rfind(')'))
            if text.startswith('（1）'):
                opener = text.find('（', 3)
            offset = 0
            for run in paragraph.runs:
                if opener >= 0 and closer > opener and offset <= closer and offset + len(run.text) > opener:
                    self.assert_font(run, '楷体_GB2312', 'Times New Roman', size)
                    checked += 1
                offset += len(run.text)
        self.assertGreater(checked, 5)
        intro = next(p for p in doc.paragraphs if p.text.startswith('正文2026'))
        self.assertEqual(intro.text, '正文2026（含加粗ABC12及(嵌套34)内容）恢复正文56。')
        self.assertTrue(next(r for r in intro.runs if r.text == '加粗ABC12').bold)
        self.assert_font(intro.runs[-1], '仿宋_GB2312', 'Times New Roman', 16)
        title_runs = doc.paragraphs[0].runs
        self.assertEqual([r.text for r in title_runs], ['审议关于示例公司', '（有限合伙ABC123）', '的议题'])
        self.assert_font(title_runs[0], '方正小标宋简体', 'Times New Roman', 22)
        self.assert_font(title_runs[1], '楷体_GB2312', 'Times New Roman', 22)
        self.assert_font(title_runs[2], '方正小标宋简体', 'Times New Roman', 22)

    def test_table_text_is_wuhao_fangsong_and_kaiti(self):
        table = self.docs[0].tables[0]
        cell_runs = table.cell(1, 0).paragraphs[0].runs
        self.assertEqual([r.text for r in cell_runs], ['利润', '（万元123）'])
        self.assert_font(cell_runs[0], '仿宋_GB2312', 'Times New Roman', 10.5)
        self.assert_font(cell_runs[1], '楷体_GB2312', 'Times New Roman', 10.5)
        self.assert_font(table.cell(1, 1).paragraphs[0].runs[0], '仿宋_GB2312', 'Times New Roman', 10.5)
        self.assert_font(table.cell(0, 0).paragraphs[0].runs[0], '仿宋_GB2312', 'Times New Roman', 10.5, bold=True)
        tr_pr = table.rows[0]._tr.trPr
        self.assertIsNotNone(tr_pr.find(qn('w:tblHeader')))

    def test_heading_fonts_including_level_four(self):
        paragraphs = {p.text: p for p in self.docs[0].paragraphs}
        self.assert_font(paragraphs['一、基本信息'].runs[0], '黑体', 'Times New Roman', 16, bold=False)
        self.assert_font(paragraphs['（一）议案'].runs[0], '楷体_GB2312', 'Times New Roman', 16, bold=True)
        self.assert_font(paragraphs['1.依据'].runs[0], '仿宋_GB2312', 'Times New Roman', 16, bold=True)
        h4 = paragraphs['（1）条款（修订）']
        # 四级标题序号"（1）"随标题用仿宋_GB2312加粗，不按括号规则改楷体。
        self.assertEqual(h4.runs[0].text, '（1）条款')
        self.assert_font(h4.runs[0], '仿宋_GB2312', 'Times New Roman', 16, bold=True)
        self.assert_font(h4.runs[1], '楷体_GB2312', 'Times New Roman', 16, bold=True)
        for text in ('一、基本信息', '（一）议案', '1.依据', '（1）条款（修订）'):
            self.assertTrue(paragraphs[text].paragraph_format.keep_with_next, text)

    def test_times_new_roman_pass_and_fullwidth_digits(self):
        for doc in (self.docs[0], self.exit_doc):
            for run in doc.element.body.iter(qn('w:r')):
                fonts = run.rPr.rFonts
                for slot in ('ascii', 'hAnsi', 'cs'):
                    self.assertEqual(fonts.get(qn('w:' + slot)), 'Times New Roman')
        para = next(p for p in self.docs[0].paragraphs if p.text.startswith('英文括号'))
        self.assertTrue(para.text.endswith('全角2,026%'))  # 全角转半角后按数量补千位分隔符

    def test_fixed_title_and_body_spacing(self):
        heading_texts = {'一、基本信息', '（一）议案', '1.依据', '（1）条款（修订）'}
        for index, paragraph in enumerate(self.docs[0].paragraphs):
            spacing = paragraph._p.pPr.find(qn('w:spacing'))
            expected = 600 if index < 2 or paragraph.text in heading_texts else 560
            self.assertEqual(spacing.get(qn('w:lineRule')), 'exact')
            self.assertEqual(spacing.get(qn('w:line')), str(expected), paragraph.text)

    def test_attachment_labels_names_and_alignment(self):
        expected = [
            ['附件：1.通知', '2.关于议案的说明', '3.表决票（修订版ABC2）'],
            ['附件：会议通知'], [],
        ]
        for doc, names in zip(self.docs, expected):
            texts = [p.text for p in doc.paragraphs]
            start = next((i for i, t in enumerate(texts) if t.startswith('附件')), len(texts))
            self.assertEqual(texts[start:], names)
            if names:
                self.assertEqual(texts[start - 1], '')  # 正文下空一行
        multi = self.docs[0].paragraphs[-3:]
        # "附件：" starts at 2 chars (640), occupies 3 chars (960); "1." is 12 pt (240) in Times New Roman.
        self.assertEqual((twips(multi[0], 'left'), twips(multi[0], 'hanging')), (1840, 1200))
        for paragraph in multi[1:]:
            self.assertEqual((twips(paragraph, 'left'), twips(paragraph, 'hanging')), (1840, 240))
        single = self.docs[1].paragraphs[-1]
        self.assertEqual((twips(single, 'left'), twips(single, 'hanging')), (1600, 960))
        for paragraph in multi:
            self.assert_font(paragraph.runs[0], '仿宋_GB2312', 'Times New Roman', 16)

    def test_complete_footer_font_and_dynamic_field(self):
        for doc in (self.docs[0], self.exit_doc):
            self.assertTrue(doc.settings.odd_and_even_pages_header_footer)
            section = doc.sections[0]
            for footer, align in ((section.footer, 'right'), (section.even_page_footer, 'left')):
                p = footer.paragraphs[0]
                self.assertEqual(p.text, '- 1 -')
                self.assertEqual(p._p.pPr.find(qn('w:jc')).get(qn('w:val')), align)
                for run in p.runs:
                    self.assert_font(run, '宋体', '宋体', 14)
                self.assertEqual([e.text.strip() for e in p._p.iter(qn('w:instrText'))], ['PAGE'])
                self.assertEqual([e.get(qn('w:fldCharType')) for e in p._p.iter(qn('w:fldChar'))],
                                 ['begin', 'separate', 'end'])

    def test_exit_kind_structure_signature_and_appendix(self):
        texts = [p.text for p in self.exit_doc.paragraphs]
        self.assertEqual(texts[:4], ['审议关于XX智能科技有限公司', '投资项目退出的议题', '提交子公司：投管公司', ''])
        self.assertNotIn('投委会：', texts)
        self.assertTrue(texts[4].startswith('2024年X月'))
        self.assertTrue(texts[5].endswith('现提请投委会审议。具体如下：'))
        attach = texts.index('附件：XX智能科技有限公司项目退出方案')
        self.assertEqual(texts[attach + 1:attach + 5], ['', '', 'XX投资管理有限公司', '2026年9月X日'])
        issuer, date = self.exit_doc.paragraphs[attach + 3], self.exit_doc.paragraphs[attach + 4]
        self.assertEqual(twips(issuer, 'right'), 1280)  # 署名右空四字
        self.assertGreater(twips(date, 'right'), twips(issuer, 'right'))  # 日期居中于署名下
        for index in range(attach - 2, attach + 4):  # 正文末段、附件说明与落款同页
            self.assertTrue(self.exit_doc.paragraphs[index].paragraph_format.keep_with_next, texts[index])
        label = self.exit_doc.paragraphs[attach + 5]
        self.assertEqual(label.text, '附件：')
        self.assertTrue(label.paragraph_format.page_break_before)
        self.assertEqual(texts[attach + 6:attach + 8], ['XX智能科技有限公司项目', '退出方案'])
        self.assert_font(self.exit_doc.paragraphs[attach + 6].runs[0], '方正小标宋简体', 'Times New Roman', 22)
        table = self.exit_doc.tables[0]
        widths = [int(g.get(qn('w:w'))) for g in table._tbl.tblGrid.findall(qn('w:gridCol'))]
        self.assertLess(widths[0], widths[1])  # 序号窄、事项宽
        self.assertLessEqual(abs(sum(widths) - 8844), 4)  # 铺满版心不溢出


class YitiTextCheckTests(unittest.TestCase):
    def run_checker(self, text: str, suffix='.md'):
        with tempfile.TemporaryDirectory(dir=REPO.parent) as tmp:
            path = Path(tmp) / f'draft{suffix}'
            path.write_text(text, encoding='utf-8')
            return subprocess.run([sys.executable, str(CHECKER), str(path)], capture_output=True,
                                  text=True, encoding='utf-8', errors='replace')

    def test_deferral_endings_and_contrast_patterns_are_hard_hits(self):
        for sentence in ('公司经营承压，具体影响需要后续进行判断。',
                         '相关风险有待进一步研判。',
                         '后续需持续关注回款情况。',
                         '退出时机视情况而定。',
                         '本次退出不是被动止损，而是主动防范风险。',
                         '采用现金回购而非股权置换。',
                         '值得注意的是，公司现金流偏紧。'):
            with self.subTest(sentence=sentence):
                proc = self.run_checker(sentence)
                self.assertEqual(proc.returncode, 1, proc.stdout)
                self.assertIn('[硬规则]', proc.stdout)

    def test_rule_statements_and_final_style_pass(self):
        text = ('最终价格以审计、评估结论及国资备案结果为准。\n'
                '收入转化和现金流贡献尚需较长时间。\n'
                '判断公司全年业绩目标基本已无实现可能，届时将大概率触发平价回购条款。\n')
        proc = self.run_checker(text)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertNotIn('[警告]', proc.stdout)

    def test_tone_warnings(self):
        proc = self.run_checker('项目必然失败，公司或许会继续亏损。')
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn('语气偏激进', proc.stdout)
        self.assertIn('语气偏保守', proc.stdout)

    def test_numbers_without_thousands_separators_are_hard_hits(self):
        for sentence in ('当期实缴出资总额1980万元。',
                         '本期管理费拟计提141583.56元。',
                         '| 净利润（万元） | 245766.75 |'):
            with self.subTest(sentence=sentence):
                proc = self.run_checker(sentence)
                self.assertEqual(proc.returncode, 1, proc.stdout)
                self.assertIn('千位分隔符', proc.stdout)
        grouped = ('该基金于2026年4月14日完成备案，2026年度计费周期共计261天，当期实缴出资总额1,980万元，'
                   '本期管理费拟计提141,583.56元。\n'
                   '依据X国资发〔2025〕8号文，2026年1—6月净利润为245,766.75元。\n')
        proc = self.run_checker(grouped)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertNotIn('千位分隔符', proc.stdout)

    def test_bundled_exit_example_is_clean(self):
        proc = subprocess.run([sys.executable, str(CHECKER), str(EXIT_SPEC)], capture_output=True,
                              text=True, encoding='utf-8', errors='replace')
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn('硬规则命中 0 处，警告 0 处', proc.stdout)



class YitiExpressionAndLogicTest(unittest.TestCase):
    """1.1.0：千位分隔符自动补齐、口语与机器腔拦截、逻辑结构复核。"""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(SKILL / 'scripts'))
        import check_yiti_text
        import create_yiti_docx
        cls.checker = check_yiti_text
        cls.generator = create_yiti_docx

    def test_thousands_added_to_quantities_only(self):
        group = self.generator.add_thousands_separators
        self.assertEqual(group('认缴总规模3960万元，首期实缴1980万元'), '认缴总规模3,960万元，首期实缴1,980万元')
        self.assertEqual(group('计提141583.56元'), '计提141,583.56元')
        self.assertEqual(group('净利润-6661.04万元'), '净利润-6,661.04万元')
        for kept in ('2026年4月23日17:00前', 'X国资发〔2025〕18号', '登记编号为P1099999',
                     '电话：029-12345678', '2027—2028年', '注册资本123.4567万元', '已分节1,980万元'):
            self.assertEqual(group(kept), kept)

    def test_generator_normalizes_spec_and_can_be_switched_off(self):
        spec = {'title': '关于测试的议题', 'intro': '金额12345.6万元，具体如下：',
                'blocks': [{'type': 'table', 'header': ['事项', '编号', '金额（元）'],
                            'rows': [['合计', '20261113', '27408']]},
                           {'type': 'para', 'text': '原样1980万元', 'thousands': False}]}
        out = self.generator.normalize_spec_numbers(spec)
        self.assertEqual(out['intro'], '金额12,345.6万元，具体如下：')
        self.assertEqual(out['blocks'][0]['rows'][0], ['合计', '20261113', '27,408'])
        self.assertEqual(out['blocks'][1]['text'], '原样1980万元')
        self.assertEqual(spec['intro'], '金额12345.6万元，具体如下：')  # 不改调用方的对象
        self.assertIs(self.generator.normalize_spec_numbers(dict(spec, thousands=False))['intro'], spec['intro'])

    def test_colloquial_and_machine_tone_are_hard_hits(self):
        scan = self.checker.scan
        for text in ('我们打算跟XX公司合作。', '这块业务先看一下。', '说白了就是价格低。',
                     '让我们来看基金概况。', '该事项至关重要。', '以下是具体方案。'):
            hard, _ = scan([('t', text)])
            self.assertTrue(hard, text)
        for text in ('我司拟联合XX公司成立有限合伙企业（SPV）对XX科技进行投资，具体情况如下：',
                     '经核查，本次两项议案均已履行XX证券内部董事会审议程序，未发现存在损害我司参股股东合法权益的情形。',
                     '随着公司投资业务持续推进，尽职调查等工作对信息获取的及时性提出了更高要求。',
                     '合伙人会议为合伙企业的最高权力机构。'):
            hard, warn = scan([('t', text)])
            self.assertEqual((hard, warn), ([], []), text)

    def test_puffery_and_dash_are_warnings(self):
        _, warn = self.checker.scan([('t', '该终端拥有海量数据，整体性价比最佳——建议选用。')])
        self.assertEqual(len(warn), 3)
        _, warn = self.checker.scan([('t', '对照《私募投资基金备案指引第3号——私募投资基金生前遗嘱》第四条。')])
        self.assertEqual(warn, [])

    def test_markdown_in_spec_is_a_hard_hit(self):
        hard, _ = self.checker.scan_spec({'intro': '具体如下：', 'blocks': [{'type': 'para', 'text': '- 一是成本低。'}]})
        self.assertTrue(any('Markdown' in line for line in hard))

    def test_structure_warnings(self):
        spec = {
            'recipient': '投委会：',
            'intro': 'XX有限公司（以下简称“XX公司”）拟召开会议。',
            'blocks': [
                {'type': 'h1', 'text': '一、基本情况'},
                {'type': 'para', 'text': '本次投资主要面临两方面风险：一是经营层面，公司拟拓展新业务领域，可能存在盈利不及预期的风险。'},
                {'type': 'h1', 'text': '三、请示事项'},
                {'type': 'para', 'text': '综上，拟申请投资金额不超过1,600万元。'},
                {'type': 'para', 'text': '现提请专题会审议。'},
            ],
        }
        _, warn = self.checker.scan_spec(spec)
        joined = '\n'.join(warn)
        for needle in ('导语末句', '审议机构前后不一致', '一级标题序号不连续', "有'一是'而无'二是'",
                       '1,600万元', '简称『XX公司』'):
            self.assertIn(needle, joined)

    def test_bundled_examples_pass_cleanly(self):
        for name in ('exit-yiti-spec.json', 'invest-yiti-spec.json'):
            data = json.loads((SKILL / 'assets/examples' / name).read_text(encoding='utf-8'))
            self.assertEqual(self.checker.scan_spec(data), ([], []), name)
            self.assertEqual(self.generator.normalize_spec_numbers(data), data, name)  # 示例本身已写对

if __name__ == '__main__':
    unittest.main()
