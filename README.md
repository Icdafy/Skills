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

## 怎么装

从上表下载对应版本的 Release ZIP，解压得到 `<英文名>/SKILL.md`，按技能 README 准备依赖。保留完整目录，不只复制 SKILL.md；整库 Download ZIP 不能当作单技能包上传。

Python 3.10+；Word 生成需各技能依赖。单技能 ZIP 和安装器不含字体，使用时自行准备有授权的原版式字体。整库源码仍保留原18份历史字体，其公开再分发授权未确认，详见 [字体与许可](docs/maintenance.md#字体与许可)。

目录安装器默认只预览，`--apply` 才写入。以公司情况项目安装为例，在解压出的 `gongsi-qingkuang` 目录运行：

```powershell
python -m pip install -r requirements.txt
python scripts/skill_portability.py check --smoke
python scripts/skill_portability.py install --agent codex --scope project --project-dir "C:/项目/示例 项目"
python scripts/skill_portability.py install --agent codex --scope project --project-dir "C:/项目/示例 项目" --apply
```

Claude Code 将 `--agent codex` 换为 `--agent claude-code`；也可通过 `/plugin marketplace add Icdafy/Skills`、`/plugin install gongsi-qingkuang@icdafy-skills` 安装。Codex 可运行 `$skill-installer install https://github.com/Icdafy/Skills/tree/main/gongsi-qingkuang`。项目路径、其他客户端及旧版备份更新见 [安装与更新](docs/maintenance.md#安装与更新)。

## 怎么用

安装后新建会话。Codex 输入 `$gongsi-qingkuang 帮我整理这份尽调资料的公司情况`；Claude Code 输入 `/gongsi-qingkuang 帮我整理这份尽调资料的公司情况`。也可直接说“帮我写立项报告的公司情况”。

立项报告三技能先询问早前期或中后期；投后报告先提出四项变更确认；会议纪要先补会议信息。每项技能 README 写明用途边界、输入输出、依赖和完整调用例子。

## 怎么升级

默认按技能独立升级：点名哪个技能就只升级哪个，点名多个就只升级指定集合。只有明确要求“所有技能”或“全库升级”，才升级全部技能。目标技能独立维护源码、版本、变更记录和 Release；共享文件的改动不自动扩散。

只在仓库根目录修改目标技能源码，索引和首页登记目标变更；单技能任务不运行全库 `--sync`。只构建投委会议题的例子：

```powershell
python tools/sync_catalog.py
python tools/check_shared_scripts.py
python tools/package_skills.py --skill yiti-skill
# 将构建摘要登记到索引的 release.sha256 后，只校验目标包
python tools/package_skills.py --check --skill yiti-skill
```

构建产物放 `work/releases/<英文名>/<版本>/`，通过 GitHub Releases 分别发布，不再提交 ZIP。版本、共享关系、测试和发布流程见 [维护说明](docs/maintenance.md#按技能独立维护)。

## 目录做什么

| 目录/文件 | 用途 |
|---|---|
| 根目录七个技能 | 每个技能的一份独立源码、规则、资源和使用说明 |
| [tools/](tools/) | 仓库目录生成、打包、校验和测试 |
| [docs/](docs/) | 一份安装维护指南及原字体校验清单 |
| [.claude-plugin/](.claude-plugin/) | Claude Code 市场索引，指向七个根目录技能 |
| [skills-index.json](skills-index.json) | 技能路径、版本、Release 和共享关系的唯一清单 |
| [LICENSE](LICENSE)、[NOTICE](NOTICE)、[第三方清单](THIRD_PARTY_NOTICES.md) | 授权范围、署名、来源与字体限制 |

安装包在 [GitHub Releases](https://github.com/Icdafy/Skills/releases)；临时材料、构建和测试输出放 `work/`，不提交。

## 验证状态

当前校验入口与历史结果见 [维护指南](docs/maintenance.md#测试与验证范围)。历史 Codex CLI 0.160.0 路由21/21、严格首轮行为18/21；会议纪要文本和两个真实 ASR 引擎的短合成语音已实测。真实长会、方言、Claude Code模型调用及其他客户端未实测，脚本检查不能代替这些验证。
