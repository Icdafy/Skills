---
name: yiti-skill
description: 撰写国企投委会议题（DOCX）：依据股东会、合伙人会议通知及议案撰写参会表决议题；依据投后资料、对赌回购条款、经营数据撰写项目退出、股权回购议题。用于“写投委会议题”“报送投委会”“提请投委会审议”，按公司公文版式排版。
---

# 议题 Skill（投委会议题撰写）

## 适用范围

Draft Chinese SOE investment-committee deliberation memos (投委会议题). Use when the user provides a 股东会/合伙人会议通知、议案、会议材料 and asks for a 投委会议题/审议议题/参会及表决事项议题, or provides 投后资料、对赌回购条款、经营数据 and asks for a 项目退出议题/股权回购退出议题/提前退出议题, or asks to 报送投委会/提请投委会审议. Covers 参股公司股东会、基金合伙人会议 and 已投项目退出（实际控制人回购、股权转让）, including full DOCX output with company officialese typography (方正小标宋简体标题、仿宋_GB2312正文、括号楷体_GB2312、Times New Roman数字、表格五号、页脚-1-四号宋体奇偶页).

Use this skill to draft 投管公司报送投委会的"议题"文书 and render it as a Word file. Two kinds of 议题 share one typography and one generator:

| 类型 | 输入 | 骨架与写法 | 范文 |
|---|---|---|---|
| A. 会议参会表决议题 | 被投企业/基金管理人发来的会议通知、议案、表决票 | `references/writing-logic.md` | 例一至例五 |
| B. 投资项目退出议题 | 投资决策文件、增资协议对赌回购条款、投后经营数据、与实际控制人沟通情况 | `references/exit-writing-logic.md` | 例六 |

Rules come from the gold examples in `references/gold-examples.md` (例六 is a desensitized 2026-09 项目退出议题终稿), the company format sample `assets/templates/文件字体格式.doc`, and the bundled fonts.

## 调用与跨 Agent 运行

本技能采用标准 `SKILL.md`（`name` / `description`）入口，可在 Claude、ChatGPT、Codex、Kimi、豆包、智谱 GLM（ZCode、AutoClaw）、WorkBuddy、TRAE、Qoder 等客户端通过自然语言匹配或在技能列表中显式选择。安装、迁移或触发异常时读取 [跨 Agent 安装与调用](references/agent-compatibility.md)，按实际产品安装完整目录或 ZIP，并完成调用验收；`scripts/skill_portability.py` 提供完整性检查、Word 冒烟测试、目录安装和打包。

执行时以当前已加载 `SKILL.md` 所在目录作为技能根目录，文内 `scripts/`、`references/`、`assets/`都相对此根目录解析，不相对用户任务目录；调用脚本时使用脚本及输入输出的绝对路径，输出文件放用户任务目录。网页检索、文件读取和代码执行使用宿主当前可用的等价工具，不要求特定工具名称。生成 Word 需要 Python 3.10+ 及 `requirements.txt`；宿主无执行或字体条件时，交付议题文本并如实说明 Word 未生成或未验证。

## What a 议题 is

- 行文方向：上行文。投管公司向投资决策委员会报送，用"提请""现申请""拟"，口吻正式、克制，不用指令性措辞。
- A 类：不设落款和日期，末尾以附件说明结束。
- B 类：不设"投委会："主送行，审议机构在导语末句点明；附件说明后落款单位、成文日期；退出方案作为附件另页排在文后。

## Workflow

1. Read every source document. A 类提取会议要素（名称、时间、地点、召集人、方式、表决方式、截止时间）和全部议案；B 类提取投资决策链（立项、尽调、董事会届次及票数、报告和备案文号）、对赌与回购条款原文、最近一个完整年度和最新一期经营数据、合同与回款、与实际控制人沟通结果。
2. Decide the type (A/B) and draft strictly on its skeleton. Where the source is thin, corroborate with authoritative public sources and cite the document number; never invent figures.
3. Write in 正式书面公文语体, neutral in tone: judgments rest on data, neither hedged into vagueness nor pushed to absolutes (see 语气基调 in `references/writing-logic.md`).
4. End every paragraph with a fact or a conclusion. Never close a paragraph with "需要后续进行判断""有待进一步研判""后续持续关注""视情况而定" or any similar deferral sentence.
5. State what things are and why they are necessary, directly. Never use "不是……而是""并非……而是""不仅……而且""而非" or other set-up-then-negate patterns.
6. Put the JSON spec through `scripts/check_yiti_text.py spec.json`; fix every 硬规则 hit, review each 警告 in context.
7. Run `scripts/ensure_fonts.py` once per machine: it installs the bundled 仿宋_GB2312, 楷体_GB2312 and 方正小标宋简体 per-user when missing (Windows registry included, no admin rights). 方正小标宋简体's licence forbids embedding it in the .docx, so the machine that opens the file must have it installed.
8. Render with `scripts/create_yiti_docx.py spec.json out.docx` (see `assets/examples/exit-yiti-spec.json` for a complete B 类 spec), then open the file in Word and check font fallback, line spacing, table layout, attachment alignment and page numbers.

## Required Format Priorities

Apply fonts in this order, exactly as in the manual Word workflow:

1. Chinese fonts by role: title 二号方正小标宋简体; `提交子公司：投管公司` 三号楷体_GB2312 centered; body 三号仿宋_GB2312; `一、` 三号黑体 not bold; `（一）` 三号楷体_GB2312 bold; `1.` 三号仿宋_GB2312 bold; `（1）` 三号仿宋_GB2312 bold (四级标题，按需使用).
2. Every round parenthesis and its contents: 楷体_GB2312. Size follows the location: 二号 in the main title and attachment titles (same size as the title), 三号 in the submit line, body, headings and attachment lines, 五号 inside tables. The serial number `（1）` of a 四级标题 is not changed to 楷体: it stays 仿宋_GB2312 bold with the heading.
3. Tables: every character 五号; outside parentheses 仿宋_GB2312, inside parentheses 楷体_GB2312; centered horizontally and vertically; header row bold and repeated across pages.
4. Footer: `-1-`, both hyphens and the PAGE field all 四号宋体 in every font slot; always on; odd/even pages different (odd right, even left).
5. Last pass: Times New Roman for the whole body — every digit, Latin letter and symbol such as `%` `.` `:` becomes Times New Roman, inside parentheses and tables too, while Chinese characters keep the fonts above. The footer is excluded and stays 四号宋体. Full-width digits and `％` are converted to half-width first so the pass reaches them.
6. Numbers (千位分隔符): every Arabic number whose integer part has four or more digits takes a half-width comma every three digits counted from the units digit, with a half-width point as the decimal mark (US/UK style): `1,234.56`、`2,350万元`、`141,583.56元`、`1,000,000`; write `1,980万元`, never `1980万元`. This applies in the title, body, parentheses, tables and attachments. The decimal part is not grouped, and the separator is never a full-width `，`, a space or a point. Identifiers are not quantities and stay ungrouped: years (`2026年`), dates, times, 文号 (`〔2026〕12号`), page numbers, phone and ID numbers, 统一社会信用代码, stock codes, contract/patent/order numbers, model, version and standard numbers. `scripts/check_yiti_text.py` flags ungrouped numbers as a 硬规则.

Layout:

- Title block and all headings: fixed 30 pt line spacing; body and attachments: fixed 28 pt. Every heading and paragraph starts with a two-character first-line indent (centered title block and the flush-left `投委会：` excepted).
- Attachment note: after the body, one blank line, then a paragraph indented two characters in 三号仿宋_GB2312. Single: `附件：名称`, wrapped lines align with the first character of the name. Multiple: `附件：1.名称`, then `2.名称` on a new line aligned with `1.`; a long item wraps to align after its own `2.`, never back to the margin. Names carry no 书名号 and no trailing punctuation; the JSON passes names only.
- B 类 signature: two blank lines after the attachment note; issuer right-indented four characters, date centered beneath it; kept on one page with the attachment note and the closing body line.
- B 类 attachment document: new page, `附件：` flush left, 二号方正小标宋简体 title, one blank line, then the same heading/body/table rules.

## Bundled Resources

- `references/format-rules.md`: page setup, font order, sizes, indentation, table, attachment, signature and footer rules.
- `references/writing-logic.md`: 议题类型判断, A 类 section-by-section logic and sentence bank, tone baseline, forbidden-wording checklist shared by both types.
- `references/exit-writing-logic.md`: B 类 skeleton, section logic, connective and data sentence bank, 退出方案 template and self-check list.
- `references/gold-examples.md`: six annotated 议题 (券商股东会两例、基金合伙人会议三例、项目退出一例).
- `assets/examples/exit-yiti-spec.json`: complete desensitized B 类 spec (正文、附件说明、落款、退出方案附件及流程表).
- `assets/fonts/`: 方正小标宋简体、楷体_GB2312、仿宋_GB2312 (simfang.ttf), not distributed; use installed licensed fonts or ICDAFY_FONT_DIR.
- `assets/templates/文件字体格式.doc`: original company format sample.
- `scripts/create_yiti_docx.py`: deterministic DOCX generator. Spec fields: `kind` (`meeting`/`exit`), `title` (use `\n` to break lines), `submit_line`, `recipient` (empty string omits it), `intro` (string or list of paragraphs), `blocks` (`h1` `h2` `h3` `h4` `para` `table` `blank`; `**...**` for inline bold), `attachments`, `signature` {`issuer`, `date`}, `appendices` [{`title`, `blocks`}], `page_numbers` (default true). Embeds the bundled 仿宋_GB2312/楷体_GB2312 on save and prints the text-check result.
- `scripts/check_yiti_text.py`: language scanner for JSON specs or text drafts (deferral endings, set-up-then-negate patterns, stock phrases, tone warnings); exit code 1 on hard hits.
- `references/agent-compatibility.md`: installation, invocation, runtime adaptation and acceptance checks for each supported client.
- `scripts/skill_portability.py`: stdlib-only package checker, DOCX smoke test, client-folder installer and ZIP packager.
- `requirements.txt`: Python dependency for DOCX output.
- `scripts/ensure_fonts.py`: checks the three official-document fonts and installs missing ones per-user only from the user-supplied ICDAFY_FONT_DIR (`--check` only reports). The generator prints a reminder when any is missing.
- `scripts/embed_fonts.py`: font embedder used by the generator; `python scripts/embed_fonts.py --docx out.docx --verify` re-checks an existing file.
