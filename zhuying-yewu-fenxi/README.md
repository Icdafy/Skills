# 主营业务分析（zhuying-yewu-fenxi）

当前分发版本：**1.0.1**；变更见 [CHANGELOG.md](CHANGELOG.md)。

## 用途与边界

企业产品技术、商业模式、客户订单、竞争优势和技术壁垒；不替代纯行业研究或公司情况。

## 输入和输出

输入：产品技术资料、业务/销售数据、客户订单、访谈和项目阶段。

输出：主营业务分析正文、计算和表格及 DOCX。

## 依赖与字体

Python 3.10+；安装和完整性检查使用标准库，DOCX 生成需 `requirements.txt` 中的 python-docx。

单技能ZIP和安装器输出不含字体。GitHub源码按维护者要求保留原main三份字体，见 [字体说明](assets/fonts/README.md)；其公开再分发授权仍未确认。自行准备有使用权的仿宋、楷体_GB2312、方正小标宋等原版式字体，可用 `ICDAFY_FONT_DIR` 指向授权文件目录；运行 `python scripts/ensure_fonts.py --check` 检测。缺字体须明确说明，不能把草稿称为已通过实际版式验收；原字体、字号和版式规则保留。

## 完整安装例子

从 [单技能 ZIP](https://github.com/Icdafy/Skills/raw/refs/heads/main/distributions/investment-report-skills/zhuying-yewu-fenxi.zip) 下载，解压后进入 `zhuying-yewu-fenxi`；不要只复制 SKILL.md。本 PR 合并前可从当前分支 `zhuying-yewu-fenxi/` 安装。

```powershell
cd "C:/下载/技能包/zhuying-yewu-fenxi"
python -m pip install -r requirements.txt
python scripts/skill_portability.py check --smoke
python scripts/skill_portability.py install --agent codex --scope project --project-dir "C:/项目/示例 项目"
python scripts/skill_portability.py install --agent codex --scope project --project-dir "C:/项目/示例 项目" --apply
```

Claude Code 把 `--agent codex` 换成 `--agent claude-code`。其他客户端及安装器目录表见 [跨客户端安装](references/agent-compatibility.md)。运行路径以本次实际加载的 SKILL.md 目录为根；脚本和输入输出使用绝对路径时可在任意任务目录执行。

## 调用例子

安装后新建会话，在 Codex 输入：

```text
$zhuying-yewu-fenxi 帮我写立项报告的主营业务分析，重点说明产品技术和客户订单。
```

Claude Code 输入 `/zhuying-yewu-fenxi 帮我写立项报告的主营业务分析，重点说明产品技术和客户订单。`；自然语言直接使用“帮我写立项报告的主营业务分析，重点说明产品技术和客户订单。”。先回答“早前期”或“中后期”，再填写该阶段的原固定模板。

## 已验证环境

Windows，Python 3.12.14。迁移后原375项用例完整发现，374通过、1项原Windows符号链接环境跳过；本技能ZIP在仓库外中文与空格路径执行 `check --smoke` 通过，项目安装、备份和本地文件保留已实测。

Codex CLI 0.160.0：新会话显式调用、自然语言和相邻技能反例均实际读取正确项目技能路径，路由通过。

Claude Code当前没有可运行客户端，未实测；其他客户端未实测。脚本成功不代替模型调用或Word视觉验收。原始提示、读取路径、结果和字体探针见 [验证记录](https://github.com/Icdafy/Skills/blob/main/docs/validation.md)。

## 升级入口

维护者只改 `zhuying-yewu-fenxi/`，同步受影响的共享副本后执行 `python tools/package_skills.py --skill zhuying-yewu-fenxi`（在整库根运行）；源码版本见 [VERSION](VERSION)，记录见 [CHANGELOG.md](CHANGELOG.md)。全部维护步骤见 [维护说明](https://github.com/Icdafy/Skills/blob/main/docs/maintenance.md)。

用户将新版解压到另一个目录，再用同样的 install 命令更新指定项目。已有安装先备份到 skills 目录外的 `skill-backups/`；出现多余文件会停止，手工确认后 `--replace --apply` 把旧目录移入备份。额外本地文件保留在备份中；确认内容后再决定是否迁入新版。源码保持在仓库根目录 `<仓库>/zhuying-yewu-fenxi/`；GitHub 源码地址及安装后的英文目录名不变。

## 许可

[Apache-2.0](LICENSE)；[NOTICE](NOTICE) 保留署名、维护者素材授权确认和本机字体说明。

## 原业务说明与历史记录

# zhuying-yewu-fenxi｜立项报告·主营业务分析

## 两阶段固定模板

调用写作时先询问“早前期（2026-09 终稿范式）还是中后期（因诺科技）”，用户回答后按对应标题逐项填入当前公司资料。同项目连续调用复用明确答案。完整标题见 [早前期](references/template-early.md)、[中后期](references/template-mid-late.md)；执行与校验见 [阶段模板规则](references/stage-template-workflow.md)。旧版自动选型和标题自由调整已取消。

撰写一级市场股权投资立项报告中"三、主营业务分析"章节的 Claude 技能（v2）。

## v2 核心变化

v1 是一套教科书式的 12 节固定框架；v2 以两篇内部范文为母版重建：

1. **两套母版结构**：多板块式（因诺科技型，板块五段式）与单主线式（伊隆纬特型，早前期已改用 2026-09 终稿范式：业务介绍→产品→技术→开展情况；原产品→技术→模式→上下游→竞对→预测），由用户明确选择早前期或中后期，完整标题以原文模板为准；
2. **写作基因系统**（`references/writing-dna.md`）：结论前置三层法、四拍技术优势法、订单五要素、客户背景小传、市场空间四句式、客户评价三段式、规划三段式、章末预测收束；
3. **会议纪要升级为一级信源**：附纪要挖掘清单（订单、市占率、竞对关系、定价机制、渗透深度、规划目标）；
4. **联网补研协议**（`references/research-protocol.md`）：竞对财务与估值、市场空间锚点、战略客户背景、企业自述核验；
5. **语言禁令**：全文禁用"标的公司"（直接写公司简称）、禁用"不是…而是/不仅…而且"等对举连词、禁机械总结腔，附改写示例；
6. **风险内嵌**：随范文取消独立风险章与空泛小结，风险以劣势三段式与实际约束及影响嵌入正文，重大风险时才增设独立节；
7. **公文排版与字体自动化**（v2.2，三技能统一）：内置集团《行文规范性格式模板》全套规则（方正小标宋二号主标题、仿宋_GB2312三号正文、28磅固定行距、A4公文页边距、外侧奇偶页码）；表格全五号、中文仿宋_GB2312及括注楷体_GB2312、西文Times New Roman；表头首行加粗、不加底纹、表头行跨页重复、宽度按窗口自动调整、所有单元格居中；渲染由与 hangye-fenxi / gongsi-qingkuang 共用的 `scripts/build_docx.py` 统一完成，不再手写排版代码；三个公文字体不进入单技能ZIP和安装器输出；`scripts/ensure_fonts.py` 检测本机并仅从自行准备的 ICDAFY_FONT_DIR 授权目录按需安装，`ensure-fonts.ps1` 是调用同一Python脚本的兼容入口，不下载字体。

## 审阅批注吸收（2026-09）

根据一份早期立项报告多轮审阅批注与修订（已脱敏，不含项目事实）更新：

1. 板块与产品由主到次排列，概况段嵌入主要客户与合作对象；
2. 产品表加应用场景列，价格写明计价范围，改装集成类产品并列购入价、售价与单台毛利；有实物照片时插图（`build_docx.py` 新增 `image` 块）；
3. 核心技术写出技术高度（“具名企业 A 达到……，公司达到……”，新增技术对标表），整机适配类业务着重写先发优势；
4. 专业术语首次出现即解释；价格随规格或产能变化的句子写清驱动因素；
5. 禁止“国内暂无同规格竞品”式排他论断，证据支撑时不用“具备一定技术基础”式模糊措辞；
6. 意向订单按业务板块拆分，单独写深度合作、绑定大客户与中标工程；
7. `style_check.py` 新增数值范围、半角括号、不规范用词、本方投资表态扫描，排他论断与复述式收尾给警告。

## 文件结构

```
zhuying-yewu-fenxi/
├── SKILL.md                        # 主流程：身份、三条铁律、七步法、数据红线
├── references/
│   ├── writing-dna.md              # 范文写作基因解构（含范文瑕疵清单）
│   ├── chapter-template.md         # 固定模板内的内容方法+表格+证据覆盖底线
│   ├── language-style.md           # 禁令清单+句式库+改写示例
│   ├── research-protocol.md        # 联网检索协议
│   ├── metrics-formulas.md         # 指标公式+交叉印证+数据充分性
│   ├── quality-checklist.md        # 输出前逐项自检
│   └── docx-format.md              # 公文排版规范（页面/字体层级/表格/统一渲染脚本）
├── scripts/
│   ├── build_docx.py               # 三技能统一 .docx 渲染脚本
│   ├── ensure_fonts.py             # 字体自动检测与用户级安装（Windows 含注册表注册）
│   ├── style_check.py              # 语言红线机械扫描
│   └── ensure-fonts.ps1            # 调用同目录Python字体脚本的PowerShell兼容入口，不下载字体
└── assets/fonts/
    └── README.md                 # 源码保留原main字体，单技能ZIP仅含说明
```

## 使用方式

上传目标公司的尽调资料包（BP、访谈/会议纪要、财务数据、订单台账、产品资料等任意组合），说明"写XX公司的主营业务分析"即可。资料缺口不阻断分析：缺口数据不写入报告正文与表格，随成稿在对话中输出"资料缺口与待核查清单"（缺什么、影响哪个判断、建议的补充渠道）；需要 Word 文档时说明即可由统一脚本生成公文排版 .docx。

## 终稿范式升级（2026-09-23）

依据一份经多轮审阅定稿的早前期立项报告（内部文件，事实不入库）升级：

- 早前期模板改为终稿结构：主营业务介绍、主要产品概况（产品重复组）、核心技术与优势（技术重复组）、业务开展情况（近期、中期、远期）；客户、订单与财务归公司情况章；
- `writing-dna.md` 新增第十节：业务介绍“一段定性＋四列板块表”、产品六要素、技术“三段式”及先发优势、开展情况“××方面”分段，以及初稿到终稿的改写规律；
- 正文不附算式、资料文件名和问题编号，算式留底稿；
- `style_check.py` 新增方法论/告诫句与内部资料痕迹扫描；`build_docx.py` 段落块支持 `lead`。

## 数字千位分隔（2026-09-28）

- 公文格式硬规则新增第 8 条：阿拉伯数字按英美通行写法三位分节，整数部分四位及以上自个位起每三位加半角逗号、小数点用半角点（`1,234.56`、`2,350万元`、`1,000,000`），正文、表格、括注、附件一律适用；年份、日期、文号、编号、代码、电话、证件号、标准号等标识性数字不加逗号；
- `style_check.py` 新增未分节数字扫描（硬规则），参考资料和范例中的数字同步改为分节写法。

## 跨 Agent 安装与调用

[下载完整技能 ZIP](https://github.com/Icdafy/Skills/raw/refs/heads/main/distributions/investment-report-skills/zhuying-yewu-fenxi.zip)。Claude、ChatGPT、Codex、Kimi、豆包、智谱 GLM（ZCode、AutoClaw）、WorkBuddy、TRAE、Qoder 的安装入口、目录差异和验收见 [跨 Agent 安装与调用](references/agent-compatibility.md)。

本技能名为 `zhuying-yewu-fenxi`。保留完整文件夹，启用后新建会话点名调用；可运行 `python scripts/skill_portability.py check --smoke` 检查资源及Word生成。技能发现与模型实际调用须在目标客户端按指引验收，不能仅凭复制文件认定成功。
