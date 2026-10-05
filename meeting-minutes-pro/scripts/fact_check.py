#!/usr/bin/env python3
"""Verify that every number in the minutes traces back to the transcript.

Modes
-----
Verify (default):
    fact_check.py minutes.txt --transcript transcript.txt [more transcripts...]
    Extracts salient numeric facts (amounts with 万/亿 scales, percentages,
    decimals, multi-digit figures, months/days, years) from the minutes body
    and requires each one to appear in at least one transcript, either
    verbatim or as the same canonical value written differently
    (3000万 == 三千万 == 0.3亿, 15% == 百分之十五, 3月15日 == 三月十五号,
    2025 == 二〇二五). Unmatched numbers are reported as suspected
    fabrications or rewrites and the check fails.

    --show-matches additionally prints the transcript-side context for every
    verified token so a human can confirm the number was not lifted from an
    unrelated statement (e.g. a 30% that was market share, not gross margin).

    --glossary/--term list hotword terms; terms that appear in the minutes
    but never in the transcript are reported as rewrite advisories (the
    drafting step may have corrected a mis-transcribed name to the glossary
    spelling — usually intended, but each case must be confirmed).

Compare:
    fact_check.py --compare a.txt b.txt
    Cross-checks two independent transcriptions of the same recording and
    lists numeric values present in one but not the other. Use for the
    dual-engine high-fidelity mode; mismatches must be resolved by
    re-listening — 待核 annotations are no longer allowed in the minutes.

Metadata lines (会议时间：/访谈时间：…) come from the user, not the
recording, and are exempt. Tokens marked 待核 nearby are still skipped for
legacy documents only.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import sys
from format_spec import FIRST_LEVEL, SECOND_LEVEL, THIRD_LEVEL, FOURTH_LEVEL

INDENT = "　　"
METADATA_PREFIXES = (
    "会议时间：", "会议地点：", "参会范围：",
    "访谈时间：", "访谈地点：", "访谈对象：", "访谈人员：",
)

CN_DIGITS = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
             "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
CN_UNITS = {"十": 10, "百": 100, "千": 1000}
CN_BIG = {"万": 10**4, "亿": 10**8}
SCALES = {
    "千": 1e3, "万": 1e4, "十万": 1e5, "百万": 1e6, "千万": 1e7,
    "亿": 1e8, "十亿": 1e9, "百亿": 1e10, "千亿": 1e11, "万亿": 1e12,
}

ARABIC_TOKEN = re.compile(
    r"[+-]?\d+(?:\.\d+)?(?:万亿|千亿|百亿|十亿|千万|百万|十万|亿|万|千)?(?:多|余)?(?:%|个百分点)?"
)
CN_NUMBER_TOKEN = re.compile(
    r"负?[零〇一二两三四五六七八九十百千]*[一二两三四五六七八九十百千](?:点[零一二三四五六七八九]+)?[万亿]+"
)
PERCENT_CN_TOKEN = re.compile(
    r"负?百分之负?[零〇一二两三四五六七八九十百点]+|负?[零〇一二两三四五六七八九十百]+(?:点[零一二三四五六七八九]+)?个百分点"
)
# Transcript-side colloquial percent forms (recognition targets only — the
# minutes side writes the normalized form): 三成==30%、三成半==35%、
# 3个点/三个点需裁决、千分之五==0.5%、万分之五==0.05%. The 成 pattern excludes
# common non-numeric continuations (成员/成本/成立…) via lookahead.
CN_CHENG_TOKEN = re.compile(r"[一二两三四五六七八九十]成[半多]?(?![员本立效品色果])")
POINT_TOKEN = re.compile(r"(?:\d+(?:\.\d+)?|[一二两三四五六七八九十半]{1,3})个点")
FRACTION_CN_TOKEN = re.compile(r"[千万]分之[零〇一二两三四五六七八九十百点]+")
# Transcript-side only: bare Chinese numerals without a 万/亿 scale (五千,
# 十五, digit strings like 二〇二五) are harvested as match targets so that
# minutes written in Arabic digits still find their spoken counterparts.
# Too noisy for the minutes side.
CN_RUN_TOKEN = re.compile(
    r"[零〇一二两三四五六七八九十百千]{2,}(?:点[零一二三四五六七八九]+)?"
)
# Calendar dates on both sides: single-digit months and days matter even
# though bare small numbers are otherwise dropped as noise. Year digit
# strings exclude 两: real years are never written with it (二〇二五, 九八),
# while colloquial approximations (两三年, 一两年) are and must not be
# force-verified as numbers.
DATE_TOKEN = re.compile(
    r"(?:(?P<year>\d{2,4}|[零〇一二三四五六七八九]{2,4})年)?"
    r"(?P<month>1[0-2]|[1-9]|十[一二]?|[一二两三四五六七八九])月"
    r"(?:(?P<day>3[01]|[12]?\d|[一二三四五六七八九十]{1,3})[日号])?"
)
CN_YEAR_TOKEN = re.compile(r"[零〇一二三四五六七八九]{2,4}年")
HEADING_MARK = re.compile("|".join(p.pattern for p in (FIRST_LEVEL, SECOND_LEVEL, THIRD_LEVEL, FOURTH_LEVEL)))


@dataclass
class Token:
    raw: str
    kind: str  # "value", "percent", "month", or "day"
    value: float | None
    line_number: int
    context: str
    unit: str = ""
    offset: int = 0


FULLWIDTH_MAP = str.maketrans("０１２３４５６７８９．％－＋", "0123456789.%-+")

# 语境绑定：纪要侧数字上下文与转录稿依据上下文的 bigram 相似度低于该值时，
# 标记“疑似移用”（数字存在但可能安到了无关表述上），供人工优先确认。
CONTEXT_BINDING_MIN = 0.2


def _bigrams(text: str) -> set[str]:
    cleaned = re.sub(r"[^\w]", "", text)
    if len(cleaned) < 2:
        return {cleaned} if cleaned else set()
    return {cleaned[i:i + 2] for i in range(len(cleaned) - 1)}


def context_binding(minutes_context: str, evidence_context: str, raw: str) -> float:
    """Similarity of the two contexts with the figures themselves removed, so a
    shared number cannot inflate the score."""
    left = re.sub(r"[\d.%]+", "", minutes_context.replace(raw, ""))
    right = re.sub(r"[\d.%]+", "", evidence_context.replace(raw, ""))
    grams_left, grams_right = _bigrams(left), _bigrams(right)
    if not grams_left or not grams_right:
        return 0.0
    return len(grams_left & grams_right) / min(len(grams_left), len(grams_right))


def normalize(text: str) -> str:
    # Deliberately narrow: full-width digits/percent only. NFKC would also
    # rewrite the ideographic-space indent and full-width colons, breaking
    # metadata-line detection.
    text = text.translate(FULLWIDTH_MAP).replace("﹪", "%").replace("−", "-")
    text = re.sub(r"负(?=\d)", "-", text)
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
    if text.startswith("负"):
        value = parse_cn_number(text[1:])
        return -value if value is not None else None
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
    kind = "percentage_point" if raw.endswith("个百分点") else ("percent" if raw.endswith("%") else "value")
    body = raw.removesuffix("个百分点").rstrip("%").replace("多", "").replace("余", "")
    match = re.match(r"([+-]?\d+(?:\.\d+)?)(.*)", body)
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


def _context_of(searchable: str, start: int, end: int) -> str:
    context_start = max(0, start - 12)
    return searchable[context_start:min(len(searchable), end + 12)]


def _parse_date_component(text: str) -> float | None:
    if text.isdigit():
        return float(text)
    return parse_cn_int(text)


# Units are recorded independently of the raw numeric spelling, so 万/亿
# equivalence remains possible while 元/美元 and 家/台 cannot silently match.
UNIT_PATTERN = r"(?:人民币|美元|美金|欧元|港元|港币|日元|英镑|摄氏度|毫米|厘米|公里|千米|公斤|千克|毫秒|分钟|小时|微米|纳米|个月|元|家|台|人|年|天|日|月|秒|米|吨|颗|套|件|个|倍|栋)"
UNIT_RE = re.compile(UNIT_PATTERN)
CN_QUANTITY_TOKEN = re.compile(r"负?[零〇一二两三四五六七八九十百千]+(?:点[零一二三四五六七八九]+)?(?=" + UNIT_PATTERN + r")")


def quantity_unit(text: str, start: int, end: int) -> str:
    match = UNIT_RE.match(text[end:])
    unit = match.group() if match else ""
    if not unit:
        prefix = re.search(r"(人民币|美元|美金|欧元|港元|港币|日元|英镑)\s*$", text[:start])
        unit = prefix.group(1) if prefix else ""
    return {"元": "CNY", "人民币": "CNY", "美元": "USD", "美金": "USD",
            "欧元": "EUR", "港币": "HKD", "港元": "HKD", "日元": "JPY",
            "英镑": "GBP", "公斤": "千克", "个月": "月"}.get(unit, unit)


def quantitative(token: Token) -> bool:
    return token.value is not None and bool(token.unit or salient(token.raw)
        or token.kind in ("month", "day", "percent", "percentage_point", "ambiguous_point")
        or token.raw.endswith("年"))


def tokens_match(left: Token, right: Token) -> bool:
    return (left.value is not None and right.value is not None
            and left.kind == right.kind and values_match(left.value, right.value)
            and (not left.unit or not right.unit or left.unit == right.unit))


def match_occurrences(source: list[Token], target: list[Token]) -> list[int | None]:
    """One target occurrence cannot cover two source facts in a window.

    Prefer the closest context among type-compatible values. This is a lexical
    aid only: subject/time/conditions still require recorded occurrence review.
    """
    used: set[int] = set()
    matches = []
    for token in source:
        candidates = [i for i, other in enumerate(target) if i not in used and tokens_match(token, other)]
        best = max(candidates, key=lambda i: context_binding(token.context, target[i].context, token.raw), default=None)
        matches.append(best)
        if best is not None:
            used.add(best)
    return matches


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

        # Calendar dates claim their spans first so 3月15日 yields month/day
        # tokens instead of noisy bare digits, on both sides.
        claimed: list[tuple[int, int]] = []
        date_tokens: list[Token] = []
        for match in DATE_TOKEN.finditer(searchable):
            claimed.append((match.start(), match.end()))
            if body_only and "待核" in searchable[match.end():match.end() + 8]:
                continue
            context = _context_of(searchable, match.start(), match.end())
            year = match.group("year")
            if year:
                date_tokens.append(Token(raw=year + "年", kind="value",
                                         value=_parse_date_component(year),
                                         line_number=line_number, context=context))
            month = match.group("month")
            date_tokens.append(Token(raw=month + "月", kind="month",
                                     value=_parse_date_component(month),
                                     line_number=line_number, context=context))
            day = match.group("day")
            if day:
                day_raw = searchable[match.start("day"):match.end("day") + 1]
                date_tokens.append(Token(raw=day_raw, kind="day",
                                         value=_parse_date_component(day),
                                         line_number=line_number, context=context))
        for match in CN_YEAR_TOKEN.finditer(searchable):
            if any(match.start() < end and match.end() > start for start, end in claimed):
                continue
            claimed.append((match.start(), match.end()))
            if body_only and "待核" in searchable[match.end():match.end() + 8]:
                continue
            date_tokens.append(Token(raw=match.group(), kind="value",
                                     value=parse_cn_int(match.group()[:-1]),
                                     line_number=line_number,
                                     context=_context_of(searchable, match.start(), match.end())))

        spans: list[tuple[int, int, str]] = []
        patterns = [ARABIC_TOKEN, CN_NUMBER_TOKEN, PERCENT_CN_TOKEN, CN_QUANTITY_TOKEN]
        if not body_only:
            # Colloquial percent forms claim their spans before the generic
            # patterns split them (3个点 must not decay into a bare 3).
            patterns = [FRACTION_CN_TOKEN, POINT_TOKEN, CN_CHENG_TOKEN] + patterns
            patterns.append(CN_RUN_TOKEN)
        for pattern in patterns:
            for match in pattern.finditer(searchable):
                overlapped = any(
                    match.start() < end and match.end() > start for start, end, _ in spans
                ) or any(
                    match.start() < end and match.end() > start for start, end in claimed
                )
                if not overlapped:
                    spans.append((match.start(), match.end(), match.group()))
        for start, end, raw in sorted(spans):
            if body_only and "待核" in searchable[end:end + 8]:
                continue
            if raw.startswith(("百分之", "负百分之")):
                value = parse_cn_percent(raw)
                kind = "percent"
            elif raw.startswith(("千分之", "万分之")):
                value = parse_cn_fraction(raw)
                kind = "percent"
            elif raw.endswith("个点"):
                value = parse_point(raw)
                kind = "ambiguous_point"
            elif CN_CHENG_TOKEN.fullmatch(raw):
                value = parse_cheng(raw)
                kind = "percent"
            elif raw.endswith("个百分点") and not (raw[0].isdigit() or raw[0] in "+-"):
                value = parse_cn_number(raw.removesuffix("个百分点"))
                kind = "percentage_point"
            elif raw[0].isdigit() or raw[0] in "+-":
                if body_only and not salient(raw) and not quantity_unit(searchable, start, end):
                    continue
                value, kind = parse_arabic(raw)
            else:
                value = parse_cn_number(raw)
                kind = "value"
            # Adjacent Chinese small numerals such as 两三年 are approximate,
            # not the integer 23; leave their wording to the occurrence review.
            if raw in ("两三", "一两", "三四", "四五", "五六", "六七", "七八", "八九"):
                continue
            tokens.append(Token(raw=raw, kind=kind, value=value,
                                line_number=line_number, unit=quantity_unit(searchable, start, end), offset=start,
                                context=_context_of(searchable, start, end)))
        tokens.extend(date_tokens)
    return tokens


def parse_cn_fraction(raw: str) -> float | None:
    """千分之X / 万分之X expressed as percent values (千分之五 == 0.5%)."""
    divisor = 10.0 if raw.startswith("千分之") else 100.0
    value = parse_cn_percent("百分之" + raw[3:])
    return value / divisor if value is not None else None


def parse_point(raw: str) -> float | None:
    """Parse the magnitude of ambiguous X个点; caller preserves its own kind."""
    body = raw.removesuffix("个点")
    if not body:
        return None
    if body == "半":
        return 0.5
    if body[0].isdigit():
        try:
            return float(body)
        except ValueError:
            return None
    return parse_cn_int(body)


def parse_cheng(raw: str) -> float | None:
    """Colloquial X成 as a percent value (三成 == 30%, 三成半 == 35%)."""
    half = raw.endswith("半")
    body = raw.rstrip("半多").removesuffix("成")
    value = parse_cn_int(body)
    if value is None:
        return None
    return value * 10 + (5 if half else 0)


def parse_cn_percent(raw: str) -> float | None:
    negative = raw.startswith("负") or "之负" in raw
    if negative:
        value = parse_cn_percent(raw.replace("负", ""))
        return -value if value is not None else None
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


def collect_terms(glossary_paths: list[Path], terms: list[str]) -> list[str]:
    collected: list[str] = []
    for path in glossary_paths:
        collected.extend(path.read_text(encoding="utf-8-sig").split())
    collected.extend(terms)
    return [term for term in dict.fromkeys(collected) if len(term) >= 2]


def verify(
    minutes_path: Path,
    transcript_paths: list[Path],
    allow: list[str],
    terms: list[str] | None = None,
    show_matches: bool = False,
) -> int:
    minutes_text = normalize(minutes_path.read_text(encoding="utf-8-sig"))
    transcripts = [normalize(p.read_text(encoding="utf-8-sig")) for p in transcript_paths]
    transcript_blob = "\n".join(transcripts)
    transcript_tokens = extract_tokens(transcript_blob, body_only=False)
    transcript_value_tokens = [t for t in transcript_tokens if t.value is not None]
    allowed = {normalize(item) for item in allow}

    def blob_context(position: int, length: int) -> str:
        start = max(0, position - 14)
        end = min(len(transcript_blob), position + length + 14)
        return transcript_blob[start:end].replace("\n", " ")

    unmatched: list[Token] = []
    matched: list[tuple[Token, str]] = []
    checked = 0
    for token in extract_tokens(minutes_text, body_only=True):
        checked += 1
        if token.raw in allowed:
            continue
        candidates = [candidate for candidate in transcript_value_tokens
                      if tokens_match(token, candidate)]
        best = max(candidates, key=lambda x: context_binding(token.context, x.context, token.raw), default=None)
        evidence = best.context if best is not None else None
        if evidence is None:
            unmatched.append(token)
        else:
            matched.append((token, evidence))

    print(f"共核对 {checked} 个数字事实，转录稿来源 {len(transcript_paths)} 份。")
    scored = [
        (token, evidence, context_binding(token.context, evidence, token.raw))
        for token, evidence in matched
    ]
    suspicious = [item for item in scored if item[2] < CONTEXT_BINDING_MIN]
    if show_matches and matched:
        print("已核对数字的转录稿依据（请人工确认数字未被移用到无关表述；"
              "低语境相似度条目排在前面，优先确认）：")
        for token, evidence, binding in sorted(scored, key=lambda item: item[2]):
            marker = "［低语境相似度，疑似移用］" if binding < CONTEXT_BINDING_MIN else ""
            # "←" stays inside GBK so Windows consoles do not choke on it.
            print(f"- 第 {token.line_number} 行「{token.raw}」{marker} ← …{evidence}…")
    elif suspicious:
        print(f"提示：{len(suspicious)} 处数字的纪要语境与转录稿依据语境相似度较低"
              "（疑似移用），建议加 --show-matches 逐条确认。")

    if terms:
        body_lines = [
            line.removeprefix(INDENT).strip()
            for line in minutes_text.splitlines()
            if line.strip() and not line.removeprefix(INDENT).strip().startswith(METADATA_PREFIXES)
        ]
        body_text = "\n".join(body_lines)
        rewritten = [
            term for term in terms
            if term in body_text and term not in transcript_blob
        ]
        if rewritten:
            print("术语改写提示（不计入通过/失败）：以下热词出现在纪要正文但未出现在"
                  "转录稿原文，多为对误转词的规范改写，请逐项确认改写对象无误：")
            for term in rewritten:
                print(f"- 「{term}」")

    if unmatched:
        print("以下数字在转录稿中找不到依据（疑似改写、误转或幻觉），"
              "必须逐一处理：回听录音确认、改回转录稿原文，或经用户确认后用 "
              "--allow 显式放行；不得在纪要中以“待核”标注代替处理：")
        for token in unmatched:
            print(f"- 第 {token.line_number} 行「{token.raw}」，上下文：…{token.context}…")
        return 1
    print("数字事实核对通过：纪要中的数字均可在转录稿中找到依据。")
    return 0


def compare(path_a: Path, path_b: Path) -> int:
    def tokens_of(path: Path) -> list[Token]:
        text = normalize(path.read_text(encoding="utf-8-sig"))
        return [
            token for token in extract_tokens(text, body_only=False)
            if token.value is not None and (
                quantitative(token)
            )
        ]

    def value_set(tokens: list[Token]) -> dict[tuple[str, float], Token]:
        result: dict[tuple[str, float], Token] = {}
        for token in tokens:
            result.setdefault((token.kind, round(token.value, 6)), token)
        return result

    def first_occurrence_order(tokens: list[Token]) -> list[tuple[tuple, str]]:
        seen: set[tuple] = set()
        order: list[tuple[tuple, str]] = []
        for token in tokens:
            key = (token.kind, round(token.value, 6))
            if key not in seen:
                seen.add(key)
                order.append((key, token.raw))
        return order

    tokens_a, tokens_b = tokens_of(path_a), tokens_of(path_b)
    values_a, values_b = value_set(tokens_a), value_set(tokens_b)
    only_a = [tok for key, tok in values_a.items() if key not in values_b]
    only_b = [tok for key, tok in values_b.items() if key not in values_a]
    print(f"交叉核对：{path_a.name} 提取 {len(values_a)} 个数值，"
          f"{path_b.name} 提取 {len(values_b)} 个数值。")
    if not only_a and not only_b:
        # Same value sets can still hide a swap; compare first-occurrence order
        # (mirrors the order-sensitive check in refine_transcript).
        order_a = first_occurrence_order(tokens_a)
        order_b = first_occurrence_order(tokens_b)
        if [key for key, _ in order_a] != [key for key, _ in order_b]:
            print("两份转录稿的数字集合一致，但出现顺序不同"
                  "（疑似同组数字被安到不同表述上，须回听确认指代）：")
            print(f"- {path_a.name}：{'、'.join(raw for _, raw in order_a)}")
            print(f"- {path_b.name}：{'、'.join(raw for _, raw in order_b)}")
            return 1
        from refine_transcript import compare_texts
        differences = compare_texts(path_a.read_text(encoding="utf-8-sig"), path_b.read_text(encoding="utf-8-sig"), [])
        if differences:
            print("数值相同但存在单位、限定词或事实实例差异，须回听确认：")
            for difference in differences:
                print(f"- {difference['category']}：{difference['funasr_only']} / {difference['qwen_only']}")
            return 1
        print("两份转录稿的数值及已实现比较项未发现差异，仍须核对语义。")
        return 0
    for name, only in ((path_a.name, only_a), (path_b.name, only_b)):
        if only:
            print(f"仅出现在 {name} 中的数字（写入纪要前必须回听录音确认）：")
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
    parser.add_argument("--glossary", action="append", type=Path, default=[],
                        help="hotword file whose terms are checked for rewrite "
                             "advisories; may be repeated")
    parser.add_argument("--term", action="append", default=[],
                        help="a single hotword term for rewrite advisories; may be repeated")
    parser.add_argument("--show-matches", action="store_true",
                        help="print the transcript context of every verified number "
                             "so misplaced figures can be spotted manually")
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
    for path in args.glossary:
        if not path.is_file():
            parser.error(f"找不到术语文件：{path}")
    terms = collect_terms(args.glossary, args.term)
    return verify(args.minutes, args.transcript, args.allow,
                  terms=terms, show_matches=args.show_matches)


if __name__ == "__main__":
    sys.exit(main())
