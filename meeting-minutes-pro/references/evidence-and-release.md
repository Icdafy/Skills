# 证据链与交付验收

本文件是复核等级、逐事实裁决及正式交付验收的操作依据。脚本检查是辅助，不能证明录音没有任何识别错误，也不能替代实际回听或全文语义核对。

## 输入与保障等级

- 有录音：`--source-kind audio --source <录音>`。录音是内容事实源；同时提供的 BP、笔记等仅提取规范术语，不引入其中的数字、结论或提纲。
- 只有转录稿：`--source-kind transcript`。以用户指定的转录稿为内容事实源，只能声明已核对材料，不能声称回听过录音。
- 只有会议笔记：`--source-kind notes`。以用户指定的笔记为内容事实源；不从材料没有的细节补造完整发言。
- 初访、尽调、路演、产品或财务讲解、数字零遗漏要求：录音模式使用 `--assurance high`。其他场景使用 `--assurance standard`。硬件只影响耗时和模型选择，不降低内容风险所要求的覆盖范围。用户明确降低保障等级时，记录原因并使用 standard。

高风险音频必须由适用的独立引擎完整复核。现有 `refine_transcript.py` 是 FunASR 主稿→Qwen 复核，`--all` 按源媒体完整时间轴切片，不依赖主稿是否识别到句子；拒绝 `--budget-minutes`。普通录音可以定向复核，并明确披露预算外片段。复核覆盖率按区间并集计算。

Qwen 主转录不能再次用同族 Qwen 重转后宣称独立双引擎核验。当前自动复核器不支持反向路由；需要改用另一适用引擎及独立证据，或由用户明确选择普通保障等级。不得为了通过程序把引擎元数据改成 FunASR。

## 原始稿、修订稿与回听

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

先回听再记录确认。`listened` 表示实际读取、理解对应音频；`user_confirmed_audio` 表示用户已根据录音确认。剪出音频、重复运行 ASR 或模型投票均不算回听。没有可用音频理解能力时，将片段交给用户裁决；不得填造确认状态。

仍无法辨识的数字不可把 ASR 猜测作为确定事实。保留可确认部分，在对应位置使用“（该处录音不清晰，无法辨识）”，并在对话与复核清单记录处理依据。实际会议所述的风险、个人判断性质、条件和未决事项仍须忠实保留；删除的是冗余归因外壳，不是事实的不确定性质。

## 逐事实审计

`audit_coverage.py --strict-numbers` 检查每个数字实例，识别带数量单位的小数字、中文年份、正负号，并区分百分比与百分点；万元/亿元等相同量级支持换算。一个纪要数字实例不能替代同一窗口中的多个源事实。币种或单位明确冲突时不能通过。

“三个点”可能指百分比或百分点，不自动换算为 `%`。先按上下文及录音裁决；有修订则同步修订稿与记录。约数、范围端点、相对年份、对象、时间和限定词仍需要逐项语义核对，程序不保证穷尽所有口语数字形态。

同一数字多次出现时，以 `W1-N2`（第1窗口第2个数字实例）分别审计。旧参数 `--allow-missing-number "1|30%|原因"` 仅在窗口中该数字唯一时可用；重复数字使用 `--allow-missing-number "1|N2|原因"`。放行只限明确更正、完全重复、非实质编号，以及已回听仍无法辨识且已在正文说明的内容，不可用于摘要压缩。每项都要记录具体理由和裁决者。

## 两阶段校验与复核清单

1. 起草并修复机械错误。`check_all.py` 默认是 `--stage draft`；`--ledger` 必须提供。`checks_passed` 只表示程序检查通过，`needs_review` 表示仍有事实、警告或人工裁决待处理，不能作为正式交付依据。
2. 生成 DOCX 并运行 `render_docx.py`；它默认保存 `<stem>.render.json`，绑定 DOCX/PDF 哈希。字体替换、页码位置未全部检测通过或渲染失败均不能作为完整验收通过。
3. 用最终输入、放行参数及 DOCX 生成 `--make-review review.json`。工具只写待判定模板，不自动确认；已存在的模板不会被覆盖。文件或放行条件变化后重新生成清单，只复用经重新核对、仍成立的判定。
4. 逐项填写 facts：保留原始证据字段，将 `decision` 改为 `include` 或 `omit`；纳入项填写 TXT 的一基行号 `minutes_lines`，所有项目填写 `reason`、`reviewer`。同值不同对象分别核对，不仅核对行内是否有该数字；省略项必须对应逐实例放行参数。
5. 逐项处理 findings：填写 `decision: confirmed`、理由和裁决者；音频分歧另填实际回听方法。所有警告及 `--allow-line/--skip/--allow` 放行理由在清单落盘。
6. 逐页目检并核对全文非数字内容后填写 `document_review`。最后运行 `--stage release --review review.json`。只有 `release_ready: true` 才表示该版本完成正式交付验收。无本地渲染条件时说明版式尚未完整验收，不把草稿状态称作交付通过。

音频高风险场景示例（所有命令使用同一运行时 Python）：

```powershell
<runtime-python> scripts/refine_transcript.py --transcript out/录音.json --source 录音.wav --output-dir out --all --offline
<runtime-python> scripts/audit_coverage.py --transcript out/录音.accepted.json --make-template out/coverage.txt
# 填写覆盖清单并完成文本校验；未修订时直接使用录音.json/.txt，不需要 revisions.json。
<runtime-python> scripts/check_all.py out/会议纪要.txt --transcript out/录音.accepted.json --ledger out/coverage.txt --mode qa-summary
<runtime-python> scripts/create_minutes_docx.py --input out/会议纪要.txt --output out/会议纪要.docx --mode qa-summary
<runtime-python> scripts/render_docx.py --input out/会议纪要.docx
<runtime-python> scripts/check_all.py out/会议纪要.txt --transcript out/录音.accepted.json --raw-transcript out/录音.json --revisions out/revisions.json --ledger out/coverage.txt --mode qa-summary --source-kind audio --source 录音.wav --assurance high --refine-report out/录音.refine.json --docx out/会议纪要.docx --render-report out/会议纪要.render.json --make-review out/review.json
# 实际逐项复核并填写 review.json 后，以完全相同的输入和放行参数验收：
<runtime-python> scripts/check_all.py out/会议纪要.txt --transcript out/录音.accepted.json --raw-transcript out/录音.json --revisions out/revisions.json --ledger out/coverage.txt --mode qa-summary --source-kind audio --source 录音.wav --assurance high --refine-report out/录音.refine.json --docx out/会议纪要.docx --render-report out/会议纪要.render.json --review out/review.json --stage release
```

有副标题、术语库或放行参数时，前后命令保持一致。正式验收必须明确传入实际副标题，不能使用旧版未知单行豁免。清单绑定输入内容、相关参数和校验器版本；修改纪要、转录稿、DOCX、术语或规则后，旧确认失效。`checks-summary.json` 保存结果、输入哈希及复核清单哈希。原始稿、修订稿、修订记录、复核报告、覆盖清单、review.json、渲染 JSON 与纪要一并归档。PDF 逐页验收完成后可删除，用户要求 PDF 时保留。正式纪要默认交付 DOCX；只要转录或指定纯文本时尊重对应输出要求。

## 缓存与离线

检查点绑定实际音频内容和识别配置。模型、热词、语言、时间戳或增强设置变化时旧块不复用；损坏或旧版无指纹检查点重算。JSON 检查点原子写入，中断后可重新运行。复核预算变化可以复用配置一致的已完成片段。

主转录和复核均支持 `--offline`：模型别名先解析到本地缓存目录，缺失时报错；CLI 进程禁用 Python 网络连接。该机制不是操作系统防火墙，也不保证第三方原生扩展的联网行为；要求严格断网时在操作系统层断网后运行。模型已缓存并不代表校验器实际加载过，不能把文件存在当成加载成功。
