# Google Antigravity 调用与执行

用户级将完整目录安装为 `~/.gemini/config/skills/officialese-skill/`，项目级使用 `.agents/skills/officialese-skill/`。安装器支持 `scripts/skill_portability.py install --agent antigravity --apply`，项目级另传 `--scope project --project-dir <绝对路径>`。从 Antigravity App 的 Customizations → Installed 检查实际来源。项目存在同名技能时，核对当前项目选中的路径。[技能文档](https://antigravity.google/docs/skills) [查找顺序](https://antigravity.google/docs/customization-discovery)

在 App 中使用 `/officialese-skill 起草项目资料归档通知，主送各部门，时间和落款使用我给出的信息。`，也支持自然语言匹配。需要本机文件或 Word 时使用本地项目会话，有文件时先打开或挂载对应的任务目录。

1. 以此次加载的 `SKILL.md` 所在目录定位 `references/`、`assets/` 和 `scripts/`。按当前任务读原规范和对应模板。先按文种读取写作规范、同类范文和适用的版式规则。需要 Word 时用 `create_official_docx.py`，核对主送、时间、数量、落款及附件与用户材料一致。
2. Windows 用终端可用的 Python 3.10+ 先执行 `-X utf8 --version` 并验证该技能依赖。PowerShell 使用调用运算符 `&` 加引号包住解释器和全部路径。脚本和输入输出都使用绝对路径，规格文件用 UTF-8，产物写入任务目录。项目阶段、模板或运行参数从当前任务和技能中取得。
3. 依据材料回读最终正文与 DOCX，核对专名、数字、单位、期间、限定词以及附件引用。需要版式验收时使用已安装的字体和 Word 或 LibreOffice 实际渲染。只根据实测结果确认检查状态。
