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

## 续跑补审的资源提示修正依据

2026-10-05，第2轮后逐项检查实际说明发现旧字体宣传遗漏。`officialese-skill/scripts/create_official_docx.py` 和 `yiti-skill/scripts/create_yiti_docx.py` 的缺字体stderr仍提示“从技能自带字体安装”，而源码和ZIP已经移除字体。只将这一处提示改为 `--check` 检测本机字体，缺失时自行准备授权文件并设置ICDAFY_FONT_DIR；不改生成器分支、排版、字体名称、输入用例或断言。

冻结审计将如实记录这两个文件字节不再完全相同，且要求仅这一条提示的精确新旧字面量归一后全文等于基线；其他六个业务渲染/规约文件仍要求字节相同。旧375项及新增13项不调整、不减数。另以现有临时SFNT资源和空目录实际调用两个CLI验证有资源/缺资源两种情况，保留生成文件检查和stderr原输出；不mock功能，不将结构测试冒充真实Word视觉验收。README/SKILL/reference与共享embed文档字符串只修正字体来源，不改变业务规则。

## 最新原main字体保留要求

维护者授权将PR其余内容合入main，但保留原18份字体的路径和字节。原375项和新增13项资源契约测试继续不改：安装/ZIP仍排除字体，运行时仍使用本机授权资源。另增加4项实物保留与排除测试，检查原摘要、实际打包、不许修改原文件及新增字体；不放宽字体槽、字号、页脚、版式或业务断言。选择性合并的验证独立登记，不改写此前三轮记录。
