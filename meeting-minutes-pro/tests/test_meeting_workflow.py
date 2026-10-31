"""Behavioral checks for persistent jobs; no model downloads or invented review."""
import contextlib
import io
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
import meeting_workflow as workflow


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / '带 空格的材料.txt'
        self.source.write_text('项目已完成样机测试。', encoding='utf-8')
        self.jobdir = self.root / '会议 归档'

    def cli(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = workflow.main([*args, '--job-dir', str(self.jobdir)])
        return code, json.loads(out.getvalue())

    def init(self, audio=False, *extra):
        code, result = self.cli('init', '--input', str(self.source), '--source-kind',
                                'audio' if audio else 'transcript', *extra)
        self.assertEqual(code, 0, result)
        return workflow.load_job(self.jobdir)

    def test_text_job_prepares_ledger_without_asr_or_fabricating_minutes(self):
        self.init()
        code, result = self.cli('run')
        self.assertEqual(code, 0, result)
        self.assertEqual(result['status'], 'agent_action')
        self.assertEqual(result['action'], 'author_minutes')
        self.assertTrue(result['continuation_required'])
        self.assertFalse(result['user_input_required'])
        self.assertFalse(result['release_ready'])
        self.assertFalse((self.jobdir / '会议纪要.txt').exists())
        self.assertIn('待判定', (self.jobdir / 'coverage.txt').read_text(encoding='utf-8'))
        code, result = self.cli('run')
        self.assertEqual(code, 0, result)
        self.assertTrue(result['steps'][0]['cached'])

    def test_source_change_rejects_job_reuse(self):
        self.init()
        self.source.write_text('其他会议内容。', encoding='utf-8')
        code, result = self.cli('status')
        self.assertEqual(code, 1)
        self.assertFalse(result['release_ready'])

    def test_existing_job_is_not_overwritten(self):
        self.init()
        original = (self.jobdir / 'workflow.json').read_bytes()
        code, _ = self.cli('init', '--input', str(self.source))
        self.assertEqual(code, 1)
        self.assertEqual((self.jobdir / 'workflow.json').read_bytes(), original)

    def test_high_review_requires_whole_audio_and_time_located_primary(self):
        job = self.init(True, '--assurance', 'high', '--offline', '--context', '公司名 术语')
        primary, _, _ = workflow.command_for(job, 'transcribe')
        review, _, _ = workflow.command_for(job, 'refine')
        self.assertIn('--timestamps', primary)
        self.assertIn('--offline', primary)
        self.assertIn('--offline', review)
        self.assertIn('--all', review)
        self.assertIn('公司名 术语', primary)
        self.assertIn(str(self.source), primary)

    def test_qwen_cannot_claim_independent_self_review(self):
        job = self.init(True, '--engine', 'qwen')
        with self.assertRaisesRegex(ValueError, '独立'):
            workflow.command_for(job, 'refine')

    def test_human_ledger_not_overwritten_on_resume(self):
        self.init()
        self.assertEqual(self.cli('run')[0], 0)
        ledger = self.jobdir / 'coverage.txt'
        ledger.write_text('人工修改记录', encoding='utf-8')
        code, result = self.cli('run')
        self.assertEqual(code, 0, result)
        self.assertEqual(ledger.read_text(encoding='utf-8'), '人工修改记录')
        self.assertFalse(result['release_ready'])

    def test_changed_transcript_requires_new_ledger(self):
        self.init()
        self.assertEqual(self.cli('run')[0], 0)
        accepted = self.root / 'accepted.txt'
        accepted.write_text('项目已启动客户验证。', encoding='utf-8')
        self.assertEqual(self.cli('accept', '--transcript', str(accepted))[0], 0)
        code, result = self.cli('run', '--step', 'ledger')
        self.assertEqual(code, 1)
        self.assertIn('另存', result['error'])

    def test_all_waivers_and_subtitle_flow_to_both_check_stages(self):
        job = self.init(False, '--subtitle', '综合办公室')
        job['waivers']['allow_missing_number'] = ['1|N2|明确口误']
        draft = workflow.common_checks(job)
        final = workflow.common_checks(job, True)
        self.assertEqual(final[:len(draft)], draft)
        self.assertIn('1|N2|明确口误', final)
        self.assertIn('综合办公室', final)

    def test_missing_stage_inputs_are_not_marked_success(self):
        self.init()
        code, result = self.cli('run', '--step', 'release')
        self.assertEqual(code, 1)
        self.assertFalse(result['release_ready'])
        self.assertFalse(self.cli('status')[1]['release_ready'])

    def test_failed_process_is_recorded_and_can_retry(self):
        self.init()
        with patch.object(workflow.subprocess, 'run', side_effect=OSError('runtime unavailable')):
            self.assertEqual(self.cli('run')[0], 1)
        job = workflow.load_job(self.jobdir)
        self.assertEqual(job['steps']['ledger']['status'], 'failed')
        self.assertEqual(self.cli('run')[0], 0)

    def test_modified_output_is_no_longer_cached(self):
        self.init()
        self.assertEqual(self.cli('run')[0], 0)
        job = workflow.load_job(self.jobdir)
        self.assertTrue(workflow.current(job, 'ledger'))
        (self.jobdir / 'coverage.txt').write_text('changed', encoding='utf-8')
        self.assertFalse(workflow.current(job, 'ledger'))

    def test_invalid_diarization_is_rejected_before_job_creation(self):
        code, result = self.cli('init', '--input', str(self.source), '--engine', 'qwen', '--diarize')
        self.assertEqual(code, 1)
        self.assertFalse((self.jobdir / 'workflow.json').exists())

    def test_format_change_preserves_asr_cache_but_engine_change_invalidates_it(self):
        job = self.init(True)
        argv, inputs, _ = workflow.command_for(job, 'transcribe')
        base = workflow.signature(argv, inputs)
        real_hash = workflow.file_hash
        with patch.object(workflow, 'file_hash', side_effect=lambda p:
                          'modified' if p.name == 'quality_check.py' else real_hash(p)):
            self.assertEqual(base, workflow.signature(argv, inputs))
        with patch.object(workflow, 'file_hash', side_effect=lambda p:
                          'modified' if p.name == 'transcribe.py' else real_hash(p)):
            self.assertNotEqual(base, workflow.signature(argv, inputs))

    def test_status_can_read_progress_while_mutation_lock_is_held(self):
        job = self.init(True)
        job['steps']['transcribe'] = {'status': 'running'}
        workflow.save_job(self.jobdir, job)
        with workflow.job_lock(self.jobdir):
            code, result = self.cli('status')
        self.assertEqual(code, 0)
        self.assertEqual(result['steps']['transcribe'], 'running')
        self.assertFalse(result['release_ready'])

    def test_no_targeted_candidates_records_no_review_without_fabricated_report(self):
        job = self.init(True)
        raw = Path(job['artifacts']['raw_transcript'])
        raw.parent.mkdir(parents=True)
        raw.write_text('{}', encoding='utf-8')
        def no_candidates(argv, **kwargs):
            json.dump({'ok': True, 'clips': 0, 'note': '没有定向候选'}, kwargs['stdout'])
            return subprocess.CompletedProcess(argv, 0)
        with patch.object(workflow.subprocess, 'run', side_effect=no_candidates):
            code, result = self.cli('run', '--step', 'refine')
        self.assertEqual(code, 0, result)
        self.assertEqual(result['status'], 'not_performed')
        self.assertFalse(Path(job['artifacts']['refine_report']).exists())
        self.assertNotIn('--refine-report', workflow.common_checks(job))
        job = workflow.load_job(self.jobdir)
        self.assertTrue(workflow.current(job, 'refine'))

    def test_filename_prefers_project_and_keeps_all_document_paths_consistent(self):
        job = self.init(False, '--project-name', '星河项目', '--interviewee', '张三',
                        '--interview-date', '2026年11月1日 09:30')
        expected = '星河项目_会议纪要_2026-11-01_09-30'
        self.assertEqual(Path(job['artifacts']['minutes']).name, expected + '.txt')
        self.assertEqual(Path(job['artifacts']['docx']).name, expected + '.docx')
        self.assertEqual(Path(job['artifacts']['render_report']).name, expected + '.render.json')
        argv, _, _ = workflow.command_for(job, 'docx')
        self.assertIn(str(self.jobdir / (expected + '.docx')), argv)

    def test_interviewee_fallback_and_missing_time_do_not_invent_metadata(self):
        self.assertEqual(workflow.minutes_stem('', '张三', '2026/11/01'), '张三_会议纪要_2026-11-01')
        self.assertEqual(workflow.minutes_stem('', '张三', '2026年11月1日14:30'), '张三_会议纪要_2026-11-01_14-30')
        self.assertEqual(workflow.minutes_stem('', '张三'), '张三_会议纪要')
        self.assertEqual(workflow.minutes_stem(), '会议纪要')
        with self.assertRaises(ValueError):
            workflow.minutes_stem('项目', '', '2026-02-30')

    def test_filename_cannot_create_subdirectories_or_escape_job(self):
        job = self.init(False, '--project-name', '../项目/甲\\乙:测试?', '--interview-date', '2026-11-01')
        for key in ('minutes', 'docx', 'render_report'):
            self.assertEqual(Path(job['artifacts'][key]).parent, self.jobdir)
            self.assertNotRegex(Path(job['artifacts'][key]).name, r'[<>:"/\\|?*]')

    def test_dynamic_filename_collision_is_rejected(self):
        self.jobdir.mkdir()
        docx = self.jobdir / '星河项目_会议纪要_2026-11-01.docx'
        docx.write_bytes(b'existing user file')
        code, _ = self.cli('init', '--input', str(self.source), '--project-name', '星河项目',
                           '--interview-date', '2026-11-01')
        self.assertEqual(code, 1)
        self.assertEqual(docx.read_bytes(), b'existing user file')

    def test_accept_requests_agent_continuation_without_user_approval(self):
        self.init()
        code, result = self.cli('accept', '--transcript', str(self.source))
        self.assertEqual(code, 0, result)
        self.assertEqual(result['action'], 'author_minutes')
        self.assertTrue(result['continuation_required'])
        self.assertFalse(result['user_input_required'])

    def test_automatic_run_advances_through_document_then_review_then_release(self):
        job = self.init()
        Path(job['artifacts']['minutes']).write_text('完整纪要', encoding='utf-8')
        called = []
        def fake_step(root, data, step):
            called.append(step)
            if step == 'review-template' and not Path(data['artifacts']['review']).exists():
                workflow.atomic_json(Path(data['artifacts']['review']), {
                    'facts': [], 'findings': [], 'document_review': {'confirmed': False}})
            return {'step': step, 'status': 'completed'}
        with patch.object(workflow, 'run_step', side_effect=fake_step), \
                patch.object(workflow, 'archive_stale_form'), patch.object(workflow, 'current', return_value=False):
            first = workflow.run_automatic(self.jobdir, job)
            self.assertEqual(called, ['ledger', 'draft', 'docx', 'render', 'review-template'])
            self.assertEqual(first['action'], 'review_document')
            self.assertFalse(first['user_input_required'])
            self.assertFalse(first['release_ready'])
            workflow.atomic_json(Path(job['artifacts']['review']), {
                'facts': [], 'findings': [], 'document_review': {'confirmed': True}})
            second = workflow.run_automatic(self.jobdir, job)
            self.assertEqual(called[-1], 'release')
            self.assertTrue(second['release_ready'])

    def test_automatic_form_refresh_preserves_previous_work_and_does_not_pause(self):
        job = self.init()
        self.assertEqual(self.cli('run')[0], 0)
        old = (self.jobdir / 'coverage.txt').read_bytes()
        accepted = self.root / 'corrected.txt'
        accepted.write_text('项目已完成样机测试，并开始客户验证。', encoding='utf-8')
        self.assertEqual(self.cli('accept', '--transcript', str(accepted))[0], 0)
        code, result = self.cli('run')
        self.assertEqual(code, 0, result)
        self.assertFalse(result['user_input_required'])
        history = list((self.jobdir / 'history').glob('*coverage.txt'))
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].read_bytes(), old)

    def test_completed_run_does_not_rewrite_or_regress(self):
        job = self.init()
        with patch.object(workflow, 'current', return_value=True), patch.object(workflow, 'run_step') as execute:
            result = workflow.run_automatic(self.jobdir, job)
        execute.assert_not_called()
        self.assertTrue(result['release_ready'])
        self.assertFalse(result['continuation_required'])


if __name__ == '__main__':
    unittest.main()
