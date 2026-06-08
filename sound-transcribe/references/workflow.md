# Sound Transcribe Workflow

## Environment Checks

Use Codex workspace dependencies when ordinary `python` is unavailable:

```powershell
& "<bundled-python>" -c "import importlib.util; mods=['faster_whisper','ctranslate2','av']; print('\n'.join(f'{m}='+str(importlib.util.find_spec(m) is not None) for m in mods))"
```

If dependencies are missing, install to the workspace, not global Python:

```powershell
& "<bundled-python>" -m pip install --target "<workspace>\.pydeps" faster-whisper --no-input
```

If the install fails due to network restrictions and transcription is required, rerun with escalation and a concise user approval question.

## Model Selection

Prefer local model paths first:

```powershell
Get-ChildItem -Path "$env:USERPROFILE\.cache\huggingface\hub" -Recurse -Directory -Include "models--Systran--faster-whisper*" -ErrorAction SilentlyContinue
```

Recommended defaults:

- `faster-whisper-medium`: Chinese meetings, interviews, and business calls when available.
- `faster-whisper-small`: quick draft, sample checks, or low-resource machines.
- `large-v3` or larger local model: use only when already cached or explicitly requested; note longer runtime.

Use `device=cpu` and `compute_type=int8` by default on unknown Windows workstations.

## File Inspection

Check existence and metadata:

```powershell
Get-Item -LiteralPath "<audio-path>" | Select-Object FullName,Length,LastWriteTime
```

On Windows, Shell.Application can often reveal duration and bitrate for `.m4a` and `.mp3` files without ffprobe.

## Transcription

Run a 60-second sample first for long or important recordings:

```powershell
& "<python>" "<skill-dir>\scripts\transcribe_audio.py" --audio "<audio-path>" --model "<model>" --out-prefix "<prefix>.sample" --language zh --clip "0,60"
```

Inspect the sample before full transcription. If `small` misrecognizes domain terms badly and `medium` is available, use `medium` for the full run.

Full run:

```powershell
& "<python>" "<skill-dir>\scripts\transcribe_audio.py" --audio "<audio-path>" --model "<model>" --out-prefix "<prefix>" --language zh
```

For long files, expect CPU transcription to take substantial time. Do not start background jobs unless you have verified they survive the tool call in the current environment.

## Verification

After transcription:

```powershell
Get-Item -LiteralPath "<prefix>.txt","<prefix>.md","<prefix>.srt","<prefix>.json"
Get-Content -LiteralPath "<prefix>.md" -Encoding UTF8 -TotalCount 20
Get-Content -LiteralPath "<prefix>.md" -Encoding UTF8 -Tail 20
```

Report:

- Backend/model used
- Audio duration if known
- Output files
- Whether the result is raw ASR or has been manually cleaned
- Any known uncertainty: noisy audio, overlapping speakers, unclear names, or numbers needing verification

## Meeting Minutes Handoff

If the user asks for a meeting record, interview memo, due-diligence note, or official minutes, invoke `meeting-minutes` after the transcript is available. Use the timestamped `.md` or plain `.txt` as the source and include a `待核实事项` section for ASR uncertainties.
