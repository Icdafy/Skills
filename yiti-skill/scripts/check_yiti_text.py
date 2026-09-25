#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_yiti_text.py —— 议题正文语言扫描。

扫描议题 JSON（create_yiti_docx.py 的输入）或 Markdown/纯文本成稿，逐段检查：

硬规则（命中即退出码 1，成稿前必须改掉）：
1. 悬置/拖延收尾句——"需要后续进行判断""有待进一步研判""后续持续关注""视情况而定"等。
   议题每段以事实或结论收尾，不留"以后再判断"的尾巴。
2. 对举句式——"不是……而是""并非……而是""不仅……而且""而非""而不是"等。
   直接陈述"是什么""为什么必要"，不先否定再肯定。
3. 引子与总结套话——"值得注意的是""需要指出的是""综上所述""总的来说""首先，""其次，"。
   流程叙述可用"先……随后……之后……最后……"，不在此列。
4. 口语与自称——"大家""非常"、感叹号、"本议题""本文"。

警告（按上下文复核，不强制）：
5. 语气偏激进——"必然""势必""彻底""毫无""严重恶化""濒临"等绝对化、情绪化用词。
6. 语气偏保守——"或许""也许""似乎""恐怕""不排除"，或同一句叠加两个以上推测词。
7. 单侧否定铺垫——"并非""不是"（未与"而是"成对时）。
8. 半角括号括住中文、全角数字或全角百分号（生成器会自动转半角，文本稿需手工改）。

用法：
    python check_yiti_text.py spec.json
    python check_yiti_text.py draft.md
退出码：0 = 无硬规则命中（可能有警告）；1 = 有硬规则命中。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # Windows GBK 控制台防乱码
    except Exception:
        pass

_CLAUSE = r"[^。；;！!？?\n]"

HARD_RULES = [
    ("悬置/拖延收尾句（以事实或结论收尾，删去'后续再判断'类尾句）", re.compile(
        r"(?:有待|尚待|仍待|留待)(?:后续|进一步|下一步|今后)?(?:判断|研判|观察|评估|论证|核实|验证|明确|确认|跟踪)|"
        rf"(?:需要|仍需|尚需|还需|需)(?:后续|进一步|持续|下一步|今后|结合后续|视后续|根据后续|密切){_CLAUSE}{{0,30}}"
        r"(?:判断|研判|观察|评估|关注|跟踪|论证|核实|验证|确认|明确)|"
        r"(?:后续|下一步|今后|未来)(?:仍|还)?(?:需要|需|将|应|有待)?(?:持续|进一步|密切)(?:关注|跟踪|观察|研判|判断|评估)|"
        r"(?:后续|下一步|今后)(?:仍|还)?(?:需要|需|有待)(?:关注|跟踪|观察|研判|判断|评估)|"
        r"视(?:后续|具体|实际)?情况(?:而定|再定|另行)|"
        r"(?:暂|尚|目前)(?:无法|难以|不能)(?:判断|研判|确定|评估)")),
    ("对举句式（直接陈述是什么，不先否定再肯定）", re.compile(
        rf"不是{_CLAUSE}{{1,40}}而是|并非{_CLAUSE}{{1,40}}而是|并不是{_CLAUSE}{{1,40}}而是|"
        rf"不仅{_CLAUSE}{{1,40}}(?:而且|而是|还|更|也)|不但{_CLAUSE}{{1,40}}(?:而且|还|也)|"
        rf"不只是{_CLAUSE}{{1,40}}(?:更|还|而是)|不止{_CLAUSE}{{1,40}}(?:而是|还)|不光{_CLAUSE}{{1,40}}还|"
        rf"与其说{_CLAUSE}{{1,40}}不如说|不在于{_CLAUSE}{{1,40}}而在于|而不是|而非")),
    ("引子与总结套话", re.compile(
        r"值得注意的是|需要指出的是|需要说明的是|综上所述|总的来说|总而言之|众所周知|不难看出|首先[，,]|其次[，,]")),
    ("口语与自称", re.compile(r"大家|非常(?!规|态|设|任)|[！!]|本议题|本文(?!件)")),
]

WARN_RULES = [
    ("语气偏激进（以数据支撑判断，改用'显著''较大''大概率'等有量化依据的表述）", re.compile(
        r"必然|必将|势必|注定|彻底|毫无|绝对|一定会|肯定会|严重恶化|急剧恶化|濒临|崩盘|全面失败|完全(?:不|没有|无法|丧失|失败)")),
    ("语气偏保守（去掉无依据的推测词，直接陈述事实与判断）", re.compile(r"或许|也许|似乎|恐怕|不排除")),
    ("单侧否定铺垫（改为正面陈述）", re.compile(r"并非|不是")),
    ("半角括号括住中文（改为全角'（）'）", re.compile(r"\([^()（）\n]*[\u4e00-\u9fff][^()（）\n]*\)")),
    ("全角数字或全角百分号（改为半角，数字统一 Times New Roman）", re.compile(r"[０-９％]")),
]

# "无实现可能""不可能""可能性"中的"可能"是名词，不计入推测词。
SPECULATION = re.compile(r"(?<![无不现])可能(?!性)|或将|或许|也许|有望|预计|大概率|估计")
PAIRED = re.compile(r"(?:不是|并非)" + _CLAUSE + r"{1,40}而是")


def _strip_markup(text: str) -> str:
    return text.replace("**", "")


def iter_spec_texts(data: dict):
    """Yield (location, text) for every text unit in a create_yiti_docx.py spec."""
    for key in ("title", "submit_line", "recipient"):
        if data.get(key):
            yield key, str(data[key])
    intro = data.get("intro")
    for i, text in enumerate([intro] if isinstance(intro, str) else (intro or []), start=1):
        yield f"intro[{i}]", text
    yield from _iter_blocks(data.get("blocks") or [], "blocks")
    for i, name in enumerate(data.get("attachments") or [], start=1):
        yield f"attachments[{i}]", str(name)
    for a_idx, appendix in enumerate(data.get("appendices") or [], start=1):
        if appendix.get("title"):
            yield f"appendices[{a_idx}].title", str(appendix["title"])
        yield from _iter_blocks(appendix.get("blocks") or [], f"appendices[{a_idx}].blocks")


def _iter_blocks(blocks: list, prefix: str):
    for b_idx, block in enumerate(blocks, start=1):
        loc = f"{prefix}[{b_idx}]"
        if block.get("text"):
            yield loc, str(block["text"])
        if block.get("caption"):
            yield loc + ".caption", str(block["caption"])
        for c_idx, cell in enumerate(block.get("header") or [], start=1):
            yield f"{loc}.header[{c_idx}]", str(cell)
        for r_idx, row in enumerate(block.get("rows") or [], start=1):
            for c_idx, cell in enumerate(row, start=1):
                yield f"{loc}.rows[{r_idx}][{c_idx}]", str(cell)


def iter_plain_texts(text: str):
    for line_no, line in enumerate(text.splitlines(), start=1):
        if line.strip():
            yield f"第{line_no}行", line


def scan(units) -> tuple[list[str], list[str]]:
    hard, warn = [], []
    for loc, raw in units:
        text = _strip_markup(raw)
        for label, pattern in HARD_RULES:
            for m in pattern.finditer(text):
                hard.append(f"[硬规则] {label}：『{m.group(0)}』（{loc}）")
        for label, pattern in WARN_RULES:
            for m in pattern.finditer(text):
                if label.startswith("单侧否定") and PAIRED.search(text):
                    continue
                warn.append(f"[警告] {label}：『{m.group(0)}』（{loc}）")
        for sentence in re.split(r"[。；;！!？?]", text):
            hits = SPECULATION.findall(sentence)
            if len(hits) >= 2:
                warn.append(f"[警告] 同一句叠加推测词{hits}，删去多余推测：『{sentence.strip()[:40]}』（{loc}）")
    return hard, warn


def scan_spec(data: dict) -> tuple[list[str], list[str]]:
    return scan(iter_spec_texts(data))


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    path = Path(sys.argv[1])
    raw = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".json":
        hard, warn = scan_spec(json.loads(raw))
    else:
        hard, warn = scan(iter_plain_texts(raw))
    for line in hard + warn:
        print(line)
    print(f"硬规则命中 {len(hard)} 处，警告 {len(warn)} 处。")
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main())
