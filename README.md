# Icdafy/Skills · 投资与公文技能库

按用途选择一个技能，下载安装完整目录，再在客户端点名调用。当前共七项：立项报告三个章节、公文与会议三项、投后管理一项。会议纪要内含可选语音转写；仓库没有 PPT 技能或独立 sound-transcribe 技能。

## 找技能

技能集合、路径和版本以 [skills-index.json](skills-index.json) 为准；下表由它生成。

<!-- skills:begin -->
### 立项报告

| 技能 / 做什么 | 源码 | 说明与调用 | 下载 | 版本 |
|---|---|---|---|---|
| 所属行业分析（`hangye-fenxi`） | [源码](skills/hangye-fenxi/) | [README](skills/hangye-fenxi/README.md) | [ZIP](distributions/investment-report-skills/hangye-fenxi.zip) | 1.0.0 |
| 主营业务分析（`zhuying-yewu-fenxi`） | [源码](skills/zhuying-yewu-fenxi/) | [README](skills/zhuying-yewu-fenxi/README.md) | [ZIP](distributions/investment-report-skills/zhuying-yewu-fenxi.zip) | 1.0.0 |
| 公司情况（`gongsi-qingkuang`） | [源码](skills/gongsi-qingkuang/) | [README](skills/gongsi-qingkuang/README.md) | [ZIP](distributions/investment-report-skills/gongsi-qingkuang.zip) | 2.0.1 |

### 公文与会议

| 技能 / 做什么 | 源码 | 说明与调用 | 下载 | 版本 |
|---|---|---|---|---|
| 国企公文写作与排版（`officialese-skill`） | [源码](skills/officialese-skill/) | [README](skills/officialese-skill/README.md) | [ZIP](distributions/office-skills/officialese-skill.zip) | 1.0.0 |
| 投委会议题（`yiti-skill`） | [源码](skills/yiti-skill/) | [README](skills/yiti-skill/README.md) | [ZIP](distributions/office-skills/yiti-skill.zip) | 1.0.0 |
| 会议转录与正式纪要（`meeting-minutes-pro`） | [源码](skills/meeting-minutes-pro/) | [README](skills/meeting-minutes-pro/README.md) | [ZIP](distributions/office-skills/meeting-minutes-pro.zip) | 1.0.0 |

### 投后管理

| 技能 / 做什么 | 源码 | 说明与调用 | 下载 | 版本 |
|---|---|---|---|---|
| 国企股权投资投后报告（`soe-post-investment-report`） | [源码](skills/soe-post-investment-report/) | [README](skills/soe-post-investment-report/README.md) | [ZIP](distributions/office-skills/soe-post-investment-report.zip) | 1.5.3 |
<!-- skills:end -->

## 怎么装

推荐只安装所需技能，先用项目目录试用。Python 3.10+；Word 生成需各技能依赖。本库不附带商用/系统字体，请自行准备授权字体；检测、嵌入和缺字体提示见技能 README。

从上表下载单技能 ZIP，解压得到 `<英文名>/SKILL.md`。整库 Download ZIP 不能直接当单技能包上传。以下是完整公司情况安装例子，在仓库根运行（路径换成你的项目）：

```powershell
git clone https://github.com/Icdafy/Skills.git
cd Skills
python -m pip install -r skills/gongsi-qingkuang/requirements.txt
python skills/gongsi-qingkuang/scripts/skill_portability.py check --smoke
python skills/gongsi-qingkuang/scripts/skill_portability.py install --agent codex --scope project --project-dir "C:/项目/示例 项目"
python skills/gongsi-qingkuang/scripts/skill_portability.py install --agent codex --scope project --project-dir "C:/项目/示例 项目" --apply
```

Codex 使用项目 `.agents/skills/`；Claude Code 把 `--agent codex` 换成 `--agent claude-code`，使用 `.claude/skills/`。目录安装器默认只预览，`--apply` 才写入；新会话前核对实际加载路径和同名旧安装。用户级安装去掉项目参数即可，但不要自动覆盖所有已安装技能。

Claude Code 也可用插件市场：`/plugin marketplace add Icdafy/Skills`，再 `/plugin install gongsi-qingkuang@icdafy-skills`。Codex 可运行 `$skill-installer install https://github.com/Icdafy/Skills/tree/main/skills/gongsi-qingkuang`。本 PR 合并前，main 中的新源码地址尚未生效，请直接用当前分支目录验证。

其他客户端的目录/ZIP 入口保留在各技能 `references/agent-compatibility.md`，均注明验证程度。没有实际客户端调用记录时，不用脚本通过代替“已验证”。

## 怎么用

安装后新建会话。Codex 输入 `$gongsi-qingkuang 帮我整理这份尽调资料的公司情况`；Claude Code 输入 `/gongsi-qingkuang 帮我整理这份尽调资料的公司情况`。自然语言例子：“帮我写立项报告的公司情况”。首轮会询问早前期或中后期，回答后才按原固定模板起草。

行业分析和主营业务分析分别使用 `$hangye-fenxi`、`$zhuying-yewu-fenxi`；投后报告先提出四项变更确认；会议纪要先补会议信息。每项技能 README 都写明用途边界、输入输出、依赖和完整调用例子。

## 怎么升级

维护者只改 `skills/<英文名>/` 中的源码；共享文件改索引指定基准后同步。只升级投委会议题的例子：

```powershell
python tools/check_shared_scripts.py --sync
python tools/package_skills.py --skill yiti-skill
python tools/package_skills.py --check
```

详细顺序、版本修改、受影响包计算及验证见 [维护说明](docs/maintenance.md)。用户更新安装时见 [安装与旧路径迁移](docs/installation.md)，已有目录先备份，私有术语保留；ZIP 与源码版本分别在 `VERSION`、`CHANGELOG.md` 和 manifest 里核对。

## 目录做什么

| 顶层目录/文件 | 用途 |
|---|---|
| [skills/](skills/) | 七项技能的唯一源码；每项可单独复制、安装和运行 |
| [distributions/](distributions/) | 保留的两类下载目录，七个单技能 ZIP 和 SHA-256 |
| [tools/](tools/) | 仓库维护、同步、打包和测试；不当作技能安装 |
| [docs/](docs/) | 安装迁移、维护、来源、验证证据及全部原文件映射 |
| [.claude-plugin/](.claude-plugin/) | Claude Code 市场索引，路径指向 skills/ |
| [skills-index.json](skills-index.json) | 技能集合、路径、版本和共享副本的唯一清单 |
| [PROGRESS.md](PROGRESS.md)、[BLOCKED.md](BLOCKED.md) | 执行断点与未达条件 |
| [LICENSE](LICENSE)、[NOTICE](NOTICE)、[第三方清单](THIRD_PARTY_NOTICES.md) | Apache-2.0 授权范围、原署名及来源；字体不随库公开分发 |

本地 `.git/` 是 Git 元数据，不属于下载技能。临时材料放 `work/`，不提交。根目录空白占位物已删除；旧顶层技能目录均迁入 skills/，不保留第二套源码。

## 验证状态

Windows / Python 3.12.14：原375项完整发现，374通过、1项既有Windows符号链接环境跳过；七个独立ZIP仓库外烟测、项目安装备份、11组共享副本和第1轮完整校验通过。第三方授权待决项0，当前源码和ZIP不分发受限字体。

Codex CLI 0.160.0：21个新会话实际加载路径与路由均正确，严格首轮行为18/21。投后报告三例都有额外进度或依据说明，**“首轮只四问”尚未通过**。会议纪要文本与两个真实ASR引擎短合成语音已实测；真实长会/方言未实测。Claude Code当前不可运行，其他客户端未实测。

具体命令、原输出、红→绿、验证边界及最后人工浏览状态见 [验证记录](docs/validation.md)；未达条件见 [BLOCKED.md](BLOCKED.md)。主分支首页和新安装路径需本PR合并后生效。
