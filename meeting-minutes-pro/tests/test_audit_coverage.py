#!/usr/bin/env python3
"""Tests for the transcript coverage auditor."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import tempfile
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "audit_coverage.py"
SPEC = importlib.util.spec_from_file_location("audit_coverage", SCRIPT)
AUDIT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = AUDIT
SPEC.loader.exec_module(AUDIT)

INDENT = "　　"


def stamp(text: str, start: float, end: float) -> dict:
    return {"text": text, "start": start, "end": end, "speaker": None}


def transcript_payload() -> dict:
    # Three 300-second windows: numbers in windows 1 and 3, filler in window 2.
    return {"text": "", "timestamps": [
        stamp("公司去年营收3000万元。", 10.0, 15.0),
        stamp("毛利率大概30%。", 200.0, 205.0),
        stamp("嗯嗯好的好的。", 400.0, 405.0),
        stamp("我们计划3月15日交付。", 700.0, 705.0),
        stamp("产能爬坡到每月500台。", 880.0, 900.0),
    ]}


class AuditCoverageTests(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.root = Path(self._dir.name)
        self.transcript = self.root / "recording.json"
        self.transcript.write_text(
            json.dumps(transcript_payload(), ensure_ascii=False), encoding="utf-8"
        )
        self.addCleanup(self._dir.cleanup)

    def windows(self) -> list:
        windows, mode = AUDIT.build_windows(self.transcript, 300.0, 1500)
        self.assertEqual(mode, "time")
        return windows

    def write_minutes(self, *body: str) -> Path:
        path = self.root / "minutes.txt"
        path.write_text("访谈纪要\n" + "\n".join(INDENT + line for line in body),
                        encoding="utf-8")
        return path

    def write_ledger(self, *lines: str) -> Path:
        path = self.root / "coverage.txt"
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def validate(self, ledger: Path, minutes: Path) -> tuple[int, str]:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = AUDIT.validate(self.windows(), "time", ledger, minutes)
        return code, buffer.getvalue()

    def test_windows_and_template(self) -> None:
        windows = self.windows()
        self.assertEqual(len(windows), 3)
        self.assertIn("3000万", windows[0].numbers)
        self.assertEqual(windows[1].numbers, [])
        template = self.root / "coverage.txt"
        AUDIT.write_template(windows, template)
        content = template.read_text(encoding="utf-8")
        window_lines = [line for line in content.splitlines() if line.startswith("窗口")]
        self.assertEqual(sum("待判定" in line for line in window_lines), 3)
        self.assertIn("窗口 3（10:00–15:00）", content)

    def test_full_pass(self) -> None:
        minutes = self.write_minutes(
            "一、完整总结概述",
            "公司去年营收3000万元，毛利率约30%，计划3月15日交付，产能爬坡到每月500台。",
        )
        ledger = self.write_ledger(
            "窗口 1（00:00–05:00）：纳入 总结一",
            "窗口 2（05:00–10:00）：省略 寒暄与确认性口语",
            "窗口 3（10:00–15:00）：纳入 总结一",
        )
        code, output = self.validate(ledger, minutes)
        self.assertEqual(code, 0, output)
        self.assertIn("覆盖率审计通过", output)

    def test_undecided_window_fails(self) -> None:
        minutes = self.write_minutes("一、完整总结概述", "内容概述。")
        ledger = self.write_ledger(
            "窗口 1（00:00–05:00）：纳入 总结一",
            "窗口 2（05:00–10:00）：待判定",
            "窗口 3（10:00–15:00）：纳入 总结一",
        )
        code, output = self.validate(ledger, minutes)
        self.assertEqual(code, 1)
        self.assertIn("待判定", output)

    def test_missing_window_fails(self) -> None:
        minutes = self.write_minutes("一、完整总结概述", "内容概述。")
        ledger = self.write_ledger("窗口 1（00:00–05:00）：纳入 总结一")
        code, output = self.validate(ledger, minutes)
        self.assertEqual(code, 1)
        self.assertIn("缺少判定", output)

    def test_omitting_number_dense_window_fails(self) -> None:
        minutes = self.write_minutes("一、完整总结概述", "内容概述。")
        ledger = self.write_ledger(
            "窗口 1（00:00–05:00）：省略 内容不重要",
            "窗口 2（05:00–10:00）：省略 寒暄",
            "窗口 3（10:00–15:00）：纳入 总结一",
        )
        code, output = self.validate(ledger, minutes)
        self.assertEqual(code, 1)
        self.assertIn("却被判定省略", output)

    def test_tampered_time_range_fails(self) -> None:
        minutes = self.write_minutes("一、完整总结概述", "内容概述。")
        ledger = self.write_ledger(
            "窗口 1（00:00–03:00）：纳入 总结一",
            "窗口 2（05:00–10:00）：省略 寒暄",
            "窗口 3（10:00–15:00）：纳入 总结一",
        )
        code, output = self.validate(ledger, minutes)
        self.assertEqual(code, 1)
        self.assertIn("时间范围与转录稿不符", output)

    def test_included_window_without_evidence_warns(self) -> None:
        minutes = self.write_minutes("一、完整总结概述", "会议介绍了公司经营情况。")
        ledger = self.write_ledger(
            "窗口 1（00:00–05:00）：纳入 总结一",
            "窗口 2（05:00–10:00）：省略 寒暄",
            "窗口 3（10:00–15:00）：纳入 总结一",
        )
        code, output = self.validate(ledger, minutes)
        self.assertEqual(code, 0)
        self.assertIn("警告", output)
        self.assertIn("均未出现在纪要中", output)

    def test_text_fallback_windows(self) -> None:
        plain = self.root / "plain.txt"
        plain.write_text("第一段内容。" * 100 + "\n" + "第二段内容。" * 100, encoding="utf-8")
        windows, mode = AUDIT.build_windows(plain, 300.0, 300)
        self.assertEqual(mode, "text")
        self.assertGreaterEqual(len(windows), 2)


if __name__ == "__main__":
    unittest.main()
