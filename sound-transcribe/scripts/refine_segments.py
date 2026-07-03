"""Second-pass refinement of low-confidence segments (sound-transcribe v2).

Reads a schema-v2 transcript JSON, collects flagged segments, merges them
into padded time windows, re-transcribes only those windows with a larger
model, and splices the results back. Originals are archived under
metadata.refinements so nothing is silently lost.

Typical cost: ~20% of a full large-model run for near-large-model quality.
"""

import argparse
import datetime as dt
import json
import pathlib
import re
import sys

DEFAULT_REFINE_MODEL = "large-v3"

AVG_LOGPROB_FLOOR = -0.8
NO_SPEECH_CEIL = 0.6
COMPRESSION_CEIL = 2.4


def ensure_utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def add_local_package_paths() -> None:
    script_path = pathlib.Path(__file__).resolve()
    candidates = [
        pathlib.Path.cwd() / ".pydeps",
        script_path.parents[1] / ".pydeps",
        script_path.parents[2] / ".pydeps" if len(script_path.parents) > 2 else None,
    ]
    for candidate in candidates:
        if candidate and candidate.exists():
            sys.path.insert(0, str(candidate))


def format_time(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    whole = int(seconds)
    millis = int(round((seconds - whole) * 1000))
    if millis == 1000:
        whole += 1
        millis = 0
    hours, rem = divmod(whole, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def compute_flags(avg_logprob, no_speech_prob, compression_ratio, text: str) -> list:
    flags = []
    if avg_logprob is not None and avg_logprob < AVG_LOGPROB_FLOOR:
        flags.append("low_confidence")
    if no_speech_prob is not None and no_speech_prob > NO_SPEECH_CEIL:
        flags.append("maybe_non_speech")
    if compression_ratio is not None and compression_ratio > COMPRESSION_CEIL:
        flags.append("high_compression")
    if text and re.search(r"(.{2,12})\1{3,}", text):
        flags.append("repetition")
    return flags


def detect_device(device: str, compute_type: str):
    if device != "auto":
        if compute_type == "auto":
            compute_type = "float16" if device == "cuda" else "int8"
        return device, compute_type
    cuda_count = 0
    try:
        import ctranslate2

        cuda_count = ctranslate2.get_cuda_device_count()
    except Exception:
        cuda_count = 0
    if cuda_count > 0:
        return "cuda", ("float16" if compute_type == "auto" else compute_type)
    return "cpu", ("int8" if compute_type == "auto" else compute_type)


def build_windows(flagged: list, pad: float, merge_gap: float, duration) -> list:
    spans = sorted((max(0.0, item["start"] - pad), item["end"] + pad) for item in flagged)
    windows = []
    for start, end in spans:
        if duration:
            end = min(end, duration)
        if windows and start - windows[-1][1] <= merge_gap:
            windows[-1][1] = max(windows[-1][1], end)
        else:
            windows.append([start, end])
    return [(round(s, 2), round(e, 2)) for s, e in windows]


def clamp_windows_to_segments(windows: list, segments: list) -> list:
    """Shrink window edges so they never cut into a healthy segment.

    Replacement later deletes every segment overlapping a window, so a padded
    edge poking 0.5s into a long healthy neighbor would delete the whole
    neighbor while re-transcribing only its tail — text loss. Clamping the
    edge to the neighbor's boundary keeps deletion == coverage.
    """
    clamped = []
    for start, end in windows:
        dropped = False
        for item in segments:
            if item.get("flags") and not item.get("refined"):
                continue  # flagged segments are what the window is for
            if item["start"] <= start and item["end"] >= end:
                dropped = True  # healthy segment swallows the window entirely
                break
            if item["start"] < start < item["end"]:
                start = item["end"]  # pokes in from the left
            if item["start"] < end < item["end"]:
                end = item["start"]  # pokes in from the right
        if not dropped and end - start >= 0.5:
            clamped.append((round(start, 2), round(end, 2)))
    return clamped


def window_badness(window, segments: list) -> float:
    """Lower avg_logprob == worse == refine first."""
    start, end = window
    probs = [
        item["avg_logprob"]
        for item in segments
        if item.get("avg_logprob") is not None and item["start"] < end and item["end"] > start
    ]
    return min(probs) if probs else 0.0


def main() -> int:
    parser = argparse.ArgumentParser(description="Re-transcribe flagged windows with a larger model.")
    parser.add_argument("--audio", required=True, help="Original audio or video path.")
    parser.add_argument("--json", dest="json_path", required=True, help="Schema-v2 transcript JSON to refine.")
    parser.add_argument("--model", default=DEFAULT_REFINE_MODEL, help="Larger model for the second pass.")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--compute-type", default="auto")
    parser.add_argument("--beam-size", type=int, default=5)
    parser.add_argument("--pad", type=float, default=1.0, help="Padding seconds around each flagged segment.")
    parser.add_argument("--merge-gap", type=float, default=2.0, help="Merge windows closer than this many seconds.")
    parser.add_argument("--max-total", type=float, default=900.0,
                        help="Cap on total re-transcribed seconds; worst windows go first.")
    parser.add_argument("--dry-run", action="store_true", help="Only print the planned windows.")
    args = parser.parse_args()

    ensure_utf8_stdout()
    add_local_package_paths()

    json_path = pathlib.Path(args.json_path).resolve()
    audio_path = pathlib.Path(args.audio).resolve()
    if not json_path.exists():
        raise SystemExit(f"Transcript JSON not found: {json_path}")
    if not audio_path.exists():
        raise SystemExit(f"Audio file not found: {audio_path}")

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    metadata = payload.get("metadata", {})
    segments = payload.get("segments", [])
    if metadata.get("schema_version", 1) < 2:
        raise SystemExit("This JSON is schema v1 (no confidence data). Re-run transcribe_audio.py first.")

    flagged = [item for item in segments if item.get("flags") and not item.get("refined")]
    if not flagged:
        print("flagged=0 nothing_to_refine=true")
        return 0

    duration = metadata.get("duration")
    windows = build_windows(flagged, args.pad, args.merge_gap, duration)
    windows = clamp_windows_to_segments(windows, segments)
    if not windows:
        print("windows=0 nothing_to_refine=true")
        return 0
    windows.sort(key=lambda w: window_badness(w, segments))
    kept, dropped, total = [], [], 0.0
    for window in windows:
        length = window[1] - window[0]
        if total + length <= args.max_total:
            kept.append(window)
            total += length
        else:
            dropped.append(window)
    kept.sort()

    print(f"flagged_segments={len(flagged)} windows={len(windows)} "
          f"kept={len(kept)} dropped={len(dropped)} refine_seconds={total:.0f}", flush=True)
    for window in kept:
        print(f"window={format_time(window[0])}..{format_time(window[1])}", flush=True)
    if dropped:
        print(f"warning=windows_dropped_by_cap count={len(dropped)} "
              f"hint=raise --max-total to cover them", flush=True)
    if args.dry_run:
        return 0

    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise SystemExit(
            "Missing faster-whisper. Install it into the workspace with: "
            "python -m pip install --target .pydeps faster-whisper"
        ) from exc

    device, compute_type = detect_device(args.device, args.compute_type)
    try:
        model = WhisperModel(args.model, device=device, compute_type=compute_type)
    except Exception as exc:
        if device == "cuda":
            print(f"warning=cuda_load_failed fallback=cpu/int8 detail={exc}", flush=True)
            device, compute_type = "cpu", "int8"
            model = WhisperModel(args.model, device=device, compute_type=compute_type)
        else:
            raise
    print(f"refine_model={args.model} device={device} compute_type={compute_type}", flush=True)

    language = metadata.get("language")
    initial_prompt = (metadata.get("options") or {}).get("initial_prompt")
    refinements = metadata.setdefault("refinements", [])

    for win_start, win_end in kept:
        kwargs = {
            "beam_size": args.beam_size,
            "vad_filter": True,
            "word_timestamps": True,
            "condition_on_previous_text": False,
            "clip_timestamps": f"{win_start},{win_end}",
        }
        if language:
            kwargs["language"] = language
        if initial_prompt:
            kwargs["initial_prompt"] = initial_prompt
        seg_iter, _info = model.transcribe(str(audio_path), **kwargs)
        new_items = []
        for seg in seg_iter:
            text = seg.text.strip()
            if not text:
                continue
            new_items.append({
                "start": float(seg.start),
                "end": float(seg.end),
                "text": text,
                "avg_logprob": round(getattr(seg, "avg_logprob", 0.0) or 0.0, 4),
                "no_speech_prob": round(getattr(seg, "no_speech_prob", 0.0) or 0.0, 4),
                "compression_ratio": round(getattr(seg, "compression_ratio", 0.0) or 0.0, 4),
            })

        # Guard: some backends return clip-relative timestamps. If everything
        # sits inside the window's *length* rather than its absolute span,
        # shift by the window start.
        if new_items and win_start > 5.0:
            max_end = max(item["end"] for item in new_items)
            if max_end <= (win_end - win_start) + 2.0:
                for item in new_items:
                    item["start"] += win_start
                    item["end"] += win_start

        replaced = [item for item in segments if item["start"] < win_end and item["end"] > win_start]
        segments = [item for item in segments if item not in replaced]
        for item in new_items:
            speaker_votes = {}
            for old in replaced:
                if old.get("speaker"):
                    overlap = min(old["end"], item["end"]) - max(old["start"], item["start"])
                    if overlap > 0:
                        speaker_votes[old["speaker"]] = speaker_votes.get(old["speaker"], 0.0) + overlap
            entry = {
                "id": 0,
                "start": item["start"],
                "end": item["end"],
                "start_text": format_time(item["start"]),
                "end_text": format_time(item["end"]),
                "text": item["text"],
                "avg_logprob": item["avg_logprob"],
                "no_speech_prob": item["no_speech_prob"],
                "compression_ratio": item["compression_ratio"],
                "flags": compute_flags(item["avg_logprob"], item["no_speech_prob"],
                                       item["compression_ratio"], item["text"]),
                "refined": True,
            }
            if speaker_votes:
                entry["speaker"] = max(speaker_votes, key=speaker_votes.get)
            segments.append(entry)
        refinements.append({
            "window": [win_start, win_end],
            "model": args.model,
            "replaced": [{"start": r["start"], "end": r["end"], "text": r["text"]} for r in replaced],
            "new_count": len(new_items),
        })
        print(f"refined_window={format_time(win_start)}..{format_time(win_end)} "
              f"replaced={len(replaced)} new={len(new_items)}", flush=True)

    segments.sort(key=lambda item: item["start"])
    for index, item in enumerate(segments, start=1):
        item["id"] = index

    flagged_after = sum(1 for item in segments if item.get("flags"))
    metadata["refined_at"] = dt.datetime.now().isoformat(timespec="seconds")
    metadata["refine_model"] = args.model
    metadata.setdefault("counts", {})["segments"] = len(segments)
    metadata["counts"]["flagged"] = flagged_after
    payload["metadata"] = metadata
    payload["segments"] = segments
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"segments={len(segments)} flagged_after_refine={flagged_after}")
    print(f"json={json_path}")
    print("hint=re-run scripts/render_outputs.py to regenerate txt/md/srt/vtt/html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
