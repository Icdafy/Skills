---
name: sound-transcribe
description: Transcribe audio or video recordings into text, timestamps, subtitles, and transcript files using local faster-whisper or an available speech-to-text backend. Use when the user asks to analyze a recording, transcribe audio, convert speech to text, generate SRT subtitles, process .m4a/.mp3/.wav/.mp4 files, or prepare a transcript for meeting minutes.
---

# Sound Transcribe

Use this skill to turn local audio/video files into usable transcript artifacts. Prefer local processing with `faster-whisper` and existing cached models. Do not claim a specific speech model was used until the actual command has run.

## Outputs

Default outputs:

- `.txt`: plain transcript
- `.md`: timestamped transcript with metadata
- `.srt`: subtitle file
- `.json`: segment metadata for later processing

When the user asks for meeting minutes, first produce or locate a transcript, then use the `meeting-minutes` skill to draft the formal record.

## Workflow

1. Confirm the file exists and identify duration, size, format, and language if possible.
2. Check whether the workspace Python can import `faster_whisper`, `ctranslate2`, and `av`.
3. If dependencies are missing, install them into the current workspace `.pydeps` only after the required approval for network access.
4. Prefer local cached models under HuggingFace cache. For Chinese meetings, use `faster-whisper-medium` when available; use `small` for a quick draft or weak machines.
5. Run `scripts/transcribe_audio.py` from this skill.
6. Verify output files exist and briefly inspect the first and last transcript lines.
7. Report the model/backend actually used, output paths, and any quality caveats.

Read `references/workflow.md` when you need exact dependency checks, model selection, or fallback handling.

## Command Pattern

Resolve paths to absolute paths before running commands.

```powershell
& "<python>" "<skill-dir>\scripts\transcribe_audio.py" `
  --audio "<audio-or-video-path>" `
  --model "<model-name-or-local-model-path>" `
  --out-prefix "<workspace-output-prefix>" `
  --language zh `
  --compute-type int8
```

For a short quality test before full processing:

```powershell
& "<python>" "<skill-dir>\scripts\transcribe_audio.py" `
  --audio "<audio-or-video-path>" `
  --model "<model-name-or-local-model-path>" `
  --out-prefix "<workspace-output-prefix>.sample" `
  --language zh `
  --clip "0,60"
```

## Quality Rules

- Keep uncertain names, numbers, and domain terms visible; do not silently correct them from memory.
- For long meetings, use a higher quality model if available and note that ASR still needs human review.
- If the audio is noisy, overlapping, or has multiple speakers, add a caveat instead of inventing speaker labels.
- If no local ASR stack is available and the user has not approved downloads or cloud APIs, explain the blocker plainly.
