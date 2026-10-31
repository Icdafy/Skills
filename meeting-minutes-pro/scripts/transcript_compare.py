#!/usr/bin/env python3
"""Conservative phrase-level ASR difference screening, not semantic adjudication.

Equivalent numeric spellings are normalised before alignment. Findings preserve
both readings for review; they never choose a winner or modify a transcript.
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import re

import fact_check


NUMBER = re.compile(r"⟦[^⟧]+⟧")
BOUNDARY = re.compile(r"[，,。；;！？!?\n]+|(?<!\d)\.(?!\d)")
FILLERS = {"嗯", "嗯嗯", "呃", "啊", "对", "对的", "是的", "好的", "好", "是"}
STATE = re.compile(
    r"尚未|还未|没有|不能|不可|无法|禁止|取消|终止|暂停|已经|已|"
    r"计划|预计|准备|拟|正在|完成|不|未(?!来)|无"
)
SCOPE = re.compile(
    r"去年|今年|明年|前年|后年|上年|本年|次年|上月|本月|下月|"
    r"此前|目前|未来|不超过|不低于|不少于|不含|至少|最多|"
    r"大约|左右|以上|以下|超过|上限|下限|约"
)
MARKER_ALIASES = {"已经": "已", "大约": "约", "上年": "去年", "本年": "今年"}


def compact(text: str) -> str:
    return re.sub(r"[^\w⟦⟧:.-]", "", text).casefold()


def canonical(text: str) -> str:
    """Normalise only quantitative spellings understood by the fact checker.

    Use each token's actual span; replacing every occurrence of a raw numeral
    would also change names such as 三一重工 when the phrase later says 三台.
    Date components may lack offsets, so locate an unused matching span then.
    """
    text = fact_check.normalize(text)
    replacements = []
    for token in fact_check.extract_tokens(text, body_only=False):
        if not fact_check.quantitative(token):
            continue
        candidates = [token.offset] + [match.start() for match in re.finditer(re.escape(token.raw), text)]
        for start in candidates:
            end = start + len(token.raw)
            if (text[start:end] == token.raw
                    and not any(start < b and end > a for a, b, _ in replacements)):
                # The caller compares numeric units separately. Remove only
                # the unit attached to this quantity from lexical comparison,
                # so 美元/美金, 公斤/千克 and an implicit 元 do not look like a
                # different business metric. Unrelated unit words stay intact.
                suffix = fact_check.UNIT_RE.match(text, end) if token.unit else None
                if suffix:
                    end = suffix.end()
                elif token.unit:
                    prefix = re.search(r"(?:人民币|美元|美金|欧元|港元|港币|日元|英镑)\s*$", text[:start])
                    if prefix:
                        start = prefix.start()
                marker = f"⟦{token.kind}:{token.value:.12g}⟧"
                replacements.append((start, end, marker))
                break
    for start, end, marker in sorted(replacements, reverse=True):
        text = text[:start] + marker + text[end:]
    return compact(text)


@dataclass(frozen=True)
class Phrase:
    raw: str
    key: str


def phrases(text: str) -> list[Phrase]:
    result = []
    seen = set()
    # Normalise thousands separators before punctuation splitting.
    for raw in BOUNDARY.split(fact_check.normalize(text)):
        raw = raw.strip()
        key = canonical(raw)
        if not key or key in FILLERS or key in seen:
            continue
        seen.add(key)
        result.append(Phrase(raw, key))
    return result


def _ratio(left: str, right: str) -> float:
    # A long numeric placeholder must not outweigh the surrounding words.
    return SequenceMatcher(None, NUMBER.sub("§", left), NUMBER.sub("§", right),
                           autojunk=False).ratio()


def _join(items: list[Phrase]) -> Phrase:
    return Phrase("，".join(item.raw for item in items), "".join(item.key for item in items))


def align(left: list[Phrase], right: list[Phrase]) -> list[tuple[Phrase | None, Phrase | None]]:
    """Order-preserving edit alignment, with exact 1:2 punctuation merges.

    This is lexical alignment, not a claim that two paraphrases mean the same
    thing. ASR punctuation changes should not themselves create missing speech.
    """
    n, m = len(left), len(right)
    cost = [[float("inf")] * (m + 1) for _ in range(n + 1)]
    previous = {}
    cost[0][0] = 0.0
    for i in range(n + 1):
        for j in range(m + 1):
            choices = []
            if i < n and j < m:
                choices.append((1, 1, 1.0 - _ratio(left[i].key, right[j].key)))
            if i < n and j + 1 < m and left[i].key == right[j].key + right[j + 1].key:
                choices.append((1, 2, 0.0))
            if i + 1 < n and j < m and left[i].key + left[i + 1].key == right[j].key:
                choices.append((2, 1, 0.0))
            if i < n:
                choices.append((1, 0, 0.6))
            if j < m:
                choices.append((0, 1, 0.6))
            for a, b, extra in choices:
                value = cost[i][j] + extra
                if value < cost[i + a][j + b]:
                    cost[i + a][j + b] = value
                    previous[i + a, j + b] = (i, j)
    pairs = []
    i, j = n, m
    while i or j:
        a, b = previous[i, j]
        pairs.append((_join(left[a:i]) if a < i else None,
                      _join(right[b:j]) if b < j else None))
        i, j = a, b
    return list(reversed(pairs))


def _markers(pattern: re.Pattern, text: str) -> list[str]:
    return [MARKER_ALIASES.get(value, value) for value in pattern.findall(text)]


def _markers_moved(pattern: re.Pattern, left: str, right: str) -> bool:
    if pattern.sub("", left) != pattern.sub("", right):
        return False
    def bindings(text):
        return [(MARKER_ALIASES.get(match.group(), match.group()),
                 len(pattern.sub("", text[:match.start()])))
                for match in pattern.finditer(text)]
    return bindings(left) != bindings(right)


def _numeric_anchors(text: str) -> list[str]:
    return [NUMBER.sub("", text[:match.start()])[-12:]
            + NUMBER.sub("", text[match.end():])[:8]
            for match in NUMBER.finditer(text)]


def compare_phrases(left_text: str, right_text: str) -> list[dict]:
    """Return review findings in the existing refine conflict schema.

    Numeric/unit comparisons remain the caller's responsibility. No finding means
    these limited rules found no difference, never that the audio is correct.
    """
    left, right = phrases(left_text), phrases(right_text)
    if "".join(p.key for p in left) == "".join(p.key for p in right):
        return []
    findings = []

    def add(category: str, a: Phrase | None, b: Phrase | None) -> None:
        item = {"category": category, "funasr_only": [a.raw] if a else [],
                "qwen_only": [b.raw] if b else []}
        if item not in findings:
            findings.append(item)

    for a, b in align(left, right):
        if a is None or b is None:
            available = a or b
            if NUMBER.search(available.key) or len(available.key) >= 4:
                add("片段遗漏", a, b)
            continue
        if a.key == b.key:
            continue
        if (_markers(STATE, a.key) != _markers(STATE, b.key)
                or _markers_moved(STATE, a.key, b.key)):
            add("否定或状态归属", a, b)
        if (_markers(SCOPE, a.key) != _markers(SCOPE, b.key)
                or _markers_moved(SCOPE, a.key, b.key)):
            add("时间或限定词归属", a, b)
        left_numbers, right_numbers = NUMBER.findall(a.key), NUMBER.findall(b.key)
        left_context, right_context = NUMBER.sub("", a.key), NUMBER.sub("", b.key)
        # Numbers themselves can make unrelated statements appear similar.
        # Remove them before comparing the surrounding object/metric wording.
        contexts = [(left_context, right_context)] + list(zip(_numeric_anchors(a.key), _numeric_anchors(b.key)))
        if (left_numbers and left_numbers == right_numbers
                and any(x != y and min(len(x), len(y)) >= 2 and _ratio(x, y) < 0.9
                        for x, y in contexts)):
            add("数字对象或语境", a, b)
        a_compare, b_compare = NUMBER.sub("§", a.key), NUMBER.sub("§", b.key)
        matcher = SequenceMatcher(None, a_compare, b_compare, autojunk=False)
        # Partial omissions can be a small fraction of a long, otherwise
        # agreeing paragraph. Detect substantive inserted/deleted spans too.
        for tag, i, j, k, l in matcher.get_opcodes():
            if (tag in ("insert", "delete")
                    and max(len(a_compare[i:j].replace("§", "")),
                            len(b_compare[k:l].replace("§", ""))) >= 4):
                add("片段遗漏", a, b)
                break
        if max(len(a.key), len(b.key)) >= 6 and matcher.ratio() < 0.75:
            add("文本差异", a, b)
    return findings
