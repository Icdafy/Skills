# 本机授权字体

公开源码和 ZIP 不包含字体二进制。原随包字体为受版权保护的商用/系统字体，原说明禁止公开再分发；fsType 允许嵌入不表示允许分发整份字体。

原版式仍要求仿宋_GB2312（simfang.ttf）、楷体_GB2312（楷体_GB2312.ttf 或 KaiTi_GB2312.ttf）、方正小标宋简体（方正小标宋简体.ttf 或 FZXiaoBiaoSongJT.ttf）。请自行取得授权并安装；也可把授权文件放到仓库外目录，设置 `ICDAFY_FONT_DIR` 后供脚本查找。不要把字体复制回公开库。

从技能根运行 `python scripts/skill_portability.py check --smoke`。原有 ensure_fonts.py / font_preflight.py 的 `--check` 仅检测本机；缺失时会提示。授权文件的用户级安装需显式准备目录并确认，脚本不从网络下载字体。缺字体时正式交付必须重新检查实际显示；保留草稿不能冒称最终版式验证通过。
