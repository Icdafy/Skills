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
glossary terms, or question marks (or everything with --all). Adjacent risky
sentences merge into clips with padding for context. Per-clip checkpoints
make interrupted runs resumable; rerun the identical command to continue.

Outputs <stem>.refine.json and a human-readable <stem>.refine.md. Every clip
listed under 分歧 must be re-listened to before its numbers enter the
minutes (待核 annotations are not allowed in the deliverable); agreement
between two independent engines is strong evidence the figure is right. Comparison covers numbers/dates (canonically, so 三千万
equals 3000万), negation words, and glossary terms.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import fact_check  # noqa: E402
import transcribe  # noqa: E402

NEGATIONS = ("没有", "不能", "不可", "禁止", "未", "无法", "取消", "终止", "暂停")
DEFAULT_PAD_SECONDS = 1.5
DEFAULT_MERGE_GAP_SECONDS = 4.0
DEFAULT_MAX_CLIP_SECONDS = 120.0
MIN_CLIP_SECONDS = 2.0
CONTEXT_CHAR_LIMIT = 400


@dataclass
class Clip:
    index: int
    start: float
    end: float
    reasons: tuple[str, ...]
    funasr_text: str
    qwen_text: str = ""
    status: str = "pending"  # consistent | conflict | review
    conflicts: list[dict] = field(default_factory=list)


def number_map(text: str) -> dict[tuple, str]:
    """Canonical (kind, value) -> raw for salient numbers and dates."""
    result: dict[tuple, str] = {}
    for token in fact_check.extract_tokens(fact_check.normalize(text), body_only=False):
        if token.value is None:
            continue
        if not (fact_check.salient(token.raw) or token.kind in ("month", "day")):
            continue
        result.setdefault((token.kind, round(token.value, 6)), token.raw)
    return result


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
    return conflicts


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
    return clips


def hms(seconds: float) -> str:
    return transcribe.srt_time(seconds)[:-4]


def write_report(
    target: Path,
    transcript: Path,
    model_name: str,
    clips: list[Clip],
    total_duration: float,
) -> None:
    consistent = [c for c in clips if c.status == "consistent"]
    conflicted = [c for c in clips if c.status == "conflict"]
    review = [c for c in clips if c.status == "review"]
    covered = sum(c.end - c.start for c in clips)
    lines = [
        "# 定向复核报告",
        "",
        f"- 主转录稿：`{transcript.name}`（FunASR）",
        f"- 复核引擎：`{model_name}`",
        f"- 复核片段：{len(clips)} 个，共 {covered / 60:.1f} 分钟"
        f"（占全长 {total_duration / 60:.1f} 分钟的 {covered / total_duration * 100:.0f}%）"
        if total_duration else f"- 复核片段：{len(clips)} 个",
        f"- 结果：一致 {len(consistent)}、分歧 {len(conflicted)}、待人工复核 {len(review)}",
        "",
        "双引擎一致的数字可视为可靠依据；下列分歧片段写入纪要前必须回听录音确认，",
        "无法确认的数字改用转录稿原文并在对话中向用户说明，不在纪要中标注“待核”。",
        "",
    ]
    if conflicted:
        lines.append("## 存在分歧的片段")
        lines.append("")
        for clip in conflicted:
            lines.append(f"### 片段 {clip.index}（{hms(clip.start)}–{hms(clip.end)}）")
            lines.append(f"- FunASR：{clip.funasr_text}")
            lines.append(f"- Qwen3-ASR：{clip.qwen_text}")
            for conflict in clip.conflicts:
                funasr_side = "、".join(conflict["funasr_only"]) or "（无）"
                qwen_side = "、".join(conflict["qwen_only"]) or "（无）"
                lines.append(f"- 分歧（{conflict['category']}）：FunASR 独有「{funasr_side}」；"
                             f"Qwen 独有「{qwen_side}」")
            lines.append("")
    if review:
        lines.append("## 待人工复核的片段（复核引擎未返回内容）")
        lines.append("")
        for clip in review:
            lines.append(f"- 片段 {clip.index}（{hms(clip.start)}–{hms(clip.end)}）：{clip.funasr_text[:60]}")
        lines.append("")
    if consistent:
        lines.append("## 双引擎一致的片段")
        lines.append("")
        for clip in consistent:
            lines.append(f"- 片段 {clip.index}（{hms(clip.start)}–{hms(clip.end)}）"
                         f"［{'、'.join(clip.reasons)}］{clip.funasr_text[:40]}")
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
    parser.add_argument("--language", default="Chinese")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda", "mps"], default="auto")
    parser.add_argument("--max-new-tokens", type=int, default=None)
    parser.add_argument("--pad", type=float, default=DEFAULT_PAD_SECONDS)
    parser.add_argument("--merge-gap", type=float, default=DEFAULT_MERGE_GAP_SECONDS)
    parser.add_argument("--max-clip", type=float, default=DEFAULT_MAX_CLIP_SECONDS)
    parser.add_argument("--all", action="store_true",
                        help="re-transcribe every segment (full dual-engine pass)")
    parser.add_argument("--dry-run", action="store_true",
                        help="plan and print the clips without loading any model")
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args()

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
    if not stamps:
        parser.error("转录 JSON 不含句级时间戳；请以 --diarize 或 --timestamps 重新转录。")
    duration = float(payload.get("duration_seconds")
                     or max(float(item.get("end", 0.0)) for item in stamps))
    terms = fact_check.collect_terms(args.glossary, args.term)

    clips = plan_clips(
        stamps, terms,
        select_all=args.all,
        pad=args.pad,
        merge_gap=args.merge_gap,
        max_clip=args.max_clip,
        duration=duration,
    )
    if not clips:
        print(json.dumps({"ok": True, "clips": 0,
                          "note": "未发现需要复核的高风险片段"}, ensure_ascii=False))
        return 0

    if args.dry_run:
        print(json.dumps({
            "ok": True,
            "dry_run": True,
            "clips": [
                {"index": c.index, "start": c.start, "end": c.end,
                 "duration": round(c.end - c.start, 1), "reasons": list(c.reasons),
                 "preview": c.funasr_text[:40]}
                for c in clips
            ],
            "covered_seconds": round(sum(c.end - c.start for c in clips), 1),
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
    max_clip_seconds = max(c.end - c.start for c in clips)
    model = Qwen3ASRModel.from_pretrained(
        args.model,
        dtype=dtype,
        device_map=device,
        max_inference_batch_size=1,
        max_new_tokens=args.max_new_tokens or transcribe.auto_max_new_tokens(max_clip_seconds),
    )
    context = " ".join(terms + ([args.context] if args.context.strip() else []))[:CONTEXT_CHAR_LIMIT]
    language = None if args.language.lower() in {"auto", "none", ""} else args.language

    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="mmp-refine-") as temp_dir:
        for clip in clips:
            checkpoint = checkpoint_dir / f"clip_{clip.index:04d}.json"
            cached_text: str | None = None
            if not args.no_resume and checkpoint.is_file():
                cached = json.loads(checkpoint.read_text(encoding="utf-8"))
                if (cached.get("model") == args.model
                        and abs(cached.get("start", -1) - clip.start) < 0.5
                        and abs(cached.get("end", -1) - clip.end) < 0.5):
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
                checkpoint.write_text(json.dumps({
                    "model": args.model,
                    "start": clip.start,
                    "end": clip.end,
                    "text": cached_text,
                }, ensure_ascii=False), encoding="utf-8")
            clip.qwen_text = cached_text
            if not clip.qwen_text:
                clip.status = "review"
            else:
                clip.conflicts = compare_texts(clip.funasr_text, clip.qwen_text, terms)
                clip.status = "conflict" if clip.conflicts else "consistent"
            transcribe.progress({"stage": "clip", "index": clip.index,
                                 "total": len(clips), "status": clip.status})

    report_json = output_dir / f"{stem}.refine.json"
    report_md = output_dir / f"{stem}.refine.md"
    report_json.write_text(json.dumps({
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "transcript": str(args.transcript),
        "source": str(args.source),
        "model": args.model,
        "device": device,
        "clips": [
            {"index": c.index, "start": c.start, "end": c.end,
             "reasons": list(c.reasons), "status": c.status,
             "funasr_text": c.funasr_text, "qwen_text": c.qwen_text,
             "conflicts": c.conflicts}
            for c in clips
        ],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(report_md, args.transcript, args.model, clips, duration)
    shutil.rmtree(checkpoint_dir, ignore_errors=True)

    summary = {
        "ok": True,
        "clips": len(clips),
        "consistent": sum(1 for c in clips if c.status == "consistent"),
        "conflict": sum(1 for c in clips if c.status == "conflict"),
        "review": sum(1 for c in clips if c.status == "review"),
        "covered_seconds": round(sum(c.end - c.start for c in clips), 1),
        "total_seconds": round(duration, 1),
        "elapsed_seconds": round(time.monotonic() - started, 1),
        "outputs": {"json": str(report_json), "md": str(report_md)},
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
