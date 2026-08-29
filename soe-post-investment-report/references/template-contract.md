# Source-derived template contract

This contract records the reusable layout and structure distilled from the supplied post-investment report template and its separate corporate-format reference. It deliberately excludes company-specific facts, signatures, phone numbers, and font binaries.

## Document anatomy

The source report contains a short main body followed by independently sized attachments. The reusable order is:

1. red-head issuer line;
2. document number and signer row with a red lower rule;
3. two-line report title;
4. recipient and one-paragraph basis or opening;
5. annual equity-investment overview;
6. material project progress;
7. attachment list;
8. issuer, date, and optional contact line;
9. numbered project attachments;
10. optional distribution or edition note when the issuing organization requires it.

The source main body occupies five pages. Treat 5–6 pages as the normal target, 10 pages as the hard ceiling, and attachment length as separate.

## Fixed main-body logic

Preserve these first-level headings exactly. The current validator does not support changing them:

- `一、年度股权投资完成总体情况`
- `二、重大投资项目进展情况`

The first section always retains these fixed second-level headings:

- `（一）存续基金`
- `（二）新设基金`
- `（三）参股公司`
- the source template's exact fourth SPV slot, for example `（四）SPV项目` or `（四）<项目名称>SPV项目`

Record the exact source sequence in `document.source_fixed_main_headings` and the output sequence in `document.fixed_main_headings`. Record a non-empty `document.heading_contract_source` describing the inspected base template; the validator only checks that this human provenance note exists and does not authenticate it against an original file. `document.heading_change_authorized` must be boolean and `document.heading_change_note` must always be non-empty. When the two lists match, authorization must be `false` and the note must say that no fixed-heading change occurred. Only the SPV category slot may differ after a later direct answer to the four-question gate confirms a project-name change; the output must remain `（四）SPV项目` or `（四）<项目名称>SPV项目`, authorization must be `true`, and the note must state the exact change. All other fixed slots remain immutable. Never generalize a source-specific SPV heading merely because the sanitized public example uses `（四）SPV项目`. When a fixed category has no project, retain the heading and state that no such project exists during the reporting year. Use third-level numbered project headings under a category when projects need separate statements. The project-specific second-level headings under the second first-level section may follow confirmed material changes; that section contains only material developments, not a second copy of the full registry. A request to change any other fixed heading requires a deliberate schema and validator update before generation; user authorization alone does not bypass the contract.

## Page geometry

Record all eight values under the report specification's required `layout` object. The builder applies them to its single generated section and the validator compares only `doc.sections[0]` against the recorded values. Final specifications may not omit the object or an individual property; copy the source-derived values below when the supplied template is unchanged. The helpers do not infer or semantically adopt arbitrary uploaded-document geometry. A richer base DOCX may preserve native additional or mixed sections, but the validator only warns that they exist and does not validate their per-section geometry. Inspect every such section manually and do not describe the whole document as geometry-certified by this contract.

| Property | Value |
| --- | --- |
| Paper | A4 portrait, 21.0 cm × 29.7 cm |
| Top margin | 3.7 cm |
| Bottom margin | 3.5 cm |
| Left margin | 2.8 cm |
| Right margin | 2.6 cm |
| Header distance | 1.5 cm |
| Footer distance | 1.75 cm |
| Main title line spacing | exactly 30 pt |
| Body line spacing | exactly 28 pt |
| Normal first-line indent | 32 pt, approximately two Chinese characters at 16 pt |

## Typography

| Element | Chinese font | Size | Weight | Alignment |
| --- | --- | --- | --- | --- |
| Red-head issuer | 方正小标宋简体 | 68 pt OOXML master size (`w:sz=136`), source-compressed to approximately 36 pt visual height | bold | centered, red; one line with `w:w=37` and `w:fitText=8195` |
| Main and attachment title | 方正小标宋简体 | 22 pt | regular | centered |
| Recipient and body | 仿宋_GB2312 | 16 pt | regular | justified |
| First-level heading `一、` | 黑体 | 16 pt | regular | justified, two-character indent |
| Second-level heading `（一）` | 楷体_GB2312 | 16 pt | bold | justified, two-character indent |
| Third-level heading `1.` | 仿宋_GB2312 | 16 pt | bold | justified, two-character indent |
| Fourth-level heading `（1）` | 仿宋_GB2312 | 16 pt | regular | justified, two-character indent |
| Table body | 仿宋_GB2312 | 10.5 pt default | regular | centered unless semantic alignment requires otherwise |
| Page number | 宋体 | 14 pt | regular | outside edge on odd/even pages |
| Latin and Arabic characters | Times New Roman | matching size | matching | inherited |

Do not reduce font size or line spacing to hit a page limit. Compress language and move detail to attachments.

The red-head settings above intentionally reproduce the supplied DOCX's run properties rather than a nominal visual-size guess. Keep the issuer on one line and preserve the 68 pt master size, bold weight, character-width compression, and fit-text value together; changing only one of them causes visible template drift.

## Tables

- Fit tables to the content width and repeat the header row across pages.
- Use thin neutral borders and avoid decorative colors unless the current supplied template uses them.
- Keep units in a separate right-aligned note or in the table header.
- Put dates, units, and scopes in labels so figures cannot be misread.
- Prevent individual table rows from splitting when practical.
- Use landscape sections only when the current uploaded template or the user explicitly requires them; the bundled validator does not certify their per-section geometry.

The bundled JSON builder covers the standard source-derived正文 and simple portrait tables only. If an uploaded template or attachment uses images, merged or nested tables, text boxes, independent headers/footers, landscape sections, or other richer Word parts, preserve the original DOCX as the base and update it in place with a document-capable tool. Do not rebuild or flatten those parts merely to fit the helper schema. Preservation is structural, not semantic extraction: the helpers do not automatically read, fact-link, or reconcile the visible meaning of complex text boxes or pictures. Inspect every rendered final page and manually reconcile any material content inside those objects.

## Page numbers and breaks

- Use outside page numbers on odd and even pages in the form `-1-`.
- Begin each attachment on a new page.
- Keep at least one numbered attachment with a standalone `附件1` page label when final main-body pagination must be certified by the bundled validator.
- Keep an attachment title with its first substantive paragraph or table.
- Avoid an isolated heading at the bottom of a page.
- Do not insert manual page breaks merely to hide weak length control; use them only at semantic boundaries after rendering.

## Source-template anomaly converted to a QA rule

The supplied source contains a duplicated project-category heading in the main body. It is not part of the reusable framework. Any exact or normalized duplicate heading must fail validation unless the two headings occur in different attachment scopes and are intentionally distinguished.

## Font licensing and portability

The builder writes font family names into the DOCX. It does not bundle or embed font binaries. Use locally installed, properly licensed copies of the exact required families. A font substitution fails the current typography contract and cannot be converted into a certified final document merely by recording it or obtaining approval. Install the exact licensed font, deliver an explicitly uncertified draft, or deliberately extend the validator contract before final delivery.
