# Skills 军团

面向一级市场股权投资与投研工作流的通用 Agent Skills 技能库，可供支持或可导入 `SKILL.md`/Agent Skills 包结构的 Claude、Codex、ChatGPT、WorkBuddy、Trae、Qoder 等智能体复用；具体导入方式、能力与中文显示名称以各客户端版本为准。按用途分为两类：**立项报告章节生成**（以资深投资经理视角，把项目资料包炼成客观、审慎、证据可追溯的报告正文）与**通用办公工具**（投后报告、纪要、公文、PPT、转写）。

## 立项报告章节生成

以四十年经验的一级市场投资经理视角，基于项目资料包（BP、尽调材料、财务、股权、行业研报等）输出面向投委会的正式章节：数据有据、语言审慎、优势与风险同台、可 DOCX 公文排版输出。按立项报告章节顺序：

| 技能 | 对应章节 | 说明 |
| --- | --- | --- |
| [hangye-fenxi](hangye-fenxi/) | 所属行业分析 | 行业定义、产业链、市场规模、竞争格局、政策技术趋势与行业投资判断 |
| [zhuying-yewu-fenxi](zhuying-yewu-fenxi/) | 主营业务分析 | 12 维度覆盖、数据有据、语言审慎的业务分析正文（含表格、指标计算与风险提示） |
| [gongsi-qingkuang](gongsi-qingkuang/) | 公司情况 | 以初步尽调视角，把尽调资料包＋会议纪要＋联网检索炼成工商主体、股权结构与实控人、核心团队、组织人员、知识产权资质、子公司、融资估值、财务快照与合规风险的证据链正文（含三角验证矩阵、红旗模式库、语言红线与待核查清单）；详见文件夹内 README |

## 通用办公工具

| 技能 | 说明 |
| --- | --- |
| [soe-post-investment-report](soe-post-investment-report/) | 国企股权投资投后报告：先通过固定四问确认项目变动与修改重点，再从项目资料建立证据台账、交叉核验并更新固定正文框架，生成正文通常 5—6 页且不超过 10 页的正式上行文 DOCX；附件承载项目明细，内置结构、编号、事实引用与启发式公开安全校验 |
| [meeting-minutes](meeting-minutes/) | 会议纪要/访谈纪要整理：将会议、访谈、尽调访谈、路演问答的原始记录转为正式中文纪要，支持公文排版 Word 输出 |
| [officialese-skill](officialese-skill/) | 国企公文写作与排版：通知、请示、报告、函等公文的起草、改写与 DOCX 版式（字体、页边距、标题、落款、页码） |
| [yiti-skill](yiti-skill/) | 投委会议题撰写：根据参股企业股东会/基金合伙人会议的通知及议案，按固定骨架（导语、会议基本信息、会议审议事项、请示事项、附件）生成核心结论前置、依据可追溯的议题正文与公文排版 DOCX |
| [ppt-to-editable](ppt-to-editable/) | 幻灯片图片转可编辑 PPTX：对单页 PPT 截图/导出图做 OCR 复核与原生形状重建 |
| [rw-consulting-ppt](rw-consulting-ppt/) | 咨询级图片型 PPT 生成：将要点、笔记、研究结论转为整页 PNG 或纯图 PPTX 的报告展示页 |
| [meeting-minutes-pro](meeting-minutes-pro/) | 本地音视频转写＋正式会议纪要一体化：FunASR/Qwen3-ASR 双引擎、数小时长音频、说话人分离、热词术语库；自动采集会议基本信息，识别并保留 QA 问答，数字逐项对照转录稿核验，公文版式 DOCX 输出并渲染检查；详见文件夹内 README |
| [sound-transcribe](sound-transcribe/) | 音视频转写：本地 faster-whisper 转写音频/视频为文本、时间戳、SRT 字幕与逐字稿 |

## 仓库维护工具

| 工具 | 说明 |
| --- | --- |
| [tools/check_shared_scripts.py](tools/check_shared_scripts.py) | 校验跨技能共享脚本的多份副本是否一致，防止静默漂移。技能自包含、可独立分发，故不能跨技能 import，`build_docx.py`（立项三技能）与 `embed_fonts.py`（五个公文技能）必须各自留物理副本。改动流程：改 `gongsi-qingkuang` 下的基准副本 → `python tools/check_shared_scripts.py --sync` 同步 → 提交前 `python tools/check_shared_scripts.py` 校验（漂移即退出码 1）。 |
| [tools/verify_embedding_with_word.py](tools/verify_embedding_with_word.py) | 决定性验证「嵌入 DOCX 的字体真的被渲染器使用」。把随附字体内部名改成本机未安装的名字再排版，带阴性对照：不嵌入必须回退系统字体，嵌入后必须不回退。单元测试只能断言 fontTable 写了 `w:charset`，证明不了渲染器会采用——这个盲区曾让一版"看起来成功、实际无效"的实现通过全部校验。改动任何 `embed_fonts.py` 后建议跑一次：`python tools/verify_embedding_with_word.py --skill <技能> [--renderer word\|libreoffice]`。 |
| [tools/tests/](tools/tests/) | 五个公文 DOCX 技能的仓库级回归测试（以子进程调各技能 CLI，避免同名 `embed_fonts` 串味）：`python -m unittest discover -s tools/tests`。 |

---

各技能文件夹内含 `SKILL.md`（触发与执行逻辑）及 `references/` 等配套资源；详细说明见各文件夹内 README（如有）。
