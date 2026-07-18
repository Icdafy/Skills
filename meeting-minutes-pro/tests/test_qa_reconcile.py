#!/usr/bin/env python3
"""Tests for the transcript-vs-minutes Q&A reconciler."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "qa_reconcile.py"
SPEC = importlib.util.spec_from_file_location("qa_reconcile", SCRIPT)
QA = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = QA
SPEC.loader.exec_module(QA)

INDENT = "　　"


def stamp(text: str, start: float, end: float, speaker: str | None) -> dict:
    return {"text": text, "start": start, "end": end, "speaker": speaker}


class QuestionDetectionTests(unittest.TestCase):
    def test_question_mark_detected(self) -> None:
        self.assertTrue(QA.is_question("公司目前的毛利率大概是多少？"))

    def test_interrogative_without_mark_detected(self) -> None:
        self.assertTrue(QA.is_question("公司目前有没有海外收入这一块"))

    def test_filler_rejected(self) -> None:
        self.assertFalse(QA.is_question("是吧？"))
        self.assertFalse(QA.is_question("嗯对，是吧"))

    def test_short_text_rejected(self) -> None:
        self.assertFalse(QA.is_question("多少？"))

    def test_adjacent_questions_same_speaker_merge(self) -> None:
        stamps = [
            stamp("咱们的产能现在到多少了？", 10.0, 13.0, "说话人1"),
            stamp("后面怎么继续爬坡呢？", 13.5, 16.0, "说话人1"),
            stamp("现在每月500台。", 17.0, 20.0, "说话人2"),
        ]
        candidates = QA.stamps_to_candidates(stamps)
        self.assertEqual(len(candidates), 1)
        self.assertIn("产能", candidates[0].text)
        self.assertIn("爬坡", candidates[0].text)


class ReconcileTests(unittest.TestCase):
    def make_candidates(self, *texts: str) -> list:
        return [QA.Candidate(text, float(i * 60), "说话人1")
                for i, text in enumerate(texts)]

    def test_all_questions_covered(self) -> None:
        candidates = self.make_candidates("公司目前的毛利率大概是多少？")
        questions = ["公司目前的毛利率水平是多少？"]
        suspected, orphaned, matched = QA.reconcile(candidates, questions, 0.30, [])
        self.assertEqual(suspected, [])
        self.assertEqual(orphaned, [])
        self.assertEqual(len(matched), 1)
        self.assertIn("毛利率", matched[0][2])

    def test_dropped_question_is_flagged(self) -> None:
        candidates = self.make_candidates(
            "公司目前的毛利率大概是多少？",
            "创始团队之前有没有相关行业的从业背景？",
        )
        questions = ["公司目前的毛利率水平是多少？"]
        suspected, _, _ = QA.reconcile(candidates, questions, 0.30, [])
        self.assertEqual(len(suspected), 1)
        self.assertIn("创始团队", suspected[0][1].text)

    def test_skip_releases_reviewed_candidate(self) -> None:
        candidates = self.make_candidates(
            "公司目前的毛利率大概是多少？",
            "创始团队之前有没有相关行业的从业背景？",
        )
        questions = ["公司目前的毛利率水平是多少？"]
        suspected, _, _ = QA.reconcile(candidates, questions, 0.30, [2])
        self.assertEqual(suspected, [])

    def test_fabricated_minutes_question_is_orphaned(self) -> None:
        candidates = self.make_candidates("公司目前的毛利率大概是多少？")
        questions = [
            "公司目前的毛利率水平是多少？",
            "公司未来三年的上市计划是什么？",
        ]
        _, orphaned, _ = QA.reconcile(candidates, questions, 0.30, [])
        self.assertEqual(len(orphaned), 1)
        self.assertIn("上市计划", orphaned[0])

    def test_short_candidate_needs_higher_similarity(self) -> None:
        # 净长不足 10 字的候选阈值抬到 0.45：弱相似不再静默算作已匹配。
        candidates = self.make_candidates("毛利多少？")
        questions = ["净利润率多少"]
        suspected, _, matched = QA.reconcile(candidates, questions, 0.30, [])
        self.assertEqual(len(suspected), 1)
        self.assertEqual(matched, [])


class AnswerGapTests(unittest.TestCase):
    def test_missing_answer_number_reported(self) -> None:
        candidate = QA.Candidate("咱们全年营收能到多少？", 10.0, "说话人1")
        matched = [(1, candidate, "全年营收能到多少？", 0.9)]
        stamps = [
            {"text": "咱们全年营收能到多少？", "start": 10.0, "end": 14.0},
            {"text": "全年营收大概3000万，净利率一成。", "start": 15.0, "end": 20.0},
        ]
        groups = [("全年营收能到多少？",
                   "问：全年营收能到多少？\n答：全年营收约3000万元。")]
        gaps = QA.answer_number_gaps(matched, [candidate], stamps, groups)
        self.assertEqual(len(gaps), 1)
        self.assertIn("一成", gaps[0][2])
        self.assertNotIn("3000万", gaps[0][2])

    def test_complete_answer_has_no_gap(self) -> None:
        candidate = QA.Candidate("咱们全年营收能到多少？", 10.0, "说话人1")
        matched = [(1, candidate, "全年营收能到多少？", 0.9)]
        stamps = [
            {"text": "咱们全年营收能到多少？", "start": 10.0, "end": 14.0},
            {"text": "全年营收大概3000万，净利率一成。", "start": 15.0, "end": 20.0},
        ]
        groups = [("全年营收能到多少？",
                   "问：全年营收能到多少？\n答：全年营收约3000万元，净利率约10%。")]
        gaps = QA.answer_number_gaps(matched, [candidate], stamps, groups)
        self.assertEqual(gaps, [])

    def test_answer_window_ends_at_next_question(self) -> None:
        first = QA.Candidate("咱们全年营收能到多少？", 10.0, "说话人1")
        second = QA.Candidate("团队现在多少人？", 30.0, "说话人1")
        matched = [(1, first, "全年营收能到多少？", 0.9)]
        stamps = [
            {"text": "全年营收大概3000万。", "start": 15.0, "end": 20.0},
            {"text": "团队现在有50人。", "start": 35.0, "end": 40.0},
        ]
        groups = [("全年营收能到多少？",
                   "问：全年营收能到多少？\n答：约3000万元。")]
        gaps = QA.answer_number_gaps(matched, [first, second], stamps, groups)
        # 50人 belongs to the next question's window and must not be demanded here.
        self.assertEqual(gaps, [])


class LoadingTests(unittest.TestCase):
    def test_load_candidates_from_json_and_minutes_questions(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            transcript = root / "recording.json"
            transcript.write_text(json.dumps({"text": "", "timestamps": [
                stamp("今天先聊聊经营情况。", 0.0, 3.0, "说话人1"),
                stamp("咱们全年营收能到多少？", 4.0, 7.0, "说话人1"),
                stamp("大概3000万左右。", 8.0, 12.0, "说话人2"),
            ]}, ensure_ascii=False), encoding="utf-8")
            candidates = QA.load_candidates(transcript)
            self.assertEqual(len(candidates), 1)
            self.assertIn("营收", candidates[0].text)

            minutes = root / "minutes.txt"
            minutes.write_text(
                "访谈纪要\n" + INDENT + "问：全年营收预计多少？\n" + INDENT + "答：约3000万元。",
                encoding="utf-8",
            )
            self.assertEqual(QA.minutes_questions(minutes), ["全年营收预计多少？"])

    def test_minutes_qa_groups_split_by_question_and_heading(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            minutes = Path(raw) / "minutes.txt"
            minutes.write_text(
                "访谈纪要\n"
                + INDENT + "二、完整问答纪要\n"
                + INDENT + "问：营收多少？\n"
                + INDENT + "答：约3000万元。\n"
                + INDENT + "（二）团队情况\n"
                + INDENT + "问：团队多少人？\n"
                + INDENT + "答：共50人。",
                encoding="utf-8",
            )
            groups = QA.minutes_qa_groups(minutes)
            self.assertEqual(len(groups), 2)
            self.assertIn("3000万元", groups[0][1])
            self.assertNotIn("50人", groups[0][1])
            self.assertIn("50人", groups[1][1])


if __name__ == "__main__":
    unittest.main()
