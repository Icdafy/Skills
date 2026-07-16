#!/usr/bin/env python3
"""Verify that every number in the minutes traces back to the transcript.

Modes
-----
Verify (default):
    fact_check.py minutes.txt --transcript transcript.txt [more transcripts...]
    Extracts salient numeric facts (amounts with 万/亿 scales, percentages,
    decimals, multi-digit figures, dates) from the minutes body and requires
    each one to appear in at least one transcript, either verbatim or as the
    same canonical value written differently (3000万 == 三千万 == 0.3亿,
    15% == 百分之十五). Unmatched numbers are reported as suspected
    fabrications or rewrites and the check fails.

Compare:
    fact_check.py --compare a.txt b.txt
    Cross-checks two independent transcriptions of the same recording and
    lists numeric values present in one but not the other. Use for the
    dual-engine high-fidelity mode; mismatches should be marked 待核.

Metadata lines (会议时间：/访谈时间：…) come from the user, not the
recording, and are exempt. Tokens already marked 待核 nearby are skipped.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import sys

INDENT = "　　"
METADATA_PREFIXES = (
    "会议时间：", "会议地点：", "参会范围：",
    "访谈时间：", "访谈地点：", "访谈对象：", "访谈人员：",
)

CN_DIGITS = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
             "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
CN_UNITS = {"十": 10, "百": 100, "千": 1000}
CN_BIG = {"万": 10**4, "亿": 10**8}
SCALES = {
    "千": 1e3, "万": 1e4, "十万": 1e5, "百万": 1e6, "千万": 1e7,
    "亿": 1e8, "十亿": 1e9, "百亿": 1e10, "千亿": 1e11, "万亿": 1e12,
}

ARABIC_TOKEN = re.compile(
    r"\d+(?:\.\d+)?(?:万亿|千亿|百亿|十亿|千万|百万|十万|亿|万|千)?(?:多|余)?%?"
)
CN_NUMBER_TOKEN = re.compile(
    r"[零一二两三四五六七八九十百千]*[一二两三四五六七八九十百千](?:点[零一二三四五六七八九]+)?[万亿]+"
)
PERCENT_CN_TOKEN = re.compile(
    r"百分之[零一二两三四五六七八九十百点]+|[零一二两三四五六七八九十百]+(?:点[零一二三四五六七八九]+)?个百分点"
)
HEADING_MARK = re.compile(r"^(?:[一二三四五六七八九十]+、|（[一二三四五六七八九十]+）|\d+\.|（\d+）)")


@dataclass
class Token:
    raw: str
    kind: str  # "value" or "percent"
    value: float | None
    line_number: int
    context: str


FULLWIDTH_MAP = str.maketrans("０１２３４５６７８９．％", "0123456789.%")


def normalize(text: str) -> str:
    # Deliberately narrow: full-width digits/percent only. NFKC would also
    # rewrite the ideographic-space indent and full-width colons, breaking
    # metadata-line detection.
    text = text.translate(FULLWIDTH_MAP).replace("﹪", "%")
    # Drop thousands separators inside digit groups: 1,234,567 -> 1234567
    text = re.sub(r"(?<=\d)[,，](?=\d{3})", "", text)
    return text


def parse_cn_int(text: str) -> float | None:
    """Parse an integer written in Chinese numerals, handling 亿/万 sections."""
    if not text:
        return None
    for big_char, big_value in (("亿", 10**8), ("万", 10**4)):
        if big_char in text:
            left, _, right = text.partition(big_char)
            left_value = parse_cn_int(left) if left else None
            right_value = parse_cn_int(right) if right else 0.0
            if left_value is None or right_value is None:
                return None
            return left_value * big_value + right_value
    total = 0.0
    num = 0.0
    for char in text:
        if char in CN_DIGITS:
            num = num * 10 + CN_DIGITS[char]
        elif char in CN_UNITS:
            total += (num if num else 1) * CN_UNITS[char]
            num = 0.0
        else:
            return None
    return total + num


def parse_cn_number(text: str) -> float | None:
    """Parse Chinese numerals incl. decimals and trailing scales (三点五亿)."""
    multiplier = 1.0
    while text and text[-1] in CN_BIG:
        multiplier *= CN_BIG[text[-1]]
        text = text[:-1]
    if not text:
        return None
    if "点" in text:
        head, _, tail = text.partition("点")
        head_value = parse_cn_int(head) if head else 0.0
        if head_value is None or not tail or any(c not in CN_DIGITS for c in tail):
            return None
        fraction = sum(CN_DIGITS[c] * 10 ** -(i + 1) for i, c in enumerate(tail))
        return (head_value + fraction) * multiplier
    value = parse_cn_int(text)
    return value * multiplier if value is not None else None


def parse_arabic(raw: str) -> tuple[float | None, str]:
    kind = "percent" if raw.endswith("%") else "value"
    body = raw.rstrip("%").replace("多", "").replace("余", "")
    match = re.match(r"(\d+(?:\.\d+)?)(.*)", body)
    if not match:
        return None, kind
    value = float(match.group(1))
    scale = match.group(2)
    if scale:
        if scale not in SCALES:
            return None, kind
        value *= SCALES[scale]
    return value, kind


def salient(raw: str) -> bool:
    """Keep tokens worth verifying; drop noisy bare small numbers."""
    if raw.endswith("%") or "百分之" in raw or "个百分点" in raw:
        return True
    if any(unit in raw for unit in ("万", "亿", "千")):
        return True
    digits = re.sub(r"\D", "", raw)
    if "." in raw:
        return True
    return len(digits) >= 2


def extract_tokens(text: str, *, body_only: bool) -> list[Token]:
    tokens: list[Token] = []
    lines = text.splitlines()
    for line_number, line in enumerate(lines, start=1):
        content = line.removeprefix(INDENT).strip()
        if not content:
            continue
        if body_only and content.startswith(METADATA_PREFIXES):
            continue
        searchable = HEADING_MARK.sub("", content) if body_only else content
        spans: list[tuple[int, int, str]] = []
        for pattern in (ARABIC_TOKEN, CN_NUMBER_TOKEN, PERCENT_CN_TOKEN):
            for match in pattern.finditer(searchable):
                overlapped = any(
                    match.start() < end and match.end() > start for start, end, _ in spans
                )
                if not overlapped:
                    spans.append((match.start(), match.end(), match.group()))
        for start, end, raw in sorted(spans):
            if body_only and "待核" in searchable[end:end + 8]:
                continue
            if raw.startswith("百分之"):
                value = parse_cn_percent(raw)
                kind = "percent"
            elif raw.endswith("个百分点"):
                value = parse_cn_number(raw.removesuffix("个百分点"))
                kind = "percent"
            elif raw[0].isdigit():
                if body_only and not salient(raw):
                    continue
                value, kind = parse_arabic(raw)
            else:
                value = parse_cn_number(raw)
                kind = "value"
            context_start = max(0, start - 12)
            context = searchable[context_start:min(len(searchable), end + 12)]
            tokens.append(Token(raw=raw, kind=kind, value=value,
                                line_number=line_number, context=context))
    return tokens


def parse_cn_percent(raw: str) -> float | None:
    body = raw.removeprefix("百分之")
    if "点" in body:
        head, _, tail = body.partition("点")
        head_value = parse_cn_int(head) if head else 0.0
        if head_value is None or any(c not in CN_DIGITS for c in tail):
            return None
        return head_value + sum(CN_DIGITS[c] * 10 ** -(i + 1) for i, c in enumerate(tail))
    return parse_cn_int(body)


def values_match(a: float, b: float) -> bool:
    if a == b:
        return True
    larger = max(abs(a), abs(b))
    return larger > 0 and abs(a - b) / larger < 1e-9


def verify(minutes_path: Path, transcript_paths: list[Path], allow: list[str]) -> int:
    minutes_text = normalize(minutes_path.read_text(encoding="utf-8-sig"))
    transcripts = [normalize(p.read_text(encoding="utf-8-sig")) for p in transcript_paths]
    transcript_blob = "\n".join(transcripts)
    transcript_tokens = extract_tokens(transcript_blob, body_only=False)
    transcript_values = [(t.kind, t.value) for t in transcript_tokens if t.value is not None]
    allowed = {normalize(item) for item in allow}

    unmatched: list[Token] = []
    checked = 0
    for token in extract_tokens(minutes_text, body_only=True):
        checked += 1
        if token.raw in allowed:
            continue
        digits = re.sub(r"[%万亿千多余]", "", token.raw)
        if token.raw in transcript_blob or (digits and digits in transcript_blob):
            continue
        if token.value is not None and any(
            kind == token.kind and value is not None and values_match(value, token.value)
            for kind, value in transcript_values
        ):
            continue
        unmatched.append(token)

    print(f"共核对 {checked} 个数字事实，转录稿来源 {len(transcript_paths)} 份。")
    if unmatched:
        print("以下数字在转录稿中找不到依据（疑似改写、误转或幻觉），"
              "必须逐一人工核实，或改为转录稿原文，或标注“待核”：")
        for token in unmatched:
            print(f"- 第 {token.line_number} 行「{token.raw}」，上下文：…{token.context}…")
        return 1
    print("数字事实核对通过：纪要中的数字均可在转录稿中找到依据。")
    return 0


def compare(path_a: Path, path_b: Path) -> int:
    def value_set(path: Path) -> dict[tuple[str, float], Token]:
        text = normalize(path.read_text(encoding="utf-8-sig"))
        result: dict[tuple[str, float], Token] = {}
        for token in extract_tokens(text, body_only=False):
            if token.value is not None and salient(token.raw):
                result.setdefault((token.kind, round(token.value, 6)), token)
        return result

    values_a, values_b = value_set(path_a), value_set(path_b)
    only_a = [tok for key, tok in values_a.items() if key not in values_b]
    only_b = [tok for key, tok in values_b.items() if key not in values_a]
    print(f"交叉核对：{path_a.name} 提取 {len(values_a)} 个数值，"
          f"{path_b.name} 提取 {len(values_b)} 个数值。")
    if not only_a and not only_b:
        print("两份转录稿的数字完全一致。")
        return 0
    for name, only in ((path_a.name, only_a), (path_b.name, only_b)):
        if only:
            print(f"仅出现在 {name} 中的数字（写入纪要前应回听录音或标注“待核”）：")
            for token in only:
                print(f"- 「{token.raw}」，上下文：…{token.context}…")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("minutes", nargs="?", type=Path, help="minutes text file to verify")
    parser.add_argument("--transcript", nargs="+", type=Path, default=[],
                        help="one or more transcript .txt files serving as the factual base")
    parser.add_argument("--compare", nargs=2, type=Path, metavar=("A", "B"),
                        help="cross-check two transcripts of the same recording")
    parser.add_argument("--allow", action="append", default=[],
                        help="a number token confirmed by the user or by explicit "
                             "reasoning (e.g. --allow 2025); may be repeated")
    args = parser.parse_args()

    if args.compare:
        for path in args.compare:
            if not path.is_file():
                parser.error(f"找不到文件：{path}")
        return compare(args.compare[0], args.compare[1])

    if not args.minutes or not args.transcript:
        parser.error("核对模式需要：fact_check.py <纪要.txt> --transcript <转录稿.txt>")
    if not args.minutes.is_file():
        parser.error(f"找不到纪要文件：{args.minutes}")
    for path in args.transcript:
        if not path.is_file():
            parser.error(f"找不到转录稿：{path}")
    return verify(args.minutes, args.transcript, args.allow)


if __name__ == "__main__":
    sys.exit(main())
