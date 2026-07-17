#!/usr/bin/env python3
"""Validate text prepared by the meeting-minutes-pro skill."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

INDENT = "　　"
FIRST_LEVEL = re.compile(r"^[一二三四五六七八九十]+、")
SECOND_LEVEL = re.compile(r"^（[一二三四五六七八九十]+）")
THIRD_LEVEL = re.compile(r"^\d+\.")
FOURTH_LEVEL = re.compile(r"^（\d+）")
INTERVIEW_METADATA = ("访谈时间：", "访谈地点：", "访谈对象：", "访谈人员：")
SUMMARY_MARKERS = (
    "完整总结概述",
    "总体情况概述",
    "主要内容概述",
    "访谈主要内容",
    "会议主要内容",
    "核心结论摘要",
    "核心结论",
    "综合摘要",
    "会议摘要",
    "访谈摘要",
    "尽调摘要",
    "总结与研判",
)
QA_SECTION_MARKERS = (
    "完整问答纪要",
    "完整问答",
    "访谈重点问答",
    "访谈问答",
    "重点问答",
    "问答纪要",
    "问答环节",
)

# Detect prohibited paired conjunctions anywhere within the same sentence.
CLAUSE = r"[^\r\n。！？!?]*?"
CONTRAST_PATTERNS = [
    re.compile("不" + "是" + CLAUSE + "而" + "是"),
    re.compile("并" + "非" + CLAUSE + "而" + "是"),
    re.compile("不" + "仅" + CLAUSE + "而" + "是"),
    re.compile("不" + "仅" + CLAUSE + "而" + "且"),
    re.compile("不" + "仅" + CLAUSE + "还"),
    re.compile("不" + "但" + CLAUSE + "而" + "且"),
    re.compile("不" + "但" + CLAUSE + "还"),
]


def level_number(text: str) -> int | None:
    if FIRST_LEVEL.match(text):
        return 1
    if SECOND_LEVEL.match(text):
        return 2
    if THIRD_LEVEL.match(text):
        return 3
    if FOURTH_LEVEL.match(text):
        return 4
    return None


def validate(path: Path, mode: str) -> list[str]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    visible = [(index + 1, line) for index, line in enumerate(lines) if line.strip()]
    errors: list[str] = []

    if len(visible) < 2:
        return ["正文至少应包含标题和一段纪要内容。"]

    title_line, title = visible[0]
    if title.startswith(INDENT):
        errors.append(f"第 {title_line} 行标题不应首行缩进。")

    last_level = 0
    first_heading_line: int | None = None
    interview_metadata: list[tuple[int, int, str]] = []
    seen_interview_metadata: dict[str, int] = {}
    qa_labels: list[tuple[int, str]] = []
    headings: list[tuple[int, int, str]] = []
    body_lines: list[tuple[int, str]] = []
    for line_number, line in visible[1:]:
        if not line.startswith(INDENT):
            errors.append(f"第 {line_number} 行未以两个全角空格起首。")
        content = line.removeprefix(INDENT).strip()
        level = level_number(content)
        if level is not None:
            headings.append((line_number, level, content))
            if first_heading_line is None:
                first_heading_line = line_number
            if last_level == 0 and level > 1:
                errors.append(f"第 {line_number} 行在缺少上级标题时使用第 {level} 级标题。")
            elif last_level and level > last_level + 1:
                errors.append(f"第 {line_number} 行层级从第 {last_level} 级跳至第 {level} 级。")
            last_level = level
        else:
            body_lines.append((line_number, content))
        for field_index, field in enumerate(INTERVIEW_METADATA):
            if content.startswith(field):
                if field in seen_interview_metadata:
                    errors.append(
                        f"第 {line_number} 行重复出现“{field.removesuffix('：')}”，"
                        f"首次出现于第 {seen_interview_metadata[field]} 行。"
                    )
                else:
                    seen_interview_metadata[field] = line_number
                    interview_metadata.append((field_index, line_number, field))
        if content.startswith("问："):
            qa_labels.append((line_number, "问"))
        if content.startswith("答："):
            qa_labels.append((line_number, "答"))

    if interview_metadata:
        field_indexes = [field_index for field_index, _, _ in interview_metadata]
        if field_indexes != sorted(field_indexes):
            errors.append("访谈基本信息顺序应为：访谈时间、访谈地点、访谈对象、访谈人员。")
        if first_heading_line is not None:
            misplaced = [
                (line_number, field)
                for _, line_number, field in interview_metadata
                if line_number > first_heading_line
            ]
            for line_number, field in misplaced:
                errors.append(
                    f"第 {line_number} 行“{field.removesuffix('：')}”应置于第一个正文标题之前。"
                )

    document = "\n".join(lines)
    if any(pattern.search(document) for pattern in CONTRAST_PATTERNS):
        errors.append("存在禁用的对照式连词组合。")

    qa_detected = bool(qa_labels)
    # Every explicit Q/A label must be paired, regardless of the selected mode.
    # The legacy ``qa`` mode is retained as a compatibility alias but no longer
    # permits a pure-QA deliverable.
    if qa_detected or mode in ("qa", "qa-summary"):
        if not qa_labels:
            errors.append("问答纪要必须同时包含“问：”和“答：”。")
        else:
            waiting_for_answer = False
            question_line = 0
            for line_number, label in qa_labels:
                if label == "问":
                    if waiting_for_answer:
                        errors.append(f"第 {question_line} 行“问：”后缺少对应“答：”。")
                    waiting_for_answer = True
                    question_line = line_number
                elif not waiting_for_answer:
                    errors.append(f"第 {line_number} 行“答：”前缺少对应“问：”。")
                else:
                    waiting_for_answer = False
            if waiting_for_answer:
                errors.append(f"第 {question_line} 行“问：”后缺少对应“答：”。")

    # A minutes deliverable containing Q/A must always begin with a standalone,
    # comprehensive thematic overview. Pure Q/A is not a valid output shape.
    summary_required = qa_detected or mode in ("qa", "qa-summary")
    if summary_required:
        if not qa_detected:
            errors.append("组合式问答纪要必须包含完整的“问：/答：”内容。")
        else:
            question_lines = [
                line_number for line_number, label in qa_labels if label == "问"
            ]
            if not question_lines:
                return errors
            first_question_line = min(question_lines)
            summary_candidates = [
                (line_number, content)
                for line_number, level, content in headings
                if level == 1
                and line_number < first_question_line
                and any(marker in content for marker in SUMMARY_MARKERS)
            ]
            qa_section_candidates = [
                (line_number, content)
                for line_number, level, content in headings
                if level == 1
                and line_number < first_question_line
                and any(marker in content for marker in QA_SECTION_MARKERS)
            ]
            if not summary_candidates:
                errors.append(
                    "含问答的纪要须在完整问答前设置一级标题“完整总结概述”（或同义标题）。"
                )
            if not qa_section_candidates:
                errors.append(
                    "组合式问答纪要须在首个问题前设置一级标题“完整问答纪要”（或同义标题）。"
                )
            if summary_candidates and qa_section_candidates:
                summary_line = summary_candidates[0][0]
                qa_section_line = qa_section_candidates[-1][0]
                if summary_line >= qa_section_line:
                    errors.append("“完整总结概述”必须置于“完整问答纪要”之前。")
                else:
                    summary_body = [
                        content
                        for line_number, content in body_lines
                        if summary_line < line_number < qa_section_line
                        and not content.startswith(INTERVIEW_METADATA)
                    ]
                    qa_body = [
                        content
                        for line_number, content in body_lines
                        if line_number >= first_question_line
                    ]
                    summary_chars = sum(len(content) for content in summary_body)
                    qa_chars = sum(len(content) for content in qa_body)
                    minimum_summary_chars = min(600, max(120, qa_chars // 10))
                    if summary_chars < minimum_summary_chars:
                        errors.append(
                            "“完整总结概述”内容不足：当前正文约 "
                            f"{summary_chars} 字，按问答篇幅至少应达到约 "
                            f"{minimum_summary_chars} 字，并覆盖整份转录稿的主要主题。"
                        )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Check meeting-minutes-pro text output.")
    parser.add_argument("input", type=Path, help="UTF-8 plain-text minutes file")
    parser.add_argument(
        "--mode", choices=("auto", "minutes", "qa", "qa-summary"), default="auto"
    )
    args = parser.parse_args()

    if args.mode == "qa":
        print(
            "提示：纯 QA 模式已停用；--mode qa 现按 qa-summary 兼容校验。",
            file=sys.stderr,
        )

    if not args.input.is_file():
        parser.error(f"找不到文件：{args.input}")

    errors = validate(args.input, args.mode)
    if errors:
        print("纪要文本校验未通过：")
        for error in errors:
            print(f"- {error}")
        return 1

    text = args.input.read_text(encoding="utf-8-sig")
    qa_pairs = len(re.findall(r"^\s*　　问：", text, re.MULTILINE))
    pending = text.count("待核")
    print("纪要文本校验通过。")
    print(f"提示：问答 {qa_pairs} 组；“待核”标注 {pending} 处"
          f"{'，交付前须与用户逐项确认' if pending else ''}。"
          "数字事实核对请另行运行 fact_check.py。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
