# 取消字体分发时的测试契约调整（先列依据）

2026-10-05，在修改字体相关旧测试前登记。用户要求不公开分发受限字体，并允许仅为此调整资源契约测试；必须保留等量有效正负覆盖，不放宽版式断言。

依据：基线 `gongsi-qingkuang/assets/fonts/README.md`、`hangye-fenxi/assets/fonts/README.md` 明示商用/系统字体“请勿再分发或公开”。18 个副本只有 3 个不同 SHA-256，见 [字体摘要](validation/baseline/restricted-fonts.json)。fsType=0 仅是嵌入标志，不能据此推断整份字体可随源码公开再分发。

原测试的字体输入指向 `assets/fonts/*.ttf`，删除该输入后应改为测试临时目录；不删除测试，不修改文档字号、字体槽、页边距、页脚、表格或事实规则。

| 原文件 | 涉及旧测试 | 调整 |
|---|---|---|
| tools/tests/test_sibling_docx_skills.py | 三个 BundledFontResolution、一个 Obfuscation、两个 GeneratorEmbedding，共 6 项 | 临时目录提供由 stdlib 生成的 SFNT/OS2 数据；仍检查 GB2312 charset、fsType 拒绝、完整反混淆、生成器 CLI 的两字体嵌入与验证 |
| meeting-minutes-pro/tests/test_embed_fonts.py | 三个 FsTypeGate、一个可读 FontDescriptor、三个 EmbedIntoDocx，共 7 项 | 相同测试数据替代随包文件；仍保留原名、原 fsType/charset/部件/settings 断言和实际 DOCX 写入 |

测试数据只含手工构造的 SFNT 表头、OS/2 标志与字符集字段，没有字体字形或第三方字节；用于测试解析/嵌入算法，不能拿来声称 Word 渲染通过。用真实环境变量 `ICDAFY_FONT_DIR` 提供该目录，实际执行被测查找、fsType、反混淆、DOCX 写入及生成器，不 mock 被测功能。

另在 `tools/library_tests/` 增加 13 项成对有效正负测试，对应 13 个受影响旧用例：可用/缺失本机资源、可嵌入/受限标志、字符集/无表、完整/损坏反混淆、成功/缺资源 CLI、带/不带字体部件。原五组测试的发现数量仍为 50、258、56、8、3。真实授权本机字体另做运行和渲染证据，不把结构测试代替视觉检查。
