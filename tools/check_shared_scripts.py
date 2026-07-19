#!/usr/bin/env python3
"""校验（并同步）跨技能共享脚本的多份副本，防止静默漂移。

技能是自包含、可独立分发的：单独拷走 `hangye-fenxi/` 也必须能跑。因此共享渲染
器不能跨技能 import，每个技能必须自带一份物理副本——重复是分发模型的必然结果，
不是可以消掉的设计缺陷。真正的风险是**静默漂移**：改了一份忘了另外两份，三个
技能的排版从此不一致，且没有任何机制会报警（此前仅靠文件头一句“必须同步另外
两份”的人工纪律）。

本工具把这件事从“靠纪律”变成“靠机械校验”：

    python tools/check_shared_scripts.py           # 报告漂移，有漂移则退出码 1
    python tools/check_shared_scripts.py --sync    # 以 canonical 为准同步其余副本

注意：`meeting-minutes-pro/scripts/embed_fonts.py` **不在** embed_fonts 组内——
它由该技能的 `format_spec.py`（排版规约唯一真源）驱动，与五个公文技能的独立版本
本就不同，属预期差异。
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

SHARED_GROUPS: tuple[dict, ...] = (
    {
        "file": "scripts/build_docx.py",
        "canonical": "gongsi-qingkuang",
        "skills": ("gongsi-qingkuang", "hangye-fenxi", "zhuying-yewu-fenxi"),
        "note": "立项报告三技能统一公文渲染器",
    },
    {
        "file": "scripts/embed_fonts.py",
        "canonical": "gongsi-qingkuang",
        "skills": ("gongsi-qingkuang", "hangye-fenxi", "zhuying-yewu-fenxi",
                   "officialese-skill", "yiti-skill"),
        "note": "公文 DOCX 字体嵌入器（meeting-minutes-pro 版本由 format_spec 驱动，不在此组）",
    },
)


def digest(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_group(group: dict, sync: bool) -> tuple[bool, list[str]]:
    """返回 (是否一致, 消息列表)。sync=True 时以 canonical 覆盖其余副本。"""
    relative = group["file"]
    canonical_path = REPO_ROOT / group["canonical"] / relative
    messages: list[str] = []
    canonical_hash = digest(canonical_path)
    if canonical_hash is None:
        return False, [f"  基准副本缺失：{group['canonical']}/{relative}"]

    consistent = True
    for skill in group["skills"]:
        if skill == group["canonical"]:
            continue
        target = REPO_ROOT / skill / relative
        target_hash = digest(target)
        if target_hash == canonical_hash:
            continue
        consistent = False
        state = "缺失" if target_hash is None else "与基准不一致"
        if sync:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(canonical_path, target)
            messages.append(f"  已同步（原{state}）：{skill}/{relative}")
        else:
            messages.append(f"  {state}：{skill}/{relative}")
    return consistent, messages


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sync", action="store_true",
                        help="以 canonical 副本为准覆盖其余副本")
    args = parser.parse_args()

    all_consistent = True
    for group in SHARED_GROUPS:
        consistent, messages = check_group(group, args.sync)
        label = f"{group['file']}（{group['note']}）"
        if consistent:
            print(f"[一致] {label}：{len(group['skills'])} 份副本")
        else:
            all_consistent = False
            print(f"[{'已同步' if args.sync else '漂移'}] {label}")
            for message in messages:
                print(message)

    if args.sync:
        print("\n同步完成；请复核改动并一并提交全部副本。")
        return 0
    if all_consistent:
        print("\n全部共享脚本副本一致。")
        return 0
    print("\n存在漂移：确认哪份为准后，改基准副本再运行 --sync，"
          "或手工对齐后重跑本检查。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
