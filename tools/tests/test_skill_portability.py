"""Portable archives and installs, isolated from real Agent configuration."""
import argparse
import importlib.util
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

REPO = Path(__file__).resolve().parents[2]
SKILLS = ('hangye-fenxi', 'zhuying-yewu-fenxi', 'gongsi-qingkuang')
spec = importlib.util.spec_from_file_location(
    'portability', REPO / 'gongsi-qingkuang/scripts/skill_portability.py')
portable = importlib.util.module_from_spec(spec)
spec.loader.exec_module(portable)


class SkillPortabilityTests(unittest.TestCase):
    def test_each_archive_is_self_contained_and_runs_after_extraction(self):
        for skill in SKILLS:
            with self.subTest(skill=skill), tempfile.TemporaryDirectory() as tmp:
                directory = Path(tmp)
                archive = portable.package(REPO / skill, directory / 'zips')
                with zipfile.ZipFile(archive) as zipped:
                    self.assertEqual({name.split('/')[0] for name in zipped.namelist()}, {skill})
                    self.assertFalse(any('__pycache__' in name or name.endswith('.pyc') for name in zipped.namelist()))
                    zipped.extractall(directory / 'Extracted with spaces 中文')
                installed = directory / 'Extracted with spaces 中文' / skill
                check = subprocess.run(
                    [sys.executable, '-X', 'utf8', str(installed / 'scripts/skill_portability.py'), 'check', '--smoke'],
                    cwd=directory, capture_output=True, encoding='utf-8')
                self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
                self.assertIn('Package SHA-256 manifest matches', check.stdout)
                for stage in ('early', 'mid-late'):
                    output = directory / (stage + '.json')
                    initialized = subprocess.run(
                        [sys.executable, '-X', 'utf8', str(installed / 'scripts/stage_template.py'),
                         'init', '--stage', stage, '--output', str(output)],
                        cwd=directory, capture_output=True, encoding='utf-8')
                    self.assertEqual(initialized.returncode, 0, initialized.stdout + initialized.stderr)
                    content = json.loads(output.read_text('utf-8'))
                    self.assertEqual(content['report_template']['skill'], skill)
                    self.assertEqual(content['report_template']['stage'], stage)
                # Tampering must fail, even when the changed file is only a reference.
                reference = installed / 'references/investment-logic-review.md'
                reference.write_text(reference.read_text(encoding='utf-8') + '\nchanged', encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                    portable.check(installed)

    def test_install_dry_run_backup_and_extra_file_preservation(self):
        root = REPO / 'gongsi-qingkuang'
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / 'agent' / 'skills'
            portable.install(root, destination)
            self.assertFalse(destination.exists())
            portable.install(root, destination, apply=True)
            portable.check(destination / root.name)
            portable.install(root, destination, apply=True)
            backups = list((destination.parent / 'skill-backups').glob(root.name + '-*'))
            self.assertEqual(len(backups), 1)
            self.assertTrue((backups[0] / 'SKILL.md').is_file())
            local_extra = destination / root.name / 'personal-notes.txt'
            local_extra.write_text('preserve this', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'extra files'):
                portable.install(root, destination, apply=True)
            self.assertEqual(local_extra.read_text(encoding='utf-8'), 'preserve this')

    def test_official_path_variants_and_kimi_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            for agent, relative in portable.DIRECTORIES.items():
                args = argparse.Namespace(agent=agent, scope='user', skills_dir=None, project_dir=None)
                with patch.object(Path, 'home', return_value=base), patch.dict(os.environ, {'KIMI_CODE_HOME': ''}):
                    self.assertEqual(portable.install_root(args), base / relative)
            args = argparse.Namespace(agent='trae-cn', scope='project', skills_dir=None, project_dir=str(base))
            self.assertEqual(portable.install_root(args), base / '.trae/skills')
            args = argparse.Namespace(agent='kimi-code', scope='user', skills_dir=None, project_dir=None)
            with patch.dict(os.environ, {'KIMI_CODE_HOME': str(base / 'custom-kimi')}):
                self.assertEqual(portable.install_root(args), base / 'custom-kimi/skills')

    def test_zip_is_reproducible_and_rejects_output_inside_source(self):
        root = REPO / 'gongsi-qingkuang'
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            first = portable.package(root, output).read_bytes()
            self.assertEqual(first, portable.package(root, output).read_bytes())
            copied = output / 'windows-checkout' / root.name
            shutil.copytree(root, copied)
            for source in portable.included_files(copied):
                if source.suffix in ('.md', '.py', '.json', '.yaml', '.txt', '.ps1'):
                    source.write_bytes(portable.payload(source).replace(b'\n', b'\r\n'))
            self.assertEqual(first, portable.package(copied, output / 'other-zips').read_bytes())
        with self.assertRaisesRegex(ValueError, 'outside the skill'):
            portable.package(root, root / 'dist')


if __name__ == '__main__':
    unittest.main()
