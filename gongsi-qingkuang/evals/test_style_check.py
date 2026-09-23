"""Run with Python's unittest. Fixtures are fictional and contain no client data."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'style_check.py'


class StyleCheckBehavior(unittest.TestCase):
    def scan(self, content):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / ('report.json' if isinstance(content, dict) else 'report.txt')
            path.write_text(json.dumps(content, ensure_ascii=False) if isinstance(content, dict) else content,
                            encoding='utf-8')
            return subprocess.run([sys.executable, str(SCRIPT), str(path)],
                                  capture_output=True, encoding='utf-8')

    def test_internal_report_and_real_model_are_allowed(self):
        result = self.scan('公司拟融资1200万元，投前估值8800万元。\n'
                           '相关协议已约定知识产权归公司所有。\n'
                           '设备型号为V10.0，按GB/T 19001—2016执行。\n'
                           '供应商核查结果已归档，应收账款核查结果亦已归档。')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_delegated_analysis_is_flagged(self):
        for text in ['应将合同、验收及收款分别核实。', '订单应分别考察。',
                     '建议投资方关注回款。', '后续仍需核查资金流向。']:
            with self.subTest(text=text):
                result = self.scan(text)
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn('外部指导口吻', result.stdout)

    def test_deferred_analysis_is_flagged(self):
        for text in ['需要后续进行判断。', '后续我们将核查相关协议。',
                     '优势的持续性有待验证。', '仍需进一步分析。']:
            with self.subTest(text=text):
                self.assertEqual(self.scan(text).returncode, 1)

    def test_json_tables_and_notes_are_scanned(self):
        data = {'blocks': [{'type': 'table', 'header': ['材料所列轮次'], 'rows': [['回复V10.0']]},
                           {'type': 'tnote', 'text': '公司在尽调回复中将某人列为负责人。'}]}
        result = self.scan(data)
        self.assertEqual(result.returncode, 1)
        self.assertIn('table.header', result.stdout)
        self.assertIn('table.cell', result.stdout)
        self.assertIn('blocks[tnote]', result.stdout)

    def test_repeated_attribution_is_warning_not_evidence_deletion(self):
        result = self.scan('公司表示预计扩产。\n\n公司解释订单尚未签订。\n公司介绍产品正在试制。')
        self.assertEqual(result.returncode, 0)
        self.assertIn('[WARN]', result.stdout)

    def test_number_range_and_time_status(self):
        result = self.scan('公司预计年收入为300—350万元。')
        self.assertEqual(result.returncode, 1)
        self.assertIn('数值范围', result.stdout)
        self.assertEqual(self.scan('公司预计年收入为300万—350万元。').returncode, 0)
        warn = self.scan('创立公司前为某企业联合创始人。')
        self.assertEqual(warn.returncode, 0)
        self.assertIn('时点不明', warn.stdout)
        self.assertNotIn('时点不明', self.scan('公司目前为小批量交付阶段。').stdout)

    def test_existing_rules_and_editorial_notes_remain_detectable(self):
        for text in ['标的公司具有优势。', '公司不仅提供产品，而且提供服务。',
                     '【待补充】财务数据。', '核心结论：业绩改善。', '（这部分重新写吧）']:
            with self.subTest(text=text):
                self.assertEqual(self.scan(text).returncode, 1)


if __name__ == '__main__':
    unittest.main()
