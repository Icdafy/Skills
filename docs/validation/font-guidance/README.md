# 字体资源说明补审

第2轮后逐项阅读实际资源说明，发现旧自带/下载字体宣传遗漏。仅修正授权来源、准备步骤、共享嵌入器文档字符串与两条CLI提示；字体名称、版式和业务规则不改。

- [逐项替换](replacements.json)；六项CHANGELOG各自记录实际变更。
- [活跃说明旧宣称命中0](documentation-claims.json)。保留旧兼容函数名，不把函数名误当仍分发字体。
- [实际正负资源结果及六包前后摘要](summary.json)：四CLI退出0，阳性嵌入两字体/charset86，阴性无字体部件且明确保留草稿；只重建六包，投后包不变。
- [当前冻结审计](../frozen-content.json)：原375名/断言保留，15素材字节相同；6渲染/规约文件相同，2仅精确提示字面量改变，其他全文与基线相同。
- [原探针失败](failed-probe.txt)：错误要求本机未安装的stderr分支出现，但本机三字体已注册。原失败及CLI输出保留，未改旧断言、mock注册表或安装字体；该提示分支未实测，仅有精确源码差异证明。
- [系统字体检查](system-font-check.txt) 实际退出0。测试临时SFNT只有结构字段，无第三方字形；不把它当Word视觉验收。

原模型调用和ASR证据保留，不宣称此次重复实测。[最后第3轮](../round-3/summary.json)12条命令全部退出0，已满3轮并停止修改实现；[最终分发/备份/反向验证](distribution/summary.json)53条命令均符合预期。未达项见 [BLOCKED.md](../../../BLOCKED.md)。

Git差异含单空格空白上下文行，直接提交会被diff --check报告行末空白（实际退出2）。font-reference-diff.txt及staged-whitespace-last.txt是标出行末空白的可读视图；对应*.raw.json保存精确UTF-8文本、Base64原始字节和SHA-256，已经解码逐字节验证，不删改失败证据。此处仅是证据格式处理。
