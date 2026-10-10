# Icdafy/Skills · 投资与公文技能库

按用途选择技能，下载完整目录并安装，再在客户端点名调用。当前共七项：立项报告三个章节、公文与会议三项、投后管理一项。

## 找技能

技能集合、路径和版本以 [skills-index.json](skills-index.json) 为准；下表由它生成。

<!-- skills:begin -->
### 立项报告

| 技能 / 做什么 | 源码 | 说明与调用 | 下载 | 版本 |
|---|---|---|---|---|
| 所属行业分析（`hangye-fenxi`） | [源码](hangye-fenxi/) | [README](hangye-fenxi/README.md) | [ZIP](https://github.com/Icdafy/Skills/releases/download/hangye-fenxi%2Fv1.0.2/hangye-fenxi.zip) | 1.0.2 |
| 主营业务分析（`zhuying-yewu-fenxi`） | [源码](zhuying-yewu-fenxi/) | [README](zhuying-yewu-fenxi/README.md) | [ZIP](https://github.com/Icdafy/Skills/releases/download/zhuying-yewu-fenxi%2Fv1.0.2/zhuying-yewu-fenxi.zip) | 1.0.2 |
| 公司情况（`gongsi-qingkuang`） | [源码](gongsi-qingkuang/) | [README](gongsi-qingkuang/README.md) | [ZIP](https://github.com/Icdafy/Skills/releases/download/gongsi-qingkuang%2Fv2.0.3/gongsi-qingkuang.zip) | 2.0.3 |

### 公文与会议

| 技能 / 做什么 | 源码 | 说明与调用 | 下载 | 版本 |
|---|---|---|---|---|
| 国企公文写作与排版（`officialese-skill`） | [源码](officialese-skill/) | [README](officialese-skill/README.md) | [ZIP](https://github.com/Icdafy/Skills/releases/download/officialese-skill%2Fv1.0.2/officialese-skill.zip) | 1.0.2 |
| 投委会议题（`yiti-skill`） | [源码](yiti-skill/) | [README](yiti-skill/README.md) | [ZIP](https://github.com/Icdafy/Skills/releases/download/yiti-skill%2Fv1.0.2/yiti-skill.zip) | 1.0.2 |
| 会议转录与正式纪要（`meeting-minutes-pro`） | [源码](meeting-minutes-pro/) | [README](meeting-minutes-pro/README.md) | [ZIP](https://github.com/Icdafy/Skills/releases/download/meeting-minutes-pro%2Fv1.0.3/meeting-minutes-pro.zip) | 1.0.3 |

### 投后管理

| 技能 / 做什么 | 源码 | 说明与调用 | 下载 | 版本 |
|---|---|---|---|---|
| 国企股权投资投后报告（`soe-post-investment-report`） | [源码](soe-post-investment-report/) | [README](soe-post-investment-report/README.md) | [ZIP](https://github.com/Icdafy/Skills/releases/download/soe-post-investment-report%2Fv1.5.6/soe-post-investment-report.zip) | 1.5.6 |
<!-- skills:end -->

## 安装与调用

从上表下载对应版本的 Release ZIP，解压得到 `<英文名>/SKILL.md`，按技能 README 准备依赖。保留完整目录，不只复制 SKILL.md；整库 Download ZIP 不能当作单技能包上传。

Python 3.10+；依赖、Word 字体和会议纪要的 ASR 环境按对应技能 README 准备。安装包不含字体或模型，字体由使用者自行准备。目录安装、Claude Code 市场安装、Codex 源码安装及旧版备份更新见 [安装与更新](docs/maintenance.md#安装与更新)，字体授权范围见 [字体与许可](docs/maintenance.md#字体与许可)。

安装后新建会话。Codex 输入 `$gongsi-qingkuang 帮我整理这份尽调资料的公司情况`；Claude Code 输入 `/gongsi-qingkuang 帮我整理这份尽调资料的公司情况`。也可直接说“帮我写立项报告的公司情况”。

每项技能 README 写明用途边界、所需材料、输入输出和完整调用例子。

## 怎么升级

默认按技能独立升级：点名哪个技能就只升级哪个，点名多个就只升级指定集合。只有明确要求“所有技能”或“全库升级”，才升级全部技能。目标技能独立维护源码、版本、变更记录和 Release；共享文件的改动不自动扩散。

只在仓库根目录修改目标技能源码，索引和首页登记目标变更；单技能任务不运行全库 `--sync`。构建产物放 `work/releases/<英文名>/<版本>/`，通过 GitHub Releases 分别发布，不提交 ZIP。版本、共享关系、构建命令和发布流程见 [维护说明](docs/maintenance.md#按技能独立维护)。

## 目录做什么

| 目录/文件 | 用途 |
|---|---|
| 根目录七个技能 | 每个技能的一份独立源码、规则、资源和使用说明 |
| [tools/](tools/) | 仓库目录生成、打包、校验和测试 |
| [docs/](docs/) | 一份安装维护指南及原字体校验清单 |
| [.claude-plugin/](.claude-plugin/) | Claude Code 市场索引，指向七个根目录技能 |
| [.gitignore](.gitignore) | 排除临时输出、缓存、私有词库及新增本机字体 |
| [AGENTS.md](AGENTS.md) | 按技能独立升级的仓库维护规则 |
| [skills-index.json](skills-index.json) | 技能路径、版本、Release 和共享关系的唯一清单 |
| [LICENSE](LICENSE) | 完整的 Apache-2.0 授权文本 |
| [NOTICE](NOTICE) | 署名、授权范围及第三方例外的简短声明 |
| [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) | 素材来源、文件摘要、字体限制与依赖许可明细 |

安装包在 [GitHub Releases](https://github.com/Icdafy/Skills/releases)；临时材料、构建和测试输出放 `work/`，不提交。

## 验证状态

校验命令、历史实测结果及其适用范围集中记录在 [维护指南](docs/maintenance.md#测试与验证范围)，分别说明脚本检查、客户端调用、ASR 和 Word 渲染的验证程度。
