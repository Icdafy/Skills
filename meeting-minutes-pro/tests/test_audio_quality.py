"""Signal/channel and chunk-boundary checks without ASR model dependencies."""
from __future__ import annotations

from array import array
import contextlib
import io
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave

SCRIPTS = Path(__file__).parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import audio_quality as quality
import transcribe


def write_pcm(path: Path, samples: list[tuple[int, ...]], rate: int = 1000) -> Path:
    values = array('h', (value for frame in samples for value in frame))
    if sys.byteorder != 'little':
        values.byteswap()
    with wave.open(str(path), 'wb') as wav:
        wav.setparams((len(samples[0]), 2, rate, 0, 'NONE', 'not compressed'))
        wav.writeframes(values.tobytes())
    return path


class AudioQualityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_per_channel_energy_and_silence_are_not_downmixed(self):
        source = write_pcm(self.root / 'stereo.wav', [(10000, 0)] * 100 + [(0, 0)] * 100)
        report = quality.inspect_wav(source)
        self.assertEqual(report['channel_count'], 2)
        self.assertEqual(report['frames_measured'], 200)
        left, right = report['channels']
        self.assertAlmostEqual(left['rms'], (10000 / 32768) / math.sqrt(2), places=7)
        self.assertEqual(left['silent_window_fraction'], 0.5)
        self.assertEqual(right['zero_fraction'], 1)
        self.assertIsNone(right['rms_dbfs'])
        json.dumps(report, allow_nan=False)

    def test_full_scale_is_reported_as_possible_clipping_only(self):
        source = write_pcm(self.root / 'clipped.wav', [(-32768,), (32767,)] * 100)
        report = quality.inspect_wav(source)
        self.assertEqual(report['channels'][0]['near_full_scale_fraction'], 1)
        flags = quality.quality_flags(report, report, 'mix', '测试')
        self.assertIn('possible_clipping', [flag['code'] for flag in flags])
        self.assertNotIn('accuracy', report)

    def test_non_silent_empty_text_is_review_flag_not_speech_claim(self):
        source = write_pcm(self.root / 'signal.wav', [(5000,)] * 200)
        report = quality.inspect_wav(source)
        flags = quality.quality_flags(report, report, 'mix', '')
        self.assertEqual(flags[0]['code'], 'non_silent_audio_without_text')
        self.assertIn('may be noise', flags[0]['message'])

    def test_digital_silence_with_text_flagged_but_normal_silence_allowed(self):
        source = write_pcm(self.root / 'silence.wav', [(0,)] * 200)
        report = quality.inspect_wav(source)
        no_text = quality.quality_flags(report, report, 'mix', '')
        with_text = quality.quality_flags(report, report, 'mix', '凭空文字')
        self.assertNotIn('text_on_digital_silence', [item['code'] for item in no_text])
        self.assertIn('text_on_digital_silence', [item['code'] for item in with_text])

    def test_energy_drop_is_reported_without_changing_channel(self):
        source = quality.inspect_wav(write_pcm(self.root / 'stereo.wav', [(10000, -10000)] * 200))
        mixed = quality.inspect_wav(write_pcm(self.root / 'mix.wav', [(0,)] * 200))
        flags = quality.quality_flags(source, mixed, 'mix', '')
        self.assertIn('downmix_energy_drop', [flag['code'] for flag in flags])
        self.assertNotIn('downmix_energy_drop', [flag['code'] for flag in quality.quality_flags(source, mixed, 'left', '')])

    def test_rounded_zero_fraction_is_not_exact_silence(self):
        report = {'status': 'measured', 'frames_measured': 10000000,
                  'channels': [{'channel_index': 0, 'rms': 0.000001, 'peak': 0.00003052,
                                'near_full_scale_fraction': 0, 'silent_window_fraction': 1,
                                'zero_fraction': 1.0}]}
        flags = quality.quality_flags(report, report, 'mix', '微弱声音')
        self.assertNotIn('text_on_digital_silence', [flag['code'] for flag in flags])

    def test_unselected_channel_clipping_does_not_flag_selected_audio(self):
        source = quality.inspect_wav(write_pcm(self.root / 'stereo.wav', [(1000, 32767)] * 200))
        selected = quality.inspect_wav(write_pcm(self.root / 'left.wav', [(1000,)] * 200))
        flags = quality.quality_flags(source, selected, 'left', '有效文字')
        self.assertNotIn('possible_clipping', [flag['code'] for flag in flags])

    def test_pcm_stream_reads_to_eof_instead_of_declared_wav_length(self):
        path = write_pcm(self.root / 'stream.wav', [(1000,)] * 200)
        data = bytearray(path.read_bytes())
        # Simulate a pipe header with a placeholder data length.
        data[40:44] = (2).to_bytes(4, 'little')
        stream = io.BytesIO(data)
        with wave.open(quality._ReadOnlyPipe(stream), 'rb') as header:
            self.assertEqual(header.getnframes(), 1)
            report = quality.inspect_pcm16(quality._StreamingPCM(stream, header))
        self.assertEqual(report['frames_measured'], 200)

    def test_boundary_windows_clamped_and_repeated_text_preserved(self):
        result = transcribe.TranscribeResult('确认确认\n确认确认', 'Chinese', chunk_boundaries=[1, 8])
        outputs = transcribe.write_outputs(self.root, self.root / 'source.wav', result,
                                          'funasr', 'cpu', 'test', 10, '', False)
        report = json.loads(Path(outputs['json']).read_text(encoding='utf-8'))
        self.assertEqual(report['text'], '确认确认\n确认确认')
        self.assertEqual([(item['start'], item['end']) for item in report['boundary_review_windows']],
                         [(0, 4), (5, 10)])
        self.assertTrue(all(item['time_basis'] == 'processed_audio' for item in report['boundary_review_windows']))

    def test_single_pass_has_no_artificial_boundaries(self):
        self.assertEqual(quality.boundary_windows([], 100), [])

    def test_channel_filter_precedes_explicit_enhancement(self):
        with patch.object(transcribe, 'ffmpeg_exe', return_value='ffmpeg'), \
             patch.object(transcribe.subprocess, 'run') as run:
            run.return_value.returncode = 0
            transcribe.prepare_wav(Path('source.wav'), Path('out.wav'), enhance=True, channel='right')
        cmd = run.call_args.args[0]
        self.assertTrue(cmd[cmd.index('-af') + 1].startswith('pan=mono|c0=c1,afftdn='))
        self.assertEqual(cmd[cmd.index('-map') + 1], '0:a:0')

    def test_default_preparation_keeps_legacy_unenhanced_mix(self):
        with patch.object(transcribe, 'ffmpeg_exe', return_value='ffmpeg'), \
             patch.object(transcribe.subprocess, 'run') as run:
            run.return_value.returncode = 0
            transcribe.prepare_wav(Path('source.wav'), Path('out.wav'))
        cmd = run.call_args.args[0]
        self.assertNotIn('-af', cmd)
        self.assertEqual(cmd[cmd.index('-ac') + 1], '1')

    def test_invalid_channel_rejected(self):
        with self.assertRaises(ValueError):
            transcribe.prepare_wav(Path('source.wav'), Path('out.wav'), channel='third')


class FFmpegSignalSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.ffmpeg = transcribe.ffmpeg_exe()
        except (ImportError, RuntimeError):
            raise unittest.SkipTest('FFmpeg runtime not installed')

    def test_stream_probe_and_channel_selection(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = write_pcm(root / 'stereo.wav', [(12000, -12000)] * 1600, rate=16000)
            raw = quality.inspect_media(source, self.ffmpeg)
            self.assertEqual(raw['channel_count'], 2)
            self.assertEqual(raw['frames_measured'], 1600)
            results = {}
            for channel in ('mix', 'left', 'right'):
                path = root / (channel + '.wav')
                transcribe.prepare_wav(source, path, channel=channel)
                results[channel] = quality.inspect_wav(path)
            self.assertEqual(results['mix']['channels'][0]['zero_fraction'], 1)
            self.assertAlmostEqual(results['left']['channels'][0]['rms'], 12000 / 32768, places=6)
            self.assertAlmostEqual(results['right']['channels'][0]['rms'], 12000 / 32768, places=6)

    def test_main_reports_channels_and_does_not_load_model(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = write_pcm(root / 'stereo.wav', [(9000, 0)] * 1600, rate=16000)
            argv = ['transcribe', '--input', str(source), '--output-dir', str(root / 'outputs'),
                    '--channel', 'left', '--engine', 'funasr', '--device', 'cpu']
            with patch.object(sys, 'argv', argv), \
                 patch.object(transcribe, 'run_funasr', return_value=transcribe.TranscribeResult('', 'Chinese')), \
                 patch.object(transcribe, 'funasr_device', return_value='cpu'), \
                 contextlib.redirect_stdout(io.StringIO()) as output, contextlib.redirect_stderr(io.StringIO()):
                result = transcribe.main()
            self.assertEqual(result, 0)
            report = json.loads(output.getvalue())
            self.assertEqual(report['audio_diagnostics']['source']['channel_count'], 2)
            self.assertEqual(report['audio_diagnostics']['channel_selection'], 'left')
            self.assertEqual(report['recognition_config']['channel'], 'left')
            self.assertIn('non_silent_audio_without_text', [item['code'] for item in report['quality_flags']])

    def test_mono_right_selection_fails_before_model_load(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = write_pcm(root / 'mono.wav', [(9000,)] * 1600, rate=16000)
            argv = ['transcribe', '--input', str(source), '--output-dir', str(root / 'outputs'),
                    '--channel', 'right']
            with patch.object(sys, 'argv', argv), patch.object(transcribe, 'run_funasr') as model, \
                 contextlib.redirect_stdout(io.StringIO()) as output, contextlib.redirect_stderr(io.StringIO()):
                result = transcribe.main()
            self.assertEqual(result, 1)
            self.assertIn('requires at least two', json.loads(output.getvalue())['error'])
            model.assert_not_called()

    def test_right_channel_fails_closed_when_source_probe_is_unavailable(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = write_pcm(root / 'mono.wav', [(9000,)] * 1600, rate=16000)
            argv = ['transcribe', '--input', str(source), '--output-dir', str(root / 'outputs'),
                    '--channel', 'right']
            with patch.object(sys, 'argv', argv), patch.object(transcribe, 'run_funasr') as model, \
                 patch.object(quality, 'inspect_media', side_effect=RuntimeError('probe unavailable')), \
                 patch.object(transcribe, 'prepare_wav') as prepare, \
                 contextlib.redirect_stdout(io.StringIO()) as output, contextlib.redirect_stderr(io.StringIO()):
                result = transcribe.main()
            self.assertEqual(result, 1)
            self.assertIn('source probing must succeed', json.loads(output.getvalue())['error'])
            prepare.assert_not_called()
            model.assert_not_called()

    def test_stream_probe_preserves_multichannel_count(self):
        with tempfile.TemporaryDirectory() as folder:
            source = write_pcm(Path(folder) / 'three.wav', [(1000, 2000, 3000)] * 1600, rate=16000)
            report = quality.inspect_media(source, self.ffmpeg)
            self.assertEqual(report['channel_count'], 3)
            self.assertEqual(len(report['channels']), 3)
            self.assertAlmostEqual(report['channels'][2]['rms'], 3000 / 32768, places=6)


if __name__ == '__main__':
    unittest.main()
