# 来源与许可清单

授权核对日期：2026-10-05（Asia/Shanghai）。

根 LICENSE 为 Apache-2.0。原代码、自编规则、模板、范文及素材由维护者确认有权授权；
没有把 Git 上传者推断为素材原创作者。既有署名和 LICENSE 保留，新增维护代码同样按 Apache-2.0。

## 原模板、范文及素材

维护者在本任务中针对下列素材答复：“全部由我有权授权，可按 Apache-2.0 公开”。
原件保持基线字节；表中提交是仓库引入/最近历史证据，不冒称外部来源证明。

| 原文件/素材范围 | 来源记录 | SHA-256 或盘点 | 分发许可依据 |
|---|---|---|---|
| `meeting-minutes-pro/assets/templates/文件字体格式.doc` | 6149206 2026-07-15 Kuangdi Liu | `5a781e07ee839c7b7d293134914fb86c4e6733793152e367d3cb26422b4c3925` | 维护者确认有权授权，Apache-2.0 |
| `officialese-skill/assets/templates/文件字体格式.doc` | c414f96 2026-06-08 Kuangdi Liu | `5a781e07ee839c7b7d293134914fb86c4e6733793152e367d3cb26422b4c3925` | 维护者确认有权授权，Apache-2.0 |
| `soe-post-investment-report/assets/preview.png` | b6b129d 2026-08-30 Kuangdi Liu | `b0e9abb903238ac8d5964ab57ae7844f4db3938eac7450e73d08007332908ae5` | 维护者确认有权授权，Apache-2.0 |
| `soe-post-investment-report/assets/reference-template.docx` | 65e0d90 2026-09-02 Kuangdi Liu | `4165afc2cb84cf81899b8d59c0e984ac035cf498fa9726b20047beba573b2790` | 维护者确认有权授权，Apache-2.0 |
| `yiti-skill/assets/templates/文件字体格式.doc` | beee0c1 2026-07-13 Icdafy | `5a781e07ee839c7b7d293134914fb86c4e6733793152e367d3cb26422b4c3925` | 维护者确认有权授权，Apache-2.0 |
| 立项三技能 `assets/templates/*.json`、`references/template-*.md`、范文及业务参考 | 原文件迁移保留 | [历史迁移映射](https://github.com/Icdafy/Skills/blob/0a15cc20451414f1506d4f7fe4e8bba8939af875/docs/migration-map.json) | 维护者确认有权授权，Apache-2.0 |
| 七个技能其他规则、示例、行业术语与脚本 | 仓库既有提交，原署名保留 | [历史基线清单](https://github.com/Icdafy/Skills/blob/0a15cc20451414f1506d4f7fe4e8bba8939af875/docs/validation/baseline/tracked-files.json) | 维护者确认有权授权，Apache-2.0；会议纪要既有 LICENSE 保留 |

## 按维护者要求保留的原main字体

此前PR移除了18个字体副本；维护者最新明确要求原main字体不变。现在仅保留六技能各三份、共18份原文件，路径和字节摘要不变；没有新增黑体或其他字库。它们不适用本仓库Apache-2.0许可。授权限制来自基线两个字体README；
仿宋/楷体 fsType=0 不等于允许把整个字体公开再分发；方正小标宋 fsType=2 仍被嵌入器拒绝。
逐项文件名、大小、fsType 和 SHA-256 见 [源码字体清单](docs/source-fonts.json)。
原main18份源码字体逐字节保留，GitHub整库源码下载因此也包含它们。维护者先前明确没有或尚不清楚公开再分发授权；保留请求不视为字体版权方许可。单技能安装器和重建ZIP继续排除全部字体，递归文档嵌入扫描也不豁免字体。旧历史与旧发布没有重写或删除。

## 运行依赖（不打包其源码或模型）

| 组件 | 使用位置 | 来源 / 许可 |
|---|---|---|
| Python | 全部脚本 | [Python](https://docs.python.org/3/license.html)，PSF License |
| python-docx | DOCX 生成/验证 | [python-docx](https://github.com/python-openxml/python-docx/blob/master/LICENSE)，MIT |
| lxml | python-docx 间接依赖 | [lxml](https://github.com/lxml/lxml/blob/master/LICENSES.txt)，BSD 及依赖各自许可 |
| pypdf | 投后报告/纪要渲染与 PDF 读取 | [pypdf](https://github.com/py-pdf/pypdf/blob/main/LICENSE)，BSD-3-Clause |
| imageio-ffmpeg | 会议纪要音频工具（可选） | [imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg/blob/main/LICENSE)，BSD-2-Clause；FFmpeg 单独许可 |
| FunASR、ModelScope、PyTorch/torchaudio | 会议纪要语音（可选） | [FunASR](https://github.com/modelscope/FunASR/blob/main/LICENSE)、[ModelScope](https://github.com/modelscope/modelscope/blob/master/LICENSE)、[PyTorch](https://github.com/pytorch/pytorch/blob/main/LICENSE)；各自许可证/模型卡生效 |
| Qwen3-ASR / transformers | 会议纪要语音（可选） | [Qwen3-ASR](https://github.com/QwenLM/Qwen3-ASR)、[transformers](https://github.com/huggingface/transformers/blob/main/LICENSE)，依赖与实际模型卡分别核对 |
| Microsoft Word / LibreOffice / Poppler | 可选真实渲染 | 软件由用户自行安装，授权不由本库授予 |

没有下载或分发 ASR 模型。模型权重、用户私有术语、录音和文档的授权由其来源另行决定。
原18份字体的公开再分发授权未确认，字体不适用本仓库Apache-2.0许可。维护者已确认原模板/规则/素材权限；依赖和模型不随库分发。
