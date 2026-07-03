"""Speaker diarization and transcript merging (sound-transcribe v2).

Runs pyannote speaker-diarization-3.1 on the audio, maps raw speaker labels
to stable S1/S2/... ids by order of first appearance, and writes a `speaker`
field onto every segment of a schema-v2 transcript JSON.

Requirements (install only with user approval, torch is heavy):
    python -m pip install --target .pydeps pyannote.audio
    # plus a HuggingFace token with access to pyannote/speaker-diarization-3.1
    # (accept the gated-model terms on huggingface.co first)

Use --rename-only to apply human names to an already-diarized JSON without
re-running the model.
"""

import argparse
import datetime as dt
import json
import os
import pathlib
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


def parse_names(spec: str) -> dict:
    mapping = {}
    for pair in spec.split(","):
        pair = pair.strip()
        if not pair or "=" not in pair:
            continue
        key, value = pair.split("=", 1)
        mapping[key.strip()] = value.strip()
    return mapping


def assign_speakers(segments: list, turns: list) -> int:
    """Assign each ASR segment the speaker with maximum time overlap."""
    assigned = 0
    for item in segments:
        best_speaker, best_overlap = None, 0.0
        for turn_start, turn_end, speaker in turns:
            overlap = min(item["end"], turn_end) - max(item["start"], turn_start)
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = speaker
        if best_speaker is None:
            # No overlap at all: take the nearest turn within 1s, else unknown.
            center = (item["start"] + item["end"]) / 2
            nearest = min(
                turns,
                key=lambda t: min(abs(center - t[0]), abs(center - t[1])),
                default=None,
            )
            if nearest and min(abs(center - nearest[0]), abs(center - nearest[1])) <= 1.0:
                best_speaker = nearest[2]
        item["speaker"] = best_speaker or "S?"
        if best_speaker:
            assigned += 1
    return assigned


def apply_names(payload: dict, mapping: dict) -> int:
    renamed = 0
    for item in payload.get("segments", []):
        speaker = item.get("speaker")
        if speaker in mapping:
            item["speaker"] = mapping[speaker]
            renamed += 1
    diarization = payload.get("metadata", {}).get("diarization")
    if diarization:
        diarization["names"] = {**diarization.get("names", {}), **mapping}
    return renamed


def main() -> int:
    parser = argparse.ArgumentParser(description="Diarize speakers and merge into transcript JSON.")
    parser.add_argument("--audio", default=None, help="Audio path (required unless --rename-only).")
    parser.add_argument("--json", dest="json_path", required=True, help="Schema-v2 transcript JSON.")
    parser.add_argument("--num-speakers", type=int, default=None, help="Exact speaker count if known.")
    parser.add_argument("--min-speakers", type=int, default=None)
    parser.add_argument("--max-speakers", type=int, default=None)
    parser.add_argument("--hf-token", default=None,
                        help="HuggingFace token; falls back to HF_TOKEN / HUGGING_FACE_HUB_TOKEN env.")
    parser.add_argument("--names", default=None, help='Rename speakers, e.g. "S1=张总,S2=李工".')
    parser.add_argument("--rename-only", action="store_true",
                        help="Only apply --names to an already-diarized JSON.")
    args = parser.parse_args()

    ensure_utf8_stdout()
    add_local_package_paths()

    json_path = pathlib.Path(args.json_path).resolve()
    if not json_path.exists():
        raise SystemExit(f"Transcript JSON not found: {json_path}")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    segments = payload.get("segments", [])
    metadata = payload.setdefault("metadata", {})

    if args.rename_only:
        if not args.names:
            raise SystemExit("--rename-only requires --names")
        renamed = apply_names(payload, parse_names(args.names))
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"renamed_segments={renamed}")
        print(f"json={json_path}")
        print("hint=re-run scripts/render_outputs.py to regenerate outputs with names")
        return 0

    if not args.audio:
        raise SystemExit("--audio is required unless --rename-only")
    audio_path = pathlib.Path(args.audio).resolve()
    if not audio_path.exists():
        raise SystemExit(f"Audio file not found: {audio_path}")

    token = args.hf_token or os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    try:
        from pyannote.audio import Pipeline
    except ImportError as exc:
        raise SystemExit(
            "Missing pyannote.audio. Install (heavy, pulls torch) with: "
            "python -m pip install --target .pydeps pyannote.audio\n"
            "Also accept the gated model terms for pyannote/speaker-diarization-3.1 "
            "on huggingface.co and provide a token via --hf-token or HF_TOKEN."
        ) from exc

    print("loading=pyannote/speaker-diarization-3.1", flush=True)
    pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1", use_auth_token=token)
    if pipeline is None:
        raise SystemExit(
            "Failed to load pyannote/speaker-diarization-3.1. Check that your HF token "
            "is valid and the gated-model terms are accepted."
        )
    try:
        import torch

        if torch.cuda.is_available():
            pipeline.to(torch.device("cuda"))
            print("device=cuda", flush=True)
    except Exception:
        pass

    diarize_kwargs = {}
    if args.num_speakers:
        diarize_kwargs["num_speakers"] = args.num_speakers
    if args.min_speakers:
        diarize_kwargs["min_speakers"] = args.min_speakers
    if args.max_speakers:
        diarize_kwargs["max_speakers"] = args.max_speakers

    annotation = pipeline(str(audio_path), **diarize_kwargs)

    label_map, turns = {}, []
    for segment, _track, label in annotation.itertracks(yield_label=True):
        if label not in label_map:
            label_map[label] = f"S{len(label_map) + 1}"
        turns.append((float(segment.start), float(segment.end), label_map[label]))
    turns.sort()
    if not turns:
        print("warning=no_speaker_turns_detected", flush=True)
        return 1

    assigned = assign_speakers(segments, turns)
    metadata["diarization"] = {
        "backend": "pyannote/speaker-diarization-3.1",
        "num_speakers": len(label_map),
        "assigned_segments": assigned,
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
    }
    if args.names:
        apply_names(payload, parse_names(args.names))

    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    turns_path = json_path.with_name(json_path.stem + ".diarization.json")
    turns_path.write_text(
        json.dumps(
            {"turns": [{"start": s, "end": e, "speaker": sp} for s, e, sp in turns]},
            ensure_ascii=False, indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    print(f"speakers={len(label_map)}")
    print(f"assigned_segments={assigned}/{len(segments)}")
    print(f"json={json_path}")
    print(f"diarization={turns_path}")
    print("hint=re-run scripts/render_outputs.py to regenerate speaker-labeled outputs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
