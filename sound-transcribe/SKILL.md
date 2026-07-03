---
name: sound-transcribe
description: Transcribe audio or video recordings into accurate text, subtitles, speaker-labeled transcripts, summaries, and scene-aware outputs (Q&A digest, meeting material, lecture notes) using local faster-whisper plus LLM post-processing. Use when the user asks to analyze a recording, transcribe audio, convert speech to text, generate SRT/VTT subtitles, summarize a recording, 整理访谈问答, identify speakers, process .m4a/.mp3/.wav/.mp4 files, or prepare a transcript for meeting minutes.
---

# Sound Transcribe (v2)

将本地音视频转成高质量转录产物。五层流水线：**预处理 → 识别 → 说话人 → LLM 理解 → 交付**。
优先本地 `faster-whisper` 与已缓存模型；在实际命令运行前不得声称用了某个模型。

## 流水线与脚本

| 层 | 脚本 | 何时使用 |
|---|---|---|
| 1 预处理 | `scripts/preprocess_audio.py` | 总是先 `--probe-only` 探测时长；音质差/音量小时做归一化降噪 |
| 2 识别 | `scripts/transcribe_audio.py` | 核心步骤，必跑 |
| 3 说话人 | `scripts/diarize.py` | 多人对话且用户需要区分说话人/问答整理时 |
| 4 精修 | `scripts/refine_segments.py` | 转录报告 flagged_ratio > 15% 时，用大模型只重转低置信段 |
| 5 渲染 | `scripts/render_outputs.py` | JSON 有任何更新（分离/精修/改名）后重出 txt/md/srt/vtt/html |
| LLM 理解 | 无脚本，Claude 直接执行 | 按 `references/post-processing.md` 做校对、章节、总结、场景化输出 |

## 决策树

- **先探测**：`preprocess_audio.py --probe-only` 拿到时长，向用户预估耗时再动手。
- **模型**：默认 `large-v3-turbo`（质量接近 large-v3、速度接近 medium）。本地已缓存哪个用哪个；
  弱机器快速草稿用 `small`；用户点名或已缓存时才用 `large-v3` 全量。
- **设备**：脚本自动探测 GPU（cuda/float16），失败自动回落 cpu/int8，无需手工指定。
- **长录音（>30 分钟）**：先跑 60 秒样本（`--clip "0,60"`）确认质量，再全量；全量默认批量推理。
  中断后用 `--resume` 续转，不要重头再来。
- **领域内容**（公司名/人名/术语多）：让用户给几个关键词，写入词表文件用 `--glossary` 注入。
- **转录完成后**：报告里 flagged_ratio 高就建议精修；然后按 `references/post-processing.md`
  执行 LLM 后处理（场景检测 → 校对 → 章节 → 总结 → 模板化输出）。

## 命令模式

先把所有路径解析为绝对路径。

```powershell
# 1. 探测
& "<python>" "<skill-dir>\scripts\preprocess_audio.py" --audio "<audio>" --probe-only

# 2. 样本试转（长录音必做）
& "<python>" "<skill-dir>\scripts\transcribe_audio.py" `
  --audio "<audio>" --out-prefix "<prefix>.sample" --language zh --clip "0,60"

# 3. 全量转录（VAD 默认开、GPU 自动探测、批量推理、增量落盘）
& "<python>" "<skill-dir>\scripts\transcribe_audio.py" `
  --audio "<audio>" --out-prefix "<prefix>" --language zh --glossary "<glossary.txt>"

# 4.（可选）说话人分离，之后重渲染
& "<python>" "<skill-dir>\scripts\diarize.py" --audio "<audio>" --json "<prefix>.json" --names "S1=张总"

# 5.（可选）低置信段精修
& "<python>" "<skill-dir>\scripts\refine_segments.py" --audio "<audio>" --json "<prefix>.json" --model large-v3

# 6. 渲染最终产物（含规范字幕与 HTML 阅读器）
& "<python>" "<skill-dir>\scripts\render_outputs.py" --json "<prefix>.json"
```

## 输出

原始层：`.txt` / `.md`（带时间戳与 ⚠ 低置信标注）/ `.srt` / `.vtt` / `.json`（schema v2，含置信度）/
`.segments.jsonl`（增量日志）/ `.html`（单文件阅读器：点句跳播、说话人着色、搜索）。

后处理层（按需）：`.clean.md`（校对稿+修订对照表）/ `.summary.md`（多层总结）/
场景化产物（`.qa.md` 问答体等，见 `references/output-templates.md`）。

用户要会议纪要时：转录 + 后处理完成后交接 `meeting-minutes` 技能。

## 质量守则

- 不确定的人名、数字、术语保持原样可见，列入"待核实事项"；LLM 修正必须附修订对照表，不静默改动。
- ⚠ 低置信段不得作为总结结论的依据。
- 依赖装进工作区 `.pydeps`，网络受限时先取得用户批准再安装。
- 无可用 ASR 栈且用户未批准下载/云端 API 时，把阻塞点讲清楚。
- 报告必须包含：实际使用的模型/设备/推理模式、时长、flagged 比例、产物路径、原始 ASR 与 LLM 整理的边界。

细节参考：依赖与环境检查见 `references/workflow.md`；参数调优与幻觉抑制见 `references/quality.md`；
LLM 后处理规范见 `references/post-processing.md`；场景模板见 `references/output-templates.md`。
