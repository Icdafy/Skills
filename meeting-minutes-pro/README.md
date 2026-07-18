# meeting-minutes-pro — 本地转写＋正式会议纪要一体化技能

在**用户本机**将中文、方言、英文或多语言的会议录音/视频转成文字（录音不出本机），再把转录稿、访谈记录、尽调问答、路演记录炼成**客观、书面化、公文版式**的正式会议纪要，最终交付通过逐项校验的 DOCX。

供纪要使用者回答一个问题：**这场会议/访谈到底谈了什么——不掺任何记录人员的判断、建议和"待核实"。**

## 核心能力

| 能力 | 说明 |
| --- | --- |
| 双引擎本地转写 | 默认 FunASR Paraformer（中文/中英混杂，数小时长音频、句级时间戳、热词、说话人分离）；纯外语、粤语等方言或多语言用 Qwen3-ASR（52 种语言） |
| 长音频工程化 | 静音切块＋断点续传；`--sample 60` 中段试转并预估整段耗时；`--enhance` 降噪；`--diarize --speakers N` 说话人分离 |
| 双引擎定向复核 | `refine_transcript.py` 自动挑出含数字、日期、术语、提问的高风险片段，用第二引擎重转并按金额/百分比/日期/否定词/术语五类比对，分歧片段必须回听 |
| 固定纪要结构 | 材料中只要存在问答，固定输出"**完整总结概述＋完整问答纪要**"，不交付纯 QA，不用摘要吞并问答 |
| 四重交付校验 | 格式校验（quality_check）→ 分窗覆盖率审计（audit_coverage）→ 问答对账（qa_reconcile）→ 逐数字事实核对（fact_check），全部通过才允许生成 DOCX |
| 公文版式 DOCX | 方正小标宋/黑体/楷体_GB2312/仿宋_GB2312 固定版式，生成后渲染 PDF 逐页检查字体替换与分页，仅交付 DOCX |
| 术语库复用 | `glossary/<项目名>.txt` 按项目沉淀人名、简称、专业术语，跨会议自动复用（仅本地）；`glossary/industry/` 内置低空经济、商业航天行业术语库，随技能分发；上传 BP、会议笔记等资料时仅提取术语，不将资料内容写入纪要 |

## 内容硬性规则（quality_check.py 机械拦截）

纪要**只客观陈述会议访谈内容**，以下规则违反即校验失败：

1. **禁核验提示句**——全文任何位置不得出现"待核实/待核验/待落实/（待核）/需结合××资料进一步核实/该口径反映××但需××核实/以××为准"等表述。唯一例外：转录稿中真实谈及的核验事项，用 `--allow-line <行号>` 放行并向用户说明。
2. **禁判断与指导**——不基于纪要内容自行判断、评价、推论；不写"下一步应……""建议关注……"类指导意见；段落末尾不加记录人员的点评或展望。
3. **总结概述不设风险板块**——"完整总结概述"中不得出现"主要风险""待核实事项""后续需重点关注"类板块标题。
4. **访谈对象括注**——人名后的职务、单位或补充说明一律写入（）内，如"张某某（某某公司总经理）"。
5. **录音不清晰括注**——无法辨识的内容在正文对应位置以"（该处录音不清晰，无法辨识）"括注说明，不写在段落末尾。
6. **问答组间空一行**——连续多组问答之间空一行（DOCX 同步渲染间隔）；问答按主题归类为二级标题，紧随标题的首组问答前不空行。
7. 无法核实的信息保留转录稿原文，问题**在对话中向用户说明**，一律不写入纪要正文。

## 固定版式要点

| 部位 | 字体字号 |
| --- | --- |
| 大标题 | 二号方正小标宋简体，居中 |
| 一级/二级/三级标题 | 三号黑体 / 三号楷体_GB2312 加粗 / 三号仿宋_GB2312 加粗 |
| 正文与问答 | 三号仿宋_GB2312，首行空两字，固定行距 28 磅 |
| **全文阿拉伯数字** | **Times New Roman**，字号随所在文字（DOCX 自动分段设置） |
| 页码 | 页脚 `-1-` 格式，三号仿宋_GB2312，奇偶页不同（奇右偶左）；页眉不设内容 |

## 使用流程

```powershell
# 1. 检查/安装本地运行环境（首次需网络下载许可）
python scripts/bootstrap_runtime.py --check
python scripts/bootstrap_runtime.py --install --engine funasr

# 2. 转写（先试转样本，再完整转写）
<runtime-python> scripts/transcribe.py --input 录音.mp3 --output-dir out --sample 60
<runtime-python> scripts/transcribe.py --input 录音.mp3 --output-dir out --diarize --speakers 3 --context "人名 公司名 术语"

# 3. 起草纪要后依次校验
python scripts/audit_coverage.py --transcript out/录音.json --make-template coverage.txt
python scripts/audit_coverage.py --transcript out/录音.json --ledger coverage.txt --minutes 会议纪要.txt
python scripts/quality_check.py 会议纪要.txt --mode qa-summary
python scripts/qa_reconcile.py 会议纪要.txt --transcript out/录音.json
python scripts/fact_check.py 会议纪要.txt --transcript out/录音.txt --show-matches

# 4. 生成并渲染检查 DOCX
<runtime-python> scripts/font_preflight.py --check
<runtime-python> scripts/create_minutes_docx.py --input 会议纪要.txt --output 会议纪要.docx --mode qa-summary
<runtime-python> scripts/render_docx.py --input 会议纪要.docx
```

在 Claude 等智能体中装载技能后，直接上传录音或转录稿说"整理成正式会议纪要"即可，技能自动完成前置信息采集→转写→起草→校验→DOCX 全流程。

## 目录结构

```
meeting-minutes-pro/
  SKILL.md                     触发与执行逻辑
  references/                  版式规范、运行环境、平台安装说明
  scripts/                     转写、复核、四重校验、DOCX 生成与渲染检查
  glossary/                    按项目维护的热词术语库（仅本地）＋ industry/ 行业术语库（随库分发）
  assets/fonts/                方正小标宋简体、楷体_GB2312、仿宋_GB2312
  assets/templates/            公司格式样例
  tests/                       校验与规划逻辑回归测试（71 项）
```

## 隐私

转写全程本地执行：不上传录音、不静默切换云端接口；模型缓存后可 `--offline` 完全离线运行。

## License

见 [LICENSE](LICENSE)。
