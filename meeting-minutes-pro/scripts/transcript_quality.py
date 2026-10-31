"""Bounded text repetition cues, not a hallucination or audio-accuracy verdict."""
from __future__ import annotations

from collections import Counter
import re


def repetition_flags(text: str) -> list[dict]:
    """Flag dense local loops without deleting text or selecting a correction.

    Examine 64 alphanumeric characters at a time with a 32-character stride
    and six fixed n-gram lengths. Ordinary two/three-fold emphasis is retained.
    Window offsets refer to the original text: zero-based, end exclusive.
    """
    indexed = [(char, index) for index, char in enumerate(text) if char.isalnum()]
    compact = ''.join(char for char, _ in indexed)
    flags = []
    last_end = {}
    for start in range(0, len(compact), 32):
        window = compact[start:start + 64]
        if len(window) < 12:
            continue
        candidates = []
        for width in (2, 3, 4, 6, 8, 12):
            counts = Counter(window[i:i + width] for i in range(len(window) - width + 1))
            for phrase, count in counts.items():
                if count < 4:
                    continue
                positions = [match.start() for match in re.finditer(re.escape(phrase), window)]
                count = len(positions)  # Non-overlapping occurrences only.
                if count < 4:
                    continue
                run = longest_run = 1
                for previous, current in zip(positions, positions[1:]):
                    run = run + 1 if current == previous + width else 1
                    longest_run = max(longest_run, run)
                span = positions[-1] + width - positions[0]
                loop = longest_run >= 4 and longest_run * width >= 12
                dense = count >= 6 and span <= 48 and count * width / span >= 0.5
                if loop or dense:
                    candidates.append((width, count * width, phrase, count,
                                       start + positions[0], start + positions[-1] + width))
        if not candidates:
            continue
        _, _, phrase, count, begin, end = max(candidates)
        original_begin, original_end = indexed[begin][1], indexed[end - 1][1] + 1
        if original_begin < last_end.get(phrase, -1):
            continue
        last_end[phrase] = original_end
        flags.append({
            'code': 'suspected_repetition', 'severity': 'warning',
            'message': '短窗口内出现密集文字重复；可能是真实重复或识别循环，'
                       '须结合对应音频复核，不自动删除或认定为幻觉。',
            'repeated_text': phrase, 'occurrences': count,
            'window': {'start_character': original_begin, 'end_character': original_end,
                       'offset_basis': 'original_text_zero_based_end_exclusive'},
        })
    return flags
