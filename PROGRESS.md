# 执行记录

最后更新：2026-10-05（Asia/Shanghai）。中断后先读此文件，再读 BLOCKED.md。独立分支 `chore/skills-library-20261005`，基线 `bf6f7d8cfb99265fc55ee45da5ea54150fff876d`。未改 main、未动旧工作区、单个执行 agent。

## 任务0：已完成

- `git ls-remote https://github.com/Icdafy/Skills.git HEAD refs/heads/main`：退出 0，两者均为基线提交。`gh api repos/Icdafy/Skills`：退出 0，当前账号 Icdafy 有 push 权限；未修改仓库权限。
- 新工作区 `work/Skills` 从远端克隆，初始状态干净；`git switch -c chore/skills-library-20261005`：退出 0。
- 默认 WindowsApps python 是占位入口。本次临时 PATH 首位使用既有 bundled Python，`python` 实际解释器为 Python 3.12.14；未安装运行依赖、未修改系统 PATH。版本与路径见 [summary.json](docs/validation/baseline/summary.json)。字体摘要使用 stdlib 读取，不增加 fontTools 依赖。
- 原五组 unittest 带 `-v` 复跑：50、258、56、8、3，共 375；374 通过，1 项既有跳过；全部进程退出 0。跳过为 `test_source_inventory_skips_symlink_that_resolves_outside_material_root`，Windows WinError 1314（创建文件符号链接缺少特权）。逐项名称和原始原因见 [基线目录](docs/validation/baseline/)。
- `python tools/check_shared_scripts.py`、`python tools/package_skills.py --check`、`git diff --check`：退出 0。全部七个 `python <技能>/scripts/skill_portability.py check --smoke`：退出 0。
- 已保存 237 个跟踪文件完整路径及 SHA-256：[tracked-files.json](docs/validation/baseline/tracked-files.json)；18 个受限字体副本及 fsType：[restricted-fonts.json](docs/validation/baseline/restricted-fonts.json)。

## 后续项

| 项目 | 状态 | 证据 |
|---|---|---|
| 1. 盘点、索引及迁移 | 已完成 | [237 个文件映射](docs/migration-map.json)；7 个源码根目录移入 skills/，19 个删除均列理由 |
| 2. 安装、打包、插件、README 入口 | 已完成 | 7 项 README、独立 LICENSE/NOTICE/VERSION；索引生成首页和市场，中央资源/链接检查已跑通 |
| 3. 单技能升级及维护说明 | 已完成 | [维护说明](docs/maintenance.md)；临时副本只改 yiti 后，重建仅改变其 ZIP，其他六个摘要保持不变 |
| 4. 许可和受限字体 | 已完成 | 维护者素材授权确认；18 字体移除；递归分发扫描命中 0，LICENSE 与 NOTICE 随单包 |
| 5. 原测试、仓库外安装、客户端、反向验收 | 已执行；严格四问未通过，人工抽查待完成 | [实际验证](docs/validation.md)、[未达项](BLOCKED.md) |
| 独立分支、提交和 PR | 待办 | |

完整验收轮次：1 / 3；第1轮全绿。局部检查不当作完整验收；每轮必须记录全部命令及结果。

## 盘点与迁移完成

- 以实际 `SKILL.md` 识别七项技能。`skills-index.json` 定义稳定 ID、中文分类、源码/README/ZIP 路径、分发版本、验证状态及十组共享副本。
- `git mv <原技能> skills/<原技能>` 七次退出 0；映射覆盖全部 237 个原跟踪文件。删除仅限 18 个受限字体副本及仅含换行的 `Skills军团` 占位物，逐项原因见映射。
- 本机试验用的旧授权字体保存到仓库外 `work/local-fonts`，不提交、不打包；未安装到系统。
- 2026-10-05 用户明确答复：“全部由我有权授权，可按 Apache-2.0 公开”。覆盖询问列明的旧模板、报告模板/预览、立项范文及原业务规则。许可清单记录为维护者授权确认，不推断第三方来源为原创。字体继续按已知限制排除。
- 路径修复脚本退出 0：原仓库级测试只调整根路径、插件 source 期望路径；后续字体资源契约调整将先列依据。

## 入口与分发完成（局部证据）

- `python tools/check_shared_scripts.py --sync`：退出 0。原十组保留；增加六技能 `local_fonts.py` 物理副本组，会议纪要 embed_fonts 仍不进入五技能组。
- `python tools/sync_catalog.py`：退出 0，索引生成中文 7/7 首页表、下载表、市场 source 和版本。
- `python tools/package_skills.py`：最终重建七个去字体 ZIP，退出 0。此前局部运行在 officialese 的旧字体路径引用处明确失败；修正 SKILL.md 的资源定位后重跑，没有吞掉失败。
- `python tools/check_library.py`：退出 0，7 项集合/入口/包一致，11 组共享一致，237 个映射/19 个带理由删除，本地断链 0；291 个文件递归扫描 ZIP/OOXML/CFB，字体命中 0。此前因尚未创建 maintenance.md 退出 1；创建后真实全绿。
- `python -m unittest discover -v -s tools/tests -p test_sibling_docx_skills.py`：7 项通过，退出 0；原字号、charset、嵌入及生成器断言保留。
- 已先登记 [字体契约调整依据](docs/font-test-contract.md)；13 个旧字体输入改为临时 SFNT/OS2 数据（无第三方字形），另补 13 个正负成对测试；完整回归待执行。

## 升级与独立安装完成

- 仓库外系统临时目录名称含中文和空格，清除 PYTHONPATH；七个正式 ZIP 逐一解压后 `python <绝对技能路径>/scripts/skill_portability.py check --smoke` 全部退出 0。日志见 [distribution](docs/validation/distribution/summary.json)。
- 七技能项目目录安装、预览不写入、额外文件时退出 1 并保留原件、replace 将旧目录移出发现目录、备份保留用户笔记及新目录完整性检查全部按实际命令通过。会议纪要私有公司词库在 replace 后仍完整保留；未修改真实已安装技能。
- 在临时副本中修改投委会议题 writing-logic 后 `python tools/package_skills.py --skill yiti-skill` 退出 0，只有 yiti ZIP SHA-256 改变，其他六个不变；随后全库检查退出 0，摘要见 [single-skill-hashes.json](docs/validation/distribution/single-skill-hashes.json)。
- 四种独立故障均红→绿：缺资源、错误市场路径、源码更新导致旧 ZIP、受限字体回流均退出 1，恢复后退出 0。字体回流首次先被过期包挡住，已调整中央扫描顺序，另补直接摘要命中的反向证据。
- `python -m unittest discover -v -s tools/library_tests`：13 项正负成对测试全部通过，退出 0，原五组数量未改变。
- 旧 25 个测试文件的 375 个方法名称、断言 AST 和 decorators 保留（只归一已允许的资源/路径变化）；15 个模板/素材和8个业务渲染器保持原内容，审计退出 0：[frozen-content.json](docs/validation/frozen-content.json)。
- 可用 Codex 新会话已真实读取项目 .agents/skills 下的技能并询问阶段。完整21例路由矩阵进行中；记录读取命令、原输出和最终答复，不能拿脚本成功替代调用。
- 真实 Microsoft Word 字体阴性/阳性探针：gongsi embed 验证退出 0，未嵌入时为 SimSun，嵌入后为 ___WRD_EMBED_SUB_46。使用已存在的本机 fontTools（临时 PYTHONPATH），没有安装依赖、字体或模型。

## 第1轮完整验收已通过

- `docs/validation/round-1/summary.json`：所有实际命令退出 0。原五组发现数仍为 50、258、56、8、3（共375），只有原文件符号链接用例因同一 WinError 1314 跳过；原374项通过。新增独立13项正负契约测试均通过，无新增skip/todo。
- 同轮共享11组、索引首页市场、全部7ZIP、旧打包入口、统一校验、git diff --check 全部退出0，逐项原输出保存在该轮目录。
- 字体摘要直接反向验证（包括改名为 .bin）：退出1，明确 `Restricted font distribution: skills/yiti-skill/assets/fonts/reintroduced.bin`；恢复退出0。[红输出](docs/validation/distribution/red-restricted-font-fingerprint.txt)、[绿输出](docs/validation/distribution/green-restricted-font-fingerprint-restored.txt)。
- 会议纪要专用 embed_fonts 的真实 Word 阴性/阳性探针也退出0，与共同组分别验证：[Word输出](docs/validation/word-embedding/meeting-minutes-pro.txt)。
- Codex 矩阵持续进行。部分临时分类显示 loaded 为空，已查原始读取命令：原因是命令里有重复转义的 Windows 反斜杠，实际读取退出0且完整返回正确 SKILL.md。收集结束后只修正证据路径解析，不修改原输出、不把失败调用标为成功。
- 七项 README 再次人工阅读后，修正“前六个技能”这种无法独立理解的字体说明，分别给出本技能实际检测命令；纪要文本检查不再误写依赖 python-docx。旧安装脚本标明兼容初次安装，升级使用已验证的项目安装入口。`python work/refine_readmes.py`（仓库外临时脚本）退出0；只改安装/依赖说明，业务用法保留。README 和公共安装说明变化将在最终状态回填后同步、重建受影响包并复查。
- Codex CLI 0.160.0 的21个新会话已全部运行完（每个CLI退出0）。最初证据解析进程退出1、错误分类为8/21；逐一核对原始读取退出码及SKILL.md完整内容后，`python work/review_client_matrix.py` 退出0，路由21/21正确。原始jsonl/final未改，旧分析保存在 initial-analysis.json。
- 严格首轮行为审计为18/21：三个涉及投后报告的会话，四问原文及顺序均正确，但整个首轮含进度或技能依据说明，违反“只能四问”，记入BLOCKED.md。最终答复本身有2/3只含四问，不能据此忽略此前agent_message。未修改冻结业务规则，也未宣称全部客户端行为全绿；同项三例均未通过后停止该项，转入纪要文本验证。
- 证据解析还遇到公司显式调用用 Join-Path 拼接 SKILL.md（中间解析退出1、20/21）。已人工核对：命令退出0，实际根目录正确，完整输出 name: gongsi-qingkuang；增加此真实命令形式后解析退出0、21/21。原始模型输出和失败的初始分类都保留，严格四问的3项失败不改变。
- `python tools/check_shared_scripts.py --sync` 再次退出0，只同步 agent-compatibility.md 中自动检测预览说明，11组一致；未改其他业务规则。
- 纪要文本新会话真实生成完成：`python work/client_text_case.py` 退出0，2组完整问答、3窗全纳入、24个数字事实，四项实际脚本检查全部退出0，无放行或省略；明确 draft / release_ready:false，没有冒称DOCX、录音回听或正式交付。原模型命令和生成文件保存至 [minutes-text](docs/validation/clients/codex/minutes-text/summary.json)。执行者用源码 check_all.py 再核对也退出0。
- 纪要输入/输出摘要及19个未改脚本比对通过。第一次完整脚本比对退出1，差异是临时安装快照早于维护者对 portability 的 VERSION/LICENSE/NOTICE LF 归一修正；已核对唯一这一行，不涉及四项文本检查，也未被模型改动。记录保留该快照差异，不把它当成业务检查成功。
- 严格Codex行为验收分析实际退出1，18/21，失败三例保留于 [behavior-review.txt](docs/validation/clients/codex/behavior-review.txt)；证据路径解析成功不再作为行为全绿的退出码。
- 真实语音可用性检查 `python skills/meeting-minutes-pro/scripts/bootstrap_runtime.py --check` 退出0：已有 F:/ASR模型 runtime、Python3.12.14、FunASR和Qwen可用、CUDA RTX3060。已用既有 Windows System.Speech 合成非敏感短语音（603092字节），只在仓库外work保存；两个引擎使用 --offline 验证进行中，不下载模型。
- 真实引擎结果：FunASR `paraformer-zh --offline --device cuda` 退出0；Qwen CUDA首次退出1，明确“CUDA was requested but is unavailable”；保留失败后以同一已有0.6B模型 `--offline --device cpu --max-new-tokens 128` 重试退出0。两者真实推理13.675秒合成语音，收入1200万元、20%、签约800万元及意向200万元均识别保留；未下载模型或改运行环境。[逐次结果](docs/validation/asr/summary.json)。这不证明长会、方言、分离或双引擎全量回听已验证。

## 最终分发与说明复查已通过

- `python work/finalize_docs.py`（仓库外）退出0：按实际客户端及ASR证据回填索引和七项README，不把投后四问失败标绿；Claude Code/其他客户端明确未实测。单包新增本机字体检测说明及本技能升级说明，不扩写业务规则。
- `python work/final_checks.py`（仓库外）退出0：[最终16个实际命令](docs/validation/final/summary.json)均退出0。只因本次七项README/共享安装说明全部受影响，使用七个明确 --skill 重建七包；最终7/7 ZIP再次仓库外中文空格路径 smoke成功。
- 最终catalog、shared11组、packages7个、旧打包命令、统一入口、冻结内容审计、git diff --check均退出0。Python3.12.14、python-docx1.2.0、pypdf6.10.0；没有安装新依赖。运行代码自第1轮后未改，说明回填只做受影响的分发复查，不冒充第2轮完整回归。
- 远端main再次核对仍为bf6f7d8cfb99265fc55ee45da5ea54150fff876d，push权限true。下一步提交此独立分支并建草稿PR；不自动合并。
- 首次 `git add -A` 后，`git diff --cached --check` 退出1：新增独立LICENSE副本和两份新README末尾多了空白行；原输出保存 staged-whitespace-red.txt。只去掉EOF空白行并归一LF，许可文字/署名/业务内容均不变。此前最终检查保存在 before-whitespace-fix/，因这次元数据变化重新打受影响七包并复查；不跳过检查、不改Git whitespace规则。
- 上条退出1是PowerShell封装的失败状态，实际Git进程退出2；首次临时修复脚本误要求1而退出1，尚未修复。已依据原始exit=2记录调整修复脚本，执行退出0，才真正完成文末空行清理。保留真实非零输出；工作树代码和测试没有变化。
- 清理后的受影响七包已重建；最终16项全部退出0，7/7再次仓库外烟测成功，旧包命令、统一校验及冻结审计通过。此前检查快照和原始空白错误仍保留。准备重新暂存、检查许可字体跟踪数量及白名单后提交。
- 重新暂存后 `git diff --cached --check` 实际退出0，空白错误红（Git退出2）→绿（退出0）。[绿输出](docs/validation/final/staged-whitespace-green.txt)。暂存白名单/敏感输出检查退出0：693个变更路径（不折叠rename），越界0、跟踪字体0、符号链接0、密钥模式命中0、main未改；[审计](docs/validation/final/scope-and-secret-audit.json)。
- 首次commit退出1，原因仅为未配置Git作者身份。`gh api user`确认已登录Icdafy，公开名称Kuangdi Liu、ID184378185；使用该账号公开noreply身份的单命令 `git -c user.name=... -c user.email=... commit`，不修改全局或本地Git配置。[GitHub公开格式依据](https://docs.github.com/en/account-and-profile/reference/email-addresses-reference)。
