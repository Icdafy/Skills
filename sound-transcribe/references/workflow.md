# Sound Transcribe Workflow（v2）

## 环境检查

```powershell
& "<python>" -c "import importlib.util; mods=['faster_whisper','ctranslate2','av']; print('\n'.join(f'{m}='+str(importlib.util.find_spec(m) is not None) for m in mods))"
```

缺依赖时装进工作区而非全局 Python（网络受限先向用户申请批准）：

```powershell
& "<python>" -m pip install --target "<workspace>\.pydeps" faster-whisper --no-input
```

可选依赖，按需申请安装：
- `ffmpeg`（预处理/降噪需要；`winget install Gyan.FFmpeg`。没有它 faster-whisper 仍可直接解码）
- `pyannote.audio`（说话人分离，体积大、拉取 torch；还需 HuggingFace token 并在
  huggingface.co 接受 `pyannote/speaker-diarization-3.1` 的门控条款）

## 模型选择

优先查本地缓存：

```powershell
Get-ChildItem -Path "$env:USERPROFILE\.cache\huggingface\hub" -Directory -Filter "models--*whisper*" -ErrorAction SilentlyContinue
```

推荐顺序：
1. `large-v3-turbo`：默认。质量接近 large-v3、速度接近 medium（faster-whisper ≥1.1 支持）。
2. `large-v3`：精修二遍（refine_segments.py 默认）或用户明确要求最高质量时。
3. `medium`：turbo 不可用且已有缓存时的中文会议备选。
4. `small`：快速草稿、样本试转、弱机器。

设备与精度由脚本自动探测（cuda→float16，cpu→int8），只在明确需要时用 `--device`/`--compute-type` 覆盖。

## 标准流程

```powershell
# 1. 探测（拿时长，预估耗时后告知用户）
& "<python>" "<skill-dir>\scripts\preprocess_audio.py" --audio "<audio>" --probe-only

# 1b. 仅当音质差/音量小：归一化 + 降噪，之后用输出的 .norm.wav 转录
& "<python>" "<skill-dir>\scripts\preprocess_audio.py" --audio "<audio>" --denoise

# 2. 样本试转（>30 分钟或重要录音必做；检查术语识别质量，决定是否换模型/加词表）
& "<python>" "<skill-dir>\scripts\transcribe_audio.py" --audio "<audio>" --out-prefix "<prefix>.sample" --language zh --clip "0,60"

# 3. 全量
& "<python>" "<skill-dir>\scripts\transcribe_audio.py" --audio "<audio>" --out-prefix "<prefix>" --language zh --glossary "<glossary.txt>"
```

耗时预估参考（每 10 分钟音频）：GPU+turbo ≈ 半分钟级；CPU+turbo 批量 ≈ 2–4 分钟；
CPU+medium 顺序 ≈ 5–10 分钟。首次使用某模型还要加下载时间。

长任务注意：
- 输出目录会先出现 `.segments.jsonl` 增量日志，中断后加 `--resume` 续转。
- 不要假设后台任务能跨工具调用存活，除非已在当前环境验证过。

## 说话人分离（可选）

多人对话且需要区分说话人（问答整理、会议归属）时：

```powershell
& "<python>" "<skill-dir>\scripts\diarize.py" --audio "<audio>" --json "<prefix>.json" --num-speakers 2
# 用户告知身份后改名（无需重跑模型）：
& "<python>" "<skill-dir>\scripts\diarize.py" --json "<prefix>.json" --rename-only --names "S1=张总,S2=李工"
```

pyannote 不可用且用户不批准安装时：跳过，声明问答/归属判断只能基于句式推断。

## 低置信精修（可选）

转录报告 `flagged_ratio > 15%` 时建议执行；先 `--dry-run` 看窗口规模再实跑：

```powershell
& "<python>" "<skill-dir>\scripts\refine_segments.py" --audio "<audio>" --json "<prefix>.json" --dry-run
& "<python>" "<skill-dir>\scripts\refine_segments.py" --audio "<audio>" --json "<prefix>.json" --model large-v3
```

## 渲染与验证

JSON 每次更新（分离/精修/改名）后重出全部产物：

```powershell
& "<python>" "<skill-dir>\scripts\render_outputs.py" --json "<prefix>.json"
Get-Content -LiteralPath "<prefix>.md" -Encoding UTF8 -TotalCount 20
Get-Content -LiteralPath "<prefix>.md" -Encoding UTF8 -Tail 20
```

验证要点：文件齐全、首尾内容合理、srt 无超长行、html 能定位到音频（相对路径）。

## LLM 后处理与交接

转录验证通过后，按 `post-processing.md` 执行：场景检测 → 校对（出修订对照表）→
章节划分 → 多层总结 → 按 `output-templates.md` 出场景化产物（问答体/讲座笔记/备忘等）。

用户要正式会议纪要时，把时间戳 `.md` 或 `.clean.md` 交给 `meeting-minutes` 技能，
并携带"待核实事项"一节。

## 最终报告模板

- 后端/模型/设备/推理模式（batched 或 sequential）
- 音频时长与实际耗时
- flagged 段数与占比；是否做了精修
- 场景判定结果（若做了后处理）
- 全部产物路径（原始层 + 后处理层）
- 结果是原始 ASR 还是经过 LLM 整理（整理的附对照表位置）
- 已知不确定性：噪音、重叠说话、待核实的人名数字
