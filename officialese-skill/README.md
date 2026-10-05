# 国企公文写作与排版（officialese-skill）

当前分发版本：**1.0.1**；变更见 [CHANGELOG.md](CHANGELOG.md)。

## 用途与边界

通知、请示、报告、函等国企公文起草和排版；投委会议题、投后报告、立项章节另有专门技能。

## 输入和输出

输入：文种、行文对象、事由、正文资料、发文单位和日期。

输出：公文正文和 DOCX；不承诺自动生成旧 DOC 二进制格式。

## 依赖与字体

Python 3.10+；安装和完整性检查使用标准库，DOCX 生成需 `requirements.txt` 中的 python-docx。

单技能ZIP和安装器输出不含字体。GitHub源码按维护者要求保留原main三份字体，见 [字体说明](assets/fonts/README.md)；其公开再分发授权仍未确认。自行准备有使用权的仿宋、楷体_GB2312、方正小标宋等原版式字体，可用 `ICDAFY_FONT_DIR` 指向授权文件目录；运行 `python scripts/ensure_fonts.py --check` 检测。缺字体须明确说明，不能把草稿称为已通过实际版式验收；原字体、字号和版式规则保留。

## 完整安装例子

从 [单技能 ZIP](https://github.com/Icdafy/Skills/raw/refs/heads/main/distributions/office-skills/officialese-skill.zip) 下载，解压后进入 `officialese-skill`；不要只复制 SKILL.md。本 PR 合并前可从当前分支 `officialese-skill/` 安装。

```powershell
cd "C:/下载/技能包/officialese-skill"
python -m pip install -r requirements.txt
python scripts/skill_portability.py check --smoke
python scripts/skill_portability.py install --agent codex --scope project --project-dir "C:/项目/示例 项目"
python scripts/skill_portability.py install --agent codex --scope project --project-dir "C:/项目/示例 项目" --apply
```

Claude Code 把 `--agent codex` 换成 `--agent claude-code`。其他客户端及安装器目录表见 [跨客户端安装](references/agent-compatibility.md)。运行路径以本次实际加载的 SKILL.md 目录为根；脚本和输入输出使用绝对路径时可在任意任务目录执行。

## 调用例子

安装后新建会话，在 Codex 输入：

```text
$officialese-skill 帮我起草关于开展项目资料归档的通知，发给各部门，落款为示例公司。
```

Claude Code 输入 `/officialese-skill 帮我起草关于开展项目资料归档的通知，发给各部门，落款为示例公司。`；自然语言直接使用“帮我起草关于开展项目资料归档的通知，发给各部门，落款为示例公司。”。先补齐 SKILL.md 要求的缺失输入；不得编造事实。

## 已验证环境

Windows，Python 3.12.14。迁移后原375项用例完整发现，374通过、1项原Windows符号链接环境跳过；本技能ZIP在仓库外中文与空格路径执行 `check --smoke` 通过，项目安装、备份和本地文件保留已实测。

Codex CLI 0.160.0：新会话显式调用、自然语言和相邻技能反例均实际读取正确项目技能路径，路由通过。

Claude Code当前没有可运行客户端，未实测；其他客户端未实测。脚本成功不代替模型调用或Word视觉验收。原始提示、读取路径、结果和字体探针见 [验证记录](https://github.com/Icdafy/Skills/blob/main/docs/validation.md)。

## 升级入口

维护者只改 `officialese-skill/`，同步受影响的共享副本后执行 `python tools/package_skills.py --skill officialese-skill`（在整库根运行）；源码版本见 [VERSION](VERSION)，记录见 [CHANGELOG.md](CHANGELOG.md)。全部维护步骤见 [维护说明](https://github.com/Icdafy/Skills/blob/main/docs/maintenance.md)。

用户将新版解压到另一个目录，再用同样的 install 命令更新指定项目。已有安装先备份到 skills 目录外的 `skill-backups/`；出现多余文件会停止，手工确认后 `--replace --apply` 把旧目录移入备份。额外本地文件保留在备份中；确认内容后再决定是否迁入新版。源码保持在仓库根目录 `<仓库>/officialese-skill/`；GitHub 源码地址及安装后的英文目录名不变。

## 许可

[Apache-2.0](LICENSE)；[NOTICE](NOTICE) 保留署名、维护者素材授权确认和本机字体说明。
