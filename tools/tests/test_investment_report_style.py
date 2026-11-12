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
            '后续更换供应商通常需要重新开展接口匹配、地面试验和飞行验证。',
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

    def test_meta_advice_and_internal_source_traces(self):
        rejected = ['技术可行性、产品定型和常态化作业应分别评价。', '不能据此推导出全国性供给网络已经形成。',
                    '数据来源：业务回复Q5.1。', '按V10.0订单口径列示。', '详版列示单价6万元。',
                    '依据《某公司业务尽调问题及回复》复算。']
        accepted = ['动力系统价格仍为现有方案的4倍以上。', '2025年第一季度收入为10万元。', '型号为V10.0，按GB/T 19001—2016执行。']
        for skill in SKILLS:
            spec = importlib.util.spec_from_file_location('style_' + skill, ROOT / skill / 'scripts/style_check.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            for text in rejected:
                with self.subTest(skill=skill, rejected=text):
                    self.assertTrue(any(rule.search(text) for _, rule in module.RULES))
            for text in accepted:
                with self.subTest(skill=skill, accepted=text):
                    self.assertFalse(any(rule.search(text) for _, rule in module.RULES))

    def test_numbers_use_thousands_separators(self):
        """Quantities of four or more integer digits take a half-width comma every three digits."""
        rejected = ['2025年度实现营业收入2350万元。', '投前估值12000万元。', '净利润-1234.56万元。',
                    '年产能12000台。', '员工1200人。', '市场规模约1000亿—1500亿元。']
        accepted = ['2025年度实现营业收入2,350万元。', '投前估值12,000万元，持股1,234,567股。', '净利润-1,234.56万元。',
                    '截至2026年9月28日，公司员工128人。', '2026—2030年进入专业应用阶段。', '2023、2024和2025年收入持续增长。',
                    '依据控股字〔2026〕12号文，执行GB/T 19001—2016标准。', '股票代码：688001，证券简称为示例科技。',
                    '2021-01-05完成工商变更。', '毛利率为35.1234%。']
        for skill in SKILLS:
            spec = importlib.util.spec_from_file_location('style_' + skill, ROOT / skill / 'scripts/style_check.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            for text in rejected:
                with self.subTest(skill=skill, rejected=text):
                    self.assertTrue(any(rule.search(text) for _, rule in module.RULES))
            for text in accepted:
                with self.subTest(skill=skill, accepted=text):
                    self.assertFalse(any(rule.search(text) for _, rule in module.RULES))

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

    def test_spoken_and_machine_phrasing_fail_and_formal_phrasing_passes(self):
        """Fictional sentences; formal ones mirror the register of approved reports."""
        rejected = [
            '好的，以下是为您撰写的行业分析。', '希望以上内容对您有帮助。',
            '值得注意的是，公司收入增长较快。', '综上所述，公司具备竞争优势。',
            '说白了，公司现在主要靠贸易赚钱。', '这项技术很牛，别人没法做。',
            '行业前景广阔，公司潜力巨大。', '公司通过平台赋能下游客户。',
            '笔者认为该赛道值得关注。', '公司产品卖得不错。',
        ]
        accepted = [
            '公司以储能变流器为核心产品，向系统集成延伸。',
            '行业及市场方面，下游需求持续释放，政策支持方向明确。',
            '所称长距离作业，指单程50公里以上需返航的任务。',
            '据公司介绍，A型号已定型并对外销售，B型号处于研发阶段。',
            '但现有合同仍以测试及小批量交付为主，批量销售尚未形成，后续转化取决于示范项目采购进度。',
            '2024年《人工智能赋能新型工业化行动方案》发布，对应公司所处环节。',
            '公司称“卖得不错”，2025年销量为120台。',
            '总体判断，在需求释放和技术路线收敛的共同作用下，该类装备将由试用验证走向专业应用。',
        ]
        for skill in SKILLS:
            module = self.load(skill)
            for text in rejected:
                with self.subTest(skill=skill, rejected=text):
                    self.assertTrue(any(rule.search(text) for _, rule in module.RULES))
            for text in accepted:
                with self.subTest(skill=skill, accepted=text):
                    self.assertFalse(any(rule.search(text) for _, rule in module.RULES))

    def test_structure_warnings_for_openers_degree_words_and_lead_counts(self):
        for skill in SKILLS:
            module = self.load(skill)
            pairs = [
                ('L1', '随着行业的不断发展，市场需求持续释放。'),
                ('L2', '此外，公司还布局了海外市场。'),
                ('L3', '公司收入大幅增长。'),
                ('L4', '以下从市场需求、技术路线和政策支持四方面梳理行业现状。'),
                ('L5', '公司2025年营业收入3,120.36万元，同比大幅增长32.74%。'),
                ('L6', '以下从市场需求、技术路线、商业化进程和政策支持四方面梳理行业现状。'),
            ]
            hits = {}
            for loc, message in module.expression_warnings(pairs):
                hits.setdefault(loc, []).append(message)
            with self.subTest(skill=skill):
                self.assertIn('L1', hits)
                self.assertIn('L2', hits)
                self.assertTrue(any('程度词' in m for m in hits['L3']))
                self.assertTrue(any('四方面' in m for m in hits['L4']))
                self.assertNotIn('L5', hits)
                self.assertNotIn('L6', hits)
            content = {'blocks': [
                {'type': 'h2', 'text': '（一）行业发展现状'},
                {'type': 'p', 'text': '行业处于过渡阶段。以下从需求、路线和政策三方面梳理。'},
                {'type': 'h3', 'text': '1.需求'}, {'type': 'p', 'text': '需求持续释放。'},
                {'type': 'h3', 'text': '2.路线'},
                {'type': 'table', 'header': ['路线', '续航'], 'rows': [['A', '26']]},
                {'type': 'h2', 'text': '（二）产业链分析'},
            ]}
            messages = [m for _, m in module.expression_warnings([], content)]
            with self.subTest(skill=skill, structure=True):
                self.assertTrue(any('小标题为2个' in m for m in messages))
                self.assertTrue(any('表前缺引导句' in m for m in messages))

    def test_generator_groups_quantities_and_keeps_identifiers(self):
        cases = {
            '注册资本1221.1121万元，收入12345.6万元': '注册资本1,221.1121万元，收入12,345.6万元',
            '2025年、2026—2027年、2023-2025年': None,
            '专利ZL201811005866.6、申请号2025113659119': None,
            'T/CIET 1244—2025、GB/T 9704-2012、FC100、DF3000': None,
            '（688568）、688568.SH': None,
            '2000万—3000万元、1200—1500亿元': '2,000万—3,000万元、1,200—1,500亿元',
            '工信厅联通信〔2026〕4号、608所': None,
            '约4700万千瓦、同比增长1437.66%': '约4,700万千瓦、同比增长1,437.66%',
            '26,294.01万元': None,
        }
        for skill in SKILLS:
            spec = importlib.util.spec_from_file_location(
                'build_' + skill.replace('-', '_'), ROOT / skill / 'scripts/build_docx.py')
            module = importlib.util.module_from_spec(spec)
            import sys
            sys.path.insert(0, str(ROOT / skill / 'scripts'))
            try:
                spec.loader.exec_module(module)
            finally:
                sys.path.pop(0)
            for source, expected in cases.items():
                with self.subTest(skill=skill, source=source):
                    self.assertEqual(module.add_thousands_separators(source), expected or source)
            content = {'blocks': [
                {'type': 'table', 'header': ['序号', '专利号', '金额（万元）'],
                 'rows': [['1', '202511365', '12345']]},
                {'type': 'table', 'header': ['项目', '内容'], 'rows': [['邮编', '710000'], ['注册资本', '5000万元']]},
                {'type': 'p', 'text': '原文照录12345', 'thousands': False},
            ]}
            result = module.normalize_content_numbers(content)['blocks']
            with self.subTest(skill=skill, table=True):
                self.assertEqual(result[0]['rows'][0], ['1', '202511365', '12,345'])
                self.assertEqual(result[1]['rows'], [['邮编', '710000'], ['注册资本', '5,000万元']])
                self.assertEqual(result[2]['text'], '原文照录12345')
                self.assertEqual(module.normalize_content_numbers(dict(content, thousands=False)), dict(content, thousands=False))

    @staticmethod
    def load(skill):
        spec = importlib.util.spec_from_file_location(
            'style_' + skill.replace('-', '_'), ROOT / skill / 'scripts/style_check.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


if __name__ == '__main__':
    unittest.main()
