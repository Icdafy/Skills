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
        for token in ("- 1 -", "-", "1", "12", " 2019", "- 3 -"):
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


class FooterXsTests(unittest.TestCase):
    """Locating the footer from the page's own content, not a fixed margin."""

    def test_real_page_coordinates(self) -> None:
        # Captured from an actual Word-rendered A4 page: footer at y≈40.6,
        # body from y≈124.5. The "5" at y=124.5 is a digit inside a body line
        # and must not be taken for the page number.
        candidates = [(40.6, 499.5), (40.6, 507.6), (40.6, 513.7), (124.5, 423.3)]
        body_ys = [124.5, 152.5]
        self.assertEqual(RD.footer_xs(candidates, body_ys, 842.0),
                         [499.5, 507.6, 513.7])

    def test_numeric_row_low_on_page_is_excluded(self) -> None:
        # A numeric table row below the last CJK line must not contaminate the
        # footer: only the lowest text line counts.
        candidates = [(40.0, 80.0), (95.0, 300.0), (95.0, 360.0)]
        self.assertEqual(RD.footer_xs(candidates, [200.0], 842.0), [80.0])

    def test_survives_a_larger_footer_distance(self) -> None:
        # Footer pushed well up the page (y=150) still found, because the
        # cutoff comes from the body text rather than a hard-coded band.
        self.assertEqual(RD.footer_xs([(150.0, 90.0)], [300.0], 842.0), [90.0])

    def test_falls_back_without_body_text(self) -> None:
        self.assertEqual(RD.footer_xs([(40.0, 90.0)], [], 842.0), [90.0])
        self.assertEqual(RD.footer_xs([(400.0, 90.0)], [], 842.0), [])

    def test_no_candidates(self) -> None:
        self.assertEqual(RD.footer_xs([], [200.0], 842.0), [])


class ExpectedSideTests(unittest.TestCase):
    def test_odd_right_even_left(self) -> None:
        self.assertEqual(RD.expected_side(1), "right")
        self.assertEqual(RD.expected_side(2), "left")
        self.assertEqual(RD.expected_side(3), "right")


if __name__ == "__main__":
    unittest.main()
