---
name: meeting-minutes
description: Convert Chinese meeting, interview, due-diligence interview, project communication, roadshow, and voice-transcript notes into complete, neutral, formal meeting minutes or 访谈纪要. Use when the user asks to 整理会议纪要, 访谈纪要, 尽调访谈纪要, 项目会议纪要, 线上会议纪要, or to turn raw speech transcription into official Chinese memo-style minutes.
---

# Meeting Minutes

## Overview

Use this skill to turn rough Chinese meeting transcripts into neutral, complete, official-style minutes. Preserve facts, numbers, named entities, responsibilities, risks, open questions, and action items; remove only spoken filler, repetition, and conversational scaffolding.

## Required References

Read these references as needed:

- `references/transcript-workflow.md`: voice-transcript conversion workflow, fact ledger, attribution, and verification protocol.
- `references/style-guide.md`: neutrality, official tone, completeness, and quality checks.
- `references/minute-templates.md`: output skeletons and section libraries.
- `references/sample-patterns.md`: distilled patterns from the user's uploaded meeting-minute samples.

Use `scripts/clean_transcript.py` only when the user provides a plain text transcript file and basic whitespace/filler cleanup is useful before drafting. Use `scripts/extract_word_outline.ps1` only when expanding or checking template samples from `.doc` or `.docx` files on Windows with Microsoft Word installed.

## Workflow

1. Identify the meeting type from the source:
   - Project/interview/due-diligence minutes: default for company, expert, founder, finance, R&D, sales, HR, or supply-chain interviews.
   - Work meeting minutes: use when the source contains decisions, responsibilities, and next steps.
   - Roadshow or project briefing minutes: use when the source is a presentation plus Q&A.
   - Q&A record: when the source contains clear question-answer exchanges, preserve them as a formal `问/答` section by default. Rewrite both questions and answers in concise official Chinese, while keeping the original meaning, facts, caveats, and attribution.

2. Extract a fact ledger before drafting:
   - Basic information: title/project/company, time, place, interviewer/attendees, interviewee, organization, role.
   - Substance: background, team, technology/product, market, customers, competition, production/operation, finance, financing, equity, compliance, risks, requests, decisions, action items.
   - Evidence details: dates, amounts, percentages, order values, capacities, milestones, named customers, responsible parties.
   - Uncertainties: contradictory statements, missing fields, unclear speaker attribution, figures needing verification.
   For long or messy transcripts, follow the detailed protocol in `references/transcript-workflow.md`.

3. Clean the transcript conservatively:
   - Remove filler words, repeated fragments, greetings, scheduling chatter, and transcription artifacts.
   - Keep every material claim, caveat, number, date, condition, responsibility, and risk.
   - Do not convert speculation into fact. Use `据介绍`, `对方表示`, `会议交流中提及`, `尚需进一步核实`, or `未提及` where appropriate.

4. Choose the output structure from `references/minute-templates.md`.
   - Default to a formal synthesized memo, not a raw transcript.
   - If the source contains Q&A exchanges, include a formal Q&A section instead of dissolving the exchange into ordinary paragraphs.
   - Use first-level Chinese numbering: `一、二、三、`.
   - Use second-level numbering: `（一）（二）（三）`.
   - Use third-level numbering: `1. 2. 3.` when detail density requires it.

5. Draft in neutral official Chinese:
   - Start with basic meeting information and a concise lead paragraph when appropriate.
   - Group content by topic, not by transcript order, unless chronology is essential or the source is a Q&A exchange.
   - For Q&A content, keep `问：` and `答：`; polish the wording into official written Chinese and remove oral filler without omitting substantive details.
   - Use concise paragraphs; avoid promotional adjectives and first-person wording.
   - Include an ending section only when supported by the source: `访谈总结`, `核心结论`, `待办事项清单`, `后续行动计划`, or `待核实事项`.

6. Run a final quality check:
   - Every important transcript topic appears in the minutes.
   - Numbers, dates, names, and units match the source.
   - Missing information is marked, not invented.
   - The tone is neutral and formal throughout.
   - The result can stand alone without the raw transcript.
   - If the user gave raw voice transcription, include `待核实事项` when speaker attribution, figures, or time nodes are uncertain.

## Output Rules

When the user provides transcript text directly, return the polished minutes in the chat unless they request a file. When the user provides a Word/text file and asks for a document, create the requested file and preserve the same structure in the document.

Do not include drafting commentary before or after the minutes unless the user asks for explanation. If the transcript is incomplete or contradictory, add a short `待核实事项` section at the end instead of asking many clarifying questions.

## Default Heading Pattern

```text
{项目/公司名称}{项目/尽调/线上}访谈纪要
访谈时间：{时间或未提及}
访谈地点：{地点或未提及}
访谈人员：{我方人员或未提及}
访谈对象：{对方人员、单位、职务或未提及}

本次访谈围绕{核心议题}展开，现将主要内容纪要如下：

一、访谈基本信息
二、主要内容
三、核心结论/后续事项/待核实事项
```

For investment/project interviews, prefer topic sections such as project background, product and technology, market and competition, business model, team and operations, financing and equity, risks, and follow-up actions.
