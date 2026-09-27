# 平台兼容性与中文显示名称

可移植技能标识固定为 `soe-post-investment-report`。文件夹名和 `SKILL.md` 的 `name` 字段均须保持小写 ASCII 和连字符形式。多个 Agent Skills 客户端会严格校验该字段，改成中文将导致部分平台无法导入。

面向用户的显示名称始终为 `国企股权投资投后报告`。本技能同时在 `metadata.display_name` 和 `agents/openai.yaml` 中声明该名称。凡平台导入、市场、API 或设置界面提供独立显示标题字段，均使用这一中文名称。

技能说明、默认提示、参考规则、用户交互和报告输出均采用中文；英文标识只为跨平台包格式兼容，不代表技能内容语言。

运行要求同时写入技能正文和 `metadata.compatibility`。为兼容只接受通用核心 frontmatter 字段的严格校验器，本包不另设顶层 `compatibility` 扩展。只识别该可选扩展的平台可能忽略机器可读运行说明，此时以 README 和技能正文为准。

各客户端（Claude、ChatGPT、Codex、Kimi、豆包、智谱 GLM、WorkBuddy、TRAE、Qoder）的安装入口、调用方式、运行环境适配与验收统一见 [agent-compatibility.md](agent-compatibility.md)，推荐使用 `scripts/skill_portability.py`（`agents` 列出目标，`install --agent <客户端> --apply` 安装，`package` 生成上传用 ZIP）。以下只列中文显示名称的表现：

| 客户端 | 中文名称表现 |
| --- | --- |
| Codex、ChatGPT 桌面版 | 读取 `agents/openai.yaml` 的 `display_name`，显示 `国企股权投资投后报告` |
| Claude 网页／桌面 Chat | 上传界面显示 `SKILL.md` 的 `name`；使用 Skills API 时把 `display_title` 设为 `国企股权投资投后报告` |
| Claude Code、Kimi Code、Qoder、TRAE、WorkBuddy、ZCode、AutoClaw | 多数只显示必填 `name`，即 `soe-post-investment-report`；导入界面提供显示名称字段时手工填写中文名 |
| 豆包电脑版、Kimi Work | 上传后以 `SKILL.md` 解析结果为准；可编辑名称时填写中文名，不改动 `name` 字段 |

`scripts/install_skill.py` 保留兼容：`--target codex` 现写入 `~/.agents/skills/`（新版 Codex 与 ChatGPT 桌面版读取的目录），`claude`、`qoder`、`trae`、`trae-cli`、`workbuddy` 与 `--zip` 行为不变。

相关规范与平台资料：

- [Agent Skills 规范](https://github.com/agentskills/agentskills/blob/main/docs/specification.mdx)
- [OpenAI Skills API 创建方法](https://developers.openai.com/api/reference/python/resources/skills/methods/create)
- [Claude Agent Skills](https://platform.claude.com/docs/en/managed-agents/skills) 与 [Claude Skills 创建 API](https://platform.claude.com/docs/en/api/beta/skills/create)

## 认证边界

文件夹能够安装，不等于 DOCX 已完成版式和页数认证。客户端即使能够执行中文说明并生成结构正确的文件，也可能无法证明分页结果。最终交付仍要求使用 Windows Microsoft Word 或 LibreOffice 渲染、校验 PDF 页数、以独立 `附件1` 标签建立正文边界，并逐页检查图片。

缺少完整渲染闭环时，必须把输出标为“未认证草稿”。正式认证还必须核对：正文及问答使用 `w:firstLineChars=200` 字符单位首行空两字、固定 28 磅行距；西文字母和阿拉伯数字为 Times New Roman；页眉无内容；页码为四号宋体 `-1-` 形式，奇数页右侧、偶数页左侧。
