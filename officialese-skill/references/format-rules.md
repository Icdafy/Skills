# 国企中文公文格式规则

These rules are extracted from `assets/templates/文件字体格式.doc`, the uploaded fonts, and the company onboarding training PDF section on 公文格式.

## Page Setup

- Paper: A4 portrait.
- Margins: top 3.7 cm, bottom 3.5 cm, left 2.8 cm, right 2.6 cm.
- Title line spacing: fixed 30 pt.
- Body line spacing: fixed 28 pt.
- Body paragraphs: justified alignment, first-line indent 2 Chinese characters.
- Numbered headings inside the body also use a first-line indent of 2 Chinese characters.
- Adjust margins and line spacing only when the document has a practical layout constraint.

## Fonts and Sizes

- Main title: 方正小标宋简体, 二号, centered, not bold.
- Subtitle or department line: 楷体_GB2312 or 楷体, 三号, centered.
- Body: 仿宋_GB2312 preferred; use bundled `simfang.ttf` when the system lacks that font, 三号.
- First-level heading `一、xxxx`: 黑体, 三号, not bold.
- Second-level heading `（一）xxxx`: 楷体_GB2312, 三号, bold.
- Third-level heading `1.xxxx`: 仿宋_GB2312, 三号, bold.
- Fourth-level heading `（1）xxxx`: 仿宋_GB2312, 三号, not bold unless the source explicitly requires emphasis.
- Page number: 四号宋体, format like `-1-`.

Word size mapping used by the sample:

- 二号 = 22 pt.
- 三号 = 16 pt.
- 四号 = 14 pt.

## Document Structure

Use this order for a standard notice-style document:

1. Issuing unit line, if needed.
2. Main title, centered.
3. Optional subtitle or department line, centered.
4. One blank line before recipient/body.
5. Recipient line ending with `：`.
6. Body paragraphs.
7. Attachment line, if any.
8. Two blank lines before signature.
9. Issuing unit, right aligned and right-indented about 4 Chinese characters.
10. Date below signature.

When the user asks for plain text rather than DOCX, preserve the same order. Main title/subtitle are not indented; body paragraphs and numbered headings begin with two full-width spaces `　　`.

## Headings and Numbering

- Use `一、` for first-level sections.
- Use `（一）` for second-level sections.
- Use `1.` for third-level sections.
- Use `（1）` for fourth-level points.
- Do not reverse or skip the hierarchy, and do not mix Arabic and Chinese numbering at the same hierarchy.
- Keep headings compact; move explanations into following paragraphs.
- First-level headings used as subheadings normally have no sentence-ending punctuation.
- Second-level headings used as subheadings may omit punctuation when compact.
- Third-level `1.` headings or points should include punctuation when written as a sentence or clause.
- Fourth-level `（1）` points should include punctuation.
- In DOCX, all four heading levels use a Word first-line indent of 2 Chinese characters; in plain text, prefix them with `　　`.

## 行文方向 and Front-Matter Notes

- 上行文: usually includes 请示 or 报告. The 发文字号 may be placed left with one-character left clearance, and the 签发人 is placed to the right of the 发文字号. Use `签发人` in 三号仿宋 and the signer's name in 三号楷体.
- 下行文: usually includes 通知, 通报, 决定, 批复, 印发类文件. Requirements should be clear and executable.
- 平行文: usually uses 函, 商请, 函询, 函告, or coordination wording between equal or unrelated units.
- If the user only needs body text and does not request a full red-head document, do not invent 份号、密级、紧急程度、版记 or 印章 information.

## Attachments

- Write `附件：行文规范性格式模板` when there is one attachment.
- For multiple attachments, use:
  - `附件：1.XXXXX`
  - `      2.XXXXX`
- Do not add book-title marks around attachment names.
- Do not add punctuation after attachment names.
- If attachments have serial numbers in the attachment body, use Arabic numerals, e.g. `附件1.XXX`.
- The word `附件：` is preceded by a 2-character indent.

## Date, Signature, and Page Numbers

- Leave two blank lines before the unit name/date block when the body ends.
- Unit name is right aligned, visually leaving about 4 Chinese characters on the right.
- Date uses Chinese date format: `2026年6月8日`; align it under the issuing unit rather than centering it independently.
- Page numbers are placed on the outside edge for odd/even pages where possible, with odd/even pages different.
- Page number format is `-1-`, `-2-`, etc.
- A seal/signature page must contain at least two lines of正文. Do not create a page headed only by `（此页无正文）`.

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
- Fourth-level headings are 三号仿宋_GB2312, not bold.
- All body paragraphs and body headings have a two-character first-line indent.
- Attachments, signature, date, and page numbers follow the rules above.
