#!/usr/bin/env python3
"""Conservative cleanup for Chinese meeting transcripts.

This script normalizes whitespace and removes filler-only lines. It does not
summarize or delete substantive content.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


FILLER_LINE = re.compile(r"^(嗯+|呃+|啊+|那个+|就是+|然后+|对+|好+|好的+|是的+|谢谢+)[。,.，、\s]*$")
TIMESTAMP_PREFIX = re.compile(
    r"^\s*(?:\[\s*)?(?:\d{1,2}:)?\d{1,2}:\d{2}(?:[.,]\d{1,3})?(?:\s*\])?\s*(?:[-–—>]+\s*)?"
)
TIMESTAMP_ONLY = re.compile(
    r"^\s*(?:\[\s*)?(?:\d{1,2}:)?\d{1,2}:\d{2}(?:[.,]\d{1,3})?(?:\s*\])?\s*$"
)
ASR_NOISE = re.compile(r"^(掌声|音乐|静音|无声|听不清|杂音|噪音)[。,.，、\s]*$")


def decode_stdin(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-16", "gb18030"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def clean_text(text: str, strip_timestamps: bool = True) -> str:
    text = text.replace("\ufeff", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t\u3000]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            if lines and lines[-1] != "":
                lines.append("")
            continue
        if strip_timestamps:
            if TIMESTAMP_ONLY.match(line):
                continue
            line = TIMESTAMP_PREFIX.sub("", line).strip()
        if FILLER_LINE.match(line) or ASR_NOISE.match(line):
            continue
        line = re.sub(r"([。！？；])\1+", r"\1", line)
        line = re.sub(r"([，、])\1+", r"\1", line)
        line = re.sub(r"\s+([，。；：！？、])", r"\1", line)
        line = re.sub(r"([（【])\s+", r"\1", line)
        line = re.sub(r"\s+([）】])", r"\1", line)
        lines.append(line)

    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines) + ("\n" if lines else "")


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean a Chinese meeting transcript conservatively.")
    parser.add_argument("input", nargs="?", help="Input text file. Reads stdin when omitted.")
    parser.add_argument("-o", "--output", help="Output file. Writes stdout when omitted.")
    parser.add_argument("--encoding", default="utf-8", help="Input/output encoding, default utf-8.")
    parser.add_argument(
        "--keep-timestamps",
        action="store_true",
        help="Keep ASR timestamps instead of stripping them from line starts.",
    )
    args = parser.parse_args()

    if args.input:
        text = Path(args.input).read_text(encoding=args.encoding)
    else:
        text = decode_stdin(sys.stdin.buffer.read())

    cleaned = clean_text(text, strip_timestamps=not args.keep_timestamps)

    if args.output:
        Path(args.output).write_text(cleaned, encoding=args.encoding)
    else:
        sys.stdout.buffer.write(cleaned.encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
