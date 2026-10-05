"""Version-bound occurrence review and release evidence; no ASR or semantic oracle."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re

import audit_coverage
import fact_check
from run_state import atomic_json, covered_seconds, file_hash


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(value, dict):
        raise ValueError(f'JSON 顶层必须是对象：{path}')
    return value


def transcript_consistency(structured: Path, plain: Path) -> list[str]:
    if structured.suffix.lower() != '.json':
        return []
    payload = read_json(structured)
    errors = []
    compact = lambda value: re.sub(r'\s+', '', value)
    if compact(str(payload.get('text', ''))) != compact(plain.read_text(encoding='utf-8-sig')):
        errors.append('JSON 与 TXT 转录内容不一致；请从同一修订版本重新导出。')
    stamps = payload.get('timestamps') or []
    if stamps:
        # Engines/aligners may segment punctuation differently, but cannot drop
        # words or numbers from the timestamp stream consumed by the audits.
        words = lambda value: re.sub(r'[^\w]', '', fact_check.normalize(value))
        joined = ''.join(str(x.get('text', '')) for x in stamps)
        if words(joined) != words(str(payload.get('text', ''))):
            errors.append('时间戳文本与完整转录正文不一致；不能只审计部分时间戳。')
    return errors


def input_bindings(paths: dict[str, Path | None]) -> dict:
    return {key: {'path': str(path.resolve()), 'sha256': file_hash(path)}
            for key, path in paths.items() if path is not None and path.is_file()}


def fact_rows(transcript: Path) -> list[dict]:
    windows, _ = audit_coverage.build_windows(transcript, 300, 1500)
    return [{'id': f'W{window.index}-N{i}', 'window': window.label,
             'raw': token.raw, 'value': token.value, 'kind': token.kind,
             'unit': token.unit, 'context': token.context,
             'decision': 'pending', 'minutes_lines': [], 'reason': '', 'reviewer': ''}
            for window in windows for i, token in enumerate(window.number_tokens, 1)]


def finding(key: str, message: str, *, audio: bool = False) -> dict:
    digest = hashlib.sha256(message.encode('utf-8')).hexdigest()[:16]
    return {'id': f'{key}:{digest}', 'message': message, 'audio_required': audio,
            'decision': 'pending', 'reason': '', 'reviewer': '', 'method': ''}


def check_findings(checks: list[dict], waivers: dict) -> list[dict]:
    findings = []
    for check in checks:
        term_block = False
        for line in check.get('stdout', '').splitlines():
            warning = line.startswith(('警告', '强警告', '提示', '术语改写提示'))
            term_block = term_block or line.startswith('术语改写提示')
            if (warning or ('疑似移用' in line and line.startswith('- 第'))
                    or (term_block and line.startswith('- 「'))):
                findings.append(finding(check['name'], line))
    for flag, values in waivers.items():
        for value in values:
            findings.append(finding('waiver', f'{flag}: {value}'))
    return {row['id']: row for row in findings}.values()


def audio_evidence(source: Path | None, transcript: Path, raw: Path | None,
                   report: Path | None, revisions: Path | None,
                   assurance: str) -> tuple[list[str], list[dict]]:
    errors, findings = [], []
    if source is None or not source.is_file():
        return ['录音模式缺少可读取的 --source。'], []
    raw = raw or transcript
    if raw.suffix.lower() != '.json':
        return ['录音模式必须保留原始 JSON 转录稿。'], []
    original = read_json(raw)
    accepted = read_json(transcript) if transcript.suffix.lower() == '.json' else {}
    source_sha = file_hash(source)
    for label, payload in [('原始稿', original), ('修订稿', accepted)]:
        if payload.get('source_sha256') != source_sha:
            errors.append(f'{label}未绑定当前录音 SHA-256。')
        if payload.get('is_partial') or payload.get('clip_start_seconds', 0):
            errors.append(f'{label}是样本或裁剪稿，不能作为整段录音验收依据。')
    if file_hash(raw) != file_hash(transcript):
        if revisions is None or not revisions.is_file():
            errors.append('原始稿与修订稿不同，缺少 --revisions 修订记录。')
        else:
            log = read_json(revisions)
            if (log.get('raw_sha256') != file_hash(raw)
                    or log.get('accepted_sha256') != file_hash(transcript)):
                errors.append('修订记录没有绑定本次原始稿和修订稿。')
            entries = log.get('entries') or []
            if not entries:
                errors.append('修订记录为空。')
            for entry in entries:
                if not all(str(entry.get(k, '')).strip() for k in ('reason', 'reviewer', 'method')):
                    errors.append('修订记录缺少理由、裁决者或裁决方式。')
                if not isinstance(entry.get('start'), (int, float)) or not isinstance(entry.get('end'), (int, float)):
                    errors.append('修订记录缺少录音起止时间。')
                if 'before' not in entry or 'after' not in entry:
                    errors.append('修订记录缺少修改前后文本。')
                if entry.get('method') not in ('listened', 'user_confirmed_audio'):
                    errors.append('修订必须记录实际回听依据，再次 ASR 不等于回听。')
                if (isinstance(entry.get('start'), (int, float)) and isinstance(entry.get('end'), (int, float))
                        and not 0 <= entry['start'] < entry['end'] <= float(original.get('duration_seconds', 0))):
                    errors.append('修订记录的时间范围无效。')
    if report is None or not report.is_file():
        if assurance == 'high':
            errors.append('高风险录音缺少全量独立复核 JSON 报告。')
        else:
            findings.append(finding('single-engine', '普通保障等级未提供独立引擎报告；仅完成单引擎处理。'))
        return errors, findings
    data = read_json(report)
    required = {'schema_version', 'model', 'primary_engine', 'primary_model', 'source_sha256',
                'transcript_sha256', 'review_mode', 'duration_seconds', 'covered_seconds',
                'budget_minutes', 'clips'}
    if not required.issubset(data) or data.get('schema_version') != 3:
        errors.append('复核报告缺少必需字段或为旧版本，须重新生成完整证据。')
    if not isinstance(data.get('model'), str) or not data['model'].strip():
        errors.append('复核报告缺少实际复核模型。')
    if not original.get('model') or data.get('primary_model') != original.get('model'):
        errors.append('复核报告缺少与原始稿一致的主模型标识。')
    if data.get('source_sha256') != source_sha:
        errors.append('复核报告与源录音哈希不一致。')
    if data.get('transcript_sha256') not in {file_hash(raw), file_hash(transcript)}:
        errors.append('复核报告没有绑定本次原始稿或修订稿。')
    if data.get('primary_engine') != original.get('engine'):
        errors.append('复核报告的主引擎与原始转录稿不一致。')
    if original.get('engine') == 'qwen' and 'qwen' in str(data.get('model', '')).lower():
        errors.append('同族 Qwen 模型不能计为独立双引擎复核。')
    duration = data.get('duration_seconds', 0)
    clips = data.get('clips') or []
    ranges = []
    for clip in clips:
        start, end = clip.get('start', -1), clip.get('end', -1)
        if not (isinstance(start, (int, float)) and isinstance(end, (int, float))
                and 0 <= start < end <= duration):
            errors.append('复核报告包含无效时间区间。')
            continue
        if clip.get('status') != 'skipped':
            ranges.append((start, end))
        if clip.get('status') not in ('consistent', 'conflict', 'review', 'skipped'):
            errors.append('复核报告包含未完成片段。')
        if (not isinstance(clip.get('funasr_text'), str) or not isinstance(clip.get('qwen_text'), str)
                or not isinstance(clip.get('conflicts'), list)):
            errors.append('复核片段缺少两引擎文本或差异证据。')
        elif clip.get('status') == 'consistent':
            from refine_transcript import compare_texts
            if (not clip['qwen_text'].strip() or clip['conflicts']
                    or compare_texts(clip['funasr_text'], clip['qwen_text'], [])):
                errors.append('一致片段的实际文本仍有差异或为空，须重新比较并裁决。')
        if clip.get('status') != 'consistent':
            findings.append(finding('audio', json.dumps(clip, ensure_ascii=False, sort_keys=True),
                                    audio=clip.get('status') != 'skipped'))
    if assurance == 'high':
        if data.get('review_mode') != 'all' or data.get('budget_minutes') is not None:
            errors.append('高风险录音必须全量复核，禁止预算截断。')
        if (not duration or abs(duration - float(original.get('duration_seconds', 0))) > 1
                or covered_seconds(ranges) < duration - 0.01):
            errors.append('全量复核未覆盖完整录音时间轴。')
    if data.get('covered_seconds') != covered_seconds(ranges):
        errors.append('报告覆盖时长与片段区间并集不一致。')
    return errors, findings


def build_review(bindings: dict, policy: dict, facts: list[dict], findings: list[dict]) -> dict:
    return {'schema_version': 1, 'inputs': bindings, 'policy': policy,
            'facts': facts, 'findings': list(findings),
            'document_review': {'confirmed': False, 'reviewer': '', 'reason': ''}}


def validate_review(review: dict, expected: dict, minutes: Path) -> list[str]:
    errors = []
    if review.get('schema_version') != 1 or review.get('inputs') != expected['inputs'] or review.get('policy') != expected['policy']:
        return ['人工复核清单与当前文件版本或保障等级不一致，请重新生成并复核。']
    lines = minutes.read_text(encoding='utf-8-sig').splitlines()
    for kind in ('facts', 'findings'):
        actual_rows = review.get(kind) or []
        rows = {row.get('id'): row for row in actual_rows}
        if len(rows) != len(actual_rows) or set(rows) != {x['id'] for x in expected[kind]}:
            errors.append(f'{kind} 清单缺项、多项或有重复 ID。')
        for original in expected[kind]:
            row = rows.get(original['id'], {})
            immutable = ('raw', 'value', 'kind', 'unit', 'context', 'window') if kind == 'facts' else ('message', 'audio_required')
            if any(row.get(key) != original.get(key) for key in immutable):
                errors.append(f'{original["id"]} 的证据字段被改动。')
            if not str(row.get('reason', '')).strip() or not str(row.get('reviewer', '')).strip():
                errors.append(f'{original["id"]} 缺少确认理由或裁决者。')
            if kind == 'facts':
                decision = row.get('decision')
                if decision not in ('include', 'omit'):
                    errors.append(f'{original["id"]} 尚未判定。')
                elif decision == 'include':
                    positions = row.get('minutes_lines') or []
                    if not positions or any(type(n) is not int or not 1 <= n <= len(lines) for n in positions):
                        errors.append(f'{original["id"]} 缺少有效纪要行号。')
                        continue
                    target = fact_check.extract_tokens(fact_check.normalize('\n'.join(lines[n-1] for n in positions)), body_only=True)
                    token = fact_check.Token(original['raw'], original['kind'], original['value'], 0, original['context'], original['unit'])
                    if not any(fact_check.tokens_match(token, candidate) for candidate in target):
                        errors.append(f'{original["id"]} 指向的纪要行没有对应数值或单位。')
            else:
                if row.get('decision') != 'confirmed':
                    errors.append(f'{original["id"]} 尚未处理。')
                if original['audio_required'] and row.get('method') not in ('listened', 'user_confirmed_audio'):
                    errors.append(f'{original["id"]} 未记录实际回听；再运行 ASR 不等于回听。')
    doc = review.get('document_review') or {}
    if doc.get('confirmed') is not True or not doc.get('reviewer') or not doc.get('reason'):
        errors.append('尚未记录全文内容、非数字事项及逐页版式人工复核。')
    return errors


def validate_render(report: Path | None, docx: Path | None) -> list[str]:
    if report is None or not report.is_file() or docx is None or not docx.is_file():
        return ['交付验收缺少 DOCX 或渲染报告。']
    data = read_json(report)
    errors = []
    if data.get('docx_sha256') != file_hash(docx):
        errors.append('渲染报告对应其他 DOCX 版本。')
    if (data.get('ok') is not True or data.get('missing_required_fonts')
            or data.get('substituted_fonts')):
        errors.append('渲染或字体检查未通过。')
    page_check = data.get('page_number_check') or {}
    if page_check.get('ok') is not True or any(x.get('ok') is not True for x in page_check.get('pages', [])):
        errors.append('页码位置未全部检测通过。')
    return errors
