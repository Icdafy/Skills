# 证据链与交付验收

本文件是复核等级、逐事实裁决及正式交付验收的操作依据。脚本检查是辅助，不能证明录音没有任何识别错误，也不能替代实际回听或全文语义核对。

统一入口 `scripts/meeting_workflow.py` 管理阶段和版本绑定，具体调用见 [采集与本地转录](acquisition-and-transcription.md) 和 [纪要编写与交付](minutes-and-delivery.md)。入口准备文件与命令，不替代本文件要求的语义核对、实际回听和有依据的裁决。

## 持续执行与事实诚实

首次集中信息答复后，智能体应连续完成证据整理、纪要正文、DOCX 和可执行验收。`needs_authoring`、`agent_action`、修订稿及 review 模板都是内部阶段，不能以 final 结束或要求用户检查后另发“生成”；仅在用户明确要求分阶段审阅时暂停。

智能体自行完成有能力执行的证据核对，保留真实依据。仍无法确认的片段只取不误导的可确认内容成文，未解分歧和处理理由随最终交付集中披露，不增设中途用户裁决。连续完成不等于无条件通过：不能编造 `listened`、`user_confirmed_audio`、审阅者、事实依据或 release 状态；程序失败与资源限制必须如实保留。

## 输入与保障等级

- 首次调用时，在收集会议信息的同时主动询问是否有 BP、演示材料、会议笔记或术语表等辅助文件；已有文件时直接复用。辅助文件用于核对具体模糊片段，不要求用户必须提供。
- 有录音：`--source-kind audio --source <录音>`。录音是内容事实源；同时提供的 BP、笔记等仅用于核对模糊的数据、单位、专名或术语，不引入会议未谈及的数字、结论或提纲。BP 数据不作为 ASR `--context` 数字提示。
- 只有转录稿：`--source-kind transcript`。以用户指定的转录稿为内容事实源，只能在对话与复核清单中声明已核对材料，不能声称回听过录音。
- 只有会议笔记：`--source-kind notes`。以用户指定的笔记为内容事实源；不从材料没有的细节补造完整发言。
- 新建录音工作流默认 `--assurance high`，初访、尽调、路演、产品或财务讲解尤其应保留全量独立复核。只有明确选择普通保障时使用 `--assurance standard`；纯文本默认 standard，不能声明录音保障。旧任务保持既有配置。硬件只影响耗时和模型选择，不降低内容风险所要求的覆盖范围。

高风险音频必须由适用的独立引擎完整复核。现有 `refine_transcript.py` 是 FunASR 主稿→Qwen 复核，`--all` 按源媒体完整时间轴切片，不依赖主稿是否识别到句子；拒绝 `--budget-minutes`。普通录音可以定向复核，并明确披露预算外片段。复核覆盖率按区间并集计算。

Qwen 主转录不能再次用同族 Qwen 重转后宣称独立双引擎核验。当前自动复核器不支持反向路由；在可行时采用另一适用引擎及独立证据，否则如实保留独立复核缺项，继续完成可确认内容及可执行阶段，最终集中披露，不声称 high 验收通过。只有用户已经明确降低保障等级时才使用 standard，不为此默认追加中途选择。不得为了通过程序把引擎元数据改成 FunASR。

## 原始稿、修订稿与回听

`consistent` 仅表示当前比较规则未发现分歧。短语对齐、数字对象/语境、否定/状态/时间归属和遗漏检测都是筛查，不等于完整语义理解；双模型共同错识别仍可能漏报。原音诊断警告进入复核清单，不能忽略警告或把裁剪、降噪、模型投票当作实际回听。

`transcribe.py` 生成的 JSON 包含源媒体 SHA-256、裁剪偏移和识别设置。原始 `.json/.txt/.md` 不覆盖；需要修订时另存 `<stem>.accepted.json` 与同名 TXT，正文、时间戳文本保持一致。原始稿和修订稿都保留源媒体哈希。新生成的样本或裁剪稿不能用于整段录音验收。

发生修订时，保存 `revisions.json`：

```json
{
  "raw_sha256": "原始JSON的SHA-256",
  "accepted_sha256": "修订JSON的SHA-256",
  "entries": [
    {
      "start": 120.5,
      "end": 128.0,
      "before": "原始表述",
      "after": "回听确认后的表述",
      "reason": "具体修订依据",
      "reviewer": "实际裁决者",
      "method": "listened"
    }
  ]
}
```

`entries` 按录音时间顺序记录非重叠修改；`before`、`after` 必须分别与原始稿、修订稿对应，并完整覆盖两稿的全部文字差异，仅忽略导出空白差异。插入可用空 `before`，删除可用空 `after`；多处变更逐项记录，或合并成一条包含全部改动的完整语句。只登记其中一处改动不能证明整份修订稿已核对。

先回听再记录确认。`listened` 表示实际读取、理解对应音频；`user_confirmed_audio` 表示用户已根据录音确认。剪出音频、重复运行 ASR 或模型投票均不算回听。没有可用音频理解能力时，保留未决片段和能力限制，按不误导的可确认内容继续完成纪要，随最终交付集中说明；不追加中途确认门槛，不得填造确认状态。

遇到模糊的数据或名词时，定点查阅 BP 等辅助文件对应页或条目，结合会议上下文及可用回听核对，也可使用用户此前已经明确确认的信息。资料只提供核对候选，不能单独证明会议说过该内容；不得复制其整页、章节、结论或未在会议提及的数据。确认后写入修订稿，在 `reason` 中记录对应音频片段、辅助文件位置和实际确认依据，保留原始稿。

仍无法辨识的数字不可把 ASR 猜测作为确定事实。纪要只保留可确认部分；未确认内容及处理依据保存在对话、修订记录和复核清单中。纪要不输出解释性括注，也不写转录、录音清晰度、识别结果、材料来源或整理过程说明。确有依据的单位、职务和条件改为直接陈述，公文层级编号保留。实际会议所述的风险、个人判断性质、条件和未决事项仍须忠实保留。

## 逐事实审计

`audit_coverage.py --strict-numbers` 检查每个数字实例，识别带数量单位的小数字、中文年份、正负号，并区分百分比与百分点；万元/亿元等相同量级支持换算。一个纪要数字实例不能替代同一窗口中的多个源事实。币种或单位明确冲突时不能通过。

“三个点”可能指百分比或百分点，不自动换算为 `%`。先按上下文及录音裁决；有修订则同步修订稿与记录。约数、范围端点、相对年份、对象、时间和限定词仍需要逐项语义核对，程序不保证穷尽所有口语数字形态。

同一数字多次出现时，以 `W1-N2`（第1窗口第2个数字实例）分别审计。旧参数 `--allow-missing-number "1|30%|原因"` 仅在窗口中该数字唯一时可用；重复数字使用 `--allow-missing-number "1|N2|原因"`。放行只限明确更正、完全重复、非实质编号，以及已回听并结合可用辅助文件核对仍无法辨识、已在对话与复核清单说明的内容，不可用于摘要压缩。每项都要记录具体理由和裁决者。

## 两阶段校验与复核清单

1. 起草并修复机械错误。`check_all.py` 默认是 `--stage draft`；`--ledger` 必须提供。`checks_passed` 只表示程序检查通过，`needs_review` 表示仍有事实、警告或人工裁决待处理，不能作为正式交付依据。
2. 生成 DOCX 并运行 `render_docx.py`；它默认保存 `<stem>.render.json`，绑定 DOCX/PDF 哈希。报告必须来自实际渲染，包含实际 renderer、PDF SHA-256、正整数页数及覆盖全部页的检查；空报告或仅写一个成功布尔值不构成渲染证据。字体替换、页码位置未全部检测通过或渲染失败均不能作为完整验收通过。
3. 用最终输入、放行参数及 DOCX 生成 `--make-review review.json`。工具只写待判定模板，不自动确认；已存在的模板不会被覆盖。文件或放行条件变化后重新生成清单，只复用经重新核对、仍成立的判定。
4. 逐项填写 facts：保留原始证据字段，将 `decision` 改为 `include` 或 `omit`；纳入项填写 TXT 的一基行号 `minutes_lines`，所有项目填写 `reason`、`reviewer`。同值不同对象分别核对，不仅核对行内是否有该数字；省略项必须对应逐实例放行参数。
5. 逐项处理 findings：仅对实际核对且能确认的项填写 `decision: confirmed`、理由和实际裁决者；音频分歧另填真实回听方法。无法确认的项保留未决状态，不为了继续生成而填成 confirmed，随最终文件集中披露。所有警告及 `--allow-line/--skip/--allow` 放行理由在清单落盘。
6. 逐页目检并核对全文非数字内容后填写 `document_review`。最后运行 `--stage release --review review.json`。只有 `release_ready: true` 才表示该版本完成正式交付验收。无本地渲染条件时说明版式尚未完整验收，不把草稿状态称作交付通过。

音频高风险场景示例（所有命令使用同一运行时 Python，`<minutes-stem>` 替换为已确认命名，如 `项目甲_会议纪要_2026-11-01`）：

```powershell
<runtime-python> scripts/refine_transcript.py --transcript out/录音.json --source 录音.wav --output-dir out --all --offline
<runtime-python> scripts/audit_coverage.py --transcript out/录音.accepted.json --make-template out/coverage.txt
# 填写覆盖清单并完成文本校验；未修订时直接使用录音.json/.txt，不需要 revisions.json。
<runtime-python> scripts/check_all.py out/<minutes-stem>.txt --transcript out/录音.accepted.json --ledger out/coverage.txt --mode qa-summary
<runtime-python> scripts/create_minutes_docx.py --input out/<minutes-stem>.txt --output out/<minutes-stem>.docx --mode qa-summary
<runtime-python> scripts/render_docx.py --input out/<minutes-stem>.docx
<runtime-python> scripts/check_all.py out/<minutes-stem>.txt --transcript out/录音.accepted.json --raw-transcript out/录音.json --revisions out/revisions.json --ledger out/coverage.txt --mode qa-summary --source-kind audio --source 录音.wav --assurance high --refine-report out/录音.refine.json --docx out/<minutes-stem>.docx --render-report out/<minutes-stem>.render.json --make-review out/review.json
# 实际逐项复核并填写 review.json 后，以完全相同的输入和放行参数验收：
<runtime-python> scripts/check_all.py out/<minutes-stem>.txt --transcript out/录音.accepted.json --raw-transcript out/录音.json --revisions out/revisions.json --ledger out/coverage.txt --mode qa-summary --source-kind audio --source 录音.wav --assurance high --refine-report out/录音.refine.json --docx out/<minutes-stem>.docx --render-report out/<minutes-stem>.render.json --review out/review.json --stage release
```

有副标题、术语库或放行参数时，前后命令保持一致。正式验收必须明确传入实际副标题，不能使用旧版未知单行豁免。清单绑定输入内容、相关参数和校验器版本；修改纪要、转录稿、DOCX、术语或规则后，旧确认失效。`checks-summary.json` 保存结果、输入哈希及复核清单哈希。原始稿、修订稿、修订记录、复核报告、覆盖清单、review.json、渲染 JSON 与纪要一并归档。纪要 TXT、DOCX 与 render JSON 按 [统一文件名](format-and-output.md#最终文件命名) 保持同一 stem，不以最终改名替代重新生成和版本绑定。PDF 逐页验收完成后可删除，用户要求 PDF 时保留。正式纪要默认交付 DOCX；只要转录或指定纯文本时尊重对应输出要求。

## 缓存与离线

检查点绑定实际音频内容和识别配置。模型、热词、语言、时间戳或增强设置变化时旧块不复用；损坏或旧版无指纹检查点重算。JSON 检查点原子写入，中断后可重新运行。复核预算变化可以复用配置一致的已完成片段。

主转录和复核均支持 `--offline`：模型别名先解析到本地缓存目录，缺失时报错；CLI 进程禁用 Python 网络连接。该机制不是操作系统防火墙，也不保证第三方原生扩展的联网行为；要求严格断网时在操作系统层断网后运行。模型已缓存并不代表校验器实际加载过，不能把文件存在当成加载成功。
