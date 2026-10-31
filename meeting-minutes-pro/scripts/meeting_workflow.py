#!/usr/bin/env python3
"""Persistent local audio-to-minutes orchestration; never invents human review.

init creates a job; run advances every available stage through release.
Semantic work returns an agent action, never a request for user approval.
The host agent continues authoring/review in the same task and invokes run again.
All subprocesses use argument arrays, the selected interpreter and local files.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from run_state import atomic_json, file_hash

SCRIPTS = Path(__file__).resolve().parent
STEPS = ('transcribe', 'refine', 'ledger', 'draft', 'docx', 'render',
         'review-template', 'release')
CODE_DEPENDENCIES = {
    'transcribe.py': ('transcribe.py', 'run_state.py'),
    'refine_transcript.py': ('refine_transcript.py', 'transcribe.py', 'run_state.py', 'fact_check.py', 'format_spec.py'),
    'audit_coverage.py': ('audit_coverage.py', 'fact_check.py', 'format_spec.py'),
    'create_minutes_docx.py': ('create_minutes_docx.py', 'quality_check.py', 'format_spec.py',
                              'docx_format_helpers.py', 'embed_fonts.py', 'font_preflight.py', 'local_fonts.py'),
    'render_docx.py': ('render_docx.py', 'format_spec.py', 'run_state.py'),
}


def now():
    return datetime.now(timezone.utc).isoformat()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def filename_component(value):
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', value.strip()).rstrip(' .')
    if re.fullmatch(r'(?i:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?', value):
        value = '_' + value
    return value


def interview_time_component(value):
    """Normalize only supplied date/time; never substitute today's date."""
    value = value.strip()
    if not value:
        return ''
    match = re.fullmatch(
        r'(\d{4})[-/.年](\d{1,2})[-/.月](\d{1,2})日?'
        r'(?:[ T_]*(\d{1,2})[:时-](\d{1,2})(?:[:分-](\d{1,2})秒?)?分?)?', value)
    if not match and re.fullmatch(r'\d{8}', value):
        return date(int(value[:4]), int(value[4:6]), int(value[6:])).isoformat()
    if match:
        year, month, day, hour, minute, second = match.groups()
        result = date(int(year), int(month), int(day)).isoformat()
        if hour is not None:
            timestamp = datetime(int(year), int(month), int(day), int(hour), int(minute), int(second or 0))
            result += timestamp.strftime('_%H-%M-%S' if second is not None else '_%H-%M')
        return result
    # Partial confirmed dates remain partial. Do not invent missing day/month.
    if value in ('今天', '昨天', '明天', '今日', '昨日', '明日'):
        raise ValueError('访谈时间请使用已确认的实际日期，不能把相对日期直接写入文件名。')
    return filename_component(value)


def minutes_stem(project_name='', interviewee='', interview_date=''):
    subject = filename_component(project_name) or filename_component(interviewee)
    timestamp = interview_time_component(interview_date)
    return '_'.join(part for part in (subject, '会议纪要', timestamp) if part)


@contextmanager
def job_lock(root):
    """OS-owned lock is automatically released if a process is interrupted."""
    root.mkdir(parents=True, exist_ok=True)
    with (root / '.workflow.lock').open('a+b') as stream:
        stream.seek(0, 2)
        if stream.tell() == 0:
            stream.write(b'0')
            stream.flush()
        stream.seek(0)
        if os.name == 'nt':
            import msvcrt
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise ValueError('任务正在运行，请等待已有进程结束。') from exc
        else:
            import fcntl
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise ValueError('任务正在运行，请等待已有进程结束。') from exc
        try:
            yield
        finally:
            if os.name == 'nt':
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)


def load_job(root):
    job = read_json(root / 'workflow.json')
    if job.get('schema_version') != 1:
        raise ValueError('不支持的 workflow.json 版本。')
    if str(root) != job['job_dir']:
        raise ValueError('任务目录已移动；请在原目录运行或为新位置建立任务。')
    source = Path(job['source'])
    if not source.is_file() or file_hash(source) != job['source_sha256']:
        raise ValueError('源文件缺失或内容已变化，请使用新任务目录。')
    return job


def save_job(root, job):
    job['updated_at'] = now()
    atomic_json(root / 'workflow.json', job)


def init_job(args):
    root = args.job_dir.expanduser().resolve()
    source = args.input.expanduser().resolve()
    if not source.is_file():
        raise ValueError(f'输入文件不存在：{source}')
    if args.speakers is not None and (args.speakers < 1 or not args.diarize):
        raise ValueError('--speakers 需要 --diarize 且人数须为正整数。')
    if args.diarize and args.engine != 'funasr':
        raise ValueError('--diarize 仅支持 FunASR。')
    if args.source_kind != 'audio' and args.assurance == 'high':
        raise ValueError('没有录音不能声明 high 录音保障。')
    python = Path(args.runtime_python).expanduser().resolve()
    if not python.is_file():
        raise ValueError(f'运行时 Python 不存在：{python}')
    stem = re.sub(r'[^\w.-]+', '_', source.stem, flags=re.UNICODE).strip('._') or 'transcript'
    raw = root / 'raw' / f'{stem}.json' if args.source_kind == 'audio' else source
    output_stem = minutes_stem(args.project_name, args.interviewee, args.interview_date)
    with job_lock(root):
        if (root / 'workflow.json').exists():
            raise ValueError('任务已存在；使用 run/status，不覆盖已有任务。')
        reserved = ('raw', 'evidence', 'coverage.txt', '会议纪要.txt', '会议纪要.docx', 'review.json',
                    output_stem + '.txt', output_stem + '.docx', output_stem + '.render.json', output_stem + '.pdf')
        if any((root / name).exists() for name in reserved):
            raise ValueError('任务目录已有材料，请选择独立的新目录，避免覆盖。')
        job = {
            'schema_version': 1, 'created_at': now(), 'job_dir': str(root),
            'source': str(source), 'source_sha256': file_hash(source),
            'source_kind': args.source_kind, 'runtime_python': str(python),
            'meeting': {'project_name': args.project_name, 'interviewee': args.interviewee,
                        'interview_date': args.interview_date, 'output_stem': output_stem},
            'interaction_policy': {'ask_once_then_complete': True, 'pause_for_user_review': False},
            'options': {name: getattr(args, name) for name in (
                'engine', 'assurance', 'offline', 'context', 'diarize', 'speakers',
                'mode', 'subtitle', 'language', 'device', 'model', 'aligner', 'review_model', 'timestamps')},
            'glossary': [str(p.expanduser().resolve()) for p in args.glossary],
            'waivers': {'allow_line': [], 'skip': [], 'allow': [], 'allow_missing_number': []},
            'artifacts': {
                'raw_transcript': str(raw), 'transcript': str(raw),
                'refine_report': str(root / 'evidence' / f'{stem}.refine.json'),
                'ledger': str(root / 'coverage.txt'), 'minutes': str(root / (output_stem + '.txt')),
                'docx': str(root / (output_stem + '.docx')),
                'render_report': str(root / (output_stem + '.render.json')),
                'review': str(root / 'review.json'), 'revisions': None,
            },
            'steps': {}, 'status': 'initialized', 'release_ready': False,
        }
        save_job(root, job)
    return {'ok': True, 'job_dir': str(root), 'next': 'run', 'release_ready': False}


def common_checks(job, final=False):
    a, o = job['artifacts'], job['options']
    argv = [a['minutes'], '--transcript', a['transcript'], '--ledger', a['ledger'],
            '--mode', o['mode'], '--source-kind', job['source_kind'],
            '--assurance', o['assurance']]
    if o['subtitle']:
        argv += ['--subtitle', o['subtitle']]
    for path in job['glossary']:
        argv += ['--glossary', path]
    for name, values in job['waivers'].items():
        if name not in ('allow_line', 'skip', 'allow', 'allow_missing_number') or not isinstance(values, list):
            raise ValueError('waivers 只允许已定义的数组字段。')
        for value in values:
            argv += ['--' + name.replace('_', '-'), str(value)]
    if job['source_kind'] == 'audio':
        argv += ['--source', job['source'], '--raw-transcript', a['raw_transcript']]
        if Path(a['refine_report']).is_file():
            argv += ['--refine-report', a['refine_report']]
        if a['revisions']:
            argv += ['--revisions', a['revisions']]
    if final:
        argv += ['--docx', a['docx'], '--render-report', a['render_report']]
    return argv


def command_for(job, step):
    """Return argv, required inputs and produced artifacts (no execution)."""
    a, o = job['artifacts'], job['options']
    root = Path(job['job_dir'])
    base = [job['runtime_python']]
    if step == 'transcribe':
        if job['source_kind'] != 'audio':
            raise ValueError('文本材料不运行 ASR。')
        argv = ['--input', job['source'], '--output-dir', str(root / 'raw'),
                '--engine', o['engine'], '--context', o['context'],
                '--language', o['language'], '--device', o['device']]
        for option in ('model', 'aligner'):
            if o.get(option):
                argv += ['--' + option, o[option]]
        if o['engine'] == 'funasr' or o.get('timestamps'):
            argv += ['--timestamps']
        if o['diarize']:
            argv += ['--diarize']
        if o['speakers']:
            argv += ['--speakers', str(o['speakers'])]
        if o['offline']:
            argv += ['--offline']
        outputs = [a['raw_transcript'], str(Path(a['raw_transcript']).with_suffix('.txt')),
                   str(Path(a['raw_transcript']).with_suffix('.md'))]
        return base + [str(SCRIPTS / 'transcribe.py')] + argv, [job['source']], outputs
    if step == 'refine':
        if job['source_kind'] != 'audio' or o['engine'] != 'funasr':
            raise ValueError('自动独立复核仅支持 FunASR→Qwen；Qwen 主稿需另行安排适用独立引擎，不能用同族重跑冒充双引擎。')
        argv = ['--transcript', a['raw_transcript'], '--source', job['source'],
                '--output-dir', str(root / 'evidence'), '--context', o['context'],
                '--language', o['language'], '--device', o['device']]
        if o['assurance'] == 'high':
            argv += ['--all']
        if o.get('review_model'):
            argv += ['--model', o['review_model']]
        if o['offline']:
            argv += ['--offline']
        for path in job['glossary']:
            argv += ['--glossary', path]
        return base + [str(SCRIPTS / 'refine_transcript.py')] + argv, [job['source'], a['raw_transcript'], *job['glossary']], [a['refine_report']]
    if step == 'ledger':
        return base + [str(SCRIPTS / 'audit_coverage.py'), '--transcript', a['transcript'], '--make-template', a['ledger']], [a['transcript']], [a['ledger']]
    if step in ('draft', 'review-template', 'release'):
        final = step != 'draft'
        summary = str(root / ('checks-summary.json' if step == 'release' else f'{step}-checks.json'))
        argv = common_checks(job, final) + ['--summary', summary]
        inputs = [a['minutes'], a['transcript'], a['ledger'], *job['glossary']]
        if Path(a['transcript']).suffix.lower() == '.json':
            inputs += [str(Path(a['transcript']).with_suffix('.txt'))]
        if job['source_kind'] == 'audio':
            inputs += [job['source'], a['raw_transcript']]
            if Path(a['refine_report']).is_file():
                inputs += [a['refine_report']]
            if a['revisions']:
                inputs += [a['revisions']]
        outputs = [summary]
        if final:
            inputs += [a['docx'], a['render_report']]
        if step == 'review-template':
            argv += ['--make-review', a['review']]
            outputs += [a['review']]
        elif step == 'release':
            argv += ['--stage', 'release', '--review', a['review']]
            inputs += [a['review']]
        return base + [str(SCRIPTS / 'check_all.py')] + argv, inputs, outputs
    if step == 'docx':
        argv = ['--input', a['minutes'], '--output', a['docx'], '--mode', o['mode']]
        if o['subtitle']:
            argv += ['--subtitle', o['subtitle']]
        for line in job['waivers']['allow_line']:
            argv += ['--allow-line', str(line)]
        return base + [str(SCRIPTS / 'create_minutes_docx.py')] + argv, [a['minutes']], [a['docx']]
    if step == 'render':
        return base + [str(SCRIPTS / 'render_docx.py'), '--input', a['docx'], '--report', a['render_report']], [a['docx']], [a['render_report']]
    raise ValueError(f'未知阶段：{step}')


def signature(argv, inputs):
    missing = [p for p in inputs if not Path(p).is_file()]
    if missing:
        raise ValueError('缺少阶段输入：' + '；'.join(missing))
    # A wording/format validator update must not discard hours of valid ASR.
    # check_all deliberately binds every validator; retain its stronger contract.
    names = CODE_DEPENDENCIES.get(Path(argv[1]).name)
    scripts = [SCRIPTS / name for name in names] if names else sorted(SCRIPTS.glob('*.py'))
    return digest({'argv': argv, 'inputs': {p: file_hash(Path(p)) for p in inputs},
                   'scripts': {p.name: file_hash(p) for p in scripts}})


def current(job, step):
    record = job['steps'].get(step, {})
    if record.get('status') != 'completed':
        return False
    try:
        argv, inputs, _ = command_for(job, step)
        if record.get('signature') != signature(argv, inputs):
            return False
        return bool(record.get('outputs')) and all(
            Path(p).is_file() and file_hash(Path(p)) == sha
            for p, sha in record['outputs'].items())
    except (ValueError, OSError):
        return False


def run_step(root, job, step):
    argv, inputs, outputs = command_for(job, step)
    sig = signature(argv, inputs)
    if current(job, step):
        return {'step': step, 'cached': True, 'status': job['steps'][step].get('result', 'completed')}
    # The ledger/review template becomes human-authored after generation. Never overwrite it.
    if step in ('ledger', 'review-template') and Path(outputs[-1]).exists():
        old = job['steps'].get(step, {})
        if old.get('signature') == sig:
            return {'step': step, 'status': 'needs_review', 'preserved': outputs[-1]}
        raise ValueError(f'{step} 输入已变化或存在旧清单；请先另存现有清单，再重新生成并核对。')
    if step == 'transcribe' and any(Path(p).exists() for p in outputs):
        raise ValueError('原始转录已存在且与阶段记录不一致；请使用新任务目录，避免覆盖证据。')
    if step == 'docx' and not current(job, 'draft'):
        raise ValueError('请先对当前版本运行 --step draft 并通过机械检查。')
    if step == 'review-template' and not current(job, 'render'):
        raise ValueError('请先对当前 DOCX 运行 --step render。')
    if step == 'release' and not current(job, 'render'):
        raise ValueError('DOCX 或渲染输入已变化；请重新渲染并核对。')
    record = {'status': 'running', 'started_at': now(), 'signature': sig, 'argv': argv}
    job['steps'][step] = record
    job.update(status=f'running:{step}', release_ready=False)
    save_job(root, job)
    log_dir = root / 'logs'
    log_dir.mkdir(exist_ok=True)
    log = log_dir / (step + '-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f') + '.log')
    try:
        with log.open('w', encoding='utf-8') as stream:
            proc = subprocess.run(argv, cwd=root, stdout=stream, stderr=subprocess.STDOUT,
                                  env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}, check=False)
        if proc.returncode != 0:
            raise ValueError(f'{step} 失败，退出码 {proc.returncode}；日志：{log}')
        result = 'completed'
        if any(not Path(p).is_file() for p in outputs):
            # Targeted review legitimately exits before loading a model when
            # there are no candidate clips. Preserve that explicit result;
            # later audio_evidence will require a single-engine disclosure.
            try:
                response = json.loads(log.read_text(encoding='utf-8'))
            except ValueError:
                response = {}
            if (step == 'refine' and job['options']['assurance'] == 'standard'
                    and response.get('ok') is True and response.get('clips') == 0):
                marker = root / 'evidence' / 'refine-not-performed.json'
                atomic_json(marker, {'performed': False, 'covered_seconds': 0,
                                     'reason': response.get('note', 'no candidate clips'),
                                     'signature': sig})
                outputs = [str(marker)]
                result = 'not_performed'
            else:
                raise ValueError(f'{step} 退出成功但产物缺失；日志：{log}')
        if step in ('draft', 'review-template', 'release'):
            summary = read_json(outputs[0])
            if summary.get('checks_passed') is not True:
                raise ValueError(f'{step} 未通过机械或证据检查；请查看 {outputs[0]}')
            result = summary['status']
            if step == 'release' and summary.get('release_ready') is not True:
                raise ValueError('正式验收仍未通过，不可标记 release_ready。')
        record.update(status='completed', finished_at=now(), result=result,
                      outputs={p: file_hash(Path(p)) for p in outputs}, log=str(log))
        job.update(status=result, release_ready=(step == 'release'))
        save_job(root, job)
        return {'step': step, 'status': result, 'log': str(log), 'cached': False}
    except BaseException as exc:
        record.update(status='failed', error=str(exc), log=str(log), finished_at=now())
        job.update(status=f'failed:{step}', release_ready=False)
        save_job(root, job)
        raise


def accept_transcript(root, job, transcript, revisions):
    accepted = transcript.expanduser().resolve()
    if not accepted.is_file():
        raise ValueError('修订稿不存在。')
    import review_gate
    plain = accepted.with_suffix('.txt') if accepted.suffix.lower() == '.json' else accepted
    errors = review_gate.transcript_consistency(accepted, plain)
    revision_path = revisions.expanduser().resolve() if revisions else None
    if job['source_kind'] == 'audio':
        audio_errors, _ = review_gate.audio_evidence(
            Path(job['source']), accepted, Path(job['artifacts']['raw_transcript']),
            Path(job['artifacts']['refine_report']) if Path(job['artifacts']['refine_report']).is_file() else None,
            revision_path, job['options']['assurance'])
        errors += audio_errors
    if errors:
        raise ValueError('；'.join(errors))
    job['artifacts'].update(transcript=str(accepted), revisions=str(revision_path) if revision_path else None)
    return agent_action(root, job, 'author_minutes',
                        '证据稿已选定。立即继续起草完整纪要并填写覆盖清单，然后再次运行 run；'
                        '不要把修订稿交给用户等待检查或询问是否生成。')


def agent_action(root, job, action, instruction):
    job.update(status='agent_action', agent_action=action, release_ready=False)
    save_job(root, job)
    return {'ok': True, 'status': 'agent_action', 'action': action,
            'continuation_required': True, 'user_input_required': False,
            'release_ready': False, 'instructions': instruction,
            'artifacts': job['artifacts']}


def archive_stale_form(root, job, step):
    """Keep earlier human work in history and regenerate version-stale forms.

    An edited form with unchanged inputs is the expected handoff, not stale.
    """
    argv, inputs, outputs = command_for(job, step)
    path = Path(outputs[-1])
    old = job['steps'].get(step, {})
    if not path.exists() or old.get('signature') == signature(argv, inputs):
        return
    if root not in path.resolve().parents:
        raise ValueError('清单不在任务目录内，不能自动归档外部文件。')
    history = root / 'history'
    history.mkdir(exist_ok=True)
    archived = history / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f') + '-' + path.name)
    path.replace(archived)
    job.setdefault('form_history', []).append({'step': step, 'path': str(archived)})
    save_job(root, job)


def review_pending(path):
    review = read_json(path)
    if review.get('document_review', {}).get('confirmed') is not True:
        return True
    return any(row.get('decision') in (None, '', 'pending')
               for section in ('facts', 'findings') for row in review.get(section, []))


def run_automatic(root, job):
    """Continue deterministic work; delegate semantics to the active host agent."""
    if current(job, 'release'):
        return {'ok': True, 'status': 'release_ready', 'release_ready': True,
                'continuation_required': False, 'user_input_required': False,
                'artifacts': job['artifacts']}
    results = []
    if job['source_kind'] == 'audio':
        for step in ('transcribe', 'refine'):
            results.append(run_step(root, job, step))
    archive_stale_form(root, job, 'ledger')
    results.append(run_step(root, job, 'ledger'))
    if not Path(job['artifacts']['minutes']).is_file():
        result = agent_action(root, job, 'author_minutes',
                              '立即由当前智能体完成可执行的证据修订、完整总结与全部实质问答，'
                              '写入 artifacts.minutes 并填写 artifacts.ledger，然后再次运行 run。'
                              '首次答复已授权整条流程，不要结束任务等待用户检查证据稿或发出生成指令。')
        return {**result, 'steps': results}
    for step in ('draft', 'docx', 'render'):
        results.append(run_step(root, job, step))
    archive_stale_form(root, job, 'review-template')
    results.append(run_step(root, job, 'review-template'))
    if review_pending(job['artifacts']['review']):
        result = agent_action(root, job, 'review_document',
                              '立即由当前智能体逐项核对事实、警告与文档页面，按实际完成情况填写 review.json，'
                              '然后再次运行 run 完成正式验收。不要请求用户中途批准或假填 listened。'
                              '确实无法验证的内容保留未完成状态，在最终文件交付时集中披露，不能声称验收已通过。')
        return {**result, 'steps': results}
    results.append(run_step(root, job, 'release'))
    return {'ok': True, 'status': 'release_ready', 'release_ready': True,
            'continuation_required': False, 'user_input_required': False,
            'steps': results, 'artifacts': job['artifacts']}


def status(job):
    states = {step: ('current' if current(job, step) else
                     (job['steps'][step]['status'] if job['steps'][step]['status'] != 'completed' else 'stale')
                     if step in job['steps'] else 'not_run') for step in STEPS}
    ready = current(job, 'release') and read_json(Path(job['job_dir']) / 'checks-summary.json').get('release_ready') is True
    return {'ok': True, 'status': 'release_ready' if ready else 'incomplete',
            'last_status': job['status'], 'steps': states, 'release_ready': ready,
            'continuation_required': not ready, 'user_input_required': False,
            'artifacts': job['artifacts'],
            'authoring': '当前智能体按 artifacts 路径继续起草、校验与交付；内部阶段不要求用户检查或再次发出生成指令。'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    init = commands.add_parser('init')
    init.add_argument('--input', type=Path, required=True)
    init.add_argument('--source-kind', choices=('audio', 'transcript', 'notes'), default='audio')
    init.add_argument('--runtime-python', default=sys.executable)
    init.add_argument('--engine', choices=('funasr', 'qwen'), default='funasr')
    init.add_argument('--assurance', choices=('standard', 'high'), default='standard')
    init.add_argument('--offline', action='store_true')
    init.add_argument('--context', default='')
    init.add_argument('--model', help='explicit primary model ID or local directory')
    init.add_argument('--aligner', help='explicit Qwen aligner ID or local directory')
    init.add_argument('--review-model', help='explicit independent Qwen review model ID or local directory')
    init.add_argument('--timestamps', action='store_true', help='enable optional Qwen forced alignment')
    init.add_argument('--language', default='auto')
    init.add_argument('--device', choices=('auto', 'cpu', 'cuda', 'mps'), default='auto')
    init.add_argument('--diarize', action='store_true')
    init.add_argument('--speakers', type=int)
    init.add_argument('--mode', choices=('auto', 'minutes', 'qa-summary'), default='auto')
    init.add_argument('--subtitle', default='')
    init.add_argument('--project-name', default='', help='confirmed project name; preferred filename subject')
    init.add_argument('--interviewee', default='', help='interview subject name when no project name is available')
    init.add_argument('--interview-date', default='', help='confirmed interview date/time; never defaults to today')
    init.add_argument('--glossary', type=Path, action='append', default=[])
    run = commands.add_parser('run')
    run.add_argument('--step', choices=STEPS)
    stat = commands.add_parser('status')
    accept = commands.add_parser('accept')
    accept.add_argument('--transcript', type=Path, required=True)
    accept.add_argument('--revisions', type=Path)
    for command in (init, run, stat, accept):
        command.add_argument('--job-dir', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'init':
            result = init_job(args)
        else:
            root = args.job_dir.expanduser().resolve()
            if args.command == 'status':
                # Atomic manifests support read-only progress inspection during
                # a long ASR run; do not wait on its exclusive mutation lock.
                result = status(load_job(root))
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return 0
            with job_lock(root):
                job = load_job(root)
                if args.command == 'accept':
                    result = accept_transcript(root, job, args.transcript, args.revisions)
                elif args.step:
                    result = run_step(root, job, args.step)
                else:
                    result = run_automatic(root, job)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'ok': False, 'error': str(exc), 'release_ready': False,
                          'continuation_required': True, 'user_input_required': False,
                          'next': '当前智能体排查并继续；无法解决的真实执行限制随最终成果集中说明，不追加常规确认门槛。'},
                         ensure_ascii=False, indent=2))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
