#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
style_check.py —— 公司情况章节语言与口吻扫描。

对成稿（含拖延判断套话检查；Markdown / 纯文本 / build_docx 用的 content.json）扫描语言红线、
外部指导口吻、材料版本和机械来源。仅扫描报告正文，不扫描来源台账或本方核查清单。
机械命中是复核入口；法律义务、真实产品型号等按上下文判断，不盲目替换。
来源重复给出警告，需人工检查作用域；不因减少重复而取消必要的证据归属。

扫描项：
1. 称谓违规——"标的公司/标的企业/该标的/本标的/目标公司/拟投资标的/标的方"
2. 成对转折/递进连词——"不是……而是""并非……而是""不仅……而且"等对举句式
3. 结论标签——"核心结论：""核心观点："（结论直接写加粗判断句，不加标签）
4. 缺口占位语——"资料未披露""【待核查""【待补充""尚未提供"等：按三技能统一
   缺口规则，报告正文不得出现占位语，全部缺口在对话交付的"资料缺口与待核查
   清单"中提示（本脚本扫描的是报告正文，清单本身不在扫描范围）

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

RULES = [
    ("拖延判断套话（完成当前分析，补证动作留正文外清单）",
     re.compile(r"(?:有待|尚待|仍待)(?:进一步)?(?:判断|验证|核实|核查|观察|分析)|"
                r"(?:需要|仍需|尚需|需)(?:后续|进一步|持续|在尽调阶段)[^。；;\n]{0,60}(?:判断|验证|核实|核查|观察|分析|关注|佐证)|"
                r"(?:后续|下一步|尽调阶段)[^。；;\n]{0,40}(?:判断|验证|核实|核查|观察|分析|关注)|"
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


def _texts_from_json(data):
    """从 build_docx 的 content 结构提取全部待扫描文本。"""
    out = []
    for blk in data.get("blocks", []):
        t = blk.get("type")
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

    if path.lower().endswith(".json"):
        pairs = _texts_from_json(json.loads(raw))
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

    for loc, warning in attribution_warnings(pairs):
        print(f"[WARN] {warning} @ {loc}")

    if hits:
        print(f"\n共 {hits} 处命中，逐条改写后重扫。")
        return 1
    print("[OK] 语言及口吻硬规则未命中；仍需人工检查表文关系、分析质量和证据边界。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
