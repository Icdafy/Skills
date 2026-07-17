#!/usr/bin/env python3
"""Reconcile the questions asked in the recording with the minutes' Q&A.

quality_check.py validates the shape of the deliverable (问/答 pairing, the
summary-before-Q&A order) but nothing verifies that every question actually
asked in the interview survived into the minutes. This script detects
question-like turns in the transcript, fuzzily matches each against the
minutes' 问： lines, and fails when questions appear to have been dropped.

    qa_reconcile.py 会议纪要.txt --transcript <stem>.json
    qa_reconcile.py 会议纪要.txt --transcript <stem>.txt   # no timestamps

Detection is heuristic; after human review a false positive is released with
--skip <编号> (repeatable), and the reason must be reported to the user.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

INDENT = "　　"
QUESTION_MARK = re.compile(r"[？?]")
INTERROGATIVES = re.compile(
    r"多少|什么|怎么|如何|为什么|为啥|是否|能不能|会不会|有没有|可不可以|"
    r"哪些|哪家|哪个|几个|几家|占比|多大|多久|多长时间"
)
FILLERS = ("是吧", "对吧", "对不对", "是不是", "好吧", "行吗", "好吗", "是吗", "对吗", "嗯", "啊")
SENTENCE_SPLIT = re.compile(r"(?<=[。！？!?；;\n])")
MERGE_GAP_SECONDS = 5.0
DEFAULT_MIN_SIMILARITY = 0.30


class Candidate:
    def __init__(self, text: str, start: float | None, speaker: str | None) -> None:
        self.text = text
        self.start = start
        self.speaker = speaker


def is_question(text: str) -> bool:
    stripped = text.strip()
    bare = re.sub(r"[\s。！？!?；;，,]+$", "", stripped)
    if len(bare) < 6:
        return False
    if any(bare.endswith(filler) for filler in FILLERS) and len(bare) < 12:
        return False
    if QUESTION_MARK.search(stripped):
        return True
    return bool(INTERROGATIVES.search(stripped)) and len(bare) >= 10


def load_candidates(path: Path) -> list[Candidate]:
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        stamps = [
            item for item in payload.get("timestamps") or []
            if str(item.get("text", "")).strip()
        ]
        if stamps:
            return stamps_to_candidates(stamps)
        text = str(payload.get("text", ""))
    else:
        text = path.read_text(encoding="utf-8-sig")
    sentences = [part.strip() for part in SENTENCE_SPLIT.split(text) if part.strip()]
    return [Candidate(sentence, None, None) for sentence in sentences if is_question(sentence)]


def stamps_to_candidates(stamps: list[dict]) -> list[Candidate]:
    """Question sentences; adjacent ones from the same speaker merge into one."""
    candidates: list[Candidate] = []
    current: Candidate | None = None
    current_end = 0.0
    for item in stamps:
        text = str(item["text"]).strip()
        start = float(item.get("start", 0.0))
        end = float(item.get("end", start))
        speaker = item.get("speaker")
        if not is_question(text):
            if current is not None and (
                speaker != current.speaker or start - current_end > MERGE_GAP_SECONDS
            ):
                candidates.append(current)
                current = None
            continue
        if (current is not None and speaker == current.speaker
                and start - current_end <= MERGE_GAP_SECONDS):
            current.text += text
        else:
            if current is not None:
                candidates.append(current)
            current = Candidate(text, start, speaker)
        current_end = end
    if current is not None:
        candidates.append(current)
    return candidates


def minutes_questions(path: Path) -> list[str]:
    questions: list[str] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        content = line.removeprefix(INDENT).strip()
        if content.startswith("问："):
            questions.append(content.removeprefix("问：").strip())
    return questions


def bigrams(text: str) -> set[str]:
    cleaned = re.sub(r"[^\w]", "", text).lower()
    if len(cleaned) < 2:
        return {cleaned} if cleaned else set()
    return {cleaned[i:i + 2] for i in range(len(cleaned) - 1)}


def similarity(a: str, b: str) -> float:
    grams_a, grams_b = bigrams(a), bigrams(b)
    if not grams_a or not grams_b:
        return 0.0
    return len(grams_a & grams_b) / min(len(grams_a), len(grams_b))


def fmt_time(seconds: float | None) -> str:
    if seconds is None:
        return "--:--"
    total = max(0, int(round(seconds)))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"


def reconcile(
    candidates: list[Candidate],
    questions: list[str],
    min_similarity: float,
    skip: list[int],
) -> tuple[list[tuple[int, Candidate, float]], list[str]]:
    """Return (suspected omissions, minutes questions with no transcript source)."""
    suspected: list[tuple[int, Candidate, float]] = []
    matched_questions: set[int] = set()
    for index, candidate in enumerate(candidates, start=1):
        best_score, best_question = 0.0, None
        for q_index, question in enumerate(questions):
            score = similarity(candidate.text, question)
            if score > best_score:
                best_score, best_question = score, q_index
        if best_score >= min_similarity and best_question is not None:
            matched_questions.add(best_question)
        elif index not in skip:
            suspected.append((index, candidate, best_score))

    orphaned = [
        question for q_index, question in enumerate(questions)
        if q_index not in matched_questions
        and all(similarity(candidate.text, question) < min_similarity
                for candidate in candidates)
    ]
    return suspected, orphaned


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("minutes", type=Path, help="minutes text file")
    parser.add_argument("--transcript", required=True, type=Path,
                        help="transcript .json (preferred) or .txt")
    parser.add_argument("--min-similarity", type=float, default=DEFAULT_MIN_SIMILARITY)
    parser.add_argument("--skip", action="append", type=int, default=[],
                        help="release a reviewed false positive by its 编号; repeatable, "
                             "and the justification must be reported to the user")
    args = parser.parse_args()

    if not args.minutes.is_file():
        parser.error(f"找不到纪要文件：{args.minutes}")
    if not args.transcript.is_file():
        parser.error(f"找不到转录稿：{args.transcript}")

    candidates = load_candidates(args.transcript)
    questions = minutes_questions(args.minutes)
    print(f"转录稿检测到疑似提问 {len(candidates)} 个；纪要包含问答 {len(questions)} 组。")

    if not candidates:
        print("未检测到疑似提问；如访谈确有问答，请人工复核转录稿。")
        return 0

    suspected, orphaned = reconcile(candidates, questions, args.min_similarity, args.skip)
    if orphaned:
        print("警告：以下纪要问题未在转录稿中检测到对应提问，请确认并非虚构或过度改写：")
        for question in orphaned:
            print(f"- 问：{question[:50]}")

    if suspected:
        print("以下疑似提问未在纪要问答中找到对应内容（疑似遗漏），"
              "必须补入问答，或人工确认后以 --skip <编号> 放行并向用户说明理由：")
        for index, candidate, score in suspected:
            speaker = f"【{candidate.speaker}】" if candidate.speaker else ""
            print(f"- 编号 {index}［{fmt_time(candidate.start)}］{speaker}"
                  f"{candidate.text[:60]}（最高相似度 {score:.2f}）")
        return 1

    skipped = f"，已按人工确认放行 {len(args.skip)} 个" if args.skip else ""
    print(f"问答对账通过：疑似提问均能在纪要问答中找到对应内容{skipped}。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
