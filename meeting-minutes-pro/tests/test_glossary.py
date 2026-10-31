from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
import glossary


class GlossaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        return path

    def structured(self, name='project.json', entries=()):
        return self.write(name, json.dumps({'schema_version': 1, 'entries': list(entries)}, ensure_ascii=False))

    def test_legacy_comments_bom_and_original_order(self):
        path = self.write('project.txt', '\ufeff# 项目说明\r\n  # 备注\r\n项目甲 C#\n\n项目甲 A ASIC\n')
        self.assertEqual(glossary.collect_terms([path], ['ASIC', '新词', '#标签']),
                         ['项目甲', 'C#', 'ASIC', '新词', '#标签'])

    def test_json_preserves_phrase_and_confirmed_aliases(self):
        path = self.structured(entries=[{'term': 'Full Mask', 'status': 'confirmed',
                                         'aliases': ['全掩膜', 'Full Mask'], 'misrecognitions': ['错写词']}])
        self.assertEqual(glossary.collect_terms([path], []), ['Full Mask', '全掩膜'])
        result = glossary.prepare_context([path])
        self.assertEqual(result['terms'], ['Full Mask', '全掩膜'])
        self.assertNotIn('错写词', result['context'])

    def test_missing_status_defaults_to_candidate(self):
        path = self.structured(entries=[{'term': '未确认', 'aliases': ['候选简称']},
                                         {'term': '已确认', 'status': 'confirmed'}])
        self.assertEqual(glossary.collect_terms([path], []), ['已确认'])
        result = glossary.prepare_context([path])
        self.assertEqual(result['terms'], ['已确认'])
        self.assertEqual([x['reason'] for x in result['dropped']], ['candidate', 'candidate'])

    def test_misrecognitions_are_review_only(self):
        path = self.structured(entries=[{'term': '规范词', 'status': 'confirmed',
                                         'misrecognitions': ['近音错词']},
                                         {'term': '未确认', 'misrecognitions': ['未确认错词']}])
        self.assertEqual(glossary.collect_risk_terms([path]), ['规范词', '近音错词'])
        result = glossary.prepare_context([path])
        self.assertEqual(result['terms'], ['规范词'])
        self.assertIn({'term': '近音错词', 'reason': 'review_only'},
                      [{'term': x['term'], 'reason': x['reason']} for x in result['dropped']])

    def test_explicit_then_project_then_supplied_industry(self):
        industry = self.structured('industry/domain.json', [
            {'term': '行业词', 'status': 'confirmed', 'priority': 100}])
        project = self.structured(entries=[{'term': '项目词', 'status': 'confirmed'}])
        result = glossary.prepare_context([industry, project], context='本场词', limit=11)
        self.assertEqual(result['terms'], ['本场词', '项目词', '行业词'])
        self.assertEqual(len(result['context']), 11)

    def test_priority_within_tier_and_deduplication(self):
        path = self.structured(entries=[{'term': '普通词', 'status': 'confirmed'},
                                         {'term': '重点词', 'status': 'confirmed', 'priority': 5},
                                         {'term': '普通词', 'status': 'confirmed', 'priority': 1}])
        result = glossary.prepare_context([path], context='重点词')
        self.assertEqual(result['terms'], ['重点词', '普通词'])
        self.assertEqual(sum(x['reason'] == 'duplicate' for x in result['dropped']), 2)

    def test_project_mismatch_is_excluded(self):
        path = self.structured(entries=[{'term': '甲方词', 'status': 'confirmed', 'project': '甲'},
                                         {'term': '乙方词', 'status': 'confirmed', 'project': '乙'}])
        result = glossary.prepare_context([path], project='甲')
        self.assertEqual(result['terms'], ['甲方词'])
        self.assertEqual(result['dropped'][0]['reason'], 'project_mismatch')

    def test_explicit_terms_preserve_phrases_and_override_project_filter(self):
        path = self.structured(entries=[{'term': '另项目词', 'status': 'confirmed', 'project': '乙'}])
        result = glossary.prepare_context([path], context='另项目词', project='甲',
                                          extra_terms=['Full Mask'])
        self.assertEqual(result['terms'], ['另项目词', 'Full Mask'])
        self.assertEqual(result['dropped'][0]['reason'], 'project_mismatch')
        self.assertEqual(result['selected'][0]['origin'], 'explicit')

    def test_exact_400_boundary_does_not_cut_a_term(self):
        path = self.structured(entries=[{'term': '甲' * 400, 'status': 'confirmed'},
                                         {'term': '溢出词', 'status': 'confirmed'}])
        result = glossary.prepare_context([path], limit=400)
        self.assertEqual(result['context'], '甲' * 400)
        self.assertEqual(result['dropped'][0]['reason'], 'budget')

    def test_long_term_skipped_without_losing_later_short_term(self):
        path = self.structured(entries=[{'term': '甲' * 401, 'status': 'confirmed'},
                                         {'term': '短词', 'status': 'confirmed'}])
        result = glossary.prepare_context([path], context='优先', limit=400)
        self.assertEqual(result['context'], '优先 短词')
        self.assertEqual(result['dropped'][0]['term'], '甲' * 401)

    def test_zero_budget_is_empty_and_negative_budget_rejected(self):
        self.assertEqual(glossary.prepare_context([], context='术语', limit=0)['context'], '')
        for limit in (-1, True, 1.5):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                glossary.prepare_context([], limit=limit)

    def test_seaco_phrase_limitation_is_reported(self):
        path = self.structured(entries=[{'term': 'Full Mask', 'status': 'confirmed'}])
        result = glossary.prepare_context([path], limit=9, engine='funasr')
        self.assertEqual(result['terms'], ['Full Mask'])
        self.assertEqual(result['context'], 'Full Mask')
        self.assertTrue(any('SeacoParaformer' in note for note in result['adapter_notes']))
        self.assertFalse(any('SeacoParaformer' in note for note in glossary.prepare_context([path])['adapter_notes']))

    def test_only_explicitly_supplied_files_are_loaded(self):
        self.write('industry/unrelated.txt', '无关行业词')
        path = self.write('project.txt', '项目甲')
        result = glossary.prepare_context([path])
        self.assertEqual(result['terms'], ['项目甲'])
        self.assertEqual(len(result['input_files']), 1)
        self.assertEqual(len(result['input_files'][0]['sha256']), 64)

    def test_invalid_schema_and_fields_fail_instead_of_silent_fallback(self):
        invalid = [[], {}, {'schema_version': True, 'entries': []},
                   {'schema_version': 2, 'entries': []}, {'schema_version': 1, 'entries': {}},
                   {'schema_version': 1, 'entries': [{'term': ''}]},
                   {'schema_version': 1, 'entries': [{'term': '词条', 'status': 'done'}]},
                   {'schema_version': 1, 'entries': [{'term': '词条', 'aliases': '别名'}]},
                   {'schema_version': 1, 'entries': [{'term': '词条', 'priority': True}]},
                   {'schema_version': 1, 'entries': [{'term': '词条', 'unknown': 'x'}]},
                   {'schema_version': 1, 'entries': [{'term': '词条', 'source': []}]}]
        for document in invalid:
            with self.subTest(document=document):
                path = self.write('invalid.json', json.dumps(document, ensure_ascii=False))
                with self.assertRaises(ValueError):
                    glossary.prepare_context([path])
        path = self.write('invalid.json', '{')
        with self.assertRaises(ValueError):
            glossary.collect_terms([path], [])

    def test_cli_exports_manifest_without_changing_sources(self):
        path = self.write('project.txt', '# 说明\n项目甲\n')
        original = path.read_bytes()
        output = self.root / 'job/context.json'
        self.assertEqual(glossary.main(['--glossary', str(path), '--output', str(output)]), 0)
        self.assertEqual(json.loads(output.read_text(encoding='utf-8'))['context'], '项目甲')
        self.assertEqual(path.read_bytes(), original)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(glossary.main(['--glossary', str(path), '--output', str(path)]), 1)
        self.assertEqual(path.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
