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
    qa_labels: list[tuple[int, str]] = []
    for line_number, line in visible[1:]:
        if not line.startswith(INDENT):
            errors.append(f"第 {line_number} 行未以两个全角空格起首。")
        content = line.removeprefix(INDENT).strip()
        level = level_number(content)
        if level is not None:
            if last_level == 0 and level > 1:
                errors.append(f"第 {line_number} 行在缺少上级标题时使用第 {level} 级标题。")
            elif last_level and level > last_level + 1:
                errors.append(f"第 {line_number} 行层级从第 {last_level} 级跳至第 {level} 级。")
            last_level = level
        if content.startswith("问："):
            qa_labels.append((line_number, "问"))
        if content.startswith("答："):
            qa_labels.append((line_number, "答"))

    document = "\n".join(lines)
    if any(pattern.search(document) for pattern in CONTRAST_PATTERNS):
        errors.append("存在禁用的对照式连词组合。")

    qa_detected = bool(qa_labels)
    if mode == "qa" or (mode == "auto" and qa_detected):
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

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Check meeting-minutes-pro text output.")
    parser.add_argument("input", type=Path, help="UTF-8 plain-text minutes file")
    parser.add_argument("--mode", choices=("auto", "minutes", "qa"), default="auto")
    args = parser.parse_args()

    if not args.input.is_file():
        parser.error(f"找不到文件：{args.input}")

    errors = validate(args.input, args.mode)
    if errors:
        print("纪要文本校验未通过：")
        for error in errors:
            print(f"- {error}")
        return 1

    print("纪要文本校验通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
