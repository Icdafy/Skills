#!/usr/bin/env python3
"""Tests for DOCX font embedding: the ECMA-376 obfuscation round-trip, the
OS/2 fsType gate, and an end-to-end embed+verify on a generated package
(skipped when python-docx is unavailable)."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "embed_fonts.py"
SPEC = importlib.util.spec_from_file_location("embed_fonts", SCRIPT)
EF = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = EF
SPEC.loader.exec_module(EF)

try:
    from docx import Document
    HAS_DOCX = True
except ImportError:  # pragma: no cover
    HAS_DOCX = False


class ObfuscationTests(unittest.TestCase):
    def test_round_trip(self) -> None:
        data = bytes((i * 7) % 256 for i in range(60))
        guid = "{AABBCCDD-1122-3344-5566-778899AABBCC}"
        obfuscated = EF.obfuscate(data, guid)
        self.assertEqual(EF.deobfuscate(obfuscated, guid), data)

    def test_only_first_32_bytes_change(self) -> None:
        data = bytes((i * 3 + 1) % 256 for i in range(64))
        guid = EF.new_font_key()
        obfuscated = EF.obfuscate(data, guid)
        self.assertEqual(obfuscated[32:], data[32:])
        self.assertNotEqual(obfuscated[:32], data[:32])

    def test_bad_guid_rejected(self) -> None:
        with self.assertRaises(ValueError):
            EF.obfuscate(b"0123456789ABCDEF0123456789ABCDEF", "not-a-guid")


class FsTypeGateTests(unittest.TestCase):
    def test_bundled_fangsong_is_embeddable(self) -> None:
        raw = (EF.FONT_DIR / "simfang.ttf").read_bytes()
        self.assertEqual(EF.read_fs_type(raw), 0)
        self.assertTrue(EF.is_embeddable(EF.read_fs_type(raw)))

    def test_title_face_is_restricted(self) -> None:
        raw = (EF.FONT_DIR / "方正小标宋简体.ttf").read_bytes()
        self.assertEqual(EF.read_fs_type(raw) & 0x0002, 0x0002)
        self.assertFalse(EF.is_embeddable(EF.read_fs_type(raw)))

    def test_none_and_signature(self) -> None:
        self.assertFalse(EF.is_embeddable(None))
        self.assertFalse(EF.is_sfnt(b"not a font"))
        self.assertTrue(EF.is_sfnt((EF.FONT_DIR / "simfang.ttf").read_bytes()))


class FontDescriptorTests(unittest.TestCase):
    """Word only uses an embedded face once w:charset tells it which script the
    face serves; without the descriptor it silently falls back to a system font."""

    def test_gb2312_charset_is_derived_from_os2(self) -> None:
        descriptor = EF.font_descriptor((EF.FONT_DIR / "simfang.ttf").read_bytes())
        self.assertIn('<w:charset w:val="86"/>', descriptor)  # GB2312
        self.assertIn("<w:panose1 ", descriptor)
        self.assertIn("<w:sig ", descriptor)

    def test_unreadable_font_yields_no_descriptor(self) -> None:
        self.assertEqual(EF.font_descriptor(b"not a font at all"), "")


class EmbeddedFontEntriesTests(unittest.TestCase):
    """The font table must be parsed per <w:font> block: a real one carries the
    descriptor between the opening tag and <w:embedRegular>, and Word also emits
    w:subsetted before w:fontKey."""

    def test_entry_with_descriptor_and_subsetted(self) -> None:
        xml = ('<w:fonts><w:font w:name="仿宋_GB2312">'
               '<w:panose1 w:val="02010609030101010101"/>'
               '<w:charset w:val="86"/><w:pitch w:val="variable"/>'
               '<w:embedRegular r:id="rId1" w:subsetted="1" '
               'w:fontKey="{AABBCCDD-1122-3344-5566-778899AABBCC}"/>'
               "</w:font></w:fonts>")
        self.assertEqual(
            EF.embedded_font_entries(xml),
            [("仿宋_GB2312", "rId1", "{AABBCCDD-1122-3344-5566-778899AABBCC}")],
        )

    def test_font_without_embedded_face_is_ignored(self) -> None:
        xml = ('<w:fonts><w:font w:name="Symbol">'
               '<w:charset w:val="02"/></w:font></w:fonts>')
        self.assertEqual(EF.embedded_font_entries(xml), [])

    def test_multiple_faces(self) -> None:
        xml = ("<w:fonts>"
               '<w:font w:name="A"><w:embedRegular r:id="r1" w:fontKey="{K1}"/></w:font>'
               '<w:font w:name="B"><w:charset w:val="86"/>'
               '<w:embedRegular r:id="r2" w:fontKey="{K2}"/></w:font>'
               "</w:fonts>")
        self.assertEqual(EF.embedded_font_entries(xml),
                         [("A", "r1", "{K1}"), ("B", "r2", "{K2}")])


@unittest.skipUnless(HAS_DOCX, "python-docx not installed")
class EmbedIntoDocxTests(unittest.TestCase):
    def _make_docx(self, path: Path) -> None:
        document = Document()
        document.add_paragraph("正文 test 5G")
        document.save(path)

    def test_embed_and_verify(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docx_path = Path(tmp) / "m.docx"
            self._make_docx(docx_path)
            report = EF.embed_fonts_into_docx(
                docx_path, {"仿宋_GB2312": EF.FONT_DIR / "simfang.ttf"})
            self.assertEqual([e["font"] for e in report["embedded"]], ["仿宋_GB2312"])
            verify = EF.verify_embedded_fonts(docx_path)
            self.assertTrue(verify["ok"])
            self.assertTrue(verify["embed_flag"])
            with zipfile.ZipFile(docx_path) as archive:
                names = archive.namelist()
                self.assertIn("word/fonts/font1.odttf", names)
                # The descriptor must reach the file, else Word ignores the face.
                font_table = archive.read("word/fontTable.xml").decode("utf-8")
                self.assertIn('<w:charset w:val="86"/>', font_table)
                content_types = archive.read("[Content_Types].xml").decode("utf-8")
                self.assertIn('Extension="odttf"', content_types)
                settings = archive.read("word/settings.xml").decode("utf-8")
                self.assertIn("<w:embedTrueTypeFonts", settings)

    def test_restricted_font_is_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docx_path = Path(tmp) / "m.docx"
            self._make_docx(docx_path)
            report = EF.embed_fonts_into_docx(
                docx_path, {"方正小标宋简体": EF.FONT_DIR / "方正小标宋简体.ttf"})
            self.assertEqual(report["embedded"], [])
            self.assertEqual(len(report["skipped"]), 1)
            self.assertIn("fsType", report["skipped"][0]["reason"])

    def test_generated_minutes_docx_embeds_both_gb2312_faces(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docx_path = Path(tmp) / "m.docx"
            self._make_docx(docx_path)
            report = EF.embed_fonts_into_docx(docx_path, EF.default_font_paths())
            fonts = sorted(e["font"] for e in report["embedded"])
            self.assertEqual(fonts, ["仿宋_GB2312", "楷体_GB2312"])
            self.assertTrue(EF.verify_embedded_fonts(docx_path)["ok"])


if __name__ == "__main__":
    unittest.main()
