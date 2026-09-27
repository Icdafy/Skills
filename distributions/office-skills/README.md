# 办公技能安装包

每个 ZIP 为一项完整技能，第一层只有技能目录，包含独立运行所需的 `SKILL.md`、参考文件、Python 脚本、依赖说明、`agents/openai.yaml`、原技能字体资源（投后报告不含字体）和 SHA-256 文件清单。用于现有授权范围内的跨客户端安装。

| 技能 | 安装包 | 完整性校验 | 分平台安装指引 |
|---|---|---|---|
| 国企公文格式 | [officialese-skill.zip](https://github.com/Icdafy/Skills/raw/refs/heads/main/distributions/office-skills/officialese-skill.zip) | [SHA-256](officialese-skill.zip.sha256) | [指引](../../officialese-skill/references/agent-compatibility.md) |
| 投委会议题 | [yiti-skill.zip](https://github.com/Icdafy/Skills/raw/refs/heads/main/distributions/office-skills/yiti-skill.zip) | [SHA-256](yiti-skill.zip.sha256) | [指引](../../yiti-skill/references/agent-compatibility.md) |
| 会议纪要专业版 | [meeting-minutes-pro.zip](https://github.com/Icdafy/Skills/raw/refs/heads/main/distributions/office-skills/meeting-minutes-pro.zip) | [SHA-256](meeting-minutes-pro.zip.sha256) | [指引](../../meeting-minutes-pro/references/agent-compatibility.md) |
| 国企股权投资投后报告 | [soe-post-investment-report.zip](https://github.com/Icdafy/Skills/raw/refs/heads/main/distributions/office-skills/soe-post-investment-report.zip) | [SHA-256](soe-post-investment-report.zip.sha256) | [指引](../../soe-post-investment-report/references/agent-compatibility.md) |

Claude 网页/桌面 Chat、ChatGPT 团队版、豆包电脑版（工作模式）、WorkBuddy、Kimi Work、Qoder 桌面版、TRAE、智谱 ZCode 走各自的“上传技能”入口导入 ZIP；Claude Code、Codex、ChatGPT 桌面版、Kimi Code、Qoder CLI、TRAE、WorkBuddy、CodeBuddy、ZCode、AutoClaw 等目录型客户端可解压后用随包 `scripts/skill_portability.py install`。Claude Code 也可直接 `/plugin marketplace add Icdafy/Skills` 后 `/plugin install <技能名>@icdafy-skills`；Codex 可用 `$skill-installer install https://github.com/Icdafy/Skills/tree/main/<技能名>`。

解压后在技能目录执行：

```bash
python scripts/skill_portability.py check
python -m pip install -r requirements.txt
python scripts/skill_portability.py check --smoke
python scripts/skill_portability.py agents
python scripts/skill_portability.py install --agent claude-code --agent codex --apply
```

需要 Python 3.10+。`meeting-minutes-pro` 的依赖为 `scripts/requirements-runtime.txt`，本地转录引擎由 `scripts/bootstrap_runtime.py` 在用户许可后另行安装；云端沙箱只能基于已有转录稿整理纪要。安装后还须在目标客户端确认启用、实际加载路径、自动路由与输出；包及脚本检查通过不等于所有客户端模型调用已经实测。说明依据各平台官方文档（2026-09-27）。

维护者更新任一技能后，在仓库根目录同步和重打包：

```bash
python tools/check_shared_scripts.py --sync
python tools/package_skills.py
python tools/package_skills.py --check
```

`--check` 对比包内清单、每个文件及 ZIP 本身的 SHA-256，发现漏文件、包损坏或源码与安装包不同步即失败。安装包以技能名为唯一顶层目录，不打入缓存、虚拟环境、Git 仓库、渲染预览或 `meeting-minutes-pro` 的项目术语表等用户数据。
