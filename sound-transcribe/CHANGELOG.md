# Changelog

## v2 (2026-07-03)

五层流水线重构：预处理 → 识别 → 说话人 → LLM 理解 → 交付。

### 识别质量（transcribe_audio.py 重构）
- VAD 过滤默认开启（原为可选），抑制静音/背景音幻觉
- `condition_on_previous_text` 默认关闭，杜绝中文长音频复读循环
- 默认模型升级为 `large-v3-turbo`；GPU 自动探测（cuda/float16），失败回落 cpu/int8
- `BatchedInferencePipeline` 批量推理默认开启，长音频提速 3–4 倍
- 新增 `--glossary`/`--initial-prompt`：领域热词注入，缓解中文专名同音字错误
- 词级时间戳 + `hallucination_silence_threshold` 幻觉抑制
- 逐段捕获 avg_logprob / no_speech_prob / compression_ratio，低置信段打 ⚠ 标记并汇入"待核实事项"
- 增量 JSONL 落盘 + `--resume` 断点续转；JSON schema 升级到 v2

### 新增脚本
- `preprocess_audio.py`：ffprobe/PyAV 探测时长码率；ffmpeg 16k 单声道 + loudnorm + 可选降噪
- `diarize.py`：pyannote 3.1 说话人分离，按重叠对齐到转录段，支持 `--names` 改名
- `refine_segments.py`：只对低置信窗口用大模型二次精修，原文存档可审计
- `render_outputs.py`：SRT/VTT 按字幕规范重切（词级时间戳、每行 ≤20 全角、单条 ≤6s、标点优先断行）；
  新增单文件 HTML 阅读器（点句跳播、说话人着色、搜索、低置信高亮）

### LLM 后处理层（新增 references）
- `post-processing.md`：可审计校对（修订对照表）、语义分段与章节、多层总结（TLDR→摘要→要点→行动项）、场景自动检测
- `output-templates.md`：问答体（访谈/答疑）、会议纪要素材、讲座笔记、语音备忘、客服记录五套模板
- `quality.md`：参数依据、flag 阈值、疑难场景配方、备选后端（FunASR）、评测方法

### 文档
- SKILL.md 重写：流水线表、决策树、六步命令模式；description 扩充总结/问答/说话人触发词

## v1

初版：faster-whisper 基础转录，txt/md/srt/json 输出，样本试转流程。
