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
        "会议围绕项目定位、技术体系、产品能力、商业化路径、团队资源、"
        "主要风险和后续核查事项进行了完整梳理。"
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


if __name__ == "__main__":
    unittest.main()
