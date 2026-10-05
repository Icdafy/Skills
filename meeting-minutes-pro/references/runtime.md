# Runtime and quality reference

复核等级、人工裁决和交付验收统一遵循 [evidence-and-release.md](evidence-and-release.md)。硬件建议不得覆盖内容风险要求。

## Engines

Two local engines share one isolated runtime. Select with `transcribe.py --engine`; install with `bootstrap_runtime.py --install --engine funasr|qwen|all`.

| | funasr（默认） | qwen |
| --- | --- | --- |
| 模型 | `paraformer-zh`（seaco-Paraformer）+ `fsmn-vad` + `ct-punc`，可选 `cam++` | `Qwen/Qwen3-ASR-0.6B`，可选 `Qwen/Qwen3-ASR-1.7B` |
| 下载来源 | ModelScope（魔搭，中国大陆网络友好） | Hugging Face |
| 长音频 | 原生 VAD 分段；超过 30 分钟且未启用 `--diarize` 时按静音切块（约 10 分钟一块）写检查点、中断自动续传；`--diarize` 时整段单遍处理以保证说话人编号一致 | 脚本按静音切块（ffmpeg silencedetect），逐块转录并写检查点，中断自动续传 |
| 时间戳 | 句级时间戳随说话人流水线产生，无额外开销 | 需 `--timestamps` 加载 Qwen3-ForcedAligner-0.6B，内存占用较高 |
| 说话人分离 | `--diarize`（cam++）；已知参会人数时加 `--speakers N`（传入 preset_spk_num）提高聚类稳定性 | 不支持 |
| 热词/上下文 | `--context` 作为热词（hotword） | `--context` 作为上下文提示 |
| 架构与速度 | 非自回归 Paraformer，CPU 上速度快 | 自回归解码，CPU 上长录音耗时明显 |
| 适用 | 中文及中英混杂的会议、访谈、路演 | 纯外语、粤语等方言、多语言混合（30种语言和22种中文方言） |

## Downloads and caching

The first setup requires a system Python 3.10 or newer and installs an isolated Python runtime under the user's cache directory. On Windows the deliberately short default is `%LOCALAPPDATA%\q3asr06`, which avoids PyTorch's deeply nested files exceeding the legacy Windows path limit.

The first funasr transcription downloads the Paraformer pipeline models (~1 GB total) from ModelScope. The first qwen transcription downloads `Qwen/Qwen3-ASR-0.6B` from Hugging Face; timestamp mode also downloads `Qwen/Qwen3-ForcedAligner-0.6B`. The skill package contains no model weights and no API credential.

Both transcription and review accept `--offline`. Cached model aliases are resolved with local-only lookup; missing caches fail without downloading. The CLI guards Python networking, including ModelScope calls, for that process. It is not an OS firewall or a guarantee about native extensions; strict isolation requires running with network access disabled at OS level. Qwen model paths can be supplied with `--model`.

## Hardware

`bootstrap_runtime.py --check` probes RAM, CUDA VRAM (via nvidia-smi), CPU cores, and free disk with the standard library only, and reports an advisory tier that drives how deep the dual-engine assurance goes. Hardware affects execution time and model size; it never automatically shortens the required coverage for high-risk recordings. The following budget suggestions apply only to standard-assurance meetings:

| Tier | 判定 | 双引擎策略建议 |
| --- | --- | --- |
| T0 | 内存 < 12GB，无≥8GB CUDA | 仅 funasr 主转录；确需复核加 `--budget-minutes 10`，避免 qwen `--timestamps` |
| T1 | 内存 ≥ 12GB（默认档） | funasr 主转录＋定向复核（0.6B）；长录音加 `--budget-minutes` |
| T2 | CUDA 显存 ≥ 8GB | 征询用户后可换 1.7B 模型、扩大复核覆盖或 `--voter sensevoice` |
| T3 | CUDA 显存 ≥ 16GB | 全量双引擎（`--all` / `fact_check --compare`）＋三取二投票 |

The tier is a recommendation: quote it (with the reason) to the user, degrade loudly rather than silently, and honor explicit user overrides with an ETA warning.

- NVIDIA CUDA: automatically selected and normally fastest.
- CPU: universal fallback. The funasr engine is comfortable on ordinary laptops; for the qwen engine on long recordings expect significant time and prefer 32 GB RAM.
- Apple: auto mode uses CPU because MPS operator coverage varies by PyTorch release; users may opt in with `--device mps` and retry with `--device cpu` after an MPS error.
- Intel Arc, AMD GPU, and NPU: the portable runtimes do not guarantee acceleration. Community OpenVINO, DirectML, MLX, or other conversions are separate optimizations and must not be presented as the official default backend.

With the qwen engine, use the 0.6B model on general laptops. When CUDA with ample VRAM is available and the recording is accuracy-critical, ask the user before switching to `--model Qwen/Qwen3-ASR-1.7B`; never substitute silently.

## Accuracy

Use `--context` for company names, people's names, abbreviations, technical vocabulary, only; reuse and extend the per-project files under `glossary/`. Context is a recognition hint, not text that must appear; keep it short and relevant. For known Chinese recordings on the qwen engine, also specify `--language Chinese`.

Run `--sample 60` before an important long recording: the probe is taken from the middle of the audio (openings are greetings and mic checks), and the result JSON reports the measured realtime factor plus an estimated full-run duration — quote that estimate to the user before starting the long run. Use `--enhance` for noisy, quiet, or far-field audio (loudness normalization plus light denoising). If names or numbers remain uncertain, preserve the raw output and list the uncertainty instead of guessing.

For number-critical recordings, use full independent review (`--all`): clips cover the source media timeline, including gaps in the primary transcript. Budget truncation is rejected in this mode. Standard-assurance meetings may use targeted review and an explicitly disclosed audio-minute budget. `--voter sensevoice` or enhanced-audio Qwen re-passes only adjust review priority; they never resolve a conflict automatically. Record actual listening decisions in the version-bound review ledger. Same-family Qwen re-passes are not independent dual-engine evidence. The comparison detects selected numeric, unit, negation and qualifier differences; it is not a semantic or accuracy guarantee.

Speaker diarization (`--diarize`, funasr engine) labels turns as 说话人1/说话人2…; it does not know real names. Pass the participant count confirmed during 前置信息采集 via `--speakers N`. Map labels to the confirmed participant list, and keep the numeric labels when unsure. Overlapping speech, clipped microphones, background music, and distant voices still require human review.

## Troubleshooting

- Runtime missing: run `bootstrap_runtime.py --install --engine funasr` (or `qwen`/`all`), then use the `python` path printed in its JSON result.
- Windows `WinError 206`: remove a custom `--runtime-dir` or choose a much shorter path.
- Model download blocked: retry on an allowed network, or manually download the official model and pass its local path with `--model`.
- Out of memory: disable `--timestamps` (qwen), close other applications, use `--device cpu`, and process a shorter clip.
- MPS or GPU operator failure: retry with `--device cpu`.
- Interrupted long transcription (either engine): rerun the identical command; completed chunks under `<输出目录>/<文件名>.chunks/` are reused automatically. Pass `--no-resume` to force a clean retranscription. Diarized funasr runs are single-pass and restart from the beginning — quote the ETA from the `--sample` probe up front.
- Interrupted targeted review: rerun the identical `refine_transcript.py` command; finished clips under `<输出目录>/<文件名>.refine-chunks/` are reused only when the source and recognition configuration fingerprints match; old or damaged checkpoints are recomputed.
- Media decoding failure: confirm the source file is complete and readable. The skill uses the FFmpeg binary bundled by `imageio-ffmpeg`.

## Upstream

- FunASR toolkit and models: <https://github.com/modelscope/FunASR>
- Paraformer-zh model card: <https://www.modelscope.cn/models/iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch>
- Qwen3-ASR source and local inference: <https://github.com/QwenLM/Qwen3-ASR>
- Qwen3-ASR-0.6B model: <https://huggingface.co/Qwen/Qwen3-ASR-0.6B>
- Qwen3 Forced Aligner model: <https://huggingface.co/Qwen/Qwen3-ForcedAligner-0.6B>

The FunASR toolkit code is MIT-licensed; its model weights carry the ModelScope model license shown on each model card. The Qwen3-ASR code and model cards identify Apache-2.0 licensing. The skill downloads upstream weights at runtime and does not redistribute them.
