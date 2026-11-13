#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_yiti_text.py —— 议题正文语言扫描。

扫描议题 JSON（create_yiti_docx.py 的输入）或 Markdown/纯文本成稿，逐段检查：

硬规则（命中即退出码 1，成稿前必须改掉）：
1. 悬置/拖延收尾句——"需要后续进行判断""有待进一步研判""后续持续关注""视情况而定"等。
   议题每段以事实或结论收尾，不留"以后再判断"的尾巴。
2. 对举句式——"不是……而是""并非……而是""不仅……而且""而非""而不是"等。
   直接陈述"是什么""为什么必要"，不先否定再肯定。
3. 引子与总结套话——"值得注意的是""需要指出的是""综上所述""总的来说""首先，""其次，"。
   流程叙述可用"先……随后……之后……最后……"，不在此列。
4. 口语与自称——"大家""非常"、感叹号、"本议题""本文"。
5. 数字未加千位分隔符——整数部分四位及以上须每三位加半角逗号（"1,980万元""141,583.56元"）；
   年份、日期、文号、编号、代码、电话、标准号等标识性数字不命中。

6. 口语——"我们""搞""说白了""比如说""看一下""这块"等；议题用"我司""我方"和书面动词。
7. 机器腔——"让我们""接下来，""以下是""希望以上""至关重要""不可或缺""日新月异""保驾护航"等
   对话腔、总结腔和抒情套话；议题只陈述事实、依据、判断和请求。
8. Markdown 标记——JSON 字段内出现"# ""- ""* ""```"等标记（加粗只用 **…**）。

警告（按上下文复核，不强制）：
6. 语气偏激进——"必然""势必""彻底""毫无""严重恶化""濒临"等绝对化、情绪化用词。
7. 语气偏保守——"或许""也许""似乎""恐怕""不排除"，或同一句叠加两个以上推测词。
8. 单侧否定铺垫——"并非""不是"（未与"而是"成对时）。
9. 半角括号括住中文、全角数字或全角百分号（生成器会自动转半角，文本稿需手工改）。
10. 拔高与营销词——"最佳""最优""痛点""海量""全方位""巨大"等；改为可核对的事实或有度的判断。
11. 破折号——议题不用破折号补充说明（书名号内的文件名除外）。
12. 逻辑结构（JSON 稿）——导语未以"具体如下："类引出句收尾；文末未见明确提请句；
    审议机构前后不一致；一级、二级标题序号不连续；"一是……"缺"二是"或序号跳号；
    请示事项中的金额、比例前文未出现；简称定义后未再使用；段落未以句号、冒号或分号收尾。

用法：
    python check_yiti_text.py spec.json
    python check_yiti_text.py draft.md
退出码：0 = 无硬规则命中（可能有警告）；1 = 有硬规则命中。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # Windows GBK 控制台防乱码
    except Exception:
        pass

_CLAUSE = r"[^。；;！!？?\n]"

# 数字千位分隔：整数部分四位及以上须自个位起每三位加半角逗号，如“2,350万元”“1,234.56”。
# 年份、日期、文号、编号、代码、电话、证件号、标准号等标识性数字不分节，不命中；
# 十一位及以上的纯数字串按编号处理。
_UNGROUPED_DIGITS = re.compile(
    r"(?<![\d,.A-Za-z_〔\[])(?<![A-Za-z][ \-/])(?<!\d[-－/:：])[1-9]\d{3,9}(?![\d,A-Za-z_〕\]])")
_YEAR_CONTEXT = re.compile(
    r"\s*(?:年|届|级|版|款|[-－/.]\d|[、，,和及与至到—–\-－~～]\s*(?:19|20)\d{2}(?!\d)|[|｜)）]|$)")
_STANDARD_PREFIX = re.compile(r"[A-Za-z][A-Za-z/]*\s?[\d.]+\s?[—–\-－]$")
_ID_PREFIX = re.compile(
    r"(?:代码|编号|编码|证号|账号|帐号|文号|型号|序号|批号|邮编|电话|手机|传真|注册号|登记号|专利号|"
    r"合同号|订单号|No\.?|NO\.?)[:：]?\s*$")
_ID_SUFFIX = re.compile(r"\s*(?:号|\.[A-Za-z])")


class _UngroupedNumber:
    """整数部分四位及以上、未按三位分节加千位分隔符的数字（接口同 re.Pattern）。"""

    def finditer(self, text):
        for m in _UNGROUPED_DIGITS.finditer(text):
            digits = m.group(0)
            if len(digits) == 4 and 1900 <= int(digits) <= 2099 and (
                    _YEAR_CONTEXT.match(text, m.end())
                    or _STANDARD_PREFIX.search(text[max(0, m.start() - 20):m.start()])):
                continue
            if _ID_PREFIX.search(text[max(0, m.start() - 8):m.start()]) or _ID_SUFFIX.match(text, m.end()):
                continue
            yield m

    def search(self, text):
        return next(self.finditer(text), None)


UNGROUPED_NUMBER = _UngroupedNumber()

HARD_RULES = [
    ("悬置/拖延收尾句（以事实或结论收尾，删去'后续再判断'类尾句）", re.compile(
        r"(?:有待|尚待|仍待|留待)(?:后续|进一步|下一步|今后)?(?:判断|研判|观察|评估|论证|核实|验证|明确|确认|跟踪)|"
        rf"(?:需要|仍需|尚需|还需|需)(?:后续|进一步|持续|下一步|今后|结合后续|视后续|根据后续|密切){_CLAUSE}{{0,30}}"
        r"(?:判断|研判|观察|评估|关注|跟踪|论证|核实|验证|确认|明确)|"
        r"(?:后续|下一步|今后|未来)(?:仍|还)?(?:需要|需|将|应|有待)?(?:持续|进一步|密切)(?:关注|跟踪|观察|研判|判断|评估)|"
        r"(?:后续|下一步|今后)(?:仍|还)?(?:需要|需|有待)(?:关注|跟踪|观察|研判|判断|评估)|"
        r"视(?:后续|具体|实际)?情况(?:而定|再定|另行)|"
        r"(?:暂|尚|目前)(?:无法|难以|不能)(?:判断|研判|确定|评估)")),
    ("对举句式（直接陈述是什么，不先否定再肯定）", re.compile(
        rf"不是{_CLAUSE}{{1,40}}而是|并非{_CLAUSE}{{1,40}}而是|并不是{_CLAUSE}{{1,40}}而是|"
        rf"不仅{_CLAUSE}{{1,40}}(?:而且|而是|还|更|也)|不但{_CLAUSE}{{1,40}}(?:而且|还|也)|"
        rf"不只是{_CLAUSE}{{1,40}}(?:更|还|而是)|不止{_CLAUSE}{{1,40}}(?:而是|还)|不光{_CLAUSE}{{1,40}}还|"
        rf"与其说{_CLAUSE}{{1,40}}不如说|不在于{_CLAUSE}{{1,40}}而在于|而不是|而非")),
    ("引子与总结套话", re.compile(
        r"值得注意的是|需要指出的是|需要说明的是|综上所述|总的来说|总而言之|众所周知|不难看出|首先[，,]|其次[，,]")),
    ("口语与自称", re.compile(r"大家|非常(?!规|态|设|任)|[！!]|本议题|本文(?!件)")),
    ("口语（改用'我司''我方'和书面动词）", re.compile(
        r"我们|你们|咱们|搞|说白了|简单来说|简单地说|换句话说|说实话|老实说|比如说|打个比方|"
        r"(?:看|说|讲|聊|谈|沟通|了解|梳理|确认|核实|汇报|介绍|对接|讨论)一下|这一?块|那一?块|"
        r"靠谱|给力|踩坑|差不多|没问题|没什么|挺(?:好|大|多|高|低)|蛮(?:好|大|多|高)")),
    ("机器腔（删去对话、总结和抒情套话，只陈述事实、依据、判断和请求）", re.compile(
        r"让我们|接下来[，,]|下面将|本节将|以下是|希望以上|如有需要|如需进一步|总结一下|简而言之|"
        r"由此可见|显而易见|毋庸置疑|不言而喻|不可否认|至关重要|不可或缺|举足轻重|扮演着|"
        r"在当今|日新月异|蓬勃发展|方兴未艾|如火如荼|浓墨重彩|添砖加瓦|保驾护航|锦上添花|"
        r"迈上新台阶|新篇章|里程碑式|注入(?:新的?|强劲)?(?:动力|活力|动能)|插上[^。；]{0,6}翅膀")),
    ("数字未加千位分隔符（整数四位及以上写成'1,980万元''141,583.56元'）", UNGROUPED_NUMBER),
]

WARN_RULES = [
    ("语气偏激进（以数据支撑判断，改用'显著''较大''大概率'等有量化依据的表述）", re.compile(
        r"必然|必将|势必|注定|彻底|毫无|绝对|一定会|肯定会|严重恶化|急剧恶化|濒临|崩盘|全面失败|完全(?:不|没有|无法|丧失|失败)")),
    ("语气偏保守（去掉无依据的推测词，直接陈述事实与判断）", re.compile(r"或许|也许|似乎|恐怕|不排除")),
    ("单侧否定铺垫（改为正面陈述）", re.compile(r"并非|不是")),
    ("半角括号括住中文（改为全角'（）'）", re.compile(r"\([^()（）\n]*[\u4e00-\u9fff][^()（）\n]*\)")),
    ("全角数字或全角百分号（改为半角，数字统一 Times New Roman）", re.compile(r"[０-９％]")),
    ("拔高与营销词（改为可核对的事实，或'较高''较为'等有度的判断）", re.compile(
        r"最佳|最优|最符合|最大化|痛点|海量|全方位|巨大|完美|极大|无可比拟|首屈一指|遥遥领先|"
        r"无与伦比|颠覆式|革命性|划时代")),
    ("破折号（议题不用破折号补充说明，改为括注或另起一句）", re.compile(r"——(?![^《》]*》)")),
]

MARKDOWN = re.compile(r"^\s*(?:#{1,6}\s|[-*+]\s|>\s|```)|`[^`\n]+`")
BODIES = "投委会|专题会|董事会|党委会|投决会|总办会|各合伙人"
SUBMIT_TO = re.compile(r"(?:提请|报请|请)(" + BODIES + r")(?:予以)?(?:审议|表决|批示|审定)")
RECIPIENT = re.compile(r"^\s*(" + BODIES + r")[：:]\s*$")
REQUEST = re.compile(r"提请|报请|请予?审议|请批示|请审定")
LEAD_OUT = re.compile(r"如下[：:]\s*$")
CN_NUM = "一二三四五六七八九十"
H1_SERIAL = re.compile(r"^\s*([一二三四五六七八九十]+)、")
H2_SERIAL = re.compile(r"^\s*[（(]([一二三四五六七八九十]+)[）)]")
ENUM = re.compile(r"([一二三四五六七八九十])是")
ABBR = re.compile(r"[（(](?:以下)?简称[“‘]?([^”’）)“或]{1,20})[”’]?(?:或[“‘]([^”’）)]{1,20})[”’])?[）)]")
AMOUNT = re.compile(r"\d[\d,]*(?:\.\d+)?\s*(?:万元|亿元|元|%|万股|股)")
PARA_END = "。：:；;）)》”"


def _cn_to_int(text: str) -> int:
    if text == "十":
        return 10
    if text.startswith("十"):
        return 10 + CN_NUM.index(text[1]) + 1
    if text.endswith("十"):
        return (CN_NUM.index(text[0]) + 1) * 10
    if "十" in text:
        return (CN_NUM.index(text[0]) + 1) * 10 + CN_NUM.index(text[2]) + 1
    return CN_NUM.index(text) + 1


def _enum_warnings(text: str, loc: str) -> list[str]:
    """同一段内"一是、二是……"必须从一起、连续、至少两项。"""
    seq = [CN_NUM.index(m.group(1)) + 1 for m in ENUM.finditer(text)
           if not re.search(r"[第其之唯同统单逐不]$", text[:m.start()])]
    if 1 not in seq:
        return []
    seq = seq[seq.index(1):]
    out = []
    for a, b in zip(seq, seq[1:] + [1]):
        if a == 1 and b == 1:
            out.append(f"[警告] 逻辑结构：有'一是'而无'二是'，单项不用序数（{loc}）")
        elif b not in (1, a + 1):
            out.append(f"[警告] 逻辑结构：'一是、二是……'序号不连续（{loc}）")
    return out


def structure_warnings(data: dict) -> list[str]:
    """JSON 稿的逻辑结构复核：导语、提请、审议机构、标题序号、数字闭合、简称。"""
    warn = []
    intro = data.get("intro")
    intro = [intro] if isinstance(intro, str) else list(intro or [])
    blocks = [b for b in (data.get("blocks") or []) if isinstance(b, dict)]
    paras = [(f"intro[{i}]", _strip_markup(t)) for i, t in enumerate(intro, 1)]
    paras += [(f"blocks[{i}]", _strip_markup(str(b.get("text", ""))))
              for i, b in enumerate(blocks, 1) if b.get("type", "para") == "para" and b.get("text")]
    body = "\n".join(t for _, t in paras)

    if intro and blocks and not LEAD_OUT.search(_strip_markup(intro[-1])):
        warn.append("[警告] 逻辑结构：导语末句未以'具体如下：''具体情况如下：'等引出句收尾（intro）")
    if paras and not REQUEST.search("\n".join(t for _, t in paras[-3:])):
        warn.append("[警告] 逻辑结构：文末未见明确提请句（如'现提请投委会审议。'）")

    bodies = [m.group(1) for m in SUBMIT_TO.finditer(body)]
    recipient = RECIPIENT.match(str(data.get("recipient") or ""))
    if recipient:
        bodies.append(recipient.group(1))
    distinct = sorted(set(bodies))
    if len(distinct) > 1:
        warn.append(f"[警告] 逻辑结构：审议机构前后不一致{distinct}，主送、导语与提请句应为同一机构")

    last_h1, last_h2 = 0, 0
    request_start = None
    for i, b in enumerate(blocks, 1):
        kind, text = b.get("type", "para"), str(b.get("text", ""))
        if kind == "h1":
            m = H1_SERIAL.match(text)
            if m:
                n = _cn_to_int(m.group(1))
                if n != last_h1 + 1:
                    warn.append(f"[警告] 逻辑结构：一级标题序号不连续『{text[:16]}』（blocks[{i}]）")
                last_h1, last_h2 = n, 0
            else:
                warn.append(f"[警告] 逻辑结构：一级标题缺'一、'类序号『{text[:16]}』（blocks[{i}]）")
            if re.search(r"请示事项|提请审议事项", text):
                request_start = i
        elif kind == "h2":
            m = H2_SERIAL.match(text)
            if m:
                n = _cn_to_int(m.group(1))
                if n != last_h2 + 1:
                    warn.append(f"[警告] 逻辑结构：二级标题序号不连续『{text[:16]}』（blocks[{i}]）")
                last_h2 = n

    warn.extend(_enum_warnings(body, "正文"))
    for loc, text in paras:
        if len(text) > 30 and text.rstrip()[-1:] not in PARA_END:
            warn.append(f"[警告] 逻辑结构：段落未以句号、冒号或分号收尾『…{text.rstrip()[-12:]}』（{loc}）")

    if request_start:
        def norm(value):
            return re.sub(r"[,\s]", "", value)
        before = norm(" ".join([str(data.get("title", ""))] + intro + [
            " ".join([str(b.get("text", "")), str(b.get("caption", ""))]
                     + [str(c) for c in (b.get("header") or [])]
                     + [str(c) for r in (b.get("rows") or []) for c in r])
            for b in blocks[:request_start - 1]]))
        for i, b in enumerate(blocks[request_start:], request_start + 1):
            for m in AMOUNT.finditer(str(b.get("text", ""))):
                figure = re.match(r"[\d.]+", norm(m.group(0))).group(0)
                if figure not in before:
                    warn.append(f"[警告] 逻辑结构：请示事项中的『{m.group(0)}』前文未出现，"
                                f"请求中的数字须在前文有来历（blocks[{i}]）")

    for m in ABBR.finditer(body):
        for name in filter(None, m.groups()):
            if name != "公司" and body.count(name) <= 1 + body[:m.start()].count(name):
                warn.append(f"[警告] 逻辑结构：简称『{name}』定义后未再使用，删去简称或后文改用简称")
    return warn

# "无实现可能""不可能""可能性"中的"可能"是名词，不计入推测词。
SPECULATION = re.compile(r"(?<![无不现])可能(?!性)|或将|或许|也许|有望|预计|大概率|估计")
PAIRED = re.compile(r"(?:不是|并非)" + _CLAUSE + r"{1,40}而是")


def _strip_markup(text: str) -> str:
    return text.replace("**", "")


def iter_spec_texts(data: dict):
    """Yield (location, text) for every text unit in a create_yiti_docx.py spec."""
    for key in ("title", "submit_line", "recipient"):
        if data.get(key):
            yield key, str(data[key])
    intro = data.get("intro")
    for i, text in enumerate([intro] if isinstance(intro, str) else (intro or []), start=1):
        yield f"intro[{i}]", text
    yield from _iter_blocks(data.get("blocks") or [], "blocks")
    for i, name in enumerate(data.get("attachments") or [], start=1):
        yield f"attachments[{i}]", str(name)
    for a_idx, appendix in enumerate(data.get("appendices") or [], start=1):
        if appendix.get("title"):
            yield f"appendices[{a_idx}].title", str(appendix["title"])
        yield from _iter_blocks(appendix.get("blocks") or [], f"appendices[{a_idx}].blocks")


def _iter_blocks(blocks: list, prefix: str):
    for b_idx, block in enumerate(blocks, start=1):
        loc = f"{prefix}[{b_idx}]"
        if block.get("text"):
            yield loc, str(block["text"])
        if block.get("caption"):
            yield loc + ".caption", str(block["caption"])
        for c_idx, cell in enumerate(block.get("header") or [], start=1):
            yield f"{loc}.header[{c_idx}]", str(cell)
        for r_idx, row in enumerate(block.get("rows") or [], start=1):
            for c_idx, cell in enumerate(row, start=1):
                yield f"{loc}.rows[{r_idx}][{c_idx}]", str(cell)


def iter_plain_texts(text: str):
    for line_no, line in enumerate(text.splitlines(), start=1):
        if line.strip():
            yield f"第{line_no}行", line


def scan(units) -> tuple[list[str], list[str]]:
    hard, warn = [], []
    for loc, raw in units:
        text = _strip_markup(raw)
        for label, pattern in HARD_RULES:
            for m in pattern.finditer(text):
                hard.append(f"[硬规则] {label}：『{m.group(0)}』（{loc}）")
        for label, pattern in WARN_RULES:
            for m in pattern.finditer(text):
                if label.startswith("单侧否定") and PAIRED.search(text):
                    continue
                warn.append(f"[警告] {label}：『{m.group(0)}』（{loc}）")
        for sentence in re.split(r"[。；;！!？?]", text):
            hits = SPECULATION.findall(sentence)
            if len(hits) >= 2:
                warn.append(f"[警告] 同一句叠加推测词{hits}，删去多余推测：『{sentence.strip()[:40]}』（{loc}）")
    return hard, warn


def scan_spec(data: dict) -> tuple[list[str], list[str]]:
    hard, warn = scan(iter_spec_texts(data))
    for loc, raw in iter_spec_texts(data):
        for m in MARKDOWN.finditer(str(raw)):
            hard.append("[硬规则] Markdown 标记（JSON 字段只写正文，加粗用 **…**）："
                        f"『{m.group(0).strip()}』（{loc}）")
    return hard, warn + structure_warnings(data)


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    path = Path(sys.argv[1])
    raw = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".json":
        hard, warn = scan_spec(json.loads(raw))
    else:
        hard, warn = scan(iter_plain_texts(raw))
        lines = raw.splitlines()
        bodies = {m.group(1) for m in SUBMIT_TO.finditer(raw)}
        bodies |= {m.group(1) for m in map(RECIPIENT.match, lines) if m}
        if len(bodies) > 1:
            warn.append(f"[警告] 逻辑结构：审议机构前后不一致{sorted(bodies)}，主送、导语与提请句应为同一机构")
        warn.extend(_enum_warnings(raw, "全文"))
    for line in hard + warn:
        print(line)
    print(f"硬规则命中 {len(hard)} 处，警告 {len(warn)} 处。")
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main())
