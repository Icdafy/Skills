#!/usr/bin/env python3
"""Tests for the pre-delivery orchestrator's pure helpers."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "check_all.py"
SPEC = importlib.util.spec_from_file_location("check_all", SCRIPT)
CHECK_ALL = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = CHECK_ALL
SPEC.loader.exec_module(CHECK_ALL)


class NormalizedLinesTests(unittest.TestCase):
    def test_ideographic_spaces_and_blanks_removed(self) -> None:
        text = "标题\n\n　　一、正文 内容\n　　\n　　问：多少？"
        self.assertEqual(
            CHECK_ALL.normalized_lines(text),
            ["标题", "一、正文内容", "问：多少？"],
        )


class CompareLineListsTests(unittest.TestCase):
    def test_identical_lists_match(self) -> None:
        result = CHECK_ALL.compare_line_lists(["标题", "正文"], ["标题", "正文"])
        self.assertTrue(result["matches"])

    def test_subtitle_line_exempted(self) -> None:
        result = CHECK_ALL.compare_line_lists(
            ["标题", "综合办公室", "正文"], ["标题", "正文"]
        )
        self.assertTrue(result["matches"])
        self.assertIn("副标题", result["note"])

    def test_known_subtitle_verified_exactly(self) -> None:
        result = CHECK_ALL.compare_line_lists(
            ["标题", "投资部", "正文"], ["标题", "正文"], "投资部"
        )
        self.assertTrue(result["matches"])
        self.assertIn("已按 --subtitle 核对", result["note"])

    def test_wrong_subtitle_is_flagged(self) -> None:
        # The old blanket exemption accepted any extra line; a known subtitle is
        # now checked precisely, so a mismatched subtitle fails.
        result = CHECK_ALL.compare_line_lists(
            ["标题", "投资部", "正文"], ["标题", "正文"], "综合办公室"
        )
        self.assertFalse(result["matches"])

    def test_diverging_paragraph_reported(self) -> None:
        result = CHECK_ALL.compare_line_lists(
            ["标题", "营收3000万元"], ["标题", "营收3500万元"]
        )
        self.assertFalse(result["matches"])
        self.assertIn("不一致", result["note"])

    def test_missing_paragraph_reported(self) -> None:
        result = CHECK_ALL.compare_line_lists(["标题"], ["标题", "被丢掉的段落"])
        self.assertFalse(result["matches"])
        self.assertIn("段落数不一致", result["note"])


class ResolveTranscriptTests(unittest.TestCase):
    def test_json_prefers_sibling_txt(self) -> None:
        structured, plain = CHECK_ALL.resolve_transcript(Path("out/rec.json"))
        self.assertEqual(structured, Path("out/rec.json"))
        self.assertEqual(plain, Path("out/rec.txt"))

    def test_plain_txt_used_for_both(self) -> None:
        structured, plain = CHECK_ALL.resolve_transcript(Path("out/rec.txt"))
        self.assertEqual(structured, plain)


if __name__ == "__main__":
    unittest.main()
