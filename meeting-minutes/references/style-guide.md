# Style Guide

## Core Stance

Write as a neutral recorder. Do not praise, criticize, infer intent, or add investment judgment unless the transcript explicitly supports it.

Use formal Chinese memo wording:

- Prefer status wording that reads like a finished official record: `目前`, `预计`, `计划`, `拟`, `已`, `尚未`, `未明确`, `未提及`.
- Avoid attribution and process wording in the final text: `据介绍`, `对方表示`, `对方认为`, `对方强调`, `会议交流中提及`, `访谈中提到`, `本次访谈了解到`.
- Avoid subjective or promotional wording: `我们认为`, `非常优秀`, `极具潜力`, `显然`, `毫无疑问`, `我觉得`, `对方很厉害`, `值得重点投资`.
- Use `会议认为` only when the transcript clearly records a collective meeting conclusion.

## Completeness Rules

- Preserve all material topics, especially numbers, dates, amounts, percentages, customer names, responsibilities, milestones, constraints, and action items.
- Merge repeated statements, but keep separate facts when their conditions differ.
- Keep caveats attached to the relevant claim: `预计`, `计划`, `意向`, `已签约`, `在手订单`, `尚未落地` are not interchangeable.
- If a field is missing, write `未提及`; if a claim is unclear, write `未明确` in the relevant sentence.
- If the transcript contains conflicting information, keep the conflict in the internal fact ledger and write the final paragraph conservatively without adding a separate `待核实事项` section unless the user asks for one.

## Transcript Conversion

- Remove greetings, pauses, filler words, repeated half-sentences, and transcription artifacts.
- Convert oral fragments into complete official sentences.
- Group content by topic rather than speaker order, but preserve clear Q&A exchanges as formal `问/答` records by default.
- For Q&A sections, formalize the question and answer rather than copying raw speech: questions should be concise issue prompts, and answers should be complete factual paragraphs with caveats retained.
- Do not over-compress: meeting minutes should be a complete structured record, not a short executive summary.
- Do not include unsupported background knowledge from memory or the internet.
- For raw ASR transcripts, perform the three-pass workflow in `transcript-workflow.md` before drafting.
- Do not add `转录质量说明`.

## Numbering And Form

- First level: `一、二、三、`.
- Second level: `（一）（二）（三）`.
- Third level: `1. 2. 3.`.
- Fourth level: `（1）（2）（3）`.
- Use short literal headings. Put interpretation and detail in the body, not in long headings.
- Do not use a table for the opening basic information. Use four indented lines in this order: `访谈时间`, `访谈地点`, `访谈对象`, `访谈人员`.
- Use tables only when the content is truly repeated row/column data and the user has not asked for plain official text.

## Typical Official Wording

- Lead sentence: `本次访谈围绕公司基本情况、核心产品、市场拓展、财务及融资规划等事项展开，现将主要内容纪要如下：`
- Neutral factual sentence: `公司现有...`; `项目计划...`; `产品主要应用于...`; `双方围绕...进行了沟通`.
- Uncertainty: `该事项尚未明确具体时间表`; `相关数据未明确具体口径`.
- Follow-up: `后续由...负责推进...`; `双方将继续围绕...开展沟通`.

## Quality Checklist

Before finalizing:

- Basic information is complete or explicitly marked `未提及`.
- The memo contains no first-person drafting voice.
- All key numbers and dates match the source.
- Claims are written as neutral record content without process-attribution phrases.
- Material constraints are not omitted, but they are integrated into the relevant topic instead of forced into a risk list.
- The ending section matches the source: summary, action items, or follow-up plan.
- The memo does not silently upgrade `意向`, `预计`, `计划`, or `初步沟通` into confirmed facts.
- The memo contains no final section named `风险与待核实事项`, `需重点关注的风险`, or `待核实事项清单` unless explicitly requested.
- The memo does not end paragraphs with formulaic sentences such as `需进一步核实` or `材料仍需补充核实`.
- If a source term may be misrecognized by ASR, keep the closest source wording and use `未明确` only when necessary.
