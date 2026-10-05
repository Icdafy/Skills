# 根目录七项技能的实际验证

维护者反馈后，七项源码直接列在仓库根目录。没有新增技能，客户端安装目录和ZIP名称保留。

- [七次git mv退出码](moves.json)、[索引生成与七包重建](preparation.json)。
- [第2轮完整验收](../round-2/summary.json)：原50/258/56/8/3共375，374通过、原Windows符号链接跳过1项；另外13项正负资源测试通过，12条命令均退出0。
- [当前分发与安装](distribution/summary.json)：7/7仓库外中文空格路径烟测，备份和本地数据保留，四项反向检查红1→绿0；共53条实际命令符合预期。
- [单技能重建摘要](distribution/single-skill-hashes.json)：只改变yiti，其他六包不变。
- [214文件等价、七SKILL.md未变](source-content-equivalence.json)：只按文本checkout换行归一，README/CHANGELOG属于本次必要路径变更；保留历史真实模型/ASR记录，无重复调用声明。
- [当前纪要运行时路径检查](runtime-check.txt)：退出0，已有运行时可用，不下载依赖或模型。
- [当前冻结审计](../frozen-content.json)；[之前布局审计备份](frozen-content-before-flat-layout.json)。

Codex严格首轮只四问失败和最终浏览状态仍以 [BLOCKED.md](../../../BLOCKED.md) 为准。历史round-1/final/distribution日志保留真实旧路径，不改写为未执行过的命令。
