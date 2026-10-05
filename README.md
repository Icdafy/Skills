# Icdafy/Skills · 投资与公文技能库

按用途选择一个技能，下载安装完整目录，再在客户端点名调用。当前共七项：立项报告三个章节、公文与会议三项、投后管理一项。会议纪要内含可选语音转写；仓库没有 PPT 技能或独立 sound-transcribe 技能。

## 找技能

技能集合、路径和版本以 [skills-index.json](skills-index.json) 为准；下表由它生成。

<!-- skills:begin -->
### 立项报告

| 技能 / 做什么 | 源码 | 说明与调用 | 下载 | 版本 |
|---|---|---|---|---|
| 所属行业分析（`hangye-fenxi`） | [源码](hangye-fenxi/) | [README](hangye-fenxi/README.md) | [ZIP](distributions/investment-report-skills/hangye-fenxi.zip) | 1.0.1 |
| 主营业务分析（`zhuying-yewu-fenxi`） | [源码](zhuying-yewu-fenxi/) | [README](zhuying-yewu-fenxi/README.md) | [ZIP](distributions/investment-report-skills/zhuying-yewu-fenxi.zip) | 1.0.1 |
| 公司情况（`gongsi-qingkuang`） | [源码](gongsi-qingkuang/) | [README](gongsi-qingkuang/README.md) | [ZIP](distributions/investment-report-skills/gongsi-qingkuang.zip) | 2.0.2 |

### 公文与会议

| 技能 / 做什么 | 源码 | 说明与调用 | 下载 | 版本 |
|---|---|---|---|---|
| 国企公文写作与排版（`officialese-skill`） | [源码](officialese-skill/) | [README](officialese-skill/README.md) | [ZIP](distributions/office-skills/officialese-skill.zip) | 1.0.1 |
| 投委会议题（`yiti-skill`） | [源码](yiti-skill/) | [README](yiti-skill/README.md) | [ZIP](distributions/office-skills/yiti-skill.zip) | 1.0.1 |
| 会议转录与正式纪要（`meeting-minutes-pro`） | [源码](meeting-minutes-pro/) | [README](meeting-minutes-pro/README.md) | [ZIP](distributions/office-skills/meeting-minutes-pro.zip) | 1.0.1 |

### 投后管理

| 技能 / 做什么 | 源码 | 说明与调用 | 下载 | 版本 |
|---|---|---|---|---|
| 国企股权投资投后报告（`soe-post-investment-report`） | [源码](soe-post-investment-report/) | [README](soe-post-investment-report/README.md) | [ZIP](distributions/office-skills/soe-post-investment-report.zip) | 1.5.4 |
<!-- skills:end -->

## 怎么装

推荐只安装所需技能，先用项目目录试用。Python 3.10+；Word 生成需各技能依赖。单技能ZIP和安装器输出不含字体。源码按维护者要求保留原main六技能各三份字体，共18份，路径和字节不变；字体公开再分发授权仍未确认。使用时请自行准备授权字体；检测、嵌入和缺字体提示见技能 README。

从上表下载单技能 ZIP，解压得到 `<英文名>/SKILL.md`。整库 Download ZIP 不能直接当单技能包上传。以下是完整公司情况安装例子，在仓库根运行（路径换成你的项目）：

```powershell
git clone https://github.com/Icdafy/Skills.git
cd Skills
python -m pip install -r gongsi-qingkuang/requirements.txt
python gongsi-qingkuang/scripts/skill_portability.py check --smoke
python gongsi-qingkuang/scripts/skill_portability.py install --agent codex --scope project --project-dir "C:/项目/示例 项目"
python gongsi-qingkuang/scripts/skill_portability.py install --agent codex --scope project --project-dir "C:/项目/示例 项目" --apply
```

Codex 使用项目 `.agents/skills/`；Claude Code 把 `--agent codex` 换成 `--agent claude-code`，使用 `.claude/skills/`。目录安装器默认只预览，`--apply` 才写入；新会话前核对实际加载路径和同名旧安装。用户级安装去掉项目参数即可，但不要自动覆盖所有已安装技能。

Claude Code 也可用插件市场：`/plugin marketplace add Icdafy/Skills`，再 `/plugin install gongsi-qingkuang@icdafy-skills`。Codex 可运行 `$skill-installer install https://github.com/Icdafy/Skills/tree/main/gongsi-qingkuang`。源码地址沿用根目录路径；统一从main安装，按各技能README核对版本和依赖。

其他客户端的目录/ZIP 入口保留在各技能 `references/agent-compatibility.md`，均注明验证程度。没有实际客户端调用记录时，不用脚本通过代替“已验证”。

## 怎么用

安装后新建会话。Codex 输入 `$gongsi-qingkuang 帮我整理这份尽调资料的公司情况`；Claude Code 输入 `/gongsi-qingkuang 帮我整理这份尽调资料的公司情况`。自然语言例子：“帮我写立项报告的公司情况”。首轮会询问早前期或中后期，回答后才按原固定模板起草。

行业分析和主营业务分析分别使用 `$hangye-fenxi`、`$zhuying-yewu-fenxi`；投后报告先提出四项变更确认；会议纪要先补会议信息。每项技能 README 都写明用途边界、输入输出、依赖和完整调用例子。

## 怎么升级

维护者只改仓库根目录 `<英文名>/` 中的源码；共享文件改索引指定基准后同步。只升级投委会议题的例子：

```powershell
python tools/check_shared_scripts.py --sync
python tools/package_skills.py --skill yiti-skill
python tools/package_skills.py --check
```

详细顺序、版本修改、受影响包计算及验证见 [维护说明](docs/maintenance.md)。用户更新安装时见 [安装与旧版更新](docs/installation.md)，已有目录先备份，私有术语保留；ZIP 与源码版本分别在 `VERSION`、`CHANGELOG.md` 和 manifest 里核对。

## 目录做什么

| 顶层目录/文件 | 用途 |
|---|---|
| [hangye-fenxi/](hangye-fenxi/) | 所属行业分析的独立源码、规则和配套资源 |
| [zhuying-yewu-fenxi/](zhuying-yewu-fenxi/) | 主营业务分析的独立源码、规则和配套资源 |
| [gongsi-qingkuang/](gongsi-qingkuang/) | 公司情况的独立源码、规则和配套资源 |
| [officialese-skill/](officialese-skill/) | 国企公文写作与排版的独立源码、规则和配套资源 |
| [yiti-skill/](yiti-skill/) | 投委会议题的独立源码、规则和配套资源 |
| [meeting-minutes-pro/](meeting-minutes-pro/) | 会议转录与正式纪要的独立源码、规则和配套资源 |
| [soe-post-investment-report/](soe-post-investment-report/) | 国企股权投资投后报告的独立源码、规则和配套资源 |
| [distributions/](distributions/) | 保留的两类下载目录，七个单技能 ZIP 和 SHA-256 |
| [tools/](tools/) | 仓库维护、同步、打包和测试；不当作技能安装 |
| [docs/](docs/) | 安装迁移、维护、来源、验证证据及全部原文件映射 |
| [.claude-plugin/](.claude-plugin/) | Claude Code 市场索引，直接指向七个根目录技能 |
| [skills-index.json](skills-index.json) | 技能集合、路径、版本和共享副本的唯一清单 |
| [PROGRESS.md](PROGRESS.md)、[BLOCKED.md](BLOCKED.md) | 执行断点与未达条件 |
| [LICENSE](LICENSE)、[NOTICE](NOTICE)、[第三方清单](THIRD_PARTY_NOTICES.md) | Apache-2.0 授权范围、原署名及来源；原18份源码字体保留，字体授权待决；单技能ZIP排除字体 |

本地 `.git/` 是 Git 元数据，不属于下载技能。临时材料放 `work/`，不提交。七个技能目录直接列在仓库根目录，每项只有一份源码。根目录空白占位物已删除，临时材料不进入分发。

## 验证状态

Windows / Python 3.12.14：原375项完整发现，374通过、1项既有Windows符号链接环境跳过；七个独立ZIP仓库外烟测、项目安装备份、11组共享副本和第3轮完整校验通过（已达到3轮上限）。这些是合并前去字体方案的历史结果。最新保留原main18份源码字体，单技能ZIP继续排除字体；字体授权待决，见[选择性合并记录](docs/validation/selective-merge/README.md)。

Codex CLI 0.160.0：21个新会话实际加载路径与路由均正确，严格首轮行为18/21。投后报告三例都有额外进度或依据说明，**“首轮只四问”尚未通过**。会议纪要文本与两个真实ASR引擎短合成语音已实测；真实长会/方言未实测。Claude Code当前不可运行，其他客户端未实测。

具体命令、原输出、红→绿、验证边界及最后人工浏览状态见 [验证记录](docs/validation.md)；未达条件见 [BLOCKED.md](BLOCKED.md)。PR #12其余内容及原18份字体保留方案已合并到main，仓库仅保留main分支；七个源码目录沿用原地址。
