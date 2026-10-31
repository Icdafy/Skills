# 信息采集与本地转录

本文件用于音视频输入、引擎选择和转录执行。复核等级、修订与回听证据遵循 [evidence-and-release.md](evidence-and-release.md)；环境故障查 [runtime.md](runtime.md)。命令中的 `<skill-dir>`、`<media-path>`、`<job-dir>` 和 `<runtime-python>` 必须替换为本次实际绝对路径，含空格时加引号。

## 1. 一次性采集，技术处理并行

用户首次集中答复后，按既定目标连续执行到最终纪要交付。统一入口 `run`、`accept` 返回的 `needs_authoring` / `agent_action` 是智能体内部接续动作，不是用户检查点；不得在生成修订证据稿后用 final 结束、询问是否继续或等待用户另发“生成”。仅当用户明确要求分阶段检查时，才暂停给用户审阅。

先读取对话、文件名、用户说明及已有项目术语，提取已知字段。文件名只提供候选，不能把修改时间或含糊日期猜成会议时间。以下表单只保留仍缺失且适用的项，一次询问；用户说跳过、不清楚、没有辅助文件或仅需转录时直接继续，不重复确认：

```text
请补充尚缺的会议信息；不清楚的项目可以跳过：
1. 会议/项目/公司名称及主题；
2. 会议或访谈时间、地点/线上平台；
3. 访谈对象的姓名、单位、职务，以及我方访谈人员；
4. 需要重点识别的人名、简称和专业术语；
5. 是否有 BP、公司介绍、会议笔记或术语表可用于核对模糊片段？没有也可继续。
```

等待答案时完成文件可读性、格式/大小/时长、运行环境和模型缓存检查；已有信息足以选择引擎时可继续试转、主转录和复核。未知日期、地点和人员不妨碍识别音频，不为等待这些字段闲置整条流水线。后来新增的热词若需重新识别，使用更新后的配置运行，不能把旧缓存伪装成新配置结果。

一般会议采集会议时间、地点、参会范围；访谈/尽调/项目交流使用访谈时间、访谈地点、访谈对象、访谈人员。用户确认的信息可作为基本信息依据；发现冲突先依据现有材料自行核对，不能混合两个口径。仍无法解决时采用不误导的可确认内容，冲突及处理理由随最终交付集中说明，不新增中途确认门槛。未知字段最终直接省略，不放空白占位或“待核”标记。

检查 `<skill-dir>/glossary/` 下同项目或公司文件并复用。涉及低空经济、商业航天等行业时，从 `glossary/industry/` 相应词库挑选本场相关词，不把整库全部传入。仅把人名、公司名、产品名、职务、简称和术语放入 `--context`；BP 中的数字、句子、结论和目录均不进入 ASR 提示。辅助文件先登记名称及用途；遇到具体模糊片段再定点查对应页，不能先按 BP 起草纪要。

任务结束前把本场经确认的新专名/术语追加到本地项目术语文件。同项目后续录音复用；项目术语属于用户数据，不随技能公开分发。

## 2. 环境与引擎

```powershell
python <skill-dir>/scripts/bootstrap_runtime.py --check --engine all
```

使用返回的运行时 Python。若缺依赖或模型，在已有授权范围内安装；尚未授权网络下载时说明缺失组件、下载来源和本地缓存用途，一次取得许可后执行，不反复询问已授权事项：

```powershell
python <skill-dir>/scripts/bootstrap_runtime.py --install --engine all
```

`--engine funasr|qwen|all` 可按实际任务安装。模型权重不随技能包附带；缓存存在不等于成功加载过。硬件 T0–T3 仅估算时间和模型尺寸，不自动降低复核覆盖要求。默认自动选 CUDA，无法使用时 CPU；MPS 由用户明确选择。使用默认 Qwen 0.6B，改用 1.7B 需与用户的精度/资源选择一致。

| 音频/需求 | 主转录 | 复核与限制 |
| --- | --- | --- |
| 中文或中英混合会议、访谈、路演 | FunASR Paraformer + VAD + 标点 | Qwen3-ASR 独立复核 |
| 外语、粤语等方言、多语言混合 | 适用的 Qwen3-ASR | 现有自动复核器不支持反向 FunASR 路由，不能重复 Qwen 冒充独立引擎 |
| 多人访谈、尽调、路演等需区分发言轮次 | FunASR 加 `--diarize`；已确认人数可加 `--speakers N` | cam++ 标签只代表说话轮次，不提供真实身份；不能把全部参会人数当然视为实际发言人数 |
| 需要精准时间定位 | FunASR 默认保留句级时间戳，示例显式加 `--timestamps` | Qwen 需 `--timestamps` 加载独立 ForcedAligner；对齐范围和语言支持应单独确认 |

本地 ASR 需要宿主能访问录音、运行 Python 并具备必要计算资源。按当前实际能力判断；缺能力时说明具体缺项，可先整理已提供的转录稿，不凭客户端名称断言已经完成本地处理。

## 3. 试转与主流程

重要、长或噪声较多的录音先试转中段 60 秒，检查语言、专名、数字、音量与时间定位：

```powershell
<runtime-python> <skill-dir>/scripts/transcribe.py --input <media-path> --output-dir <job-dir>/samples --engine funasr --timestamps --sample 60
```

根据样本 JSON 中 `inference_realtime_factor`、`setup_seconds` 和 `estimated_full_run_minutes` 告知估计耗时；估算将一次性模型加载成本与每秒推理成本分离，不能把冷启动时间按整段时长倍增。说明这仍只是该设备/配置的样本估算。样本存于 `samples/`，不占用统一入口保留的 `raw/` 输出位置；首次 init 前不要在 `raw/` 写入完整转录。样本带 `.sample` 后缀；必须继续跑完整录音，不能交样本充当全稿。噪声、低音量或远场音频可加 `--enhance` 后对比样本；不能假设增强总是更准确。

推荐用统一入口记录输入和配置，以下是**高风险中文访谈**的示例；普通内部会议使用 standard，人数仅在已确认且适用时填写：

```powershell
<runtime-python> <skill-dir>/scripts/meeting_workflow.py init --input <media-path> --job-dir <job-dir> --source-kind audio --engine funasr --assurance high --runtime-python <runtime-python> --project-name "项目甲" --interview-date "2026-11-01" --context "人名 公司名 专业术语" --diarize --speakers 3 --mode qa-summary
<runtime-python> <skill-dir>/scripts/meeting_workflow.py run --job-dir <job-dir>
<runtime-python> <skill-dir>/scripts/meeting_workflow.py status --job-dir <job-dir>
```

初始化时用 `--project-name`、`--interviewee`、`--interview-date` 保存首次集中采集的命名信息：项目名优先，未提供项目名时用访谈对象姓名；`--interviewee` 不填我方访谈人员或记录人。访谈时间只填用户已确认的值，示例日期需替换成真实确认日期，不得照抄。正文 TXT、DOCX、渲染报告以 `workflow.json` 中实际产物路径为准，遵循 [统一命名规则](format-and-output.md#最终文件命名)。

按需在 init 明确模型：`--model` 指定主转录模型 ID 或本地目录，`--review-model` 指定独立 Qwen 复核模型；Qwen 主转录需要强制对齐时传 `--timestamps`，可用 `--aligner` 指定对齐模型。FunASR 默认保留句级时间戳。模型选项与所选引擎相匹配；用户已指定模型时保持该选择，不静默改用另一尺寸、后端或云服务。默认模型无需填这些参数，变更模型会使相关识别阶段重新核验，不能沿用旧配置结果。

`run` 按当前产物状态推进可执行阶段，遇到错误报出具体阶段。缺正文时返回 `agent_action: author_minutes`：智能体立即核对证据、起草纪要及填写覆盖清单，再次运行相同 `run`，入口继续检查、DOCX、渲染和 review 模板；返回 `agent_action: review_document` 时智能体完成实际复核和清单填写，再次 `run` 进入适用 release。`continuation_required: true`、`user_input_required: false` 明确这些是内部接续；兼容的旧 `needs_authoring` 也不能作为结束任务或请用户检查后继续的理由。状态文件 `workflow.json` 保存绝对路径和参数；已完成阶段按输入/输出/脚本绑定复用。需要离线时在 init 加 `--offline`，缺本地模型时先解决缓存，不移除离线要求静默下载。

仅转录、试样或需要额外 ASR 参数时也可使用底层脚本：

```powershell
<runtime-python> <skill-dir>/scripts/transcribe.py --input <media-path> --output-dir <job-dir>/raw --engine funasr --timestamps --diarize --speakers 3 --context "人名 公司名 专业术语"
```

FunASR 的 `--diarize` 与 Qwen 不兼容，Qwen 命令必须移除；`--speakers` 只能与 FunASR 的 `--diarize` 一同使用。Qwen 主稿必须如实保留引擎元数据。

长音频按静音附近切块并保存检查点，使用相同命令续传。**FunASR 启用 `--diarize` 时为保持全程说话人编号一致采用单遍处理，不能从分片断点恢复。** 重要长会开跑前应据样本告知耗时与此限制。不能直接逐块聚类后把不同块的“说话人1”当成同一人。

## 4. 独立复核与证据修订

先根据内容确定等级：初访、尽调、路演、公司介绍、产品/财务讲解、数字密集或用户要求数字零遗漏均使用 high；普通内部会议可用 standard。全量复核按源音频完整时间轴独立切片，覆盖主稿未识别到内容的区间，以发现主引擎整句漏数。高风险模式禁止预算截断。

```powershell
<runtime-python> <skill-dir>/scripts/refine_transcript.py --transcript <job-dir>/raw/<stem>.json --source <media-path> --output-dir <job-dir>/evidence --all --glossary <skill-dir>/glossary/<项目名>.txt
```

只在确有对应术语文件时传 `--glossary`。普通会议可去掉 `--all` 做定向复核，按数字、日期、专名、否定、承诺和疑似提问选片；使用 `--budget-minutes` 时明确实际范围和未处理片段。时间覆盖按区间并集计算，不把重叠片段时长相加当成覆盖率。定向结果不能声称发现所有主稿漏句。

复核比较金额、百分比、日期、否定、限定词、术语及数字顺序，也提示明显文本缺失或非数字文本分歧，并剪出分歧音频。这是启发式筛查，不能证明找到了全部语义差异。数字缺失、值/单位差异、范围端点、对象和条件错配均逐条实际回听裁决。一方完全缺失的量化句不能“主稿优先”直接抹去。智能体完成能力范围内的回听、资料和上下文核对；仍无法确认的部分保留原始证据与未决状态，纪要只纳入不误导的可确认内容，疑点随最终交付集中说明，不暂停等待用户裁决。仲裁重跑和第三引擎投票仅调整回听优先级，不能自动解除分歧。

原始 JSON/TXT/MD 保持不变。确认的修改另存 `<stem>.accepted.json` 及一致的 TXT，保留源媒体哈希与时间戳，并按 [修订记录](evidence-and-release.md#原始稿修订稿与回听) 写 `revisions.json`。统一入口选择修订稿：

```powershell
<runtime-python> <skill-dir>/scripts/meeting_workflow.py accept --job-dir <job-dir> --transcript <job-dir>/<stem>.accepted.json --revisions <job-dir>/revisions.json
<runtime-python> <skill-dir>/scripts/meeting_workflow.py run --job-dir <job-dir> --step ledger
```

如已生成 coverage，默认 `run` 在源稿变更后把旧清单保存在 `history/`，重新生成适配新证据的清单；智能体随即逐窗重新核对，不需用户审批。输入未变时正常填写的清单保持原样。仅单独使用 `--step ledger` 时，先自行另存旧清单再重建。`accept` 登记要使用的稿件并给出 `continuation_required: true`、`user_input_required: false` 的后续智能体动作，不替代实际裁决或版本绑定验收。登记完成后立即继续覆盖审计、纪要写作和 DOCX，不把修订稿交给用户检查后等待“生成”。没有修改时直接使用原始稿，不制造无意义修订记录。

最后核对实际输出文件、首条和末条非空转录、处理时长与源音频范围；说明实际引擎、模型、设备、语言、复核范围和剩余分歧。只要转录时按用户格式交付；需要纪要时继续 [minutes-and-delivery.md](minutes-and-delivery.md)，不在转录完成处结束任务。
