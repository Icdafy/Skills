"""A runtime check must honor the requested engines and render dependencies."""
from __future__ import annotations

import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
import bootstrap_runtime as runtime


class RequestedEngineTests(unittest.TestCase):
    def probe(self, missing, engines):
        modules = {name: name not in missing for name in
                   ('imageio_ffmpeg', 'docx', 'pypdf', 'torch', 'funasr',
                    'modelscope', 'torchaudio', 'qwen_asr')}
        proc = SimpleNamespace(returncode=0, stdout=json.dumps(modules), stderr='')
        with patch.object(runtime.subprocess, 'run', return_value=proc):
            return runtime.probe(Path(sys.executable), engines)

    def test_all_requires_both_engines(self):
        result = self.probe({'qwen_asr'}, ['funasr', 'qwen'])
        self.assertFalse(result['ready'])
        self.assertEqual(result['missing_engines'], ['qwen'])
        self.assertIn('qwen_asr', result['missing_modules'])

    def test_single_engine_does_not_require_other_engine(self):
        self.assertTrue(self.probe({'qwen_asr'}, ['funasr'])['ready'])
        self.assertTrue(self.probe({'funasr', 'modelscope', 'torchaudio'}, ['qwen'])['ready'])

    def test_funasr_dependencies_and_pdf_are_required(self):
        result = self.probe({'modelscope', 'torchaudio', 'pypdf'}, ['funasr'])
        self.assertFalse(result['ready'])
        self.assertCountEqual(result['missing_modules'], ['modelscope', 'torchaudio', 'pypdf'])

    def test_module_discovery_does_not_claim_inference(self):
        result = self.probe(set(), ['funasr', 'qwen'])
        self.assertTrue(result['ready'])
        self.assertFalse(result['inference_checked'])
        self.assertFalse(result['model_cache_checked'])
        self.assertEqual(result['probe_level'], 'module_discovery')


if __name__ == '__main__':
    unittest.main()
