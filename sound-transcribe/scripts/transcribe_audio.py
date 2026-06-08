import argparse
import datetime as dt
import json
import pathlib
import sys


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


def make_output_paths(prefix: pathlib.Path) -> dict[str, pathlib.Path]:
    prefix.parent.mkdir(parents=True, exist_ok=True)
    return {
        "txt": pathlib.Path(f"{prefix}.txt"),
        "md": pathlib.Path(f"{prefix}.md"),
        "srt": pathlib.Path(f"{prefix}.srt"),
        "json": pathlib.Path(f"{prefix}.json"),
    }


def resolve_model_value(model: str) -> str:
    try:
        model_path = pathlib.Path(model)
        if model_path.exists():
            return str(model_path.resolve())
    except OSError:
        pass
    return model


def main() -> int:
    parser = argparse.ArgumentParser(description="Transcribe audio/video with faster-whisper.")
    parser.add_argument("--audio", required=True, help="Input audio or video path.")
    parser.add_argument("--model", required=True, help="Model name or local CTranslate2 model path.")
    parser.add_argument("--out-prefix", required=True, help="Output prefix without extension.")
    parser.add_argument("--language", default=None, help="Language code such as zh or en. Omit for auto-detect.")
    parser.add_argument("--clip", default=None, help='Optional clip_timestamps value, e.g. "0,60".')
    parser.add_argument("--beam-size", type=int, default=5)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument("--vad", action="store_true", help="Enable VAD filtering.")
    parser.add_argument("--no-condition", action="store_true", help="Disable conditioning on previous text.")
    args = parser.parse_args()

    add_local_package_paths()
    try:
        from faster_whisper import WhisperModel
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

    model = WhisperModel(model_value, device=args.device, compute_type=args.compute_type)
    kwargs = {
        "beam_size": args.beam_size,
        "vad_filter": args.vad,
        "word_timestamps": False,
        "condition_on_previous_text": not args.no_condition,
    }
    if args.language:
        kwargs["language"] = args.language
    if args.clip:
        kwargs["clip_timestamps"] = args.clip

    segments_iter, info = model.transcribe(str(audio_path), **kwargs)
    segments = []

    print(f"language={info.language}", flush=True)
    print(f"language_probability={info.language_probability:.4f}", flush=True)
    for seg in segments_iter:
        item = {
            "id": len(segments) + 1,
            "start": float(seg.start),
            "end": float(seg.end),
            "start_text": format_time(seg.start),
            "end_text": format_time(seg.end),
            "text": seg.text.strip(),
        }
        segments.append(item)
        if item["text"]:
            print(f"segment_end={item['end_text']} text={item['text']}", flush=True)

    plain_text = "\n".join(item["text"] for item in segments if item["text"])
    paths["txt"].write_text(plain_text + ("\n" if plain_text else ""), encoding="utf-8")

    metadata = {
        "audio_file": str(audio_path),
        "model": model_value,
        "device": args.device,
        "compute_type": args.compute_type,
        "language": info.language,
        "language_probability": info.language_probability,
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "segments": len(segments),
    }
    payload = {"metadata": metadata, "segments": segments}
    paths["json"].write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md_lines = [
        "# 语音转录",
        "",
        f"- 音频文件: `{audio_path}`",
        f"- 模型: `{model_value}`",
        f"- 设备: `{args.device}`",
        f"- 计算类型: `{args.compute_type}`",
        f"- 检测语言: `{info.language}`",
        f"- 语言置信度: `{info.language_probability:.4f}`",
        f"- 生成时间: `{metadata['generated_at']}`",
        "",
        "## 带时间戳文本",
        "",
    ]
    for item in segments:
        if item["text"]:
            md_lines.append(f"[{item['start_text']} - {item['end_text']}] {item['text']}")
    paths["md"].write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    srt_blocks = []
    for index, item in enumerate((item for item in segments if item["text"]), start=1):
        srt_blocks.append(
            f"{index}\n{format_srt_time(item['start'])} --> {format_srt_time(item['end'])}\n{item['text']}"
        )
    paths["srt"].write_text("\n\n".join(srt_blocks) + ("\n" if srt_blocks else ""), encoding="utf-8")

    print(f"segments={len(segments)}")
    for key, path in paths.items():
        print(f"{key}={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
