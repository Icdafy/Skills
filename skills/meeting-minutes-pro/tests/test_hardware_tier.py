#!/usr/bin/env python3
"""Tests for the T0–T3 hardware tier classification in bootstrap_runtime."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "bootstrap_runtime.py"
SPEC = importlib.util.spec_from_file_location("bootstrap_runtime", SCRIPT)
BOOTSTRAP = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = BOOTSTRAP
SPEC.loader.exec_module(BOOTSTRAP)


class ClassifyTierTests(unittest.TestCase):
    def test_big_gpu_is_t3(self) -> None:
        self.assertEqual(BOOTSTRAP.classify_tier(16.0, 24.0)[0], "T3")

    def test_mid_gpu_is_t2(self) -> None:
        self.assertEqual(BOOTSTRAP.classify_tier(16.0, 8.0)[0], "T2")

    def test_small_gpu_falls_back_to_ram_tiers(self) -> None:
        self.assertEqual(BOOTSTRAP.classify_tier(16.0, 6.0)[0], "T1")
        self.assertEqual(BOOTSTRAP.classify_tier(8.0, 6.0)[0], "T0")

    def test_cpu_only_by_ram(self) -> None:
        self.assertEqual(BOOTSTRAP.classify_tier(32.0, None)[0], "T1")
        self.assertEqual(BOOTSTRAP.classify_tier(8.0, None)[0], "T0")

    def test_unknown_ram_defaults_to_t1(self) -> None:
        tier, reason = BOOTSTRAP.classify_tier(None, None)
        self.assertEqual(tier, "T1")
        self.assertIn("无法探测", reason)

    def test_every_tier_has_advice(self) -> None:
        for ram, vram in ((8.0, None), (16.0, None), (16.0, 8.0), (16.0, 24.0)):
            tier, _ = BOOTSTRAP.classify_tier(ram, vram)
            self.assertIn(tier, BOOTSTRAP.TIER_ADVICE)


class AttachTierTests(unittest.TestCase):
    def test_attach_tier_adds_fields(self) -> None:
        result: dict = {"engines": {"funasr": True, "qwen": True}}
        BOOTSTRAP.attach_tier(result)
        self.assertIn(result["tier"], ("T0", "T1", "T2", "T3"))
        self.assertTrue(result["tier_advice"])
        self.assertIn("ram_gb", result["hardware"])
        self.assertIn("cuda", result["hardware"])

    def test_missing_qwen_engine_noted_above_t0(self) -> None:
        result: dict = {"engines": {"funasr": True, "qwen": False}}
        BOOTSTRAP.attach_tier(result)
        if result["tier"] != "T0":
            self.assertIn("qwen", result["tier_advice"])


class HardwareReportTests(unittest.TestCase):
    def test_report_shape(self) -> None:
        report = BOOTSTRAP.hardware_report()
        for key in ("ram_gb", "cpu_cores", "cuda", "gpu_name", "vram_gb", "disk_free_gb"):
            self.assertIn(key, report)
        self.assertIsInstance(report["cuda"], bool)


if __name__ == "__main__":
    unittest.main()
