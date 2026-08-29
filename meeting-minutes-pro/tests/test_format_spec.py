#!/usr/bin/env python3
"""Tests for the shared layout spec: heading grammar, western-run rule and the
role→font mapping consumed by both the validator and the renderer."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "format_spec.py"
SPEC = importlib.util.spec_from_file_location("format_spec", SCRIPT)
FS = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(FS)


class LevelGrammarTests(unittest.TestCase):
    def test_ordinal_levels(self) -> None:
        self.assertEqual(FS.level_number("一、完整总结概述"), 1)
        self.assertEqual(FS.level_number("（一）项目背景"), 2)
        self.assertEqual(FS.level_number("1.核心技术指标"), 3)
        self.assertEqual(FS.level_number("（1）测试环境"), 4)

    def test_body_is_unnumbered(self) -> None:
        self.assertIsNone(FS.level_number("公司成立于2019年。"))
        self.assertIsNone(FS.level_number("问：核心壁垒是什么？"))

    def test_third_level_rejects_decimal_led_body(self) -> None:
        # The #3 fix: a body line opening with a decimal must not be read as a
        # "3." third-level heading.
        self.assertIsNone(FS.level_number("3.5亿元用于研发投入。"))
        self.assertIsNone(FS.level_number("12.5%的同比增长。"))
        self.assertIsNone(FS.level_number("1.2.3 版本已发布。"))

    def test_third_level_still_matches_two_digit_ordinal(self) -> None:
        self.assertEqual(FS.level_number("10.风险与应对"), 3)


class WesternSegmentTests(unittest.TestCase):
    def test_alphanumeric_tokens_are_whole_runs(self) -> None:
        self.assertEqual(
            FS.WESTERN_SEGMENT.findall("采用 T3 与 5G，Qwen3 框架，COO 负责"),
            ["T3", "5G", "Qwen3", "COO"],
        )

    def test_ranges_paths_and_percentages(self) -> None:
        self.assertEqual(
            FS.WESTERN_SEGMENT.findall("2024-2025 年，GB/T 9704，占比 1,234.56%"),
            ["2024-2025", "GB/T", "9704", "1,234.56%"],
        )

    def test_pure_letters_match(self) -> None:
        # Previously a letters-only token stayed in the CJK font; now it is a
        # western run set in Times New Roman.
        self.assertEqual(FS.WESTERN_SEGMENT.findall("由 CEO 与 CFO 汇报"), ["CEO", "CFO"])

    def test_cjk_only_has_no_western_run(self) -> None:
        self.assertEqual(FS.WESTERN_SEGMENT.findall("公司团队规模稳定"), [])


class RoleMappingTests(unittest.TestCase):
    def test_role_fonts(self) -> None:
        self.assertEqual(FS.paragraph_role("一、总述"), ("first", FS.HEI_FONT, False))
        self.assertEqual(FS.paragraph_role("（一）背景"), ("second", FS.KAI_FONT, True))
        self.assertEqual(FS.paragraph_role("1.指标"), ("third", FS.FANGSONG_FONT, True))
        self.assertEqual(FS.paragraph_role("（1）环境"), ("fourth", FS.FANGSONG_FONT, False))
        self.assertEqual(FS.paragraph_role("正文一段。"), ("body", FS.FANGSONG_FONT, False))


class PageNumberSpecTests(unittest.TestCase):
    def test_fourth_size_simsun_with_spaced_dashes(self) -> None:
        self.assertEqual(FS.PAGE_NUMBER_FONT, "宋体")
        self.assertEqual(FS.PAGE_NUMBER_FONT, FS.SONG_FONT)
        self.assertEqual(FS.PAGE_NUMBER_SIZE, 14)
        self.assertEqual((FS.PAGE_NUMBER_PREFIX, FS.PAGE_NUMBER_SUFFIX), ("- ", " -"))


class FontCatalogueTests(unittest.TestCase):
    def test_embeddable_fonts_are_the_two_gb2312_faces(self) -> None:
        self.assertEqual(
            FS.embeddable_fonts(),
            {"楷体_GB2312": "楷体_GB2312.ttf", "仿宋_GB2312": "simfang.ttf"},
        )

    def test_title_face_is_not_embeddable(self) -> None:
        title = next(e for e in FS.FONT_CATALOG if e["run_name"] == FS.TITLE_FONT)
        self.assertFalse(title["embeddable"])

    def test_simsun_is_required_as_localised_system_font(self) -> None:
        song = next(e for e in FS.FONT_CATALOG if e["run_name"] == FS.SONG_FONT)
        self.assertEqual(song["family"], "SimSun")
        self.assertIsNone(song["asset"])
        self.assertFalse(song["embeddable"])

    def test_pdf_markers_and_alerts(self) -> None:
        self.assertEqual(FS.pdf_required_markers(), ("KaiTi_GB2312", "FangSong_GB2312"))
        self.assertEqual(FS.pdf_substitute_alerts(), ("KaiTi", "FangSong"))


if __name__ == "__main__":
    unittest.main()
