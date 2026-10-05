# 原main字体保留与PR选择性合并

维护者最新指示：“除了原main中字体文件不变以外（六技能各带三款字体，共18份），其余的所有内容全部合并在一起，只保留一个main”。本次据此恢复原18份字体的原路径和字节，保留PR其他内容，只调整与字体保留冲突的说明和安装/打包校验契约；业务规则与排版不扩写。

基线main：`bf6f7d8cfb99265fc55ee45da5ea54150fff876d`；此前PR：`dcc5ff4624a3ac4b60f04881d5b06d73b70bc82b`。字体清单仍以[原摘要](../baseline/restricted-fonts.json)和[索引](../../../skills-index.json)为准。公开再分发授权未确认；保留不等于Apache-2.0授权。单技能ZIP及安装器排除字体，GitHub整库源码下载包含原字体。

这属于维护者在原三轮止损后授权的合并工作。原三轮、375项、13项及真实客户端/ASR证据保留，不用本次脚本检查冒充模型重新调用。客户端实际输出和未实测范围保留在[验证记录](../../validation.md)，字体许可见[来源清单](../../../THIRD_PARTY_NOTICES.md)。

实际命令、退出码、18份字节审计及合并结果随执行写入此目录；执行前不标通过。

## 本次实际验证

- Python3.12.14；[十二条回归命令](acceptance/summary.json)全退出0。原五组50、258、56、8、3，375项完整保留，374通过；唯一原Windows符号链接用例因WinError1314跳过。原13项资源契约不改，另增4项源码保留/打包排除/改字节拒绝/新增路径拒绝测试，17项全部通过。
- [冻结审计](frozen-content.json)退出0：25个原测试文件375个名字/断言/装饰器保留，15素材及8渲染器保持既有冻结契约。[PR内容审计](pr-content-preservation.json)：679个PR原跟踪文件全部保留，159个代码/测试/参考/素材与此前PR等价，丢失0。
- [18份字体](original-fonts-unchanged.json)逐字节等于原main Git对象；原路径、大小、摘要和fsType不变。源码保留18份，单技能ZIP/安装器字体0。
- 完整回归后只补行业README中一条遗留字体来源说明和投后metadata版本引号匹配，未改运行代码或测试；按明确两个--skill重建这两包，[实际退出0](metadata-followup-rebuild.txt)。随后[最终57条分发/安装命令](distribution/summary.json)全符合预期：7/7仓库外中文空格目录smoke成功，预览不写、备份、本地材料与纪要私有词库保留通过；多余文件默认停止的退出1为预期结果。
- [临时只升级yiti](distribution/single-skill-hashes.json)：只变该ZIP，其他六个摘要不变，统一校验退出0。客户端和ASR本次没有重新调用，原21会话的严格四问失败继续保留。

| 故障 | 实际红结果 | 精确恢复后 |
|---|---|---|
| 缺必需模板 | [exit1：Missing resources](distribution/red-missing-resource.txt) | [exit0](distribution/green-missing-resource-restored.txt) |
| 错误插件路径 | [exit1：Marketplace differs](distribution/red-plugin-path.txt) | [exit0](distribution/green-plugin-path-restored.txt) |
| 过期ZIP | [exit1：ZIP is stale](distribution/red-stale-zip.txt) | [exit0](distribution/green-stale-zip-restored.txt) |
| 原字体改名.bin新增 | [exit1：Restricted font distribution](distribution/red-restricted-font-fingerprint.txt) | [exit0](distribution/green-restricted-font-fingerprint-restored.txt) |
| 修改允许保留字体字节 | [exit1：Retained source font changed](distribution/red-modified-retained-font.txt) | [exit0](distribution/green-modified-retained-font-restored.txt) |
| 删除允许保留字体 | [exit1：Retained source font missing](distribution/red-missing-retained-font.txt) | [exit0](distribution/green-missing-retained-font-restored.txt) |

以上是合并工作验证，原三轮记录没有重写；字体许可未解决，不宣称原开源发布目标全部完成。

## 已合并到唯一main

[PR #12](https://github.com/Icdafy/Skills/pull/12)已合并，合并提交`e2f8282f4fd8cae67cd64f5fd61a1977999e3400`；远端和本地均仅main，工作分支已删除。合并树等于受测PR树，原18字体在合并树及工作树逐字节等于bf6f7d8。[实际回执](merge-receipt.json)。随后只提交合并回执和当前状态说明，不改变技能、版本或ZIP。字体许可、严格首轮四问和最后浏览缺证仍保留。
