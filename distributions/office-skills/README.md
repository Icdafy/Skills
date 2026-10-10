# 办公及投后四技能下载

每个 ZIP 第一层只有该英文技能目录，包含独立脚本、参考、模板、README、LICENSE、NOTICE、VERSION 和逐文件 SHA-256 manifest。不包含字体二进制、用户私有术语或模型。

<!-- skills:begin -->
### 公文与会议

| 技能 / 做什么 | 源码 | 说明与调用 | 下载 | 版本 |
|---|---|---|---|---|
| 国企公文写作与排版（`officialese-skill`） | [源码](../../officialese-skill/) | [README](../../officialese-skill/README.md) | [ZIP](officialese-skill.zip) | 1.0.2 |
| 投委会议题（`yiti-skill`） | [源码](../../yiti-skill/) | [README](../../yiti-skill/README.md) | [ZIP](yiti-skill.zip) | 1.0.2 |
| 会议转录与正式纪要（`meeting-minutes-pro`） | [源码](../../meeting-minutes-pro/) | [README](../../meeting-minutes-pro/README.md) | [ZIP](meeting-minutes-pro.zip) | 1.0.3 |

### 投后管理

| 技能 / 做什么 | 源码 | 说明与调用 | 下载 | 版本 |
|---|---|---|---|---|
| 国企股权投资投后报告（`soe-post-investment-report`） | [源码](../../soe-post-investment-report/) | [README](../../soe-post-investment-report/README.md) | [ZIP](soe-post-investment-report.zip) | 1.5.6 |
<!-- skills:end -->

解压后在技能根运行 `python scripts/skill_portability.py check --smoke`；按各 README 安装所需依赖及本机授权字体，使用项目目录安装后新建会话验证。下载包结构检查不能代替客户端模型调用。

维护者在仓库根运行 `python tools/package_skills.py --skill <英文名>` 只重建对应 ZIP，`python tools/package_skills.py --check` 检查全部包。见 [维护说明](../../docs/maintenance.md)、[许可来源](../../THIRD_PARTY_NOTICES.md) 和 [实际验证](../../docs/validation.md)。
