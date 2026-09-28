---
name: officialese-skill
description: 起草、改写、润色并排版中国国企公文及Word文件：通知、请示、报告、函、会议纪要、方案、附件说明等；识别上行文、平行文、下行文口吻，按公司版式设置字体、字号、页边距、标题层级、附件、落款和页码，输出DOC/DOCX。投委会议题、投后报告、立项报告章节另用专门技能。
---

# Officialese Skill

## When to Use

Draft, revise, and format Chinese state-owned enterprise official documents and Word files using a company-style officialese format. Use for SOE or Chinese corporate/government-style documents such as 通知, 请示, 报告, 函, 会议纪要, 附件说明, 上行文, 平行文, 下行文, formal redrafting, official tone polishing, DOC/DOCX layout, Chinese public-document typography, fonts, margins, headings, attachments, signatures, and page numbers.

Use this skill to create or revise Chinese SOE-style official documents with both correct wording and Word layout. The local rules are based on the uploaded company sample `assets/templates/文件字体格式.doc`, the bundled official fonts, and the company onboarding training PDF's 公文格式 rules.

## Cross-Agent Use

This skill uses the standard `SKILL.md` entry (`name` / `description`) and runs unchanged in Claude, ChatGPT, Codex, Kimi, 豆包, 智谱 GLM (ZCode, AutoClaw), WorkBuddy, TRAE and Qoder, invoked by natural language or by picking it from the client's skill list. For installation, migration or triggering problems read `references/agent-compatibility.md` and install the complete folder or ZIP; `scripts/skill_portability.py` checks the package, runs a Word smoke test, installs into client skill folders and builds upload ZIPs.

Resolve every `scripts/`, `references/` and `assets/` path against the folder that contains this `SKILL.md`, never against the task working directory; call scripts with absolute paths and write output into the user's task folder. Use whatever web, file and code-execution tools the host provides. Word output needs Python 3.10+ and `requirements.txt`; when the host cannot execute code or install fonts, deliver the text and state plainly that the DOCX was not generated or verified.

## Workflow

1. Identify the document type: 通知, 请示, 报告, 函, 会议纪要, 方案, 制度, 附件, or internal presentation material.
2. Identify 行文方向 before drafting:
   - Explicit `上行文` in the user prompt, or 请示/报告/报送/呈报/报批/申请批复 style wording, means use 上行文口吻.
   - Explicit `平行文`, or 函/商请/函询/函告/同级/不相隶属 coordination wording, means use 平行文口吻.
   - Explicit `下行文`, or 通知/通报/决定/批复/印发/下发/部署/要求 wording, means use 下行文口吻.
   - If no direction signal appears, default to normal formal SOE written style.
3. When the task is to draft or polish text, output the document content directly in the detected tone. Do not preface the answer with a long explanation of the detection unless the user asks for analysis.
4. Draft in formal, concise official language: state the basis, purpose, matter, requirements, responsible parties, and timing.
5. Apply the format rules in `references/format-rules.md`. The explicit rules below take precedence over the original sample where they differ.
6. Detect attachments without being asked. If the document ships anything alongside the body — the user writes 附件/附后/附表/附图/随文报送/见附件/一并印发, hands over a list of attached items, or the source already carries a 附件 line — lay out the 附件说明 block per `references/format-rules.md`, and silently normalize an existing 附件 line that does not match: 2-character start, no serial for one attachment, Arabic serials from `1.` for multiple attachments, later serials at 5 characters, each name hanging under its own name column when it wraps, no 书名号, no trailing punctuation. Then set the 发文机关署名 two blank lines below it, right-indented 4 characters, with the 成文日期 on the next line centered on the signature. Do not stop to ask whether to apply this.
7. Use wording patterns in `references/writing-patterns.md` when the task is drafting, polishing, or converting informal text into officialese.
8. For Word output, use the fonts in `assets/fonts/` and the sample template in `assets/templates/文件字体格式.doc`.
9. For a quick DOCX draft, first run `scripts/ensure_fonts.py` (detects the three official fonts and installs the bundled copies per user when missing), then run `scripts/create_official_docx.py`, then inspect and fine-tune in Word when strict page-number placement or legacy `.doc` compatibility is required. The generator implements the shared company format standard (the same as yiti-skill): tables take `{"table": [[header...], [row...]]}` with the first row as header, attachment bodies go in `appendices`, and `**...**` marks inline bold.

## Required Format Priorities

- Prefer the uploaded company sample over generic GB/T 9704 defaults when they differ.
- Main title: 二号方正小标宋简体, centered.
- Subtitle or department line: 三号楷体_GB2312, centered.
- After subtitle/department line, leave one blank line before the recipient/body.
- Body: 三号仿宋_GB2312.
- All content in Chinese or English round parentheses `（…）` / `(...)`, including the parentheses themselves, uses 楷体_GB2312 at the size of its position: 二号 (22 pt) inside the main title and attachment titles, 三号 (16 pt) in the subtitle, body, headings, attachment names and signatures, 五号 (10.5 pt) in tables. This applies to nested parentheses too; retain the position's bold. The only exception is the leading `（1）` serial of a fourth-level heading, which stays in the heading font. Digits, Latin letters and `%` inside the parentheses follow the Times New Roman rule below.
- Tables: every character in a table is fixed at 五号 (10.5 pt): 仿宋_GB2312 outside parentheses, 楷体_GB2312 for parenthesized spans. The header row is bold with no shading and repeats across pages; other rows are not bold and never split across pages. Cells use single line spacing, no first-line indent, centered horizontally and vertically. The table fills the text width with content-based column widths, and its lead-in sentence stays on the same page.
- Convert full-width digits, Latin letters and `％` to half-width (the generator does this automatically).
- Thousands separators (千位分隔符): every Arabic number whose integer part has four or more digits takes a half-width Western comma `,` every three digits counted from the units digit, with a half-width point `.` as the decimal mark (US/UK style): `1,234.56`、`2,350万元`、`245,766.75`、`1,000,000`; write `2,350万元`, never `2350万元`. This applies everywhere — title, body, headings, parentheses, tables, attachments and signature. The decimal part is not grouped, and the separator is never a full-width `，`, a space or a point. Identifiers are not quantities and stay ungrouped: years (`2026年`), dates, times, 发文字号 (`〔2026〕12号`), page numbers, phone and ID numbers, 统一社会信用代码, stock codes, contract/patent/order numbers, model, version and standard numbers (`GB/T 9704-2012`). When redrafting, add missing separators to the source's numbers.
- Times New Roman final pass: all digits, Latin letters, `%` and other half-width characters in the whole document (titles, body, headings, parentheses, tables, attachments, signature, date) use Times New Roman. Apply it as the last step, after 方正小标宋简体、黑体、楷体_GB2312、仿宋_GB2312 and the 四号宋体 footer have been set: set the Western font (ascii/hAnsi/cs) of every body and table run to Times New Roman while keeping each run's East Asian font unchanged, so Chinese characters keep their Chinese faces. The footer `-1-` stays entirely 四号宋体.
- Title lines (main title, subtitle and issuing-unit title line) and every numbered heading: exactly 30 pt line spacing. Body, 附件说明 and signature: exactly 28 pt. Space before/after is 0. Do not substitute multiple/minimum spacing or reduce these values to fit a page.
- Preserve Chinese punctuation and numbering hierarchy: `一、`, `（一）`, `1.`, `（1）`.
- First-level heading `一、xxxx`: 三号黑体, not bold.
- Second-level heading `（一）xxxx`: 三号楷体_GB2312, bold.
- Third-level heading `1.xxxx`: 三号仿宋_GB2312, bold.
- Fourth-level heading `（1）xxxx` (use only when the content needs a fourth level): 三号仿宋_GB2312, bold; the leading `（1）` serial stays 仿宋_GB2312 bold (digit in Times New Roman) and is not switched to 楷体.
- Body paragraphs and numbered headings must start with a two-Chinese-character first-line indent. In plain-text output, prefix them with two full-width spaces `　　`; in DOCX output, use Word first-line indent.
- 附件说明 starts 2 characters in, uses Arabic serials for two or more attachments, and hangs each wrapped name under that attachment's own name column instead of returning to the margin. Names carry no 书名号 and no trailing punctuation.
- Attachment bodies start on a new page with a top-left 三号仿宋_GB2312 label: `附件：` for a sole attachment, `附件1：` `附件2：` … for several; the attachment title follows in 二号方正小标宋简体, centered, then one blank line. A sole attachment has no Arabic serial in the list either (`附件：XXX`).
- The entire footer page number `-1-`, including both hyphens and the PAGE field/result, must use 宋体, 四号 (14 pt) — the hyphens are 四号 too, not only the digit. Explicitly set every run's Chinese and Western fonts to 宋体. Odd and even pages use different footers: odd pages right-aligned, even pages left-aligned.
- 发文机关署名 sits two blank lines below the body or 附件说明, right-indented 4 characters; 成文日期 goes on the next line, centered on the signature (both lines right aligned, right indent = 4 characters + half the width difference, CJK/Latin auto-spacing off). The signature never sits alone on a page.
- Keep titles short and literal. Put explanatory content in the body, not the title.
- Do not use casual, promotional, or emotional wording.
- Tone: formal written officialese with a neutral overall tone — neither overly conservative nor aggressive. State facts, basis and arrangements plainly; avoid both hedging and overstatement.
- Never end a paragraph (or write anywhere in the text) with follow-up-judgment tails such as `需要后续进行判断`、`有待进一步研判`、`后续视情况再定`、`仍需持续观察`、`需进一步评估`. The document states what it states; do not append such sentences.
- State necessity and conclusions directly as affirmative statements (`是……`、`需要……`、`有利于……`). Do not use negation-contrast constructions such as `不是……而是……`、`并非……而是……`、`不在于……而在于……`、`……而非……`、`与其……不如……`.
- Check the final file visually for font fallback, page margins, fixed line spacing, attachment labels, seal/signature area, and page numbers.

## Bundled Resources

- `references/format-rules.md`: typography, margins, spacing, headings, attachment, signature, and page-number rules extracted from the uploaded sample.
- `references/writing-patterns.md`: concise drafting patterns for common SOE official documents, including 上行文/平行文/下行文 tone detection.
- `assets/fonts/方正小标宋简体.ttf`: title font.
- `assets/fonts/楷体_GB2312.ttf`: subtitle, second-level heading and parenthesized-content font.
- `assets/fonts/simfang.ttf`: 仿宋_GB2312 body font.
- `assets/templates/文件字体格式.doc`: original uploaded format sample.
- `scripts/create_official_docx.py`: deterministic starter DOCX generator. Parenthesized spans are split into their own runs with 楷体_GB2312 as the Chinese face at the size of their position (二号 in titles, 三号 in the body, 五号 in tables). Tables are given as `{"table": [[...], ...]}` items in `body` or a section's `paragraphs` and render in 五号仿宋_GB2312 with a bold, unshaded, repeating header row. Every run of the footer `-1-` is entirely 四号宋体, with odd/even footers. As its final step the generator runs a Times New Roman pass over every body and table run (ascii/hAnsi/cs → Times New Roman, eastAsia unchanged), so digits, letters and `%` are Times New Roman everywhere outside the footer. On save it embeds the bundled 仿宋_GB2312 / 楷体_GB2312 into the file so it renders faithfully on machines without those fonts (方正小标宋 is licence-restricted and is skipped); embedding is verified and falls back to the un-embedded file if verification fails. `--attachment` normalizes names and builds the 附件说明 block with the hanging indents described above (one attachment has no serial), and `--issuer`/`--date` emit the 4-character-indented signature with the date centered on it.
- `scripts/embed_fonts.py`: font embedder used by the generator; run `python scripts/embed_fonts.py --docx out.docx --verify` to re-check an existing file.
- `references/agent-compatibility.md`: installation, invocation, runtime adaptation and acceptance checks for each supported client.
- `scripts/skill_portability.py`: stdlib-only package checker, DOCX smoke test, client-folder installer and ZIP packager.
- `agents/openai.yaml`: Chinese display name and default prompt for Codex and ChatGPT.
- `requirements.txt`: Python dependency for DOCX output.
- `scripts/ensure_fonts.py`: detects 仿宋_GB2312, 楷体_GB2312 and 方正小标宋简体 and installs the bundled copies per user when missing (`--check` only reports).
