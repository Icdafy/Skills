#!/usr/bin/env python3
"""Initialize and validate a report against the user-selected heading template.

Standard library only. Paths are resolved from this script, independent of cwd.
The stage argument records the user's answer; agents must not infer that answer.
"""
import argparse
import json
import re
from pathlib import Path
from string import Formatter

ROOT = Path(__file__).resolve().parents[1]
STAGES = {"early": "early", "早前期": "early", "早期": "early",
          "mid-late": "mid-late", "中后期": "mid-late"}
TOKEN = re.compile(r"【填：[^】]+】|\{[a-zA-Z_][a-zA-Z_0-9]*\}")


def load_template(stage, root=ROOT):
    if stage not in STAGES:
        raise ValueError("请先询问用户选择早前期或中后期，不可自动判断阶段。")
    path = root / "assets" / "templates" / (STAGES[stage] + ".json")
    return json.loads(path.read_text(encoding="utf-8"))


def fields(text):
    return {field for _, field, _, _ in Formatter().parse(text) if field}


def binding_example(template):
    values = {}
    for node in template["nodes"]:
        if "repeat" in node:
            keys = set().union(*(fields(item["text"]) for item in node["items"])) - {"n"}
            values[node["repeat"]] = [{key: "【填：" + key + "】" for key in sorted(keys)}]
        else:
            values.update({key: "【填：" + key + "】" for key in sorted(fields(node["text"]))})
    return values


def format_text(text, values):
    required = fields(text)
    if required - values.keys():
        raise ValueError("标题填空缺少：" + ", ".join(sorted(required - values.keys())))
    for key in required:
        value = values[key]
        if not isinstance(value, (str, int)) or isinstance(value, bool) or not str(value).strip():
            raise ValueError("标题填空必须是非空文字：" + key)
        if any(c in str(value) for c in ("\n", "\r", "\t")):
            raise ValueError("标题填空不可插入换行或新标题：" + key)
    return text.format_map(values)


def heading_blocks(template, bindings):
    expected_keys = binding_example(template).keys()
    if set(bindings) != set(expected_keys):
        raise ValueError("填空字段与模板不符；缺少或多出：" + str(set(bindings) ^ set(expected_keys)))
    result = []
    for node in template["nodes"]:
        if "repeat" not in node:
            result.append({"type": "h" + str(node["level"]),
                           "text": format_text(node["text"], bindings)})
            continue
        rows = bindings[node["repeat"]]
        if not isinstance(rows, list):
            raise ValueError("重复项必须为列表：" + node["repeat"])
        if len(rows) < node.get("min_items", 0):
            raise ValueError("重复项数量不足：" + node["repeat"])
        for n, row in enumerate(rows, 1):
            if not isinstance(row, dict) or "n" in row:
                raise ValueError("每个重复项必须为字段对象，编号由模板生成。")
            required = set().union(*(fields(item["text"]) for item in node["items"])) - {"n"}
            if set(row) != required:
                raise ValueError("重复项字段与模板不符：" + node["repeat"])
            for item in node["items"]:
                result.append({"type": "h" + str(item["level"]),
                               "text": format_text(item["text"], dict(row, n=n))})
    return result


def initialize(stage, bindings=None, root=ROOT):
    template = load_template(stage, root)
    if bindings is None:
        bindings = binding_example(template)
    heads = heading_blocks(template, bindings)
    blocks = []
    for i, heading in enumerate(heads):
        blocks.append(heading)
        # Containers can be covered by their child sections. Every leaf needs facts.
        if i + 1 == len(heads) or heads[i + 1]["type"] <= heading["type"]:
            blocks.append({"type": "p", "text": "【填：本节有依据的正文；缺口留正文外清单】"})
    return {"report_template": {"stage": template["stage"], "skill": template["skill"],
                                 "version": template["version"], "bindings": bindings},
            "_authoring_notes": "阶段须由用户选择。仅填入资料支持的标题变量与正文；不得改写固定标题。",
            "toc": False, "blocks": blocks}


def has_content(block):
    if block.get("type") == "table":
        return any(str(cell).strip() for row in block.get("rows", []) for cell in row)
    if block.get("type") == "bullet":
        return any(str(item).strip() for item in block.get("items", []))
    return block.get("type") == "p" and bool((str(block.get("lead", "")) + str(block.get("text", ""))).strip())


def validate(content, root=ROOT):
    meta = content.get("report_template")
    if not isinstance(meta, dict):
        raise ValueError("缺少 report_template；先取得用户阶段选择，再执行 init。")
    template = load_template(meta.get("stage"), root)
    if meta.get("skill") != template["skill"] or meta.get("version") != template["version"]:
        raise ValueError("技能或模板版本不匹配。")
    expected = heading_blocks(template, meta.get("bindings", {}))
    blocks = content.get("blocks", [])
    actual = [{"type": b.get("type"), "text": b.get("text")} for b in blocks
              if re.fullmatch(r"h\d+", str(b.get("type", "")))]
    if actual != expected:
        raise ValueError("标题、层级或顺序偏离选定模板；请按 init 输出恢复。")
    rendered = [b for b in blocks if not str(b.get("type", "")).startswith("_")]
    if TOKEN.search(json.dumps(rendered, ensure_ascii=False)):
        raise ValueError("正文或标题仍有未填占位项，不可交付。")
    for i, block in enumerate(blocks):
        if block.get("type") not in {"h1", "h2", "h3", "h4"}:
            continue
        stop = next((j for j in range(i + 1, len(blocks))
                     if blocks[j].get("type") in {"h1", "h2", "h3", "h4"}), len(blocks))
        has_children = stop < len(blocks) and blocks[stop]["type"] > block["type"]
        if not has_children and not any(has_content(b) for b in blocks[i + 1:stop]):
            raise ValueError("末级标题没有正文或数据：" + block["text"])
    return len(expected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="用户选择阶段后生成待填骨架")
    init.add_argument("--stage", required=True, choices=tuple(STAGES))
    init.add_argument("--bindings", type=Path, help="资料支持的标题变量 JSON")
    init.add_argument("--output", type=Path, required=True)
    check = commands.add_parser("check", help="交付前严格核对固定标题及填空状态")
    check.add_argument("content", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "init":
            bindings = json.loads(args.bindings.read_text("utf-8")) if args.bindings else None
            data = initialize(args.stage, bindings)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print("已生成待填骨架（不可直接交付）：", args.output)
        else:
            count = validate(json.loads(args.content.read_text("utf-8")))
            print(f"[OK] {count} 个标题与所选模板一致，未留空标题或占位项。")
        return 0
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print("[FAIL]", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
