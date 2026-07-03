---
name: meeting-minutes
description: Convert Chinese meeting, interview, due-diligence interview, project communication, roadshow, Q&A, and voice-transcript notes into complete, neutral, formal Chinese meeting minutes or 访谈纪要, with WeiYang official document formatting for Word output. Use when the user asks to 整理会议纪要, 访谈纪要, 尽调访谈纪要, 项目会议纪要, 线上会议纪要, 问答纪要, or to turn raw speech transcription into official Chinese memo-style minutes.
---

# Meeting Minutes

## Overview

Use this skill to turn rough Chinese meeting transcripts into neutral, complete, official-style minutes. Preserve facts, numbers, named entities, responsibilities, conditions, caveats, and action items; remove only spoken filler, repetition, and conversational scaffolding.

For Word document output, follow the WeiYang official document format: only use 方正小标宋简体, 黑体, 楷体_GB2312, 仿宋_GB2312, and Times New Roman for Arabic numerals.

## Required References

Read these references as needed:

- `references/transcript-workflow.md`: voice-transcript conversion workflow, fact ledger, Q&A handling, and final wording rules.
- `references/style-guide.md`: neutrality, official tone, completeness, prohibited phrasing, and quality checks.
- `references/minute-templates.md`: output skeletons and section libraries.
- `references/official-document-format.md`: WeiYang official document typography, margins, numbering hierarchy, and Word-output font rules.
- `references/sample-patterns.md`: distilled patterns from the user's uploaded meeting-minute samples.

Use `scripts/clean_transcript.py` only when the user provides a plain text transcript file and basic whitespace/filler cleanup is useful before drafting. Use `scripts/detect_qna.py` when a plain text transcript may contain question-answer exchanges and the structure is not obvious. Use `scripts/build_minutes_docx.py` when creating a Word document from finished minutes text or auditing a generated DOCX. Use `scripts/extract_word_outline.ps1` only when expanding or checking template samples from `.doc` or `.docx` files on Windows with Microsoft Word installed.

## Workflow

1. Identify the meeting type from the source:
   - Project/interview/due-diligence minutes: default for company, expert, founder, finance, R&D, sales, HR, or supply-chain interviews.
   - Work meeting minutes: use when the source contains decisions, responsibilities, and next steps.
   - Roadshow or project briefing minutes: use when the source is a presentation plus Q&A.
   - Q&A record: when the source contains clear question-answer exchanges, automatically output the exchange as formal `问/答` records. Rewrite both questions and answers in concise official Chinese while keeping the original meaning, facts, numbers, conditions, and caveats.

2. Extract a fact ledger before drafting:
   - Basic information: title/project/company, time, place, interviewee/object, interviewer/personnel, organization, role.
   - Substance: background, team, technology/product, market, customers, competition, production/operation, finance, financing, equity, compliance, requests, decisions, action items, and material constraints.
   - Evidence details: dates, amounts, percentages, order values, capacities, milestones, named customers, responsible parties.
   - Uncertainties: contradictory statements, missing fields, unclear speaker attribution, and unclear figures. Keep these in the internal ledger unless the user asks for an issues list.
   For long or messy transcripts, follow the detailed protocol in `references/transcript-workflow.md`.

3. Clean the transcript conservatively:
   - Remove filler words, repeated fragments, greetings, scheduling chatter, and transcription artifacts.
   - Keep every material claim, caveat, number, date, condition, responsibility, and constraint.
   - Do not convert speculation into fact. Use factual neutral sentences and status words such as `拟`, `计划`, `预计`, `已`, `尚未`, `未明确`, and `未提及` as supported by the source.
   - Do not use process-attribution phrases such as `对方表示`, `对方认为`, `对方强调`, `据介绍`, `访谈中提到`, or `会议交流中提及` in the final minutes.

4. Choose the output structure from `references/minute-templates.md`.
   - Default to a formal synthesized memo, not a raw transcript.
   - If the source contains Q&A exchanges, include a formal Q&A section instead of dissolving the exchange into ordinary paragraphs.
   - Use first-level Chinese numbering: `一、二、三、`.
   - Use second-level numbering: `（一）（二）（三）`.
   - Use third-level numbering: `1. 2. 3.` when detail density requires it.
   - All headings at every level (`一、`, `（一）`, `1.`, `（1）`) must begin with a two-character indent: in chat/plain-text output prefix each heading with two full-width spaces (`　　`); in Word output use the two-character first-line indent. Never place a heading flush with the left margin.
   - Do not add a standalone `风险与待核实事项`, `需重点关注的风险`, `待核实事项清单`, or `转录质量说明` section unless the user explicitly requests it.

5. Draft in neutral official Chinese:
   - Start with basic meeting information and a concise lead paragraph when appropriate.
   - Opening basic information must contain `访谈时间`, `访谈地点`, `访谈对象`, and `访谈人员` in that order. Do not use a table. In plain text, prefix each line with two full-width spaces; in Word output, use a two-character first-line indent.
   - Group content by topic, not by transcript order, unless chronology is essential or the source is a Q&A exchange.
   - For Q&A content, keep `问：` and `答：`; polish the wording into official written Chinese and remove oral filler without omitting substantive details.
   - Use concise paragraphs; avoid promotional adjectives and first-person wording.
   - Include an ending section only when supported by the source, such as `访谈总结`, `核心结论`, `后续事项`, or `后续行动计划`. Do not end paragraphs with formulaic verification language such as `需进一步核实` or `材料仍需补充核实`.
   - When a paragraph would otherwise end with an unresolved-status sentence such as `尚不明确`, `需要资料作为口径依据`, `对标口径未明确`, or similar pending-verification wording: delete the sentence if it adds no substantive information; if the uncertainty is material and genuinely needs later verification, rewrite it as a brief note inside Chinese parentheses `（）` attached to the end of the relevant sentence, for example `（该数据口径尚不明确，有待后续资料核实）`. Never leave such wording as a bare standalone sentence closing the paragraph.

6. Run a final quality check:
   - Every important transcript topic appears in the minutes.
   - Numbers, dates, names, and units match the source.
   - Missing information is marked, not invented.
   - The tone is neutral and formal throughout.
   - The result can stand alone without the raw transcript.
   - Every heading at every level starts with the two-character indent (two full-width spaces in plain text; two-character first-line indent in Word).
   - No paragraph ends with a bare unresolved-status sentence (`尚不明确`, `需要资料作为口径依据`, `对标口径未明确` and the like); each such point is either deleted or converted into a parenthetical note in `（）`.
   - The final minutes contain no `对方表示/认为/强调`, `访谈中提到`, forced risk list, pending-verification list, or transcript-quality note.
   - If creating DOCX, run `scripts/build_minutes_docx.py --audit-only <docx>` or build with `--audit` to check fonts and digit runs.

## Output Rules

When the user provides transcript text directly, return the polished minutes in the chat unless they request a file. When the user provides a Word/text file and asks for a document, create the requested file and preserve the same structure in the document.

Do not include drafting commentary before or after the minutes unless the user asks for explanation. If the transcript is incomplete or contradictory, keep uncertain items as `未提及` or `未明确` in the relevant sentence, or as a short parenthetical note in `（）` when the point needs later verification; do not add a separate pending-verification section by default and do not close paragraphs with bare unresolved-status sentences.

## Default Heading Pattern

```text
{项目/公司名称}{项目/尽调/线上}访谈纪要
　　访谈时间：{时间或未提及}
　　访谈地点：{地点或未提及}
　　访谈对象：{对象人员、单位、职务或未提及}
　　访谈人员：{我方人员或未提及}

　　本次访谈围绕{核心议题}展开，现将主要内容纪要如下：

　　一、主要内容
　　二、访谈问答
　　三、核心结论/后续事项
```

For investment/project interviews, prefer topic sections such as project background, product and technology, market and competition, business model, team and operations, financing and equity, constraints, and follow-up actions. Use `访谈问答` automatically when the source is clearly Q&A.
