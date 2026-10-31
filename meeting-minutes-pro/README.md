# 会议转录与正式纪要（meeting-minutes-pro）

本地处理会议音视频，使用 FunASR 与 Qwen3-ASR 完成主转录和独立复核，再由智能体按固定写作规则生成“完整总结概述＋完整问答”的正式 DOCX。也支持已有转录稿、访谈笔记，或仅输出原始转录。

源码版本 **1.2.0**，以 [VERSION](VERSION) 为准；变更见 [CHANGELOG.md](CHANGELOG.md)。

## 从音频到纪要

```text
音视频 → 主转录 → 独立复核 → 分歧裁决/修订证据稿
                              ↓
                     逐窗事实和全部问答
                              ↓
                完整总结＋完整问答 → 文本检查
                              ↓
                  DOCX → 回读/渲染 → 正式验收
```

`SKILL.md` 是精简的执行入口；详细转录、写作、格式和验收规则按阶段加载。`scripts/meeting_workflow.py` 保存源文件、配置、阶段结果和版本绑定，减少重复手写命令、混用路径和拿旧结果继续处理的问题。`run` 按当前产物状态推进可执行阶段：缺正文时给出 `agent_action: author_minutes`，智能体在同一任务内核对证据、起草纪要并填写覆盖清单，再次 `run` 推进 DOCX 与渲染；出现 `agent_action: review_document` 时完成实际文档复核，再次 `run` 执行正式验收。动作明确 `continuation_required: true`、`user_input_required: false`，旧 `needs_authoring` 同样表示内部接续。脚本不会代写语义内容或自动假定人已听审。

中文及中英混合录音默认 FunASR；方言、外语等选择适用的 Qwen3-ASR。现有自动独立复核支持 **FunASR 主稿 → Qwen 复核**，Qwen 再跑 Qwen 不计为独立双引擎。初访、尽调、路演、公司/产品/财务讲解和数字密集录音采用全量复核，覆盖源音频完整时间轴，包含主稿没有识别到内容的区间；普通会议可定向复核并披露范围。硬件只影响模型和耗时，不自动降低高风险覆盖要求。

## 安装与运行

需要 Python 3.10+ 和能在本机读取媒体的执行环境。请安装完整目录或 [已发布的完整技能包](https://github.com/Icdafy/Skills/releases)，不要只复制 `SKILL.md`；以实际 Release 版本为准，不将尚未发布的源码版本当成已发布包。

```powershell
cd "C:/下载/技能包/meeting-minutes-pro"
python -m pip install -r scripts/requirements-runtime.txt
python scripts/skill_portability.py check --smoke
python scripts/skill_portability.py install --agent codex --scope project --project-dir "C:/项目/示例 项目"
python scripts/skill_portability.py install --agent codex --scope project --project-dir "C:/项目/示例 项目" --apply
```

Claude Code 使用 `--agent claude-code`；其他客户端、个人范围、检测和安装位置见 [跨客户端安装](references/agent-compatibility.md)。已有安装更新会检查本地差异并备份，项目术语保留。旧版 `install_skill.py` 仅供兼容；推荐用 `skill_portability.py`。

先检查语音运行环境，缺组件时在已获授权范围内安装双引擎运行时：

```powershell
python scripts/bootstrap_runtime.py --check --engine all
python scripts/bootstrap_runtime.py --install --engine all
```

模型另行从官方来源下载，技能包不含模型权重。检查命令报告模块和硬件状态，不代表真实模型加载成功；使用它返回的 Python 路径进行试转。模型、硬件、长音频、离线和故障处理见 [运行参考](references/runtime.md)。

使用技能时可直接说：

```text
$meeting-minutes-pro 请处理这份尽调录音：双引擎转录并核对关键分歧，按我的完整总结和完整问答框架生成正式纪要 Word。
```

先提取已知信息，一次性询问仍缺失的基本信息及辅助文件；等待时继续环境检查和不依赖答案的音频处理。元信息缺失不阻塞转录，最终不猜填未知字段。首次集中答复后连续完成最终纪要，不在修订证据稿后暂停，不把中间稿发给用户检查后等“生成”指令；仅在用户明确要求分阶段审阅时暂停。

统一入口示例中的路径请替换为实际绝对路径。新建音频任务默认 `--assurance high` 全量独立复核，纯文本默认 standard；仅明确选择普通定向复核时为音频传 `--assurance standard`：

```powershell
<runtime-python> <skill-dir>/scripts/meeting_workflow.py init --input <录音绝对路径> --job-dir <任务绝对目录> --source-kind audio --engine funasr --assurance high --runtime-python <runtime-python> --project-name "项目甲" --interview-date "2026-11-01" --mode qa-summary
<runtime-python> <skill-dir>/scripts/meeting_workflow.py run --job-dir <任务绝对目录>
<runtime-python> <skill-dir>/scripts/meeting_workflow.py status --job-dir <任务绝对目录>
```

`needs_authoring` / `agent_action` 是内部继续阶段，不是结束对话或向用户索取“是否继续”的节点。智能体自行完成实际核对、纪要 TXT 和覆盖清单；修订稿用 `accept` 登记后立即继续。完成相应智能体动作后再次 `run`，让入口继续推进；排障或只重跑指定阶段时使用 `run --step draft|docx|render|review-template|release`。步骤的完整命令与智能体衔接分别见 [采集与转录](references/acquisition-and-transcription.md)、[纪要编写与交付](references/minutes-and-delivery.md)。

## 内容与验收规则

- 工作流自动把已选择词库送入主转录，精确项目名可发现本地同名 JSON/TXT，`hotwords.json` 保存两引擎实际使用的词条和舍弃原因。结构化词库区分已确认词、候选、别名与错写，格式见 [术语库](glossary/README.md)。
- 原始 JSON 保存各声道音频诊断、选择的声道和切块边缘复核区间；`--channel left|right` 可分别建任务，默认 mix 不代表自动分离说话人。增强需显式 `--enhance`，独立复核仍使用原音同一声道。
- 数字对象、否定/状态/时间归属和部分漏句进入短语级差异筛查；`consistent` 仅指规则未发现分歧。模型选择与热词收益用 [评测工具](references/asr-evaluation.md) 验证，字错率、术语和关键表述分别统计。
- 录音及确认后的转录稿提供会议内容；BP、公司介绍、笔记和术语库仅用于具体模糊片段核对，不提供纪要提纲或新增会议事实，辅助资料数字不进入 ASR 提示。
- 保留全部重要数字的对象、单位、区间、时间和限定条件。先梳理事实与问答，再起草总结；原稿漏识别与摘要漏内容分别由独立复核和覆盖审计处理。
- 存在明确问答时，完整总结先于完整问答，两部分均保留；没有问答不造问题。正文只客观陈述会议内容，不写解释性括注、转录过程、材料来源说明或无依据的判断。职务、单位和必要条件直接书写，公文层级编号保留。
- `checks_passed` 只代表机械检查通过；最终文件、逐事实裁决、分歧回听和版式检查均完成后，才可能 `release_ready: true`。不能把模型一致或测试通过称为识别绝对正确。
- 原始转录保持不变；修订稿另存并逐项记录依据。版本绑定覆盖源媒体、原/修订稿、参数、规则和最终文件，修改后旧确认不能直接复用。

详细写作、标题层级、问答空行、数字千位分隔、字体/字号/固定行距、表格和页码见 [格式与输出规范](references/format-and-output.md)。`format_spec.py` 是排版实现的唯一规约，DOCX 需经过内容与样式回读及实际逐页渲染。

字体由用户提供授权版本，可用 `ICDAFY_FONT_DIR` 指向字体目录；执行 `font_preflight.py --check`。单技能 ZIP 和安装器不包含字体；源码中的历史字体及其许可状态见 [字体说明](assets/fonts/README.md)。缺字体时不静默替换并声称通过版式验收。

最终文件统一命名为 `项目名称_会议纪要_访谈时间.docx`；无项目名称时，首段改用访谈对象姓名，不能用我方访谈人员或记录人。`项目名称/访谈人名` 中的 `/` 表示二选一，不作为路径分隔符。日期来自用户已确认的访谈时间，例 `项目甲_会议纪要_2026-11-01.docx`；不猜日期。TXT、DOCX 与渲染报告使用同一 stem，缺项处理见 [文件命名](references/format-and-output.md#最终文件命名)。

每场会议单独归档原始转录、适用的修订稿与记录、复核报告、覆盖清单、纪要 TXT/DOCX、`review.json`、渲染 JSON 和 `checks-summary.json`；阶段执行日志和 `workflow.json` 便于续跑。默认交付 DOCX；仅转录或指定其他格式时遵循用户要求。渲染 PDF 逐页验收后删除，用户需要时保留。

## 隐私与执行边界

录音在本机处理，不静默上传、不改用云接口。`--offline` 只允许本地模型缓存，并限制 CLI 的 Python 网络连接；它不等同于操作系统防火墙。严格断网要求在系统层断网后运行。

`glossary/industry/` 是公共词库；项目术语和 `banned-phrases.txt` 是用户数据，安装与打包需保留或排除私有文件。录音、转录、模型缓存、私有资料及本机路径补丁不进入公开技能包。分发规则见 [platforms.md](references/platforms.md)。

“实际回听”指理解对应音频；剪片、重复 ASR 和投票均不算。宿主没有音频理解能力或存在未解分歧时，以不误导的可确认内容继续生成最终纪要，疑点与能力限制随最终交付集中披露；不追加中途确认门槛，也不填造听审结果。缺渲染器时也必须明确版式尚未完成验收。完整证据字段与状态含义见 [evidence-and-release.md](references/evidence-and-release.md)。

## 验证与维护

```powershell
<runtime-python> -B -m unittest discover -s tests
```

回归测试覆盖转录辅助函数、断点和时间定位、全量复核规划、数字与问答反例、版本绑定证据、DOCX 内容/样式和渲染报告。模拟测试不代表真实长录音准确率；更换引擎、模型或依赖后需要重新做样例加载与推理。

1.1.0 本轮验证：312 项回归通过；默认 FunASR 原始 CLI 对 4 秒官方样本离线转录通过；Qwen3-ASR 0.6B＋ForcedAligner 对 4.523 秒样本的输出契约通过；FunASR 主稿→Qwen 全量独立复核链通过。合成转录稿生成完整总结与两组问答，经本机 Word 真正渲染、逐页目检和正式验收通过。尚未完成真实长会议、方言、多人重叠语音和说话人分离准确率基准；短样本成功不代表这些场景已验证。历史记录见 [维护记录](https://github.com/Icdafy/Skills/blob/main/docs/maintenance.md#历史实测范围)，本轮变更见 [CHANGELOG.md](CHANGELOG.md)。

只维护本技能目录及其索引/版本/包，不跨技能同步安装器和兼容文档。`scripts/skill_portability.py` 支持 check、install 和 package；完整仓库维护可运行 `python tools/package_skills.py --skill meeting-minutes-pro`。架构约束见 [architecture.md](references/architecture.md)。

许可为 [Apache-2.0](LICENSE)；[NOTICE](NOTICE) 保留署名与素材说明。
