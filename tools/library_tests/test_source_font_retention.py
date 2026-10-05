"""Verify exact historical font retention without shipping fonts in skill payloads."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    'retention_portable', REPO / 'gongsi-qingkuang/scripts/skill_portability.py')
PORTABLE = importlib.util.module_from_spec(spec)
spec.loader.exec_module(PORTABLE)


class SourceFontRetention(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='原字体 保留与打包 ')
        self.addCleanup(self.temp.cleanup)
        self.outer = Path(self.temp.name)
        self.skill = self.outer / 'gongsi-qingkuang'
        shutil.copytree(REPO / 'gongsi-qingkuang', self.skill,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))

    def test_original_eighteen_files_and_contract_match_baseline(self):
        baseline = json.loads((REPO / 'docs/validation/baseline/restricted-fonts.json').read_text('utf-8'))
        policy = json.loads((REPO / 'skills-index.json').read_text('utf-8'))['font_policy']
        self.assertEqual(len(baseline), 18)
        self.assertEqual(len({f['path'].split('/')[0] for f in baseline}), 6)
        self.assertEqual(policy['retained_source_fonts'], baseline)
        self.assertFalse(policy['single_skill_zip_fonts'])
        self.assertFalse(policy['redistribution_authorization_confirmed'])
        self.assertEqual(PORTABLE.RETAINED_SOURCE_FONT_SHA256,
                         {f['path']: f['sha256'] for f in baseline})
        for item in baseline:
            path = REPO / item['path']
            self.assertFalse(path.is_symlink())
            self.assertEqual(path.stat().st_size, item['bytes'])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), item['sha256'])

    def test_real_package_excludes_original_fonts_and_verifies_after_extract(self):
        self.assertEqual(len(list((self.skill / 'assets/fonts').glob('*.ttf'))), 3)
        record = PORTABLE.check(self.skill)
        self.assertFalse(any(p.endswith('.ttf') for p in record['files']))
        archive = PORTABLE.package(self.skill, self.outer / '下载包')
        with zipfile.ZipFile(archive) as zipped:
            self.assertFalse(any(p.endswith('.ttf') for p in zipped.namelist()))
            zipped.extractall(self.outer / '仓库外 中文 空格')
        extracted = self.outer / '仓库外 中文 空格/gongsi-qingkuang'
        self.assertEqual(PORTABLE.check(extracted), record)

    def test_modified_original_font_is_rejected(self):
        PORTABLE.check(self.skill)
        font = self.skill / 'assets/fonts/simfang.ttf'
        font.write_bytes(font.read_bytes() + b'changed')
        with self.assertRaisesRegex(ValueError, 'Retained source font changed'):
            PORTABLE.check(self.skill)

    def test_new_font_path_with_original_bytes_is_rejected(self):
        PORTABLE.check(self.skill)
        shutil.copyfile(self.skill / 'assets/fonts/simfang.ttf',
                        self.skill / 'assets/fonts/new-font.ttf')
        with self.assertRaisesRegex(ValueError, 'Restricted font distribution'):
            PORTABLE.check(self.skill)


if __name__ == '__main__':
    unittest.main()
