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


    def test_number_ranges_parentheses_and_wording(self):
        """Fictional sentences mirroring recurring reviewer edits on public-document style."""
        rejected = [
            '单次往返成本约7—10万元。', '运维市场约80—105亿元。', '占比约15—30%。',
            '全国市场规模约1,200—1,500亿元。', '市场空间约为40-50亿元。',
            '混合方案(电池+燃料电池)续航更长。', '系统能量密度(Wh/kg)为350。',
            '增量主要来自于长航时场景。', '参与测量金属毛细管粘度。',
        ]
        accepted = [
            '单次往返成本约7万—10万元。', '运维市场约80亿—105亿元。', '占比约15%—30%。',
            '单场配置8—10台，延误2—3天，约为其1/10—1/15。', '2026—2030年进入专业应用阶段。',
            '混合方案（电池+燃料电池）续航更长。', '执行GB/T 19001—2016标准，型号为V10.0。',
            '增量主要来自长航时场景。',
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
            with self.subTest(skill=skill, warn='exclusivity'):
                self.assertTrue(any(rule.search('国内暂无同规格直接竞品。')
                                    for _, rule in module.WARN_RULES))

    def test_industry_and_business_chapters_reject_investment_stance(self):
        for skill in ('hangye-fenxi', 'zhuying-yewu-fenxi'):
            spec = importlib.util.spec_from_file_location(
                'style_' + skill, ROOT / skill / 'scripts/style_check.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            for text in ['由此，该环节的投资逻辑闭环为需求、技术与政策共振。',
                         '本项目拟围绕这一关键环节布局。']:
                with self.subTest(skill=skill, rejected=text):
                    self.assertTrue(any(rule.search(text) for _, rule in module.RULES))


if __name__ == '__main__':
    unittest.main()
