"""Portable archives and installs, isolated from real Agent configuration."""
import argparse
import importlib.util
import json
import os
import re
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

REPO = Path(__file__).resolve().parents[2]
INVESTMENT = ('hangye-fenxi', 'zhuying-yewu-fenxi', 'gongsi-qingkuang')
SKILLS = INVESTMENT + ('officialese-skill', 'yiti-skill', 'meeting-minutes-pro', 'soe-post-investment-report')
spec = importlib.util.spec_from_file_location(
    'portability', REPO / 'gongsi-qingkuang/scripts/skill_portability.py')
portable = importlib.util.module_from_spec(spec)
spec.loader.exec_module(portable)
CLEAN_ENV = {'KIMI_CODE_HOME': '', 'CLAUDE_CONFIG_DIR': '', 'CODEX_HOME': '', 'OPENCLAW_STATE_DIR': ''}


def install_args(**overrides):
    values = dict(agent=None, detect=False, scope='user', skills_dir=None, project_dir=None)
    values.update(overrides)
    return argparse.Namespace(**values)


class SkillPortabilityTests(unittest.TestCase):
    def test_every_skill_has_a_profile_and_passes_check(self):
        self.assertEqual(set(portable.PROFILES), set(SKILLS))
        for skill in SKILLS:
            with self.subTest(skill=skill):
                fields = portable.metadata(REPO / skill)
                self.assertLessEqual(len(fields['description']), 200)
                portable.check(REPO / skill)

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
                if skill in INVESTMENT:
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
                reference = installed / 'references/agent-compatibility.md'
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
            # --replace moves the old copy aside instead of deleting anything.
            portable.install(root, destination, apply=True, replace=True)
            self.assertFalse(local_extra.exists())
            moved = list((destination.parent / 'skill-backups').rglob('personal-notes.txt'))
            self.assertTrue(moved)
            self.assertEqual(moved[-1].read_text(encoding='utf-8'), 'preserve this')
            portable.check(destination / root.name)

    def test_minutes_glossary_is_user_data(self):
        root = REPO / 'meeting-minutes-pro'
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'source' / root.name
            shutil.copytree(root, source, ignore=shutil.ignore_patterns('__pycache__', 'tests'))
            (source / 'glossary/某公司.txt').write_text('私有术语', encoding='utf-8')
            archive = portable.package(source, Path(tmp) / 'zips')
            with zipfile.ZipFile(archive) as zipped:
                names = zipped.namelist()
            self.assertNotIn(root.name + '/glossary/某公司.txt', names)
            self.assertIn(root.name + '/glossary/README.md', names)
            self.assertTrue(any(name.startswith(root.name + '/glossary/industry/') for name in names))
            skills = Path(tmp) / 'agent' / 'skills'
            portable.install(source, skills, apply=True)
            self.assertFalse((skills / root.name / 'glossary/某公司.txt').exists())
            user_file = skills / root.name / 'glossary' / 'banned-phrases.txt'
            user_file.write_text('机构禁词', encoding='utf-8')
            portable.install(source, skills, apply=True)  # not reported as a stale extra file
            portable.install(source, skills, apply=True, replace=True)
            self.assertEqual(user_file.read_text(encoding='utf-8'), '机构禁词')
            portable.check(skills / root.name)

    def test_skill_in_version_folder_is_identified_by_skill_md(self):
        # Claude Code and Codex plugin caches store a skill under <plugin>/<version>/.
        root = REPO / 'yiti-skill'
        with tempfile.TemporaryDirectory() as tmp:
            cached = Path(tmp) / 'cache' / 'yiti-skill' / '290e7a5f75c4'
            shutil.copytree(root, cached, ignore=shutil.ignore_patterns('__pycache__'))
            self.assertEqual(portable.check(cached)['name'], 'yiti-skill')
            archive = portable.package(cached, Path(tmp) / 'zips')
            self.assertEqual(archive.name, 'yiti-skill.zip')
            with zipfile.ZipFile(archive) as zipped:
                self.assertEqual({name.split('/')[0] for name in zipped.namelist()}, {'yiti-skill'})
            installed = portable.install(cached, Path(tmp) / 'skills', apply=True)
            self.assertEqual(installed, (Path(tmp) / 'skills' / 'yiti-skill').resolve())

    def test_official_path_variants_and_env_overrides(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            with patch.object(Path, 'home', return_value=base), patch.dict(os.environ, CLEAN_ENV):
                for agent, (user, project, _env, _label) in portable.AGENTS.items():
                    self.assertEqual(portable.agent_root(agent), base / user)
                    if project is None:
                        with self.assertRaisesRegex(ValueError, 'no project-level'):
                            portable.agent_root(agent, 'project', str(base))
                    else:
                        self.assertEqual(portable.agent_root(agent, 'project', str(base)), base / project)
                self.assertEqual(portable.agent_root('codex'), base / '.agents/skills')
                self.assertEqual(portable.agent_root('trae-cn', 'project', str(base)), base / '.trae/skills')
                # codex, chatgpt and agents share one folder: install it once.
                roots = portable.install_roots(install_args(agent=['codex', 'chatgpt', 'agents', 'claude-code']))
                self.assertEqual(roots, [base / '.agents/skills', base / '.claude/skills'])
                (base / '.workbuddy').mkdir()
                (base / '.trae-cn').mkdir()
                self.assertEqual(portable.install_roots(install_args(detect=True)),
                                 [base / '.trae-cn/skills', base / '.workbuddy/skills'])
            for agent, env in (('kimi-code', 'KIMI_CODE_HOME'), ('claude-code', 'CLAUDE_CONFIG_DIR'),
                               ('codex-legacy', 'CODEX_HOME'), ('openclaw', 'OPENCLAW_STATE_DIR')):
                with patch.dict(os.environ, {**CLEAN_ENV, env: str(base / 'custom')}):
                    self.assertEqual(portable.agent_root(agent), base / 'custom/skills')

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

    def test_strict_client_metadata_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / 'officialese-skill'
            skill.mkdir()
            cases = {
                'description: ' + '长' * 201: 'currently 201',
                'description: 用于: 公文': 'not plain YAML',
                'description: 公文\nversion: 1': 'rejected by strict clients',
                'description: 生成 <docx> 文件': 'angle brackets',
            }
            for body, message in cases.items():
                (skill / 'SKILL.md').write_text(f'---\nname: officialese-skill\n{body}\n---\n', encoding='utf-8')
                with self.subTest(body=body[:20]), self.assertRaisesRegex(ValueError, message):
                    portable.metadata(skill)

    def test_claude_code_marketplace_lists_every_skill(self):
        marketplace = json.loads((REPO / '.claude-plugin/marketplace.json').read_text(encoding='utf-8'))
        plugins = {plugin['name']: plugin for plugin in marketplace['plugins']}
        self.assertEqual(set(plugins), set(SKILLS))
        for skill, plugin in plugins.items():
            with self.subTest(skill=skill):
                self.assertEqual(plugin['source'], './' + skill)
                self.assertEqual(plugin['skills'], ['./'])
                self.assertFalse(plugin['strict'])
                self.assertEqual(plugin['description'], portable.metadata(REPO / skill)['description'])
                yaml = (REPO / skill / 'agents/openai.yaml').read_text(encoding='utf-8')
                self.assertRegex(yaml, re.compile(r'^\s*display_name:\s*\S', re.M))


if __name__ == '__main__':
    unittest.main()
