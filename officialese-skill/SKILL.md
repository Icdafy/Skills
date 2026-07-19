---
name: officialese-skill
description: Draft, revise, and format Chinese state-owned enterprise official documents and Word files using a company-style officialese format. Use for SOE or Chinese corporate/government-style documents such as 通知, 请示, 报告, 函, 会议纪要, 附件说明, 上行文, 平行文, 下行文, formal redrafting, official tone polishing, DOC/DOCX layout, Chinese public-document typography, fonts, margins, headings, attachments, signatures, and page numbers.
---

# Officialese Skill

Use this skill to create or revise Chinese SOE-style official documents with both correct wording and Word layout. The local rules are based on the uploaded company sample `assets/templates/文件字体格式.doc`, the bundled official fonts, and the company onboarding training PDF's 公文格式 rules.

## Workflow

1. Identify the document type: 通知, 请示, 报告, 函, 会议纪要, 方案, 制度, 附件, or internal presentation material.
2. Identify 行文方向 before drafting:
   - Explicit `上行文` in the user prompt, or 请示/报告/报送/呈报/报批/申请批复 style wording, means use 上行文口吻.
   - Explicit `平行文`, or 函/商请/函询/函告/同级/不相隶属 coordination wording, means use 平行文口吻.
   - Explicit `下行文`, or 通知/通报/决定/批复/印发/下发/部署/要求 wording, means use 下行文口吻.
   - If no direction signal appears, default to normal formal SOE written style.
3. When the task is to draft or polish text, output the document content directly in the detected tone. Do not preface the answer with a long explanation of the detection unless the user asks for analysis.
4. Draft in formal, concise official language: state the basis, purpose, matter, requirements, responsible parties, and timing.
5. Apply the format rules in `references/format-rules.md`.
6. Use wording patterns in `references/writing-patterns.md` when the task is drafting, polishing, or converting informal text into officialese.
7. For Word output, use the fonts in `assets/fonts/` and the sample template in `assets/templates/文件字体格式.doc`.
8. For a quick DOCX draft, run `scripts/create_official_docx.py`, then inspect and fine-tune in Word when strict page-number placement or legacy `.doc` compatibility is required.

## Required Format Priorities

- Prefer the uploaded company sample over generic GB/T 9704 defaults when they differ.
- Main title: 二号方正小标宋简体, centered.
- Subtitle or department line: 三号楷体_GB2312, centered.
- After subtitle/department line, leave one blank line before the recipient/body.
- Body: 三号仿宋_GB2312.
- Preserve Chinese punctuation and numbering hierarchy: `一、`, `（一）`, `1.`, `（1）`.
- First-level heading `一、xxxx`: 三号黑体, not bold.
- Second-level heading `（一）xxxx`: 三号楷体_GB2312, bold.
- Third-level heading `1.xxxx`: 三号仿宋_GB2312, bold.
- Fourth-level heading `（1）xxxx`: 三号仿宋_GB2312, not bold.
- Body paragraphs and numbered headings must start with a two-Chinese-character first-line indent. In plain-text output, prefix them with two full-width spaces `　　`; in DOCX output, use Word first-line indent.
- Keep titles short and literal. Put explanatory content in the body, not the title.
- Do not use casual, promotional, or emotional wording.
- Check the final file visually for font fallback, page margins, fixed line spacing, attachment labels, seal/signature area, and page numbers.

## Bundled Resources

- `references/format-rules.md`: typography, margins, spacing, headings, attachment, signature, and page-number rules extracted from the uploaded sample.
- `references/writing-patterns.md`: concise drafting patterns for common SOE official documents, including 上行文/平行文/下行文 tone detection.
- `assets/fonts/方正小标宋简体.ttf`: title font.
- `assets/fonts/楷体_GB2312.ttf`: subtitle and second-level heading font.
- `assets/fonts/simfang.ttf`: 仿宋_GB2312 body font.
- `assets/templates/文件字体格式.doc`: original uploaded format sample.
- `scripts/create_official_docx.py`: deterministic starter DOCX generator. On save it embeds the bundled 仿宋_GB2312 / 楷体_GB2312 into the file so it renders faithfully on machines without those fonts (方正小标宋 is licence-restricted and is skipped); embedding is verified and falls back to the un-embedded file if verification fails.
- `scripts/embed_fonts.py`: font embedder used by the generator; run `python scripts/embed_fonts.py --docx out.docx --verify` to re-check an existing file.
