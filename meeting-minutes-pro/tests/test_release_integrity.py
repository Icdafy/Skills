"""Release evidence must describe the actual edits and every rendered page."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
import review_gate as gate
from run_state import file_hash


class FindingClassificationTests(unittest.TestCase):
    def test_success_counts_do_not_create_manual_review_work(self):
        lines = ['提示：冗余归因表述检查：0 处残留。',
                 '提示：总结概述转述句式检查：0 处残留。',
                 '提示：解释性括注检查：0 处残留。',
                 '提示：加工元说明检查：0 处残留。',
                 '提示：问答 2 组。数字事实核对请另行运行 fact_check.py。']
        checks = [{'name': 'quality_check', 'stdout': '\n'.join(lines)}]
        self.assertEqual(list(gate.check_findings(checks, {})), [])

    def test_waivers_and_real_diagnostics_remain_reviewable(self):
        checks = [{'name': 'quality_check', 'stdout':
                   '提示：第 3 行的表述已按转录稿真实内容放行，交付前向用户说明。\n'
                   '提示：解释性括注检查：1 处残留。'},
                  {'name': 'fact_check', 'stdout':
                   '提示：1 处数字的纪要语境与转录稿依据语境相似度较低'},
                  {'name': 'qa_reconcile', 'stdout': '警告：原始提问未匹配。'}]
        findings = list(gate.check_findings(checks, {'allow_line': [3]}))
        self.assertEqual(len(findings), 5)


class RevisionReplayTests(unittest.TestCase):
    def check(self, before, after, entries):
        rows = [dict(start=i, end=i + 1, before=old, after=new)
                for i, (old, new) in enumerate(entries)]
        return gate.validate_revision_text({'text': before}, {'text': after}, rows)

    def test_unrelated_log_cannot_authorize_changed_facts(self):
        self.assertTrue(self.check('收入100万元。', '收入900万元，客户20家。',
                                   [('完全不存在的原文', '与真正修改无关')]))

    def test_log_must_cover_every_change(self):
        self.assertTrue(self.check('收入100万元，客户10家。', '收入900万元，客户20家。',
                                   [('收入100万元', '收入900万元')]))

    def test_complete_disjoint_edits_pass(self):
        self.assertEqual(self.check('收入100万元，客户10家。', '收入900万元，客户20家。',
                                    [('收入100万元', '收入900万元'), ('客户10家', '客户20家')]), [])

    def test_insert_delete_and_export_whitespace_pass(self):
        self.assertEqual(self.check('收入100万元。重复说明。', '\n收入100万元，客户20家。\n',
                                    [('', '，客户20家'), ('重复说明。', '')]), [])

    def test_repeated_phrases_do_not_select_wrong_occurrence(self):
        self.assertEqual(self.check('营收100万元，成本100万元。', '营收100万元，成本200万元。',
                                    [('100万元', '200万元')]), [])

    def test_insertion_only_cannot_hide_unlogged_replacement(self):
        self.assertTrue(self.check('收入100万元。', '收入900万元，客户20家。', [('', '，客户20家')]))


class RenderEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.docx = self.root / 'minutes.docx'
        self.docx.write_bytes(b'version-bound-document')
        self.report = self.root / 'minutes.render.json'
        self.valid = {'docx_sha256': file_hash(self.docx), 'pdf_sha256': '1' * 64,
                      'renderer': 'word', 'pages': 2, 'ok': True,
                      'missing_required_fonts': [], 'substituted_fonts': [],
                      'page_number_check': {'available': True, 'ok': True, 'pages': [
                          {'page': 1, 'expected': 'right', 'detected': 'right', 'ok': True},
                          {'page': 2, 'expected': 'left', 'detected': 'left', 'ok': True}]}}

    def check(self, payload):
        self.report.write_text(json.dumps(payload), encoding='utf8')
        return gate.validate_render(self.report, self.docx)

    def test_full_generator_report_passes_without_retaining_pdf(self):
        self.assertEqual(self.check(self.valid), [])

    def test_empty_report_cannot_claim_rendering(self):
        self.assertTrue(self.check({'docx_sha256': file_hash(self.docx), 'ok': True,
                                   'page_number_check': {'ok': True, 'pages': []}}))

    def test_missing_repeated_and_wrong_pages_fail(self):
        for pages in ([], [self.valid['page_number_check']['pages'][0]],
                      [self.valid['page_number_check']['pages'][0]] * 2):
            payload = copy.deepcopy(self.valid)
            payload['page_number_check']['pages'] = pages
            self.assertTrue(self.check(payload))
        payload = copy.deepcopy(self.valid)
        payload['page_number_check']['pages'][1]['detected'] = 'right'
        self.assertTrue(self.check(payload))

    def test_invalid_provenance_and_page_count_fail(self):
        for field, value in (('renderer', ''), ('pdf_sha256', ''), ('pages', 0),
                             ('pages', True), ('pages', '2')):
            payload = copy.deepcopy(self.valid)
            payload[field] = value
            self.assertTrue(self.check(payload), field)


if __name__ == '__main__':
    unittest.main()
