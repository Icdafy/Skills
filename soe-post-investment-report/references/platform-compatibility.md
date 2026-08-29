# 平台兼容性与中文显示名称

可移植技能标识固定为 `soe-post-investment-report`。文件夹名和 `SKILL.md` 的 `name` 字段均须保持小写 ASCII 和连字符形式。多个 Agent Skills 客户端会严格校验该字段，改成中文将导致部分平台无法导入。

面向用户的显示名称始终为 `国企股权投资投后报告`。本技能同时在 `metadata.display_name` 和 `agents/openai.yaml` 中声明该名称。凡平台导入、市场、API 或设置界面提供独立显示标题字段，均使用这一中文名称。

技能说明、默认提示、参考规则、用户交互和报告输出均采用中文；英文标识只为跨平台包格式兼容，不代表技能内容语言。

运行要求同时写入技能正文和 `metadata.compatibility`。为兼容只接受通用核心 frontmatter 字段的严格校验器，本包不另设顶层 `compatibility` 扩展。只识别该可选扩展的平台可能忽略机器可读运行说明，此时以 README 和技能正文为准。

| 客户端 | 安装／导入方式 | 中文名称表现 | 注意事项 |
| --- | --- | --- | --- |
| Codex／OpenAI | 安装到配置的技能目录，或通过受支持界面上传目录／ZIP；`scripts/install_skill.py --target codex` 使用通用用户级目录 | 支持时由 `agents/openai.yaml` 和 `metadata.display_name` 显示中文名称 | 功能可用性和上传入口随账号及版本而异 |
| Claude | 安装到 Claude 技能目录，或通过 Skills API 上传 ZIP；安装脚本支持 `--target claude` | 使用 API 时把 `display_title` 设为 `国企股权投资投后报告`；忽略显示元数据的本地客户端可能显示英文标识 | ZIP 须保留顶层技能文件夹 |
| Qoder | 安装到 Qoder 技能目录；安装脚本支持 `--target qoder` | Qoder 的必填 `name` 要求小写 ASCII；不识别可选显示元数据时会显示 `soe-post-investment-report` | 不得把标准标识改成中文 |
| Trae IDE／CLI | 使用项目级技能目录；安装脚本支持 `--target trae` 和 `--target trae-cli`，并要求 `--project` | 平台提供显示名称字段时手工设置中文，否则可能显示英文标识 | 按所安装版本核对当前项目级目录 |
| WorkBuddy／CodeBuddy | 使用项目技能目录；安装脚本支持 `--target workbuddy --project ...` | 导入或市场界面支持时设置中文名称；忽略元数据时可能显示英文标识 | 不同版本的产品命名和本地目录约定可能不同 |
| 其他 Agent Skills 客户端 | 复制完整目录或上传可移植 ZIP | 优先把显示标题设为 `国企股权投资投后报告`；只显示必填 `name` 的客户端会显示英文标识 | 正式使用前验证触发行为、相对资源、Python 依赖和渲染能力 |

相关规范与平台资料：

- [Agent Skills 规范](https://github.com/agentskills/agentskills/blob/main/docs/specification.mdx)
- [OpenAI Skills API 创建方法](https://developers.openai.com/api/reference/python/resources/skills/methods/create)
- [Claude Agent Skills](https://platform.claude.com/docs/en/managed-agents/skills) 与 [Claude Skills 创建 API](https://platform.claude.com/docs/en/api/beta/skills/create)
- [Qoder Skills](https://docs.qoder.com/zh/cli/Skills)
- [Trae Skills](https://docs.trae.cn/work_skills)、[Trae CLI Skills](https://docs.trae.cn/cli_skills) 与 [Trae IDE Skills](https://docs.trae.cn/ide_skills)
- [腾讯云 WorkBuddy skills](https://cloud.tencent.com/document/product/1831/134516)

## 认证边界

文件夹能够安装，不等于 DOCX 已完成版式和页数认证。客户端即使能够执行中文说明并生成结构正确的文件，也可能无法证明分页结果。最终交付仍要求使用 Windows Microsoft Word 或 LibreOffice 渲染、校验 PDF 页数、以独立 `附件1` 标签建立正文边界，并逐页检查图片。

缺少完整渲染闭环时，必须把输出标为“未认证草稿”。正式认证还必须核对：正文及问答使用 `w:firstLineChars=200` 字符单位首行空两字、固定 28 磅行距；西文字母和阿拉伯数字为 Times New Roman；页眉无内容；页码为四号宋体 `- 1 -` 形式，奇数页右侧、偶数页左侧。
