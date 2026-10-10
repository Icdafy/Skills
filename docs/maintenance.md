# 安装、维护与验证

七项技能的唯一源码位于仓库根目录 `<英文名>/`，集合、路径、版本、Release 和共享组以 [skills-index.json](../skills-index.json) 为准。各技能可独立安装和分发；公共工具和本页只用于维护仓库，不作为技能安装。

## 安装与更新

在 [首页](../README.md) 选择技能，下载对应版本的 GitHub Release ZIP，解压得到 `<英文名>/SKILL.md`。保留完整目录，不只复制 SKILL.md；整库 Download ZIP 不能作为单技能包上传。Release 提供 ZIP 和 SHA-256，ZIP 内含逐文件 manifest、VERSION、README、LICENSE、NOTICE 及本技能资源，不含字体、模型或私有词库。

在解压出的技能目录安装依赖，然后检查并安装到指定项目，例如：

```powershell
python -m pip install -r requirements.txt
python scripts/skill_portability.py check --smoke
python scripts/skill_portability.py install --agent codex --scope project --project-dir "C:/项目/示例 项目"
python scripts/skill_portability.py install --agent codex --scope project --project-dir "C:/项目/示例 项目" --apply
```

Python 3.10+；Word 生成依赖及会议纪要的 ASR 环境按各技能 README 准备。安装器默认只预览，`--apply` 才写入。Codex 项目路径为 `.agents/skills/<英文名>`；Claude Code 改用 `--agent claude-code`，路径为 `.claude/skills/<英文名>`。用户级安装去掉项目参数；客户端另有指定目录时使用 `--skills-dir "绝对目录"`。旧版仍读取 `$CODEX_HOME/skills` 时可用 `--agent codex-legacy`，并在实际客户端核对路径。

Claude Code 也可运行 `/plugin marketplace add Icdafy/Skills`，再运行 `/plugin install <英文名>@icdafy-skills`。Codex 可运行 `$skill-installer install https://github.com/Icdafy/Skills/tree/main/<英文名>`。不要重复启用同名的目录安装和市场安装；源码安装与版本固定的 Release 下载分别核对实际 VERSION。

更新时将新版解压到另一个目录，核对 VERSION 和 CHANGELOG，检查后仅更新指定项目或技能。安装器先备份旧目录到技能发现目录之外的 `skill-backups/`；遇到旧版多余文件会停止。检查备份后，可用 `--replace --apply` 将整个旧目录移入备份再安装。会议纪要的 `glossary/` 私有项目词库和禁词表自动保留，不进入 ZIP；其他本地材料保留在备份中，按需要取回。

安装后新建会话，完成显式调用、自然语言调用和相邻技能反例检查，观察实际加载路径。复制目录或脚本通过不能证明模型已经调用。Codex 的路径与 `$<name>` 见 [官方说明](https://learn.chatgpt.com/docs/build-skills)，Claude Code 的路径与 `/<name>` 见 [官方说明](https://code.claude.com/docs/en/skills)；其他客户端入口及验证程度见各技能 `references/agent-compatibility.md`。

## 按技能独立维护

- 用户点名一个技能，只升级该技能；点名多个，只升级指定集合。只有明确要求“所有技能”或“全库升级”，才升级全部技能。整理、修复或优化单个技能不扩大升级范围。
- 每个技能独立维护源码、VERSION、CHANGELOG、索引自身记录和 Release 安装包。公共元数据只登记目标变更；其他技能的源码、版本、变更记录和发布资产保持不变。
- 共享组记录当前副本的一致关系，不构成扩大升级范围的授权。单技能任务不运行全库 `check_shared_scripts.py --sync`。需要独立修改共享副本时，只改目标，按实际依赖调整 `shared_groups`；目标为 canonical 时，先将基准移至保留原内容的成员。保持组非空、基准在组内及其余成员一致。
- 检查公共工具对 canonical 与资源契约的依赖，优先在目标技能适配；必要时只调整支持目标升级所需的公共工具。确实需要修改其他技能时，先说明对象和原因，由用户明确扩大范围。
- 全库只读检查可以发现影响、确认未指定技能未变化。提交前检查 diff 和目标包。独立分支提交并发可审查 PR，不自动合并。

共享文件以索引的 `shared_groups` 为准，独立分发仍保留物理副本，不跨技能 import 或用符号链接代替。`meeting-minutes-pro/scripts/embed_fonts.py` 由自己的 `format_spec.py` 驱动，不属于其他五技能的 embed_fonts 同步组，不能直接覆盖。

## 构建与发布

只升级 `yiti-skill` 的例子，在仓库根目录执行：

```powershell
python tools/sync_catalog.py
python tools/check_shared_scripts.py
python yiti-skill/scripts/skill_portability.py check --smoke
python tools/package_skills.py --skill yiti-skill
# 将构建输出的 SHA-256 登记到目标 release.sha256 后再校验
python tools/package_skills.py --check --skill yiti-skill
python tools/check_library.py
git diff --check
```

先更新目标 VERSION、CHANGELOG、索引 version、对应的 release.tag 及 SKILL.md 中已有的 metadata.version，再生成目录并运行受影响测试。构建会输出新包摘要，发布前将它登记到目标 release.sha256；该字段锁定已发布 ZIP 的字节，不能靠只改版本沿用旧摘要。`sync_catalog.py --check` 只读核对首页和插件市场；普通共享检查不写入副本。

安装包输出到 `work/releases/<英文名>/<版本>/`，不提交 ZIP 或 SHA-256。GitHub Releases 按 `<英文名>/v<版本>` 分别发布 ZIP 与校验文件；Release 是下载入口，源码仍在根目录技能中。发布前核对 ZIP 中 VERSION、逐文件 manifest、SHA-256 和目标源码。发布一个技能不重新发布其他技能。

`--skill <英文名>` 只构建一个技能，可重复指定获准的集合；无选择参数的写入会被拒绝，`--all` 只用于明确授权的全库构建。旧 `tools/package_investment_skills.py` 也要求明确选择；它的 `--all` 仅指历史立项三个技能，`--check` 默认只读检查这三个技能。只升级共享组的部分成员时，不能因组关系自动重打全部成员。

`package_skills.py --check` 检查本地 Release 缓存；`--check --download` 下载已公开的发布资产并校验。`check_library.py` 默认检查源码、索引、名称、版本、资源、共享关系、链接、许可、字体契约和已有本地包；`--release-assets` 另行核验公开 Release 资产。远端检查需要联网，尚未发布的版本用本地包检查。

## 测试与验证范围

运行受影响测试；共享排版脚本变化时还需完整回归和实际字体渲染证据。原五组回归及字体契约命令保留：

```powershell
python -m unittest discover -s tools/tests
python -m unittest discover -s meeting-minutes-pro/tests
python -m unittest discover -s soe-post-investment-report/tests
python -m unittest discover -s gongsi-qingkuang/evals
python -m unittest discover -s officialese-skill/scripts -p test_create_official_docx.py
python -m unittest discover -s tools/library_tests
```

Windows 中文输出环境可设置测试进程 `PYTHONIOENCODING=utf-8` 和 `PYTHONUTF8=1`。日志、模型调用输出、安装试验和渲染缓存保存在本地 `work/validation/`，不提交。本页记录结论、日期、受测范围和证据入口；脚本检查不代替客户端调用、实际 ASR 或 Word 逐页验收。

### 历史实测范围

2026-10-05 在 Windows / Python 3.12.10 上执行原五组375项回归加17项字体契约，共392项：391通过，1项因既有 Windows 符号链接权限跳过，0失败。字体契约首次运行有两个中文输出编码错误，设置上述环境变量后17项全通过，未修改断言。统一校验、七包源码一致性、11组共享副本、18份字体摘要和本地链接检查通过。此结果记录当时版本，不表示当前改动已完成全部实测。

| 范围 | 已记录结果及限制 |
|---|---|
| 分发与安装 | 七个独立 ZIP 仓库外烟测，项目安装、备份及纪要私有术语保留通过 |
| Codex CLI 0.160.0 | 21个新会话路由21/21；严格首轮行为18/21。投后三例四问正确，但另有进度或依据说明 |
| 会议纪要文本 | 虚构素材文本通过四项检查；仍是草稿，未完成 DOCX 验收或音频回听 |
| ASR | 13.675秒中文合成音频：FunASR离线CUDA、Qwen3-ASR 0.6B离线CPU通过；Qwen CUDA失败。真实会议、长音频、方言及说话人分离未实测 |
| Word 字体 | 共同组与纪要组阳性/阴性探针通过，不代替业务文档逐页验收 |
| 其他客户端 | Claude Code项目目录安装通过，模型调用未实测；其他客户端未实测 |

历史原始输出保存在固定提交 `0a15cc20451414f1506d4f7fe4e8bba8939af875`，Git 历史未重写；2026-10-05 已从当前目录移出621份历史日志和迁移记录。

- [全部历史输出](https://github.com/Icdafy/Skills/tree/0a15cc20451414f1506d4f7fe4e8bba8939af875/docs/validation)
- [回归、安装与最后复查](https://github.com/Icdafy/Skills/blob/0a15cc20451414f1506d4f7fe4e8bba8939af875/docs/validation/final-review-20261005/README.md)
- [21个 Codex 会话摘要](https://github.com/Icdafy/Skills/blob/0a15cc20451414f1506d4f7fe4e8bba8939af875/docs/validation/clients/codex/summary.json)
- [历史字体测试契约](https://github.com/Icdafy/Skills/blob/0a15cc20451414f1506d4f7fe4e8bba8939af875/docs/font-test-contract.md)

## 字体与许可

[source-fonts.json](source-fonts.json) 保留18份源码字体的原路径、大小和摘要，仍是当前校验依据。仅索引 font_policy 列出的原文件可保留，禁止新增、改名或替换；单技能 ZIP 和安装器始终排除字体。GitHub整库源码下载仍含原字体，其公开再分发授权未确认，保留文件不等于取得授权。

用户自行准备有使用权的原版式字体，可设置 `ICDAFY_FONT_DIR` 指向仓库外目录。不凭 fsType 或上传作者判断公开再分发许可。缺字体须明确提示，未完成实际渲染和页数核验的 DOCX 仍是草稿。许可与来源见根 [第三方清单](../THIRD_PARTY_NOTICES.md)、[LICENSE](../LICENSE) 和 [NOTICE](../NOTICE)；README、LICENSE、NOTICE、VERSION、CHANGELOG 必须随包分发。旧历史和旧发布保留，不重写或删除。
