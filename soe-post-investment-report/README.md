# 国企股权投资投后报告（soe-post-investment-report）

当前分发版本：**1.6.0**；变更见 [CHANGELOG.md](CHANGELOG.md)。

## 用途与边界

国企股权投资半年度/年度投后情况报告；先四问，沿用上期框架，不代写单个立项章节。成文按实际投后报告定稿的口吻、句型和论证逻辑：`references/expression-playbook.md` 管写什么和顺序，`references/report-voice.md` 管每句话怎么说（十三种句型、段首定位词、固定程度词、素材转写、去机器腔），`references/logic-chain.md` 管每句话凭什么成立和上下句怎么接（一句四问、判断五级、算式、一致性约束）。数量一律加千位分隔符（`scripts/group_thousands.py` 可一次补齐），页码为 `- 1 -`。

## 输入和输出

输入：上期定稿、项目名册、投后材料、财务与经营数据、报告期间及四问答复。

输出：正文不超过10页的报告/附件 DOCX；完整渲染闭环后才认证，未认证草稿如实标注。

## 依赖与字体

Python 3.10+；安装和资料盘点使用标准库，DOCX 生成需 `requirements.txt` 中的依赖。最终认证另需 pypdf、Microsoft Word 或 LibreOffice 及 Poppler，完整依赖说明保留在下方。

公开包不含字体。在出文机器准备合法授权的准确字体，运行 `python scripts/font_preflight.py` 做只读检测。本技能不使用 ICDAFY_FONT_DIR；未完成字体及实际渲染闭环时，只能交付未认证草稿。原版式规则保留。

## 完整安装例子

从 [单技能 ZIP](https://github.com/Icdafy/Skills/releases/download/soe-post-investment-report%2Fv1.6.0/soe-post-investment-report.zip) 下载，解压后进入 `soe-post-investment-report`；不要只复制 SKILL.md。从 Release 下载本页版本的 ZIP，源码安装使用 main；核对本页版本与[VERSION](VERSION)。

```powershell
cd "C:/下载/技能包/soe-post-investment-report"
python -m pip install -r requirements.txt
python scripts/skill_portability.py check --smoke
python scripts/skill_portability.py install --agent codex --scope project --project-dir "C:/项目/示例 项目"
python scripts/skill_portability.py install --agent codex --scope project --project-dir "C:/项目/示例 项目" --apply
```

Claude Code 把 `--agent codex` 换成 `--agent claude-code`，DeepSeek Harness 用 `--agent dsh`，千问办公用 `--agent qwenwork`，Qoder、TRAE、WorkBuddy 分别用 `qoder-cli`、`trae-cn`、`workbuddy`；ChatGPT 团队版、Claude 网页和桌面版、豆包电脑版工作模式上传 ZIP。其他客户端及安装器目录表见 [跨客户端安装](references/agent-compatibility.md)。运行路径以本次实际加载的 SKILL.md 目录为根；脚本和输入输出使用绝对路径时可在任意任务目录执行。

## 调用例子

安装后新建会话，在 Codex 输入：

```text
$soe-post-investment-report 用这些本期投后资料更新半年度投后情况报告，先确认变化事项。
```

Claude Code 输入 `/soe-post-investment-report 用这些本期投后资料更新半年度投后情况报告，先确认变化事项。`；自然语言直接使用“用这些本期投后资料更新半年度投后情况报告，先确认变化事项。”。首轮只按 SKILL.md 提出四项变更确认，再据回复更新。

## 已验证环境

Windows，Python 3.12.14。迁移后原375项用例完整发现，374通过、1项原Windows符号链接环境跳过；本技能ZIP在仓库外中文与空格路径执行 `check --smoke` 通过，项目安装、备份和本地文件保留已实测。

Codex CLI 0.160.0：新会话显式调用、自然语言和相邻技能反例均实际读取正确项目技能路径，路由通过。历史会话中，三例的四问内容和顺序正确，首轮另含进度或技能依据说明；实际输出保留在[客户端验证记录](https://github.com/Icdafy/Skills/blob/0a15cc20451414f1506d4f7fe4e8bba8939af875/docs/validation/clients/codex/summary.json)。

1.6.0（2026-11-13）：本技能测试60项通过（1项跳过），单技能 ZIP 在仓库外中文与空格路径 `check --smoke` 通过；本机无可用渲染器，未做 PDF 渲染和逐页目视验收；新增的口吻与逻辑规则在各客户端的实际成文效果未实测。

Claude Code、ChatGPT、Qoder、TRAE、WorkBuddy、DeepSeek Harness、千问办公、豆包等客户端的模型调用均未实测，安装入口见[跨客户端安装](references/agent-compatibility.md)。脚本成功不代替模型调用或Word视觉验收。原始提示、读取路径、结果和字体探针见 [验证记录](https://github.com/Icdafy/Skills/blob/main/docs/maintenance.md#历史实测范围)。

## 升级入口

维护者只改 `soe-post-investment-report/`，执行 `python tools/package_skills.py --skill soe-post-investment-report`（在整库根运行）；源码版本见 [VERSION](VERSION)，记录见 [CHANGELOG.md](CHANGELOG.md)。全部维护步骤见 [维护说明](https://github.com/Icdafy/Skills/blob/main/docs/maintenance.md)。

用户将新版解压到另一个目录，再用同样的 install 命令更新指定项目。已有安装先备份到 skills 目录外的 `skill-backups/`；出现多余文件会停止，手工确认后 `--replace --apply` 把旧目录移入备份。额外本地文件保留在备份中；确认内容后再决定是否迁入新版。源码保持在仓库根目录 `<仓库>/soe-post-investment-report/`；GitHub 源码地址及安装后的英文目录名不变。

## 许可

[Apache-2.0](LICENSE)；[NOTICE](NOTICE) 保留署名、维护者素材授权确认和本机字体说明。
