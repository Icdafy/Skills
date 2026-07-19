#!/usr/bin/env python3
"""One-command pre-delivery gate for the minutes.

Runs the four checks in order (quality_check -> audit_coverage ->
qa_reconcile -> fact_check), optionally verifies that the generated DOCX
carries exactly the validated text (paragraph-by-paragraph, whitespace
ignored, one subtitle line exempted), audits the deliverable folder, and
writes an auditable checks-summary.json next to the minutes: every check's
result plus every waiver used (--allow-line / --skip / --allow), so the
release trail lives in the archive instead of only in the conversation.

    check_all.py 会议纪要.txt --transcript <输出目录>/<文件名>.json \
        --ledger coverage.txt [--glossary 术语.txt] [--mode qa-summary]
    # after the DOCX exists, rerun with --docx 会议纪要.docx

Each sub-check keeps its own exit semantics; this orchestrator fails when
any of them fails. Pass --fail-fast to stop at the first failure. The DOCX
text check needs python-docx (present in the skill runtime); when missing
it is reported as unavailable rather than silently skipped.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys

SCRIPTS_DIR = Path(__file__).resolve().parent


def normalized_lines(text: str) -> list[str]:
    """Non-empty lines with all whitespace (incl. ideographic space) removed."""
    lines: list[str] = []
    for line in text.splitlines():
        cleaned = re.sub(r"[\s　]+", "", line)
        if cleaned:
            lines.append(cleaned)
    return lines


def _first_diff(docx_lines: list[str], expected: list[str]) -> dict:
    for position, (docx_line, txt_line) in enumerate(
            zip(docx_lines, expected), start=1):
        if docx_line != txt_line:
            return {
                "matches": False,
                "note": f"第 {position} 段起不一致：DOCX「{docx_line[:30]}」"
                        f"≠ 文本「{txt_line[:30]}」",
            }
    return {
        "matches": False,
        "note": f"段落数不一致：DOCX {len(docx_lines)} 段，预期 {len(expected)} 段",
    }


def compare_line_lists(docx_lines: list[str], txt_lines: list[str],
                       subtitle: str | None = None) -> dict:
    """Paragraph-level equality between the DOCX and the minutes text.

    The optional centred subtitle is not part of the text file. When the caller
    passes ``--subtitle`` its exact placement (right after the title) is
    verified; otherwise a single extra DOCX line after the title is exempted as
    a best-effort fallback."""
    if subtitle:
        subtitle_norm = re.sub(r"[\s　]+", "", subtitle)
        expected = txt_lines[:1] + [subtitle_norm] + txt_lines[1:]
        if docx_lines == expected:
            return {"matches": True, "note": "DOCX 含副标题行（已按 --subtitle 核对）"}
        return _first_diff(docx_lines, expected)
    if docx_lines == txt_lines:
        return {"matches": True, "note": ""}
    if (len(docx_lines) == len(txt_lines) + 1
            and docx_lines[:1] == txt_lines[:1]
            and docx_lines[2:] == txt_lines[1:]):
        return {"matches": True, "note": "DOCX 含副标题行（未传 --subtitle，已按单行豁免）"}
    return _first_diff(docx_lines, txt_lines)


def docx_text_lines(path: Path) -> list[str] | None:
    """Body paragraphs of the DOCX, normalized; None when python-docx is
    unavailable (run with the runtime python in that case)."""
    try:
        from docx import Document
    except ImportError:
        return None
    document = Document(str(path))
    return normalized_lines("\n".join(p.text for p in document.paragraphs))


def check_docx_style_report(path: Path) -> dict:
    """Run the style readback (fonts/sizes/weights vs the spec) on the DOCX.
    Returns {ok, problems} or an unavailable note when python-docx is missing."""
    try:
        sys.path.insert(0, str(SCRIPTS_DIR))
        from docx_style_check import check_docx_style
    except ImportError:
        return {"ok": None, "note": "python-docx 不可用；请用运行时 Python 执行本脚本"}
    problems = check_docx_style(path)
    return {"ok": not problems, "problems": problems[:20]}


def resolve_transcript(transcript: Path) -> tuple[Path, Path]:
    """Return (structured, plain_text): the .json is preferred for the
    structure-aware checks, the sibling .txt feeds fact_check."""
    if transcript.suffix.lower() == ".json":
        plain = transcript.with_suffix(".txt")
        return transcript, plain
    return transcript, transcript


def run_check(name: str, argv: list[str]) -> dict:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    proc = subprocess.run(
        [sys.executable, *argv], capture_output=True,
        text=True, encoding="utf-8", errors="replace", env=env,
    )
    return {
        "name": name,
        "command": " ".join(str(part) for part in argv),
        "exit_code": proc.returncode,
        "passed": proc.returncode == 0,
        "skipped": False,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def skipped_check(name: str, reason: str) -> dict:
    return {"name": name, "command": "", "exit_code": None, "passed": True,
            "skipped": True, "reason": reason, "stdout": "", "stderr": ""}


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("minutes", type=Path, help="minutes text file")
    parser.add_argument("--transcript", required=True, type=Path,
                        help="transcript .json (preferred) or .txt")
    parser.add_argument("--ledger", type=Path,
                        help="filled-in coverage ledger for audit_coverage")
    parser.add_argument("--glossary", action="append", type=Path, default=[])
    parser.add_argument("--term", action="append", default=[])
    parser.add_argument("--mode", choices=("auto", "minutes", "qa", "qa-summary"),
                        default="auto")
    parser.add_argument("--allow-line", action="append", type=int, default=[],
                        metavar="行号", help="forwarded to quality_check")
    parser.add_argument("--skip", action="append", type=int, default=[],
                        metavar="编号", help="forwarded to qa_reconcile")
    parser.add_argument("--allow", action="append", default=[],
                        help="forwarded to fact_check")
    parser.add_argument("--docx", type=Path, default=None,
                        help="generated DOCX to verify against the minutes text")
    parser.add_argument("--subtitle", default=None,
                        help="生成 DOCX 时用过的副标题；传入后精确核对其位置，"
                             "不再走单行豁免")
    parser.add_argument("--summary", type=Path, default=None,
                        help="summary JSON path (default: checks-summary.json "
                             "next to the minutes)")
    parser.add_argument("--fail-fast", action="store_true",
                        help="stop at the first failing check")
    args = parser.parse_args()

    if not args.minutes.is_file():
        parser.error(f"找不到纪要文件：{args.minutes}")
    if not args.transcript.is_file():
        parser.error(f"找不到转录稿：{args.transcript}")
    for path in args.glossary:
        if not path.is_file():
            parser.error(f"找不到术语文件：{path}")
    structured, transcript_txt = resolve_transcript(args.transcript)
    if not transcript_txt.is_file():
        parser.error(f"缺少 fact_check 所需的转录稿文本：{transcript_txt}")

    glossary_args: list[str] = []
    for path in args.glossary:
        glossary_args += ["--glossary", str(path)]
    for term in args.term:
        glossary_args += ["--term", term]

    plan: list[tuple[str, list[str] | None, str]] = [
        (
            "quality_check",
            [str(SCRIPTS_DIR / "quality_check.py"), str(args.minutes),
             "--mode", args.mode]
            + [part for number in args.allow_line
               for part in ("--allow-line", str(number))],
            "",
        ),
        (
            "audit_coverage",
            [str(SCRIPTS_DIR / "audit_coverage.py"),
             "--transcript", str(structured),
             "--ledger", str(args.ledger),
             "--minutes", str(args.minutes)] if args.ledger else None,
            "未提供 --ledger（覆盖率清单）",
        ),
        (
            "qa_reconcile",
            [str(SCRIPTS_DIR / "qa_reconcile.py"), str(args.minutes),
             "--transcript", str(structured), "--show-matches"]
            + [part for number in args.skip
               for part in ("--skip", str(number))],
            "",
        ),
        (
            "fact_check",
            [str(SCRIPTS_DIR / "fact_check.py"), str(args.minutes),
             "--transcript", str(transcript_txt), "--show-matches"]
            + glossary_args
            + [part for value in args.allow for part in ("--allow", value)],
            "",
        ),
    ]

    checks: list[dict] = []
    failed = False
    for name, argv, skip_reason in plan:
        if argv is None:
            checks.append(skipped_check(name, skip_reason))
            continue
        if failed and args.fail_fast:
            checks.append(skipped_check(name, "fail-fast：前序校验未通过"))
            continue
        result = run_check(name, argv)
        checks.append(result)
        if not result["passed"]:
            failed = True

    # Deliverable folder audit + DOCX text fidelity.
    deliverable: dict = {
        "transcript_structured": str(structured),
        "transcript_txt_present": transcript_txt.is_file(),
        "ledger_present": bool(args.ledger and args.ledger.is_file()),
        "refine_report_present":
            (structured.parent / f"{structured.stem}.refine.md").is_file(),
    }
    if args.docx is not None:
        docx_entry: dict = {"path": str(args.docx), "present": args.docx.is_file()}
        if not args.docx.is_file():
            docx_entry["note"] = "DOCX 不存在"
            failed = True
        else:
            docx_entry["newer_than_minutes"] = (
                args.docx.stat().st_mtime >= args.minutes.stat().st_mtime
            )
            if not docx_entry["newer_than_minutes"]:
                docx_entry["note"] = "DOCX 比纪要文本旧，需重新生成"
                failed = True
            docx_lines = docx_text_lines(args.docx)
            if docx_lines is None:
                docx_entry["text_check"] = {
                    "matches": None,
                    "note": "python-docx 不可用；请用运行时 Python 执行本脚本",
                }
                failed = True
            else:
                txt_lines = normalized_lines(
                    args.minutes.read_text(encoding="utf-8-sig")
                )
                docx_entry["text_check"] = compare_line_lists(
                    docx_lines, txt_lines, args.subtitle)
                if not docx_entry["text_check"]["matches"]:
                    failed = True
                style = check_docx_style_report(args.docx)
                docx_entry["style_check"] = style
                if style.get("ok") is False:
                    failed = True
        deliverable["docx"] = docx_entry

    summary_path = args.summary or (args.minutes.parent / "checks-summary.json")
    summary = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "minutes": str(args.minutes),
        "transcript": str(args.transcript),
        "mode": args.mode,
        "all_passed": not failed,
        "checks": checks,
        "waivers": {
            "allow_line": sorted(args.allow_line),
            "skip": sorted(args.skip),
            "allow": list(args.allow),
            "note": "放行理由须在对话中向用户说明；此处仅存审计痕迹。",
        },
        "deliverable": deliverable,
    }
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    for check in checks:
        if check["skipped"]:
            state = f"跳过（{check.get('reason', '')}）"
        else:
            state = "通过" if check["passed"] else "未通过"
        print(f"[{state}] {check['name']}")
    if args.docx is not None:
        docx_state = deliverable["docx"]
        text_check = docx_state.get("text_check") or {}
        docx_ok = (docx_state.get("present") and docx_state.get("newer_than_minutes")
                   and text_check.get("matches"))
        print(f"[{'通过' if docx_ok else '未通过'}] docx_text"
              + (f"（{text_check.get('note') or docx_state.get('note', '')}）"
                 if not docx_ok else ""))
        style_check = docx_state.get("style_check")
        if style_check:
            style_ok = style_check.get("ok")
            state = "通过" if style_ok else ("跳过" if style_ok is None else "未通过")
            detail = ""
            if style_ok is False:
                detail = f"（{'；'.join(style_check.get('problems', [])[:3])}）"
            elif style_ok is None:
                detail = f"（{style_check.get('note', '')}）"
            print(f"[{state}] docx_style{detail}")
    print(f"校验汇总已写入：{summary_path}")
    print(f"总体：{'全部通过' if not failed else '存在未通过项，逐项处理后重跑'}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
