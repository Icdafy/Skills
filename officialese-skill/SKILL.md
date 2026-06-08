---
name: officialese-skill
description: Draft, revise, and format Chinese state-owned enterprise official documents and Word files using a company-style officialese format. Use for SOE or Chinese corporate/government-style documents such as 通知, 请示, 报告, 函, 会议纪要, 附件说明, formal redrafting, official tone polishing, DOC/DOCX layout, Chinese public-document typography, fonts, margins, headings, attachments, signatures, and page numbers.
---

# Officialese Skill

Use this skill to create or revise Chinese SOE-style official documents with both correct wording and Word layout.

## Workflow

1. Identify the document type: 通知, 请示, 报告, 函, 会议纪要, 方案, 制度, 附件, or internal presentation material.
2. Draft in formal, concise official language: state the basis, purpose, matter, requirements, responsible parties, and timing.
3. Apply the format rules in `references/format-rules.md`.
4. Use wording patterns in `references/writing-patterns.md` when the task is drafting, polishing, or converting informal text into officialese.
5. For Word output, use the fonts in `assets/fonts/` and the sample template in `assets/templates/文件字体格式.doc`.
6. For a quick DOCX draft, run `scripts/create_official_docx.py`, then inspect and fine-tune in Word when strict page-number placement or legacy `.doc` compatibility is required.

## Required Format Priorities

- Prefer the uploaded company sample over generic GB/T 9704 defaults when they differ.
- Preserve Chinese punctuation and numbering hierarchy: `一、`, `（一）`, `1.`, `（1）`.
- Keep titles short and literal. Put explanatory content in the body, not the title.
- Do not use casual, promotional, or emotional wording.
- Check the final file visually for font fallback, page margins, fixed line spacing, attachment labels, seal/signature area, and page numbers.

## Bundled Resources

- `references/format-rules.md`: typography, margins, spacing, headings, attachment, signature, and page-number rules extracted from the uploaded sample.
- `references/writing-patterns.md`: concise drafting patterns for common SOE official documents.
- `assets/fonts/方正小标宋简体.ttf`: title font.
- `assets/fonts/楷体_GB2312.ttf`: subtitle and second-level heading font.
- `assets/fonts/simfang.ttf`: FangSong-compatible body font fallback.
- `assets/templates/文件字体格式.doc`: original uploaded format sample.
- `scripts/create_official_docx.py`: deterministic starter DOCX generator.
