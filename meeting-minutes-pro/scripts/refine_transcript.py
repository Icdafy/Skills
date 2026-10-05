#!/usr/bin/env python3
"""Targeted dual-engine review: re-transcribe risky segments with Qwen3-ASR.

The funasr engine (fast, diarized, sentence timestamps) produces the master
transcript. This script then re-transcribes only the fact-carrying segments
with Qwen3-ASR — the accuracy specialist — and reports where the two engines
disagree, so a two-hour recording gets dual-engine assurance at a fraction
of the cost of transcribing everything twice.

    refine_transcript.py --transcript <stem>.json --source <media> \
        --output-dir <dir> [--glossary 术语.txt] [--context "人名 术语"]

Segments are selected when a sentence carries salient numbers, dates,
glossary terms, or question marks (or independent full-media windows with --all). Adjacent risky
sentences merge into clips with padding for context. Per-clip checkpoints
make interrupted runs resumable; rerun the identical command to continue.

--budget-minutes M ranks clips by risk score (amounts/percentages in
commitment-like sentences first) and reviews highest-risk clips until the
budget is spent; skipped clips stay in the report as single-engine-only.
Number comparison is order-sensitive: identical value sets in a different
first-occurrence order are reported as 数字顺序 conflicts. Conflict and
review clips are exported as individual wav files under
<stem>.review-clips/ for click-to-play re-listening (--no-audio disables).

Conflicts get a third piece of evidence for re-listen prioritising: with
--voter sensevoice, SenseVoiceSmall (funasr package, a third independent
model family) votes 2-of-3; otherwise an enhanced-audio Qwen re-pass
arbitrates (disable with --no-arbitrate). A verdict of 支持主稿 downgrades
the conflict to low re-listen priority; 支持复核稿 flags the master
transcript itself as suspect. Verdicts never auto-clear a conflict — the
human ear stays the final arbiter.

Outputs <stem>.refine.json and a human-readable <stem>.refine.md. Every clip
listed under 分歧 must be re-listened to before its numbers enter the
minutes (待核 annotations are not allowed in the deliverable); agreement
between two independent engines is strong evidence the figure is right.
Comparison covers numbers/dates (canonically, so 三千万 equals 3000万),
negation words, and glossary terms.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import time

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import fact_check  # noqa: E402
import transcribe  # noqa: E402
from run_state import atomic_json, fingerprint, read_checkpoint, enable_offline, local_model, covered_seconds, file_hash

NEGATIONS = ("没有", "不能", "不可", "禁止", "未", "无法", "取消", "终止", "暂停")
# Sentences carrying commitments or hard limits: mis-heard numbers here hurt the
# most, so they raise the clip's risk score for --budget-minutes prioritising.
CONCLUSION_HINTS = ("承诺", "约定", "保证", "不低于", "不超过", "上限", "下限",
                    "违约", "交付", "期限", "截止", "签约", "合同", "订单", "中标",
                    "回购", "对赌")
DEFAULT_PAD_SECONDS = 1.5
DEFAULT_MERGE_GAP_SECONDS = 4.0
DEFAULT_MAX_CLIP_SECONDS = 120.0
MIN_CLIP_SECONDS = 2.0
CONTEXT_CHAR_LIMIT = 400
# Third-vote engine: SenseVoiceSmall runs inside the already-installed funasr
# package and is a different model family from both Paraformer and Qwen3-ASR,
# so its vote is reasonably independent of either side.
SENSEVOICE_MODEL = "iic/SenseVoiceSmall"
SENSEVOICE_TAG = re.compile(r"<\|[^|]*\|>")


@dataclass
class Clip:
    index: int
    start: float
    end: float
    reasons: tuple[str, ...]
    funasr_text: str
    qwen_text: str = ""
    status: str = "pending"  # consistent | conflict | review | skipped
    conflicts: list[dict] = field(default_factory=list)
    score: int = 0
    audio: str = ""
    third_text: str = ""
    third_source: str = ""
    verdict: str = ""
    priority: str = ""  # conflicts: "high" (default) | "low" (third evidence backs master)


def number_map(text: str) -> dict[tuple, str]:
    """Canonical (kind, value) -> raw for salient numbers and dates."""
    result: dict[tuple, str] = {}
    for token in fact_check.extract_tokens(fact_check.normalize(text), body_only=False):
        if token.value is None:
            continue
        # 以“年”结尾的日期（二〇二三年）和三成/个点等口语百分比由中文写成，
        # salient() 提不出 digits，需单独放行——它们与金额同为复核重点。
        if not fact_check.quantitative(token):
            continue
        result.setdefault((token.kind, round(token.value, 6)), token.raw)
    return result


def ordered_values(text: str) -> list[tuple]:
    """Salient numbers/dates as (kind, value, raw) in first-occurrence order.

    Both engines' texts pass through the same extraction rule, so comparing the
    two sequences detects same-set-different-order cases (a figure attached to
    the wrong statement). Duplicated values keep only their first occurrence so
    ASR stutter/repetition differences do not raise false alarms.
    """
    seen: set[tuple] = set()
    ordered: list[tuple] = []
    for token in fact_check.extract_tokens(fact_check.normalize(text), body_only=False):
        if token.value is None:
            continue
        if not fact_check.quantitative(token):
            continue
        key = (token.kind, round(token.value, 6))
        if key in seen:
            continue
        seen.add(key)
        ordered.append((token.kind, round(token.value, 6), token.raw))
    return ordered


def clip_risk_score(text: str, terms: list[str]) -> int:
    """Rank clips for --budget-minutes: amounts/percentages in commitment-like
    sentences first, bare years and questions last."""
    score = 0
    for kind, value, raw in ordered_values(text):
        if kind == "percent" or any(unit in raw for unit in ("万", "亿")):
            score += 3
        elif kind in ("month", "day") or raw.endswith("年"):
            score += 2
        else:
            score += 1
    if any(hint in text for hint in CONCLUSION_HINTS):
        score += 2
    if any(word in text for word in NEGATIONS):
        score += 1
    if any(term in text for term in terms):
        score += 1
    if "？" in text or "?" in text:
        score += 1
    return score


def sentence_risks(text: str, terms: list[str]) -> tuple[str, ...]:
    risks = []
    if number_map(text):
        risks.append("number")
    if any(term in text for term in terms):
        risks.append("glossary")
    if "？" in text or "?" in text:
        risks.append("question")
    return tuple(risks)


def compare_texts(funasr_text: str, qwen_text: str, terms: list[str]) -> list[dict]:
    def categories(text: str) -> dict[str, dict]:
        return {
            "数字": number_map(text),
            "否定词": {word: word for word in NEGATIONS if word in text},
            "术语": {term: term for term in terms if term in text},
        }

    conflicts: list[dict] = []
    left, right = categories(funasr_text), categories(qwen_text)
    for name in left:
        funasr_only = [left[name][key] for key in left[name] if key not in right[name]]
        qwen_only = [right[name][key] for key in right[name] if key not in left[name]]
        if funasr_only or qwen_only:
            conflicts.append({
                "category": name,
                "funasr_only": funasr_only,
                "qwen_only": qwen_only,
            })
    # Same number set on both sides can still hide a swap (30% market share vs
    # 30% gross margin). When presence agrees, compare first-occurrence order.
    if not any(item["category"] == "数字" for item in conflicts):
        left_seq = ordered_values(funasr_text)
        right_seq = ordered_values(qwen_text)
        if [item[:2] for item in left_seq] != [item[:2] for item in right_seq]:
            conflicts.append({
                "category": "数字顺序",
                "funasr_only": [item[2] for item in left_seq],
                "qwen_only": [item[2] for item in right_seq],
            })
    left_tokens = [t for t in fact_check.extract_tokens(fact_check.normalize(funasr_text), body_only=False) if fact_check.quantitative(t)]
    right_tokens = [t for t in fact_check.extract_tokens(fact_check.normalize(qwen_text), body_only=False) if fact_check.quantitative(t)]
    for ltoken, rtoken in zip(left_tokens, right_tokens):
        if (ltoken.kind == rtoken.kind and ltoken.value == rtoken.value
                and ltoken.unit and rtoken.unit and ltoken.unit != rtoken.unit):
            conflicts.append({"category": "单位", "funasr_only": [ltoken.raw + ltoken.unit],
                              "qwen_only": [rtoken.raw + rtoken.unit]})
    def occurrence_count(text):
        identities = set()
        for clause in re.split(r"[，,。；;！!?？]", fact_check.normalize(text)):
            tokens = [t for t in fact_check.extract_tokens(clause, body_only=False) if fact_check.quantitative(t)]
            anchor = clause
            for token in tokens:
                anchor = anchor.replace(token.raw, "")
            anchor = re.sub(r"对|嗯|是的|\s", "", anchor)
            for token in tokens:
                identities.add((token.kind, token.value, anchor))
        return len(identities)
    if occurrence_count(funasr_text) != occurrence_count(qwen_text) and not any(c["category"] == "数字" for c in conflicts):
        conflicts.append({"category": "事实实例数量", "funasr_only": [str(occurrence_count(funasr_text))],
                          "qwen_only": [str(occurrence_count(qwen_text))]})
    qualifiers = ("预计", "约", "以上", "以下", "不含", "至少", "最多", "去年", "今年", "明年", "已实现", "未实现")
    lscope = [q for q in qualifiers if q in funasr_text]
    rscope = [q for q in qualifiers if q in qwen_text]
    if lscope != rscope and (left_tokens or right_tokens):
        conflicts.append({"category": "时间或限定词", "funasr_only": lscope, "qwen_only": rscope})
    return conflicts


def strip_sensevoice_tags(text: str) -> str:
    """SenseVoice emits rich tags like <|zh|><|NEUTRAL|>; keep plain text only."""
    return SENSEVOICE_TAG.sub("", text).strip()


def third_text_verdict(funasr_text: str, qwen_text: str, third_text: str,
                       terms: list[str]) -> str:
    """Adjudicate a funasr-vs-qwen conflict with a third transcription.

    The third text comes from either an independent engine vote (SenseVoice)
    or an enhanced-audio Qwen re-pass. It never auto-clears a conflict — it
    only sets the re-listen priority; the human ear stays the final arbiter.
    """
    if not third_text.strip():
        return "无法判定"
    vs_funasr = compare_texts(funasr_text, third_text, terms)
    vs_qwen = compare_texts(qwen_text, third_text, terms)
    if not vs_funasr and vs_qwen:
        return "支持主稿"
    if not vs_qwen and vs_funasr:
        return "支持复核稿"
    if vs_funasr and vs_qwen:
        return "三方各异"
    return "无法判定"


def plan_clips(
    stamps: list[dict],
    terms: list[str],
    *,
    select_all: bool,
    pad: float,
    merge_gap: float,
    max_clip: float,
    duration: float,
) -> list[Clip]:
    if duration <= 0 or max_clip <= 0 or pad < 0 or merge_gap < 0:
        raise ValueError("duration/max-clip must be positive; pad/merge-gap must be non-negative")
    if select_all:
        # Plan from the media timeline, never from the primary ASR's omissions.
        clips = []
        cursor = 0.0
        while cursor < duration:
            end = min(duration, cursor + max_clip)
            start = max(0.0, cursor - pad)
            stop = min(duration, end + pad)
            text = "".join(str(x["text"]).strip() for x in stamps
                           if float(x.get("start", 0)) < stop and float(x.get("end", 0)) > start)
            clips.append(Clip(len(clips) + 1, start, stop, ("all",), text,
                              score=clip_risk_score(text, terms)))
            cursor = end
        return clips
    ranges: list[tuple[float, float, set[str]]] = []
    for item in stamps:
        text = str(item["text"]).strip()
        risks = ("all",) if select_all else sentence_risks(text, terms)
        if not risks:
            continue
        start = float(item.get("start", 0.0))
        end = float(item.get("end", start))
        if ranges:
            last_start, last_end, last_risks = ranges[-1]
            if start - last_end <= merge_gap and end - last_start <= max_clip:
                ranges[-1] = (last_start, max(last_end, end), last_risks | set(risks))
                continue
        ranges.append((start, end, set(risks)))

    clips: list[Clip] = []
    for start, end, risks in ranges:
        clip_start = max(0.0, start - pad)
        clip_end = min(duration, end + pad)
        if clip_end - clip_start < MIN_CLIP_SECONDS:
            clip_end = min(duration, clip_start + MIN_CLIP_SECONDS)
        members = [
            str(item["text"]).strip() for item in stamps
            if clip_start <= (float(item.get("start", 0.0)) + float(item.get("end", 0.0))) / 2 <= clip_end
        ]
        clips.append(Clip(
            index=len(clips) + 1,
            start=round(clip_start, 2),
            end=round(clip_end, 2),
            reasons=tuple(sorted(risks)),
            funasr_text="".join(members),
        ))
    for clip in clips:
        clip.score = clip_risk_score(clip.funasr_text, terms)
    return clips


def apply_budget(clips: list[Clip], budget_minutes: float | None) -> tuple[list[Clip], list[Clip]]:
    """Greedy highest-score-first selection within the review time budget.

    The single highest-risk clip is always reviewed even when it alone exceeds
    the budget — a budget must never silently drop the most critical figures.
    Returns (selected, skipped), both in time order; skipped clips are marked
    with status "skipped" and stay in the report so nothing is dropped silently.
    """
    if budget_minutes is None:
        return list(clips), []
    remaining = budget_minutes * 60.0
    selected: list[Clip] = []
    skipped: list[Clip] = []
    for position, clip in enumerate(sorted(clips, key=lambda c: (-c.score, c.index))):
        duration = clip.end - clip.start
        if position == 0 or duration <= remaining:
            selected.append(clip)
            remaining -= duration
        else:
            skipped.append(clip)
    for clip in skipped:
        clip.status = "skipped"
    selected.sort(key=lambda c: c.index)
    skipped.sort(key=lambda c: c.index)
    return selected, skipped


def safe_hms(seconds: float) -> str:
    """011005 style timestamp safe for Windows filenames (no colons)."""
    total = max(0, int(round(seconds)))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}{minutes:02d}{secs:02d}"


def export_review_audio(clips: list[Clip], source: Path, output_dir: Path, stem: str) -> str | None:
    """Cut every conflict/review clip from the source media into its own wav so
    re-listening is click-to-play instead of scrubbing the full recording."""
    targets = [clip for clip in clips if clip.status in ("conflict", "review")]
    if not targets:
        return None
    audio_dir = output_dir / f"{stem}.review-clips"
    if audio_dir.exists():
        shutil.rmtree(audio_dir)
    audio_dir.mkdir(parents=True)
    for clip in targets:
        name = f"clip_{clip.index:04d}_{safe_hms(clip.start)}-{safe_hms(clip.end)}.wav"
        path = audio_dir / name
        transcribe.prepare_wav(
            source, path, clip_start=clip.start, clip_duration=clip.end - clip.start
        )
        clip.audio = str(path)
    return str(audio_dir)


def hms(seconds: float) -> str:
    return transcribe.srt_time(seconds)[:-4]


def write_report(
    target: Path,
    transcript: Path,
    model_name: str,
    clips: list[Clip],
    total_duration: float,
    budget_minutes: float | None = None,
    audio_dir: str | None = None,
) -> None:
    consistent = [c for c in clips if c.status == "consistent"]
    conflicted = [c for c in clips if c.status == "conflict"]
    review = [c for c in clips if c.status == "review"]
    skipped = [c for c in clips if c.status == "skipped"]
    reviewed = [c for c in clips if c.status != "skipped"]
    covered = covered_seconds([(c.start, c.end) for c in reviewed])
    lines = [
        "# 双引擎复核报告",
        "",
        f"- 主转录稿：`{transcript.name}`（FunASR）",
        f"- 复核引擎：`{model_name}`",
        f"- 复核片段：{len(reviewed)} 个，共 {covered / 60:.1f} 分钟"
        f"（占全长 {total_duration / 60:.1f} 分钟的 {covered / total_duration * 100:.0f}%）"
        if total_duration else f"- 复核片段：{len(reviewed)} 个",
        f"- 结果：一致 {len(consistent)}、分歧 {len(conflicted)}"
        + (
            f"（高优先级 {sum(1 for c in conflicted if c.priority != 'low')}、"
            f"低优先级 {sum(1 for c in conflicted if c.priority == 'low')}）"
            if any(c.priority == "low" for c in conflicted) else ""
        )
        + f"、待人工复核 {len(review)}"
        + (f"、预算外未复核 {len(skipped)}" if skipped else ""),
    ]
    if budget_minutes is not None:
        skipped_seconds = sum(c.end - c.start for c in skipped)
        lines.append(
            f"- 风险预算：{budget_minutes:g} 分钟，按风险分从高到低选取；"
            f"跳过低风险片段 {len(skipped)} 个（共 {skipped_seconds / 60:.1f} 分钟），"
            "明细见文末，未复核内容仅有单引擎背书。"
        )
    if audio_dir:
        lines.append(f"- 回听音频：分歧与待复核片段已剪出至 `{Path(audio_dir).name}/`，逐条点开即听。")
    lines += [
        "",
        "一致仅表示已实现的比较项未发现差异，不证明事实或录音绝对准确；分歧须实际回听裁决。",
        "无法辨识的数字保留可确认部分并就地括注；裁决在 review.json 留痕，不将 ASR 猜测当作事实。",
        "低优先级分歧＝第三份证据支持主稿口径，仍须回听，但可排在高优先级之后处理。",
        "",
    ]
    if conflicted:
        conflicted = sorted(
            conflicted, key=lambda c: (0 if c.priority != "low" else 1, c.index)
        )
        lines.append("## 存在分歧的片段（高优先级在前）")
        lines.append("")
        for clip in conflicted:
            lines.append(f"### 片段 {clip.index}（{hms(clip.start)}–{hms(clip.end)}）")
            lines.append(f"- FunASR：{clip.funasr_text}")
            lines.append(f"- Qwen3-ASR：{clip.qwen_text}")
            for conflict in clip.conflicts:
                funasr_side = "、".join(conflict["funasr_only"]) or "（无）"
                qwen_side = "、".join(conflict["qwen_only"]) or "（无）"
                if conflict["category"] == "数字顺序":
                    lines.append(
                        f"- 分歧（数字顺序）：FunASR 侧顺序「{funasr_side}」；"
                        f"Qwen 侧顺序「{qwen_side}」——同组数字出现顺序不一致，"
                        "疑似数字被安到不同表述上，回听时须确认每个数字的指代。"
                    )
                else:
                    lines.append(f"- 分歧（{conflict['category']}）：FunASR 独有「{funasr_side}」；"
                                 f"Qwen 独有「{qwen_side}」")
            if clip.verdict:
                priority_note = "低（可后置）" if clip.priority == "low" else "高"
                lines.append(f"- 仲裁（{clip.third_source}）：{clip.verdict}；"
                             f"回听优先级：{priority_note}")
                if clip.third_text:
                    lines.append(f"- 第三份转写：{clip.third_text}")
            if clip.audio:
                lines.append(f"- 回听音频：`{Path(clip.audio).name}`")
            lines.append("")
    if review:
        lines.append("## 待人工复核的片段（复核引擎未返回内容）")
        lines.append("")
        for clip in review:
            audio_note = f" ｜回听：`{Path(clip.audio).name}`" if clip.audio else ""
            verdict_note = (
                f" ｜{clip.third_source}：{clip.verdict}" if clip.verdict else ""
            )
            lines.append(f"- 片段 {clip.index}（{hms(clip.start)}–{hms(clip.end)}）："
                         f"{clip.funasr_text[:60]}{verdict_note}{audio_note}")
        lines.append("")
    if consistent:
        lines.append("## 双引擎一致的片段")
        lines.append("")
        for clip in consistent:
            lines.append(f"- 片段 {clip.index}（{hms(clip.start)}–{hms(clip.end)}）"
                         f"［{'、'.join(clip.reasons)}］{clip.funasr_text[:40]}")
        lines.append("")
    if skipped:
        lines.append("## 预算外未复核的片段（仅单引擎，未经双引擎背书）")
        lines.append("")
        for clip in skipped:
            lines.append(f"- 片段 {clip.index}（{hms(clip.start)}–{hms(clip.end)}）"
                         f"［风险分 {clip.score}］{clip.funasr_text[:40]}")
    target.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--transcript", required=True, type=Path,
                        help="funasr transcript .json with sentence timestamps")
    parser.add_argument("--source", required=True, type=Path, help="original audio/video file")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--glossary", action="append", type=Path, default=[])
    parser.add_argument("--term", action="append", default=[])
    parser.add_argument("--context", default="", help="extra recognition context for Qwen3-ASR")
    parser.add_argument("--model", default=transcribe.QWEN_MODEL_DEFAULT)
    parser.add_argument("--language", default="auto")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda", "mps"], default="auto")
    parser.add_argument("--max-new-tokens", type=int, default=None)
    parser.add_argument("--pad", type=float, default=DEFAULT_PAD_SECONDS)
    parser.add_argument("--merge-gap", type=float, default=DEFAULT_MERGE_GAP_SECONDS)
    parser.add_argument("--max-clip", type=float, default=DEFAULT_MAX_CLIP_SECONDS)
    parser.add_argument("--all", action="store_true",
                        help="re-transcribe the full source media timeline, including primary ASR gaps")
    parser.add_argument("--budget-minutes", type=float, default=None,
                        help="review time budget: clips are ranked by risk score "
                             "and reviewed highest-first until the budget is spent; "
                             "skipped clips are listed in the report")
    parser.add_argument("--voter", choices=("none", "sensevoice"), default="none",
                        help="third engine for 2-of-3 voting on conflicts "
                             "(SenseVoiceSmall via the funasr package); downgrades "
                             "master-backed conflicts to low re-listen priority")
    parser.add_argument("--no-arbitrate", action="store_true",
                        help="skip the enhanced-audio Qwen re-pass that arbitrates "
                             "conflicts when no voter engine is enabled")
    parser.add_argument("--no-audio", action="store_true",
                        help="do not export conflict/review clips as wav files")
    parser.add_argument("--dry-run", action="store_true",
                        help="plan and print the clips without loading any model")
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args()

    if args.all and args.budget_minutes is not None:
        parser.error("--all 不允许 --budget-minutes 缩减覆盖")
    if args.offline:
        enable_offline()
    if args.budget_minutes is not None and args.budget_minutes <= 0:
        parser.error("--budget-minutes 必须为正数")

    if not args.transcript.is_file():
        parser.error(f"找不到转录稿：{args.transcript}")
    if not args.source.is_file():
        parser.error(f"找不到源媒体文件：{args.source}")
    for path in args.glossary:
        if not path.is_file():
            parser.error(f"找不到术语文件：{path}")

    payload = json.loads(args.transcript.read_text(encoding="utf-8-sig"))
    stamps = [
        item for item in payload.get("timestamps") or []
        if str(item.get("text", "")).strip()
    ]
    if not stamps and not args.all:
        parser.error("转录 JSON 不含句级时间戳；请以 --diarize 或 --timestamps 重新转录。")
    duration = transcribe.media_duration(args.source)
    if duration is None or duration <= 0:
        parser.error("无法读取源媒体总时长，不能核验复核覆盖范围")
    if payload.get("is_partial") or payload.get("clip_start_seconds", 0):
        parser.error("不可把样本或裁剪转录当作全片主稿，请提供完整录音转录")
    if payload.get("source_sha256") and payload["source_sha256"] != file_hash(args.source):
        parser.error("主稿与源媒体哈希不一致")
    terms = fact_check.collect_terms(args.glossary, args.term)

    clips = plan_clips(
        stamps, terms,
        select_all=args.all,
        pad=args.pad,
        merge_gap=args.merge_gap,
        max_clip=args.max_clip,
        duration=duration,
    )
    if payload.get("engine") == "qwen":
        parser.error("主稿已由 Qwen 生成；本复核器不能把同族模型重转称为独立双引擎复核。请使用另一适用引擎独立转录并人工核验。")
    if not clips:
        print(json.dumps({"ok": True, "clips": 0,
                          "note": "未发现需要复核的高风险片段"}, ensure_ascii=False))
        return 0

    selected, skipped = apply_budget(clips, args.budget_minutes)
    if not selected:
        parser.error("--budget-minutes 过小：任何片段都无法纳入复核，请增大预算")

    if args.dry_run:
        selected_ids = {c.index for c in selected}
        print(json.dumps({
            "ok": True,
            "dry_run": True,
            "budget_minutes": args.budget_minutes,
            "clips": [
                {"index": c.index, "start": c.start, "end": c.end,
                 "duration": round(c.end - c.start, 1), "reasons": list(c.reasons),
                 "score": c.score, "selected": c.index in selected_ids,
                 "preview": c.funasr_text[:40]}
                for c in clips
            ],
            "covered_seconds": round(covered_seconds([(c.start, c.end) for c in selected]), 1),
            "skipped_clips": len(skipped),
            "total_seconds": round(duration, 1),
        }, ensure_ascii=False, indent=2))
        return 0

    try:
        import torch
        from qwen_asr import Qwen3ASRModel
    except ImportError as exc:
        print(json.dumps({
            "ok": False,
            "error": f"qwen runtime dependency missing: {exc}; "
                     "run scripts/bootstrap_runtime.py --install --engine qwen, "
                     "then invoke this script with the reported runtime Python",
        }, ensure_ascii=False))
        return 1

    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = args.transcript.stem
    checkpoint_dir = output_dir / f"{stem}.refine-chunks"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    device, dtype = transcribe.choose_device(torch, args.device)
    identity = fingerprint(args.source, {**vars(args), "transcript_sha256": file_hash(args.transcript), "terms": terms, "checkpoint_schema": 1, "output_dir": None, "budget_minutes": None, "no_resume": False})
    max_clip_seconds = max(c.end - c.start for c in clips)
    model = Qwen3ASRModel.from_pretrained(
        local_model(args.model, "hf", args.offline),
        dtype=dtype,
        device_map=device,
        max_inference_batch_size=1,
        max_new_tokens=args.max_new_tokens or transcribe.auto_max_new_tokens(max_clip_seconds),
    )
    context = " ".join(terms + ([args.context] if args.context.strip() else []))[:CONTEXT_CHAR_LIMIT]
    language = None if args.language.lower() in {"auto", "none", ""} else args.language

    voter_model = None
    if args.voter == "sensevoice":
        try:
            from funasr import AutoModel as FunASRAutoModel
        except ImportError as exc:
            print(json.dumps({
                "ok": False,
                "error": f"sensevoice voter needs the funasr engine: {exc}; "
                         "run scripts/bootstrap_runtime.py --install --engine funasr",
            }, ensure_ascii=False))
            return 1
        transcribe.progress({"stage": "load", "engine": "sensevoice"})
        voter_model = FunASRAutoModel(
            model=local_model(SENSEVOICE_MODEL, "ms", args.offline),
            check_latest=False,
            vad_model=local_model("fsmn-vad", "ms", args.offline),
            vad_kwargs={"max_single_segment_time": 30000},
            device=transcribe.funasr_device(args.device),
            disable_update=True,
            disable_pbar=True,
        )

    def voter_transcribe(clip: Clip, temp_dir: str) -> str:
        checkpoint = checkpoint_dir / f"clip_{clip.index:04d}.voter.json"
        if not args.no_resume and checkpoint.is_file():
            cached = read_checkpoint(checkpoint, identity + ":voter", clip.start, clip.end)
            if cached is not None:
                return str(cached.get("text", ""))
        voter_wav = Path(temp_dir) / f"clip_{clip.index:04d}.voter.wav"
        transcribe.prepare_wav(
            args.source, voter_wav, clip_start=clip.start, clip_duration=clip.end - clip.start
        )
        results = voter_model.generate(
            input=str(voter_wav), language="auto", use_itn=True,
            merge_vad=True, merge_length_s=15,
        )
        text = strip_sensevoice_tags(str(results[0].get("text", ""))) if results else ""
        atomic_json(checkpoint, {
            "identity": identity + ":voter",
            "model": SENSEVOICE_MODEL,
            "start": clip.start,
            "end": clip.end,
            "text": text,
        })
        return text

    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="mmp-refine-") as temp_dir:
        for clip in selected:
            checkpoint = checkpoint_dir / f"clip_{clip.index:04d}.json"
            cached_text: str | None = None
            if not args.no_resume and checkpoint.is_file():
                cached = read_checkpoint(checkpoint, identity, clip.start, clip.end)
                if cached is not None:
                    cached_text = str(cached.get("text", ""))
            if cached_text is None:
                clip_wav = Path(temp_dir) / f"clip_{clip.index:04d}.wav"
                transcribe.prepare_wav(
                    args.source, clip_wav,
                    clip_start=clip.start, clip_duration=clip.end - clip.start,
                )
                results = model.transcribe(
                    audio=str(clip_wav), context=context, language=language,
                    return_time_stamps=False,
                )
                cached_text = str(results[0].text).strip() if results else ""
                atomic_json(checkpoint, {
                    "identity": identity,
                    "model": args.model,
                    "start": clip.start,
                    "end": clip.end,
                    "text": cached_text,
                })
            clip.qwen_text = cached_text
            if not clip.qwen_text:
                clip.status = "review"
            else:
                clip.conflicts = compare_texts(clip.funasr_text, clip.qwen_text, terms)
                clip.status = "conflict" if clip.conflicts else "consistent"
            if clip.status == "conflict":
                clip.priority = "high"

            # Third evidence: an independent engine vote (preferred) or an
            # enhanced-audio Qwen re-pass. Sets re-listen priority only —
            # conflicts are never auto-cleared.
            if voter_model is not None and clip.status in ("conflict", "review"):
                clip.third_text = voter_transcribe(clip, temp_dir)
                clip.third_source = "第三引擎三取二（SenseVoice）"
            elif (not args.no_arbitrate and clip.status == "conflict"):
                enhanced_wav = Path(temp_dir) / f"clip_{clip.index:04d}.enh.wav"
                transcribe.prepare_wav(
                    args.source, enhanced_wav,
                    clip_start=clip.start, clip_duration=clip.end - clip.start,
                    enhance=True,
                )
                results = model.transcribe(
                    audio=str(enhanced_wav), context=context, language=language,
                    return_time_stamps=False,
                )
                clip.third_text = str(results[0].text).strip() if results else ""
                clip.third_source = "增强重转仲裁（Qwen）"
            if clip.third_source:
                if clip.status == "review":
                    if not clip.third_text:
                        clip.verdict = "无法判定"
                    elif not compare_texts(clip.funasr_text, clip.third_text, terms):
                        clip.verdict = "支持主稿"
                    else:
                        clip.verdict = "三方各异"
                else:
                    clip.verdict = third_text_verdict(
                        clip.funasr_text, clip.qwen_text, clip.third_text, terms
                    )
                clip.priority = "low" if clip.verdict == "支持主稿" else "high"
            transcribe.progress({"stage": "clip", "index": clip.index,
                                 "total": len(selected), "status": clip.status,
                                 "verdict": clip.verdict or None})

    audio_dir: str | None = None
    if not args.no_audio:
        audio_dir = export_review_audio(clips, args.source, output_dir, stem)

    report_json = output_dir / f"{stem}.refine.json"
    report_md = output_dir / f"{stem}.refine.md"
    report_json.write_text(json.dumps({
        "schema_version": 3,
        "source_sha256": file_hash(args.source),
        "transcript_sha256": file_hash(args.transcript),
        "review_mode": "all" if args.all else "targeted",
        "duration_seconds": duration,
        "covered_seconds": covered_seconds([(c.start, c.end) for c in selected]),
        "primary_engine": payload.get("engine", "unknown"),
        "primary_model": payload.get("model", "unknown"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "transcript": str(args.transcript),
        "source": str(args.source),
        "model": args.model,
        "device": device,
        "budget_minutes": args.budget_minutes,
        "review_audio_dir": audio_dir,
        "voter": args.voter,
        "arbitrate": not args.no_arbitrate,
        "clips": [
            {"index": c.index, "start": c.start, "end": c.end,
             "reasons": list(c.reasons), "score": c.score, "status": c.status,
             "funasr_text": c.funasr_text, "qwen_text": c.qwen_text,
             "conflicts": c.conflicts, "audio": c.audio,
             "third_text": c.third_text, "third_source": c.third_source,
             "verdict": c.verdict, "priority": c.priority}
            for c in clips
        ],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(report_md, args.transcript, args.model, clips, duration,
                 budget_minutes=args.budget_minutes, audio_dir=audio_dir)
    if skipped:
        # A budgeted run left clips unreviewed: keep the checkpoints so a rerun
        # with a larger --budget-minutes reuses the finished clips instantly.
        transcribe.progress({"stage": "checkpoints", "kept": len(selected),
                             "note": "预算运行保留检查点，加大预算重跑可续传"})
    else:
        shutil.rmtree(checkpoint_dir, ignore_errors=True)

    summary = {
        "ok": True,
        "clips": len(clips),
        "consistent": sum(1 for c in clips if c.status == "consistent"),
        "conflict": sum(1 for c in clips if c.status == "conflict"),
        "conflict_high": sum(1 for c in clips if c.status == "conflict" and c.priority != "low"),
        "conflict_low": sum(1 for c in clips if c.status == "conflict" and c.priority == "low"),
        "review": sum(1 for c in clips if c.status == "review"),
        "skipped": len(skipped),
        "voter": args.voter,
        "budget_minutes": args.budget_minutes,
        "review_audio_dir": audio_dir,
        "covered_seconds": round(covered_seconds([(c.start, c.end) for c in selected]), 1),
        "total_seconds": round(duration, 1),
        "elapsed_seconds": round(time.monotonic() - started, 1),
        "outputs": {"json": str(report_json), "md": str(report_md)},
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
