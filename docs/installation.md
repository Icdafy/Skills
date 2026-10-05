# 安装与旧版更新

七项技能直接放在仓库根目录 `<仓库>/<英文名>/`，GitHub 地址沿用 `tree/main/<英文名>`。安装后的英文目录名、ZIP 下载目录及文件名不变，旧已安装技能不会自动更新。若使用过本PR早期的 `skills/<英文名>/` 路径，请改为根目录 `<英文名>/`；仓库只保留这一份源码。

## 单技能安装

在中文首页按用途选技能，下载一个 ZIP，解压进入英文目录，按 README 准备依赖和本机授权字体。`python scripts/skill_portability.py check --smoke` 是脚本执行验证。每个目录都包含本技能配套脚本、规则、模板、依赖和 LICENSE/NOTICE；不跨技能 import，不用符号链接代替资源。

以项目目录为例：

```powershell
python scripts/skill_portability.py install --agent codex --scope project --project-dir "C:/项目/示例 项目"
python scripts/skill_portability.py install --agent codex --scope project --project-dir "C:/项目/示例 项目" --apply
```

Claude Code 使用 `--agent claude-code`。只有 `--apply` 才写入；默认只预览。安装路径分别为项目 `.agents/skills/<英文名>`、`.claude/skills/<英文名>`。客户端提供另一个目录时用 `--skills-dir "绝对目录"`。仅目录或 ZIP 导入不能证明客户端模型已经调用；新建会话后做显式、自然语言和相邻技能反例验证。

## 更新一个已安装技能

将新版解压到不同目录，核对 VERSION 和 CHANGELOG，检查新包，再运行同一 install 命令更新指定项目。已有目录先备份到配置目录旁的 `skill-backups/`，备份不处于技能发现目录。

如果旧目录含多余文件，安装器保存备份后停止，原目录保留。查看文件后，必要时用 `--replace --apply` 将整个旧目录移到备份。会议纪要 `glossary/` 私有项目词库和禁词表被保留到新版，不进入 ZIP；其他本地材料保留在备份中，按需要手工取回。不要批量全局覆盖已安装技能，不要直接删掉旧目录来“升级”。

## 插件市场与旧安装

Claude Code：`/plugin marketplace add Icdafy/Skills` 后 `/plugin install <英文名>@icdafy-skills`，本次市场 source 已指向 `./<英文名>`。直接复制和市场安装不要重复启用同名技能。

Codex 可用 `$skill-installer install https://github.com/Icdafy/Skills/tree/main/<英文名>`；统一从main安装；单技能ZIP和安装器排除字体，GitHub整库源码下载含原18份历史字体。旧版仍读取 `$CODEX_HOME/skills` 时选择安装器的 `codex-legacy`，并在真实客户端确认实际路径。

Codex 的 `.agents/skills` 与显式 `$<name>`：[官方说明](https://learn.chatgpt.com/docs/build-skills)。Claude Code 的 `.claude/skills` 与 `/<name>`：[官方说明](https://code.claude.com/docs/en/skills)。其他客户端入口在各包共享 compatibility 参考中保留，实际验证程度见 [验证记录](validation.md)。
