# 纪要编写、校验与交付

本文件从已确认的内容事实源继续。起草前读取 [format-and-output.md](format-and-output.md) 的全部写作与版式规则；正式验收使用 [evidence-and-release.md](evidence-and-release.md)。底层命令的路径均替换成绝对路径，并统一使用实际运行时 Python。

## 1. 先整理证据，再起草

收到 `needs_authoring` / `agent_action` 或完成 `accept` 后，智能体在当前任务内连续执行本文件的全部适用步骤。首次集中信息答复已经授权生成最终纪要；不在证据稿、纪要草稿或复核模板处结束，不询问“是否继续生成”，不要求用户逐阶段检查。只有用户明确要求分阶段审阅或暂停时才停下。

无法完全解决的分歧不构成新增中途确认节点。先完成现有证据和能力允许的核对，只把不误导的可确认内容写入纪要；疑点、未纳入内容及能力限制保留在内部证据中，随最终交付集中披露。不能为了不中断而伪造回听、修改事实、清空告警或宣称正式验收通过。

本文件 `<minutes-stem>` 指统一命名得到的真实文件 stem，例如 `项目甲_会议纪要_2026-11-01`；从 `workflow.json` 的产物路径读取，不能仍写成固定的 `会议纪要.txt` 后让生成器读取另一文件。完整规则见 [最终文件命名](format-and-output.md#最终文件命名)。

第一遍按转录时间窗通读，列出全部量化事实及实质问答。每个数字保存“时间位置、对象、数值/区间、单位、时间范围、条件、比较基准、限定词、必要的说话人口径”，避免同值不同对象被合并。高风险录音先执行独立全量复核并完成能力范围内的关键分歧核对；未决部分保留证据和未决状态，按可确认内容继续成文。不直接根据 BP 或零散 ASR 片段起草摘要。

合并用户确认的基本信息。说话人标签只有具备依据时才映射姓名和角色；不确定标签仅留在内部转录稿，纪要不猜发言主体。修正明显断句和有依据的同音字；不确定专名或数字回到具体音频及辅助文件核对，修订另存。

结构按材料决定：

- 存在任何明确问答：先写“一、完整总结概述”，按主题覆盖**整份材料**的问答和陈述；再写“二、完整问答纪要”，按主题集中列出全部实质“问：/答：”。问答数量少也不删此结构，前置总结不能替代后部问答。
- 无明确问答：按议题完整概括背景、事实、意见、明确结论、未决事项与工作安排，不人为造问答。
- 总结必须能够独立阅读，覆盖材料实际涉及的背景、关键事实、业务/技术情况、意见、分歧、条件和安排。实际谈及的风险内容按相应实质主题忠实保留，不设置“主要风险”“待核实事项”“后续需重点关注”等栏目，也不把总结写成投决判断。

第二遍拿草稿逐句回到转录稿：检查每个量化事实及限定词是否保留；“会议明确/同意”有无实际表态；每窗重要内容有无遗漏；全部问题及答复实质有无保留；是否凭空混入 BP 内容。只压缩重复口语、寒暄与无实质插话，不以篇幅为由删事实。

## 2. 覆盖清单与四项机械检查

统一入口已生成 `coverage.txt` 时直接填写。每窗把“待判定”改成“纳入 <真实标题/位置>”或“省略 <具体原因>”，不得全填一个不存在的标题。源稿修订后先把旧清单另存归档并移出当前清单位置，再重新生成、核对；入口拒绝静默覆盖，旧清单不能替代新稿审计。

底层等价命令：

```powershell
<runtime-python> <skill-dir>/scripts/audit_coverage.py --transcript <accepted-transcript> --make-template <job-dir>/coverage.txt
<runtime-python> <skill-dir>/scripts/audit_coverage.py --transcript <accepted-transcript> --ledger <job-dir>/coverage.txt --minutes <job-dir>/<minutes-stem>.txt --strict-numbers
```

窗口缺判定、范围被改、严格模式下数字实例遗漏均需修复。一个窗口保留一个数字不代表其余数字已覆盖；同值不同对象必须分别核对。放行只限明确口误且已更正、完全重复、非实质页码/编号，或实际回听并结合可用辅助文件仍无法辨识且已在对话/复核清单说明的内容。参数为 `--allow-missing-number "窗口编号|原文数字|具体原因"`；同值重复时用 `"窗口编号|N序号|具体原因"`。不得以摘要需要压缩为由放行市场、价格、成本、比例、精度、产能、订单、收入利润、融资估值及国内外对比事实。

完成纪要 TXT 和覆盖清单后再次 `meeting_workflow.py run --job-dir <job-dir>`，入口会连续推进草稿检查、DOCX、渲染和 review 模板；需单独处理草稿阶段时执行：

```powershell
<runtime-python> <skill-dir>/scripts/meeting_workflow.py run --job-dir <job-dir> --step draft
```

底层 `check_all.py` 统一编排格式、覆盖、问答与事实四项检查，默认 draft，必须提供 ledger：

```powershell
<runtime-python> <skill-dir>/scripts/check_all.py <job-dir>/<minutes-stem>.txt --transcript <accepted-transcript> --ledger <job-dir>/coverage.txt --mode qa-summary
```

含问答用 `qa-summary`；`qa` 只作兼容别名。无问答用 `minutes` 或 `auto`。有项目及相关行业术语时按脚本支持传 `--glossary`，不要传不存在的文件。

| 检查 | 结果必须如何处理 |
| --- | --- |
| `quality_check.py` | 修复缩进、层级、千位分隔、基本信息、问答配对/空行、禁词及括注；不可放行项保持零残留 |
| `audit_coverage.py --strict-numbers` | 按源数字实例核对覆盖；逐窗位置必须指向真实内容，省略需具体理由 |
| `qa_reconcile.py --show-matches` | 疑似遗漏提问逐一补回或确认误报；纪要新增问题核对是否虚构；追问与对应答案中的显著数字不得被吞并 |
| `fact_check.py --show-matches` | 无依据数字逐个处理；低语境相似度“疑似移用”优先核对对象/口径；术语改写提示逐项核实 |

程序匹配只能辅助，不能证明事实完整或语义正确。`fact_check` 在转录稿里找到某个数值，不证明该数值属于纪要所写对象；`qa_reconcile` 检测的疑问句也不是全部真实问答的完备清单。

## 3. 例外与放行不能替代修复

- 疑似问题确属寒暄、修辞反问等误报时，可用 `qa_reconcile --skip <编号>`，说明理由；不得跳过实质追问。
- 无依据数字先回听/核对并修改。确属用户提供的基本信息，或根据已确认会议日期解释相对年份时，可用 `fact_check --allow <数字>` 并记录依据，不得把“合理推测”当成一般补数权限。
- 核验提示、后续判断或机构自定义禁词确为会议原话时，仅按 `quality_check` 允许的规则用 `--allow-line <行号>`，记录具体原话和理由，DOCX 生成传相同参数。解释性括注、加工说明、泛化主体、冗余归因、总结转述句式和否定对照句式均不得放行。
- 放行记录进入 `review.json` 与 `checks-summary.json`，用户可在对话看到原因。统一入口的高级放行参数在 `workflow.json` 的 `waivers` 显式填写，按实际生成的字段结构填写；draft、DOCX、review 和 release 使用同一组设置。
- 修改文本、转录、术语或放行参数后重跑检查；旧 review 先另存归档并移出当前 `review.json` 位置，再重新生成、核对版本绑定清单。禁止通过改报告哈希、填虚假听审结论或静默删除告警使状态变绿。

## 4. DOCX 生成、回读和逐页验收

文本与事实通过后检查固定字体：

```powershell
<runtime-python> <skill-dir>/scripts/font_preflight.py --check
```

缺字体时说明缺项及安装对当前用户字体目录的修改；在用户已有或新给授权范围内运行 `--install-user`。字体文件由用户提供合法使用版本，参见 `assets/fonts/README.md`。黑体、宋体、Times New Roman 等固定要求缺失时不能静默替换后称正式验收通过。

默认 `run` 在正文和覆盖清单具备后继续这些文档阶段；只重跑指定阶段时使用：

```powershell
<runtime-python> <skill-dir>/scripts/meeting_workflow.py run --job-dir <job-dir> --step docx
<runtime-python> <skill-dir>/scripts/meeting_workflow.py run --job-dir <job-dir> --step render
```

对应底层操作：

```powershell
<runtime-python> <skill-dir>/scripts/create_minutes_docx.py --input <job-dir>/<minutes-stem>.txt --output <job-dir>/<minutes-stem>.docx --mode qa-summary
<runtime-python> <skill-dir>/scripts/render_docx.py --input <job-dir>/<minutes-stem>.docx
<runtime-python> <skill-dir>/scripts/check_all.py <job-dir>/<minutes-stem>.txt --transcript <accepted-transcript> --ledger <job-dir>/coverage.txt --mode qa-summary --docx <job-dir>/<minutes-stem>.docx
```

只有用户要求或材料确定部门副标题时加 `--subtitle`，并在创建、回读和最终验收时传入同一内容，不凭示例自动加“综合办公室”。文本放行参数也保持一致。

生成器按 `format_spec.py` 输出 A4 页面、固定字体字号/行距、两字符缩进、标题层级、表格和问答留白。fsType 允许的本机授权字体默认嵌入，`--no-embed` 可关闭；需要验证嵌入时运行 `embed_fonts.py --docx <docx> --verify`。方正小标宋受限时不嵌入，在 PDF 以轮廓输出可正常显示，仍须目检标题。

回读必须确认：DOCX 与通过检查的 TXT 逐段内容一致；各 run 字体/字号/加粗正确；标题固定 30 磅、正文固定 28 磅；页眉空；页脚完整 `-1-` 的左右短横线、PAGE 域及显示数字都为四号宋体，Footer 样式和段落默认属性同样设置，奇右偶左。段落丢失、错位、样式漂移或 DOCX 旧于正文都须重生成。

逐页检查渲染 PDF 的字体、标题偏移、截断和异常分页。渲染报告 `missing_required_fonts`、`substituted_fonts` 非空，或 `page_number_check.ok` 不为 true 时修复后重渲染。只有 XML 样式检查通过而没有实际渲染，不算完成视觉验收。没有 Word/LibreOffice 等可用渲染器时如实说明未完成项，不填写虚假确认。

## 5. 正式验收与归档

`run` 返回 `agent_action: review_document` 时，智能体接着核对最终版本的待判定 review 模板，自行完成能力范围内的逐事实、逐警告、逐回听和全文版式实际复核后据实填写，再次 `run` 执行适用 release；模板不交给用户作为默认的中途审批：

```powershell
<runtime-python> <skill-dir>/scripts/meeting_workflow.py run --job-dir <job-dir> --step review-template
# 智能体实际核对并填写 review.json 后，立即再次 run；不等待用户另发“生成”。
<runtime-python> <skill-dir>/scripts/meeting_workflow.py run --job-dir <job-dir>
```

底层 `check_all.py --make-review` / `--stage release --review` 的完整参数和裁决字段见 [evidence-and-release.md](evidence-and-release.md)。统一入口将草稿检查写入 `draft-checks.json`，模板准备检查写入 `review-template-checks.json`，正式 release 写入 `checks-summary.json`；阶段日志保存在 `logs/`。`checks_passed` 是机械检查结果，`release_ready: true` 才是该绑定版本的正式验收结果。未解音频分歧在最终交付集中披露，不暂停等待用户裁决；按可确认内容完成纪要和所有可执行步骤。若字体、渲染、模型或程序错误造成客观缺项，最终交付如实列明可提供文件及尚未通过的验收项，不能把实际失败或未验收状态改成正式验收通过。

统一入口归档结构：

```text
<录音文件名>/
  workflow.json                   输入、配置、阶段状态与路径
  samples/                       试转样本及估时报告，执行过试转时保留
  raw/<stem>.json/.txt/.md/.srt    原始转录，SRT 仅在有真实时间戳时产生
  evidence/<stem>.refine.json/.md 独立复核报告
  evidence/<stem>.review-clips/   分歧回听片段
  <stem>.accepted.json/.txt       有修订时保存的证据稿
  revisions.json                 有修订时的逐项依据
  coverage.txt                   已填写并通过检查的覆盖清单
  <minutes-stem>.txt / .docx       统一命名的内容基准与最终文档
  review.json                    实际逐项复核，绑定最终版本
  <minutes-stem>.render.json      同 stem 的 DOCX 渲染检查证据
  draft-checks.json              草稿机械检查结果
  review-template-checks.json    最终复核模板准备结果
  checks-summary.json            正式验收状态
  logs/                          各阶段运行日志
```

底层脚本单独调用时允许在同一会议目录内平铺文件，但原始稿、修订稿、媒体和纪要的对应关系必须清楚。不要删除原始转录；回听片段逐条裁决后可删除，渲染 PDF 逐页核对后删除，用户明确需要时保留。多场会议逐个完成、不混排内容或证据，同项目共用已确认的术语；全部处理后在对话集中说明未确认事项、分歧位置和放行理由，不把该清单塞进正式纪要。
