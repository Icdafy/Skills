# Transcript Workflow

Use this reference when the source is raw voice transcription, meeting recording text, ASR output, or pasted dialogue with filler, repeated speech, partial speaker labels, or unclear structure.

## Three-Pass Method

1. **Pass 1: Restore the record**
   - Identify meeting type, project/company name, participants, time, place, and core purpose.
   - Keep source attribution: distinguish `对方表示`, `我方提出`, `会议讨论`, and `资料显示` when the transcript makes this clear.
   - Preserve speaker labels if they affect responsibility, opinion ownership, or follow-up tasks.

2. **Pass 2: Build a fact ledger**
   - Basic facts: company/project, date, location, attendees, interviewee roles.
   - Business facts: product, technology, market, customers, orders, revenue, financing, equity, production, delivery, compliance.
   - Evidence facts: exact amounts, percentages, dates, time nodes, customer names, product names, model numbers, capacity, headcount.
   - Process facts: tasks, responsible parties, deadlines, documents to provide, next meeting arrangements.
   - Risk facts: uncertainties, conflicting claims, missing data, assumptions, legal/compliance constraints.

3. **Pass 3: Draft the formal minutes**
   - Reorganize by topic, not transcript order, except clear Q&A exchanges should remain in formal `问/答` format.
   - Merge repeated answers under one Q&A topic or memo section without deleting distinct facts.
   - Convert spoken fragments into complete sentences.
   - For Q&A, rewrite questions into neutral issue prompts and answers into complete official-style paragraphs.
   - Keep caveats: `预计`, `计划`, `意向`, `初步`, `尚未`, `需核实` must remain visible.
   - Add `待核实事项` if key figures or speaker attribution remain unclear.

## Voice Transcript Cleanup Rules

- Remove only filler, greetings, meeting logistics, obvious repetition, and timestamp noise.
- Do not remove offhand comments if they contain business facts, risks, negotiation positions, or action items.
- Convert `我们/他们/这个/那个` into named parties only when the referent is clear.
- If the transcript says `他说/老板说/他们那边说` and the speaker cannot be confidently identified, write `对方表示` or `会议交流中提及`.
- If ASR text corrupts a person/company/product name, preserve the closest source wording and add `名称待核实` only when the name matters.

## Attribution Rules

- Use `对方表示` for claims by interviewees or project companies.
- Use `我方提出` for questions, investment requirements, document requests, and follow-up needs from the user's side.
- Use `会议交流中提及` when attribution is mixed or unclear.
- Use `据介绍` for background facts supplied by one party but not independently verified.
- Do not write `会议认为` unless the transcript records a shared conclusion.

## Detail Preservation Rules

- Keep exact numbers and units. Do not round unless the source already uses an approximate expression.
- Keep ranges as ranges: `3000-4000万元`, `2-6个月`, `5%-10%`.
- Keep status differences: `在手订单`, `意向订单`, `已中标`, `已签约`, `已回款`, `预计营收`.
- Keep responsibility and timing together: `由财务部于4月前补充审计报告`.
- If a topic is discussed at length but lacks a conclusion, summarize the discussion and mark the unresolved point.

## Recommended Ending For Messy Transcripts

Use this ending when there are unresolved points:

```text
三、待核实事项
（一）{需核实的数据、名称、时间节点或责任方}
（二）{需补充的材料或后续确认事项}
```

Use this ending when there are clear tasks:

```text
三、后续行动计划
| 序号 | 事项 | 责任方 | 时间节点 | 备注 |
| --- | --- | --- | --- | --- |
```

If both exist, place `后续行动计划` before `待核实事项`.
