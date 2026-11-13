# 投委会议题（yiti-skill）

当前分发版本：**1.1.0**；变更见 [CHANGELOG.md](CHANGELOG.md)。

## 用途与边界

撰写报送投委会、董事会、专题会审议的议题，共五类：股东会与合伙人会议参会表决、项目投资、基金组建、项目退出与股权回购、采购等经营事项。成文遵循本单位议题的书面公文口吻和硬逻辑要求（表述规范、逻辑规范见 `references/expression-style.md`、`references/logic-chain.md`）。不代写一般通知、请示、投后报告和会议纪要。

## 输入和输出

输入：会议通知、议案和表决票；尽调、审计、评估报告和交易方案；基金方案及管理人资料；退出与回购条款、经营数据；采购需求和报价比选。

输出：按所属类型固定骨架写成的议题正文、附件说明及 DOCX；页码 `- 1 -`，四位以上数量带千位分隔符。

## 依赖与字体

Python 3.10+；安装和完整性检查使用标准库，DOCX 生成需 `requirements.txt` 中的 python-docx。

单技能ZIP和安装器输出不含字体。GitHub源码按维护者要求保留原main三份字体，见 [字体说明](assets/fonts/README.md)；其公开再分发授权仍未确认。自行准备有使用权的仿宋、楷体_GB2312、方正小标宋等原版式字体，可用 `ICDAFY_FONT_DIR` 指向授权文件目录；运行 `python scripts/ensure_fonts.py --check` 检测。缺字体须明确说明，不能把草稿称为已通过实际版式验收；原字体、字号和版式规则保留。

## 完整安装例子

从 [单技能 ZIP](https://github.com/Icdafy/Skills/releases/download/yiti-skill%2Fv1.1.0/yiti-skill.zip) 下载，解压后进入 `yiti-skill`；不要只复制 SKILL.md。从 Release 下载本页版本的 ZIP，源码安装使用 main；核对本页版本与[VERSION](VERSION)。

```powershell
cd "C:/下载/技能包/yiti-skill"
python -m pip install -r requirements.txt
python scripts/skill_portability.py check --smoke
python scripts/skill_portability.py install --agent codex --scope project --project-dir "C:/项目/示例 项目"
python scripts/skill_portability.py install --agent codex --scope project --project-dir "C:/项目/示例 项目" --apply
```

Claude Code 把 `--agent codex` 换成 `--agent claude-code`；DeepSeek Harness 用 `--agent dsh`，千问办公用 `--agent qwenwork`，WorkBuddy 用 `--agent workbuddy`，TRAE 用 `--agent trae-cn` 或 `--agent trae`，Qoder CLI 用 `--agent qoder-cli`。ChatGPT、Claude 网页与桌面版、豆包电脑版工作模式、Qoder 桌面版在各自的技能页上传 ZIP。其他客户端及安装器目录表见 [跨客户端安装](references/agent-compatibility.md)。运行路径以本次实际加载的 SKILL.md 目录为根；脚本和输入输出使用绝对路径时可在任意任务目录执行。

## 调用例子

安装后新建会话，在 Codex 输入：

```text
$yiti-skill 根据股东会通知和议案写投委会议题，提请审议参会及表决事项。
```

Claude Code 输入 `/yiti-skill 根据股东会通知和议案写投委会议题，提请审议参会及表决事项。`；自然语言直接使用“根据股东会通知和议案写投委会议题，提请审议参会及表决事项。”。先补齐 SKILL.md 要求的缺失输入；不得编造事实。

## 已验证环境

1.1.0（2026-11-13）：Windows，Python 3.12.16。`tools/tests`、`tools/library_tests` 全部通过；`check --smoke` 通过（核对 `- 1 -` 页脚、千位分隔符自动补齐且标识数字不变）；单技能 ZIP 在仓库外解压后 `check --smoke` 通过，并以 `--skills-dir` 方式试装到临时目录。新增的口语与机器腔规则在维护者提供的议题终稿文本上试扫，未出现误报。

各客户端的模型实际调用（ChatGPT、Claude、Qoder、TRAE、WorkBuddy、DeepSeek Harness、千问办公、豆包）本次均未实测；表述与逻辑规则在各模型上的成文效果未实测；本机未做 Word 逐页目视验收。Codex CLI 0.160.0 的路由结果为1.0.x版本的历史记录，见 [验证记录](https://github.com/Icdafy/Skills/blob/main/docs/maintenance.md#历史实测范围)。脚本成功不代替模型调用或 Word 视觉验收。

## 升级入口

维护者只改 `yiti-skill/`，同步受影响的共享副本后执行 `python tools/package_skills.py --skill yiti-skill`（在整库根运行）；源码版本见 [VERSION](VERSION)，记录见 [CHANGELOG.md](CHANGELOG.md)。全部维护步骤见 [维护说明](https://github.com/Icdafy/Skills/blob/main/docs/maintenance.md)。

用户将新版解压到另一个目录，再用同样的 install 命令更新指定项目。已有安装先备份到 skills 目录外的 `skill-backups/`；出现多余文件会停止，手工确认后 `--replace --apply` 把旧目录移入备份。额外本地文件保留在备份中；确认内容后再决定是否迁入新版。源码保持在仓库根目录 `<仓库>/yiti-skill/`；GitHub 源码地址及安装后的英文目录名不变。

## 许可

[Apache-2.0](LICENSE)；[NOTICE](NOTICE) 保留署名、维护者素材授权确认和本机字体说明。
