"""Transcribe audio/video with faster-whisper (sound-transcribe v2).

Upgrades over v1:
- VAD filtering on by default (turn off with --no-vad)
- condition_on_previous_text off by default (turn on with --condition)
- GPU auto-detection with graceful CPU fallback
- Batched inference pipeline when available (3-4x faster)
- Glossary / hotword / initial-prompt injection for domain terms
- Per-segment confidence capture (avg_logprob / no_speech_prob /
  compression_ratio) with hallucination flagging
- Incremental JSONL persistence and --resume for long recordings
"""

import argparse
import datetime as dt
import inspect
import json
import pathlib
import re
import sys

SCHEMA_VERSION = 2
DEFAULT_MODEL = "large-v3-turbo"
DEFAULT_ZH_PROMPT = "以下是普通话的句子，使用简体中文和标点符号。"

# Segments beyond these thresholds get flagged for human review / refinement.
AVG_LOGPROB_FLOOR = -0.8
NO_SPEECH_CEIL = 0.6
COMPRESSION_CEIL = 2.4
REFINE_HINT_RATIO = 0.15


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


def format_srt_time(seconds: float) -> str:
    return format_time(seconds).replace(".", ",")


def make_output_paths(prefix: pathlib.Path) -> dict:
    prefix.parent.mkdir(parents=True, exist_ok=True)
    return {
        "txt": pathlib.Path(f"{prefix}.txt"),
        "md": pathlib.Path(f"{prefix}.md"),
        "srt": pathlib.Path(f"{prefix}.srt"),
        "json": pathlib.Path(f"{prefix}.json"),
        "jsonl": pathlib.Path(f"{prefix}.segments.jsonl"),
    }


def resolve_model_value(model: str) -> str:
    try:
        model_path = pathlib.Path(model)
        if model_path.exists():
            return str(model_path.resolve())
    except OSError:
        pass
    return model


def read_glossary(path: str) -> list:
    terms = []
    text = pathlib.Path(path).read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        for term in re.split(r"[,，、;；]", line):
            term = term.strip()
            if term and term not in terms:
                terms.append(term)
    return terms


def build_initial_prompt(language, user_prompt, glossary_terms):
    parts = []
    if user_prompt:
        parts.append(user_prompt)
    elif (language or "").startswith("zh"):
        parts.append(DEFAULT_ZH_PROMPT)
    if glossary_terms:
        parts.append("可能出现的词汇：" + "、".join(glossary_terms[:40]) + "。")
    prompt = "".join(parts)
    return prompt[:400] if prompt else None


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


def load_model(model_value: str, device: str, compute_type: str):
    from faster_whisper import WhisperModel

    try:
        return WhisperModel(model_value, device=device, compute_type=compute_type), device, compute_type
    except Exception as exc:
        if device == "cuda":
            print(f"warning=cuda_load_failed fallback=cpu/int8 detail={exc}", flush=True)
            return WhisperModel(model_value, device="cpu", compute_type="int8"), "cpu", "int8"
        raise


def filter_kwargs(func, kwargs: dict):
    try:
        allowed = set(inspect.signature(func).parameters)
    except (TypeError, ValueError):
        return dict(kwargs), []
    filtered = {k: v for k, v in kwargs.items() if k in allowed}
    dropped = sorted(k for k in kwargs if k not in allowed)
    return filtered, dropped


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


def load_existing_segments(jsonl_path: pathlib.Path) -> list:
    segments = []
    if not jsonl_path.exists():
        return segments
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict) and "start" in item and "end" in item:
            segments.append(item)
    return segments


def write_outputs(paths: dict, segments: list, metadata: dict) -> None:
    plain_text = "\n".join(item["text"] for item in segments if item["text"])
    paths["txt"].write_text(plain_text + ("\n" if plain_text else ""), encoding="utf-8")

    payload = {"metadata": metadata, "segments": segments}
    paths["json"].write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    flagged = [item for item in segments if item.get("flags")]
    md_lines = [
        "# 语音转录",
        "",
        f"- 音频文件: `{metadata['audio_file']}`",
        f"- 模型: `{metadata['model']}`",
        f"- 设备/精度: `{metadata['device']}/{metadata['compute_type']}`",
        f"- 推理模式: `{metadata['mode']}`",
        f"- 检测语言: `{metadata['language']}` (置信度 {metadata['language_probability']:.4f})",
        f"- 音频时长: `{format_time(metadata['duration'])}`" if metadata.get("duration") else "- 音频时长: `未知`",
        f"- 段落数: `{len(segments)}`，其中低置信标记 `{len(flagged)}` 段（⚠ 标注，见待核实事项）",
        f"- 生成时间: `{metadata['generated_at']}`",
        "",
        "## 带时间戳文本",
        "",
    ]
    for item in segments:
        if not item["text"]:
            continue
        speaker = f"**{item['speaker']}**：" if item.get("speaker") else ""
        warn = f" ⚠({','.join(item['flags'])})" if item.get("flags") else ""
        md_lines.append(f"[{item['start_text']} - {item['end_text']}] {speaker}{item['text']}{warn}")
    if flagged:
        md_lines += ["", "## 待核实事项", ""]
        for item in flagged:
            md_lines.append(f"- [{item['start_text']}] {item['text']} （{','.join(item['flags'])}）")
    paths["md"].write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    srt_blocks = []
    for index, item in enumerate((item for item in segments if item["text"]), start=1):
        srt_blocks.append(
            f"{index}\n{format_srt_time(item['start'])} --> {format_srt_time(item['end'])}\n{item['text']}"
        )
    paths["srt"].write_text("\n\n".join(srt_blocks) + ("\n" if srt_blocks else ""), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Transcribe audio/video with faster-whisper (v2).")
    parser.add_argument("--audio", required=True, help="Input audio or video path.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model name or local CTranslate2 model path.")
    parser.add_argument("--out-prefix", required=True, help="Output prefix without extension.")
    parser.add_argument("--language", default=None, help="Language code such as zh or en. Omit for auto-detect.")
    parser.add_argument("--clip", default=None, help='Optional clip_timestamps value, e.g. "0,60". Forces sequential mode.')
    parser.add_argument("--beam-size", type=int, default=5)
    parser.add_argument("--device", default="auto", help="auto / cpu / cuda")
    parser.add_argument("--compute-type", default="auto", help="auto / int8 / float16 / int8_float16 ...")
    parser.add_argument("--no-vad", action="store_true", help="Disable VAD filtering (on by default).")
    parser.add_argument("--condition", action="store_true",
                        help="Enable condition_on_previous_text (off by default to avoid repetition loops).")
    parser.add_argument("--no-word-timestamps", action="store_true",
                        help="Disable word timestamps (faster, but subtitle re-splitting degrades).")
    parser.add_argument("--initial-prompt", default=None, help="Custom initial prompt to bias decoding.")
    parser.add_argument("--glossary", default=None, help="Path to a hotword/glossary file (one term per line).")
    parser.add_argument("--no-batched", action="store_true", help="Disable batched inference pipeline.")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--resume", action="store_true",
                        help="Resume from existing .segments.jsonl (continue after the last finished segment).")
    args = parser.parse_args()

    ensure_utf8_stdout()
    add_local_package_paths()
    try:
        from faster_whisper import WhisperModel  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "Missing faster-whisper. Install it into the workspace with: "
            "python -m pip install --target .pydeps faster-whisper"
        ) from exc

    audio_path = pathlib.Path(args.audio).resolve()
    if not audio_path.exists():
        raise SystemExit(f"Audio file not found: {audio_path}")

    model_value = resolve_model_value(args.model)
    out_prefix = pathlib.Path(args.out_prefix).resolve()
    paths = make_output_paths(out_prefix)

    glossary_terms = read_glossary(args.glossary) if args.glossary else []
    initial_prompt = build_initial_prompt(args.language, args.initial_prompt, glossary_terms)

    existing_segments = []
    clip_value = args.clip
    if args.resume:
        existing_segments = load_existing_segments(paths["jsonl"])
        if existing_segments:
            resume_from = max(item["end"] for item in existing_segments)
            clip_value = f"{resume_from:.2f}"
            print(f"resume_from={format_time(resume_from)} existing_segments={len(existing_segments)}", flush=True)
        else:
            print("resume=no_existing_segments (starting fresh)", flush=True)
    elif paths["jsonl"].exists():
        paths["jsonl"].unlink()

    device, compute_type = detect_device(args.device, args.compute_type)
    model, device, compute_type = load_model(model_value, device, compute_type)
    print(f"device={device} compute_type={compute_type}", flush=True)

    word_timestamps = not args.no_word_timestamps
    kwargs = {
        "beam_size": args.beam_size,
        "vad_filter": not args.no_vad,
        "vad_parameters": {"min_silence_duration_ms": 500, "speech_pad_ms": 400},
        "word_timestamps": word_timestamps,
        "condition_on_previous_text": args.condition,
    }
    if word_timestamps:
        kwargs["hallucination_silence_threshold"] = 2.0
    if initial_prompt:
        kwargs["initial_prompt"] = initial_prompt
    if glossary_terms:
        kwargs["hotwords"] = " ".join(glossary_terms[:40])
    if args.language:
        kwargs["language"] = args.language
    if clip_value:
        kwargs["clip_timestamps"] = clip_value

    # clip/resume need the sequential path; batched mode ignores clip windows.
    use_batched = not args.no_batched and not clip_value
    mode = "sequential"
    transcribe_func = model.transcribe
    if use_batched:
        try:
            from faster_whisper import BatchedInferencePipeline

            pipeline = BatchedInferencePipeline(model=model)
            transcribe_func = pipeline.transcribe
            kwargs["batch_size"] = args.batch_size
            mode = "batched"
        except ImportError:
            print("warning=batched_pipeline_unavailable fallback=sequential", flush=True)

    call_kwargs, dropped = filter_kwargs(transcribe_func, kwargs)
    if dropped:
        print(f"warning=dropped_unsupported_kwargs keys={','.join(dropped)}", flush=True)

    segments_iter, info = transcribe_func(str(audio_path), **call_kwargs)
    duration = float(getattr(info, "duration", 0.0) or 0.0)
    print(f"mode={mode}", flush=True)
    print(f"language={info.language}", flush=True)
    print(f"language_probability={info.language_probability:.4f}", flush=True)
    if duration:
        print(f"duration={format_time(duration)}", flush=True)

    segments = list(existing_segments)
    next_id = len(segments) + 1
    dup_run = 0
    last_norm = None
    with paths["jsonl"].open("a", encoding="utf-8") as jsonl_file:
        for seg in segments_iter:
            text = seg.text.strip()
            avg_logprob = getattr(seg, "avg_logprob", None)
            no_speech_prob = getattr(seg, "no_speech_prob", None)
            compression_ratio = getattr(seg, "compression_ratio", None)
            flags = compute_flags(avg_logprob, no_speech_prob, compression_ratio, text)

            norm = re.sub(r"\s+", "", text)
            if norm and norm == last_norm:
                dup_run += 1
                if dup_run >= 2 and "repetition_run" not in flags:
                    flags.append("repetition_run")
            else:
                dup_run = 0
            last_norm = norm

            item = {
                "id": next_id,
                "start": float(seg.start),
                "end": float(seg.end),
                "start_text": format_time(seg.start),
                "end_text": format_time(seg.end),
                "text": text,
                "avg_logprob": round(avg_logprob, 4) if avg_logprob is not None else None,
                "no_speech_prob": round(no_speech_prob, 4) if no_speech_prob is not None else None,
                "compression_ratio": round(compression_ratio, 4) if compression_ratio is not None else None,
                "flags": flags,
            }
            if word_timestamps and getattr(seg, "words", None):
                item["words"] = [
                    {
                        "start": round(float(w.start), 3),
                        "end": round(float(w.end), 3),
                        "word": w.word,
                        "probability": round(float(w.probability), 4),
                    }
                    for w in seg.words
                ]
            segments.append(item)
            next_id += 1
            jsonl_file.write(json.dumps(item, ensure_ascii=False) + "\n")
            jsonl_file.flush()

            if text:
                warn = f" ⚠({','.join(flags)})" if flags else ""
                print(f"segment_end={item['end_text']} text={text}{warn}", flush=True)
            if duration and next_id % 20 == 0:
                print(f"progress={min(100.0, item['end'] / duration * 100):.1f}%", flush=True)

    segments.sort(key=lambda item: item["start"])
    for index, item in enumerate(segments, start=1):
        item["id"] = index

    flagged_count = sum(1 for item in segments if item.get("flags"))
    metadata = {
        "schema_version": SCHEMA_VERSION,
        "audio_file": str(audio_path),
        "model": model_value,
        "device": device,
        "compute_type": compute_type,
        "mode": mode,
        "language": info.language,
        "language_probability": float(info.language_probability),
        "duration": duration or None,
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "options": {
            "beam_size": args.beam_size,
            "vad": not args.no_vad,
            "condition_on_previous_text": args.condition,
            "word_timestamps": word_timestamps,
            "initial_prompt": initial_prompt,
            "glossary_terms": len(glossary_terms),
            "clip": clip_value,
        },
        "counts": {"segments": len(segments), "flagged": flagged_count},
    }
    write_outputs(paths, segments, metadata)

    ratio = (flagged_count / len(segments)) if segments else 0.0
    print(f"segments={len(segments)}")
    print(f"flagged={flagged_count} flagged_ratio={ratio:.2%}")
    if ratio > REFINE_HINT_RATIO and len(segments) >= 10:
        print("hint=high_flag_ratio consider running scripts/refine_segments.py with a larger model")
    for key, path in paths.items():
        print(f"{key}={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
