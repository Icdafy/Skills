# 验证摘要

当前维护入口是 `python tools/check_library.py`，检查七项技能、资源、版本、独立ZIP、11组共享副本、本地链接、许可文件和18份源码字体摘要。具体测试命令见 [维护说明](maintenance.md)，字体清单见 [source-fonts.json](source-fonts.json)。

## 本次清理

2026-10-05，清理621份历史测试输出、模型调用日志、迁移映射和执行记录；字体摘要迁到 `docs/source-fonts.json`，索引和说明改为指向本页。跟踪文件由911个减至290个，减少68.17%。七项技能的源码、模板、字体、版本及下载包保持原内容。

本次 Windows / Python 3.12.10 实测：原五组375项回归加17项字体契约，共392项，391通过、1项因既有Windows符号链接权限跳过、0失败。字体契约首次运行遇到两个中文输出编码错误，设置测试进程 `PYTHONIOENCODING=utf-8` 和 `PYTHONUTF8=1` 后17项全通过，未修改测试断言。统一校验通过，七包与源码一致、11组共享副本一致、18份字体摘要不变、本地断链为0；Git差异检查通过。原始输出保留在本地工作目录。

后续测试输出放本地 `work/validation/`，不提交。一项已经完成的历史迁移不再要求永久保留其逐文件映射；当前必需资源、包一致性和字体检查继续执行。

## 历史实测范围

以下是清理前的实测记录，本次没有重新调用模型、转写语音或进行 Word 视觉验收。

| 范围 | 已记录的结果及限制 |
|---|---|
| 原五组回归测试 | 375项：374通过，1项因Windows符号链接权限跳过；另17项字体契约测试通过 |
| 分发与安装 | 七个独立ZIP仓库外烟测通过；项目安装、备份和纪要私有术语保留通过 |
| Codex CLI 0.160.0 | 21个新会话路由21/21；严格首轮行为18/21。投后三例四问正确，但另含进度或依据说明 |
| 会议纪要文本 | 虚构素材生成的文本通过四项检查；仍是草稿，未完成DOCX或音频回听 |
| ASR | 13.675秒中文合成音频：FunASR离线CUDA通过、Qwen3-ASR 0.6B离线CPU通过；Qwen CUDA尝试失败。真实会议、长音频、方言和说话人分离未实测 |
| Word字体探针 | 共同组与纪要组的阴性/阳性探针通过；不能替代全部业务文档逐页验收 |
| 其他客户端 | Claude Code项目目录安装通过，模型调用未实测；其他客户端未实测 |
| 字体 | 原18份源码字体保留原路径和字节；单技能ZIP和安装器排除字体，公开再分发授权未确认 |

## 原始证据

历史文件仍保存在清理前的固定提交 `0a15cc20451414f1506d4f7fe4e8bba8939af875`，没有重写 Git 历史。

- [全部历史原始输出](https://github.com/Icdafy/Skills/tree/0a15cc20451414f1506d4f7fe4e8bba8939af875/docs/validation)
- [最后复查及回归、安装结果](https://github.com/Icdafy/Skills/blob/0a15cc20451414f1506d4f7fe4e8bba8939af875/docs/validation/final-review-20261005/README.md)
- [21个Codex会话摘要及原始输出入口](https://github.com/Icdafy/Skills/blob/0a15cc20451414f1506d4f7fe4e8bba8939af875/docs/validation/clients/codex/summary.json)
- [历史字体测试契约](https://github.com/Icdafy/Skills/blob/0a15cc20451414f1506d4f7fe4e8bba8939af875/docs/font-test-contract.md)

来源与许可继续以 [第三方清单](../THIRD_PARTY_NOTICES.md) 为准。历史实测只证明当时受测范围，不能用脚本检查代替客户端调用、实际ASR或视觉验收。
