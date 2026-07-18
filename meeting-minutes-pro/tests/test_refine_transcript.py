#!/usr/bin/env python3
"""Tests for targeted dual-engine review planning and comparison (no models)."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "refine_transcript.py"
SPEC = importlib.util.spec_from_file_location("refine_transcript", SCRIPT)
REFINE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = REFINE
SPEC.loader.exec_module(REFINE)


def stamp(text: str, start: float, end: float) -> dict:
    return {"text": text, "start": start, "end": end, "speaker": None}


class RiskSelectionTests(unittest.TestCase):
    def test_number_sentence_selected(self) -> None:
        self.assertIn("number", REFINE.sentence_risks("全年营收3000万元。", []))

    def test_date_sentence_selected(self) -> None:
        self.assertIn("number", REFINE.sentence_risks("计划3月15日交付。", []))

    def test_glossary_sentence_selected(self) -> None:
        self.assertIn("glossary", REFINE.sentence_risks("张三介绍了情况。", ["张三"]))

    def test_question_sentence_selected(self) -> None:
        self.assertIn("question", REFINE.sentence_risks("毛利率能到多少？", []))

    def test_plain_talk_not_selected(self) -> None:
        self.assertEqual(REFINE.sentence_risks("大家先随便聊聊。", []), ())

    def test_chinese_year_selected(self) -> None:
        self.assertIn("number", REFINE.sentence_risks("公司二〇二三年成立。", []))


class ClipPlanningTests(unittest.TestCase):
    def test_adjacent_risky_sentences_merge_with_padding(self) -> None:
        stamps = [
            stamp("全年营收3000万元。", 10.0, 14.0),
            stamp("毛利率30%。", 15.0, 18.0),
            stamp("大家随便聊聊。", 60.0, 63.0),
            stamp("产能每月500台。", 200.0, 204.0),
        ]
        clips = REFINE.plan_clips(stamps, [], select_all=False, pad=1.5,
                                  merge_gap=4.0, max_clip=120.0, duration=300.0)
        self.assertEqual(len(clips), 2)
        self.assertAlmostEqual(clips[0].start, 8.5)
        self.assertAlmostEqual(clips[0].end, 19.5)
        self.assertIn("3000万", clips[0].funasr_text)
        self.assertIn("30%", clips[0].funasr_text)
        self.assertNotIn("随便聊聊", clips[0].funasr_text)

    def test_max_clip_splits_long_runs(self) -> None:
        stamps = [
            stamp(f"第{i}项指标是{i * 7}万元。", float(i * 10), float(i * 10 + 8))
            for i in range(1, 30)
        ]
        clips = REFINE.plan_clips(stamps, [], select_all=False, pad=0.0,
                                  merge_gap=4.0, max_clip=60.0, duration=400.0)
        self.assertGreater(len(clips), 1)
        for clip in clips:
            self.assertLessEqual(clip.end - clip.start, 60.0 + 1e-6)

    def test_select_all_covers_everything(self) -> None:
        stamps = [
            stamp("大家随便聊聊。", 0.0, 5.0),
            stamp("聊聊天气。", 6.0, 9.0),
        ]
        clips = REFINE.plan_clips(stamps, [], select_all=True, pad=0.0,
                                  merge_gap=4.0, max_clip=120.0, duration=9.0)
        self.assertEqual(len(clips), 1)
        self.assertEqual(clips[0].reasons, ("all",))


class ComparisonTests(unittest.TestCase):
    def test_equivalent_number_writings_do_not_conflict(self) -> None:
        conflicts = REFINE.compare_texts("全年营收三千万。", "全年营收3000万。", [])
        self.assertEqual(conflicts, [])

    def test_diverging_percentages_conflict(self) -> None:
        conflicts = REFINE.compare_texts("毛利率30%左右。", "毛利率13%左右。", [])
        categories = {item["category"] for item in conflicts}
        self.assertIn("数字", categories)

    def test_negation_flip_conflicts(self) -> None:
        conflicts = REFINE.compare_texts("目前未中标该项目。", "目前已中标该项目。", [])
        categories = {item["category"] for item in conflicts}
        self.assertIn("否定词", categories)

    def test_glossary_disagreement_conflicts(self) -> None:
        conflicts = REFINE.compare_texts("由张三负责推进。", "由章散负责推进。", ["张三"])
        categories = {item["category"] for item in conflicts}
        self.assertIn("术语", categories)

    def test_date_disagreement_conflicts(self) -> None:
        conflicts = REFINE.compare_texts("三月十五号交付。", "三月二十号交付。", [])
        categories = {item["category"] for item in conflicts}
        self.assertIn("数字", categories)


class OrderComparisonTests(unittest.TestCase):
    def test_same_set_different_order_conflicts(self) -> None:
        conflicts = REFINE.compare_texts(
            "市占率30%，毛利率15%。", "市占率15%，毛利率30%。", []
        )
        categories = {item["category"] for item in conflicts}
        self.assertIn("数字顺序", categories)

    def test_same_order_does_not_conflict(self) -> None:
        conflicts = REFINE.compare_texts(
            "市占率百分之三十，毛利率15%。", "市占率30%，毛利率15%。", []
        )
        self.assertEqual(conflicts, [])

    def test_presence_conflict_not_doubled_as_order(self) -> None:
        conflicts = REFINE.compare_texts("毛利率30%。", "毛利率13%。", [])
        categories = [item["category"] for item in conflicts]
        self.assertIn("数字", categories)
        self.assertNotIn("数字顺序", categories)

    def test_repetition_does_not_conflict(self) -> None:
        conflicts = REFINE.compare_texts(
            "3000万，对，3000万。", "3000万。", []
        )
        self.assertEqual(conflicts, [])


class RiskScoreTests(unittest.TestCase):
    def test_amount_with_commitment_outranks_bare_year(self) -> None:
        high = REFINE.clip_risk_score("承诺回购价3000万元。", [])
        low = REFINE.clip_risk_score("公司二〇二三年成立。", [])
        self.assertGreater(high, low)

    def test_negation_and_glossary_raise_score(self) -> None:
        base = REFINE.clip_risk_score("产能500台。", [])
        richer = REFINE.clip_risk_score("张三说产能不能超过500台。", ["张三"])
        self.assertGreater(richer, base)


class BudgetTests(unittest.TestCase):
    @staticmethod
    def clip(index: int, start: float, end: float, score: int) -> "REFINE.Clip":
        return REFINE.Clip(index=index, start=start, end=end, reasons=("number",),
                           funasr_text="", score=score)

    def test_highest_scores_selected_within_budget(self) -> None:
        clips = [self.clip(1, 0, 60, 5), self.clip(2, 100, 160, 1),
                 self.clip(3, 200, 260, 3)]
        selected, skipped = REFINE.apply_budget(clips, 2.0)
        self.assertEqual([c.index for c in selected], [1, 3])
        self.assertEqual([c.index for c in skipped], [2])
        self.assertEqual(skipped[0].status, "skipped")

    def test_top_risk_clip_always_reviewed(self) -> None:
        clips = [self.clip(1, 0, 300, 9), self.clip(2, 400, 430, 1)]
        selected, skipped = REFINE.apply_budget(clips, 1.0)
        self.assertEqual([c.index for c in selected], [1])
        self.assertEqual([c.index for c in skipped], [2])

    def test_no_budget_selects_everything(self) -> None:
        clips = [self.clip(1, 0, 60, 5), self.clip(2, 100, 160, 1)]
        selected, skipped = REFINE.apply_budget(clips, None)
        self.assertEqual(len(selected), 2)
        self.assertEqual(skipped, [])

    def test_safe_hms_has_no_colons(self) -> None:
        self.assertEqual(REFINE.safe_hms(3661), "010101")
        self.assertNotIn(":", REFINE.safe_hms(7325.4))


if __name__ == "__main__":
    unittest.main()
