# 字体来源与保留范围

2026-10-05维护者要求原main字体文件不变。本技能源码保留以下三份历史文件，原路径、字节及fsType不改；字体不适用仓库Apache-2.0授权，公开再分发授权尚未确认。GitHub整库Download ZIP包含源码中的历史字体；单技能下载ZIP和安装器输出排除它们。

| 文件 | SHA-256 | fsType |
|---|---|---:|
| `FZXiaoBiaoSongJT.ttf` | `5b1d10a2543c436df12aa292b05bff59ce6dae1b5351a90892599a7b3fed5904` | 2 |
| `KaiTi_GB2312.ttf` | `99092cbb0df301625f46509e85854db8685556551742097ab3fbbc2e2ca0778b` | 0 |
| `simfang.ttf` | `fef7cf991b458cabd184b73378918d9d15429010e1d6c804f08d394395c3c3b4` | 0 |

原版式仍使用仿宋_GB2312、楷体_GB2312、方正小标宋简体，黑体及宋体页码、Times New Roman数字/英文规则保持。脚本继续查找本机已安装字体或仓库外 `ICDAFY_FONT_DIR` 授权目录，不自动加载或安装这些历史副本，不从网络下载字体。

从技能根运行 `python scripts/skill_portability.py check --smoke`。`ensure_fonts.py` / `font_preflight.py` 的 `--check` 只检测；缺字体明确提示。允许嵌入的本机授权字体按fsType处理；方正fsType=2仍拒绝嵌入。缺字体或未做实际渲染时不能宣称最终版式通过。

仅保留原三份，不新增、改名或替换字体；统一校验按索引中的原18个路径与摘要检查，递归拒绝ZIP及文档里的字体资源。
