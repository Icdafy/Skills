# Style Guide

## Core Stance

Write as a neutral recorder. Do not praise, criticize, infer intent, or add investment judgment unless the transcript explicitly supports it.

Use formal Chinese memo wording:

- Prefer: `据介绍`, `对方表示`, `会议交流中提及`, `目前`, `预计`, `计划`, `尚未明确`, `需进一步核实`.
- Avoid: `我们认为`, `非常优秀`, `极具潜力`, `显然`, `毫无疑问`, `我觉得`, `对方很厉害`, `值得重点投资`.
- Use `会议认为` only when the transcript clearly records a collective meeting conclusion.

## Completeness Rules

- Preserve all material topics, especially numbers, dates, amounts, percentages, customer names, responsibilities, milestones, risks, and constraints.
- Merge repeated statements, but keep separate facts when their conditions differ.
- Keep caveats attached to the relevant claim: `预计`, `计划`, `意向`, `已签约`, `在手订单`, `尚未落地` are not interchangeable.
- If a field is missing, write `未提及`; if a claim is unclear, write `待核实`.
- If the transcript contains conflicting information, state the conflict in `待核实事项`, not in a hidden note.

## Transcript Conversion

- Remove greetings, pauses, filler words, repeated half-sentences, and transcription artifacts.
- Convert oral fragments into complete official sentences.
- Group content by topic rather than speaker order, but preserve clear Q&A exchanges as formal `问/答` records by default.
- For Q&A sections, formalize the question and answer rather than copying raw speech: questions should be concise issue prompts, and answers should be complete factual paragraphs with caveats retained.
- Do not over-compress: meeting minutes should be a complete structured record, not a short executive summary.
- Do not include unsupported background knowledge from memory or the internet.
- For raw ASR transcripts, perform the three-pass workflow in `transcript-workflow.md` before drafting.

## Numbering And Form

- First level: `一、二、三、`.
- Second level: `（一）（二）（三）`.
- Third level: `1. 2. 3.`.
- Use short literal headings. Put interpretation and detail in the body, not in long headings.
- Use tables for participant lists and action items when the output medium supports tables.

## Typical Official Wording

- Lead sentence: `本次访谈围绕公司基本情况、核心产品、市场拓展、财务及融资规划等事项展开，现将主要内容纪要如下：`
- Source attribution: `对方表示，...`; `据介绍，...`; `会议交流中提及，...`.
- Uncertainty: `该事项尚未明确具体时间表`; `相关数据仍需结合后续资料进一步核实`.
- Follow-up: `后续需重点关注...`; `建议进一步核实...`; `由...负责推进...`.

## Quality Checklist

Before finalizing:

- Basic information is complete or explicitly marked `未提及`.
- The memo contains no first-person drafting voice.
- All key numbers and dates match the source.
- Claims remain attributed when they come from one party.
- Risks, constraints, and unresolved issues are not omitted.
- The ending section matches the source: summary, action items, or pending verification.
- The memo does not silently upgrade `意向`, `预计`, `计划`, or `初步沟通` into confirmed facts.
- If a source term may be misrecognized by ASR, the memo either keeps the original term or marks it `待核实`.
