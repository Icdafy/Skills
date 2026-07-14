#!/usr/bin/env python3
"""Transcribe a local media file with Qwen3-ASR-0.6B and write reusable artifacts."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import wave


MODEL_DEFAULT = "Qwen/Qwen3-ASR-0.6B"
ALIGNER_DEFAULT = "Qwen/Qwen3-ForcedAligner-0.6B"


@dataclass
class Stamp:
    text: str
    start: float
    end: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="local audio or video path")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--language", default="auto", help="auto, Chinese, English, Cantonese, etc.")
    parser.add_argument("--context", default="", help="names and domain terms that may occur")
    parser.add_argument("--model", default=MODEL_DEFAULT)
    parser.add_argument("--aligner", default=ALIGNER_DEFAULT)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda", "mps"], default="auto")
    parser.add_argument("--timestamps", action="store_true")
    parser.add_argument("--offline", action="store_true", help="forbid model/network downloads")
    parser.add_argument("--clip-start", type=float, default=0.0)
    parser.add_argument("--clip-duration", type=float)
    parser.add_argument("--max-new-tokens", type=int, default=4096)
    return parser.parse_args()


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
    mps = getattr(torch_module.backends, "mps", None)
    if mps is not None and mps.is_available():
        return "mps", torch_module.float16
    return "cpu", torch_module.float32


def safe_stem(path: Path) -> str:
    stem = re.sub(r"[^\w.-]+", "_", path.stem, flags=re.UNICODE).strip("._")
    return stem or "transcript"


def prepare_wav(source: Path, target: Path, clip_start: float, clip_duration: float | None) -> None:
    import imageio_ffmpeg

    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-nostdin", "-hide_banner", "-loglevel", "error", "-y"]
    if clip_start > 0:
        cmd += ["-ss", str(clip_start)]
    cmd += ["-i", str(source)]
    if clip_duration is not None:
        if clip_duration <= 0:
            raise ValueError("--clip-duration must be positive")
        cmd += ["-t", str(clip_duration)]
    cmd += ["-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(target)]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg conversion failed: {proc.stderr.strip()}")


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as handle:
        return handle.getnframes() / float(handle.getframerate())


def extract_stamps(result) -> list[Stamp]:
    stamps: list[Stamp] = []
    for item in result.time_stamps or []:
        text = str(getattr(item, "text", "")).strip()
        start = float(getattr(item, "start_time", 0.0))
        end = float(getattr(item, "end_time", start))
        if text:
            stamps.append(Stamp(text=text, start=start, end=end))
    return stamps


def group_stamps(items: list[Stamp], max_seconds: float = 8.0, max_chars: int = 42) -> list[Stamp]:
    groups: list[Stamp] = []
    current: list[Stamp] = []
    for item in items:
        current.append(item)
        combined = "".join(x.text for x in current)
        span = current[-1].end - current[0].start
        punctuation = bool(re.search(r"[。！？!?；;]$", item.text))
        if span >= max_seconds or len(combined) >= max_chars or punctuation:
            groups.append(Stamp(text=combined, start=current[0].start, end=current[-1].end))
            current = []
    if current:
        groups.append(Stamp(text="".join(x.text for x in current), start=current[0].start, end=current[-1].end))
    return groups


def srt_time(seconds: float) -> str:
    millis = max(0, int(round(seconds * 1000)))
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def write_outputs(
    output_dir: Path,
    source: Path,
    text: str,
    language: str,
    device: str,
    model: str,
    duration: float,
    context: str,
    stamps: list[Stamp],
    sampled: bool,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = ".sample" if sampled else ""
    prefix = output_dir / f"{safe_stem(source)}{suffix}"
    paths = {
        "txt": Path(str(prefix) + ".txt"),
        "md": Path(str(prefix) + ".md"),
        "json": Path(str(prefix) + ".json"),
    }
    paths["txt"].write_text(text.strip() + "\n", encoding="utf-8")
    stamp_groups = group_stamps(stamps)
    md_lines = [
        "# Transcript",
        "",
        f"- Source: `{source.name}`",
        f"- Model: `{model}`",
        f"- Device: `{device}`",
        f"- Language: `{language}`",
        f"- Processed duration: `{duration:.2f} seconds`",
        "- Status: `raw ASR; not human-reviewed`",
        "",
    ]
    if stamp_groups:
        md_lines += ["## Timestamped transcript", ""]
        md_lines += [f"[{srt_time(x.start)[:-4]}–{srt_time(x.end)[:-4]}] {x.text}" for x in stamp_groups]
    else:
        md_lines += ["## Transcript", "", text.strip()]
    paths["md"].write_text("\n".join(md_lines).rstrip() + "\n", encoding="utf-8")
    payload = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": str(source),
        "model": model,
        "device": device,
        "language": language,
        "duration_seconds": round(duration, 3),
        "context_supplied": bool(context.strip()),
        "raw_asr": True,
        "text": text.strip(),
        "timestamps": [asdict(x) for x in stamps],
    }
    paths["json"].write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if stamp_groups:
        srt_path = Path(str(prefix) + ".srt")
        blocks = [
            f"{index}\n{srt_time(item.start)} --> {srt_time(item.end)}\n{item.text}"
            for index, item in enumerate(stamp_groups, start=1)
        ]
        srt_path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
        paths["srt"] = srt_path
    return {name: str(path) for name, path in paths.items()}


def main() -> int:
    args = parse_args()
    source = args.input.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    if not source.is_file():
        print(json.dumps({"ok": False, "error": f"input file not found: {source}"}, ensure_ascii=False))
        return 2
    if args.offline:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
    try:
        import torch
        from qwen_asr import Qwen3ASRModel
    except ImportError as exc:
        print(json.dumps({
            "ok": False,
            "error": f"runtime dependency missing: {exc}",
            "next": "run scripts/bootstrap_runtime.py --install, then invoke this script with the reported runtime Python",
        }, ensure_ascii=False, indent=2))
        return 3

    try:
        device, dtype = choose_device(torch, args.device)
        with tempfile.TemporaryDirectory(prefix="qwen3-asr-") as temp_dir:
            wav_path = Path(temp_dir) / "input.wav"
            prepare_wav(source, wav_path, args.clip_start, args.clip_duration)
            duration = wav_duration(wav_path)
            model_kwargs = {
                "dtype": dtype,
                "device_map": device,
                "max_inference_batch_size": 1,
                "max_new_tokens": args.max_new_tokens,
            }
            if args.timestamps:
                model_kwargs["forced_aligner"] = args.aligner
                model_kwargs["forced_aligner_kwargs"] = {"dtype": dtype, "device_map": device}
            model = Qwen3ASRModel.from_pretrained(args.model, **model_kwargs)
            language_arg = None if args.language.lower() in {"auto", "none", ""} else args.language
            results = model.transcribe(
                audio=str(wav_path),
                context=args.context,
                language=language_arg,
                return_time_stamps=args.timestamps,
            )
            if not results:
                raise RuntimeError("the model returned no result")
            result = results[0]
            transcript = str(result.text).strip()
            detected_language = str(result.language or language_arg or "unknown")
            stamps = extract_stamps(result) if args.timestamps else []
            outputs = write_outputs(
                output_dir=output_dir,
                source=source,
                text=transcript,
                language=detected_language,
                device=device,
                model=args.model,
                duration=duration,
                context=args.context,
                stamps=stamps,
                sampled=args.clip_duration is not None,
            )
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps({
        "ok": True,
        "model": args.model,
        "device": device,
        "language": detected_language,
        "duration_seconds": round(duration, 3),
        "timestamps": bool(stamps),
        "outputs": outputs,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
