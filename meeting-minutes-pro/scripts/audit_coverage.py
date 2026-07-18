#!/usr/bin/env python3
"""Mechanically audit that every window of the transcript was triaged.

The minutes workflow requires the drafter to walk the transcript in 5-10
minute windows and decide, window by window, whether the content was folded
into the summary/Q&A or deliberately dropped (greetings, repetition). This
script turns that honor-system step into a checked artifact:

1. Template:
       audit_coverage.py --transcript <stem>.json --make-template coverage.txt
   Writes one line per window with its time range, the salient numbers found
   inside, a text preview, and the placeholder disposition 待判定.

2. The drafter edits coverage.txt, replacing every 待判定 with either
       纳入 <总结/问答中的位置>      or      省略 <原因>

3. Validate:
       audit_coverage.py --transcript <stem>.json --ledger coverage.txt \
           --minutes 会议纪要.txt
   Fails when windows are missing, still undecided, dropped despite carrying
   two or more salient numbers, or when time ranges were tampered with.
   Warns when an included window's numbers never surface in the minutes.

Transcripts without timestamps fall back to fixed-size character blocks.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import fact_check  # noqa: E402
import qa_reconcile  # noqa: E402

LEDGER_LINE = re.compile(r"^窗口\s*(\d+)（([^）]*)）：(纳入|省略|待判定)(.*)$")
DEFAULT_WINDOW_SECONDS = 300.0
DEFAULT_CHARS_PER_WINDOW = 1500
PREVIEW_CHARS = 24
# 纳入位置允许的通用指向；其余位置须与纪要中的某个真实标题有交集。
GENERIC_POSITION_WORDS = ("总结", "概述", "问答", "基本信息", "导语", "全文")


def _bigrams(text: str) -> set[str]:
    cleaned = re.sub(r"[^\w]", "", text)
    if len(cleaned) < 2:
        return {cleaned} if cleaned else set()
    return {cleaned[i:i + 2] for i in range(len(cleaned) - 1)}


def minutes_headings(minutes_text: str) -> list[str]:
    headings: list[str] = []
    for line in minutes_text.splitlines():
        content = line.removeprefix("　　").strip()
        if content and fact_check.HEADING_MARK.match(content):
            headings.append(content)
    return headings


def position_plausible(position: str, headings: list[str]) -> bool:
    """A 纳入 position must point at something real: a generic section word
    or a fragment of an actual heading in the minutes."""
    if any(word in position for word in GENERIC_POSITION_WORDS):
        return True
    grams = _bigrams(position)
    return any(grams & _bigrams(heading) for heading in headings)


class Window:
    def __init__(self, index: int, label: str, text: str,
                 terms: tuple[str, ...] | list[str] = ()) -> None:
        self.index = index
        self.label = label
        self.text = text
        tokens = fact_check.extract_tokens(fact_check.normalize(text), body_only=False)
        seen: dict[str, None] = {}
        for token in tokens:
            if (fact_check.salient(token.raw)
                    or token.kind in ("month", "day", "percent")):
                seen.setdefault(token.raw)
        self.numbers = list(seen)
        self.number_tokens = [
            token for token in tokens
            if token.raw in seen and token.value is not None
        ]
        sentences = [part.strip() for part in qa_reconcile.SENTENCE_SPLIT.split(text)
                     if part.strip()]
        self.question_sentences = [sentence for sentence in sentences
                                   if qa_reconcile.is_question(sentence)]
        self.questions = len(self.question_sentences)
        self.terms = [term for term in terms if term in text]


def fmt_time(seconds: float) -> str:
    total = max(0, int(round(seconds)))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def parse_time(text: str) -> float | None:
    parts = text.replace("：", ":").split(":")
    if not all(part.strip().isdigit() for part in parts):
        return None
    values = [int(part) for part in parts]
    if len(values) == 2:
        return values[0] * 60.0 + values[1]
    if len(values) == 3:
        return values[0] * 3600.0 + values[1] * 60.0 + values[2]
    return None


def load_transcript(path: Path) -> tuple[list[dict], str]:
    """Return (stamps, full_text); stamps is empty for plain-text input."""
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        stamps = [
            item for item in payload.get("timestamps") or []
            if str(item.get("text", "")).strip()
        ]
        return stamps, str(payload.get("text", ""))
    return [], path.read_text(encoding="utf-8-sig")


def time_windows(stamps: list[dict], window_seconds: float,
                 terms: tuple[str, ...] | list[str] = ()) -> list[Window]:
    duration = max(float(item.get("end", 0.0)) for item in stamps)
    windows: list[Window] = []
    index = 0
    start = 0.0
    while start < duration:
        end = min(start + window_seconds, duration)
        index += 1
        members = [
            str(item["text"]).strip() for item in stamps
            if start <= (float(item.get("start", 0.0)) + float(item.get("end", 0.0))) / 2 < end
        ]
        label = f"{fmt_time(start)}–{fmt_time(end)}"
        windows.append(Window(index, label, "".join(members), terms))
        start = end
    return windows


def text_windows(text: str, chars_per_window: int,
                 terms: tuple[str, ...] | list[str] = ()) -> list[Window]:
    lines = [line for line in text.splitlines() if line.strip()]
    windows: list[Window] = []
    block: list[str] = []
    block_chars = 0
    consumed = 0
    block_start = 1

    def flush(start_char: int, end_char: int) -> None:
        if block:
            windows.append(Window(len(windows) + 1, f"字符 {start_char}–{end_char}",
                                  "\n".join(block), terms))

    for line in lines:
        block.append(line)
        block_chars += len(line)
        consumed += len(line)
        if block_chars >= chars_per_window:
            flush(block_start, consumed)
            block, block_chars, block_start = [], 0, consumed + 1
    flush(block_start, consumed)
    return windows


def build_windows(path: Path, window_seconds: float, chars_per_window: int,
                  terms: tuple[str, ...] | list[str] = ()) -> tuple[list[Window], str]:
    stamps, text = load_transcript(path)
    if stamps:
        return time_windows(stamps, window_seconds, terms), "time"
    if not text.strip():
        raise SystemExit(f"转录稿为空：{path}")
    return text_windows(text, chars_per_window, terms), "text"


def write_template(windows: list[Window], target: Path) -> None:
    lines = [
        "# 覆盖率审计清单：将每行的“待判定”改为“纳入 <总结/问答中的位置>”或“省略 <原因>”。",
        "# 时间范围与窗口编号不得改动；“｜”之后的提示信息可保留或删除。",
    ]
    for window in windows:
        hint_parts = []
        if window.numbers:
            shown = "、".join(window.numbers[:6])
            more = f" 等{len(window.numbers)}项" if len(window.numbers) > 6 else ""
            hint_parts.append(f"数字×{len(window.numbers)}：{shown}{more}")
        if window.questions:
            hint_parts.append(f"疑似提问×{window.questions}")
        if window.terms:
            shown_terms = "、".join(window.terms[:4])
            hint_parts.append(f"术语×{len(window.terms)}：{shown_terms}")
        preview = re.sub(r"\s+", "", window.text)[:PREVIEW_CHARS]
        hint_parts.append(f"预览：{preview}" if preview else "（无转录内容）")
        lines.append(f"窗口 {window.index}（{window.label}）：待判定 ｜" + " ｜".join(hint_parts))
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate(
    windows: list[Window],
    mode: str,
    ledger_path: Path,
    minutes_path: Path,
) -> int:
    errors: list[str] = []
    warnings: list[str] = []
    entries: dict[int, tuple[str, str, str]] = {}
    for line_number, line in enumerate(
        ledger_path.read_text(encoding="utf-8-sig").splitlines(), start=1
    ):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = LEDGER_LINE.match(stripped)
        if not match:
            errors.append(f"清单第 {line_number} 行无法解析：{stripped[:40]}")
            continue
        index = int(match.group(1))
        if index in entries:
            errors.append(f"窗口 {index} 在清单中重复出现。")
            continue
        entries[index] = (match.group(2), match.group(3), match.group(4).strip())

    expected = {window.index for window in windows}
    for index in sorted(expected - set(entries)):
        errors.append(f"窗口 {index} 缺少判定。")
    for index in sorted(set(entries) - expected):
        errors.append(f"窗口 {index} 不在转录稿的窗口范围内（共 {len(windows)} 个）。")

    minutes_raw = minutes_path.read_text(encoding="utf-8-sig")
    minutes_text = fact_check.normalize(minutes_raw)
    minutes_tokens = fact_check.extract_tokens(minutes_text, body_only=True)
    minutes_values = {
        (token.kind, round(token.value, 6))
        for token in minutes_tokens if token.value is not None
    }
    headings = minutes_headings(minutes_raw)
    minutes_question_list = qa_reconcile.minutes_questions(minutes_path)

    def question_reaches_minutes(sentence: str) -> bool:
        required = qa_reconcile.effective_threshold(
            sentence, qa_reconcile.DEFAULT_MIN_SIMILARITY
        )
        return any(
            qa_reconcile.similarity(sentence, question) >= required
            for question in minutes_question_list
        )

    included_positions = [
        remark.split("｜")[0].strip(" ｜|")
        for _, decision, remark in entries.values() if decision == "纳入"
    ]
    if len(included_positions) >= 5 and len(set(included_positions)) == 1:
        warnings.append(
            f"全部 {len(included_positions)} 个纳入窗口写了同一位置"
            f"「{included_positions[0]}」，疑似机械填写，请核实各窗口位置的真实性。"
        )

    for window in windows:
        if window.index not in entries:
            continue
        label, decision, remark = entries[window.index]
        if mode == "time":
            parts = re.split(r"[–—~-]", label)
            starts = parse_time(parts[0].strip()) if parts else None
            ends = parse_time(parts[-1].strip()) if len(parts) > 1 else None
            own = re.split(r"[–—~-]", window.label)
            expected_start, expected_end = parse_time(own[0]), parse_time(own[-1])
            if (starts is None or ends is None
                    or abs(starts - expected_start) > 2 or abs(ends - expected_end) > 2):
                errors.append(
                    f"窗口 {window.index} 的时间范围与转录稿不符："
                    f"清单为（{label}），应为（{window.label}）。"
                )
        if decision == "待判定":
            errors.append(f"窗口 {window.index} 仍为“待判定”。")
            continue
        cleaned = remark.split("｜")[0].strip(" ｜|")
        if not cleaned:
            kind = "纳入位置" if decision == "纳入" else "省略原因"
            errors.append(f"窗口 {window.index} 判定为“{decision}”但未写明{kind}。")
        elif decision == "纳入" and not position_plausible(cleaned, headings):
            errors.append(
                f"窗口 {window.index} 的纳入位置「{cleaned}」无法对应纪要中的"
                "任何标题或通用位置（总结/概述/问答等），请写明真实位置。"
            )
        unmatched_questions = [
            sentence for sentence in window.question_sentences
            if not question_reaches_minutes(sentence)
        ]
        if decision == "省略":
            if len(window.numbers) >= 2:
                errors.append(
                    f"窗口 {window.index}（{window.label}）含 {len(window.numbers)} 项数字事实"
                    f"（{'、'.join(window.numbers[:4])}…）却被判定省略，必须纳入或逐项说明。"
                )
            elif len(window.numbers) == 1:
                warnings.append(
                    f"窗口 {window.index} 被省略但含数字「{window.numbers[0]}」，请再次确认。"
                )
            if unmatched_questions:
                warnings.append(
                    f"窗口 {window.index} 被省略，但其中的疑似提问"
                    f"「{unmatched_questions[0][:24]}」未在纪要问答中找到对应，请确认省略合理。"
                )
        elif decision == "纳入" and window.numbers:
            hit = any(
                token.raw in minutes_text
                or (token.kind, round(token.value, 6)) in minutes_values
                for token in window.number_tokens
            ) or any(raw in minutes_text for raw in window.numbers)
            if not hit and unmatched_questions:
                # 两个弱信号叠加（数字未现＋提问未对上）＝该段大概率整体遗漏。
                warnings.append(
                    f"强警告：窗口 {window.index}（{window.label}）判定纳入，但其数字"
                    f"（{'、'.join(window.numbers[:4])}）均未出现在纪要，且窗口内疑似提问"
                    f"「{unmatched_questions[0][:24]}」也未在纪要问答中找到对应——"
                    "两个信号叠加，疑似该段内容整体遗漏，请优先核查。"
                )
            elif not hit:
                warnings.append(
                    f"窗口 {window.index}（{window.label}）判定纳入，但其数字"
                    f"（{'、'.join(window.numbers[:4])}）均未出现在纪要中，请核实。"
                )

    for warning in warnings:
        print(warning if warning.startswith("强警告") else f"警告：{warning}")
    if errors:
        print("覆盖率审计未通过：")
        for error in errors:
            print(f"- {error}")
        return 1
    included = sum(1 for _, decision, _ in entries.values() if decision == "纳入")
    omitted = sum(1 for _, decision, _ in entries.values() if decision == "省略")
    print(f"覆盖率审计通过：共 {len(windows)} 个窗口，纳入 {included} 个、省略 {omitted} 个"
          f"{'，另有 ' + str(len(warnings)) + ' 条警告待人工确认' if warnings else ''}。")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--transcript", required=True, type=Path,
                        help="transcript .json (preferred, uses timestamps) or .txt")
    parser.add_argument("--window-seconds", type=float, default=DEFAULT_WINDOW_SECONDS)
    parser.add_argument("--chars-per-window", type=int, default=DEFAULT_CHARS_PER_WINDOW,
                        help="window size when the transcript has no timestamps")
    parser.add_argument("--make-template", type=Path, metavar="OUT",
                        help="write a ledger template and exit")
    parser.add_argument("--ledger", type=Path, help="filled-in coverage ledger")
    parser.add_argument("--minutes", type=Path, help="minutes text file to cross-check")
    parser.add_argument("--glossary", action="append", type=Path, default=[],
                        help="hotword file whose terms are hinted per window; may be repeated")
    parser.add_argument("--term", action="append", default=[],
                        help="a single hotword term for window hints; may be repeated")
    args = parser.parse_args()

    if not args.transcript.is_file():
        parser.error(f"找不到转录稿：{args.transcript}")
    for path in args.glossary:
        if not path.is_file():
            parser.error(f"找不到术语文件：{path}")
    terms = fact_check.collect_terms(args.glossary, args.term)
    windows, mode = build_windows(args.transcript, args.window_seconds,
                                  args.chars_per_window, terms)

    if args.make_template:
        write_template(windows, args.make_template)
        print(f"已生成覆盖率清单模板：{args.make_template}（{len(windows)} 个窗口，"
              f"{'按时间' if mode == 'time' else '按字符块'}划分）。")
        return 0

    if not args.ledger or not args.minutes:
        parser.error("校验模式需要 --ledger 与 --minutes；生成模板请用 --make-template。")
    if not args.ledger.is_file():
        parser.error(f"找不到覆盖率清单：{args.ledger}")
    if not args.minutes.is_file():
        parser.error(f"找不到纪要文件：{args.minutes}")
    return validate(windows, mode, args.ledger, args.minutes)


if __name__ == "__main__":
    sys.exit(main())
