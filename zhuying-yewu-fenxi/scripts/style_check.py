#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
style_check.py —— 立项报告章节语言红线机械扫描（三技能统一版）。

对成稿（含拖延判断套话检查；Markdown / 纯文本 / build_docx 用的 content.json）扫描语言红线与拖延判断套话，
输出命中位置，供交付前自检。只做机械匹配；结论前置、口径归因等仍需人工核对。

扫描项：
1. 称谓违规——"标的公司/标的企业/该标的/本标的/目标公司/拟投资标的/标的方"
2. 成对转折/递进连词——"不是……而是""并非……而是""不仅……而且"等对举句式
3. 结论标签——"核心结论：""核心观点："（结论直接写加粗判断句，不加标签）
4. 缺口占位语——"资料未披露""【待核查""【待补充""尚未提供"等：按三技能统一
   缺口规则，报告正文不得出现占位语，全部缺口在对话交付的"资料缺口与待核查
   清单"中提示（本脚本扫描的是报告正文，清单本身不在扫描范围）
5. 公文数字与用词——数值范围两端带量级/百分号（"7万—10万元"而非"7—10万元"），
   中文语境用全角括号，不用"来自于""粘度"等不规范词
6. 章节越界——出现"投资逻辑闭环""本项目拟围绕……布局"等本方投资表态
7. 方法论/告诫句（"应分别评价""不能据此"）与内部资料痕迹（"尽调回复""Q5.1""V10.0口径"）
警告（不影响退出码）：排他/绝对化论断（国内暂无竞品、唯一、首家）与复述式收尾。

用法：
    python style_check.py 章节正文.md
    python style_check.py content.json     # 自动提取全部 text/header/rows 后扫描
退出码：0 = 全部通过；1 = 有命中。
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
    ("数值范围省略量级或百分号（写成'7万—10万元''15%—30%'）", NUMBER_RANGE),
    ("中文语境使用半角括号（改为全角'（）'）", HALF_WIDTH_PAREN),
    ("不规范用词（'来自于'改'来自'，'粘度/粘性/粘稠'改'黏度/黏性/黏稠'）",
     re.compile(r"来自于|粘度|粘性|粘稠")),
    ("方法论/告诫句（把应比较的直接比较完，写出结果）", META_ADVICE),
    ("内部资料痕迹（正文不写资料文件名、问题编号、版本口径）", INTERNAL_SOURCE),
    ("本方投资表态越出本章职责（投资判断留立项结论）",
     re.compile(r"投资逻辑闭环|构成选择[^。；;\n]{0,15}(?:产业|投资)依据|本项目拟(?:围绕|布局|投资)")),
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
]


def _texts_from_json(data):
    """从 build_docx 的 content 结构提取全部待扫描文本。"""
    out = []
    for blk in data.get("blocks", []):
        t = blk.get("type")
        if blk.get("lead"):
            out.append((f"blocks[{t}].lead", str(blk["lead"])))
        if blk.get("text"):
            out.append((f"blocks[{t}]", blk["text"]))
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

    if path.lower().endswith(".json"):
        pairs = _texts_from_json(json.loads(raw))
    else:
        pairs = [(f"L{i}", line) for i, line in enumerate(raw.splitlines(), 1)]

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

    if hits:
        print(f"\n共 {hits} 处命中，逐条改写后重扫。")
        return 1
    print("[OK] 称谓 / 对举连词 / 结论标签 / 缺口占位语 / 拖延判断套话：未命中；仍须完成投资逻辑复核。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
