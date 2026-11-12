#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
style_check.py —— 公司情况章节语言与口吻扫描。

对成稿（含拖延判断套话检查；Markdown / 纯文本 / build_docx 用的 content.json）扫描语言红线、
外部指导口吻、材料版本和机械来源。仅扫描报告正文，不扫描来源台账或本方核查清单。
另扫公文数字（整数四位及以上加千位分隔符、数值范围两端带量级）、半角括号、不规范用词；排他论断与任职时点不明给警告。
机械命中是复核入口；法律义务、真实产品型号等按上下文判断，不盲目替换。
来源重复给出警告，需人工检查作用域；不因减少重复而取消必要的证据归属。

扫描项：
1. 称谓违规——"标的公司/标的企业/该标的/本标的/目标公司/拟投资标的/标的方"
2. 成对转折/递进连词——"不是……而是""并非……而是""不仅……而且"等对举句式
3. 结论标签——"核心结论：""核心观点："（结论直接写加粗判断句，不加标签）
4. 缺口占位语——"资料未披露""【待核查""【待补充""尚未提供"等：按三技能统一
   缺口规则，报告正文不得出现占位语，全部缺口在对话交付的"资料缺口与待核查
   清单"中提示（本脚本扫描的是报告正文，清单本身不在扫描范围）

另扫书面公文表述与硬逻辑（规则见 references/formal-expression.md、references/hard-logic.md）：
硬规则——对话痕迹、提示性引子与总结腔、口语及网络表达、空泛拔高与宣传黑话、主观人称、表情符号；
告警——铺垫式开头、机械连接词起段、第一人称判断、口语化程度词、程度词后无数字、单句超过130字、
导语列举项数与“N方面”不符、导语预告方面数与下文小标题数不符、表前缺引导句（后两项仅 content.json）。
书名号和引号内的原文照录不扫描。

用法：
    python style_check.py 章节正文.md
    python style_check.py content.json     # 自动提取全部 text/header/rows 后扫描
退出码：0 = 无硬规则命中（可能有警告）；1 = 有硬规则命中。
"""
import io
import json
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows GBK 控制台防乱码
except Exception:
    pass

# 数值范围：前一个数缺少“万/亿/%”而后一个数带有，如“7—10万元”“15—30%”；
# “8—10台”“2—3天”“7万—10万元”“15%—30%”不命中。
NUMBER_RANGE = re.compile(r"(?<![\d.,，])\d[\d,，.]*\s*[—–~～\-－]{1,2}\s*\d[\d,，.]*\s*(?:万|亿|%|％)")
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
# 半角括号紧跟中文或括住中文，如“方案(电池+燃料电池)”“能量密度(Wh/kg)”
HALF_WIDTH_PAREN = re.compile(r"[\u4e00-\u9fff]\s*\([^()（）\n]{0,40}\)|\([^()（）\n]*[\u4e00-\u9fff][^()（）\n]*\)")

# 写给读者的分析方法与告诫，如“应分别评价”“不能据此推导”
META_ADVICE = re.compile(r"应分别(?:评价|判断|理解|考察|核算)|不能据此|(?:评价|判断)[^。；;\n]{0,12}应(?:以|当以)[^。；;\n]{0,20}为(?:依据|准)")
# 内部资料文件名、问题编号与版本口径，如“业务回复Q5.1”“V10.0订单口径”“详版”
INTERNAL_SOURCE = re.compile(r"问题及回复|尽调回复|业务回复|详版|(?<![A-Za-z])Q\d+\.\d+|[vV]\d+(?:\.\d+)+(?:订单)?口径")

RULES = [
    ("拖延判断套话（完成当前分析，补证动作留正文外清单）",
     re.compile(r"(?:有待|尚待|仍待)(?:进一步)?(?:判断|验证|核实|核查|观察|分析)|"
                r"(?:需要|仍需|尚需|需)(?:后续|进一步|持续|在尽调阶段)[^。；;\n]{0,60}(?:判断|验证|核实|核查|观察|分析|关注|佐证)|"
                r"(?:后续|下一步|尽调阶段)[^。；;\n]{0,40}(?:判断|(?<!飞行)(?<!运行)(?<!试飞)(?<!场景)(?<!应用)(?<!地面)验证|核实|核查|观察|分析|关注)|"
                r"(?:仍需|尚需)[^。；;\n]{0,60}(?:判断|验证|核实|核查|观察|分析|佐证)|"
                r"尚需第三方[^。；;\n]{0,15}佐证")),
    ("称谓违规（只用'公司'或公司简称）",
     re.compile(r"标的公司|标的企业|该标的|本标的|目标公司|拟投资标的|标的方")),
    ("成对转折/递进连词（直接正面陈述）",
     re.compile(r"不是[^。；;\n]{1,40}而是|并非[^。；;\n]{1,40}而是|不仅[^。；;\n]{1,40}(而且|而是|还|更)|"
                r"不但[^。；;\n]{1,40}还|不止[^。；;\n]{1,40}而是|不光[^。；;\n]{1,40}还|"
                r"不只是[^。；;\n]{1,40}更|与其说[^。；;\n]{1,40}不如说")),
    ("结论标签（结论直接写加粗判断句，不加标签）",
     re.compile(r"核心结论[:：]|核心观点[:：]")),
    ("缺口占位语（缺口只在对话中提示，不写入报告）",
     re.compile(r"资料未披露|【待核查|【待补充|尚未提供|待进一步核实事项|建议后续尽调核查")),
    ("外部指导口吻（先完成分析；必要后续工作用本方计划表达）",
     re.compile(r"(?:建议(?:投资方|项目组|团队|我们)|(?:后续|下一步)?(?<![供适响反相对回呼])应(?:该|当)?(?!收))"
                r"[^。；;\n]{0,45}(?:核查|核实|核对|验证|关注|考察)|"
                r"后续(?:仍)?需[^。；;\n]{0,35}(?:核查|核实|核对|验证|关注|考察)")),
    ("材料版本痕迹（来源版本留在台账）",
     re.compile(r"(?:回复|材料|文件|详版|初稿|报告)[^。；;\n]{0,12}[vV]\s*\d+(?:\.\d+)*|"
                r"[vV]\s*\d+(?:\.\d+)*(?:版|列示|所载|显示|记载)|"
                r"第[一二三四五六七八九十\d]+轮(?:尽调|补充)?回复")),
    ("机械来源句（直接陈述事实，必要归属在段首或表前交代）",
     re.compile(r"(?:公司)?在尽调(?:中)?回复(?:中)?|(?:回复|材料|详版)(?:所列|列示|记载)|"
                r"股东表列示|按回复|回复(?:更新)?(?:花名册|名册)|材料所列轮次|"
                r"根据[^。；;\n]{0,12}(?:材料|附件|文件)显示")),
    ("编辑留言（落实意见后移出正文）",
     re.compile(r"这部分(?:整体)?(?:都)?(?:需要|重新)|写的有点乱|写得有点乱|"
                r"(?:ai|AI)[，,你].{0,20}(?:意见|重写)|你别再给意见")),
    ("数值范围省略量级或百分号（写成'7万—10万元''15%—30%'）", NUMBER_RANGE),
    ("数字未加千位分隔符（整数四位及以上写成'2,350万元''1,234.56'）", UNGROUPED_NUMBER),
    ("中文语境使用半角括号（改为全角'（）'）", HALF_WIDTH_PAREN),
    ("不规范用词（'来自于'改'来自'，'粘度/粘性/粘稠'改'黏度/黏性/黏稠'）",
     re.compile(r"来自于|粘度|粘性|粘稠")),
    ("方法论/告诫句（把应比较的直接比较完，写出结果）", META_ADVICE),
    ("内部资料痕迹（正文不写资料文件名、问题编号、版本口径）", INTERNAL_SOURCE),
]

# 警告项：需人工判断上下文，不影响退出码
WARN_RULES = [
    ("排他/绝对化论断（写明检索范围，并列出最接近的可比企业）",
     re.compile(r"(?:国内|国际|全球|行业内?|市场上?)(?:暂|尚)?(?:无|没有)[^。；;\n]{0,8}(?:竞品|竞争对手|同类产品|可比产品)|"
                r"唯一|首家|填补(?:国内)?空白|不可替代|无可替代")),
    ("保留性告诫（真实限制集中写一句，删去重复的“不能直接……”）",
     re.compile(r"不能直接(?:等同|视为|作为|用作|推导|套用)|不宜直接|不宜(?:据此|按)")),
    ("复述式收尾（只重复上文时删除，保留新判断）",
     re.compile(r"上述[^。；;\n]{0,12}(?:表明|说明|显示)|由此可见")),
    ("任职/持股时点不明（写“曾任/现任/至今仍持有”）",
     re.compile(r"(?<![目此之提当先以])前(?:为|系|任|是)")),
]

ATTRIBUTION = re.compile(r"公司(?:在尽调回复中)?(?:表示|解释|介绍|称)|据访谈|据公司介绍")


def attribution_warnings(pairs):
    """Locate dense repeated attribution; retain human judgment about source boundaries."""
    warnings = []
    streak = 0
    for loc, text in pairs:
        # Table cells need their own source scope, not a paragraph-streak heuristic.
        if loc.startswith('table.'):
            streak = 0
            continue
        count = len(ATTRIBUTION.findall(text))
        streak = streak + 1 if count else 0
        if count >= 3 or streak == 3:
            warnings.append((loc, '归属表达连续重复；检查能否在同段或同组内容前统一交代，保留必要证据边界。'))
    return warnings


# ---------------------------------------------------------------------------
# 书面公文表述与硬逻辑的机械扫描（规则见 references/formal-expression.md、
# references/hard-logic.md）。书名号《》和引号“”内的文字是原文照录，不扫描。
# ---------------------------------------------------------------------------
_QUOTED = re.compile(r"《[^》\n]*》|“[^”\n]*”")


class _OutsideQuotes:
    """在书名号、引号之外匹配（接口同 re.Pattern.search）。"""

    def __init__(self, pattern):
        self.pattern = re.compile(pattern)

    def search(self, text):
        masked = _QUOTED.sub(lambda m: "　" * len(m.group(0)), text)
        return self.pattern.search(masked)


RULES += [
    ("对话痕迹（正文从事实开始、以事实结束，不写开场白和结束语）",
     _OutsideQuotes(r"^\s*(?:好的|当然|没问题)[，,。！!]|以下是(?:为您|我|根据您)|希望(?:以上|这份|对您)|"
                    r"如(?:有|需)(?:任何)?(?:疑问|其他需要|进一步(?:的)?(?:帮助|修改|调整))|"
                    r"请(?:随时)?(?:告知|告诉)我|您|小编")),
    ("提示性引子或总结腔（删去引子，直接写事实）",
     _OutsideQuotes(r"值得注意的是|值得一提的是|需要指出的是|需要注意的是|需要强调的是|不难看出|不难发现|"
                    r"众所周知|毋庸置疑|毫无疑问|总而言之|综上所述|简而言之|换句话说|换言之[，,]|"
                    r"可以说[，,]|总的来说|这充分(?:说明|表明|体现)")),
    ("口语或网络表达（改为书面语，见 formal-expression.md 第四部分）",
     _OutsideQuotes(r"说白了|简单来说|通俗地讲|通俗来说|讲真|靠谱|给力|很牛|厉害|烧钱|砸钱|赚钱|搞定|"
                    r"踩坑|干货|接地气|拉满|躺赢|内卷|卖得(?:不错|很好|好)|做得(?:不错|很好)|"
                    r"没法|啥|咋|挺(?:好|大|多|高|强)|蛮(?:好|大|多|高)|差不多|大概(?!率)")),
    ("空泛拔高或宣传黑话（换成规模、增速、订单、对标等事实）",
     _OutsideQuotes(r"前景广阔|空间巨大|潜力巨大|巨大的?(?:发展)?潜力|大有可为|未来可期|不可限量|遥遥领先|"
                    r"独一无二|里程碑意义|划时代|革命性|颠覆性|赋能|抓手|打法|风口|蓝海|降维打击|"
                    r"弯道超车|驶入快车道|保驾护航|添砖加瓦|颗粒度|心智")),
    ("主观人称（不写‘笔者’‘我认为’，直接下判断并给依据）",
     _OutsideQuotes(r"笔者|本人认为|个人认为|我认为|我觉得|我们觉得")),
    ("表情或装饰符号（正文不使用）",
     re.compile("[\U0001F300-\U0001FAFF☀-➿⭐⬆✅❌]")),
]

WARN_RULES += [
    ("第一人称判断（改为‘整体来看’‘总体判断’，或直接写判断）",
     _OutsideQuotes(r"我们认为|我们判断|我们相信|我们看好|我们预计")),
    ("口语化程度词或模糊表达（写数值，或删去）",
     _OutsideQuotes(r"很多|非常|十分|特别(?!是在|约定|条款|权利|表决|决议|说明|行政|许可|设备|法人|国债)|其实|"
                    r"好像|似乎|或许|也许|左右(?=[，。；）]|$)")),
]

_PARA_OPENERS = [
    ("铺垫式开头（首句直接写判断或事实，背景写具体年份和文件）",
     re.compile(r"^\s*(?:\*\*)?(?:随着|伴随着?|在[^，。]{2,24}(?:大背景|背景下|浪潮下|趋势下)|近年来|当今|如今|当前，随着)")),
    ("机械连接词起段（并列用‘一是、二是’或‘××方面，’，递进靠内容承接）",
     re.compile(r"^\s*(?:\*\*)?(?:首先|其次|再次|再者|最后|此外|另外|除此之外|与此同时|总之)[，,]")),
]
_DEGREE = re.compile(r"大幅|显著|明显(?:提升|提高|增长|增加|下降|降低|改善|优于|高于|低于)|快速增长|高速增长|持续攀升|急剧|迅猛")
_LEAD_COUNT = re.compile(
    r"([^，。；：:\n]{2,70}?)(?:等)?(两|二|三|四|五|六|七|八)(?:个|大|条|项|类)?"
    r"(?:方面|部分|维度|层面|角度)(?:梳理|展开|说明|列示|分析|介绍|阐述|论证|[。；，])")
_CN_NUM = {"两": 2, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8}
_SENT_SPLIT = re.compile(r"[。；！？!?]")
_HEADING_LEVEL = {"h1": 1, "h2": 2, "h3": 3, "h4": 4}


def _lead_items(fragment):
    """导语中用顿号和末尾一个‘和/及/与/以及’并列的项数；看不出并列时返回 0。"""
    fragment = re.split(r"从|按|围绕|体现在|包括|分为|涵盖|覆盖", fragment)[-1]
    pieces = [p for p in fragment.split("、") if p.strip()]
    if not pieces:
        return 0
    count = len(pieces)
    if re.search(r"(?:和|及|与|以及)", pieces[-1]):
        count += 1
    return count if count >= 2 else 0


def expression_warnings(pairs, data=None):
    """表述与逻辑的结构性告警：起段方式、程度词缺数字、超长句、导语与项数、表前引导句。"""
    out = []
    for loc, text in pairs:
        if loc.startswith("table"):
            continue
        body = text.strip()
        if not body or body.startswith("#") or body.startswith("|"):
            continue
        for name, pattern in _PARA_OPENERS:
            if pattern.search(body):
                out.append((loc, f"{name}：…{body[:24]}…"))
        for sentence in _SENT_SPLIT.split(_QUOTED.sub("", body)):
            if _DEGREE.search(sentence) and not re.search(r"\d", sentence):
                out.append((loc, f"程度词后没有数字（补数值或删去程度词）：…{sentence.strip()[:30]}…"))
            if len(sentence) > 130:
                out.append((loc, f"单句超过130字（拆成每句一个主谓结构）：…{sentence.strip()[:24]}…"))
        for m in _LEAD_COUNT.finditer(body):
            listed = _lead_items(m.group(1))
            if listed and listed != _CN_NUM[m.group(2)]:
                out.append((loc, f"导语列举{listed}项，却写‘{m.group(2)}方面’，核对项数与下文小标题：…{m.group(0)[-28:]}…"))
    if isinstance(data, dict):
        blocks = [b for b in data.get("blocks", []) if isinstance(b, dict)]
        for i, blk in enumerate(blocks):
            kind = blk.get("type")
            if kind == "table":
                prev = blocks[i - 1].get("type") if i else None
                if prev in _HEADING_LEVEL or prev in (None, "table", "pagebreak"):
                    out.append((f"blocks[{i}].table", "表前缺引导句（用一句话交代这张表看什么）"))
            if kind == "p":
                m = _LEAD_COUNT.search(str(blk.get("text") or "") + str(blk.get("lead") or ""))
                level = next((_HEADING_LEVEL[b.get("type")] for b in reversed(blocks[:i])
                              if b.get("type") in _HEADING_LEVEL), None)
                prev_is_heading = i and blocks[i - 1].get("type") in _HEADING_LEVEL
                if not (m and level and prev_is_heading):
                    continue
                children = 0
                for later in blocks[i + 1:]:
                    lv = _HEADING_LEVEL.get(later.get("type"))
                    if lv is None:
                        continue
                    if lv <= level:
                        break
                    if lv == level + 1:
                        children += 1
                if children and children != _CN_NUM[m.group(2)]:
                    out.append((f"blocks[{i}].p", f"导语预告‘{m.group(2)}方面’，下文同级小标题为{children}个，二者须一致"))
    return out


def _texts_from_json(data):
    """从 build_docx 的 content 结构提取全部待扫描文本。"""
    out = []
    for blk in data.get("blocks", []):
        t = blk.get("type")
        if blk.get("lead"):
            out.append((f"blocks[{t}].lead", str(blk["lead"])))
        if blk.get("text"):
            out.append((f"blocks[{t}]", str(blk["text"])))
        for item in blk.get("items", []) or []:
            out.append(("blocks[bullet]", str(item)))
        if t == "table":
            for h in blk.get("header") or []:
                out.append(("table.header", str(h)))
            for row in blk.get("rows", []) or []:
                for cell in row:
                    out.append(("table.cell", str(cell)))
    if data.get("summary"):
        out.append(("summary", str(data["summary"])))
    return out


def main():
    if len(sys.argv) < 2:
        print("用法: python style_check.py 章节正文.md|content.json")
        return 2
    path = sys.argv[1]
    with io.open(path, "r", encoding="utf-8") as f:
        raw = f.read()

    data = None
    if path.lower().endswith(".json"):
        data = json.loads(raw)
        pairs = _texts_from_json(data)
    else:
        pairs = [(f"L{i}", line) for i, line in enumerate(raw.splitlines(), 1) if line.strip()]

    hits = 0
    for rule_name, pat in RULES:
        for loc, text in pairs:
            m = pat.search(text)
            if m:
                hits += 1
                frag = text.strip()
                if len(frag) > 50:
                    start = max(0, m.start() - 15)
                    frag = "…" + frag[start:start + 50] + "…"
                print(f"[FAIL] {rule_name} @ {loc}: {frag}")

    for rule_name, pat in WARN_RULES:
        for loc, text in pairs:
            m = pat.search(text)
            if m:
                frag = text[max(0, m.start() - 15):m.end() + 15].strip()
                print(f"[WARN] {rule_name} @ {loc}: …{frag}…")

    for loc, warning in expression_warnings(pairs, data):
        print(f"[WARN] {warning} @ {loc}")

    for loc, warning in attribution_warnings(pairs):
        print(f"[WARN] {warning} @ {loc}")

    if hits:
        print(f"\n共 {hits} 处命中，逐条改写后重扫。")
        return 1
    print("[OK] 语言及口吻硬规则未命中；仍需人工检查表文关系、分析质量和证据边界。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
