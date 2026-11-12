# 主营业务分析（zhuying-yewu-fenxi）

当前分发版本：**1.1.1**；变更见 [CHANGELOG.md](CHANGELOG.md)。

## 用途与边界

企业产品技术、商业模式、客户订单、竞争优势和技术壁垒；不替代纯行业研究或公司情况。

## 1.1.0 的主要变化

- 成文口吻按实际上会的立项报告终稿校准：`SKILL.md` 写入表述十二条、逻辑十条，另附 [书面公文表述](references/formal-expression.md) 和 [硬逻辑论证](references/hard-logic.md) 两份规范；`style_check.py` 增加口语、机器腔、空话和逻辑结构的机械扫描。
- 页码改为 `- 1 -`；生成 Word 时自动为四位以上的数量补千位分隔符，年份、文号、型号、专利号等标识不变。
- 新增 DeepSeek Harness、千问办公的安装说明。

## 输入和输出

输入：产品技术资料、业务/销售数据、客户订单、访谈和项目阶段。

输出：主营业务分析正文、计算和表格及 DOCX。

## 依赖与字体

Python 3.10+；安装和完整性检查使用标准库，DOCX 生成需 `requirements.txt` 中的 python-docx。

单技能ZIP和安装器输出不含字体。GitHub源码按维护者要求保留原main三份字体，见 [字体说明](assets/fonts/README.md)；其公开再分发授权仍未确认。自行准备有使用权的仿宋、楷体_GB2312、方正小标宋等原版式字体，可用 `ICDAFY_FONT_DIR` 指向授权文件目录；运行 `python scripts/ensure_fonts.py --check` 检测。缺字体须明确说明，不能把草稿称为已通过实际版式验收；原字体、字号和版式规则保留。

## 完整安装例子

从 [单技能 ZIP](https://github.com/Icdafy/Skills/releases/download/zhuying-yewu-fenxi%2Fv1.1.1/zhuying-yewu-fenxi.zip) 下载，解压后进入 `zhuying-yewu-fenxi`；不要只复制 SKILL.md。从 Release 下载本页版本的 ZIP，源码安装使用 main；核对本页版本与[VERSION](VERSION)。

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

1.1.0（2026-11-12）：Windows，Python 3.12.14。三技能回归、独立工作目录 `check --smoke`（含 `- 1 -` 页脚和千位分隔符核对）通过；新增表述与逻辑规则在各客户端的实际成文效果未实测，DeepSeek Harness、千问办公的模型调用未实测。以下为此前版本的记录。

Windows，Python 3.12.14。迁移后原375项用例完整发现，374通过、1项原Windows符号链接环境跳过；本技能ZIP在仓库外中文与空格路径执行 `check --smoke` 通过，项目安装、备份和本地文件保留已实测。

Codex CLI 0.160.0：新会话显式调用、自然语言和相邻技能反例均实际读取正确项目技能路径，路由通过。

Claude Code当前没有可运行客户端，未实测；其他客户端未实测。脚本成功不代替模型调用或Word视觉验收。原始提示、读取路径、结果和字体探针见 [验证记录](https://github.com/Icdafy/Skills/blob/main/docs/maintenance.md#历史实测范围)。

## 升级入口

维护者只改 `zhuying-yewu-fenxi/`，同步受影响的共享副本后执行 `python tools/package_skills.py --skill zhuying-yewu-fenxi`（在整库根运行）；源码版本见 [VERSION](VERSION)，记录见 [CHANGELOG.md](CHANGELOG.md)。全部维护步骤见 [维护说明](https://github.com/Icdafy/Skills/blob/main/docs/maintenance.md)。

用户将新版解压到另一个目录，再用同样的 install 命令更新指定项目。已有安装先备份到 skills 目录外的 `skill-backups/`；出现多余文件会停止，手工确认后 `--replace --apply` 把旧目录移入备份。额外本地文件保留在备份中；确认内容后再决定是否迁入新版。源码保持在仓库根目录 `<仓库>/zhuying-yewu-fenxi/`；GitHub 源码地址及安装后的英文目录名不变。

## 许可

[Apache-2.0](LICENSE)；[NOTICE](NOTICE) 保留署名、维护者素材授权确认和本机字体说明。
