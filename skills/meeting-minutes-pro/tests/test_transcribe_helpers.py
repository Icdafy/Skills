#!/usr/bin/env python3
"""Tests for pure helpers in transcribe.py (chunk planning, ETA reporting)."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import tempfile
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "transcribe.py"
SPEC = importlib.util.spec_from_file_location("transcribe", SCRIPT)
TRANSCRIBE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = TRANSCRIBE
SPEC.loader.exec_module(TRANSCRIBE)


class PlanChunksTests(unittest.TestCase):
    def test_short_audio_single_chunk(self) -> None:
        chunks = TRANSCRIBE.plan_chunks(500.0, [], 600.0, 240.0, 900.0)
        self.assertEqual(chunks, [(0.0, 500.0)])

    def test_funasr_bounds_without_silence(self) -> None:
        chunks = TRANSCRIBE.plan_chunks(2000.0, [], 600.0, 240.0, 900.0)
        self.assertEqual(chunks[0], (0.0, 900.0))
        self.assertEqual(chunks[-1][1], 2000.0)
        for start, end in chunks:
            self.assertLessEqual(end - start, 900.0)

    def test_cut_prefers_silence_near_target(self) -> None:
        silences = [(590.0, 594.0)]
        chunks = TRANSCRIBE.plan_chunks(2000.0, silences, 600.0, 240.0, 900.0)
        self.assertAlmostEqual(chunks[0][1], 592.0)

    def test_qwen_bounds_still_work(self) -> None:
        chunks = TRANSCRIBE.plan_chunks(700.0, [], 120.0, 30.0, 180.0)
        for start, end in chunks[:-1]:
            self.assertLessEqual(end - start, 180.0)
        self.assertEqual(chunks[-1][1], 700.0)


class EtaTests(unittest.TestCase):
    def test_eta_emitted_from_sample_probe(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            output_dir = Path(raw)
            source = output_dir / "会议录音.m4a"
            source.write_bytes(b"")
            stem = TRANSCRIBE.safe_stem(source)
            (output_dir / f"{stem}.sample.json").write_text(
                json.dumps({"realtime_factor": 0.25}), encoding="utf-8"
            )
            buffer = io.StringIO()
            with contextlib.redirect_stderr(buffer):
                TRANSCRIBE.emit_eta(output_dir, source, 7200.0)
            payload = json.loads(buffer.getvalue())
            self.assertEqual(payload["progress"]["stage"], "eta")
            self.assertAlmostEqual(payload["progress"]["estimated_minutes"], 30.0)

    def test_eta_silent_without_sample(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            output_dir = Path(raw)
            source = output_dir / "会议录音.m4a"
            buffer = io.StringIO()
            with contextlib.redirect_stderr(buffer):
                TRANSCRIBE.emit_eta(output_dir, source, 7200.0)
            self.assertEqual(buffer.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
