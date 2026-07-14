# Runtime and quality reference

## Downloads and caching

The first setup requires a system Python 3.10 or newer and installs an isolated Python runtime under the user's cache directory. On Windows the deliberately short default is `%LOCALAPPDATA%\q3asr06`, which avoids PyTorch's deeply nested files exceeding the legacy Windows path limit. The first transcription downloads `Qwen/Qwen3-ASR-0.6B` from Hugging Face unless it is already cached. Timestamp mode also downloads `Qwen/Qwen3-ForcedAligner-0.6B`.

The skill package contains no model weights and no API credential. After dependencies and weights are cached, pass `--offline` to make Hugging Face and Transformers reject network access.

Users in mainland China may pre-download the same official model from ModelScope and pass the local model directory with `--model`. The portable default uses the Hugging Face model identifier because it is consistent across operating systems.

## Hardware

- NVIDIA CUDA: automatically selected and normally fastest.
- CPU: universal fallback. Use 32 GB RAM when possible; expect long recordings to take time.
- Apple MPS: selected when PyTorch reports it as available, but model/operator compatibility can vary by PyTorch release. Retry with `--device cpu` after an MPS error.
- Intel Arc, AMD GPU, and NPU: the portable Transformers runtime does not guarantee acceleration. Community OpenVINO, DirectML, MLX, or other conversions are separate optimizations and must not be presented as the official default backend.

Use the 0.6B model for general laptops. Do not silently substitute the 1.7B model.

## Accuracy

For known Chinese recordings, specify `--language Chinese`. Use `--context` for company names, people's names, abbreviations, technical vocabulary, and exact number spellings that may occur. Context is a recognition hint, not text that must appear; keep it short and relevant.

Run a 60-second sample before an important long recording. If names or numbers remain uncertain, preserve the raw output and list the uncertainty instead of guessing.

Qwen3-ASR does not identify speakers. Timestamp mode performs forced alignment, not diarization. Overlapping speech, clipped microphones, background music, and distant voices still require human review.

## Troubleshooting

- Runtime missing: run `bootstrap_runtime.py --install`, then use the `python` path printed in its JSON result.
- Windows `WinError 206`: remove a custom `--runtime-dir` or choose a much shorter path.
- Model download blocked: retry on an allowed network or manually download the official model and pass its local path with `--model`.
- Out of memory: disable `--timestamps`, close other applications, use `--device cpu`, and process a shorter clip.
- MPS or GPU operator failure: retry with `--device cpu`.
- Media decoding failure: confirm the source file is complete and readable. The skill uses the FFmpeg binary bundled by `imageio-ffmpeg`.

## Upstream

- Qwen3-ASR source and local inference: <https://github.com/QwenLM/Qwen3-ASR>
- Qwen3-ASR-0.6B model: <https://huggingface.co/Qwen/Qwen3-ASR-0.6B>
- Qwen3 Forced Aligner model: <https://huggingface.co/Qwen/Qwen3-ForcedAligner-0.6B>

The upstream code and model cards identify Apache-2.0 licensing. The skill downloads upstream weights at runtime and does not redistribute them.
