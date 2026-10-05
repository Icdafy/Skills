# 立项报告三技能下载

每个 ZIP 第一层只有该英文技能目录，包含独立脚本、参考、模板、README、LICENSE、NOTICE、VERSION 和逐文件 SHA-256 manifest。不包含字体二进制、用户私有术语或模型。

<!-- skills:begin -->
### 立项报告

| 技能 / 做什么 | 源码 | 说明与调用 | 下载 | 版本 |
|---|---|---|---|---|
| 所属行业分析（`hangye-fenxi`） | [源码](../../hangye-fenxi/) | [README](../../hangye-fenxi/README.md) | [ZIP](hangye-fenxi.zip) | 1.0.0 |
| 主营业务分析（`zhuying-yewu-fenxi`） | [源码](../../zhuying-yewu-fenxi/) | [README](../../zhuying-yewu-fenxi/README.md) | [ZIP](zhuying-yewu-fenxi.zip) | 1.0.0 |
| 公司情况（`gongsi-qingkuang`） | [源码](../../gongsi-qingkuang/) | [README](../../gongsi-qingkuang/README.md) | [ZIP](gongsi-qingkuang.zip) | 2.0.1 |
<!-- skills:end -->

解压后在技能根运行 `python scripts/skill_portability.py check --smoke`；按各 README 安装所需依赖及本机授权字体，使用项目目录安装后新建会话验证。下载包结构检查不能代替客户端模型调用。

维护者在仓库根运行 `python tools/package_skills.py --skill <英文名>` 只重建对应 ZIP，`python tools/package_skills.py --check` 检查全部包。见 [维护说明](../../docs/maintenance.md)、[许可来源](../../THIRD_PARTY_NOTICES.md) 和 [实际验证](../../docs/validation.md)。
