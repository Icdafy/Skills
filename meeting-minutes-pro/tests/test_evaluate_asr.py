from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
import evaluate_asr as evaluation


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def write(self, name, samples, **metadata):
        path = self.root / name
        path.write_text(json.dumps({'schema_version': 1, 'samples': samples, **metadata}, ensure_ascii=False), encoding='utf-8')
        return path

    def score(self, reference, hypothesis, **metadata):
        return evaluation.score(self.write('reference.json', reference),
                                self.write('hypothesis.json', hypothesis, **metadata))

    def test_exact_edit_counts(self):
        cases = [('甲乙', '甲丙', (1, 0, 0)), ('甲乙', '甲', (0, 1, 0)),
                 ('甲', '甲乙', (0, 0, 1)), ('', '', (0, 0, 0)),
                 ('', '假话', (0, 0, 2)), ('abcdef', 'azced', (2, 1, 0))]
        for reference, hypothesis, expected in cases:
            with self.subTest(reference=reference, hypothesis=hypothesis):
                counts = evaluation.edit_counts(reference, hypothesis)
                self.assertEqual(tuple(counts[key] for key in ('substitutions', 'deletions', 'insertions')), expected)

    def test_normalization_does_not_hide_numeric_errors(self):
        self.assertEqual(evaluation.normalized('营收 3万元，增长30%。'), '营收3万元增长30%')
        result = self.score([{'id': 'a', 'text': '营收3万元。'}], [{'id': 'a', 'text': '营收三万元'}])
        self.assertEqual(result['overall']['substitutions'], 1)
        self.assertGreater(result['overall']['cer'], 0)

    def test_numeric_punctuation_does_not_hide_decimal_percent_or_sign_errors(self):
        for reference, hypothesis in [('3.5万元', '35万元'), ('30%', '30'),
                                      ('-3万元', '3万元'), ('10:30', '1030')]:
            with self.subTest(reference=reference, hypothesis=hypothesis):
                result = self.score([{'id': 'a', 'text': reference}], [{'id': 'a', 'text': hypothesis}])
                self.assertGreater(result['overall']['errors'], 0)

    def test_overall_cer_is_character_weighted(self):
        result = self.score([{'id': 'a', 'text': '甲'}, {'id': 'b', 'text': '乙' * 9}],
                            [{'id': 'a', 'text': '丙'}, {'id': 'b', 'text': '乙' * 9}])
        self.assertEqual(result['overall']['cer'], 0.1)

    def test_missing_hypothesis_is_not_ignored(self):
        result = self.score([{'id': 'a', 'text': '甲乙'}, {'id': 'b', 'text': '丙丁'}],
                            [{'id': 'a', 'text': '甲乙'}])
        self.assertEqual(result['missing_sample_ids'], ['b'])
        self.assertEqual(result['overall']['deletions'], 2)
        self.assertEqual(result['overall']['cer'], 0.5)
        self.assertTrue(result['samples'][1]['missing_hypothesis'])

    def test_all_hypotheses_missing_is_full_deletion(self):
        result = self.score([{'id': 'a', 'text': '甲乙'}], [])
        self.assertEqual(result['overall']['deletions'], 2)
        self.assertEqual(result['missing_sample_ids'], ['a'])

    def test_extra_and_duplicate_ids_fail(self):
        for reference, hypothesis in [
            ([{'id': 'a', 'text': '甲'}], [{'id': 'a', 'text': '甲'}, {'id': 'b', 'text': '乙'}]),
            ([{'id': 'a', 'text': '甲'}, {'id': 'a', 'text': '乙'}], [{'id': 'a', 'text': '甲'}]),
            ([{'id': 'a', 'text': '甲'}], [{'id': 'a', 'text': '甲'}, {'id': 'a', 'text': '乙'}]),
        ]:
            with self.subTest(reference=reference, hypothesis=hypothesis), self.assertRaises(ValueError):
                self.score(reference, hypothesis)

    def test_empty_reference_insertion_has_no_fabricated_percentage(self):
        result = self.score([{'id': 'silence', 'text': ''}], [{'id': 'silence', 'text': '幻觉内容'}])
        self.assertIsNone(result['overall']['cer'])
        self.assertEqual(result['overall']['empty_reference_insertions'], 4)
        self.assertEqual(result['overall']['insertions'], 4)

    def test_empty_reference_insertions_remain_in_mixed_corpus_error_count(self):
        result = self.score([{'id': 'silence', 'text': ''}, {'id': 'speech', 'text': '甲'}],
                            [{'id': 'silence', 'text': '乙丙'}, {'id': 'speech', 'text': '甲'}])
        self.assertEqual(result['overall']['cer'], 2.0)
        self.assertEqual(result['overall']['empty_reference_insertions'], 2)

    def test_term_precision_recall_and_false_insertions(self):
        result = self.score([{'id': 'a', 'text': '星河科技', 'expected_terms': ['星河科技']},
                             {'id': 'b', 'text': '别的公司'}],
                            [{'id': 'a', 'text': '星和科技'}, {'id': 'b', 'text': '星河科技'}])
        terms = result['overall']['terms']
        self.assertEqual((terms['true_positives'], terms['false_positives'], terms['false_negatives']), (0, 1, 1))
        self.assertEqual((terms['precision'], terms['recall']), (0, 0))
        self.assertEqual(result['samples'][1]['terms']['false_insertions'], ['星河科技'])

    def test_expected_term_must_be_present_in_reference(self):
        with self.assertRaises(ValueError):
            self.score([{'id': 'a', 'text': '公司', 'expected_terms': ['未出现']}], [{'id': 'a', 'text': '公司'}])

    def test_critical_checks_are_explicitly_literal_not_semantic(self):
        checks = [{'id': 'revenue', 'kind': 'number', 'accepted_phrases': ['30万元']},
                  {'id': 'contract', 'kind': 'status', 'accepted_phrases': ['已经签约']}]
        result = self.score([{'id': 'a', 'text': '营收30万元，已经签约。', 'critical_checks': checks}],
                            [{'id': 'a', 'text': '营收3万元，并非已经签约。'}])
        detail = result['samples'][0]['critical_checks']
        self.assertFalse(detail[0]['matched'])
        self.assertTrue(detail[1]['matched'])  # Demonstrates why it is not a semantic metric.
        self.assertIsNone(result['overall']['critical_checks']['semantic_accuracy'])

    def test_invalid_critical_checks_fail(self):
        for checks in ([{'id': 'a', 'kind': 'number', 'accepted_phrases': []}],
                       [{'id': 'a', 'kind': 'number', 'accepted_phrases': ['30万元']}],
                       [{'id': 'a', 'kind': 'number', 'accepted_phrases': ['3万元']}] * 2):
            with self.subTest(checks=checks), self.assertRaises(ValueError):
                self.score([{'id': 'a', 'text': '3万元', 'critical_checks': checks}], [{'id': 'a', 'text': '3万元'}])

    def test_audio_benchmark_eligibility_requires_all_declared_evidence(self):
        audio = self.root / 'clip.wav'
        audio.write_bytes(b'test fixture, not real meeting audio')
        base = {'id': 'a', 'text': '甲', 'audio': {'path': 'clip.wav', 'sha256': evaluation.file_hash(audio)},
                'annotation_status': 'human_verified', 'reviewer': 'test reviewer'}
        result = self.score([base], [{'id': 'a', 'text': '甲'}])
        self.assertTrue(result['samples'][0]['eligible_for_audio_benchmark'])
        for replacement in ({'annotation_status': 'synthetic'}, {'annotation_status': 'unverified'},
                            {'reviewer': ''}, {'audio': {'path': 'clip.wav', 'sha256': '0' * 64}},
                            {'audio': {'path': 'missing.wav', 'sha256': '0' * 64}}):
            with self.subTest(replacement=replacement):
                result = self.score([{**base, **replacement}], [{'id': 'a', 'text': '甲'}])
                self.assertFalse(result['all_samples_audio_benchmark_eligible'])
                self.assertEqual(result['eligible_audio_only']['sample_count'], 0)

    def test_label_provenance_hashes_and_model_metadata_are_recorded(self):
        result = self.score([{'id': 'a', 'text': '甲', 'annotation_status': 'synthetic'}],
                            [{'id': 'a', 'text': '甲'}], model_metadata={'engine': 'test', 'model': 'fixture'})
        self.assertEqual(result['reference']['annotation_status_counts']['synthetic'], 1)
        self.assertEqual(result['model_metadata']['model'], 'fixture')
        self.assertEqual(result['reference']['sha256'], evaluation.file_hash(self.root / 'reference.json'))
        self.assertEqual(result['hypothesis']['sha256'], evaluation.file_hash(self.root / 'hypothesis.json'))

    def test_length_guard_rejects_reference_and_hypothesis(self):
        for ref, hyp in [('甲' * 4001, '甲'), ('甲', '乙' * 4001)]:
            with self.subTest(reference_length=len(ref), hypothesis_length=len(hyp)), self.assertRaises(ValueError):
                self.score([{'id': 'a', 'text': ref}], [{'id': 'a', 'text': hyp}])

    def test_init_produces_only_unverified_draft_and_preserves_existing_files(self):
        audio = self.root / 'clip.wav'
        audio.write_bytes(b'fixture')
        output = self.root / 'dataset.json'
        result = evaluation.initialize([audio], output)
        self.assertEqual(result['dataset_status'], 'draft_requires_annotation')
        self.assertEqual(result['samples'][0]['annotation_status'], 'unverified')
        self.assertEqual(result['samples'][0]['text'], '')
        self.assertEqual(result['samples'][0]['reviewer'], '')
        before = output.read_bytes()
        with self.assertRaises(ValueError):
            evaluation.initialize([audio], output)
        self.assertEqual(output.read_bytes(), before)

    def test_cli_outputs_report_and_cannot_overwrite_reference(self):
        ref = self.write('ref.json', [{'id': 'a', 'text': '甲'}])
        hyp = self.write('hyp.json', [{'id': 'a', 'text': '甲'}])
        output = self.root / 'report.json'
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(evaluation.main(['score', '--reference', str(ref), '--hypothesis', str(hyp), '--output', str(output)]), 0)
        self.assertTrue(output.is_file())
        before = ref.read_bytes()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(evaluation.main(['score', '--reference', str(ref), '--hypothesis', str(hyp), '--output', str(ref)]), 1)
        self.assertEqual(ref.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
