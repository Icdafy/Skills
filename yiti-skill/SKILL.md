---
name: yiti-skill
description: Draft Chinese SOE investment-committee deliberation memos (投委会议题) from investee or fund meeting notices. Use when the user provides a 股东会/合伙人会议通知、议案、会议材料 and asks to write a 议题, 投委会议题, 审议议题, 参会及表决事项议题, 投后管理议题, or asks to 报送投委会/提请投委会审议. Covers 参股公司临时股东会、年度股东会、基金合伙人会议（首次/年度/临时）等场景, including full DOCX output with company officialese typography (方正小标宋简体标题、仿宋_GB2312正文、Times New Roman数字、仿宋五号表格).
---

# 议题 Skill（投委会议题撰写）

Use this skill to draft 投管公司报送投委会的"议题"文书. The input is a meeting notice package sent by an investee company or fund manager (股东会通知、合伙人会议通知、议案、会议材料); the output is a standalone 议题 that reports the meeting, summarizes each 议案, states the compliance-check conclusion, and requests the 投委会 to deliberate the participation and voting stance. Rules are based on the four gold examples in `references/gold-examples.md`, the company format sample `assets/templates/文件字体格式.doc`, and the bundled official fonts.

## What a 议题 is

- 行文方向: 上行文。投管公司（提交部门/子公司）向产投公司投资决策委员会报送，口吻恭敬、克制、请求审定，用"提请""请予审议""拟"，不得使用指令性措辞。
- 触发场景: 被投企业或基金管理人发来会议通知及议案，投后管理工作要求将其报送投委会，审议我方参会表决意见。
- 文书本身不落款、不写日期，末尾以附件行结束（配套的召开投委会请示另有表单）。

## Workflow

1. Read every source document in the notice package: 会议通知、各项议案全文、会议材料、表决票。Extract the meeting facts (名称、时间、地点、召集人、会议方式、表决方式、表决文件截止时间) and the full list of 议案.
2. Identify the 主体 and the relationship: 参股企业股东会（如证券公司临时股东会）还是基金合伙人会议（首次/年度/临时）。Identify 召集人身份（董事会/执行事务合伙人/基金管理人）。
3. Draft strictly on the fixed skeleton in `references/writing-logic.md`: 标题 → 提交部门/子公司 → 投委会： → 导语 → 一、会议基本信息 → 二、会议审议事项 → 三、请示事项 → 附件。
4. For each 议案, put the core conclusion first in bold, then the supporting basis: 协议条款编号原文、监管政策文号、内部决策程序、关键数字（金额、期限、比例、计算基数）。Where the source material is thin, corroborate with authoritative public sources (监管公告、交易所通知、行业统计) and cite the document number; never invent figures.
5. Run the language checks in `references/writing-logic.md`: 禁用"不是……而是""并非……而是""不仅……而是""不但……而且""值得注意的是""综上所述"等连接词；转折用"但"；全文书面公文语气。
6. Apply the typography in `references/format-rules.md`. All Chinese runs use the company fonts; all digits and Latin characters use Times New Roman.
7. For Word output, run `scripts/create_yiti_docx.py` with a JSON spec, then inspect the file in Word for font fallback, fixed line spacing, table layout, and attachment indentation.

## Required Format Priorities

- Main title: 二号方正小标宋简体, centered, may wrap to multiple lines; pattern `审议关于XXXX（主体全称）XXXX年XX会议（参会及表决事项）的议题`.
- Second line: `提交部门/子公司：投管公司`, 三号楷体_GB2312, centered.
- One blank line, then recipient `投委会：` at the left margin, 三号仿宋_GB2312.
- Body: 三号仿宋_GB2312; every paragraph and every heading starts with a two-Chinese-character first-line indent.
- First-level heading `一、会议基本信息`: 三号黑体, not bold. Second-level heading `（一）XXX议案`: 三号楷体_GB2312, bold.
- All digits and Latin characters: Times New Roman, same point size as the surrounding text (三号 in body).
- Tables: cell text 仿宋_GB2312 五号, centered horizontally and vertically; digits in cells Times New Roman; table autofits to content and window width.
- Core conclusions and lead-in labels (`主要内容：` `审议依据：`) may be bold 仿宋_GB2312; no other decoration.
- Attachment block ends the document: single attachment `附件：XXXX`; multiple attachments numbered `1.` `2.` with hanging alignment. No 落款, no date.

## Bundled Resources

- `references/format-rules.md`: page setup, fonts, sizes, indentation, table, and attachment rules for the 议题 document.
- `references/writing-logic.md`: the section-by-section drafting logic, sentence bank, compliance-conclusion formulas, and forbidden-wording checklist.
- `references/gold-examples.md`: four annotated real 议题 examples (参股券商股东会两例、基金合伙人会议两例).
- `assets/fonts/方正小标宋简体.ttf`: title font.
- `assets/fonts/楷体_GB2312.ttf`: subtitle and second-level heading font.
- `assets/fonts/simfang.ttf`: 仿宋_GB2312 body font.
- `assets/templates/文件字体格式.doc`: original company format sample.
- `scripts/create_yiti_docx.py`: deterministic 议题 DOCX generator with mixed Chinese/Times New Roman runs, inline bold, and formatted tables.
