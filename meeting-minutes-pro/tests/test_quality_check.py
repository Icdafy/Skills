#!/usr/bin/env python3
"""Regression tests for the meeting-minutes-pro structure validator."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).parents[1] / "scripts" / "quality_check.py"
SPEC = importlib.util.spec_from_file_location("quality_check", SCRIPT)
QUALITY_CHECK = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(QUALITY_CHECK)

INDENT = "　　"


class TextInput:
    def __init__(self, text: str) -> None:
        self.text = text

    def read_text(self, encoding: str | None = None) -> str:
        return self.text


def document(title: str, *lines: str) -> TextInput:
    return TextInput(title + "\n" + "\n".join(INDENT + line for line in lines))


class CustomBannedTests(unittest.TestCase):
    def test_custom_phrase_blocks(self) -> None:
        doc = document("访谈纪要", "一、总体情况", "公司业务实现全面赋能。")
        errors = QUALITY_CHECK.validate(doc, "minutes", frozenset(), ["赋能"])
        self.assertTrue(any("赋能" in error for error in errors))

    def test_custom_phrase_released_by_allow_line(self) -> None:
        doc = document("访谈纪要", "一、总体情况", "公司业务实现全面赋能。")
        errors = QUALITY_CHECK.validate(doc, "minutes", {3}, ["赋能"])
        self.assertFalse(any("赋能" in error for error in errors))

    def test_empty_custom_list_is_noop(self) -> None:
        doc = document("访谈纪要", "一、总体情况", "公司经营情况良好。")
        errors = QUALITY_CHECK.validate(doc, "minutes", frozenset(), [])
        self.assertFalse(any("自定义禁用" in error for error in errors))


class HalfwidthPunctTests(unittest.TestCase):
    def test_halfwidth_paren_next_to_cjk_flagged(self) -> None:
        doc = document("访谈纪要", "一、总体情况", "张某某(总经理)介绍了情况。")
        errors = QUALITY_CHECK.validate(doc, "minutes", frozenset(), [])
        self.assertTrue(any("半角标点" in error for error in errors))

    def test_thousands_separator_not_flagged(self) -> None:
        doc = document("访谈纪要", "一、总体情况", "全年营收1,234万元符合预期。")
        errors = QUALITY_CHECK.validate(doc, "minutes", frozenset(), [])
        self.assertFalse(any("半角标点" in error for error in errors))


class DuplicateQuestionTests(unittest.TestCase):
    def test_near_identical_questions_flagged(self) -> None:
        doc = document(
            "访谈纪要",
            "一、完整总结概述",
            "总结内容概述。",
            "二、完整问答纪要",
            "问：公司全年营收能达到多少？",
            "答：约3000万元。",
            "",
            "问：公司全年营收能达到多少呢？",
            "答：与上一问相同。",
        )
        errors = QUALITY_CHECK.validate(doc, "qa-summary", frozenset(), [])
        self.assertTrue(any("疑似重复问答" in error for error in errors))

    def test_distinct_questions_not_flagged(self) -> None:
        doc = document(
            "访谈纪要",
            "一、完整总结概述",
            "总结内容概述。",
            "二、完整问答纪要",
            "问：公司全年营收能达到多少？",
            "答：约3000万元。",
            "",
            "问：创始团队的行业背景如何？",
            "答：均来自相关行业。",
        )
        errors = QUALITY_CHECK.validate(doc, "qa-summary", frozenset(), [])
        self.assertFalse(any("疑似重复问答" in error for error in errors))


def substantial_summary() -> str:
    sentence = (
        "会议围绕项目定位、技术体系、产品能力、商业化路径、团队资源"
        "和后续安排等主题进行了完整梳理。"
    )
    return sentence * 4


class QualityCheckTests(unittest.TestCase):
    def errors(self, mode: str, *lines: str, title: str = "项目会议纪要") -> list[str]:
        return QUALITY_CHECK.validate(document(title, *lines), mode)

    def test_pure_qa_is_rejected_in_auto(self) -> None:
        errors = self.errors("auto", "一、访谈问答", "问：项目处于什么阶段？", "答：处于验证阶段。")
        self.assertTrue(any("完整总结概述" in error for error in errors))

    def test_general_qa_also_requires_summary(self) -> None:
        errors = self.errors(
            "auto",
            "一、问答纪要",
            "问：如何申请试用？",
            "答：在线提交申请。",
            title="产品答疑记录",
        )
        self.assertTrue(any("完整总结概述" in error for error in errors))

    def test_ceo_reference_heading_shape_passes(self) -> None:
        errors = self.errors(
            "auto",
            "一、核心结论",
            substantial_summary(),
            "二、访谈重点问答",
            "问：项目处于什么阶段？",
            "答：处于验证阶段。",
        )
        self.assertEqual([], errors)

    def test_cto_reference_heading_shape_passes(self) -> None:
        errors = self.errors(
            "auto",
            "一、访谈主要内容",
            substantial_summary(),
            "二、访谈问答",
            "问：核心技术是什么？",
            "答：包括数据处理、轨道计算和风险研判。",
        )
        self.assertEqual([], errors)

    def test_minutes_mode_cannot_bypass_unpaired_question(self) -> None:
        errors = self.errors("minutes", "一、会议主要内容", substantial_summary(), "问：何时测试？")
        self.assertTrue(any("缺少对应“答：”" in error for error in errors))

    def test_minutes_mode_with_qa_still_requires_summary(self) -> None:
        errors = self.errors("minutes", "一、访谈问答", "问：何时测试？", "答：计划下月测试。")
        self.assertTrue(any("完整总结概述" in error for error in errors))

    def test_legacy_qa_mode_is_summary_alias(self) -> None:
        errors = self.errors("qa", "一、访谈问答", "问：何时测试？", "答：计划下月测试。")
        self.assertTrue(any("完整总结概述" in error for error in errors))

    def test_summary_only_minutes_pass(self) -> None:
        errors = self.errors("auto", "一、会议主要内容", substantial_summary())
        self.assertEqual([], errors)

    def test_token_summary_is_rejected(self) -> None:
        errors = self.errors(
            "auto",
            "一、核心结论",
            "项目情况总体正常。",
            "二、完整问答纪要",
            "问：项目处于什么阶段？",
            "答：处于验证阶段。",
        )
        self.assertTrue(any("内容不足" in error for error in errors))

    def test_long_qa_demands_proportional_summary(self) -> None:
        # A two-hour interview: ~30k characters of Q/A must not pass with a
        # 600-character overview; the requirement scales up to 2000 characters.
        answer = "答：" + "回答内容涉及技术路线、订单结构、毛利率与产能爬坡等。" * 60
        qa_lines: list[str] = []
        for _ in range(20):
            qa_lines.append("问：请介绍公司当前的业务进展和主要客户结构情况？")
            qa_lines.append(answer)
        errors = self.errors(
            "auto",
            "一、完整总结概述",
            substantial_summary() * 4,  # ~700 chars, below the scaled minimum
            "二、完整问答纪要",
            *qa_lines,
        )
        self.assertTrue(any("内容不足" in error for error in errors))

    def test_summary_must_precede_questions(self) -> None:
        errors = self.errors(
            "auto",
            "一、完整问答纪要",
            "问：项目处于什么阶段？",
            "答：处于验证阶段。",
            "二、完整总结概述",
            substantial_summary(),
        )
        self.assertTrue(any("完整总结概述" in error for error in errors))

    def test_pending_verification_phrase_is_rejected(self) -> None:
        errors = self.errors(
            "auto",
            "一、会议主要内容",
            substantial_summary() + "具体产能数据需结合审计报告进一步核实。",
        )
        self.assertTrue(any("核验或指导类表述" in error for error in errors))

    def test_daihe_marker_is_rejected(self) -> None:
        errors = self.errors(
            "auto",
            "一、会议主要内容",
            substantial_summary() + "订单金额为三千万元（待核）。",
        )
        self.assertTrue(any("核验或指导类表述" in error for error in errors))

    def test_yizhun_phrase_is_rejected(self) -> None:
        errors = self.errors(
            "auto",
            "一、会议主要内容",
            substantial_summary() + "最终数据以年报披露为准。",
        )
        self.assertTrue(any("核验或指导类表述" in error for error in errors))

    def test_allow_line_releases_quoted_content(self) -> None:
        doc = document(
            "项目会议纪要",
            "一、会议主要内容",
            substantial_summary(),
            "会议明确，最终交付时间以合同约定为准。",
        )
        errors = QUALITY_CHECK.validate(doc, "auto")
        self.assertTrue(any("核验或指导类表述" in error for error in errors))
        self.assertEqual([], QUALITY_CHECK.validate(doc, "auto", {4}))

    def test_redundant_interviewee_attributions_are_rejected(self) -> None:
        phrases = (
            "据受访人介绍，公司已完成样机测试。",
            "据受访人个人估计，市场规模约为500亿元。",
            "受访人表示，公司计划明年扩产。",
            "受访者认为，当前需求保持增长。",
            "据其自述，产品精度达到0.05摄氏度。",
            "对方表示，交付周期约为三个月。",
            "个人估计，市场规模约为500亿元。",
            "从个人判断来看，需求仍会增长。",
            "个人的初步印象是技术路线较为成熟。",
            "我个人认为，公司计划具备可行性。",
            "我的判断是明年可以完成扩产。",
            "我的印象是团队经验较为丰富。",
        )
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                errors = self.errors(
                    "auto",
                    "一、会议主要内容",
                    substantial_summary() + phrase,
                )
                self.assertTrue(any("冗余归因表述" in error for error in errors))

    def test_redundant_attribution_is_rejected_in_qa_answer(self) -> None:
        errors = self.errors(
            "auto",
            "一、完整总结概述",
            substantial_summary(),
            "二、完整问答纪要",
            "问：公司计划何时扩产？",
            "答：受访人表示，公司计划明年扩产。",
        )
        self.assertTrue(any("冗余归因表述" in error for error in errors))

    def test_redundant_interviewee_label_is_rejected_in_title(self) -> None:
        errors = self.errors(
            "auto",
            "一、会议主要内容",
            substantial_summary(),
            title="受访人访谈纪要",
        )
        self.assertTrue(any("冗余归因表述" in error for error in errors))

    def test_allow_line_cannot_release_redundant_attribution(self) -> None:
        doc = document(
            "项目会议纪要",
            "一、会议主要内容",
            substantial_summary(),
            "受访人表示，公司计划明年扩产。",
        )
        errors = QUALITY_CHECK.validate(doc, "auto", {4})
        self.assertTrue(any("不可用 --allow-line 放行" in error for error in errors))

    def test_success_reports_zero_redundant_attribution_residuals(self) -> None:
        text = "\n".join(
            [
                "项目会议纪要",
                INDENT + "一、会议主要内容",
                INDENT + substantial_summary(),
            ]
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            minutes = Path(temp_dir) / "会议纪要.txt"
            minutes.write_text(text, encoding="utf-8")
            output = io.StringIO()
            argv = ["quality_check.py", str(minutes), "--mode", "auto"]
            with mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(output):
                code = QUALITY_CHECK.main()
        self.assertEqual(0, code)
        self.assertIn("冗余归因表述检查：0 处残留", output.getvalue())

    def test_risk_section_in_summary_is_rejected(self) -> None:
        errors = self.errors(
            "auto",
            "一、完整总结概述",
            "（一）项目情况",
            substantial_summary(),
            "（二）主要风险与待核事项",
            substantial_summary(),
            "二、完整问答纪要",
            "问：项目处于什么阶段？",
            "答：处于验证阶段。",
        )
        self.assertTrue(any("板块" in error for error in errors))

    def test_consecutive_qa_groups_require_blank_line(self) -> None:
        errors = self.errors(
            "auto",
            "一、核心结论",
            substantial_summary(),
            "二、访谈重点问答",
            "问：项目处于什么阶段？",
            "答：处于验证阶段。",
            "问：客户结构如何？",
            "答：以头部客户为主。",
        )
        self.assertTrue(any("空一行" in error for error in errors))

    def test_blank_line_between_qa_groups_passes(self) -> None:
        text = "\n".join(
            [
                "项目会议纪要",
                INDENT + "一、核心结论",
                INDENT + substantial_summary(),
                INDENT + "二、访谈重点问答",
                INDENT + "问：项目处于什么阶段？",
                INDENT + "答：处于验证阶段。",
                "",
                INDENT + "问：客户结构如何？",
                INDENT + "答：以头部客户为主。",
            ]
        )
        self.assertEqual([], QUALITY_CHECK.validate(TextInput(text), "auto"))

    def test_interviewee_affiliation_requires_parentheses(self) -> None:
        errors = self.errors(
            "auto",
            "访谈对象：张某某，某某公司总经理",
            "一、会议主要内容",
            substantial_summary(),
        )
        self.assertTrue(any("（）" in error for error in errors))

    def test_common_words_are_not_false_positives(self) -> None:
        errors = self.errors(
            "auto",
            "一、会议主要内容",
            substantial_summary()
            + "公司期待核心团队进一步扩充，员工现有待遇高于行业平均水平。",
        )
        self.assertEqual([], errors)

    def test_waiting_verification_is_still_caught(self) -> None:
        errors = self.errors(
            "auto",
            "一、会议主要内容",
            substantial_summary() + "上述产能数据等待核实。",
        )
        self.assertTrue(any("核验或指导类表述" in error for error in errors))

    def test_interviewee_with_parentheses_passes(self) -> None:
        errors = self.errors(
            "auto",
            "访谈对象：张某某（某某公司总经理）",
            "一、会议主要内容",
            substantial_summary(),
        )
        self.assertEqual([], errors)


if __name__ == "__main__":
    unittest.main()
