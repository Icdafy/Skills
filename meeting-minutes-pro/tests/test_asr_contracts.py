"""ASR adapter/evidence regressions without downloading or loading models."""
from __future__ import annotations

from argparse import Namespace
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import refine_transcript as refine
import run_state
import transcribe


def args(**overrides):
    values = dict(device='cpu', model=None, clip_duration=None, chunk_seconds=None,
                  timestamps=False, diarize=False, language='auto', no_resume=False,
                  context='', offline=False, speakers=None)
    values.update(overrides)
    return Namespace(**values)


class FunASRContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.wav = self.root / 'audio.wav'
        self.wav.write_bytes(b'audio content')

    def test_default_retains_timestamp_evidence_without_speaker_model(self):
        captured = {}

        class Model:
            def __init__(self, **kwargs):
                captured['model'] = kwargs

            def generate(self, **kwargs):
                captured['generate'] = kwargs
                return [{'text': '收入五百万元。', 'sentence_info': [
                    {'text': '收入五百万元。', 'start': 100, 'end': 3000}]}]

        with patch.dict(sys.modules, {'funasr': types.SimpleNamespace(AutoModel=Model)}), \
             patch.object(transcribe, 'funasr_device', return_value='cpu'):
            result = transcribe.run_funasr(args(), self.wav, 4, self.root / 'chunks')
        self.assertNotIn('spk_model', captured['model'])
        self.assertTrue(captured['generate']['sentence_timestamp'])
        self.assertEqual(len(result.stamps), 1)
        self.assertEqual(result.stamps[0].start, 0.1)
        self.assertEqual(result.stamps[0].end, 3)
        self.assertEqual(result.text, ''.join(s.text for s in result.stamps))
        self.assertFalse(result.speakers)

    def test_diarize_still_loads_cam_and_keeps_global_labels(self):
        captured = {}

        class Model:
            def __init__(self, **kwargs):
                captured['model'] = kwargs

            def generate(self, **kwargs):
                captured['generate'] = kwargs
                return [{'text': '现在开始。', 'sentence_info': [
                    {'text': '现在开始。', 'start': 0, 'end': 1500, 'spk': 1}]}]

        with patch.dict(sys.modules, {'funasr': types.SimpleNamespace(AutoModel=Model)}), \
             patch.object(transcribe, 'funasr_device', return_value='cpu'), \
             patch.object(transcribe, 'plan_chunks') as planner:
            result = transcribe.run_funasr(args(diarize=True, speakers=3), self.wav, 4000,
                                           self.root / 'chunks')
        self.assertIn('spk_model', captured['model'])
        self.assertEqual(captured['generate']['preset_spk_num'], 3)
        self.assertEqual(result.stamps[0].speaker, '说话人2')
        self.assertTrue(result.speakers)
        planner.assert_not_called()

    def test_interrupted_forced_run_resumes_with_normal_flag_and_global_times(self):
        calls = []
        fail_once = [True]

        class Model:
            def __init__(self, **kwargs):
                pass

            def generate(self, **kwargs):
                chunk = Path(kwargs['input']).stem
                calls.append(chunk)
                if chunk == 'chunk_0002' and fail_once[0]:
                    fail_once[0] = False
                    raise RuntimeError('interrupted')
                return [{'text': chunk, 'sentence_info': [
                    {'text': chunk, 'start': 100, 'end': 2000}]}]

        with patch.dict(sys.modules, {'funasr': types.SimpleNamespace(AutoModel=Model)}), \
             patch.object(transcribe, 'funasr_device', return_value='cpu'), \
             patch.object(transcribe, 'detect_silences', return_value=[]), \
             patch.object(transcribe, 'plan_chunks', return_value=[(0, 900), (900, 1900)]), \
             patch.object(transcribe, 'prepare_wav'):
            with self.assertRaisesRegex(RuntimeError, 'interrupted'):
                transcribe.run_funasr(args(no_resume=True), self.wav, 1900, self.root / 'chunks')
            result = transcribe.run_funasr(args(), self.wav, 1900, self.root / 'chunks')
        self.assertEqual(calls, ['chunk_0001', 'chunk_0002', 'chunk_0002'])
        self.assertEqual(result.text, 'chunk_0001\nchunk_0002')
        self.assertEqual([s.start for s in result.stamps], [0.1, 900.1])
        self.assertEqual(result.inferred_audio_seconds, 1000)


class CheckpointContractTests(unittest.TestCase):
    def test_malformed_stamp_payload_is_recomputed(self):
        invalid = [None, {}, [None], [{'text': 'x', 'start': 0}],
                   [{'text': 'x', 'start': '0', 'end': 1}],
                   [{'text': 'x', 'start': 0, 'end': float('nan')}],
                   [{'text': 'x', 'start': 2, 'end': 1}],
                   [{'text': 'x', 'start': 0, 'end': 1, 'speaker': 3}],
                   [{'text': 'x', 'start': 0, 'end': 1, 'unexpected': True}]]
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'checkpoint.json'
            for stamps in invalid:
                with self.subTest(stamps=stamps):
                    run_state.atomic_json(target, {'identity': 'id', 'start': 0, 'end': 3,
                                                   'text': 'x', 'stamps': stamps})
                    self.assertIsNone(run_state.read_checkpoint(target, 'id', 0, 3))

    def test_text_only_review_cache_and_silent_transcription_remain_valid(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'checkpoint.json'
            run_state.atomic_json(target, {'identity': 'id', 'start': 0, 'end': 3, 'text': 'x'})
            self.assertIsNotNone(run_state.read_checkpoint(target, 'id', 0, 3))
            self.assertIsNone(run_state.read_checkpoint(target, 'id', 0, 3, require_stamps=True))
            run_state.atomic_json(target, {'identity': 'id', 'start': 0, 'end': 3,
                                           'text': '', 'stamps': []})
            self.assertIsNotNone(run_state.read_checkpoint(target, 'id', 0, 3, require_stamps=True))


class IndependentReviewTests(unittest.TestCase):
    def test_nonnumeric_primary_gap_is_not_consistent(self):
        for left, right in [('', '公司已经完成样机测试。'), ('已完成样机测试。', '')]:
            conflicts = refine.compare_texts(left, right, [])
            self.assertIn('文本缺失', [x['category'] for x in conflicts])

    def test_substantial_nonnumeric_divergence_is_flagged_for_listening(self):
        conflicts = refine.compare_texts('公司已经完成样机测试。', '下午讨论团队招聘安排。', [])
        self.assertIn('文本差异', [x['category'] for x in conflicts])

    def test_identical_silence_has_no_text_conflict(self):
        self.assertEqual(refine.compare_texts('', '', []), [])

    def test_negation_and_commitment_are_reviewed_without_numbers(self):
        self.assertIn('negation', refine.sentence_risks('目前未中标该项目。', []))
        self.assertIn('commitment', refine.sentence_risks('承诺完成设备交付。', []))


class TimingTests(unittest.TestCase):
    def test_sample_setup_is_paid_once_in_full_run_estimate(self):
        sample = transcribe.TranscribeResult('示例', 'Chinese', setup_seconds=120,
                                             inference_seconds=6, inferred_audio_seconds=60)
        timings = transcribe.timing_summary(sample, 7200)
        self.assertEqual(timings['inference_realtime_factor'], 0.1)
        self.assertEqual(timings['estimated_full_run_minutes'], 14)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'audio.sample.json').write_text(
                json.dumps({**timings, 'realtime_factor': 2.1}), encoding='utf-8')
            output = io.StringIO()
            with contextlib.redirect_stderr(output):
                transcribe.emit_eta(root, Path('audio.wav'), 7200)
        self.assertEqual(json.loads(output.getvalue())['progress']['estimated_minutes'], 14)

    def test_cached_audio_does_not_make_inference_rate_look_faster(self):
        result = transcribe.TranscribeResult('cached plus new', 'Chinese', setup_seconds=10,
                                             inference_seconds=3, inferred_audio_seconds=30)
        self.assertEqual(transcribe.timing_summary(result)['inference_realtime_factor'], 0.1)
        result.inferred_audio_seconds = 0
        result.inference_seconds = 0
        self.assertNotIn('inference_realtime_factor', transcribe.timing_summary(result, 7200))

    def test_corrupt_sample_timing_does_not_block_transcription(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for value in ('broken', float('nan'), -2):
                (root / 'audio.sample.json').write_text(
                    json.dumps({'inference_realtime_factor': value}), encoding='utf-8')
                output = io.StringIO()
                with contextlib.redirect_stderr(output):
                    transcribe.emit_eta(root, Path('audio.wav'), 7200)
                self.assertEqual(output.getvalue(), '')


if __name__ == '__main__':
    unittest.main()
