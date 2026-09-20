# 跨 Agent 安装与调用

适用于本套 `hangye-fenxi`、`zhuying-yewu-fenxi`、`gongsi-qingkuang`。官方文档核对日期：2026-09-20。支持标准 `SKILL.md` 的客户端共用相同内容及脚本，各产品按自己的技能入口安装和启用。本文中的 `SKILL_ROOT` 指本次实际加载的技能文件夹。

## 安装包与安装入口

从 [GitHub 分发目录](https://github.com/Icdafy/Skills/tree/main/distributions/investment-report-skills) 下载三个独立 ZIP 中需要的一个或多个（文件页选择 Download raw）。每个 ZIP 的第一层只有该技能目录，内部包括 `SKILL.md`、`references/`、`scripts/`、`requirements.txt`、字体资源和 SHA-256 文件清单（文本先统一LF换行，字体按原始二进制校验）。GitHub 整库的“Download ZIP”带 `Skills-main` 外层，须解压后选取单个完整技能目录重新打包，不能直接当单技能包上传；仅复制 `SKILL.md` 会遗漏参考文件和生成器。

| 客户端 | 安装与启用 | 显式调用与验收 | 官方依据 |
|---|---|---|---|
| WorkBuddy | 技能页面→添加技能→上传技能，导入完整本地技能包；在已安装页确认开关开启 | 消息写“使用 hangye-fenxi 技能……”；查看是否实际加载技能及参考文件 | [WorkBuddy 技能](https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market) |
| Kimi Work 桌面端 | Work 模式→技能，使用当前版本的上传本地技能入口，导入完整包；文件类型以界面支持为准，不能将普通附件上传等同安装 | 输入 `/` 从技能列表选取，或直接点名技能；核对脚本和资源可读 | [Kimi Work](https://www.kimi.com/help/kimi-work/overview) |
| Kimi Code CLI | 完整目录放 `$KIMI_CODE_HOME/skills/`，默认 `~/.kimi-code/skills/`；项目级 `.kimi-code/skills/`，也支持 `.agents/skills/` | `/skill:hangye-fenxi`；重开会话后确认列表。旧版本如使用不同目录，以该版本配置为准 | [Kimi Code Skills](https://www.kimi.com/code/docs/kimi-code-cli/customization/skills.html) |
| Kimi 在线 Agent | 技能面板的自定义技能入口按当期产品能力配置；官方页面介绍文档转技能及对话创建，未据此确认任意 ZIP 原样导入 | `/` 或“+”选择技能。若只保存了说明文字而没有本包参考文件、脚本，不能标记为完整适配；优先用 Kimi Work/Code | [Kimi Agent 技能](https://www.kimi.com/help/plugins-and-skills/use-skills-in-agent) |
| Claude 桌面版（Chat/支持 Skills 的 Cowork） | Customize→Skills→“+”→Create skill→Upload a skill，逐个上传 ZIP 并启用；需要账户/组织允许自定义技能及代码执行 | 自然语言点名“使用 gongsi-qingkuang 技能……”，查看技能加载与代码执行记录；桌面 Chat 的上传技能不通过 `~/.claude/skills` 安装 | [使用技能](https://support.claude.com/en/articles/12512180-use-skills-in-claude)、[创建与ZIP结构](https://support.claude.com/en/articles/12512198-how-to-create-custom-skills) |
| Claude Code（含桌面 Code 工作流） | 用户级 `~/.claude/skills/<name>/` 或项目级 `.claude/skills/<name>/`，与桌面 Chat 的上传入口区分 | 新会话点名技能；以该工作流实际技能列表为准 | [Claude Skills 概览](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) |
| Qoder 桌面版 | Extensions→Skills→Add Skills→Upload Skill，上传 ZIP；Installed 中确认 | 输入 `/` 选择对应技能，再运行小样 | [Qoder Skills](https://docs.qoder.com/qoder/skills) |
| Qoder CLI / QoderWork / Qoder CN | CLI：`~/.qoder/skills/` 或项目 `.qoder/skills/`；QoderWork：`~/.qoderwork/skills/`；Qoder CN IDE：`~/.lingma/skills/` 或项目 `.lingma/skills/`。按实际产品选一处 | CLI 可 `/hangye-fenxi`、`/skills reload`；QoderWork 直接点名；CN 按 `/` 列表选择 | [CLI](https://docs.qoder.com/cli/Skills)、[QoderWork](https://docs.qoder.com/qoderwork/skills)、[CN IDE](https://docs.qoder.cn/user-guide/skills) |
| TraeCode / TRAE IDE 中国版 | 设置→技能与命令→创建→全局/项目→导入 ZIP；完整目录项目路径 `.trae/skills/`，中国版全局 `~/.trae-cn/skills/` | 确认启用后直接点名技能。使用 `.agents/skills/` 时还须开启该目录的导入开关；同名 `.trae/skills` 版本优先 | [TRAE 技能](https://docs.trae.cn/ide_skills) |
| 其他地区/版本及 Agent | 优先使用其官方完整 ZIP 导入入口；路径安装先从设置或对应版本文档确认真实技能根目录，使用下方 `--skills-dir` | 不假定与中国版、CLI或同品牌桌面端共用路径；完成下方调用验收后再记录成功 | 目标客户端当期官方文档与设置 |

相同名称只保留一个实际启用版本，排查旧项目技能覆盖新全局技能的情况。不要将本技能转换成一个删减过的“文档转技能”副本，也不需要额外构建 MCP 服务。`agents/openai.yaml` 是 Codex 可选界面信息，其余平台的触发以 `SKILL.md` 的 `name`、`description` 为依据。

## 目录安装与更新命令

需要 Python 3.10 或以上。在已下载技能的根目录运行，`python` 可替换为本机可用的 `python3` 或 `py -3`；路径带空格时加引号。以下是**本技能自带安装器**的参数，不是各客户端的内置命令。

```bash
# 完整性检查；无需第三方依赖
python scripts/skill_portability.py check

# 先打印安装路径，检查后用 --apply 真正复制
python scripts/skill_portability.py install --agent kimi-code
python scripts/skill_portability.py install --agent kimi-code --apply

# 项目技能（project-dir 使用实际项目绝对路径）
python scripts/skill_portability.py install --agent trae-cn --scope project --project-dir "/path/to/project" --apply

# 目标客户端已确认的自定义技能目录
python scripts/skill_portability.py install --skills-dir "/path/to/skills" --apply

# 从源码重新打包；输出目录放在技能目录之外
python scripts/skill_portability.py package --output-dir "../skill-zips"
```

可选 `--agent`：`claude-code`、`kimi-code`、`qoder-cli`、`qoder-cn`、`qoderwork`、`trae-cn`、`agents`。WorkBuddy、Kimi Work、Claude Chat、Qoder桌面端优先走界面上传，不虚构它们的配置目录。安装器默认仅预览路径；覆盖已存在版本前复制到技能根目录之外的 `skill-backups/`，保留原文件。不删除额外的本地文件；发现额外文件会停止更新，先对照备份确定是否保留，避免混装。

## 运行环境与工具适配

1. **路径**：以已加载 `SKILL.md` 的绝对路径确定 `SKILL_ROOT`，`references/`、`scripts/`、`assets/` 均相对此目录解析。调用命令使用脚本和输入输出的绝对路径，或先进入技能目录；报告输出到用户任务目录。Kimi Code 可用 `${KIMI_SKILL_DIR}` 获取技能目录，其他平台用其技能加载结果，不原样传递不支持的变量。
2. **Python**：写作本身不要求 Python；生成 Word 需要 `python-docx`。在 Agent 实际执行环境中安装 `requirements.txt`，云端沙箱与本机 Python 是不同环境。不得引用作者电脑用户名、特定 Python 路径、Codex 私有工具或工作目录。
3. **工具名称**：正文中的 WebSearch/WebFetch 代表“检索权威网页/打开来源”的能力，映射到当前 Agent 的搜索、浏览器或网页工具；读取资料、执行 Python 同理使用可用工具。没有网络时保留来源边界，不声称检索已完成。没有文件或执行能力时可交付已完成的文本并明确 Word 排版未验证，不能宣称已生成合规 Word。
4. **文档读取**：可用平台的 PDF、表格、Word 读取器；名称不同不影响技能规则。Word资料也可运行随包 `scripts/extract_docx.py`（公司情况技能）。存在同类通用文档技能时，由其负责文件读取，当前技能负责报告逻辑及指定生成器。
5. **字体**：先运行 `ensure_fonts.py --check`；按宿主权限及现有授权安装。沙箱不能安装系统字体时保留 DOCX 中文字体槽，并用随包嵌入器处理允许嵌入的字体；最终打开文档的设备仍须具备实际未嵌入的字体。Times New Roman、黑体、宋体在非 Windows 环境不能假定存在。字体替换或缺失须在交付说明中如实说明，不声称已实现视觉一致。

```bash
python -m pip install -r requirements.txt
python scripts/ensure_fonts.py --check
python scripts/skill_portability.py check --smoke
```

`--smoke` 从不同工作目录调用本包 Word 生成器，检查表格字号、最终西文字体、奇偶页脚、完整页码字号及动态域。它不会安装字体、修改客户端配置或上传文档；通过只代表包结构及代码可执行。最终字体显示还需在目标 Word/渲染器上目视检查。

## 技能路由与真实调用验收

| 请求范围 | 应调用技能 | 不应代替的内容 |
|---|---|---|
| 所属行业、市场规模、增长动力、产业链价值及共性门槛 | `hangye-fenxi` | 公司工商、团队履历和详细产品订单分析 |
| 产品、技术优势、商业模式、客户订单、竞争比较及商业转化 | `zhuying-yewu-fenxi` | 纯宏观行业概述或公司工商汇总 |
| 主体、股权沿革、核心团队、权属、组织资源、融资与财务快照 | `gongsi-qingkuang` | 行业研究或完整主营业务章 |

安装后在目标客户端**新建会话**完成以下验收，并记录客户端名称/版本、实际技能路径、结果及日期。当前分发包不预先宣称各客户端已经实测。

1. **可发现**：技能列表出现原始英文 `name`，开关开启，无旧版本覆盖。直接说“使用 `<name>` 技能，只读取其规范，概括适用章节和3条排版规则”，观察实际技能加载记录。仅复述用户消息或模型声称“已调用”不算验收。
2. **自动选择**：分别输入“写一下某公司的所属行业与产业链分析”“根据资料写主营业务分析及技术壁垒”“根据工商资料与访谈写公司情况”。观察是否调用对应技能及所需参考文件。信息不足时应收集必要输入，不能编造报告。再输入“改一段普通通知”，这三个技能均不应被自动选中。
3. **运行完整**：在宿主执行环境运行上面的 `check --smoke`，确认 `references/investment-logic-review.md` 可读取、生成器能找到同目录的辅助模块与字体资源。无运行环境的平台不能记录为完整 Word 能力通过。
4. **输出一致**：用非敏感测试材料生成含表格、括注、`（1）`标题、分页的 Word，核对中文字体、TNR数字及百分号、表格全五号、奇偶页外侧页码和整段14pt；确认正文无拖延判断尾句，先完成阶段选择、按固定模板撰写，再执行逻辑复核修订正文；标题检查通过。

未触发时依次检查：产品与模式→启用开关→目录层级→同名覆盖→描述是否完整→参考文件可读→重载/新会话。显式点名后仍无加载记录时，按该客户端提供的技能管理方式排查；不要用“文件已经复制”替代调用成功。

## 两阶段模板调用验收

在每个宿主中使用非敏感虚构公司测试：只说“写行业分析／主营业务分析／公司情况”，不提供阶段时，首轮应询问早前期或中后期并等待；不能直接出正文。回复“早前期”应读取本技能 `early.json`，回复“中后期”应读取 `mid-late.json`。三个技能连续处理同一项目时复用用户答案；换公司重新问。核对标题来源、个案填空和重复组，运行 `stage_template.py check`。中文路径、带空格路径和宿主无Python时的人工核对均按 `stage-template-workflow.md` 执行。打包安装时必须包含两个JSON、两份原文对照、执行规则及 `stage_template.py`；只复制入口文件不算安装成功。
