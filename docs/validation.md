# 实际验证记录

日期：2026-10-05（Asia/Shanghai）。基线 `bf6f7d8cfb99265fc55ee45da5ea54150fff876d`，独立分支 `chore/skills-library-20261005`。只使用已有运行依赖；Python实际为3.12.14。未改main、用户旧工作区、权限、历史或旧发布。

## 原测试与完整验收

按维护者最新反馈，七项唯一源码直接放在仓库根目录。第2轮完整验收12个命令全部退出0；完整修改→验收轮次为2/3。五组原用例合计375个名字完整保留，374通过、1个原环境跳过。新增13项字体资源正负成对测试全部通过，无新增skip/todo。[当前布局实际命令及退出码](validation/round-2/summary.json)。第1轮原始命令和结果保留在 [历史第1轮](validation/round-1/summary.json)，其中 skills/ 是当时真实路径。

| 实际命令 | 发现数 | 退出码 / 结果 |
|---|---:|---|
| `python -m unittest discover -v -s tools/tests` | 50 | 0 / 全通过 |
| `python -m unittest discover -v -s meeting-minutes-pro/tests` | 258 | 0 / 全通过 |
| `python -m unittest discover -v -s soe-post-investment-report/tests` | 56 | 0 / 55通过、原1跳过 |
| `python -m unittest discover -v -s gongsi-qingkuang/evals` | 8 | 0 / 全通过 |
| `python -m unittest discover -v -s officialese-skill/scripts -p test_create_official_docx.py` | 3 | 0 / 全通过 |
| `python -m unittest discover -v -s tools/library_tests` | 13（另列） | 0 / 全通过 |

原跳过名称 `test_source_inventory_skips_symlink_that_resolves_outside_material_root`，原因仍是WinError1314“客户端没有所需的特权”，没有新增跳过。[基线原因](validation/baseline/soe-tests.txt)与[根目录布局原输出](validation/round-2/soe-tests.txt)均保留。

[冻结内容审计](validation/frozen-content.json)：原25个测试文件的375个名称、断言和decorators保留；只归一允许的路径/字体输入变化。15个模板素材和8个业务渲染器保留原内容，审计退出0。字体契约先登记[依据](font-test-contract.md)，再调整输入并补等量13项有效正负测试，不放宽版式断言。

第2轮 `check_shared_scripts.py`、`sync_catalog.py --check`、`package_skills.py --check`、旧 `package_investment_skills.py --check`、`check_library.py`、`git diff --check` 均退出0。本次七项README/CHANGELOG路径均受影响，以七个明确 --skill 重建七包。[重建实际输出](validation/flat-layout/preparation.json)与[当前分发结果](validation/flat-layout/distribution/summary.json)以实际日志为准；旧版 final/ 证据保留。

## 七个ZIP与项目安装

[当前独立分发验证](validation/flat-layout/distribution/summary.json)：七包分别解压到仓库外含中文和空格的临时路径，清除PYTHONPATH后执行其 `scripts/skill_portability.py check --smoke`，7/7退出0。预览不写、项目安装、备份、多余文件先停止（预期退出1）、确认replace后保留本地文件与纪要私有术语均已验证；未修改真实已安装技能。

临时副本只修改yiti并执行 `python tools/package_skills.py --skill yiti-skill`，退出0，只有该ZIP变化，另六个摘要不变；随后全库校验退出0。[当前前后摘要](validation/flat-layout/distribution/single-skill-hashes.json)。本次根目录布局新版七包再次仓库外烟测；53条实际分发/安装/反向命令全部符合预期。旧 [分发证据](validation/distribution/summary.json) 保留。

## 反向校验实际红→绿

| 制造的故障 | 红结果 | 恢复后 |
|---|---|---|
| 删除必需资源 | [退出1：Missing resources](validation/flat-layout/distribution/red-missing-resource.txt) | [退出0](validation/flat-layout/distribution/green-missing-resource-restored.txt) |
| 错误插件source路径 | [退出1：Marketplace differs](validation/flat-layout/distribution/red-plugin-path.txt) | [退出0](validation/flat-layout/distribution/green-plugin-path-restored.txt) |
| 修改源码而不重建ZIP | [退出1：ZIP is stale](validation/flat-layout/distribution/red-stale-zip.txt) | [退出0](validation/flat-layout/distribution/green-stale-zip-restored.txt) |
| 受限字体改名.bin回流 | [退出1：Restricted font distribution](validation/flat-layout/distribution/red-restricted-font-fingerprint.txt) | [退出0](validation/flat-layout/distribution/green-restricted-font-fingerprint-restored.txt) |

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

本次只改仓库源码位置、README/CHANGELOG及仓库入口。214个其他配套文件与上一提交等价，七个SKILL.md全部未变；客户端实际安装目录仍是.agents/skills。因此保留原21会话、纪要文本及ASR实测证据，没有伪称重新跑过模型调用。[逐文件等价证明](validation/flat-layout/source-content-equivalence.json)。

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
