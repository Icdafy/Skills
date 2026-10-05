# 完成条件逐项审计

审计依据当前工作树、第3轮原输出、最终七包及真实客户端证据。完整验收已满3轮，停止修改实现。原skills/布局由维护者最新根目录要求覆盖。

整项完成尚未证实：投后严格首轮只四问未通过，最终人工浏览未收到确认。以下逐项列证据及范围，不把测试通过或文件存在当成模型调用/视觉验收。

| 具体要求 | 结论 | 权威证据与范围 |
|---|---|---|
| 任务0版本/权限/解释器/基线 | 已证实 | [远端基线bf6f7d8、push权限、实际Python3.12.14；原375及逐名/跳过/字体摘要已存](validation/baseline/summary.json) |
| 核对后先给≤10行开工回执 | 已证实 | [原线程实际消息7行，目标/顺序/风险齐全；不能事后改写为未说过的话](validation/task0-receipt.json) |
| 七SKILL.md识别及唯一来源索引 | 已证实 | [稳定ID、中文名/类别、根目录源码、版本、README/ZIP与验证状态齐全；根目录是维护者最新授权](../skills-index.json) |
| 全部原跟踪文件映射、不丢失 | 已证实 | [237逐项，19解释删除；只限18受限字体及空白占位物](migration-map.json) |
| 七项README完整并可独立使用 | 已证实 | [逐项亲读且七种必需段落检查通过；本技能安装/调用/升级、依赖及验证边界均有](../README.md) |
| 中文首页7/7分类/源码/说明/下载及顶层用途 | 已证实 | [首页实际表、七根目录与11顶层目录用途；sync_catalog由索引生成技能表](../README.md) |
| 索引/源码/插件/ZIP集合一致、唯一名称、必需资源及断链 | 已证实 | [统一入口亲跑0，集合7、共享11、迁移237、缺文件0/断链0；四类反向检测](validation/round-3/library.txt) |
| 修复资源及安装/调用入口，不保留双源码 | 已证实 | [七个根目录；客户端.agents/.claude安装路径保留；ZIP第一层仍单技能英文名，旧PR路径有迁移说明](installation.md) |
| 旧维护命令及原下载目录/ZIP名保留 | 已证实 | [旧package_investment_skills.py --check退出0，原两下载目录七包保留](validation/round-3/legacy-package-command.txt) |
| 单技能版本/变更及精准重建 | 已证实 | [临时仅修改yiti，重建只变其包、另六摘要不变；本次六包受影响，投后包未变](validation/font-guidance/distribution/single-skill-hashes.json) |
| 维护顺序/共享canonical物理副本 | 已证实 | [源码→canonical→sync→验证→只打受影响包；11组一致，不跨技能import或符号链接](maintenance.md) |
| 纪要专用embed不误同步 | 已证实 | [索引五技能embed明确排除meeting；纪要专用版本独立验证](validation/round-3/shared.txt) |
| 原模板/版式/事实/语言/阶段规则保留 | 已证实 | [38原脚本/47参考字节相同，资源变更23脚本/11参考逐项审查；15素材、6渲染器相同，2仅精确提示字面量](validation/font-guidance/business-content-audit.json) |
| 旧375方法/断言/装饰器保留；不新增skip/todo/mock/吞失败 | 已证实 | [原25文件375名/断言/装饰器审计通过，13资源契约正负覆盖；错误探针和行为失败如实保留](validation/frozen-content.json) |
| 五组实际回归及同一Windows跳过 | 已证实 | [50/258/56/8/3=375，374通过、WinError1314同一文件符号链接跳过1；另13通过](validation/round-3/summary.json) |
| 七包仓库外中文空格解压/运行 | 已证实 | [7/7最终包绝对路径check --smoke退出0，PYTHONPATH清除](validation/font-guidance/distribution/summary.json) |
| 项目安装备份和本地数据保留 | 已证实 | [七项预览不写/安装/默认停止/replace/备份通过；纪要私有词库保留，真实全局安装未覆盖](validation/font-guidance/distribution/summary.json) |
| Apache-2.0/署名/第三方来源与授权 | 已证实 | [维护者直接确认原素材有权授权；原许可/署名保留，未称外部素材原创；第三方授权待决0](../THIRD_PARTY_NOTICES.md) |
| 受限字体源树/ZIP/嵌入资源为0 | 已证实 | [原18摘要+后缀/签名递归ZIP/OOXML/CFB扫描0；旧历史/旧发布未删/重写](validation/round-3/library.txt) |
| 本机字体检测/使用与缺资源明确提示 | 已证实且边界已标 | [真实CLI正负4次：两字体/charset86与空目录草稿提示；新系统未安装提示分支未触发，仅精确字面量审计，不冒称实测](validation/font-guidance/summary.json) |
| 可用客户端新会话显式/自然/相邻反例 | 已证实且失败已标 | [CLI0.160.0，21新会话实际提示/读取路径/结果；路由21/21，严格行为18/21；Claude/其他客户端未实测](validation/clients/codex/summary.json) |
| 三个立项技能不串路由 | 已证实 | [显式/自然/相邻反例实际读取正确技能，先问阶段](validation/clients/codex/summary.json) |
| 投后首轮只能四问 | 未达标 | [三个涉及投后的会话都有额外进度/依据说明；原规则已要求四问，不修改冻结规则或客户端指令体系](validation/clients/codex/behavior-review.txt) |
| 纪要文本真实生成 | 已证实且草稿边界已标 | [真实新会话文本2完整QA/3窗/24数字，四检查0；draft/release_ready:false，不称DOCX或录音回听完成](validation/clients/codex/minutes-text/summary.json) |
| 真实语音引擎验证程度 | 已证实且未测边界已标 | [既有FunASR/Qwen0.6短合成语音离线推理；Qwen CUDA1、CPU0；真实长会/方言/分离/全量回听未实测](validation/asr/summary.json) |
| 实际字体嵌入效果 | 已证实限定范围 | [共享组与纪要组真实Word阴性/阳性探针；不替代全部业务文档逐页视觉验收](validation/word-embedding/meeting-minutes-pro.txt) |
| 统一入口实现亲跑后登记维护文档 | 已证实 | [tools/check_library.py先实际运行0后登记；路径/许可规则及模型验证边界写清](maintenance.md) |
| 四项反向红→绿实跑 | 已证实 | [缺资源、插件路径、旧ZIP、改名.bin字体各exit1；精确恢复后exit0](validation/font-guidance/distribution/summary.json) |
| 不新增依赖/服务/模型下载、单agent及白名单 | 已证实 | [单agent、现有Python/Word/ASR及缓存；临时材料在work和具名系统临时路径；最终暂存白名单复核后提交](validation/font-guidance/business-content-audit.json) |
| 不改main/权限/历史/强推/旧发布 | 已证实本次操作 | [普通分支push和草稿PR；remote main持续bf6f7d8，未执行禁止动作；用户旧工作区未改](../PROGRESS.md) |
| 失败3次换独立项、最多3轮验收 | 已证实 | [投后三例失败后停止；完整轮1/2/3均有原输出，满3后只记录/提交，不继续修实现](../PROGRESS.md) |
| 维护者最后浏览首页/7README/维护说明 | 缺少证据 | [已收到布局反馈并落实；最新最终浏览请求未收到答复，GitHub reviews/comments为空](../BLOCKED.md) |
| PR/分支或补丁、交付记录与BLOCKED | 已交付 | [本轮实况已普通push同一草稿PR #12；亲读OPEN/DRAFT、分支一致及main原基线；只补交付回执，不自动合并](validation/font-guidance/published-followup.json) |

结构化记录与goal阻塞轮次见 [审计JSON](validation/completion-audit.json)。当前已观测两个goal轮出现同一B2/B3，不能现在提前置blocked；下一连续goal轮仍无外部变化且无法继续时按规则置blocked。
