#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
style_check.py —— 立项报告章节语言红线机械扫描（三技能统一版）。

对成稿（Markdown / 纯文本 / build_docx 用的 content.json）逐行扫描四类硬伤，
输出命中位置，供交付前自检。只做机械匹配；结论前置、口径归因等仍需人工核对。

扫描项：
1. 称谓违规——"标的公司/标的企业/该标的/本标的/目标公司/拟投资标的/标的方"
2. 成对转折/递进连词——"不是……而是""并非……而是""不仅……而且"等对举句式
3. 结论标签——"核心结论：""核心观点：""综上所述"开头式标签
4. 缺口占位语——"资料未披露""【待核查""【待补充""尚未提供"等：按三技能统一
   缺口规则，报告正文不得出现占位语，全部缺口在对话交付的"资料缺口与待核查
   清单"中提示（本脚本扫描的是报告正文，清单本身不在扫描范围）

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

RULES = [
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
]


def _texts_from_json(data):
    """从 build_docx 的 content 结构提取全部待扫描文本。"""
    out = []
    for blk in data.get("blocks", []):
        t = blk.get("type")
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

    if hits:
        print(f"\n共 {hits} 处命中，逐条改写后重扫。")
        return 1
    print("[OK] 称谓 / 对举连词 / 结论标签 / 缺口占位语：全部通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
