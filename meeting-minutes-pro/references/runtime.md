# Runtime and quality reference

## Engines

Two local engines share one isolated runtime. Select with `transcribe.py --engine`; install with `bootstrap_runtime.py --install --engine funasr|qwen|all`.

| | funasr（默认） | qwen |
| --- | --- | --- |
| 模型 | `paraformer-zh`（seaco-Paraformer）+ `fsmn-vad` + `ct-punc`，可选 `cam++` | `Qwen/Qwen3-ASR-0.6B`，可选 `Qwen/Qwen3-ASR-1.7B` |
| 下载来源 | ModelScope（魔搭，中国大陆网络友好） | Hugging Face |
| 长音频 | 原生 VAD 分段，数小时录音直接处理 | 脚本按静音切块（ffmpeg silencedetect），逐块转录并写检查点，中断自动续传 |
| 时间戳 | 句级时间戳随说话人流水线产生，无额外开销 | 需 `--timestamps` 加载 Qwen3-ForcedAligner-0.6B，内存占用较高 |
| 说话人分离 | `--diarize`（cam++） | 不支持 |
| 热词/上下文 | `--context` 作为热词（hotword） | `--context` 作为上下文提示 |
| 架构与速度 | 非自回归 Paraformer，CPU 上速度快 | 自回归解码，CPU 上长录音耗时明显 |
| 适用 | 中文及中英混杂的会议、访谈、路演 | 纯外语、粤语等方言、多语言混合（52 种语言） |

## Downloads and caching

The first setup requires a system Python 3.10 or newer and installs an isolated Python runtime under the user's cache directory. On Windows the deliberately short default is `%LOCALAPPDATA%\q3asr06`, which avoids PyTorch's deeply nested files exceeding the legacy Windows path limit.

The first funasr transcription downloads the Paraformer pipeline models (~1 GB total) from ModelScope. The first qwen transcription downloads `Qwen/Qwen3-ASR-0.6B` from Hugging Face; timestamp mode also downloads `Qwen/Qwen3-ForcedAligner-0.6B`. The skill package contains no model weights and no API credential.

After dependencies and weights are cached, pass `--offline` to reject Hugging Face network access; funasr's `disable_update` is always set and cached ModelScope models are reused without network. Users in mainland China may also pre-download the Qwen models from ModelScope and pass the local model directory with `--model`.

## Hardware

- NVIDIA CUDA: automatically selected and normally fastest.
- CPU: universal fallback. The funasr engine is comfortable on ordinary laptops; for the qwen engine on long recordings expect significant time and prefer 32 GB RAM.
- Apple: auto mode uses CPU because MPS operator coverage varies by PyTorch release; users may opt in with `--device mps` and retry with `--device cpu` after an MPS error.
- Intel Arc, AMD GPU, and NPU: the portable runtimes do not guarantee acceleration. Community OpenVINO, DirectML, MLX, or other conversions are separate optimizations and must not be presented as the official default backend.

With the qwen engine, use the 0.6B model on general laptops. When CUDA with ample VRAM is available and the recording is accuracy-critical, ask the user before switching to `--model Qwen/Qwen3-ASR-1.7B`; never substitute silently.

## Accuracy

Use `--context` for company names, people's names, abbreviations, technical vocabulary, and exact number spellings that may occur; reuse and extend the per-project files under `glossary/`. Context is a recognition hint, not text that must appear; keep it short and relevant. For known Chinese recordings on the qwen engine, also specify `--language Chinese`.

Run a 60-second sample before an important long recording. Use `--enhance` for noisy, quiet, or far-field audio (loudness normalization plus light denoising). If names or numbers remain uncertain, preserve the raw output and list the uncertainty instead of guessing.

For number-critical recordings, transcribe with both engines and run `fact_check.py --compare` on the two transcripts; treat numbers that appear in only one transcript as 待核 until confirmed against the audio.

Speaker diarization (`--diarize`, funasr engine) labels turns as 说话人1/说话人2…; it does not know real names. Map labels to the participant list confirmed during 前置信息采集, and keep the numeric labels when unsure. Overlapping speech, clipped microphones, background music, and distant voices still require human review.

## Troubleshooting

- Runtime missing: run `bootstrap_runtime.py --install --engine funasr` (or `qwen`/`all`), then use the `python` path printed in its JSON result.
- Windows `WinError 206`: remove a custom `--runtime-dir` or choose a much shorter path.
- Model download blocked: retry on an allowed network, or manually download the official model and pass its local path with `--model`.
- Out of memory: disable `--timestamps` (qwen), close other applications, use `--device cpu`, and process a shorter clip.
- MPS or GPU operator failure: retry with `--device cpu`.
- Interrupted long transcription (qwen): rerun the identical command; completed chunks under `<输出目录>/<文件名>.chunks/` are reused automatically. Pass `--no-resume` to force a clean retranscription.
- Media decoding failure: confirm the source file is complete and readable. The skill uses the FFmpeg binary bundled by `imageio-ffmpeg`.

## Upstream

- FunASR toolkit and models: <https://github.com/modelscope/FunASR>
- Paraformer-zh model card: <https://www.modelscope.cn/models/iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch>
- Qwen3-ASR source and local inference: <https://github.com/QwenLM/Qwen3-ASR>
- Qwen3-ASR-0.6B model: <https://huggingface.co/Qwen/Qwen3-ASR-0.6B>
- Qwen3 Forced Aligner model: <https://huggingface.co/Qwen/Qwen3-ForcedAligner-0.6B>

The FunASR toolkit code is MIT-licensed; its model weights carry the ModelScope model license shown on each model card. The Qwen3-ASR code and model cards identify Apache-2.0 licensing. The skill downloads upstream weights at runtime and does not redistribute them.
