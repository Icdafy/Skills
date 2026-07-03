"""Probe and normalize audio before transcription (sound-transcribe v2).

- Probe duration / sample rate / channels via ffprobe, falling back to PyAV
  (already a faster-whisper dependency) when ffmpeg is not installed.
- Optionally produce a normalized 16 kHz mono WAV: loudness normalization
  (loudnorm) plus optional denoise (highpass + afftdn) for noisy recordings.

Preprocessing is optional: faster-whisper can decode most formats directly.
Use it when the recording is quiet, noisy, or in an exotic container.
"""

import argparse
import json
import pathlib
import shutil
import subprocess
import sys


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


def probe_ffprobe(audio: pathlib.Path):
    if not shutil.which("ffprobe"):
        return None
    cmd = [
        "ffprobe", "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", str(audio),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    fmt = data.get("format", {})
    audio_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), {})
    return {
        "backend": "ffprobe",
        "duration_sec": float(fmt.get("duration", 0.0) or 0.0),
        "size_bytes": int(fmt.get("size", 0) or 0),
        "bit_rate": int(fmt.get("bit_rate", 0) or 0),
        "codec": audio_stream.get("codec_name"),
        "sample_rate": int(audio_stream.get("sample_rate", 0) or 0),
        "channels": int(audio_stream.get("channels", 0) or 0),
    }


def probe_pyav(audio: pathlib.Path):
    try:
        import av
    except ImportError:
        return None
    try:
        with av.open(str(audio)) as container:
            duration = float(container.duration / av.time_base) if container.duration else 0.0
            stream = next((s for s in container.streams if s.type == "audio"), None)
            return {
                "backend": "pyav",
                "duration_sec": duration,
                "size_bytes": audio.stat().st_size,
                "bit_rate": int(container.bit_rate or 0),
                "codec": stream.codec_context.name if stream else None,
                "sample_rate": int(stream.rate) if stream and stream.rate else 0,
                "channels": int(stream.channels) if stream and stream.channels else 0,
            }
    except Exception:
        return None


def probe(audio: pathlib.Path) -> dict:
    info = probe_ffprobe(audio) or probe_pyav(audio)
    if info is None:
        info = {
            "backend": "stat_only",
            "duration_sec": 0.0,
            "size_bytes": audio.stat().st_size,
            "bit_rate": 0,
            "codec": None,
            "sample_rate": 0,
            "channels": 0,
        }
    return info


def preprocess(audio: pathlib.Path, out: pathlib.Path, loudnorm: bool, denoise: bool) -> int:
    if not shutil.which("ffmpeg"):
        print("error=ffmpeg_not_found hint=faster-whisper 可直接解码原文件，预处理可跳过；"
              "或安装 ffmpeg（winget install Gyan.FFmpeg）后重试", flush=True)
        return 3
    filters = []
    if denoise:
        filters.append("highpass=f=80")
        filters.append("afftdn=nf=-25")
    if loudnorm:
        filters.append("loudnorm=I=-16:TP=-1.5:LRA=11")
    cmd = ["ffmpeg", "-y", "-i", str(audio)]
    if filters:
        cmd += ["-af", ",".join(filters)]
    cmd += ["-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(out)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        tail = (result.stderr or "").strip().splitlines()[-3:]
        print("error=ffmpeg_failed detail=" + " | ".join(tail), flush=True)
        return 4
    print(f"preprocessed={out}", flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe and normalize audio before transcription.")
    parser.add_argument("--audio", required=True, help="Input audio or video path.")
    parser.add_argument("--out", default=None,
                        help="Output WAV path. Default: <audio>.norm.wav next to the input.")
    parser.add_argument("--probe-only", action="store_true", help="Only print media info, no conversion.")
    parser.add_argument("--denoise", action="store_true", help="Apply highpass + afftdn noise reduction.")
    parser.add_argument("--no-loudnorm", action="store_true", help="Skip loudness normalization.")
    args = parser.parse_args()

    ensure_utf8_stdout()
    add_local_package_paths()

    audio = pathlib.Path(args.audio).resolve()
    if not audio.exists():
        raise SystemExit(f"Audio file not found: {audio}")

    info = probe(audio)
    for key, value in info.items():
        print(f"{key}={value}", flush=True)
    if info["duration_sec"]:
        minutes = info["duration_sec"] / 60
        print(f"duration_min={minutes:.1f}", flush=True)

    if args.probe_only:
        return 0

    out = pathlib.Path(args.out).resolve() if args.out else audio.with_suffix(audio.suffix + ".norm.wav")
    out.parent.mkdir(parents=True, exist_ok=True)
    return preprocess(audio, out, loudnorm=not args.no_loudnorm, denoise=args.denoise)


if __name__ == "__main__":
    raise SystemExit(main())
