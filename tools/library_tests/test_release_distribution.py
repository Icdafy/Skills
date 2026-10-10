"""Release migration checks: independent writes, byte locks and cache-only verification."""
from contextlib import redirect_stderr, redirect_stdout
import copy
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import check_library
import package_investment_skills
import package_skills
import skill_catalog
import sync_catalog

REPO = TOOLS.parent
SKILL = 'yiti-skill'


def copy_skill(destination):
    shutil.copytree(REPO / SKILL, destination,
                    ignore=shutil.ignore_patterns('*.ttf', '*.otf', '*.ttc', '*.woff',
                                                 '*.woff2', '*.odttf', '__pycache__'))


class ReleaseDistributionTests(unittest.TestCase):
    def test_download_table_uses_independent_release_tags(self):
        index = skill_catalog.load_index()
        table = sync_catalog.table(index)
        self.assertNotIn('distributions/', table)
        for entry in index['skills']:
            name, version = entry['id'], entry['version']
            expected = (f'https://github.com/Icdafy/Skills/releases/download/'
                        f'{name}%2Fv{version}/{name}.zip')
            with self.subTest(skill=name):
                self.assertEqual(skill_catalog.release_asset_url(entry), expected)
                self.assertIn(f'[ZIP]({expected})', table)
                self.assertEqual(skill_catalog.release_asset_url(entry, True), expected + '.sha256')
                self.assertEqual(skill_catalog.release_archive_path(entry, Path('repo')),
                                 Path('repo/work/releases') / name / version / (name + '.zip'))

    def test_index_rejects_release_binding_and_legacy_archive_errors(self):
        index = skill_catalog.load_index()
        cases = (
            ('tag', '../other/v1.0.0', 'Release tag'),
            ('asset', '../another.zip', 'asset name'),
            ('sha256', 'not-a-digest', 'SHA-256'),
        )
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            for field, value, message in cases:
                changed = copy.deepcopy(index)
                changed['skills'][0]['release'][field] = value
                (repo / 'skills-index.json').write_text(json.dumps(changed), encoding='utf-8')
                with self.subTest(field=field), self.assertRaisesRegex(ValueError, message):
                    skill_catalog.load_index(repo)
            changed = copy.deepcopy(index)
            changed['skills'][0]['archive'] = 'distributions/old.zip'
            (repo / 'skills-index.json').write_text(json.dumps(changed), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Legacy tracked archive'):
                skill_catalog.load_index(repo)

    def test_build_requires_an_explicit_selection(self):
        with patch.object(package_skills.portable, 'package') as build:
            for command, argv in (
                    (package_skills.main, []),
                    (package_skills.main, ['--group', 'investment-report-skills']),
                    (package_investment_skills.main, [])):
                with self.subTest(argv=argv), redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as error:
                        command(argv)
                    self.assertEqual(error.exception.code, 2)
            build.assert_not_called()

    def test_a_target_build_preserves_other_release_assets(self):
        index = skill_catalog.load_index()
        catalog = {entry['id']: entry for entry in index['skills']}
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / 'skills-index.json').write_text(json.dumps(index), encoding='utf-8')
            copy_skill(repo / SKILL)
            other = skill_catalog.release_archive_path(catalog['officialese-skill'], repo)
            other.parent.mkdir(parents=True)
            other.write_bytes(b'preserve the other skill archive')
            checksum = other.with_name(other.name + '.sha256')
            checksum.write_bytes(b'preserve the other skill checksum')
            with patch.object(package_skills, 'REPO', repo), redirect_stdout(io.StringIO()):
                self.assertEqual(package_skills.main(['--skill', SKILL]), 0)
            self.assertTrue(skill_catalog.release_archive_path(catalog[SKILL], repo).is_file())
            self.assertEqual(other.read_bytes(), b'preserve the other skill archive')
            self.assertEqual(checksum.read_bytes(), b'preserve the other skill checksum')
            self.assertFalse((repo / 'distributions').exists())

    def test_legacy_wrapper_all_selects_exactly_its_three_skills(self):
        with patch.object(package_skills, 'main', return_value=0) as invoke:
            self.assertEqual(package_investment_skills.main(['--all']), 0)
            argv = invoke.call_args.args[0]
            selected = [argv[i + 1] for i, value in enumerate(argv) if value == '--skill']
            self.assertEqual(selected, list(package_investment_skills.INVESTMENT))
            self.assertNotIn('--all', argv)
            invoke.reset_mock()
            for argv in (['--skill', 'officialese-skill'], ['--group', 'office-skills']):
                with self.subTest(argv=argv), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    package_investment_skills.main(argv)
            invoke.assert_not_called()

    def test_published_lock_and_current_source_both_have_to_match(self):
        entry = copy.deepcopy(package_skills.CATALOG[SKILL])
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(io.StringIO()):
            directory = Path(tmp)
            archive = package_skills.portable.package(REPO / SKILL, directory / 'assets')
            original = archive.read_bytes()
            entry['release']['sha256'] = hashlib.sha256(original).hexdigest()
            with patch.object(package_skills, 'CATALOG', {SKILL: entry}):
                package_skills.verify(SKILL, archive.parent)
                archive.write_bytes(original + b'tampered')
                with self.assertRaisesRegex(ValueError, 'ZIP checksum mismatch'):
                    package_skills.verify(SKILL, archive.parent)
                archive.write_bytes(original)
                checksum = archive.with_name(archive.name + '.sha256')
                checksum.write_text('0' * 64 + '  ' + archive.name + '\n', encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'published SHA-256 differs'):
                    package_skills.verify(SKILL, archive.parent)
                copied = directory / 'source' / SKILL
                copy_skill(copied)
                readme = copied / 'README.md'
                readme.write_text(readme.read_text(encoding='utf-8') + '\nChanged documentation.\n',
                                  encoding='utf-8')
                changed_archive = package_skills.portable.package(copied, archive.parent)
                entry['release']['sha256'] = hashlib.sha256(changed_archive.read_bytes()).hexdigest()
                with self.assertRaisesRegex(ValueError, 'release ZIP is stale'):
                    package_skills.verify(SKILL, archive.parent)

    def test_download_rejects_corruption_before_writing_the_cache(self):
        entry = copy.deepcopy(package_skills.CATALOG[SKILL])
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(io.StringIO()):
            directory = Path(tmp)
            archive = package_skills.portable.package(REPO / SKILL, directory / 'assets')
            body = archive.read_bytes()
            entry['release']['sha256'] = hashlib.sha256(body).hexdigest()
            checksum = archive.with_name(archive.name + '.sha256').read_bytes()
            payloads = {skill_catalog.release_asset_url(entry): body,
                        skill_catalog.release_asset_url(entry, True): checksum}

            def response(request, timeout):
                self.assertEqual(timeout, 30)
                return io.BytesIO(payloads[request.full_url])

            with patch.object(package_skills, 'CATALOG', {SKILL: entry}), \
                    patch.object(package_skills.urllib.request, 'urlopen', side_effect=response) as fetch:
                cache = directory / 'cache'
                downloaded = package_skills.download(SKILL, cache)
                self.assertEqual(downloaded.read_bytes(), body)
                package_skills.verify(SKILL, cache)
                self.assertEqual(fetch.call_count, 2)
                package_skills.download(SKILL, cache)
                self.assertEqual(fetch.call_count, 2)
                package_skills.download(SKILL, cache, force=True)
                self.assertEqual(fetch.call_count, 4)
                payloads[skill_catalog.release_asset_url(entry)] = body + b'corrupt'
                bad_cache = directory / 'bad-cache'
                with self.assertRaisesRegex(ValueError, 'ZIP checksum mismatch'):
                    package_skills.download(SKILL, bad_cache)
                self.assertFalse(bad_cache.exists())

    def test_default_library_check_does_not_fetch_missing_release_assets(self):
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(check_library, 'check_distribution'), \
                patch.object(check_library, 'check_links'), \
                patch.object(sync_catalog, 'main', return_value=0), \
                patch.object(package_skills, 'archive_path',
                             side_effect=lambda name: Path(tmp) / (name + '.zip')), \
                patch.object(package_skills, 'download') as fetch, \
                patch.object(package_skills, 'verify') as verify, \
                patch.object(sys, 'argv', ['check_library.py']), \
                redirect_stdout(io.StringIO()) as output:
            self.assertEqual(check_library.main(), 0)
            fetch.assert_not_called()
            verify.assert_not_called()
            self.assertIn('release contents were not fully verified', output.getvalue())


if __name__ == '__main__':
    unittest.main()
