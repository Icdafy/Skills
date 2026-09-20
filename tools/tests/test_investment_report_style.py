"""Behavior checks for report language rules; investment logic still needs reading."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ('hangye-fenxi', 'zhuying-yewu-fenxi', 'gongsi-qingkuang')


class ReportStyleTests(unittest.TestCase):
    def test_empty_deferrals_fail_and_concrete_limits_pass(self):
        rejected = [
            '这一优势需要后续进行判断。', '该技术仍需进一步验证。',
            '技术壁垒有待核实。', '后续我们将进一步分析。',
            '优势仍需结合竞争对手的研发进展进一步验证。',
            '公司并非一般供应商，而是行业领导者。',
            '市占率尚需第三方数据佐证。',
        ]
        accepted = [
            '试验已覆盖室内环境，室外场景尚未形成交付记录。',
            '公司预测以合同按期交付及客户验收为基础。',
            '客户认证需要6个月，期间须完成可靠性测试。',
            '技术团队完成样机验证，已交付10套产品。',
            '公司在同一工况下将检测误差从2毫米降至1毫米，满足客户验收要求。',
        ]
        for skill in SKILLS:
            spec = importlib.util.spec_from_file_location(
                'style_' + skill, ROOT / skill / 'scripts/style_check.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            for text in rejected:
                with self.subTest(skill=skill, rejected=text):
                    self.assertTrue(any(rule.search(text) for _, rule in module.RULES))
            for text in accepted:
                with self.subTest(skill=skill, accepted=text):
                    self.assertFalse(any(rule.search(text) for _, rule in module.RULES))


if __name__ == '__main__':
    unittest.main()
