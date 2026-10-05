"""Shared text rules; keep standalone copies in the four consuming skills.

Edit this canonical copy, then run tools/check_shared_scripts.py --sync.
Font names and sizes remain in each renderer's existing format constants.
"""
import re


def parenthesized_spans(text):
    """Return merged [start, end) spans of paired round parentheses, nested too.

    Both Chinese and ASCII delimiters are included. Unmatched delimiters do
    not reformat the remaining text.
    """
    stack, spans = [], []
    pairs = {'）': '（', ')': '('}
    for index, char in enumerate(text):
        if char in '（(':
            stack.append((char, index))
        elif char in pairs and stack and stack[-1][0] == pairs[char]:
            _, start = stack.pop()
            spans.append((start, index + 1))
    merged = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


SERIAL = r'(?:\d+|[一二三四五六七八九十百零〇两]+)'
ATTACHMENT_PREFIX = re.compile(rf'^附件\s*(?:[:：]\s*|{SERIAL}\s*[.、．:：]\s*)')


def normalize_attachment_name(name):
    """Remove attachment labels/serials, book-title marks and terminal punctuation."""
    cleaned = str(name).strip()
    while ATTACHMENT_PREFIX.match(cleaned):
        cleaned = ATTACHMENT_PREFIX.sub('', cleaned, count=1)
    cleaned = re.sub(rf'^(?:{SERIAL}\s*[.、．:：]|[（(]{SERIAL}[）)])\s*', '', cleaned)
    cleaned = cleaned.replace('《', '').replace('》', '')
    # Closing parentheses are part of names such as 实施方案（试行）.
    return cleaned.strip().rstrip('。；;，,、.．：:！!？?… \t\r\n')


def attachment_lines(names):
    """A single item has no serial; multiple items use 附件1.XXX, 附件2.XXX."""
    names = [name for source in names if (name := normalize_attachment_name(source))]
    if len(names) == 1:
        return ['附件：' + names[0]]
    return [f'附件{index}.{name}' for index, name in enumerate(names, 1)]
