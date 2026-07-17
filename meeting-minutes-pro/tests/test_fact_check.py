#!/usr/bin/env python3
"""Regression tests for the extended fact checker (dates, 〇, advisories)."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import tempfile
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "fact_check.py"
SPEC = importlib.util.spec_from_file_location("fact_check", SCRIPT)
FACT_CHECK = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = FACT_CHECK
SPEC.loader.exec_module(FACT_CHECK)

INDENT = "　　"


class TempFiles:
    def __enter__(self) -> "TempFiles":
        self._dir = tempfile.TemporaryDirectory()
        self.root = Path(self._dir.name)
        return self

    def __exit__(self, *exc) -> None:
        self._dir.cleanup()

    def write(self, name: str, text: str) -> Path:
        path = self.root / name
        path.write_text(text, encoding="utf-8")
        return path


def minutes_doc(*body_lines: str) -> str:
    return "访谈纪要\n" + "\n".join(INDENT + line for line in body_lines)


def run_verify(minutes: str, transcript: str, **kwargs) -> tuple[int, str]:
    with TempFiles() as files:
        minutes_path = files.write("minutes.txt", minutes)
        transcript_path = files.write("transcript.txt", transcript)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = FACT_CHECK.verify(minutes_path, [transcript_path], [], **kwargs)
        return code, buffer.getvalue()


class ParserTests(unittest.TestCase):
    def test_digit_string_year(self) -> None:
        self.assertEqual(FACT_CHECK.parse_cn_int("二〇二五"), 2025)
        self.assertEqual(FACT_CHECK.parse_cn_int("二零二五"), 2025)

    def test_month_day_tokens_extracted_from_minutes(self) -> None:
        tokens = FACT_CHECK.extract_tokens(INDENT + "计划3月15日交付设备。", body_only=True)
        kinds = {(t.kind, t.value) for t in tokens}
        self.assertIn(("month", 3.0), kinds)
        self.assertIn(("day", 15.0), kinds)


class VerifyTests(unittest.TestCase):
    def test_spoken_date_matches_written_date(self) -> None:
        code, _ = run_verify(
            minutes_doc("会议明确3月15日前完成交付。"),
            "我们争取三月十五号之前交付",
        )
        self.assertEqual(code, 0)

    def test_unsupported_month_fails(self) -> None:
        code, output = run_verify(
            minutes_doc("会议明确5月交付。"),
            "我们尽快安排交付",
        )
        self.assertEqual(code, 1)
        self.assertIn("5月", output)

    def test_cn_year_matches_arabic_year(self) -> None:
        code, _ = run_verify(
            minutes_doc("公司于二〇二五年完成融资。"),
            "公司2025年完成了一轮融资",
        )
        self.assertEqual(code, 0)

    def test_colloquial_year_span_not_force_verified(self) -> None:
        # 两三年/一两年 are approximations, not years; they must not be
        # extracted as numeric facts that fail verification.
        code, _ = run_verify(
            minutes_doc("公司预计未来两三年完成产能扩张。"),
            "我们尽快把产能提上去",
        )
        self.assertEqual(code, 0)

    def test_amount_equivalence_still_passes(self) -> None:
        code, _ = run_verify(
            minutes_doc("全年营收3000万元。"),
            "我们去年做了三千万的收入",
        )
        self.assertEqual(code, 0)

    def test_fabricated_amount_still_fails(self) -> None:
        code, _ = run_verify(
            minutes_doc("全年营收3000万元。"),
            "我们收入情况还不错",
        )
        self.assertEqual(code, 1)

    def test_show_matches_prints_transcript_context(self) -> None:
        code, output = run_verify(
            minutes_doc("毛利率为30%。"),
            "整体毛利率大概30%左右",
            show_matches=True,
        )
        self.assertEqual(code, 0)
        self.assertIn("转录稿依据", output)
        self.assertIn("30%", output)

    def test_glossary_rewrite_advisory_is_warning_only(self) -> None:
        code, output = run_verify(
            minutes_doc("张三介绍了公司情况。"),
            "章散介绍了公司情况",
            terms=["张三"],
        )
        self.assertEqual(code, 0)
        self.assertIn("术语改写提示", output)
        self.assertIn("张三", output)

    def test_glossary_term_present_in_transcript_not_flagged(self) -> None:
        code, output = run_verify(
            minutes_doc("张三介绍了公司情况。"),
            "张三介绍了公司情况",
            terms=["张三"],
        )
        self.assertEqual(code, 0)
        self.assertNotIn("术语改写提示", output)


class CompareTests(unittest.TestCase):
    def test_date_disagreement_across_engines(self) -> None:
        with TempFiles() as files:
            a = files.write("a.txt", "计划三月十五号交付")
            b = files.write("b.txt", "计划三月二十号交付")
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = FACT_CHECK.compare(a, b)
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
