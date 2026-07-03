# 转录质量调优参考

## 默认参数为什么这样设

| 参数 | v2 默认 | 理由 |
|---|---|---|
| `vad_filter` | 开 | Whisper 对静音/背景音乐段会产生幻觉文本（凭空生成、整段重复），Silero VAD 先切掉非语音段是第一道防线 |
| `condition_on_previous_text` | 关 | 开着时一旦某段出错，错误会作为上文污染后续解码，中文长音频极易进入"复读机循环"。关掉的代价是跨段上下文一致性略降，可用 `--condition` 恢复 |
| `word_timestamps` | 开 | 字幕规范重切、`hallucination_silence_threshold` 幻觉抑制都依赖词级时间戳；约有 10–20% 速度代价，赶时间用 `--no-word-timestamps` |
| `hallucination_silence_threshold` | 2.0 | 检测到 ≥2 秒静音却仍产出文本时跳过该窗口，抑制静音幻觉 |
| `beam_size` | 5 | faster-whisper 官方默认，速度/质量平衡点 |
| 批量推理 | 开 | `BatchedInferencePipeline` 长音频提速 3–4 倍；`--clip`/`--resume` 时自动回落顺序模式 |

## 低置信标记（flags）的含义与阈值

| flag | 触发条件 | 典型含义 |
|---|---|---|
| `low_confidence` | avg_logprob < -0.8 | 模型对该段文本不确定，常见于含糊/远场/术语 |
| `maybe_non_speech` | no_speech_prob > 0.6 | 可能是音乐、噪声被硬转成了文字 |
| `high_compression` | compression_ratio > 2.4 | 文本高度重复，幻觉的典型指纹 |
| `repetition` / `repetition_run` | 段内 n-gram 连续重复 / 相邻段文本相同 ≥3 次 | 复读循环 |

处置规则：
- flagged_ratio ≤ 5%：正常，逐条列入"待核实事项"即可。
- 5%–15%：提醒用户音质一般，重点段落建议人工复听。
- > 15%：建议 `refine_segments.py` 精修（默认只重转标记窗口，成本约为全量大模型的 20%），
  或降噪后重转。

## 热词与领域术语

- `--glossary` 文件一行一个词（支持逗号分隔、`#` 注释），脚本会同时注入
  `initial_prompt`（引导简体+标点）和 `hotwords`。
- 词表控制在 40 词以内——prompt 有 224 token 上限，塞太多反而稀释引导效果。
- 最有效的词：会反复出现的公司名、产品名、人名、行业缩写。通用词不要放。
- **不要放带单位的数字短语**（如"三万六千公里"）：实测会把全文其他数字的单位
  偏置成同一单位（"一万五千元"被转成"一万五千公里"），金额、里程全部失真。
  只放纯名词；数字问题交给 LLM 校对轮处理。
- 热词字符串可能在幻觉循环段中原样泄漏进转录文本（实测出现过"词汇：<热词>"重复串）。
  精修通道只传 initial_prompt 不传 hotwords，正是为了修这类段落。

## 疑难场景配方

| 症状 | 处方 |
|---|---|
| 音量小、远场录音 | `preprocess_audio.py`（loudnorm）后重转 |
| 空调/电流底噪 | `preprocess_audio.py --denoise` 后重转 |
| 整段整段的重复文本 | 确认 VAD 开着、condition 关着；仍出现则精修该区间 |
| 术语/人名错得离谱 | 加 `--glossary`；样本试转验证后再全量 |
| 中英混杂 | `--language zh` 保持不变（Whisper 能处理句内英文）；全英文段落多时改用自动检测 |
| 繁简混出 | initial_prompt 已引导简体；仍混出时在 LLM 校对轮统一 |
| 方言/口音重 | 换 `large-v3`（对口音更稳）；效果仍差时如实告知局限 |
| 多人抢话重叠 | ASR 层无解，标注"重叠段落，内容可能缺失"；diarization 对重叠段的归属也不可靠 |

## 备选后端（Whisper 效果不佳时）

中文场景可考虑 FunASR（阿里开源）：Paraformer-zh 中文准确率普遍优于 Whisper 系，
自带标点恢复与数字归一化，SenseVoice-Small 速度极快。代价是另一套依赖栈（modelscope + torch）。
只在用户批准安装且 Whisper 系确实不达标时引入，不默认使用。

## 质量评测（可选但推荐）

调参或换模型前后，用同一段 2–3 分钟有人工校对底稿的样本音频对比：
- 让 Claude 对照底稿数错字（近似 CER）
- 重点看人名、数字、术语三类是否改善
- 把结论记录在项目里，避免下次凭感觉调参
