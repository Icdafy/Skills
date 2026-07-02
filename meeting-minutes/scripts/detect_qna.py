#!/usr/bin/env python3
"""Detect likely question-answer structure in Chinese meeting transcripts."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


QUESTION_MARKER = re.compile(r"^\s*(?:问|问题|Q|Question|采访者|访谈人|提问)[:：\.\s]")
ANSWER_MARKER = re.compile(r"^\s*(?:答|回答|A|Answer|受访者|被访谈人|回复)[:：\.\s]")
SPEAKER_LINE = re.compile(r"^\s*[^：:]{1,12}[:：]")
QUESTION_TEXT = re.compile(r"[？?]|(是否|能否|请问|怎么|如何|什么|哪些|多少|为什么|有没有|是否可以)")


def decode_stdin(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-16", "gb18030"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def detect_qna(text: str) -> tuple[bool, dict[str, int]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    question_markers = sum(1 for line in lines if QUESTION_MARKER.search(line))
    answer_markers = sum(1 for line in lines if ANSWER_MARKER.search(line))
    speaker_lines = [line for line in lines if SPEAKER_LINE.search(line)]
    question_like_speaker_lines = sum(1 for line in speaker_lines if QUESTION_TEXT.search(line))

    marker_pairs = min(question_markers, answer_markers)
    alternating_speakers = len(speaker_lines) >= 6 and question_like_speaker_lines >= 2
    likely = marker_pairs >= 1 or alternating_speakers
    return likely, {
        "question_markers": question_markers,
        "answer_markers": answer_markers,
        "speaker_lines": len(speaker_lines),
        "question_like_speaker_lines": question_like_speaker_lines,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect whether a transcript likely contains Q&A turns.")
    parser.add_argument("input", nargs="?", help="Input text file. Reads stdin when omitted.")
    parser.add_argument("--encoding", default="utf-8", help="Input encoding, default utf-8.")
    parser.add_argument("--quiet", action="store_true", help="Only set exit status: 0 detected, 1 not detected.")
    args = parser.parse_args()

    if args.input:
        text = Path(args.input).read_text(encoding=args.encoding)
    else:
        text = decode_stdin(sys.stdin.buffer.read())

    likely, stats = detect_qna(text)
    if not args.quiet:
        verdict = "QNA_DETECTED" if likely else "NO_QNA_DETECTED"
        details = " ".join(f"{key}={value}" for key, value in stats.items())
        print(f"{verdict} {details}")
    return 0 if likely else 1


if __name__ == "__main__":
    raise SystemExit(main())
