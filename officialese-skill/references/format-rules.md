# 国企中文公文格式规则

These rules are extracted from `assets/templates/文件字体格式.doc`.

## Page Setup

- Paper: A4 portrait.
- Margins: top 3.7 cm, bottom 3.5 cm, left 2.8 cm, right 2.6 cm.
- Title line spacing: fixed 30 pt.
- Body line spacing: fixed 28 pt.
- Body paragraphs: justified alignment, first-line indent 2 Chinese characters.
- Adjust margins and line spacing only when the document has a practical layout constraint.

## Fonts and Sizes

- Main title: 方正小标宋简体, 二号, centered, not bold.
- Subtitle or department line: 楷体_GB2312 or 楷体, 三号, centered.
- Body: 仿宋_GB2312 preferred; use 仿宋 or bundled `simfang.ttf` as fallback, 三号.
- First-level heading `一、`: 黑体, 三号, not bold.
- Second-level heading `（一）`: 楷体_GB2312, 三号, bold.
- Third-level heading `1.`: 仿宋_GB2312, 三号, bold.
- Fourth-level heading `（1）`: 仿宋_GB2312, 三号, not bold unless emphasis is required.
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

## Headings and Numbering

- Use `一、` for first-level sections.
- Use `（一）` for second-level sections.
- Use `1.` for third-level sections.
- Use `（1）` for fourth-level points.
- Do not mix Arabic and Chinese numbering at the same hierarchy.
- Keep headings compact; move explanations into following paragraphs.

## Attachments

- Write `附件：行文规范性格式模板` when there is one attachment.
- For multiple attachments, use:
  - `附件：1.XXXXX`
  - `      2.XXXXX`
- Do not add book-title marks around attachment names.
- Do not add punctuation after attachment names.
- If attachments have serial numbers in the attachment body, use Arabic numerals, e.g. `附件1.XXX`.

## Date, Signature, and Page Numbers

- Leave two blank lines before the unit name/date block when the body ends.
- Unit name is right aligned, visually leaving about 4 Chinese characters on the right.
- Date uses Chinese date format: `2026年6月8日`.
- Page numbers are placed on the outside edge for odd/even pages where possible, with odd/even pages different.
- Page number format is `-1-`, `-2-`, etc.

## Punctuation and Typography

- Use full-width Chinese punctuation in Chinese text.
- Do not place punctuation between consecutive book-title marks or quotation marks.
- Avoid decorative formatting, colored text, emojis, underlines, and unnecessary bold.
- Keep one formatting system throughout the document; do not mix Microsoft YaHei/SimSun body text unless required by source material.
