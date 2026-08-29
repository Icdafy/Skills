# Quality gates

All blocking gates must pass before delivery.

## A. Scope and evidence

- [ ] The user answered all four mandatory change-control questions.
- [ ] Reporting year and cut-off date are explicit.
- [ ] Every source is inventoried and mapped to a project or portfolio scope.
- [ ] The canonical project registry reflects additions, removals, renames, exits, and category changes.
- [ ] Every material number and conclusion has a fact-ledger locator.
- [ ] Every fact has a non-empty list of atomic exact-match `assertions`.
- [ ] Every substantive block that references a fact contains at least one assertion for that fact; numeric and status conclusions are covered by matching assertions.
- [ ] Every non-structural sentence and comma-level factual clause overlaps at least one assertion from a fact referenced by its block, followed by human clause review for unmatched extra wording.
- [ ] Numeric table rows use `row_fact_ids`, and each row consumes only facts whose assertions support that row.
- [ ] Material conflicts are resolved or explicitly held for user decision.
- [ ] Calculated facts retain formula, inputs, units, and rounding.

## B. Main-body structure

- [ ] The title year matches the reporting period.
- [ ] The recipient and opening basis are present.
- [ ] `一、年度股权投资完成总体情况` occurs exactly once.
- [ ] `二、重大投资项目进展情况` occurs exactly once.
- [ ] Category and project numbering is consecutive.
- [ ] No exact or normalized heading is duplicated within the same scope.
- [ ] No empty heading remains.
- [ ] The attachment list matches the generated attachments exactly.
- [ ] Issuer and date are present; contact details are included only when required.

## C. Cross-document reconciliation

- [ ] Project count and official names agree across body, registry, and attachments.
- [ ] Investment, paid-in, ownership, recovery, valuation, revenue, profit, net assets, budget, and dividends agree after unit and scope normalization.
- [ ] Current-period and cumulative figures are not mixed.
- [ ] Parent-only and consolidated figures are not mixed.
- [ ] Blank values have not been converted to zero.
- [ ] Narrative claims do not overstate the supporting table or source.
- [ ] Risks, trigger events, and remediation status are current as of the cut-off date.

## D. Language and compression

- [ ] The report is formal, restrained, and suitable for upward reporting.
- [ ] Conclusions precede detail.
- [ ] Unsupported promotional language is removed.
- [ ] Long histories, inventories, and full tables are in attachments.
- [ ] The main body is normally 5–6 pages and never exceeds 10 pages.
- [ ] Typography and margins were not reduced to meet the page budget.

## E. DOCX structure

- [ ] All eight required page width, height, margin, header-distance, and footer-distance values are recorded under spec `layout`.
- [ ] The first DOCX section geometry matches the spec `layout`; A4 portrait and source-derived margins are correct.
- [ ] Every additional or mixed section is inspected manually; the bundled validator warning is recorded and no whole-document geometry-certification claim is made.
- [ ] Title, body, four heading levels, tables, and page numbers use the specified styles.
- [ ] Odd/even page numbers sit on the outside edge.
- [ ] Each attachment begins on a new page.
- [ ] Table header rows repeat across pages.
- [ ] Required fonts are installed; the certified source-template path uses the exact recorded families rather than an unvalidated substitution.
- [ ] No macros, external templates, source attachments, or hidden project files are embedded.

## F. Rendered-page inspection

Inspect every page image, not a sample. Page PNG generation may be omitted for an intermediate draft, but `--png-dir` output and full-page visual inspection are mandatory for final certification. Preserved text boxes and pictures are not automatically understood or fact-reconciled by the helpers.

- [ ] No text, table, rule, footer, or page number is clipped or outside the printable area.
- [ ] No overlapping objects or corrupted glyphs appear.
- [ ] No heading is stranded at the bottom of a page.
- [ ] No unintended blank page appears.
- [ ] Tables remain readable and do not lose headers at page breaks.
- [ ] Red-head first-page elements and rule align correctly.
- [ ] Attachment title and first content remain together.
- [ ] Main-body and total page counts are recorded.
- [ ] A standalone `附件1` page label establishes the main-body boundary; without it, the current validator does not certify the 10-page ceiling.

## G. Public-repository safety

- [ ] Synthetic or sanitized examples contain no real project facts.
- [ ] Names, signatures, phone numbers, IDs, bank details, addresses, and non-public financials are absent.
- [ ] No licensed font binary is added without redistribution authority.
- [ ] Source files are not nested or embedded in generated assets.

## Automated validator interpretation

`scripts/validate_report.py` returns exit code 0 only when automated blocking checks pass. In addition to first-section geometry, it checks the source-template red head, title, document row, recipient/opening, body and heading typography, simple-table typography/header repetition/row splitting, closing envelope, odd/even PAGE-field typography, and render-manifest PNG signatures, dimensions, sequence, and hashes. This is the certified standard-template contract; a deliberately different typeface or richer layout must first be represented by a future validator contract and cannot be waved through as an undocumented substitution. Assertion matching is an exact short-phrase overlap check at block, sentence, comma-clause, and numeric-table-row levels (with layout whitespace and the optional `|` table-cell separator normalized); it does not authenticate the cited source, verify the locator, prove that the assertion is true, or prove that extra wording inside a matched clause is supported. The validator cannot replace clause-by-clause factual review or visual inspection. A warning is not automatically safe; document the decision. Use `--template-mode` only for the committed synthetic reference template, never for a final user report. The flag requires a supplied `--spec` with `template_only: true`, but those declarative values do not prove that arbitrary input is genuinely synthetic.

`--public-safe` and its deny-term options are heuristic package scans. A clean result is not an absolute guarantee that an artifact is public-safe, anonymous, licensed for redistribution, or free of confidential facts. Maintain a project-specific denylist and complete a human disclosure review before publication.
