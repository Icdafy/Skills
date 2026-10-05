"""Thirteen real positive/negative pairs replacing the removed font-resource assumption."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

from docx import Document

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'tools/tests'))
from font_fixture import FontFixture, sfnt
from test_sibling_docx_skills import BUILDERS, embedded_entries


def load(name):
    path = REPO / name / 'scripts/embed_fonts.py'
    spec = importlib.util.spec_from_file_location('contract_' + name.replace('-', '_'), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


COMMON = load('gongsi-qingkuang')
MINUTES = load('meeting-minutes-pro')


class FontContractPairs(unittest.TestCase):
    def setUp(self):
        self.fixture = FontFixture()
        self.fonts = self.fixture.__enter__()
        self.addCleanup(self.fixture.__exit__)
        self.temp = tempfile.TemporaryDirectory(prefix='font-contract-output-')
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name)

    def empty_fonts(self):
        folder = self.output / '无字体 空目录'
        folder.mkdir(exist_ok=True)
        os.environ['ICDAFY_FONT_DIR'] = str(folder)

    def docx(self, name='test.docx'):
        path = self.output / name
        document = Document()
        document.add_paragraph('中文 ABC 20%')
        document.save(path)
        return path

    def test_common_resolution_present_and_absent(self):
        for skill in BUILDERS:
            module = load(skill)
            self.assertEqual(set(module.resolve_bundled_fonts()), {'仿宋_GB2312', '楷体_GB2312', '方正小标宋简体'})
        self.empty_fonts()
        for skill in BUILDERS:
            self.assertEqual(load(skill).resolve_bundled_fonts(), {})

    def test_common_title_gate_allowed_and_restricted(self):
        self.assertTrue(COMMON.is_embeddable(COMMON.read_fs_type(sfnt(0))))
        self.assertFalse(COMMON.is_embeddable(COMMON.read_fs_type(sfnt(2))))

    def test_common_charset_readable_and_unreadable(self):
        self.assertIn('w:charset w:val="86"', COMMON.font_descriptor(sfnt()))
        self.assertEqual(COMMON.font_descriptor(b'no OS2 table'), '')

    def test_common_roundtrip_correct_and_wrong_key(self):
        key = COMMON.new_font_key()
        raw = sfnt()
        encoded = COMMON.obfuscate(raw, key)
        self.assertEqual(COMMON.deobfuscate(encoded, key), raw)
        self.assertNotEqual(COMMON.deobfuscate(encoded, '{FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF}'), raw)

    def test_common_generators_with_and_without_local_fonts(self):
        for skill, builder in BUILDERS.items():
            target = self.output / (skill + '.docx')
            result = subprocess.run(builder(skill, target, self.output), capture_output=True, encoding='utf-8')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual({n for n, _ in embedded_entries(target)}, {'仿宋_GB2312', '楷体_GB2312'})
        self.empty_fonts()
        for skill, builder in BUILDERS.items():
            target = self.output / (skill + '-draft.docx')
            result = subprocess.run(builder(skill, target, self.output), capture_output=True, encoding='utf-8')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('缺少本机授权字体', result.stdout + result.stderr)
            self.assertEqual(embedded_entries(target), [])

    def test_common_document_embeds_allowed_and_rejects_title(self):
        target = self.docx()
        report = COMMON.embed_fonts_into_docx(target, {'仿宋_GB2312': self.fonts / 'simfang.ttf',
                                                     '方正小标宋简体': self.fonts / '方正小标宋简体.ttf'})
        self.assertEqual([e['font'] for e in report['embedded']], ['仿宋_GB2312'])
        self.assertEqual([e['font'] for e in report['skipped']], ['方正小标宋简体'])
        self.assertIn('fsType', report['skipped'][0]['reason'])

    def test_minutes_fs_type_allowed_and_restricted(self):
        self.assertEqual(MINUTES.read_fs_type(sfnt()), 0)
        self.assertTrue(MINUTES.is_embeddable(0))
        self.assertEqual(MINUTES.read_fs_type(sfnt(2)), 2)
        self.assertFalse(MINUTES.is_embeddable(2))

    def test_minutes_title_embeddability_present_and_denied(self):
        title = self.fonts / '方正小标宋简体.ttf'
        target = self.docx()
        denied = MINUTES.embed_fonts_into_docx(target, {'方正小标宋简体': title})
        self.assertEqual(denied['embedded'], [])
        self.assertIn('fsType=2', denied['skipped'][0]['reason'])
        allowed = MINUTES.embed_fonts_into_docx(target, {'仿宋_GB2312': self.fonts / 'simfang.ttf'})
        self.assertTrue(MINUTES.verify_embedded_fonts(target)['ok'])
        self.assertEqual([f['font'] for f in allowed['embedded']], ['仿宋_GB2312'])

    def test_minutes_signature_valid_and_invalid(self):
        self.assertTrue(MINUTES.is_sfnt(sfnt()))
        self.assertFalse(MINUTES.is_sfnt(b'not a font'))
        self.assertFalse(MINUTES.is_embeddable(MINUTES.read_fs_type(b'not a font')))

    def test_minutes_descriptor_gb2312_and_other_charset(self):
        self.assertIn('w:charset w:val="86"', MINUTES.font_descriptor(sfnt()))
        self.assertNotIn('w:charset w:val="86"', MINUTES.font_descriptor(sfnt(code_page=0)))

    def test_minutes_embed_valid_and_corrupt_part(self):
        target = self.docx()
        MINUTES.embed_fonts_into_docx(target, {'仿宋_GB2312': self.fonts / 'simfang.ttf'})
        self.assertTrue(MINUTES.verify_embedded_fonts(target)['ok'])
        with zipfile.ZipFile(target) as zipped:
            parts = {n: zipped.read(n) for n in zipped.namelist()}
        parts['word/fonts/font1.odttf'] = b'corrupt'
        with zipfile.ZipFile(target, 'w') as zipped:
            for n, body in parts.items():
                zipped.writestr(n, body)
        self.assertFalse(MINUTES.verify_embedded_fonts(target)['ok'])

    def test_minutes_missing_path_reports_failure_after_valid_input(self):
        target = self.docx()
        good = MINUTES.embed_fonts_into_docx(target, {'仿宋_GB2312': self.fonts / 'simfang.ttf'})
        self.assertEqual(len(good['embedded']), 1)
        bad = MINUTES.embed_fonts_into_docx(self.docx('missing.docx'), {'仿宋_GB2312': self.fonts / 'missing.ttf'})
        self.assertEqual(bad['embedded'], [])
        self.assertEqual(len(bad['skipped']), 1)
        self.assertFalse(MINUTES.verify_embedded_fonts(self.output / 'missing.docx')['ok'])

    def test_minutes_default_paths_present_and_generator_fails_when_missing(self):
        self.assertEqual(set(MINUTES.default_font_paths()), {'仿宋_GB2312', '楷体_GB2312'})
        source = self.output / '纪要.txt'
        source.write_text('示例会议纪要\n\n　　一、会议基本情况\n　　会议时间：2026年10月5日。\n'
                          '　　会议地点：会议室。\n\n　　二、会议主要内容\n　　公司介绍项目进展。\n', encoding='utf-8')
        args = [sys.executable, str(REPO / 'meeting-minutes-pro/scripts/create_minutes_docx.py'),
                '--input', str(source), '--output', str(self.output / 'minutes.docx'), '--mode', 'minutes']
        result = subprocess.run(args, capture_output=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.empty_fonts()
        self.assertEqual(MINUTES.default_font_paths(), {})
        result = subprocess.run(args, capture_output=True, encoding='utf-8')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('缺少本机', result.stderr)


if __name__ == '__main__':
    unittest.main()
