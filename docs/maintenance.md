# 维护与精准升级

七项唯一源码直接位于仓库根目录 `<英文名>/`，集合、路径、版本、分发目录和共享组统一定义在 `skills-index.json`。在各英文技能目录改源码，不编辑解压出的 ZIP；不把 tools/、distributions/、插件配置当技能。

## 改哪份 → 同步什么 → 验证 → 打哪个包

1. 只改一个技能的非共享文件：改该技能源码，更新它的 VERSION、CHANGELOG.md、索引 version，以及 SKILL.md 中已有的 metadata.version。业务模板、版式和事实规则的升级另做，本次没有扩写。
2. 改共享文件：先在索引 shared_groups 指定的 canonical 技能中改基准，然后 `python tools/check_shared_scripts.py --sync`。同步后所有该组成员的版本和变更记录都更新。脚本物理副本必须保留，不能跨技能 import 或用符号链接代替。
3. `python tools/sync_catalog.py` 从索引更新中文首页、下载说明及插件市场；`--check` 只校验，不改文件。
4. 跑受影响测试及各技能 `scripts/skill_portability.py check --smoke`。共享排版脚本变化时还需原五组完整回归和实际字体渲染证据；元数据/包检查不能充当模型调用证据。
5. `python tools/package_skills.py --skill <英文名>` 只重建该技能 ZIP 和 SHA-256；重复 `--skill` 处理多个成员。`python tools/package_skills.py --check` 检查全部 ZIP 及逐文件 manifest。
6. 验证通过后在独立分支提交、发可审查 PR。main 首页和新版技能内容在合并后生效，不自动合并。

共享组的文件、基准、成员以 [索引](../skills-index.json) 的 `shared_groups` 为准。原十组保留，新增 `local_fonts.py` 第十一组只负责本机字体查找。`meeting-minutes-pro/scripts/embed_fonts.py` 由自己的 format_spec.py 驱动，明确不属于五技能 embed_fonts 同步组；不得用其他技能的字体脚本覆盖它。

## 单技能例子

修改 `yiti-skill/references/writing-logic.md` 后，在库根运行：

```powershell
python tools/sync_catalog.py
python tools/check_shared_scripts.py
python tools/package_skills.py --skill yiti-skill
python tools/package_skills.py --check
```

其他六个 ZIP 的 SHA-256 应保持不变。如果改的是五技能共享的 ensure_fonts.py，则按索引将五个成员分别传给 `--skill`；不要为了省事始终重打全库。旧 `python tools/package_investment_skills.py` 命令保留，只处理立项三技能，支持 `--check`。

## 原五组测试与证据

```powershell
python -m unittest discover -s tools/tests
python -m unittest discover -s meeting-minutes-pro/tests
python -m unittest discover -s soe-post-investment-report/tests
python -m unittest discover -s gongsi-qingkuang/evals
python -m unittest discover -s officialese-skill/scripts -p test_create_official_docx.py
python tools/check_shared_scripts.py
python tools/package_skills.py --check
git diff --check
```

原五组375个测试及文档版式断言保留。`tools/library_tests` 另含17项字体资源契约测试，字体原路径、大小和摘要以 [源码字体清单](source-fonts.json) 为准。结果与未实测范围见 [验证摘要](validation.md)。

统一校验入口已经实际跑通（退出 0）后登记：

```powershell
python tools/check_library.py
python -m unittest discover -s tools/library_tests
```

`check_library.py` 只读检查当前技能集合、唯一名称、索引/首页/插件/ZIP、必需资源、版本、本地 Markdown 链接、许可文件、字体摘要，以及 ZIP/OOXML/CFB 中的字体资源。不联网、不重建、不写入安装目录。已经完成的旧目录迁移不再作为每次校验的前置条件；历史映射保存在 Git 历史中。

测试原始输出、模型调用日志和安装试验材料放在本地 `work/validation/`，不提交。`docs/validation.md` 只维护简短结论、受测范围及历史提交入口；`docs/source-fonts.json` 是仍用于校验的18份源码字体摘要，需保留。旧日志目录和执行记录已加入 `.gitignore`，避免再次堆积。

## 分发前许可与资源核对

README、LICENSE、NOTICE、VERSION 和 CHANGELOG 必须随单技能包分发。根 [第三方清单](../THIRD_PARTY_NOTICES.md) 保留来源与维护者授权确认；不以 fsType 或上传作者推断公开分发许可。

运行时本机授权字体放仓库外目录，可设置 ICDAFY_FONT_DIR。维护者最新要求保留原main18份源码字体：仅索引font_policy列出的原路径和摘要可保留，禁止新增、改名或替换；单技能ZIP和安装器始终排除字体。GitHub整库源码下载仍含原字体，公开再分发授权未确认。字体缺失要明确提示；未完成实际渲染/页数闭环的 DOCX 仍是草稿。旧历史与旧发布不删除、不重写。私有术语和参考渲染缓存按 .gitignore 与打包规则排除。
