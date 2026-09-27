# 国企中文公文格式规则

These rules are extracted from `assets/templates/文件字体格式.doc`, the uploaded fonts, and the company onboarding training PDF section on 公文格式.
The explicit rules in this file take precedence over the original sample where they differ.
The typography is the shared company standard defined in yiti-skill `references/format-rules.md`; this skill, yiti-skill, hangye-fenxi, zhuying-yewu-fenxi, gongsi-qingkuang and soe-post-investment-report all follow it.

## Page Setup

- Paper: A4 portrait.
- Margins: top 3.7 cm, bottom 3.5 cm, left 2.8 cm, right 2.6 cm.
- Title line spacing (main title, subtitle, issuing-unit title line and every numbered heading `一、` `（一）` `1.` `（1）`): exactly 30 pt.
- Body, 附件说明, signature and attachment-body line spacing: exactly 28 pt. Space before/after is 0 everywhere.
- Body paragraphs: justified alignment, first-line indent 2 Chinese characters.
- Numbered headings inside the body also use a first-line indent of 2 Chinese characters.
- Keep these fixed line spacings when adjusting pagination; do not use minimum or multiple spacing or compress them to fit a page.

## Fonts and Sizes

- Main title: 方正小标宋简体, 二号, centered, not bold.
- Subtitle or department line: 楷体_GB2312 or 楷体, 三号, centered.
- Body: 仿宋_GB2312 preferred; use bundled `simfang.ttf` when the system lacks that font, 三号.
- First-level heading `一、xxxx`: 黑体, 三号, not bold.
- Second-level heading `（一）xxxx`: 楷体_GB2312, 三号, bold.
- Third-level heading `1.xxxx`: 仿宋_GB2312, 三号, bold.
- Fourth-level heading `（1）xxxx`: 仿宋_GB2312, 三号, bold. Use it only when the content needs a fourth level. The leading serial `（1）` stays in the heading font (仿宋_GB2312, bold) and is not switched to 楷体; later parentheses in the heading text follow the parentheses rule.
- Parenthesized content: all paired Chinese/English round parentheses `（…）` / `(...)` and their contents use 楷体_GB2312 throughout the document, including nested parentheses, titles, attachment names and signatures. The size follows the position: 二号 (22 pt) inside the main title and attachment titles, 三号 (16 pt) in the subtitle, body, headings, 附件说明 and signature, 五号 (10.5 pt) in tables. Preserve the position's bold. The only exception is the leading `（1）` serial of a fourth-level heading. Digits, Latin letters and `%` inside the parentheses use Times New Roman (see the final pass below). Unpaired parentheses do not change subsequent text formatting.
- Tables: all text inside a table is fixed at 五号 (10.5 pt): 仿宋_GB2312 outside parentheses, 楷体_GB2312 for parenthesized spans. The header row is bold (no shading) and repeats on every page; other rows are not bold; no row splits across pages. Cells use single line spacing, no first-line indent, centered horizontally and vertically, with plain single black borders. The table fills the text width and column widths follow the content (short columns such as 序号 keep their width, long text columns share the rest). A lead-in sentence ending with `：` precedes the table on the same page; use `—` for empty cells and thousands separators for amounts.
- Full-width digits, Latin letters and `％` are converted to half-width first (the generator does it automatically; fix them by hand in plain text), otherwise the final pass cannot reach them.
- Times New Roman final pass: every digit, Latin letter, `%` and other half-width character in the whole document uses Times New Roman — titles, body, headings, parenthesized spans, tables, attachments, signature and date. Apply it last, after 方正小标宋简体、黑体、楷体_GB2312、仿宋_GB2312 and the 四号宋体 footer are in place: select the whole text and set only the Western font (ascii/hAnsi/cs) to Times New Roman. Times New Roman has no CJK glyphs, so Chinese characters keep their Chinese faces (eastAsia unchanged). The footer `-1-` is excluded and stays 四号宋体.
- Page number: the entire `-1-` uses 四号宋体 (14 pt), including both hyphens, the PAGE field and its displayed result — the two hyphens are resized to 四号 as well, not only the digit. Set ascii/hAnsi/cs/eastAsia to 宋体 for every footer page-number run. Odd and even pages use different footers.

Word size mapping used by the sample:

- 二号 = 22 pt.
- 三号 = 16 pt.
- 四号 = 14 pt.
- 五号 = 10.5 pt.

## Document Structure

Use this order for a standard notice-style document:

1. Issuing unit line, if needed.
2. Main title, centered.
3. Optional subtitle or department line, centered.
4. One blank line before recipient/body.
5. Recipient line ending with `：`.
6. Body paragraphs.
7. One blank line, then the 附件说明 block, if any.
8. Two blank lines before the signature.
9. Issuing unit, right aligned with a 4-character right indent.
10. Date on the line below, centered on the issuing unit.

When the user asks for plain text rather than DOCX, preserve the same order. Main title/subtitle are not indented; body paragraphs and numbered headings begin with two full-width spaces `　　`.

## Headings and Numbering

- Use `一、` for first-level sections.
- Use `（一）` for second-level sections.
- Use `1.` for third-level sections.
- Use `（1）` for fourth-level points (三号仿宋_GB2312, bold), only when needed.
- Do not reverse or skip the hierarchy, and do not mix Arabic and Chinese numbering at the same hierarchy.
- Keep headings compact; move explanations into following paragraphs.
- First-level headings used as subheadings normally have no sentence-ending punctuation.
- Second-level headings used as subheadings may omit punctuation when compact.
- Third-level `1.` headings or points should include punctuation when written as a sentence or clause.
- Fourth-level `（1）` points should include punctuation when written as a sentence or clause.
- In DOCX, all four heading levels use a Word first-line indent of 2 Chinese characters; in plain text, prefix them with `　　`.

## 行文方向 and Front-Matter Notes

- 上行文: usually includes 请示 or 报告. The 发文字号 may be placed left with one-character left clearance, and the 签发人 is placed to the right of the 发文字号. Use `签发人` in 三号仿宋 and the signer's name in 三号楷体.
- 下行文: usually includes 通知, 通报, 决定, 批复, 印发类文件. Requirements should be clear and executable.
- 平行文: usually uses 函, 商请, 函询, 函告, or coordination wording between equal or unrelated units.
- If the user only needs body text and does not request a full red-head document, do not invent 份号、密级、紧急程度、版记 or 印章 information.

## Attachments（附件说明）

Detect this automatically. Whenever the document ships something alongside the body — the user writes 附件/附后/附表/附图/随文报送/见附件/一并印发, hands over a list of attached items, or the source text already carries a 附件 line — lay out the block below without being asked, and normalize an existing 附件 line that does not match it.

The character unit is the body size: 三号 = 16 pt per full-width character.

- The block goes after the last body paragraph, separated by one blank line, and before the 发文机关署名.
- `附件：` starts 2 characters in, the same as a body first-line indent. Never 顶格.
- One attachment: `附件：XXXXX`, no serial number.
- Two or more: number them with Arabic numerals `1.` `2.` `3.`. The first rides on the `附件：` line; each later one starts its own paragraph indented 5 characters so its serial sits directly under `1.`.
- Hanging indent, never 定格. When a name overruns the line, the continuation lines align with the start of that attachment's own name — not with the left margin, and not with the serial number:

```
　　附件：1.西安未央城市建设集团有限公司公文行文
　　　　　　规范性格式模板
　　　　　2.西安未央城市建设集团有限公司公文用纸、
　　　　　　字体字号及页边距对照表
```

Column 1 is the left margin; `附件：` occupies columns 3–5, the serial column 6, and every name — first line and continuation alike — starts at column 7.

- Word indents that produce it (computed from the real glyph widths: `附件：` is 3 full-width characters, the serial `1.` is measured in Times New Roman; CJK/Latin auto-spacing is switched off on these paragraphs so the columns line up exactly):
  - Single attachment: left indent = 2 chars + width of `附件：`; first line hangs back to 2 chars.
  - Numbered first item: left indent = 2 chars + `附件：` + width of `1.`; first line hangs back to 2 chars.
  - Numbered later items: first line starts at 2 chars + `附件：` (so `2.` sits under `1.`); left indent = that point + width of the serial.
  - A wider serial (`10.` and up) shifts only that item's own name column; every item still hangs under itself.
- Names take no 书名号 and no trailing punctuation. Remove `《》` and trailing sentence/separator punctuation (including 。；，、．：！？ and ASCII equivalents), while preserving meaningful closing parentheses in names such as `实施方案（试行）`.
- Do not repeat `附件：` on the continuation items.
- Attachment bodies start on a new page. The top-left label is 三号仿宋_GB2312 with no indent: `附件：` for a sole attachment, `附件1：` `附件2：` … for several. The attachment title follows in 二号方正小标宋简体, centered (it may wrap), then one blank line, then the body under the same heading, body and table rules as the main text.

## 发文机关署名、成文日期与页码

- Leave two blank lines between the end of the body (or of the 附件说明) and the signature block.
- 发文机关署名: right aligned, right indent exactly 4 characters (64 pt).
- 成文日期: the line directly below the signature, centered on the signature — the date's midpoint sits on the signature's midpoint.
- Both lines are right aligned and centered on each other: right indent = 4 characters + (width of the wider line − width of this line) / 2, with widths measured from the real glyphs (Chinese full width, digits in Times New Roman) and 中西文自动间距 switched off so Word does not widen `2026年6月8日` past its measured width.
- Keep the last body paragraph, 附件说明, the two blank lines and the signature on one page; the signature never sits alone on a page.
- Date format: `2026年6月8日`, Arabic numerals, no leading zeros.

```
                         西安未央城市建设集团有限公司····    ← 右空 4 字
                              2026年6月8日                  ← 与署名同心
```

- Page numbers are placed on the outside edge, odd and even pages different (odd pages right, even pages left).
- Page number format is `-1-`, `-2-`: both hyphens and every part of the PAGE field/result are explicitly 四号宋体 (14 pt), on odd and even pages alike.
- A seal/signature page must contain at least two lines of 正文. Do not create a page headed only by `（此页无正文）`.

## Punctuation and Typography

- Use full-width Chinese punctuation in Chinese text.
- Do not place punctuation between consecutive book-title marks or quotation marks.
- Avoid decorative formatting, colored text, emojis, underlines, and unnecessary bold.
- Keep one formatting system throughout the document; do not mix Microsoft YaHei/SimSun body text unless required by source material.
- Use Chinese six-angle brackets `〔〕` for 发文年度 in 发文字号, e.g. `未城产投发〔2026〕1号`; do not use square brackets or `【】` for this role.

## Final Format Checklist

- Title is 二号方正小标宋简体 and centered.
- Subtitle or department line is 三号楷体_GB2312 and centered.
- There is one blank line after subtitle/department line before正文 or主送机关.
- Body is 三号仿宋_GB2312.
- First-level headings are 三号黑体, not bold.
- Second-level headings are 三号楷体_GB2312, bold.
- Third-level headings are 三号仿宋_GB2312, bold.
- Fourth-level headings are 三号仿宋_GB2312, bold, and the `（1）` serial stays 仿宋_GB2312 bold.
- All round-parenthesized spans, including delimiters, are 楷体_GB2312 at the size of their position: 二号 in the main/attachment title, 五号 inside tables, 三号 elsewhere.
- All table text is 五号; only the header row is bold, with no shading; the header repeats and rows do not split.
- No full-width digits, Latin letters or `％` remain.
- Every digit, Latin letter and `%` outside the footer is Times New Roman, including inside parentheses and tables; Chinese characters keep their Chinese faces.
- Title lines and numbered headings have exactly 30 pt spacing; body, 附件说明 and signature have exactly 28 pt spacing.
- All body paragraphs and body headings have a two-character first-line indent.
- `附件：` starts 2 characters in; multiple attachments are numbered `1.` `2.`, with later serials at 5 characters.
- Every attachment name that wraps hangs under its own first-line name column, not at the margin.
- Attachment names carry no 书名号 and no trailing punctuation.
- A sole attachment has no serial; multiple attachments use Arabic serials. Attachment pages carry `附件：` (sole) or `附件1：` `附件2：` … at the top left.
- Two blank lines precede the signature; the issuing unit is right-indented 4 characters.
- The date sits directly below the issuing unit and is centered on it.
- The complete footer `-1-` uses 宋体 at 14 pt (四号) on odd and even pages, including both hyphens and the field result; odd/even footers are different.
