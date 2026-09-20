# 立项报告技能安装包

每个ZIP为一项完整技能，包含独立运行所需的规则、参考文件、Python脚本、依赖说明和原技能字体资源。用于现有授权范围内的跨客户端安装。

| 技能 | 安装包 | 完整性校验 | 分平台安装指引 |
|---|---|---|---|
| 所属行业分析 | [hangye-fenxi.zip](https://github.com/Icdafy/Skills/raw/refs/heads/main/distributions/investment-report-skills/hangye-fenxi.zip) | [SHA-256](hangye-fenxi.zip.sha256) | [指引](../../hangye-fenxi/references/agent-compatibility.md) |
| 主营业务分析 | [zhuying-yewu-fenxi.zip](https://github.com/Icdafy/Skills/raw/refs/heads/main/distributions/investment-report-skills/zhuying-yewu-fenxi.zip) | [SHA-256](zhuying-yewu-fenxi.zip.sha256) | [指引](../../zhuying-yewu-fenxi/references/agent-compatibility.md) |
| 公司情况 | [gongsi-qingkuang.zip](https://github.com/Icdafy/Skills/raw/refs/heads/main/distributions/investment-report-skills/gongsi-qingkuang.zip) | [SHA-256](gongsi-qingkuang.zip.sha256) | [指引](../../gongsi-qingkuang/references/agent-compatibility.md) |

WorkBuddy、Kimi Work、Claude桌面Chat、Qoder桌面、TraeCode按指引走技能导入入口；CLI及目录型客户端可用随包 `scripts/skill_portability.py install`。Kimi在线Agent等产品能力有差异，详见对应指引，不将普通文件上传等同安装。

解压后在技能目录执行：

```bash
python scripts/skill_portability.py check
python -m pip install -r requirements.txt
python scripts/skill_portability.py check --smoke
```

需要Python 3.10+。安装后还须在目标客户端确认启用、实际加载路径、自动路由与输出；包及脚本检查通过不等于所有客户端模型调用已经实测。说明依据各平台官方文档（2026-09-20），未提供逐客户端登录验收结果。

维护者更新任一技能后，在仓库根目录同步和重打包：

```bash
python tools/check_shared_scripts.py --sync
python tools/package_investment_skills.py
python tools/package_investment_skills.py --check
```

`--check` 对比包内清单、每个文件及ZIP本身的SHA-256，发现漏文件、包损坏或源码与安装包不同步即失败。安装包以技能名为唯一顶层目录，不打入缓存、虚拟环境或Git仓库。
