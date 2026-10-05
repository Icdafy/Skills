# 会议转录与正式纪要（meeting-minutes-pro）

当前分发版本：**1.0.1**；变更见 [CHANGELOG.md](CHANGELOG.md)。

## 用途与边界

录音、转录稿或访谈的正式纪要，完整概述与完整问答；语音端仅在已有引擎/模型可用时执行。

## 输入和输出

输入：会议名称、时间、地点、主持/记录/参会人；文本转录稿或音视频、术语资料。

输出：纪要/问答文本、事实与覆盖检查、DOCX；有语音环境时另有转录及证据。

## 依赖与字体

Python 3.10+；文本检查使用标准库，DOCX 生成需 `scripts/requirements-runtime.txt` 中的依赖。语音环境由 `python scripts/bootstrap_runtime.py --check` 检测；FunASR/Qwen3-ASR、FFmpeg 和模型另行准备，本次真实引擎未实测。

单技能ZIP和安装器输出不含字体。GitHub源码按维护者要求保留原main三份字体，见 [字体说明](assets/fonts/README.md)；其公开再分发授权仍未确认。自行准备有使用权的仿宋_GB2312、楷体_GB2312、方正小标宋简体等原版式字体，可用 `ICDAFY_FONT_DIR` 指向授权文件目录；运行 `python scripts/font_preflight.py --check` 检测。缺字体须明确说明，不能把草稿称为已通过版式验收；原字体、字号和版式规则保留。

## 完整安装例子

从 [单技能 ZIP](https://github.com/Icdafy/Skills/raw/refs/heads/main/distributions/office-skills/meeting-minutes-pro.zip) 下载，解压后进入 `meeting-minutes-pro`；不要只复制 SKILL.md。本 PR 合并前可从当前分支 `meeting-minutes-pro/` 安装。

```powershell
cd "C:/下载/技能包/meeting-minutes-pro"
python -m pip install -r scripts/requirements-runtime.txt
python scripts/skill_portability.py check --smoke
python scripts/skill_portability.py install --agent codex --scope project --project-dir "C:/项目/示例 项目"
python scripts/skill_portability.py install --agent codex --scope project --project-dir "C:/项目/示例 项目" --apply
```

Claude Code 把 `--agent codex` 换成 `--agent claude-code`。其他客户端及安装器目录表见 [跨客户端安装](references/agent-compatibility.md)。运行路径以本次实际加载的 SKILL.md 目录为根；脚本和输入输出使用绝对路径时可在任意任务目录执行。

## 调用例子

安装后新建会话，在 Codex 输入：

```text
$meeting-minutes-pro 把这份访谈转录稿整理成完整概述和完整问答的正式会议纪要。
```

Claude Code 输入 `/meeting-minutes-pro 把这份访谈转录稿整理成完整概述和完整问答的正式会议纪要。`；自然语言直接使用“把这份访谈转录稿整理成完整概述和完整问答的正式会议纪要。”。先补齐 SKILL.md 要求的缺失输入；不得编造事实。

## 已验证环境

Windows，Python 3.12.14。迁移后原375项用例完整发现，374通过、1项原Windows符号链接环境跳过；本技能ZIP在仓库外中文与空格路径执行 `check --smoke` 通过，项目安装、备份和本地文件保留已实测。

Codex CLI 0.160.0：新会话显式调用、自然语言和相邻技能反例均实际读取正确项目技能路径，路由通过。文本生成实测保留2组问答、3窗全部内容和24个数字事实，四项检查全部退出0；这是文本草稿，`release_ready:false`。已有FunASR及Qwen0.6B真实离线推理13.675秒合成中文语音均成功；Qwen CUDA首次失败，CPU重试通过。真实长会、方言、说话人分离和全量回听未实测。

Claude Code当前没有可运行客户端，未实测；其他客户端未实测。脚本成功不代替模型调用或Word视觉验收。原始提示、读取路径、结果和字体探针见 [验证记录](https://github.com/Icdafy/Skills/blob/main/docs/validation.md)。

## 升级入口

维护者只改 `meeting-minutes-pro/`，同步受影响的共享副本后执行 `python tools/package_skills.py --skill meeting-minutes-pro`（在整库根运行）；源码版本见 [VERSION](VERSION)，记录见 [CHANGELOG.md](CHANGELOG.md)。全部维护步骤见 [维护说明](https://github.com/Icdafy/Skills/blob/main/docs/maintenance.md)。

用户将新版解压到另一个目录，再用同样的 install 命令更新指定项目。已有安装先备份到 skills 目录外的 `skill-backups/`；出现多余文件会停止，手工确认后 `--replace --apply` 把旧目录移入备份。会议纪要私有术语自动保留，其他本地文件在备份中保留。源码保持在仓库根目录 `<仓库>/meeting-minutes-pro/`；GitHub 源码地址及安装后的英文目录名不变。

## 许可

[Apache-2.0](LICENSE)；[NOTICE](NOTICE) 保留署名、维护者素材授权确认和本机字体说明。

## 原业务说明与历史记录

下方保留原业务用法与历史。旧 `install_skill.py` 供兼容初次安装；更新已有版本请使用上方项目安装命令，以获得备份和本地数据保留检查。

# meeting-minutes-pro

在用户本机转录会议音视频，并依据录音或用户指定的文字材料生成客观、书面化、公文版式的会议纪要。默认中文转录使用 FunASR，外语、方言和多语言场景使用 Qwen3-ASR。含明确问答时保留“完整总结概述＋完整问答”，正式纪要默认交付 DOCX。

## 可靠性与适用边界

- 有录音时，BP、辅助笔记等只用于规范术语；仅提供文字材料时按 transcript/notes 模式处理，不声称经过录音核验。
- 高风险录音的独立复核覆盖源音频完整时间轴，包括主稿没有识别内容的区间；禁止预算截断。硬件建议不能降低保障要求。
- 严格数字审计按实例匹配，保留带单位的小数字、中文年份、正负号及币种，区分百分比和百分点；对象、时间、限定条件仍须逐事实语义核对。
- 短问题保留为候选；多个提问匹配同一纪要问题时提示逐项检查追问与答复。
- 检查点绑定实际音频及识别配置，模型、热词、语言、增强和时间戳设置变化后不复用旧结果。
- `checks_passed` 是程序检查结果；`release_ready` 才是该版本完成证据、人工裁决和版式验收的状态。双引擎一致不保证录音绝对准确。

## 工作流程

1. 读取 [SKILL.md](SKILL.md)，确定输入类型、会议信息及风险等级。
2. 用运行时 Python 执行 `scripts/bootstrap_runtime.py --check`；模型缺失时在已有授权范围内安装。
3. 试转样本、完整转录，适用时执行全量或定向独立复核；保留原始稿，修订另存并记录依据。
4. 起草完整纪要，填写覆盖清单并运行 `check_all.py --ledger ...`。修复数字遗漏、问答错误和格式问题。
5. 生成 DOCX、渲染并逐页检查。用 `--make-review` 生成版本绑定的事实与警告清单，完成实际裁决。
6. 使用相同输入执行 `check_all.py --stage release --review ... --render-report ...`；以 `release_ready: true` 作为正式验收结果。

完整命令、复核 JSON 字段及状态语义见 [证据链与交付验收](references/evidence-and-release.md)。不要把旧版只运行四个子脚本或只回读 DOCX 的命令当成正式验收。

## 模型与环境

FunASR 提供中文及中英混合转录、热词、句级时间戳和可选说话人分离。Qwen3-ASR 支持30种语言及22种中文方言；其强制对齐模型支持11种语言，转录支持范围不等于对齐支持范围。

主转录和复核均可用 `--offline` 解析本地模型缓存并阻止进程内 Python 网络连接；缺缓存时报错。它不是系统防火墙，严格隔离应在操作系统层断网后运行。具体环境、硬件与故障处理见 [运行参考](references/runtime.md)。

Qwen 主稿再次由 Qwen 重转不计作独立双引擎；当前自动复核器支持 FunASR 主稿→Qwen 复核。没有适用独立引擎时须说明限制，不能填写虚假的高保障状态。

## 版式与归档

纯文本是纪要内容基准，DOCX 按 [固定版式](references/format-and-output.md) 生成；数字按英美写法加半角千位分隔符（`1,234.56`、`2,350万元`，年份、日期、文号、编号等标识性数字除外），`quality_check.py` 扫描未分节数字；`format_spec.py` 统一层级、字体和页面规约。保留内容与样式回读、字体嵌入和逐页渲染检查。PDF 中只要求实际使用的相应字体，不因文档未使用某种标题而误报缺字体。

每场会议独立归档原始转录、适用的修订稿与修订记录、复核报告、覆盖清单、`review.json`、`checks-summary.json`、渲染 JSON 和纪要。渲染 PDF 完成检查后可删除；用户索要时保留。

## 安装、更新与隐私

[下载完整技能 ZIP](https://github.com/Icdafy/Skills/raw/refs/heads/main/distributions/office-skills/meeting-minutes-pro.zip)，在 Claude、ChatGPT、豆包、WorkBuddy、Kimi Work、Qoder、TRAE 的技能界面上传；目录型客户端用 `python scripts/skill_portability.py install --agent <客户端> --apply`（`agents` 子命令列出 claude-code、codex、kimi-code、workbuddy、trae-cn、qoder-cli、zcode、openclaw 等全部目标，`--detect` 自动识别本机客户端）。覆盖更新时旧版先备份到 `skill-backups/`，项目术语与机构禁词始终保留。旧命令 `python scripts/install_skill.py --target codex|claude|workbuddy|all [--force]` 仍可用。旧版无指纹 ASR 检查点自动重算，旧版复核报告须按新版重新生成。

`glossary/industry/` 是公共行业术语库；`glossary/` 根下项目术语和 `banned-phrases.txt` 是用户数据。安装复制与 Git 发布默认排除私有数据。对目录手工打包时也必须排除这些文件，不得仅依赖 `.gitignore`。不把模型、录音、转录稿、项目数据或本机路径补丁上传到技能仓库。

各客户端安装入口、调用方式与验收见 [跨 Agent 安装与调用](references/agent-compatibility.md)，本技能特有的执行环境与分发要求见 [安装参考](references/platforms.md)。从已使用目录分发前按公共文件清单核对；本地环境可能另有平台兼容修复，不随技能复制。

## 验证

```powershell
<runtime-python> -B -m unittest discover -s tests
```

测试包括转录辅助函数、断点恢复、全量覆盖、数字与问答反例、版本绑定证据、私有术语保留、DOCX 内容/样式和渲染检查。模拟测试不代表真实录音识别准确率；更换依赖或模型后需在本地重新验证加载及样例推理。

排版分层及暂不引入系统级文档模型的理由见 [架构说明](references/architecture.md)。
