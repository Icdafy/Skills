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


class ToneRuleTests(unittest.TestCase):
    def test_follow_up_judgment_tail_is_flagged(self) -> None:
        for tail in ("该事项需要后续进行判断。", "相关影响有待进一步研判。",
                     "市场变化仍需持续观察。", "具体安排视情况而定。"):
            with self.subTest(tail=tail):
                doc = document("访谈纪要", "一、总体情况", "公司已完成样机测试，" + tail)
                errors = QUALITY_CHECK.validate(doc, "minutes", frozenset(), [])
                self.assertTrue(any("后续判断" in error or "有待" in error for error in errors))

    def test_negation_contrast_is_flagged(self) -> None:
        for sentence in ("该项目的核心不在于规模而在于技术。",
                         "公司选择自研而非外购。",
                         "本轮融资用于扩产而不是研发。",
                         "这不是短期行为，是长期布局。"):
            with self.subTest(sentence=sentence):
                doc = document("访谈纪要", "一、总体情况", sentence)
                errors = QUALITY_CHECK.validate(doc, "minutes", frozenset(), [])
                self.assertTrue(any("对照式" in error for error in errors))

    def test_plain_statement_passes_tone_rules(self) -> None:
        doc = document("访谈纪要", "一、总体情况", "公司选择自研路线，非常重视核心技术积累。")
        errors = QUALITY_CHECK.validate(doc, "minutes", frozenset(), [])
        self.assertFalse(any("对照式" in error or "后续判断" in error for error in errors))

    def test_table_rows_skip_indent_rule(self) -> None:
        doc = TextInput("访谈纪要\n　　一、财务情况\n|指标|金额（万元）|\n|---|---|\n|收入|100|\n　　正文。")
        errors = QUALITY_CHECK.validate(doc, "minutes", frozenset(), [])
        self.assertFalse(any("全角空格" in error for error in errors))


class HalfwidthPunctTests(unittest.TestCase):
    def test_halfwidth_paren_next_to_cjk_flagged(self) -> None:
        doc = document("访谈纪要", "一、总体情况", "张某某(总经理)介绍了情况。")
        errors = QUALITY_CHECK.validate(doc, "minutes", frozenset(), [])
        self.assertTrue(any("半角标点" in error for error in errors))

    def test_thousands_separator_not_flagged(self) -> None:
        doc = document("访谈纪要", "一、总体情况", "全年营收1,234万元符合预期。")
        errors = QUALITY_CHECK.validate(doc, "minutes", frozenset(), [])
        self.assertFalse(any("半角标点" in error for error in errors))
        self.assertFalse(any("千位分隔符" in error for error in errors))

    def test_ungrouped_number_flagged_and_identifiers_exempt(self) -> None:
        doc = document("访谈纪要", "一、总体情况", "全年营收1234万元，交付12000台。")
        errors = QUALITY_CHECK.validate(doc, "minutes", frozenset(), [])
        self.assertTrue(any("千位分隔符" in error for error in errors))
        released = QUALITY_CHECK.validate(doc, "minutes", frozenset({3}), [])
        self.assertFalse(any("千位分隔符" in error for error in released))
        identifiers = document(
            "访谈纪要", "一、总体情况",
            "2026年9月28日14:00，依据〔2026〕12号文，2025—2030年规划产能1,200台。",
        )
        errors = QUALITY_CHECK.validate(identifiers, "minutes", frozenset(), [])
        self.assertFalse(any("千位分隔符" in error for error in errors))


class DeliverableContentTests(unittest.TestCase):
    def errors(self, *lines: str, title: str = "项目会议纪要") -> list[str]:
        return QUALITY_CHECK.validate(document(title, *lines), "minutes", custom_banned=[])

    def test_explanatory_parentheses_are_rejected_everywhere(self) -> None:
        examples = (
            ("项目会议纪要（内部讨论）", ("公司已完成样机测试。",)),
            ("项目会议纪要 (Draft)", ("公司已完成样机测试。",)),
            ("项目会议纪要", ("访谈对象：张某某（公司总经理）",)),
            ("项目会议纪要", ("一、总体情况（讨论内容）",)),
            ("项目会议纪要", ("公司计划扩产（含一期产能），交付周期约三个月。",)),
            ("项目会议纪要", ("The platform (draft) supports exports.",)),
            ("项目会议纪要", ("|指标|金额（万元）|",)),
            ("项目会议纪要", ("|指标|Amount (CNY)|",)),
            ("项目会议纪要", ("附件：工作方案（试行）",)),
        )
        for title, lines in examples:
            with self.subTest(title=title, lines=lines):
                self.assertTrue(any("解释性括注" in e for e in self.errors(*lines, title=title)))

    def test_qa_parenthetical_notes_are_rejected(self) -> None:
        for qa_line in ("问：本年收入是多少（含税）？", "答：收入约3,000万元（未审计）。"):
            with self.subTest(qa_line=qa_line):
                errors = self.errors("一、会议主要内容", qa_line)
                self.assertTrue(any("解释性括注" in e for e in errors))

    def test_only_leading_official_heading_numbers_are_exempt(self) -> None:
        errors = self.errors(
            "一、总体情况", "（一）产品能力", "1.测试情况", "（1）测试环境", "公司完成测试。",
        )
        self.assertEqual([], errors)
        for line in ("设备共（100）台。", "问：（1）为何扩产？", "|（1）|产能|",
                     "（一）产品能力（补充说明）", "（1）环境（说明）", "(1)测试环境", "（1）"):
            with self.subTest(line=line):
                self.assertTrue(any("解释性括注" in e for e in self.errors("一、总体情况", line)))

    def test_nested_or_unclosed_parentheses_are_rejected(self) -> None:
        for line in ("公司计划扩产（含一期（试验线））。", "公司计划扩产（补充说明。",
                     "公司计划扩产）补充说明。", "The platform (draft supports exports."):
            with self.subTest(line=line):
                self.assertTrue(any("解释性括注" in e for e in self.errors(line)))

    def test_validator_does_not_silently_remove_facts(self) -> None:
        text = "项目会议纪要\n　　公司计划扩产（补充说明），交付周期约三个月。"
        doc = TextInput(text)
        self.assertTrue(any("解释性括注" in e for e in QUALITY_CHECK.validate(doc, "minutes")))
        self.assertEqual(text, doc.text)
        self.assertEqual([], self.errors("公司计划扩产，交付周期约三个月。"))

    def test_parenthesis_error_preserves_effective_units_and_qualifiers(self) -> None:
        errors = self.errors("本年收入约1,000万元（含税）。")
        error = next(e for e in errors if "解释性括注" in e)
        self.assertIn("有效单位、范围或限定词等应直接并入句子", error)
        self.assertEqual([], self.errors("本年含税收入约1,000万元。"))

    def test_processing_and_source_notes_are_rejected(self) -> None:
        examples = (
            "本纪要根据录音整理，项目已完成验证。",
            "纪要由音频转文字后形成。",
            "本段名词已按BP核对。",
            "根据会议录音，交付周期约三个月。",
            "依据转录内容，公司已完成样机测试。",
            "据转录稿显示，公司计划扩产。",
            "根据BP，公司预计下一年收入为5亿元。",
            "来源：录音转写文本。",
            "转录说明：部分音频不清晰。",
            "整理说明：内容取自录音。",
            "以上内容由转录稿整理。",
            "|内容来源：转录稿|已完成测试|",
            "录音中提到，年产能约1,000台。",
            "转录稿未明确具体交付时间。",
            "原文识别为某某科技。",
            "该名词识别不清。",
            "转录存疑。",
            "该处录音不清晰，无法辨识。",
            "该处录音不清晰，无法辨认。",
            "该名称无法辨识。",
            "该数字转录为30。",
            "BP核对后，名称为星锥一号。",
            "经BP核对，名称为星锥一号。",
            "根据转录稿整理，合同金额约1,200万元。",
        )
        for line in examples:
            with self.subTest(line=line):
                self.assertTrue(any("加工元说明" in e for e in self.errors(line)))

    def test_processing_notes_in_title_metadata_and_qa_are_rejected(self) -> None:
        examples = (
            ("本纪要根据录音整理", "公司完成测试。"),
            ("项目会议纪要", "访谈对象：本纪要根据音频记载，张某某"),
            ("项目会议纪要", "答：根据转录稿，交付周期约三个月。"),
            ("项目会议纪要", "问：原文识别为某某科技吗？"),
        )
        for title, line in examples:
            with self.subTest(title=title, line=line):
                self.assertTrue(any("加工元说明" in e for e in self.errors(line, title=title)))

    def test_audio_and_transcription_business_content_remains_allowed(self) -> None:
        examples = (
            "公司生产录音设备，年产能约1,000台。",
            "公司提供会议转录服务，单月处理音频时长约1,000小时。",
            "语音识别准确率达到98%，识别结果用于实时字幕。",
            "产品根据录音生成字幕，再将转录结果存入数据库。",
            "根据录音生成字幕是公司的核心功能。",
            "录音中包含音乐与人声，系统可分别识别。",
            "会议讨论了转录模型的识别错误与改进方案。",
            "数据来源：业务系统。",
            "合同原文为交付后支付货款，双方计划延长账期。",
            "该处产品标记不清晰，需要提高印刷精度。",
            "公司提供BP核对服务，主要客户为投资机构。",
        )
        for line in examples:
            with self.subTest(line=line):
                self.assertEqual([], self.errors(line))

    def test_allow_line_cannot_bypass_deliverable_content_rules(self) -> None:
        doc = document("项目会议纪要", "公司计划扩产（补充说明）。", "根据录音，公司完成测试。")
        errors = QUALITY_CHECK.validate(doc, "minutes", {2, 3}, [])
        for label in ("解释性括注", "加工元说明"):
            self.assertTrue(any(label in e and "不可用 --allow-line 放行" in e for e in errors))


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

    def test_named_reporting_clauses_are_rejected_in_summary(self) -> None:
        phrases = (
            "张三介绍了公司当前的产品布局。",
            "李四认为市场需求仍将增长。",
            "技术负责人提到核心模块已完成验证。",
            "管理层指出今年将扩大产能。",
            "公司方面表示，交付周期约为三个月。",
        )
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                errors = self.errors(
                    "auto",
                    "一、完整总结概述",
                    substantial_summary() + phrase,
                    "二、完整问答纪要",
                    "问：项目处于什么阶段？",
                    "答：处于验证阶段。",
                )
                self.assertTrue(any("转述句式" in error for error in errors))

    def test_direct_summary_statement_passes_reporting_clause_check(self) -> None:
        errors = self.errors(
            "auto",
            "一、完整总结概述",
            substantial_summary() + "公司当前已完成样机测试，交付周期约为三个月。",
            "二、完整问答纪要",
            "问：项目处于什么阶段？",
            "答：处于验证阶段。",
        )
        self.assertFalse(any("转述句式" in error for error in errors))

    def test_source_label_passes_reporting_clause_check(self) -> None:
        errors = self.errors(
            "auto",
            "一、完整总结概述",
            substantial_summary() + "管理层口径：明年计划完成扩产。",
            "二、完整问答纪要",
            "问：项目处于什么阶段？",
            "答：处于验证阶段。",
        )
        self.assertFalse(any("转述句式" in error for error in errors))

    def test_named_reporting_clause_outside_summary_is_not_scoped_error(self) -> None:
        errors = self.errors(
            "auto",
            "一、完整总结概述",
            substantial_summary(),
            "二、完整问答纪要",
            "问：谁说明了扩产计划？",
            "答：张三介绍了扩产计划。",
        )
        self.assertFalse(any("转述句式" in error for error in errors))

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
        self.assertIn("总结概述转述句式检查：0 处残留", output.getvalue())
        self.assertIn("解释性括注检查：0 处残留", output.getvalue())
        self.assertIn("加工元说明检查：0 处残留", output.getvalue())

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

    def test_second_qa_heading_requires_blank_after_previous_answer(self) -> None:
        errors = self.errors(
            "auto",
            "一、完整总结概述",
            substantial_summary(),
            "二、完整问答纪要",
            "（一）业务情况",
            "问：当前进展如何？",
            "答：已完成验证。",
            "（二）后续安排",
            "问：下一步如何安排？",
            "答：计划下月启动。",
        )
        self.assertTrue(any("二级标题" in error and "空一行" in error for error in errors))

    def test_blank_before_heading_and_tight_first_qa_passes(self) -> None:
        text = "\n".join(
            [
                "项目会议纪要",
                INDENT + "一、完整总结概述",
                INDENT + substantial_summary(),
                INDENT + "二、完整问答纪要",
                INDENT + "（一）业务情况",
                INDENT + "问：当前进展如何？",
                INDENT + "答：已完成验证。",
                "",
                INDENT + "（二）后续安排",
                INDENT + "问：下一步如何安排？",
                INDENT + "答：计划下月启动。",
            ]
        )
        self.assertEqual([], QUALITY_CHECK.validate(TextInput(text), "auto"))

    def test_interviewee_affiliation_uses_plain_text(self) -> None:
        errors = self.errors(
            "auto",
            "访谈对象：张某某，某某公司总经理",
            "一、会议主要内容",
            substantial_summary(),
        )
        self.assertEqual([], errors)

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

    def test_interviewee_with_parentheses_is_rejected(self) -> None:
        errors = self.errors(
            "auto",
            "访谈对象：张某某（某某公司总经理）",
            "一、会议主要内容",
            substantial_summary(),
        )
        self.assertTrue(any("解释性括注" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
