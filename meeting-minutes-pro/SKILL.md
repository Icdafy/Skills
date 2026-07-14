---
name: meeting-minutes-pro
description: Transcribe meeting, interview, due-diligence, roadshow, and other local audio or video files accurately and privately with the downloadable Qwen3-ASR-0.6B model, without a cloud API or API key. Use when an agent needs to convert WAV, MP3, M4A, FLAC, OGG, AAC, MP4, MOV, MKV, or WEBM recordings into TXT, Markdown, JSON, or optional SRT subtitles; process Chinese, Chinese dialects, English, or multilingual speech; or prepare a local transcript for later meeting-minutes writing. Do not use for live microphone streaming, speaker diarization, cloud transcription, or drafting polished minutes directly from unverified audio.
---

# Meeting Minutes Pro

Run Qwen3-ASR-0.6B on the user's machine. Keep audio local. Never upload the recording or silently switch to a cloud API.

## Workflow

1. Resolve the attached or named media file to an absolute path and verify it exists.
2. Run the environment check:

```text
python <skill-dir>/scripts/bootstrap_runtime.py --check
```

3. If the check reports that the runtime is missing, ask for permission before the first network download, then run:

```text
python <skill-dir>/scripts/bootstrap_runtime.py --install
```

4. For a long, important, or noisy recording, transcribe a 60-second sample first:

```text
<runtime-python> <skill-dir>/scripts/transcribe.py --input <media-path> --output-dir <output-dir> --language Chinese --clip-duration 60
```

5. Run the full transcription. Set `--language Chinese` when the recording is known to be Chinese; otherwise use `auto`. Add domain terms, names, abbreviations, and number spellings with `--context`.

```text
<runtime-python> <skill-dir>/scripts/transcribe.py --input <media-path> --output-dir <output-dir> --language Chinese --context "specific names and terms"
```

6. Add `--timestamps` only when the user needs SRT or timestamped text. This downloads and loads the separate Qwen3-ForcedAligner-0.6B model and uses substantially more memory.
7. Verify the generated files exist. Inspect the first and last non-empty transcript lines.
8. Report the model, actual device, detected language, raw-ASR status, outputs, and any uncertainty.

## Output Rules

- Produce `.txt`, `.md`, and `.json` by default. Produce `.srt` when `--timestamps` is enabled.
- Preserve uncertain names, numbers, acronyms, and technical terms. Do not silently replace them from general knowledge.
- Do not invent speaker labels. Qwen3-ASR does not perform speaker diarization.
- State when noise, overlap, music, clipping, or weak speech may reduce accuracy.
- Treat the transcript as raw ASR unless a human or a separate editing pass has reviewed it.
- For formal meeting minutes, complete transcription first, then hand the transcript to a meeting-minutes workflow.

## Runtime Selection

- Default model: `Qwen/Qwen3-ASR-0.6B`.
- Default backend: official `qwen-asr` Transformers backend.
- Prefer CUDA automatically when available; otherwise use CPU. The portable release does not promise acceleration on every Intel, AMD, Apple, or NPU device.
- Use batch size 1. Do not enable vLLM on ordinary laptops.
- Keep model files in the standard Hugging Face cache so every installed copy of the skill can reuse them.
- Use `--offline` after the runtime and model are cached to enforce zero network access.

Read [references/runtime.md](references/runtime.md) for hardware, download, privacy, and troubleshooting details. Read [references/platforms.md](references/platforms.md) only when installing or distributing the skill across agents.
