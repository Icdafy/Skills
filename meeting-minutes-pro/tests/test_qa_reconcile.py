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


if __name__ == "__main__":
    unittest.main()
