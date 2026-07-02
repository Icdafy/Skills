# Sample Patterns

This reference distills the user's uploaded Word samples. Do not copy sample wording verbatim unless it is a generic structure label.

## Corpus Observations

The analyzed corpus includes project/interview minutes across advanced manufacturing, commercial aerospace, biotechnology, low-altitude economy, hydrogen power, communications, radar, robotics, and due-diligence interviews. The dominant style is a neutral investment/project memo, not a verbatim transcript.

The user's newer WeiYang samples add a stricter official-document requirement: use the typography and hierarchy in `official-document-format.md`; do not use participant tables in the opening metadata; avoid process-attribution phrases and forced risk/pending-verification endings.

Some uploaded files, such as `商天大纲终版.doc`, `商天行研大纲.docx`, and `商业航天研究报告v2.docx`, are research outline/report materials rather than meeting-minute templates. Use them only as supplemental evidence for industry-analysis section design when the user's transcript explicitly requires a research-report angle; do not let them override the meeting-minute front matter, neutral transcript-conversion workflow, or memo structure.

Common front matter:

- Title: `{公司/项目名称}访谈纪要`, `{公司/项目名称}项目访谈纪要`, `{项目名称}会议纪要`, or `{公司名称}项目尽调访谈纪要`.
- Metadata: `访谈时间`, `访谈地点`, `访谈对象`, `访谈人员`; sometimes `同行人员` or `被访谈人` can be normalized into these fields.
- Opening metadata: no table; four indented lines.
- Lead paragraph: longer due-diligence samples use `本次访谈围绕...展开，现将...整理如下：`.

Common body structures:

- Short project interviews: `一、主要内容`, with second-level sections for company, product, market, production, finance, cooperation.
- Deep due-diligence interviews: topic-specific first-level sections such as background, organization, business segments, technology, competition, finance, equity, listing plan, constraints, and follow-up.
- Expert interviews or raw Q&A sources: preserve clear question-answer exchanges as formal `问/答` sections, while polishing both questions and answers into official written Chinese.
- Follow-up/action-oriented meetings: end with `后续行动计划` or `待办事项清单` when tasks are clear. Do not add a `待核实事项` ending by default.

## Per-Sample Structural Notes

- `超验-薛老师访谈纪要.docx`: short expert/project interview. Six first-level sections: company background, industrialization progress, future planning, equity/IP, development expectation, production landing.
- `鼎宣科技访谈纪要260408终.doc`: narrative project interview with metadata and同行人员. Less formal numbering in body; ends with strategic planning, financing progress, and a reserve-project recommendation.
- `方元明鑫访谈纪要12.9.docx`: compact template: `主要内容`, then financing, products, customers, production, team, operations, advantages, future planning.
- `访谈纪要（华岳生物）.docx`: compact biotech interview: company/team, business/technology, project results, production/funding, finance/IP, cooperation points.
- `访谈纪要（西安超验）.docx`: short technical-commercial interview: business role, market/technology, production/R&D, development expectations/team.
- `访谈纪要（西安超验）-海老师.docx`: more detailed technical interview: background/team, technology/product advantages, market/competition, production/commercialization, qualification/constraint.
- `访谈纪要-12.3.doc`: raw Q&A record. Preserve the `问/答` structure by default, but rewrite each question and answer in concise official Chinese and group related exchanges by topic.
- `访谈纪要-胡总、海老师.docx`: merged multi-person summary. It separates founder/business content from technical expert content; useful when one meeting has multiple interviewees.
- `访谈纪要-天权时空联合创始人&CTO-4.21.26.docx`: project memo with two-line title, basic info, project overview, industry pain points, financing/fund-use table style.
- `访谈纪要-同尘和光-260508.docx`: project memo emphasizing core advantages, application scenarios, commercialization, orders, and financing.
- `访谈纪要-伊隆纬特-4.24.26.docx` and `伊隆维特访谈纪要.docx`: communications project memo; useful sections include technology route, advantages, market layout, milestones, financing, constraint.
- `毫米波高速数据连接器.docx`: complete project memo with ten first-level sections, including project positioning, product stages, technology, applications, team/resources, commercialization, competition, financing, discussion points, and follow-up actions.
- `华岳访谈纪要-海斯夫与巨子生物.docx`: multiple external counterpart interviews in one memo; organize by counterpart and topic.
- `华岳访谈纪要-香兰素专家.docx`: expert interview with summary and investment suggestion; keep expert claims as neutral memo content and separate them from unsupported conclusions.
- `华岳访谈纪要-销售总监.docx`: role-specific interview; sections follow personal background, motivation, work plan, Q&A.
- `华岳生物访谈.docx`: concise synthesized memo without full front matter; uses industry background, company, production/operations, market/cooperation, financing, goals/constraints.
- `会议纪要-斡丰流体初访-260512.docx`: project meeting memo with basic information, project overview, basic company situation, financing/investment concerns.
- `空天动力电推进器线上会议纪要4.1.26.docx`: online meeting memo; uses meeting time/place; ends with action items and investment/financing follow-up.
- `雷创图原访谈纪要.docx`: radar project memo with policy background, technical/product advantages, cooperation, equity, funding, investment exchange, timelines.
- `龙行智巡访谈纪要.docx`: robotics project memo with company background, product system, competitive advantages, and company requests.
- `星用空间项目路演.docx`: roadshow minutes; structure follows project background, technical path, business model, low-altitude economy layout, progress/team, financing, investment highlights.
- `旭航氢能访谈纪要20260313.doc`: hydrogen project memo; emphasizes landing urgency, industry chain, application scenarios, team, planning, financing.
- `液氢动力项目情况及发展规划讨论会议纪要.docx`: discussion meeting memo; useful ending structure: challenges and follow-up action plan.
- `云脉智能访谈.docx`: concise project interview without full front matter; company/project, application results, market advantages, financing/business plan, cooperation model.
- `因诺科技` role interviews: deep due-diligence template. Each interview focuses on one function: finance, R&D, sales, HR, supply chain, founder strategy, or technical expert.

## Template Selection Heuristics

- If the transcript contains company financing, product, market, and team content, use Project Or Due-Diligence Interview Minutes.
- If the transcript has only a few broad topics, use Compact Interview Minutes.
- If it contains explicit tasks/responsible parties/time nodes, add `后续行动计划` or `待办事项清单`.
- If it is a multi-interviewee transcript, split by person only when their topics differ materially; otherwise synthesize by topic.
- If it is raw Q&A, first extract topics, then rewrite into formal `问/答` sections.
- If it is voice transcription without headings, infer headings from recurring topics and use `未提及` or `未明确` for unclear metadata inside the relevant line or paragraph.
- If it is a role-specific due-diligence interview, structure around the interviewee's function, such as finance, R&D, sales, HR, supply chain, founder strategy, or technical expert.

## Common Endings

- No forced conclusion: many short samples end after the last topic.
- `访谈总结`: use when the source supports a neutral wrap-up.
- `核心结论`: use for due-diligence synthesis, especially when there are several judgments to preserve.
- `待办事项清单`: use when responsibilities and follow-up tasks are clear.
- Do not add `待核实事项` by default; use it only when the user explicitly asks for a verification list.
