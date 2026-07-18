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

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import fact_check  # noqa: E402

INDENT = "　　"
HEADING_MARK = re.compile(r"^(?:[一二三四五六七八九十]+、|（[一二三四五六七八九十]+）|\d+\.|（\d+）)")
QUESTION_MARK = re.compile(r"[？?]")
INTERROGATIVES = re.compile(
    r"多少|什么|怎么|如何|为什么|为啥|是否|能不能|会不会|有没有|可不可以|"
    r"哪些|哪家|哪个|几个|几家|占比|多大|多久|多长时间"
)
FILLERS = ("是吧", "对吧", "对不对", "是不是", "好吧", "行吗", "好吗", "是吗", "对吗", "嗯", "啊")
SENTENCE_SPLIT = re.compile(r"(?<=[。！？!?；;\n])")
MERGE_GAP_SECONDS = 5.0
DEFAULT_MIN_SIMILARITY = 0.30
# 短问题的 bigram 少，包含度天然虚高，容易把真正被遗漏的提问误判为已匹配
# （静默漏报比误报更危险）；对净长不足 10 字的候选抬高匹配门槛。
SHORT_TEXT_CHARS = 10
SHORT_TEXT_MIN_SIMILARITY = 0.45


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


def minutes_qa_groups(path: Path) -> list[tuple[str, str]]:
    """(question, group_text) pairs; group_text spans 问： to the next 问：
    or heading, so the answer-substance check sees the whole Q&A group."""
    groups: list[tuple[str, list[str]]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        content = line.removeprefix(INDENT).strip()
        if not content:
            continue
        if content.startswith("问："):
            groups.append((content.removeprefix("问：").strip(), [content]))
        elif groups and HEADING_MARK.match(content):
            groups.append(("", []))  # heading closes the current group
        elif groups and groups[-1][0]:
            groups[-1][1].append(content)
    return [(question, "\n".join(lines))
            for question, lines in groups if question]


def minutes_questions(path: Path) -> list[str]:
    return [question for question, _ in minutes_qa_groups(path)]


def load_stamps(path: Path) -> list[dict]:
    if path.suffix.lower() != ".json":
        return []
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return [
        item for item in payload.get("timestamps") or []
        if str(item.get("text", "")).strip()
    ]


def _salient_tokens(text: str) -> list:
    return [
        token for token in fact_check.extract_tokens(
            fact_check.normalize(text), body_only=False)
        if token.value is not None and (
            fact_check.salient(token.raw)
            or token.kind in ("month", "day", "percent")
            or token.raw.endswith("年")
        )
    ]


def answer_number_gaps(
    matched: list[tuple[int, Candidate, str, float]],
    all_candidates: list[Candidate],
    stamps: list[dict],
    groups: list[tuple[str, str]],
) -> list[tuple[int, str, list[str]]]:
    """Numbers spoken in each answered window that never reached the minutes'
    corresponding Q&A group. Warnings only — a figure may be deliberately
    summarised away, so the human confirms each gap."""
    group_by_question = {}
    for question, group_text in groups:
        group_by_question.setdefault(question, group_text)
    question_starts = sorted(
        candidate.start for candidate in all_candidates
        if candidate.start is not None
    )
    gaps: list[tuple[int, str, list[str]]] = []
    for index, candidate, question, _score in matched:
        if candidate.start is None:
            continue
        later = [start for start in question_starts if start > candidate.start]
        window_end = later[0] if later else float("inf")
        answer_text = "".join(
            str(item["text"]) for item in stamps
            if candidate.start < float(item.get("start", 0.0)) < window_end
        )
        if not answer_text:
            continue
        group_text = group_by_question.get(question, "")
        group_norm = fact_check.normalize(group_text)
        group_values = {
            (token.kind, round(token.value, 6))
            for token in fact_check.extract_tokens(group_norm, body_only=False)
            if token.value is not None
        }
        missing: list[str] = []
        for token in _salient_tokens(answer_text):
            key = (token.kind, round(token.value, 6))
            if key in group_values or token.raw in group_norm:
                continue
            if token.raw not in missing:
                missing.append(token.raw)
        if missing:
            gaps.append((index, question, missing))
    return gaps


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


def effective_threshold(text: str, base: float) -> float:
    cleaned = re.sub(r"[^\w]", "", text)
    if len(cleaned) < SHORT_TEXT_CHARS:
        return max(base, SHORT_TEXT_MIN_SIMILARITY)
    return base


def reconcile(
    candidates: list[Candidate],
    questions: list[str],
    min_similarity: float,
    skip: list[int],
) -> tuple[list[tuple[int, Candidate, float]], list[str],
           list[tuple[int, Candidate, str, float]]]:
    """Return (suspected omissions, orphaned minutes questions, matches).

    matches carries the full 转录提问 ↔ 纪要问答 mapping for --show-matches,
    mirroring fact_check's positive-evidence output.
    """
    suspected: list[tuple[int, Candidate, float]] = []
    matched: list[tuple[int, Candidate, str, float]] = []
    matched_questions: set[int] = set()
    for index, candidate in enumerate(candidates, start=1):
        required = effective_threshold(candidate.text, min_similarity)
        best_score, best_question = 0.0, None
        for q_index, question in enumerate(questions):
            score = similarity(candidate.text, question)
            if score > best_score:
                best_score, best_question = score, q_index
        if best_score >= required and best_question is not None:
            matched_questions.add(best_question)
            matched.append((index, candidate, questions[best_question], best_score))
        elif index not in skip:
            suspected.append((index, candidate, best_score))

    orphaned = [
        question for q_index, question in enumerate(questions)
        if q_index not in matched_questions
        and all(
            similarity(candidate.text, question)
            < effective_threshold(candidate.text, min_similarity)
            for candidate in candidates
        )
    ]
    return suspected, orphaned, matched


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
    parser.add_argument("--show-matches", action="store_true",
                        help="print the full transcript-question ↔ minutes-question "
                             "mapping for positive review")
    args = parser.parse_args()

    if not args.minutes.is_file():
        parser.error(f"找不到纪要文件：{args.minutes}")
    if not args.transcript.is_file():
        parser.error(f"找不到转录稿：{args.transcript}")

    candidates = load_candidates(args.transcript)
    groups = minutes_qa_groups(args.minutes)
    questions = [question for question, _ in groups]
    print(f"转录稿检测到疑似提问 {len(candidates)} 个；纪要包含问答 {len(questions)} 组。")

    if not candidates:
        print("未检测到疑似提问；如访谈确有问答，请人工复核转录稿。")
        return 0

    suspected, orphaned, matched = reconcile(
        candidates, questions, args.min_similarity, args.skip
    )
    if args.show_matches and matched:
        print("对账映射（转录疑似提问 ↔ 纪要问答，请正向浏览确认指向未变）：")
        for index, candidate, question, score in matched:
            speaker = f"【{candidate.speaker}】" if candidate.speaker else ""
            print(f"- 编号 {index}［{fmt_time(candidate.start)}］{speaker}"
                  f"{candidate.text[:40]}")
            # "<->" 保持在 GBK 字符集内，避免 Windows 控制台输出失败。
            print(f"    <-> 问：{question[:40]}（相似度 {score:.2f}）")
    if orphaned:
        print("警告：以下纪要问题未在转录稿中检测到对应提问，请确认并非虚构或过度改写：")
        for question in orphaned:
            print(f"- 问：{question[:50]}")

    # 答案实质对账：答复窗口里说过的显著数字必须进入纪要对应问答组。
    stamps = load_stamps(args.transcript)
    if stamps and matched:
        gaps = answer_number_gaps(matched, candidates, stamps, groups)
        for index, question, missing in gaps:
            print(f"警告：问「{question[:30]}」的答复中，转录稿数字"
                  f"「{'、'.join(missing[:6])}」未出现在纪要该组问答中，"
                  "请确认是否为刻意省略并向用户说明。")

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
