# 跨 Agent 安装与调用

适用于此技能的完整目录。技能集合、中文分类、源码路径、下载和版本以 [仓库首页](https://github.com/Icdafy/Skills) 及 skills-index.json 为准。`SKILL_ROOT` 指本次实际加载的 SKILL.md 所在目录，`<name>` 为其 name。

## 一、获取完整技能包

在本技能 README 下载单技能 ZIP，解压第一层只有 `<name>/`。包含完整规则、脚本、资源、VERSION、LICENSE、NOTICE 和逐文件 manifest。整库 Download ZIP 不是单技能包，不能只复制 SKILL.md。公开包不含商用/系统字体或模型，使用本机授权字体。

## 验证程度

Codex 和 Claude Code 的目录与调用说明于 2026-10-05 核对官方文档；真实调用结果见 [验证记录](https://github.com/Icdafy/Skills/blob/main/docs/maintenance.md#历史实测范围)。其他客户端保留下列安装参考（原核对日 2026-09-27），本次均未实测，入口可能随版本变化，请以客户端实际界面为准。目录复制或脚本成功均不等于模型调用成功。

## 二、各客户端安装与调用

| 客户端 | 安装入口 | 调用方式 | 官方依据 |
|---|---|---|---|
| **Claude** 网页 / 桌面 Chat / Cowork | 自定义（Customize）→ 技能（Skills）→“+”→ 上传技能，逐个上传 ZIP 并开启；账户或组织须允许自定义技能与代码执行 | 自然语言点名“使用 `<name>` 技能……” | [使用技能](https://support.claude.com/en/articles/12512180-use-skills-in-claude)、[ZIP 要求](https://support.claude.com/en/articles/12512198-how-to-create-custom-skills) |
| **Claude Code**（CLI、桌面 Code、IDE） | 插件市场：`/plugin marketplace add Icdafy/Skills`，再 `/plugin install <name>@icdafy-skills`；或目录安装 `--agent claude-code`（`~/.claude/skills/`，项目级 `.claude/skills/`） | `/<name>`（插件方式安装时斜杠菜单带插件名前缀）或自然语言 | [Claude Code 技能](https://code.claude.com/docs/en/skills) |
| **ChatGPT** 桌面版 | 目录安装 `--agent chatgpt`（与 Codex 共用 `~/.agents/skills/`），侧栏“技能”中确认 | 输入 `@` 选择技能，或按描述自动匹配 | [Build skills](https://learn.chatgpt.com/docs/build-skills) |
| **ChatGPT** Business / Enterprise / Edu | 技能 → 创建 → 从电脑上传，选择 ZIP；等待安全扫描，标记“需审核”时按提示复核 | `@` 选择技能 | [Skills in ChatGPT](https://help.openai.com/en/articles/20001066-skills-in-chatgpt) |
| **Codex** CLI / IDE 扩展 | `--agent codex`（`~/.agents/skills/`，项目级 `.agents/skills/`）；或在 Codex 中运行 `$skill-installer install https://github.com/Icdafy/Skills/tree/main/<name>`。仍读取 `$CODEX_HOME/skills` 的旧版用 `--agent codex-legacy` | `$<name>` 或 `/skills` | [Build skills](https://learn.chatgpt.com/docs/build-skills) |
| **Kimi Work**（Kimi 电脑客户端 Work 模式） | 侧栏“技能”→ 上传本地技能，导入完整 ZIP | 输入框输入 `/` 选择技能，或直接点名 | [Kimi Work](https://www.kimi.com/help/kimi-work/overview) |
| **Kimi Code CLI** | `--agent kimi-code`（`$KIMI_CODE_HOME/skills/`，默认 `~/.kimi-code/skills/`；也读取 `~/.agents/skills/`） | `/skill:<name>` | [Kimi Code Skills](https://www.kimi.com/code/docs/kimi-code-cli/customization/skills.html) |
| **豆包** 电脑版（工作模式） | 左侧“插件·技能·伙伴”→“技能”→ 右上角“+ 添加”→“上传技能”，拖入 ZIP 或解压后的技能文件夹；在“我安装的”中确认 | “新工作任务”对话框输入 `/` 或 `@` 选择技能，或直接描述需求自动匹配 | [在豆包工作中使用技能](https://www.doubao.com/work/docs/zh-cn/articles/081010973544-skills) |
| **智谱 GLM**：ZCode | 设置 → Skills → 右上角导入（选“复制”）；或 `--agent zcode`（`~/.zcode/skills/`） | `$<name>` 或斜杠菜单 | [ZCode Skill](https://zcode.z.ai/en/docs/skill) |
| **智谱 GLM**：AutoClaw（澳龙，基于 OpenClaw） | `--agent openclaw`（`~/.openclaw/skills/`）或 `--agent agents`（`~/.agents/skills/`），重启后生效。界面“Plugins → Skills”导入限制单文件 1 MiB、总量 8 MiB，遇到体积限制时可用目录安装；本库不分发字体 | 斜杠命令 `/<name>` 或自然语言 | [OpenClaw Skills](https://docs.openclaw.ai/tools/skills) |
| **WorkBuddy** | 技能 → 添加技能 → 上传技能，导入 ZIP 并在已安装页开启；或 `--agent workbuddy`（`~/.workbuddy/skills/`，项目级 `.workbuddy/skills/`）。CodeBuddy 用 `--agent codebuddy` | 自然语言点名或在技能列表选择 | [WorkBuddy 技能](https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market) |
| **TRAE** / TraeCode | 设置 → 技能与命令 → 创建 → 全局或项目 → 导入 ZIP；中国版 `--agent trae-cn`（`~/.trae-cn/skills/`），国际版 `--agent trae`（`~/.trae/skills/`），项目级 `.trae/skills/` | 直接点名技能，或由 AI 自动加载。使用 `.agents/skills/` 须在“导入设置”开启，同名时 `.trae/skills/` 优先 | [TRAE 技能](https://docs.trae.cn/ide_skills) |
| **Qoder** 桌面版 | Extensions → Skills → Add Skills → Upload Skill，上传 ZIP，在 Installed 中确认 | 输入 `/` 选择技能 | [Qoder Skills](https://docs.qoder.com/qoder/skills) |
| **Qoder** CLI / QoderWork / Qoder CN | CLI `--agent qoder-cli`（`~/.qoder/skills/`）；QoderWork `--agent qoderwork`；Qoder CN IDE `--agent qoder-cn`（`~/.lingma/skills/`） | CLI `/<name>`，安装后 `/skills reload`；QoderWork 直接点名 | [CLI](https://docs.qoder.com/cli/Skills)、[QoderWork](https://docs.qoder.com/qoderwork/skills) |
| 其他 Agent Skills 客户端 | 优先官方 ZIP 导入入口；目录型客户端先在设置中确认真实技能根目录，再用 `--skills-dir` | 按该客户端规则 | 目标客户端当期官方文档 |

同一名称只保留一个启用版本，排查旧项目级技能覆盖新全局技能的情况。`agents/openai.yaml` 为 Codex、ChatGPT 提供中文显示名称和默认提示，其余平台以 `SKILL.md` 的 `name`、`description` 为准；描述已控制在 200 字符以内，满足 claude.ai 上传上限及 Kimi、Codex、ZCode 的长度要求。不要把技能转换成删减过的“文档转技能”副本，也不需要额外构建 MCP 服务。

## 三、随包安装器

各技能自带 `scripts/skill_portability.py`（Python 3.10+，仅标准库）。在技能根目录运行，`python` 可替换为 `python3` 或 `py -3`；路径带空格时加引号。以下是**本技能安装器**的参数，不是各客户端的内置命令。

```bash
# 列出支持的客户端、目录与界面上传入口
python scripts/skill_portability.py agents

# 完整性检查；--smoke 另需 python-docx，从独立工作目录生成并核验一份样例 Word
python scripts/skill_portability.py check
python scripts/skill_portability.py check --smoke

# 目录安装：默认只打印路径，加 --apply 才写入；--agent 可重复
python scripts/skill_portability.py install --agent claude-code --agent codex
python scripts/skill_portability.py install --agent claude-code --agent codex --apply

# 自动识别本机已存在的配置目录，仅预览；确认目标后单独安装
python scripts/skill_portability.py install --detect

# 项目级安装（project-dir 使用实际项目绝对路径）
python scripts/skill_portability.py install --agent trae-cn --scope project --project-dir "/path/to/project" --apply

# 客户端设置中确认过的自定义技能目录
python scripts/skill_portability.py install --skills-dir "/path/to/skills" --apply

# 生成界面上传用 ZIP；输出目录放在技能目录之外
python scripts/skill_portability.py package --output-dir "../skill-zips"
```

`--agent` 可选：`claude-code`、`codex`、`chatgpt`、`codex-legacy`、`kimi-code`、`qoder-cli`、`qoder-cn`、`qoderwork`、`trae`、`trae-cn`、`workbuddy`、`codebuddy`、`zcode`、`openclaw`、`agents`。设置了 `CLAUDE_CONFIG_DIR`、`KIMI_CODE_HOME`、`CODEX_HOME`（仅 `codex-legacy`）或 `OPENCLAW_STATE_DIR` 时，安装到对应目录下的 `skills/`。Claude 网页版、ChatGPT 团队版、豆包、Kimi Work、Qoder 桌面版等界面型客户端不虚构配置目录，一律上传 ZIP。

覆盖已安装版本前，安装器先把旧版复制到技能根目录之外的 `skill-backups/`，不删除任何文件。旧目录中有新版没有的文件时默认停止，先对照备份确认；确认后加 `--replace`，旧目录整体移入 `skill-backups/` 后写入新版。`meeting-minutes-pro` 的项目术语表与机构禁词（`glossary/` 下除 `README.md`、`industry/` 以外的文件）属于用户数据：不打包、不视为多余文件，`--replace` 时自动迁入新版目录。

## 四、运行环境适配

1. **路径**：以已加载 `SKILL.md` 的绝对路径确定 `SKILL_ROOT`，`references/`、`scripts/`、`assets/` 均相对此目录解析；脚本及输入输出使用绝对路径，报告写到用户任务目录。Kimi Code 可用 `${KIMI_SKILL_DIR}`，其他平台以技能加载结果为准，不原样传递不支持的变量。
2. **Python 与依赖**：写作本身不要求 Python；生成 Word 需要在 Agent 实际执行环境安装 `requirements.txt`（`meeting-minutes-pro` 为 `scripts/requirements-runtime.txt`，ASR 引擎由 `bootstrap_runtime.py` 另行安装）。云端沙箱与本机是不同环境；不得引用作者电脑用户名、特定 Python 路径或某一客户端私有工具。
3. **执行能力分级**：

| 能力 | 适用客户端 | 七个技能的可用范围 |
|---|---|---|
| 本机执行（读写本地文件、运行 Python） | Claude Code、Codex、ChatGPT 桌面版、Kimi Work / Kimi Code、豆包电脑版工作模式、WorkBuddy、TRAE、Qoder、ZCode、AutoClaw | 全部功能，含 `meeting-minutes-pro` 本地音视频转录 |
| 云端代码沙箱 | Claude 网页 / 桌面 Chat、ChatGPT 团队版 | 写作与 Word 生成可用；`meeting-minutes-pro` 仅能基于已有转录稿整理纪要，不能下载 ASR 模型转录本地录音 |
| 无代码执行 | 仅对话、不运行脚本的入口 | 可交付文本，须说明 Word 排版未生成或未验证，不得宣称已生成合规 Word |

4. **工具名称**：正文中的 WebSearch/WebFetch 代表“检索权威网页/打开来源”的能力，映射到当前 Agent 的搜索、浏览器或网页工具；读取资料、执行 Python 同理使用可用工具。没有网络时保留来源边界，不声称检索已完成。
5. **文档读取**：可使用平台自带的 PDF、表格、Word 读取器；存在同类通用文档技能时由其负责读取，当前技能负责业务逻辑及指定生成器。
6. **字体**：先运行技能内的字体检查（`ensure_fonts.py --check`；`meeting-minutes-pro`、`soe-post-investment-report` 为 `font_preflight.py`），按宿主权限及现有授权安装。沙箱不能安装系统字体时保留 DOCX 中文字体槽，并用随包嵌入器处理允许嵌入的字体；方正小标宋简体禁止嵌入，打开文档的设备须已安装。Times New Roman、黑体、宋体在非 Windows 环境不能假定存在，字体替换或缺失须在交付说明中如实说明。

`check --smoke` 从不同工作目录调用本包 Word 生成器，核对奇偶页脚、`-1-` 四号宋体页码、PAGE 域、Times New Roman 西文统一及表格五号（投后报告按其自带校验器）。它不安装字体、不修改客户端配置、不上传文档；通过只代表包结构与代码可执行，最终字体显示仍须在目标 Word/渲染器上目视检查。

## 五、技能路由与调用验收

| 技能 | 应触发的请求 | 不应代替的内容 |
|---|---|---|
| `hangye-fenxi` | 所属行业、市场规模、增长动力、产业链价值及共性门槛 | 公司工商、团队履历和产品订单分析 |
| `zhuying-yewu-fenxi` | 产品、技术优势、商业模式、客户订单、竞争比较及商业转化 | 纯行业概述或公司工商汇总 |
| `gongsi-qingkuang` | 主体、股权沿革、核心团队、权属、组织资源、融资与财务快照 | 行业研究或完整主营业务章 |
| `officialese-skill` | 通知、请示、报告、函等通用公文的起草、改写与 Word 排版 | 投委会议题、投后报告、立项报告章节 |
| `yiti-skill` | 股东会/合伙人会议参会表决议题、项目退出议题、提请投委会审议 | 一般通知或投后年度报告 |
| `meeting-minutes-pro` | 会议、访谈、路演录音转录及正式会议纪要 | 与录音无关的公文起草 |
| `soe-post-investment-report` | 基于投后材料创建或更新投后情况报告 | 立项报告或投委会议题 |

安装后在目标客户端**新建会话**完成以下验收，并记录客户端名称/版本、实际技能路径、结果及日期。本包不预先宣称各客户端已经实测。

1. **可发现**：技能列表出现原始英文 `name`（支持显示名称的客户端显示中文名），开关开启，无旧版本覆盖。直接说“使用 `<name>` 技能，只读取其规范，概括适用范围和 3 条排版规则”，观察实际技能加载记录；模型仅声称“已调用”不算验收。
2. **自动选择**：按上表分别输入一句典型请求，观察是否调用对应技能及所需参考文件；信息不足时应先收集必要输入，不能编造。再输入与各技能无关的请求，确认不被误选。
3. **运行完整**：在宿主执行环境运行 `check --smoke`，确认参考文件可读、生成器能找到同目录辅助模块及本机授权字体。无运行环境的平台不能记录为完整 Word 能力通过。
4. **输出一致**：用非敏感测试材料生成含表格、括注、`（1）` 标题、分页的 Word，核对中文字体、Times New Roman 数字及百分号、表格五号、奇偶页外侧页码和整段 14 磅页脚。

各技能另有首轮行为，验收时一并核对：立项报告三技能首轮先问“早前期或中后期”并等待；`soe-post-investment-report` 首轮只逐字提出四项变更确认问题；`meeting-minutes-pro` 生成纪要前先一次性收集缺失的会议基本信息；`yiti-skill` 先判定会议类或退出类骨架。

### 立项报告三技能附加验收

使用非敏感虚构公司测试：只说“写行业分析／主营业务分析／公司情况”，不提供阶段时，首轮应询问早前期或中后期并等待，不能直接出正文。回复“早前期”应读取本技能 `early.json`，回复“中后期”应读取 `mid-late.json`。三个技能连续处理同一项目时复用用户答案；换公司重新问。核对标题来源、个案填空和重复组，运行 `stage_template.py check`。中文路径、带空格路径和宿主无 Python 时的人工核对按 `stage-template-workflow.md` 执行。安装包必须包含两个 JSON、两份原文对照、执行规则及 `stage_template.py`。

## 六、排障

未触发时依次检查：产品与模式（如豆包须在“工作”模式、Kimi 须在 Work 模式）→ 启用开关 → 目录层级（`skills/<name>/SKILL.md`，不能多一层 `Skills-main/`）→ 同名覆盖 → 描述是否完整 → 参考文件可读 → 重载或新会话（Qoder CLI `/skills reload`，Codex、OpenClaw、WorkBuddy 重启）。界面上传因体积失败时改用目录安装。显式点名后仍无加载记录时，按该客户端提供的技能管理方式排查；不要用“文件已经复制”替代调用成功。
