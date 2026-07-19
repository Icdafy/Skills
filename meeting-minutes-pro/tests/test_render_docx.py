#!/usr/bin/env python3
"""Tests for the page-number geometry helpers used by the render check."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "render_docx.py"
SPEC = importlib.util.spec_from_file_location("render_docx", SCRIPT)
RD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(RD)


class FooterTokenTests(unittest.TestCase):
    def test_dashes_and_digits_match(self) -> None:
        for token in ("-1-", "-", "1", "12", " 2019", "- 3 -"):
            self.assertTrue(RD.is_footer_token(token), token)

    def test_letters_and_cjk_do_not_match(self) -> None:
        for token in ("COO", "5G", "产品良率", "", "   "):
            self.assertFalse(RD.is_footer_token(token), token)


class PageSideTests(unittest.TestCase):
    def test_right_and_left(self) -> None:
        self.assertEqual(RD.page_side([499.5, 507.6, 513.7], 595.0), "right")
        self.assertEqual(RD.page_side([79.3, 87.4, 93.5], 595.0), "left")

    def test_empty_is_none(self) -> None:
        self.assertIsNone(RD.page_side([], 595.0))


class ExpectedSideTests(unittest.TestCase):
    def test_odd_right_even_left(self) -> None:
        self.assertEqual(RD.expected_side(1), "right")
        self.assertEqual(RD.expected_side(2), "left")
        self.assertEqual(RD.expected_side(3), "right")


if __name__ == "__main__":
    unittest.main()
