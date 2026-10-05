# 实际验证记录

最新范围：维护者已授权原main18份字体文件保持原路径/字节，其余PR内容统一合并到main。下方原三轮与原完成审计按受测快照保留；其中“源码字体为0”“第三方待决0”“不自动合并”不适用于最新交付。当前源码保留18份，单技能ZIP/安装器排除字体，许可仍待决。合并与新增验证见[选择性合并](validation/selective-merge/README.md)。

日期：2026-10-05（Asia/Shanghai）。基线 `bf6f7d8cfb99265fc55ee45da5ea54150fff876d`，独立分支 `chore/skills-library-20261005`。只使用已有运行依赖；Python实际为3.12.14。未改main、用户旧工作区、权限、历史或旧发布。

补充范围：维护者新增“四种中文字体随七技能分发”，并确认保留宋体页码和Times New Roman数字/英文；随后明确答复“没有此授权，或尚不清楚”。新要求因缺公开再分发授权记为B4未完成，未修改源码、测试、版本或ZIP。以下3轮及仓库外运行结果证明当前去字体分发方案，不能证明新字体随包要求已实现。[本次输入核查与授权答复](validation/font-request/README.md)。

## 原测试与完整验收

按维护者最新反馈，七项唯一源码直接放在仓库根目录。最后第3轮完整验收12个命令全部退出0；完整修改→验收轮次为3/3，停止修改实现。五组原用例合计375个名字完整保留，374通过、1个原环境跳过。新增13项字体资源正负成对测试全部通过，无新增skip/todo。[最终实际命令及退出码](validation/round-3/summary.json)。第1轮原始命令和结果保留在 [历史第1轮](validation/round-1/summary.json)，其中 skills/ 是当时真实路径；[第2轮根目录记录](validation/round-2/summary.json)也保留。

| 实际命令 | 发现数 | 退出码 / 结果 |
|---|---:|---|
| `python -m unittest discover -v -s tools/tests` | 50 | 0 / 全通过 |
| `python -m unittest discover -v -s meeting-minutes-pro/tests` | 258 | 0 / 全通过 |
| `python -m unittest discover -v -s soe-post-investment-report/tests` | 56 | 0 / 55通过、原1跳过 |
| `python -m unittest discover -v -s gongsi-qingkuang/evals` | 8 | 0 / 全通过 |
| `python -m unittest discover -v -s officialese-skill/scripts -p test_create_official_docx.py` | 3 | 0 / 全通过 |
| `python -m unittest discover -v -s tools/library_tests` | 13（另列） | 0 / 全通过 |

原跳过名称 `test_source_inventory_skips_symlink_that_resolves_outside_material_root`，原因仍是WinError1314“客户端没有所需的特权”，没有新增跳过。[基线原因](validation/baseline/soe-tests.txt)与[最后第3轮原输出](validation/round-3/soe-tests.txt)均保留。

[冻结内容审计](validation/frozen-content.json)：原25个测试文件的375个名称、断言和decorators保留；只归一允许的路径/字体输入变化。15个模板素材、6个业务渲染/规约文件字节相同；另2个生成器仅一条字体资源提示字面量改变，精确归一后全文等于基线，布局与业务代码不变。审计退出0。字体契约先登记[依据](font-test-contract.md)，再调整输入并补等量13项有效正负测试，不放宽版式断言。

第3轮 `check_shared_scripts.py`、`sync_catalog.py --check`、`package_skills.py --check`、旧 `package_investment_skills.py --check`、`check_library.py`、`git diff --check` 均退出0。根目录调整时七项README/CHANGELOG路径均受影响，以七个明确 --skill 重建七包；字体补审按实际六个--skill重建六包，投后包摘要不变。[重建实际输出](validation/flat-layout/preparation.json)与[当前分发结果](validation/flat-layout/distribution/summary.json)以实际日志为准；旧版 final/ 证据保留。

## 七个ZIP与项目安装

[最终独立分发验证](validation/font-guidance/distribution/summary.json)：七包分别解压到仓库外含中文和空格的临时路径，清除PYTHONPATH后执行其 `scripts/skill_portability.py check --smoke`，7/7退出0。预览不写、项目安装、备份、多余文件先停止（预期退出1）、确认replace后保留本地文件与纪要私有术语均已验证；未修改真实已安装技能。

临时副本只修改yiti并执行 `python tools/package_skills.py --skill yiti-skill`，退出0，只有该ZIP变化，另六个摘要不变；随后全库校验退出0。[最终前后摘要](validation/font-guidance/distribution/single-skill-hashes.json)。最后七包再次仓库外烟测；53条实际分发/安装/反向命令全部符合预期。旧 [分发证据](validation/distribution/summary.json) 保留。

## 反向校验实际红→绿

| 制造的故障 | 红结果 | 恢复后 |
|---|---|---|
| 删除必需资源 | [退出1：Missing resources](validation/font-guidance/distribution/red-missing-resource.txt) | [退出0](validation/font-guidance/distribution/green-missing-resource-restored.txt) |
| 错误插件source路径 | [退出1：Marketplace differs](validation/font-guidance/distribution/red-plugin-path.txt) | [退出0](validation/font-guidance/distribution/green-plugin-path-restored.txt) |
| 修改源码而不重建ZIP | [退出1：ZIP is stale](validation/font-guidance/distribution/red-stale-zip.txt) | [退出0](validation/font-guidance/distribution/green-stale-zip-restored.txt) |
| 受限字体改名.bin回流 | [退出1：Restricted font distribution](validation/font-guidance/distribution/red-restricted-font-fingerprint.txt) | [退出0](validation/font-guidance/distribution/green-restricted-font-fingerprint-restored.txt) |

四项当前布局反向检查均真实退出1，精确恢复后各退出0。字体改名.bin仍由原摘要直接命中。历史首次字体回流先被旧ZIP拦住的输出保留在旧distribution/；不把过期包报错冒充字体规则命中。

## 真实客户端调用

Codex CLI **0.160.0**：在仓库外中文空格临时项目安装七项 `.agents/skills/<name>`，原用户同名副本仅在每次CLI调用配置中停用，未写全局配置。每例新建 `codex exec --ephemeral` 会话，记录原提示、真实Get-Content命令、退出码、完整SKILL.md输出及最终答复。[21例摘要](validation/clients/codex/summary.json)与[行为验收输出](validation/clients/codex/behavior-review.txt)。

| 技能 | 显式请求 | 自然语言 | 相邻反例路由 | 首轮限制 |
|---|---|---|---|---|
| hangye-fenxi | 实际加载正确 | 实际加载正确 | zhuying-yewu-fenxi正确、未载行业 | 先问早前期/中后期 |
| zhuying-yewu-fenxi | 实际加载正确 | 实际加载正确 | gongsi-qingkuang正确、未载主营 | 先问早前期/中后期 |
| gongsi-qingkuang | 实际加载正确 | 实际加载正确 | hangye-fenxi正确、未载公司 | 先问早前期/中后期 |
| officialese-skill | 实际加载正确 | 实际加载正确 | yiti-skill正确、未载通用公文 | 补必要材料 |
| yiti-skill | 实际加载正确 | 实际加载正确 | 投后正确、未载议题 | 判会议类，补通知和议案 |
| meeting-minutes-pro | 实际加载正确 | 实际加载正确 | officialese-skill正确、未载纪要 | 一次补齐基本信息 |
| soe-post-investment-report | 实际加载正确 | 实际加载正确 | 公司正确、未载投后 | 严格只四问未通过 |

路由21/21正确；严格首轮行为18/21。三个实际加载投后技能的会话（显式、自然、yiti相邻反例）四问文字和顺序均正确，但还发出进度或技能依据说明。最终答复2/3只含四问，整个首轮0/3符合“只能四问”；已保留失败，行为审计退出1。同项三例失败后停止，不扩写冻结业务规则，也不只看最终答复来伪报成功。[未达项](../BLOCKED.md)。

最初Windows重复反斜杠和Join-Path导致证据分类8/21与20/21，均是解析问题；每次真实读取都退出0。保留[初始分类](validation/clients/codex/initial-analysis.json)及原jsonl，人工核对后只修正路径解析，不改模型输出。既有客户端配置警告也保留，没有擅自改用户设置。

根目录布局调整时，214个配套文件（包含七个SKILL.md）与当时上一提交等价；该时点的 [逐文件证明](validation/flat-layout/source-content-equivalence.json) 保留。之后补审只修正字体来源/下载说明、共享嵌入器文档字符串及两个CLI提示，阶段选择、首轮四问、纪要文本/语音和事实规则未改。客户端安装目录仍是.agents/skills。原21会话展示其受测快照的真实行为，不伪称字体说明修正后重新跑过模型调用。

## 字体说明补审与提示分支边界

实际README/SKILL/reference补审发现旧“自带字体”和“GitHub下载兜底”说明，已更正为本机授权来源；共享嵌入器只改gongsi基准说明后同步，纪要专用脚本未入组。仅六包受影响并按六个--skill重建，投后包摘要不变。[实际结果](validation/font-guidance/summary.json)。

公文/议题生成器各以现有临时SFNT与空目录真实调用，四次CLI退出0：阳性嵌入两字体/charset86，阴性无嵌入并说明ICDAFY_FONT_DIR与未嵌入草稿。本机三字体已全部注册，新增“本机未安装”提示分支没有触发，仅由精确字面量全文审计证明其更正；不声称该分支实测。第一次探针错误要求stderr分支出现而退出1，保留 [失败记录](validation/font-guidance/failed-probe.txt) 和原CLI输出；旧375测试未改，不改旧探针断言、不mock注册表或安装字体。

Claude Code当前PATH及既有入口均未找到可执行程序（只发现安装器，未运行）。其他客户端本次未实测；[可用性记录](validation/clients/unavailable.json)。官方安装说明已核对：[Codex](https://learn.chatgpt.com/docs/build-skills)、[Claude Code](https://code.claude.com/docs/en/skills)。保留说明不等于真实调用通过。

## 纪要文本、字体与真实语音

Codex新增独立会话，基于完整虚构元信息及两组问答真实保存纪要文本。[摘要及文件摘要](validation/clients/codex/minutes-text/summary.json)。内容保留统计口径、尚未审计、签约未交付和意向未签约等限定；四项校验全部退出0，3窗全纳入、2问答、24数字，无放行。19个实际脚本内容比对不变；唯一安装快照差异是维护者后加的portability元数据LF归一，不用于文本校验。执行者用源码再次check_all退出0。[纪要正文](validation/clients/codex/minutes-text/generated/会议纪要.txt)、[执行者复核](validation/clients/codex/minutes-text/executor-recheck.txt)。本例仅文本draft，release_ready:false，不声称完成DOCX或音频回听。

真实Microsoft Word字体探针，使用现有本机授权字体及fontTools（临时PYTHONPATH，未安装）：[共同组gongsi](validation/word-embedding/gongsi-qingkuang.txt)与[纪要专用组](validation/word-embedding/meeting-minutes-pro.txt)均退出0。阴性PDF为SimSun，嵌入阳性出现 ___WRD_EMBED_SUB_46；这证明嵌入生效，不能代替全部业务文档逐页视觉验收。

`python meeting-minutes-pro/scripts/bootstrap_runtime.py --check` 在当前根目录布局亲跑退出0，发现已有F盘ASR运行时Python3.12.14和本地模型：[当前路径输出](validation/flat-layout/runtime-check.txt)。用现有Windows System.Speech合成13.675秒非敏感中文，真实离线推理：[全部尝试](validation/asr/summary.json)。

| 引擎 | 实际参数 | 退出码 | 结果 |
|---|---|---:|---|
| FunASR paraformer-zh | --offline --device cuda | 0 | 收入1200万元、20%、签约800万元、意向200万元识别保留 |
| Qwen3-ASR0.6B首次 | --offline --device cuda | 1 | CUDA was requested but is unavailable |
| Qwen3-ASR0.6B重试 | --offline --device cpu --max-new-tokens128 | 0 | 同四项量化信息识别保留 |

合成音频留在仓库外work，仅保存命令、摘要和输出；不分发录音、权重或新增依赖。已实测真实引擎与中文短样本；真实会议、长音频、方言、说话人分离、双引擎全量回听未实测。

## 许可与最后浏览

维护者已明确确认原模板、范文、预览和业务规则有权以Apache-2.0公开。18个受限字体副本已删除，237个文件映射完整，19个删除都有理由。统一入口递归扫描源码、全部ZIP、OOXML关系及CFB流，字体命中0。旧历史和旧发布保留。[许可清单](../THIRD_PARTY_NOTICES.md)。第三方授权待决项0。

维护者最终浏览首页、七项README及maintenance.md尚待完成；执行者阅读和自动检查不能替代。已交付 [草稿PR #12](https://github.com/Icdafy/Skills/pull/12)，收到“七技能直接放根目录”的反馈并已完成调整/重新验收；修改后的最终抽查仍待确认。BLOCKED.md保留严格四问和人工抽查两项。本任务没有宣称所有完成条件已满足。

逐项验收范围、证据及未达条件见 [完成审计](completion-audit.md)。完整验收已满3轮，不继续修改实现；最终人工抽查尚未收到答复。
