#!/usr/bin/env python3
"""给报告规格中的数量补千位分隔符（每三位一个西文半角逗号）。

用法：
    python -X utf8 group_thousands.py <report-spec.json> [--output <新规格.json>] [--check]

处理范围与 validate_report.py 的千位分隔符校验一致：正文和附件的段落、表题、表注、
表头、单元格、附件标题，以及事实台账的 assertions、row_fact 断言（保证“报告—台账”
的精确关联不因补逗号而断开）。年份、日期、文号、编号、代码、电话、证件号等标识性
数字不加逗号，判定规则直接复用校验器的 UNGROUPED_NUMBER。

不带 --output 时只列出将要修改的位置，不写文件；--check 在存在未分节数字时返回 1。
不得把输出覆盖到来源材料；规格文件属于工作产物。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_report import UNGROUPED_NUMBER, configure_utf8_stdio  # noqa: E402

SKIP_DOCUMENT_KEYS = {"document_number", "contact_phone"}
RENDERED_DOCUMENT_KEYS = (
    "company", "signer", "recipient", "legal_basis", "issuer", "contact_name", "printer",
)


def group_text(text: str) -> tuple[str, list[str]]:
    """Return the text with every ungrouped quantity grouped, plus the originals found."""

    found: list[str] = []
    pieces: list[str] = []
    cursor = 0
    for match in UNGROUPED_NUMBER.finditer(text):
        digits = match.group(0)
        found.append(digits)
        pieces.append(text[cursor:match.start()])
        pieces.append(f"{int(digits):,}")
        cursor = match.end()
    pieces.append(text[cursor:])
    return "".join(pieces), found


class Grouper:
    def __init__(self) -> None:
        self.changes: list[tuple[str, str]] = []

    def fix(self, value: Any, location: str) -> Any:
        if isinstance(value, str):
            fixed, found = group_text(value)
            for digits in found:
                self.changes.append((location, digits))
            return fixed
        if isinstance(value, list):
            return [self.fix(item, location) for item in value]
        return value

    def blocks(self, blocks: Any, scope: str) -> None:
        if not isinstance(blocks, list):
            return
        for index, block in enumerate(blocks, start=1):
            if not isinstance(block, dict):
                continue
            where = f"{scope} block {index}"
            for key in ("text", "header", "rows", "row_assertions"):
                if key in block:
                    block[key] = self.fix(block[key], f"{where} {key}")

    def spec(self, spec: dict[str, Any]) -> None:
        document = spec.get("document")
        if isinstance(document, dict):
            for key in RENDERED_DOCUMENT_KEYS:
                if key in document and key not in SKIP_DOCUMENT_KEYS:
                    document[key] = self.fix(document[key], f"document.{key}")
        self.blocks(spec.get("main_blocks"), "main body")
        for attachment in spec.get("attachments") or []:
            if not isinstance(attachment, dict):
                continue
            scope = f"attachment {attachment.get('id')}"
            if "title" in attachment:
                attachment["title"] = self.fix(attachment["title"], f"{scope} title")
            self.blocks(attachment.get("blocks"), scope)
        for fact in spec.get("fact_ledger") or []:
            if isinstance(fact, dict) and "assertions" in fact:
                fact["assertions"] = self.fix(
                    fact["assertions"], f"fact {fact.get('id')} assertions"
                )


def main() -> int:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="给报告规格中的数量补千位分隔符")
    parser.add_argument("spec", type=Path)
    parser.add_argument("--output", type=Path, help="写出补齐后的规格；省略时只预览")
    parser.add_argument("--check", action="store_true", help="存在未分节数字时返回 1")
    args = parser.parse_args()

    spec = json.loads(args.spec.read_text(encoding="utf-8-sig"))
    grouper = Grouper()
    grouper.spec(spec)
    for location, digits in grouper.changes:
        print(f"{location}: {digits} -> {int(digits):,}")
    print(f"共 {len(grouper.changes)} 处未分节数字")
    if args.output is not None:
        args.output.write_text(
            json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"已写出 {args.output}；补齐后须重新运行 validate_report.py")
    if args.check and grouper.changes:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
