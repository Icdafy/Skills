---
name: meeting-minutes-pro
description: 使用本地 Qwen3-ASR-0.6B 将中文、方言、英文或多语言会议录音和视频转录为文字，并将音视频、转录稿、访谈记录、尽调问答、路演记录和会议笔记整理为完整、客观、书面化的正式会议纪要；自动识别连续问答并转换为问答纪要。适用于需要本地私密转录、会议内容完整总结、国有企业公文格式排版、会议纪要 DOCX 输出和 QA 问答整理的场景。
---

# Meeting Minutes Pro

在用户设备上运行 Qwen3-ASR-0.6B，录音文件保持本地处理。将转录稿作为事实基础，形成可直接流转的会议纪要。默认交付经整理的纪要正文；用户明确只需要原始转录时，完成转录核验后结束。

## 输入分流

1. 收到音频或视频时，先执行“本地转录流程”，保存原始转录文件，再进入“会议纪要流程”。
2. 收到现成转录稿、会议笔记或访谈记录时，直接进入“会议纪要流程”。
3. 用户要求 TXT、Markdown、JSON、SRT 或仅需语音转文字时，按转录输出要求交付；用户要求纪要、总结、访谈纪要或问答整理时，最终成果必须是整理后的纪要正文。

## 本地转录流程

1. 将媒体文件解析为绝对路径，核实文件存在并识别格式、大小和时长。
2. 检查运行环境：

```powershell
python <skill-dir>/scripts/bootstrap_runtime.py --check
```

3. 首次运行缺少依赖或模型时，先取得用户对网络下载的许可，再安装运行环境：

```powershell
python <skill-dir>/scripts/bootstrap_runtime.py --install
```

4. 对时长较长、内容重要或噪声较多的录音，先转录 60 秒样本：

```powershell
<runtime-python> <skill-dir>/scripts/transcribe.py --input <media-path> --output-dir <output-dir> --language Chinese --clip-duration 60
```

5. 核对样本后执行完整转录。已知为中文时使用 `--language Chinese`；语言不确定时使用 `auto`。通过 `--context` 提供人名、项目名称、简称、专业术语和数字写法。

```powershell
<runtime-python> <skill-dir>/scripts/transcribe.py --input <media-path> --output-dir <output-dir> --language Chinese --context "specific names and terms"
```

6. 仅在用户需要 SRT 或带时间戳文本时增加 `--timestamps`。该参数会下载并加载 Qwen3-ForcedAligner-0.6B，内存占用较高。
7. 核对生成文件、首条和末条非空转录内容，说明实际模型、设备、识别语言、输出位置和可能影响准确率的因素。

## 会议纪要流程

1. 通读并清理转录稿。修正明显断句和可确认的同音字；人名、金额、日期、项目名称、文件名称和专业术语无法核实时保留原文或标注“待核”。
2. 提取材料中明确出现的会议名称、时间、地点、参会范围、议题、事实、意见、结论、任务、责任人和时限。缺失信息不补写。
3. 判定输出模式。存在显式“问/答”“Q/A”标记，或连续出现三个及以上清晰问题并有相邻答复时，使用问答纪要；其余情形使用主题式会议纪要。混合会议按主题拆分，问答密集的主题单独使用问答结构。
4. 读取 `references/format-and-output.md`，按固定公文格式组织正文。先保证内容完整，再压缩重复口语、寒暄和无实质内容的插话。
5. 保留影响会议结论、任务安排、时间节点、争议焦点、条件限制和问答实质的信息。各方意见存在差异时，分别记录其范围和依据。
6. 交付前执行：

```powershell
python <skill-dir>/scripts/quality_check.py <minutes-text-file> --mode auto
```

7. 修复脚本提示，并人工复核事实完整性、层级顺序、两字缩进、客观语气和问答配对。

## 写作口径

- 使用客观、审慎、书面化表述，聚焦会议所述事实、意见和处理安排。没有来源依据的判断、评价、原因、结论、责任人和期限均不写入。
- 完整归纳会议内容，不逐句复述。保留不同意见及其边界，不将讨论倾向写成已形成的决定。
- 仅在材料明确显示时使用“会议明确”“会议同意”“会议要求”等结论性措辞；讨论中的建议使用“提出”“建议”“表示”等中性动词。
- 不虚构参会人员、发言人、职责、任务分工或截止时间。没有可靠说话人标识时不推断发言主体。
- 删除宣传性语言、主观评价、泛化意义阐释和机械的结尾展望。避免用户指定的对照式连词组合，改用直接陈述。
- 数字、时间、单位、文件名称和责任主体照录或谨慎规范化；出现歧义时标注“待核”。

## 输出结构

默认以纯文本提供纪要正文，标题外的一级至四级标题及全部段落均以两个全角空格起首。

- 主题式纪要：标题；材料中明确的会议基本信息；按议题展开的事项、意见、结论和工作安排。
- 问答纪要：标题；材料中明确的会议基本信息；“一、问答纪要”下按主题列出“问：”和“答：”。问题与答复逐组对应，答复完整归纳事实依据、执行口径、条件、时间节点和后续安排。
- 没有材料依据的基本信息不设置空白占位段。确需核验的内容在对应位置标注“待核”。

## DOCX 交付

先通过文本校验，再运行：

```powershell
<python-with-python-docx> <skill-dir>/scripts/create_minutes_docx.py `
  --input "会议纪要.txt" `
  --output "会议纪要.docx" `
  --subtitle "综合办公室" `
  --mode auto
```

脚本会再次执行文本校验，并依据公司样例设置 A4 页面、页边距、字体、字号、固定行距、两字缩进和奇偶页外侧页码。生成后渲染并检查每一页；字体回退、标题偏移、段落截断、异常分页和页码位置均需修正后再次渲染。

## 转录与隐私规则

- 默认模型为 `Qwen/Qwen3-ASR-0.6B`，默认使用官方 `qwen-asr` Transformers 后端。
- 自动优先使用 CUDA；无可用 CUDA 时使用 CPU。普通电脑使用批量大小 1，不启用 vLLM。
- 模型保存在标准 Hugging Face 缓存中。运行环境和模型已缓存后，可使用 `--offline` 禁止网络访问。
- 默认生成 `.txt`、`.md` 和 `.json`；启用 `--timestamps` 时增加 `.srt`。
- 不上传录音，不静默切换云端接口，不虚构说话人标签。噪声、重叠发言、音乐、削波或弱语音可能影响准确率时，应明确提示。

## 资源

- `references/format-and-output.md`：固定字体、版式、层级、写作口径和两种纪要模板。
- `references/runtime.md`：硬件、下载、隐私、离线运行和故障处理说明。
- `references/platforms.md`：在不同智能体平台安装和分发技能的说明。
- `scripts/bootstrap_runtime.py`：检查和安装本地 Qwen3-ASR 运行环境。
- `scripts/transcribe.py`：执行本地音视频转录。
- `scripts/install_skill.py`：安装和分发技能。
- `scripts/requirements-runtime.txt`：转录与 DOCX 运行依赖。
- `scripts/quality_check.py`：检查缩进、标题层级、问答配对和禁用表达。
- `scripts/create_minutes_docx.py`：以固定公文版式生成 DOCX。
- `assets/fonts/`：方正小标宋简体、楷体_GB2312、仿宋_GB2312 字体文件。
- `assets/templates/文件字体格式.doc`：公司格式样例。发生格式冲突时，以样例和 `references/format-and-output.md` 为准。
