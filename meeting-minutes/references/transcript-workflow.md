# Transcript Workflow

Use this reference when the source is raw voice transcription, meeting recording text, ASR output, or pasted dialogue with filler, repeated speech, partial speaker labels, or unclear structure.

## Three-Pass Method

1. **Pass 1: Restore the record**
   - Identify meeting type, project/company name, participants, time, place, and core purpose.
   - Keep source ownership in the internal ledger when it affects responsibility or caveats, but do not carry process-attribution phrases into the final minutes.
   - Preserve speaker labels if they affect responsibility, questions, answers, or follow-up tasks.

2. **Pass 2: Build a fact ledger**
   - Basic facts: company/project, date, location, attendees, interviewee roles.
   - Business facts: product, technology, market, customers, orders, revenue, financing, equity, production, delivery, compliance.
   - Evidence facts: exact amounts, percentages, dates, time nodes, customer names, product names, model numbers, capacity, headcount.
   - Process facts: tasks, responsible parties, deadlines, documents to provide, next meeting arrangements.
   - Constraint facts: uncertainties, conflicting claims, missing data, assumptions, legal/compliance constraints, and other material limitations.

3. **Pass 3: Draft the formal minutes**
   - Reorganize by topic, not transcript order, except clear Q&A exchanges should remain in formal `问/答` format.
   - Merge repeated answers under one Q&A topic or memo section without deleting distinct facts.
   - Convert spoken fragments into complete sentences.
   - For Q&A, rewrite questions into neutral issue prompts and answers into complete official-style paragraphs.
   - Keep caveats: `预计`, `计划`, `意向`, `初步`, `尚未`, `未明确` must remain visible.
   - Convert `需核实`-type source wording to conservative final wording such as `未明确` when necessary; do not add a separate pending-verification section by default.
   - If a paragraph would end with an unresolved-status sentence such as `尚不明确`, `需要资料作为口径依据`, or `对标口径未明确`: delete it when it adds nothing, or, when the point genuinely needs later verification, turn it into a parenthetical note in `（）` attached to the relevant sentence.
   - Give every heading at every level the two-character indent (two full-width spaces in plain text).

## Voice Transcript Cleanup Rules

- Remove only filler, greetings, meeting logistics, obvious repetition, and timestamp noise.
- Do not remove offhand comments if they contain business facts, constraints, negotiation positions, or action items.
- Convert `我们/他们/这个/那个` into named parties only when the referent is clear.
- If the transcript says `他说/老板说/他们那边说` and the speaker cannot be confidently identified, write the final sentence without attribution and preserve only the factual content that is clear.
- If ASR text corrupts a person/company/product name, preserve the closest source wording and use `名称未明确` only when the name matters.

## Q&A Detection Rules

Treat the source as Q&A when any of these are present:

- Repeated `问：/答：`, `Q:/A:`, `问题：/回答：`, or similar labels.
- Alternating interviewer/interviewee speaker labels with repeated question prompts.
- Roadshow, expert interview, or due-diligence dialogue where questions define the structure of the source.

When Q&A is detected:

- Preserve the exchange as `问：` and `答：` records.
- Group consecutive exchanges by topic when that improves readability.
- Keep narrative sections outside the Q&A when the source contains both narrative briefing and Q&A.
- Do not dissolve explicit Q&A into only synthesized prose unless the user asks for a non-Q&A memo.

## Final-Wording Rules

- Do not write `对方表示`, `对方认为`, `对方强调`, `据介绍`, `会议交流中提及`, or `访谈中提到`.
- Use direct neutral records: `公司现有...`, `项目计划...`, `产品主要应用于...`, `双方围绕...进行了沟通`.
- Use `我方提出` only when the source records a concrete requirement, document request, or task raised by the user's side and the ownership matters.
- Do not write `会议认为` unless the transcript records a shared conclusion.

## Detail Preservation Rules

- Keep exact numbers and units. Do not round unless the source already uses an approximate expression.
- Keep ranges as ranges: `3000-4000万元`, `2-6个月`, `5%-10%`.
- Keep status differences: `在手订单`, `意向订单`, `已中标`, `已签约`, `已回款`, `预计营收`.
- Keep responsibility and timing together: `由财务部于4月前补充审计报告`.
- If a topic is discussed at length but lacks a conclusion, summarize the discussion with `未明确` or omit the unsupported conclusion.

## Recommended Ending For Messy Transcripts

Do not add a default `待核实事项` ending. Keep unclear points inside the relevant paragraph, woven into the sentence (`相关时间节点未明确`) or as a parenthetical note when later verification is needed:

```text
项目预计于2026年三季度完成中试线建设（具体时间节点尚不明确，有待后续资料核实）。
```

Do not leave `尚不明确`、`需要资料作为口径依据`、`对标口径未明确` as standalone sentences closing a paragraph — delete them or convert them into the parenthetical form above.

Use this ending when there are clear tasks:

```text
　　三、后续行动计划
| 序号 | 事项 | 责任方 | 时间节点 | 备注 |
| --- | --- | --- | --- | --- |
```
