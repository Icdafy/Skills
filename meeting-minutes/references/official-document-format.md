# Official Document Format

Use this reference when creating or formatting meeting-minute Word documents. The rules come from the user's `文件字体格式.doc` and the `新员工入职培训资料（综合办公室）.pdf` public-document-format section.

## Font Whitelist

Only use these fonts in the final meeting-minute document:

- Title: `方正小标宋简体`.
- First-level headings: `黑体`.
- Second-level headings: `楷体_GB2312`.
- Body, third-level headings, fourth-level headings, front matter, and dates: `仿宋_GB2312`.
- Arabic numerals: `Times New Roman`.

Do not use Songti, Microsoft YaHei, Calibri, Arial, WPS bullets, or other fonts in the final DOCX. If page numbers are required, Arabic numerals still use `Times New Roman`; otherwise omit page numbers by default.

The user's wording `楷体GB2312` and `仿宋GB2312` corresponds to the Word font names `楷体_GB2312` and `仿宋_GB2312` seen in the sample document.

## Page And Paragraph Geometry

- Paper: A4 portrait.
- Margins: top 3.7 cm, bottom 3.5 cm, left 2.8 cm, right 2.6 cm.
- Title line spacing: fixed 30 pt.
- Body line spacing: fixed 28 pt.
- Paragraph spacing before/after: 0 pt unless a blank line is intentionally needed.
- Body alignment: justified.
- Body first-line indent: two Chinese characters, about 32 pt for 16 pt text.
- Heading first-line indent: all heading levels (`一、`, `（一）`, `1.`, `（1）`) also take the two-character first-line indent, same as body paragraphs. In plain-text output this appears as two full-width spaces (`　　`) before the heading.
- Title alignment: centered.

## Type Scale And Hierarchy

- Main title: 22 pt, `方正小标宋简体`, centered, not bold.
- Optional subtitle or department line: 16 pt, `楷体_GB2312`, centered.
- Body: 16 pt, `仿宋_GB2312`.
- First-level heading `一、`: 16 pt, `黑体`, not bold. When used as a heading, omit the sentence-ending punctuation.
- Second-level heading `（一）`: 16 pt, `楷体_GB2312`, bold.
- Third-level heading `1.`: 16 pt, `仿宋_GB2312`, bold, with sentence-ending punctuation when it forms a sentence.
- Fourth-level heading `（1）`: 16 pt, `仿宋_GB2312`, normal weight, with sentence-ending punctuation when it forms a sentence.

## Opening Metadata

Meeting minutes must open with four basic information lines after the title:

```text
　　访谈时间：{时间或未提及}
　　访谈地点：{地点或未提及}
　　访谈对象：{对象人员、单位、职务或未提及}
　　访谈人员：{我方人员或未提及}
```

Do not use a table for this opening block. In chat/plain text output, use two full-width spaces before each line. In DOCX output, use the two-character first-line indent and do not rely on table cells.

## Numbering And Attachments

- Body hierarchy order: `一、` -> `（一）` -> `1.` -> `（1）`; do not reverse the order.
- Every heading in the hierarchy starts with the two-character indent; never left-flush a heading.
- Attachment line: `附件：1. XXXXX`; do not add book-title marks around attachment names and do not add punctuation after attachment names.
- When there are multiple attachments, align subsequent attachment lines under the first attachment name.

## PDF Training Notes

The training PDF is a 39-page landscape courseware file. Treat it as supporting evidence for content principles rather than the Word page layout. It confirms:

- Official documents include a subject section and list `纪要` among statutory document types.
- The main body generally uses 3rd-size `仿宋_GB2312`.
- Attachments begin after a two-character indent and use Arabic sequence numbers.
- The body hierarchy uses `一、`, `（一）`, `1.`, `（1）`, with first-level `黑体`, second-level `楷体`, and third/fourth-level `仿宋`.
