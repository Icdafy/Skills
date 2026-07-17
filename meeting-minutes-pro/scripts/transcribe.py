#!/usr/bin/env python3
"""Transcribe a local media file with FunASR (Paraformer) or Qwen3-ASR and write reusable artifacts.

Engines
-------
funasr  Default. Paraformer-zh + fsmn-vad + ct-punc pipeline from ModelScope.
        Handles hours-long audio via VAD segmentation, produces sentence
        timestamps at no extra cost, and supports optional speaker
        diarization (--diarize, cam++, with an optional --speakers count
        hint) and hotwords (--context). Long non-diarized audio is chunked
        at silences with per-chunk checkpoints so interrupted runs resume;
        diarized runs stay single-pass because cam++ clusters speakers per
        call and chunking would renumber them.
qwen    Qwen3-ASR (default 0.6B) via the qwen-asr Transformers backend.
        Recommended for multilingual or dialect-heavy recordings. Long audio
        is split at silences (ffmpeg silencedetect) into chunks that are
        transcribed sequentially with per-chunk checkpoints, so an
        interrupted run resumes instead of starting over.

Use --sample N to transcribe an N-second probe taken from the middle of the
recording (openings are usually greetings and mic checks); the result JSON
reports the measured realtime factor and a full-run time estimate.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import wave


QWEN_MODEL_DEFAULT = "Qwen/Qwen3-ASR-0.6B"
ALIGNER_DEFAULT = "Qwen/Qwen3-ForcedAligner-0.6B"
FUNASR_MODEL_DEFAULT = "paraformer-zh"
FUNASR_VAD_DEFAULT = "fsmn-vad"
FUNASR_PUNC_DEFAULT = "ct-punc"
FUNASR_SPK_DEFAULT = "cam++"

# Single-pass limits; longer audio is chunked at silences with per-chunk
# checkpoints. Diarized funasr runs are never chunked: cam++ clusters
# speakers per generate() call, so chunking would renumber 说话人N labels.
QWEN_SINGLE_PASS_SECONDS = 600.0
QWEN_CHUNK_TARGET_SECONDS = 120.0
QWEN_CHUNK_MIN_SECONDS = 30.0
QWEN_CHUNK_MAX_SECONDS = 180.0
FUNASR_SINGLE_PASS_SECONDS = 1800.0
FUNASR_CHUNK_TARGET_SECONDS = 600.0
FUNASR_CHUNK_MIN_SECONDS = 240.0
FUNASR_CHUNK_MAX_SECONDS = 900.0


@dataclass
class Stamp:
    text: str
    start: float
    end: float
    speaker: str | None = None


@dataclass
class TranscribeResult:
    text: str
    language: str
    stamps: list[Stamp] = field(default_factory=list)
    speakers: bool = False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--input", required=True, type=Path, help="local audio or video path")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--engine", choices=["funasr", "qwen"], default="funasr",
                        help="funasr: Chinese meetings, long audio, diarization (default); "
                             "qwen: multilingual or dialect recordings")
    parser.add_argument("--language", default="auto", help="auto, Chinese, English, Cantonese, etc.")
    parser.add_argument("--context", default="", help="names and domain terms that may occur (hotwords)")
    parser.add_argument("--model", default=None,
                        help="engine model override; defaults to paraformer-zh or Qwen/Qwen3-ASR-0.6B")
    parser.add_argument("--aligner", default=ALIGNER_DEFAULT, help="qwen timestamps aligner model")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda", "mps"], default="auto")
    parser.add_argument("--timestamps", action="store_true", help="emit sentence timestamps and SRT")
    parser.add_argument("--diarize", action="store_true",
                        help="funasr only: label speaker turns with the cam++ model")
    parser.add_argument("--speakers", type=int, default=None,
                        help="funasr with --diarize: known participant count passed to "
                             "cam++ clustering (preset_spk_num) for steadier speaker labels")
    parser.add_argument("--enhance", action="store_true",
                        help="preprocess audio with loudness normalization and light denoising")
    parser.add_argument("--offline", action="store_true", help="forbid model/network downloads")
    parser.add_argument("--clip-start", type=float, default=0.0)
    parser.add_argument("--clip-duration", type=float)
    parser.add_argument("--sample", type=float, default=None,
                        help="transcribe an N-second probe from the middle of the recording "
                             "and report the measured realtime factor plus a full-run estimate")
    parser.add_argument("--max-new-tokens", type=int, default=None,
                        help="qwen only; default scales with audio length per chunk")
    parser.add_argument("--chunk-seconds", type=float, default=None,
                        help="target chunk length for long-audio splitting "
                             "(defaults: qwen 120s, funasr 600s)")
    parser.add_argument("--no-resume", action="store_true",
                        help="ignore existing chunk checkpoints and retranscribe")
    return parser.parse_args()


def progress(payload: dict) -> None:
    print(json.dumps({"progress": payload}, ensure_ascii=False), file=sys.stderr, flush=True)


def safe_stem(path: Path) -> str:
    stem = re.sub(r"[^\w.-]+", "_", path.stem, flags=re.UNICODE).strip("._")
    return stem or "transcript"


def ffmpeg_exe() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def prepare_wav(
    source: Path,
    target: Path,
    clip_start: float = 0.0,
    clip_duration: float | None = None,
    enhance: bool = False,
) -> None:
    cmd = [ffmpeg_exe(), "-nostdin", "-hide_banner", "-loglevel", "error", "-y"]
    if clip_start > 0:
        cmd += ["-ss", str(clip_start)]
    cmd += ["-i", str(source)]
    if clip_duration is not None:
        if clip_duration <= 0:
            raise ValueError("--clip-duration must be positive")
        cmd += ["-t", str(clip_duration)]
    if enhance:
        cmd += ["-af", "afftdn=nf=-25,loudnorm=I=-16:TP=-1.5:LRA=11"]
    cmd += ["-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(target)]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg conversion failed: {proc.stderr.strip()}")


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as handle:
        return handle.getnframes() / float(handle.getframerate())


def media_duration(path: Path) -> float | None:
    """Parse the container duration from the ffmpeg -i header without decoding.

    Best-effort: runs before the main try-block, so it must never raise —
    a missing runtime dependency should surface later as a clean JSON error.
    """
    try:
        proc = subprocess.run(
            [ffmpeg_exe(), "-nostdin", "-hide_banner", "-i", str(path)],
            capture_output=True, text=True, check=False,
        )
    except Exception:
        return None
    match = re.search(r"Duration:\s*(\d+):(\d{2}):(\d{2}(?:\.\d+)?)", proc.stderr)
    if not match:
        return None
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def detect_silences(wav_path: Path) -> list[tuple[float, float]]:
    """Return (start, end) silence intervals using ffmpeg silencedetect."""
    cmd = [
        ffmpeg_exe(), "-nostdin", "-hide_banner", "-i", str(wav_path),
        "-af", "silencedetect=noise=-35dB:d=0.4", "-f", "null", "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    silences: list[tuple[float, float]] = []
    start: float | None = None
    for line in proc.stderr.splitlines():
        begin = re.search(r"silence_start:\s*([0-9.]+)", line)
        if begin:
            start = float(begin.group(1))
            continue
        finish = re.search(r"silence_end:\s*([0-9.]+)", line)
        if finish and start is not None:
            silences.append((start, float(finish.group(1))))
            start = None
    return silences


def plan_chunks(
    duration: float,
    silences: list[tuple[float, float]],
    target: float,
    minimum: float,
    maximum: float,
) -> list[tuple[float, float]]:
    """Split [0, duration] at silence midpoints near multiples of the target length."""
    target = min(max(target, minimum), maximum)
    midpoints = sorted((a + b) / 2 for a, b in silences)
    chunks: list[tuple[float, float]] = []
    cursor = 0.0
    while duration - cursor > maximum:
        ideal = cursor + target
        low, high = cursor + minimum, cursor + maximum
        candidates = [m for m in midpoints if low <= m <= high]
        cut = min(candidates, key=lambda m: abs(m - ideal)) if candidates else high
        chunks.append((cursor, cut))
        cursor = cut
    chunks.append((cursor, duration))
    return chunks


def choose_device(torch_module, requested: str) -> tuple[str, object]:
    if requested == "cuda":
        if not torch_module.cuda.is_available():
            raise RuntimeError("CUDA was requested but is unavailable")
        return "cuda:0", torch_module.bfloat16
    if requested == "mps":
        available = bool(getattr(torch_module.backends, "mps", None)) and torch_module.backends.mps.is_available()
        if not available:
            raise RuntimeError("MPS was requested but is unavailable")
        return "mps", torch_module.float16
    if requested == "cpu":
        return "cpu", torch_module.float32
    if torch_module.cuda.is_available():
        return "cuda:0", torch_module.bfloat16
    # MPS operator coverage is unreliable for these models; auto prefers CPU on
    # Apple hardware and users may opt in explicitly with --device mps.
    return "cpu", torch_module.float32


def auto_max_new_tokens(chunk_seconds: float) -> int:
    # Mandarin speech peaks around 6 chars/second; leave generous headroom.
    return min(8192, max(1024, int(chunk_seconds * 10)))


# ---------------------------------------------------------------------------
# qwen engine
# ---------------------------------------------------------------------------

def run_qwen(args: argparse.Namespace, wav_path: Path, duration: float, checkpoint_dir: Path) -> TranscribeResult:
    try:
        import torch
        from qwen_asr import Qwen3ASRModel
    except ImportError as exc:
        raise RuntimeError(
            f"qwen runtime dependency missing: {exc}; "
            "run scripts/bootstrap_runtime.py --install --engine qwen, "
            "then invoke this script with the reported runtime Python"
        ) from exc

    device, dtype = choose_device(torch, args.device)
    model_name = args.model or QWEN_MODEL_DEFAULT
    single_pass = duration <= QWEN_SINGLE_PASS_SECONDS or args.clip_duration is not None
    if single_pass:
        chunks = [(0.0, duration)]
    else:
        progress({"stage": "plan", "engine": "qwen", "duration": round(duration, 1)})
        chunks = plan_chunks(
            duration,
            detect_silences(wav_path),
            args.chunk_seconds or QWEN_CHUNK_TARGET_SECONDS,
            QWEN_CHUNK_MIN_SECONDS,
            QWEN_CHUNK_MAX_SECONDS,
        )

    max_chunk = max(end - start for start, end in chunks)
    model_kwargs = {
        "dtype": dtype,
        "device_map": device,
        "max_inference_batch_size": 1,
        "max_new_tokens": args.max_new_tokens or auto_max_new_tokens(max_chunk),
    }
    if args.timestamps:
        model_kwargs["forced_aligner"] = args.aligner
        model_kwargs["forced_aligner_kwargs"] = {"dtype": dtype, "device_map": device}
    model = Qwen3ASRModel.from_pretrained(model_name, **model_kwargs)
    language_arg = None if args.language.lower() in {"auto", "none", ""} else args.language

    if not single_pass:
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

    texts: list[str] = []
    stamps: list[Stamp] = []
    detected_language = language_arg or "unknown"
    with tempfile.TemporaryDirectory(prefix="qwen3-chunks-") as temp_dir:
        for index, (start, end) in enumerate(chunks, start=1):
            checkpoint = checkpoint_dir / f"chunk_{index:04d}.json"
            if not single_pass and not args.no_resume and checkpoint.is_file():
                cached = json.loads(checkpoint.read_text(encoding="utf-8"))
                if (cached.get("engine", "qwen") == "qwen"
                        and abs(cached.get("start", -1) - start) < 0.5
                        and abs(cached.get("end", -1) - end) < 0.5):
                    texts.append(cached["text"])
                    stamps.extend(Stamp(**item) for item in cached.get("stamps", []))
                    if cached.get("language"):
                        detected_language = cached["language"]
                    progress({"stage": "chunk", "index": index, "total": len(chunks), "cached": True})
                    continue
            if single_pass:
                chunk_wav = wav_path
            else:
                chunk_wav = Path(temp_dir) / f"chunk_{index:04d}.wav"
                prepare_wav(wav_path, chunk_wav, clip_start=start, clip_duration=end - start)
            results = model.transcribe(
                audio=str(chunk_wav),
                context=args.context,
                language=language_arg,
                return_time_stamps=args.timestamps,
            )
            if not results:
                raise RuntimeError(f"the model returned no result for chunk {index}")
            result = results[0]
            chunk_text = str(result.text).strip()
            detected_language = str(result.language or language_arg or detected_language)
            chunk_stamps: list[Stamp] = []
            if args.timestamps:
                for item in result.time_stamps or []:
                    text = str(getattr(item, "text", "")).strip()
                    if not text:
                        continue
                    stamp_start = float(getattr(item, "start_time", 0.0)) + start
                    stamp_end = float(getattr(item, "end_time", stamp_start - start)) + start
                    chunk_stamps.append(Stamp(text=text, start=stamp_start, end=stamp_end))
            texts.append(chunk_text)
            stamps.extend(chunk_stamps)
            if not single_pass:
                checkpoint.write_text(json.dumps({
                    "engine": "qwen",
                    "start": start,
                    "end": end,
                    "language": detected_language,
                    "text": chunk_text,
                    "stamps": [asdict(x) for x in chunk_stamps],
                }, ensure_ascii=False), encoding="utf-8")
            progress({"stage": "chunk", "index": index, "total": len(chunks), "cached": False})

    return TranscribeResult(
        text="\n".join(t for t in texts if t),
        language=detected_language,
        stamps=stamps,
    )


# ---------------------------------------------------------------------------
# funasr engine
# ---------------------------------------------------------------------------

def funasr_device(requested: str) -> str:
    try:
        import torch
    except ImportError:
        return "cpu"
    if requested == "cuda" or (requested == "auto" and torch.cuda.is_available()):
        return "cuda:0"
    return "cpu"


def run_funasr(
    args: argparse.Namespace, wav_path: Path, duration: float, checkpoint_dir: Path
) -> TranscribeResult:
    try:
        from funasr import AutoModel
    except ImportError as exc:
        raise RuntimeError(
            f"funasr runtime dependency missing: {exc}; "
            "run scripts/bootstrap_runtime.py --install --engine funasr, "
            "then invoke this script with the reported runtime Python"
        ) from exc

    device = funasr_device(args.device)
    want_sentences = args.timestamps or args.diarize
    # cam++ clusters speakers per generate() call, so diarized recordings keep
    # a single pass to hold 说话人N numbering consistent end to end.
    single_pass = (
        args.diarize
        or args.clip_duration is not None
        or duration <= FUNASR_SINGLE_PASS_SECONDS
    )
    if single_pass:
        chunks = [(0.0, duration)]
        if args.diarize and duration > FUNASR_SINGLE_PASS_SECONDS:
            progress({"stage": "plan", "engine": "funasr", "single_pass": True,
                      "note": "diarization runs in one pass to keep speaker labels consistent"})
    else:
        progress({"stage": "plan", "engine": "funasr", "duration": round(duration, 1)})
        chunks = plan_chunks(
            duration,
            detect_silences(wav_path),
            args.chunk_seconds or FUNASR_CHUNK_TARGET_SECONDS,
            FUNASR_CHUNK_MIN_SECONDS,
            FUNASR_CHUNK_MAX_SECONDS,
        )
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

    model_kwargs = {
        "model": args.model or FUNASR_MODEL_DEFAULT,
        "vad_model": FUNASR_VAD_DEFAULT,
        "vad_kwargs": {"max_single_segment_time": 30000},
        "punc_model": FUNASR_PUNC_DEFAULT,
        "device": device,
        "disable_update": True,
        "disable_pbar": True,
    }
    if want_sentences:
        # Sentence-level segments come from the speaker pipeline; speaker labels
        # are only surfaced when --diarize was requested.
        model_kwargs["spk_model"] = FUNASR_SPK_DEFAULT
    progress({"stage": "load", "engine": "funasr", "device": device})
    model = AutoModel(**model_kwargs)

    texts: list[str] = []
    stamps: list[Stamp] = []
    with tempfile.TemporaryDirectory(prefix="funasr-chunks-") as temp_dir:
        for index, (start, end) in enumerate(chunks, start=1):
            checkpoint = checkpoint_dir / f"chunk_{index:04d}.json"
            if not single_pass and not args.no_resume and checkpoint.is_file():
                cached = json.loads(checkpoint.read_text(encoding="utf-8"))
                if (cached.get("engine") == "funasr"
                        and abs(cached.get("start", -1) - start) < 0.5
                        and abs(cached.get("end", -1) - end) < 0.5):
                    texts.append(cached["text"])
                    stamps.extend(Stamp(**item) for item in cached.get("stamps", []))
                    progress({"stage": "chunk", "index": index, "total": len(chunks), "cached": True})
                    continue
            if single_pass:
                chunk_wav = wav_path
            else:
                chunk_wav = Path(temp_dir) / f"chunk_{index:04d}.wav"
                prepare_wav(wav_path, chunk_wav, clip_start=start, clip_duration=end - start)
            generate_kwargs = {"input": str(chunk_wav), "batch_size_s": 300}
            if args.context.strip():
                generate_kwargs["hotword"] = args.context.strip()
            if args.diarize and args.speakers:
                # Known participant count constrains the cam++ clustering.
                generate_kwargs["preset_spk_num"] = args.speakers
            results = model.generate(**generate_kwargs)
            if not results:
                raise RuntimeError(f"the model returned no result for chunk {index}")
            result = results[0]
            chunk_text = str(result.get("text", "")).strip()
            chunk_stamps: list[Stamp] = []
            for sentence in result.get("sentence_info") or []:
                sentence_text = str(sentence.get("text", "")).strip()
                if not sentence_text:
                    continue
                speaker = None
                if args.diarize and sentence.get("spk") is not None:
                    speaker = f"说话人{int(sentence['spk']) + 1}"
                chunk_stamps.append(Stamp(
                    text=sentence_text,
                    start=start + float(sentence.get("start", 0)) / 1000.0,
                    end=start + float(sentence.get("end", 0)) / 1000.0,
                    speaker=speaker,
                ))
            if not chunk_text and chunk_stamps:
                chunk_text = "".join(x.text for x in chunk_stamps)
            texts.append(chunk_text)
            stamps.extend(chunk_stamps)
            if not single_pass:
                checkpoint.write_text(json.dumps({
                    "engine": "funasr",
                    "start": start,
                    "end": end,
                    "text": chunk_text,
                    "stamps": [asdict(x) for x in chunk_stamps],
                }, ensure_ascii=False), encoding="utf-8")
                progress({"stage": "chunk", "index": index, "total": len(chunks), "cached": False})

    return TranscribeResult(
        text="\n".join(t for t in texts if t),
        language="Chinese" if args.language.lower() in {"auto", "none", ""} else args.language,
        stamps=stamps if want_sentences else [],
        speakers=args.diarize and any(x.speaker for x in stamps),
    )


# ---------------------------------------------------------------------------
# outputs
# ---------------------------------------------------------------------------

def group_stamps(items: list[Stamp], max_seconds: float = 8.0, max_chars: int = 42) -> list[Stamp]:
    groups: list[Stamp] = []
    current: list[Stamp] = []
    for item in items:
        if current and item.speaker != current[-1].speaker:
            groups.append(Stamp(
                text="".join(x.text for x in current),
                start=current[0].start, end=current[-1].end, speaker=current[0].speaker,
            ))
            current = []
        current.append(item)
        combined = "".join(x.text for x in current)
        span = current[-1].end - current[0].start
        punctuation = bool(re.search(r"[。！？!?；;]$", item.text))
        if span >= max_seconds or len(combined) >= max_chars or punctuation:
            groups.append(Stamp(text=combined, start=current[0].start, end=current[-1].end,
                                speaker=current[0].speaker))
            current = []
    if current:
        groups.append(Stamp(text="".join(x.text for x in current), start=current[0].start,
                            end=current[-1].end, speaker=current[0].speaker))
    return groups


def srt_time(seconds: float) -> str:
    millis = max(0, int(round(seconds * 1000)))
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def stamp_label(item: Stamp) -> str:
    prefix = f"【{item.speaker}】" if item.speaker else ""
    return f"[{srt_time(item.start)[:-4]}–{srt_time(item.end)[:-4]}]{prefix} {item.text}"


def write_outputs(
    output_dir: Path,
    source: Path,
    outcome: TranscribeResult,
    engine: str,
    device: str,
    model: str,
    duration: float,
    context: str,
    sampled: bool,
    extra: dict | None = None,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = ".sample" if sampled else ""
    prefix = output_dir / f"{safe_stem(source)}{suffix}"
    paths = {
        "txt": Path(str(prefix) + ".txt"),
        "md": Path(str(prefix) + ".md"),
        "json": Path(str(prefix) + ".json"),
    }
    paths["txt"].write_text(outcome.text.strip() + "\n", encoding="utf-8")
    stamp_groups = group_stamps(outcome.stamps)
    md_lines = [
        "# Transcript",
        "",
        f"- Source: `{source.name}`",
        f"- Engine: `{engine}`",
        f"- Model: `{model}`",
        f"- Device: `{device}`",
        f"- Language: `{outcome.language}`",
        f"- Processed duration: `{duration:.2f} seconds`",
        f"- Speaker labels: `{'yes' if outcome.speakers else 'no'}`",
        "- Status: `raw ASR; not human-reviewed`",
        "",
    ]
    if stamp_groups:
        md_lines += ["## Timestamped transcript", ""]
        md_lines += [stamp_label(x) for x in stamp_groups]
    else:
        md_lines += ["## Transcript", "", outcome.text.strip()]
    paths["md"].write_text("\n".join(md_lines).rstrip() + "\n", encoding="utf-8")
    payload = {
        "schema_version": 2,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": str(source),
        "engine": engine,
        "model": model,
        "device": device,
        "language": outcome.language,
        "duration_seconds": round(duration, 3),
        "context_supplied": bool(context.strip()),
        "speaker_labels": outcome.speakers,
        "raw_asr": True,
        "text": outcome.text.strip(),
        "timestamps": [asdict(x) for x in outcome.stamps],
    }
    payload.update(extra or {})
    paths["json"].write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if stamp_groups:
        srt_path = Path(str(prefix) + ".srt")
        blocks = []
        for index, item in enumerate(stamp_groups, start=1):
            speaker = f"【{item.speaker}】" if item.speaker else ""
            blocks.append(f"{index}\n{srt_time(item.start)} --> {srt_time(item.end)}\n{speaker}{item.text}")
        srt_path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
        paths["srt"] = srt_path
    return {name: str(path) for name, path in paths.items()}


def emit_eta(output_dir: Path, source: Path, duration: float) -> None:
    """Report an ETA for the full run based on an earlier --sample probe."""
    sample_json = output_dir / f"{safe_stem(source)}.sample.json"
    if not sample_json.is_file():
        return
    try:
        rtf = json.loads(sample_json.read_text(encoding="utf-8")).get("realtime_factor")
    except Exception:
        return
    if rtf:
        progress({
            "stage": "eta",
            "estimated_minutes": round(duration * float(rtf) / 60, 1),
            "based_on": sample_json.name,
        })


def main() -> int:
    args = parse_args()
    source = args.input.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    if not source.is_file():
        print(json.dumps({"ok": False, "error": f"input file not found: {source}"}, ensure_ascii=False))
        return 2
    if args.diarize and args.engine != "funasr":
        print(json.dumps({"ok": False, "error": "--diarize requires --engine funasr"}, ensure_ascii=False))
        return 2
    if args.speakers is not None:
        if args.speakers < 1:
            print(json.dumps({"ok": False, "error": "--speakers must be a positive integer"}, ensure_ascii=False))
            return 2
        if not args.diarize:
            print(json.dumps({"ok": False, "error": "--speakers requires --diarize"}, ensure_ascii=False))
            return 2
    if args.offline:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"

    full_duration = media_duration(source)
    if args.sample is not None:
        if args.sample <= 0:
            print(json.dumps({"ok": False, "error": "--sample must be positive"}, ensure_ascii=False))
            return 2
        args.clip_duration = args.sample
        # Probe the middle of the recording: openings are usually greetings,
        # introductions, and microphone checks that misrepresent audio quality.
        if full_duration and full_duration > args.sample * 2:
            args.clip_start = max(0.0, full_duration * 0.4)
        else:
            args.clip_start = 0.0

    try:
        with tempfile.TemporaryDirectory(prefix="mmp-asr-") as temp_dir:
            wav_path = Path(temp_dir) / "input.wav"
            prepare_wav(source, wav_path, args.clip_start, args.clip_duration, enhance=args.enhance)
            duration = wav_duration(wav_path)
            sampled = args.clip_duration is not None
            checkpoint_dir = output_dir / f"{safe_stem(source)}.chunks"
            if not sampled:
                emit_eta(output_dir, source, duration)
            started = time.monotonic()
            if args.engine == "funasr":
                outcome = run_funasr(args, wav_path, duration, checkpoint_dir)
                device = funasr_device(args.device)
                model_name = args.model or FUNASR_MODEL_DEFAULT
            else:
                outcome = run_qwen(args, wav_path, duration, checkpoint_dir)
                model_name = args.model or QWEN_MODEL_DEFAULT
                device = "cpu"
                try:
                    import torch

                    device = choose_device(torch, args.device)[0]
                except Exception:
                    pass
            elapsed = time.monotonic() - started
            realtime_factor = round(elapsed / duration, 3) if duration else None
            extra = {
                "elapsed_seconds": round(elapsed, 1),
                "realtime_factor": realtime_factor,
            }
            if full_duration:
                extra["media_duration_seconds"] = round(full_duration, 3)
            if sampled and realtime_factor and full_duration:
                extra["estimated_full_run_minutes"] = round(
                    full_duration * realtime_factor / 60, 1
                )
            outputs = write_outputs(
                output_dir=output_dir,
                source=source,
                outcome=outcome,
                engine=args.engine,
                device=device,
                model=model_name,
                duration=duration,
                context=args.context,
                sampled=sampled,
                extra=extra,
            )
            if not sampled:
                # Outputs are safely on disk; the per-chunk checkpoints only
                # exist to resume an interrupted transcription. Sample probes
                # never write checkpoints and must not delete a full run's.
                shutil.rmtree(checkpoint_dir, ignore_errors=True)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps({
        "ok": True,
        "engine": args.engine,
        "model": model_name,
        "device": device,
        "language": outcome.language,
        "duration_seconds": round(duration, 3),
        "timestamps": bool(outcome.stamps),
        "speaker_labels": outcome.speakers,
        "outputs": outputs,
        **extra,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
