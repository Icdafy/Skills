# Minute Templates

## A. Project Or Due-Diligence Interview Minutes

Use this as the default for company/project interviews, founder interviews, expert interviews, investment due diligence, financing talks, roadshows, and technical briefings.

```text
{公司/项目名称}项目访谈纪要
　　访谈时间：{时间}
　　访谈地点：{地点}
　　访谈对象：{姓名、单位、职务}
　　访谈人员：{我方人员}

本次访谈围绕{核心议题}展开，现将主要内容纪要如下：

一、项目/公司基本情况
（一）成立背景与发展历程
（二）团队与组织架构
（三）股权及治理情况

二、核心产品、技术与业务模式
（一）核心产品及应用场景
（二）技术路线与竞争优势
（三）商业模式与收入构成

三、市场、客户与竞争格局
（一）目标市场与行业趋势
（二）客户拓展与订单情况
（三）竞争对手与差异化优势

四、生产、交付与运营情况
（一）产能与供应链
（二）交付周期与服务模式
（三）成本控制与管理机制

五、财务、融资与资本规划
（一）营收、毛利、现金流或回款情况
（二）融资需求与资金用途
（三）上市、股权激励或后续资本计划

六、后续事项
```

Delete sections that are unsupported by the transcript. Add domain sections when needed, such as `军工业务`, `管网巡检`, `液氢动力`, `生物制造`, `商业航天`, or `毫米波通信`. Do not add a standalone risk or pending-verification section by default; integrate source-supported constraints into the relevant topic.

## B. Compact Interview Minutes

Use when the transcript is short or only covers one topic.

```text
{公司/项目名称}访谈纪要
　　访谈时间：{时间或未提及}
　　访谈地点：{地点或未提及}
　　访谈对象：{对象或未提及}
　　访谈人员：{人员或未提及}

一、主要内容
（一）{主题一}
（二）{主题二}
（三）{主题三}

二、访谈总结/后续事项
```

## C. Work Meeting Minutes

Use when the source focuses on decisions, responsibilities, schedules, and internal coordination. Keep the same opening fields requested for interview minutes unless the user explicitly asks for `会议时间/会议地点/参会人员`.

```text
{事项名称}会议纪要
　　访谈时间：{时间}
　　访谈地点：{地点}
　　访谈对象：{对象或事项相关方}
　　访谈人员：{参会人员}

一、会议背景
二、会议主要内容
三、会议议定事项
四、任务分工及时间安排
五、待协调事项
```

Use an action-item table only when the user needs a tabular task list and the content is truly row/column data:

| 序号 | 事项 | 责任方 | 时间节点 | 备注 |
| --- | --- | --- | --- | --- |

## D. Q&A Record To Formal Minutes

Use Q&A format whenever the source contains clear question-answer exchanges, including expert interviews, due-diligence Q&A, roadshow Q&A, or raw transcripts marked by `问/答`, `Q/A`, interviewer/interviewee turns, or repeated question prompts. Do not require the user to ask for Q&A preservation.

Polish Q&A into formal official Chinese:

- Rewrite questions into concise, neutral issue prompts. Preserve the question's scope and constraints.
- Rewrite answers into complete factual paragraphs. Remove oral filler, repetition, and personal tone.
- Keep numbers, dates, caveats, and uncertain status.
- If several consecutive questions cover the same matter, group them under one second-level heading.
- If an answer is unclear, write conservatively with `未明确` rather than adding verification language.

```text
{公司/项目名称}访谈纪要
　　访谈时间：{时间或未提及}
　　访谈地点：{地点或未提及}
　　访谈对象：{对象或未提及}
　　访谈人员：{人员或未提及}

本次访谈主要采取问答方式进行，现将主要内容纪要如下：

一、访谈问答
（一）关于{主题}
问：{经正式化整理后的问题}
答：{经正式化整理后的答复}
```

When the transcript mixes topic narration and Q&A, keep the narrative sections first, then add `访谈问答` for the explicit exchanges. If Q&A content duplicates earlier topic sections, keep the more complete version in Q&A and avoid repeating the same paragraph twice.

## Section Library

Choose sections that match the source:

- Basic: `项目概况`, `公司基本情况`, `访谈背景与参与方`.
- People: `创始人与核心团队`, `组织架构与人员配置`, `人力管理体系`.
- Product/tech: `核心产品及应用场景`, `核心技术与产品优势`, `研发体系与技术壁垒`.
- Market: `行业痛点与市场机遇`, `客户结构及拓展情况`, `竞争格局分析`.
- Operations: `生产与产能`, `供应链管理体系`, `交付与运维服务`, `库存管理`.
- Finance/capital: `经营核心数据`, `回款及应收账款`, `融资需求与资金用途`, `股权结构与上市规划`.
- Ending: `访谈总结`, `核心结论`, `后续事项`, `后续行动计划`, `待办事项清单`.

## Output Depth

Choose the level that fits the user's request and source length:

- `完整纪要`: default for voice transcripts and due-diligence interviews. Preserve all material topics and details; use multiple first-level sections.
- `标准纪要`: use when the transcript is short or the user asks for a normal meeting memo. Keep the main topics and important figures.
- `简版纪要`: use only when the user explicitly asks for a short version. Keep core conclusions, action items, and key constraints.

When the user says `完整总结`, `不要遗漏`, `详细纪要`, or provides a long transcript, default to `完整纪要`.

## Field Fallbacks

If metadata is missing from the transcript:

- Title: infer from the project/company/topic when clear; otherwise use `{主题}会议纪要`.
- Time/place/object/personnel: write `未提及`.
- Interviewee list: if the transcript contains names but no roles, use `访谈对象：{姓名/职务未明确}`.
- Opening metadata: never use a table; use four indented lines.
