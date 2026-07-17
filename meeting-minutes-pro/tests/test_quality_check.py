#!/usr/bin/env python3
"""Regression tests for the meeting-minutes-pro structure validator."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


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
            "受访人表示，最终交付时间以合同约定为准。",
        )
        errors = QUALITY_CHECK.validate(doc, "auto")
        self.assertTrue(any("核验或指导类表述" in error for error in errors))
        self.assertEqual([], QUALITY_CHECK.validate(doc, "auto", {4}))

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
