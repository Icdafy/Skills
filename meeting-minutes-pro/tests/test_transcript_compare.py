#!/usr/bin/env python3
"""Behavioural checks for phrase-level difference screening (no ASR model)."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
import refine_transcript
import transcript_compare


class TranscriptComparisonTests(unittest.TestCase):
    def compare(self, left, right):
        return refine_transcript.compare_texts(left, right, [])

    def categories(self, left, right):
        return {item['category'] for item in self.compare(left, right)}

    def test_equal_number_on_different_metric_needs_review(self):
        self.assertIn('数字对象或语境', self.categories(
            '公司营业收入3000万元。', '公司净利润3000万元。'))

    def test_negation_bound_to_different_subject_needs_review(self):
        self.assertIn('否定或状态归属', self.categories(
            '国内业务盈利，海外业务不盈利。', '国内业务不盈利，海外业务盈利。'))

    def test_non_numeric_plan_and_achievement_differ(self):
        categories = self.categories('公司计划在明年推出产品。', '公司已经在去年推出产品。')
        self.assertIn('否定或状态归属', categories)
        self.assertIn('时间或限定词归属', categories)

    def test_negation_reassignment_without_punctuation(self):
        self.assertIn('否定或状态归属', self.categories(
            '国内业务盈利海外业务不盈利。', '国内业务不盈利海外业务盈利。'))

    def test_same_global_state_words_on_different_subjects(self):
        self.assertIn('否定或状态归属', self.categories(
            '甲产品已经量产，乙产品计划量产。', '甲产品计划量产，乙产品已经量产。'))

    def test_same_relative_dates_on_different_subjects(self):
        self.assertIn('时间或限定词归属', self.categories(
            '甲产品去年量产，乙产品明年量产。', '甲产品明年量产，乙产品去年量产。'))

    def test_partial_clause_omission(self):
        self.assertIn('片段遗漏', self.categories(
            '公司主营业务是工业机器人研发，公司客户主要来自汽车行业。',
            '公司主营业务是工业机器人研发。'))

    def test_omission_inside_unpunctuated_speech(self):
        self.assertIn('片段遗漏', self.categories(
            '公司主营业务是工业机器人研发公司客户主要来自汽车行业目前已经量产。',
            '公司主营业务是工业机器人研发目前已经量产。'))

    def test_general_text_change_is_checked_despite_shared_number(self):
        self.assertIn('文本差异', self.categories(
            '计划投资3000万元用于开发医疗设备。', '计划投资3000万元用于建设汽车工厂。'))

    def test_same_number_different_entity(self):
        self.assertTrue(self.compare('甲公司收入3000万元。', '乙公司收入3000万元。'))

    def test_long_shared_prefix_does_not_hide_changed_metric(self):
        prefix = '针对公司本年度经营情况相关问题董事长专门补充介绍公司'
        self.assertIn('数字对象或语境', self.categories(
            prefix + '营业收入3000万元。', prefix + '净利润3000万元。'))

    def test_numeric_equivalence_preserves_consistency(self):
        examples = [
            ('全年营收三千万。', '全年营收3000万。'),
            ('市占率百分之三十，毛利率15%。', '市占率30%，毛利率15%。'),
            ('3月15日交付。', '三月十五号交付。'),
            ('公司2025年完成融资。', '公司二〇二五年完成融资。'),
            ('价格1,000万元。', '价格一千万元。'),
            ('售价100万美元。', '售价一百万美金。'),
            ('材料重500公斤。', '材料重五百千克。'),
            ('今年收入3000万。', '今年收入三千万元。'),
        ]
        for left, right in examples:
            with self.subTest(left=left):
                self.assertEqual(self.compare(left, right), [])

    def test_repeated_confirmation_not_missing_speech(self):
        for left in ('3000万，对，3000万。', '嗯，3000万，是的，3000万。'):
            with self.subTest(left=left):
                self.assertEqual(self.compare(left, '3000万。'), [])

    def test_normalisation_does_not_replace_numerals_inside_names(self):
        left, right = '三一重工采购三台设备。', '三一重工采购3台设备。'
        self.assertEqual(transcript_compare.canonical(left), transcript_compare.canonical(right))
        self.assertEqual(self.compare(left, right), [])

    def test_repeated_whole_clause_not_missing_speech(self):
        self.assertEqual(self.compare('公司主营机器人，公司主营机器人。', '公司主营机器人。'), [])

    def test_punctuation_only_is_not_a_difference(self):
        self.assertEqual(self.compare('公司主营机器人，产品已经量产。', '公司主营机器人产品已经量产。'), [])

    def test_punctuation_merge_with_changed_neighbour(self):
        self.assertEqual(transcript_compare.compare_phrases(
            '公司主营机器人，产品已经量产。收入三千万元。',
            '公司主营机器人产品已经量产，收入3000万元。'), [])

    def test_empty_side_retains_missing_text_category(self):
        self.assertIn('文本缺失', self.categories('', '产品已经交付客户。'))

    def test_conflict_schema_preserves_both_readings(self):
        result = self.compare('公司营业收入3000万元。', '公司净利润3000万元。')
        for finding in result:
            self.assertEqual(set(finding), {'category', 'funasr_only', 'qwen_only'})
            self.assertIsInstance(finding['funasr_only'], list)
            self.assertIsInstance(finding['qwen_only'], list)

    def test_no_rewrite_or_winner_is_produced(self):
        result = self.compare('甲公司收入3000万元。', '乙公司收入3000万元。')
        self.assertTrue(result)
        self.assertNotIn('accepted_text', str(result))


if __name__ == '__main__':
    unittest.main()
