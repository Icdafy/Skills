#!/usr/bin/env python3
"""Compare ASR text with supplied labels; never transcribe or invent labels."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata

MAX_SAMPLE_CHARACTERS = 4000
STATUSES = ('human_verified', 'synthetic', 'unverified')


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def normalized(text):
    """Ignore ordinary punctuation; retain numeric separators/signs and digits."""
    compact = ''.join(char for char in text if not char.isspace())
    result = []
    for index, char in enumerate(compact):
        left_digit = index > 0 and compact[index - 1].isdecimal()
        right_digit = index + 1 < len(compact) and compact[index + 1].isdecimal()
        numeric_mark = ((char in '.．,，:：/／' and left_digit and right_digit)
                        or (char in '%％‰' and left_digit)
                        or (char in '+＋-－−' and right_digit))
        if not unicodedata.category(char).startswith('P') or numeric_mark:
            result.append(char)
    return ''.join(result)


def edit_counts(reference, hypothesis):
    """Exact unit-cost Levenshtein S/D/I with deterministic diagonal-first ties."""
    if max(len(reference), len(hypothesis)) > MAX_SAMPLE_CHARACTERS:
        raise ValueError(f'each normalized sample must be <= {MAX_SAMPLE_CHARACTERS} characters; split long audio into labelled clips')
    previous = [(0, 0, j) for j in range(len(hypothesis) + 1)]
    for i, left in enumerate(reference, 1):
        current = [(0, i, 0)]
        for j, right in enumerate(hypothesis, 1):
            sub, delete, insert = previous[j - 1]
            diagonal = (sub + (left != right), delete, insert)
            sub, delete, insert = previous[j]
            deletion = (sub, delete + 1, insert)
            sub, delete, insert = current[-1]
            insertion = (sub, delete, insert + 1)
            current.append(min((diagonal, deletion, insertion), key=sum))
        previous = current
    substitutions, deletions, insertions = previous[-1]
    errors = substitutions + deletions + insertions
    return {'substitutions': substitutions, 'deletions': deletions, 'insertions': insertions,
            'errors': errors, 'reference_characters': len(reference),
            'hypothesis_characters': len(hypothesis),
            'cer': errors / len(reference) if reference else None,
            'empty_reference_insertions': insertions if not reference else 0}


def _string(value, field, *, nonempty=False):
    if not isinstance(value, str) or (nonempty and not value.strip()):
        raise ValueError(f'{field} must be a {"nonempty " if nonempty else ""}string')
    return value


def _strings(value, field):
    if not isinstance(value, list):
        raise ValueError(f'{field} must be a list')
    return list(dict.fromkeys(_string(item, field, nonempty=True) for item in value))


def read_dataset(path, *, allow_empty=False):
    path = Path(path).expanduser().resolve()
    try:
        document = json.loads(path.read_text(encoding='utf-8-sig'))
    except json.JSONDecodeError as error:
        raise ValueError(f'{path}: invalid JSON: {error.msg}') from error
    if not isinstance(document, dict) or type(document.get('schema_version')) is not int or document['schema_version'] != 1:
        raise ValueError(f'{path}: expected schema_version 1')
    if not isinstance(document.get('samples'), list) or (not document['samples'] and not allow_empty):
        raise ValueError(f'{path}: samples must be a {"" if allow_empty else "nonempty "}list')
    samples = {}
    for sample in document['samples']:
        if not isinstance(sample, dict):
            raise ValueError(f'{path}: each sample must be an object')
        identity = _string(sample.get('id'), 'sample.id', nonempty=True)
        _string(sample.get('text'), f'{identity}.text')
        if len(normalized(sample['text'])) > MAX_SAMPLE_CHARACTERS:
            raise ValueError(f'{identity}: normalized text exceeds {MAX_SAMPLE_CHARACTERS} characters; split into labelled clips')
        if identity in samples:
            raise ValueError(f'{path}: duplicate sample id {identity}')
        samples[identity] = sample
    return path, document, samples


def media_evidence(sample, dataset_path):
    audio = sample.get('audio', sample.get('path', ''))
    if isinstance(audio, dict):
        audio_path, expected_hash = audio.get('path', ''), audio.get('sha256', '')
    else:
        audio_path, expected_hash = audio, sample.get('sha256', '')
    _string(audio_path, 'audio.path')
    _string(expected_hash, 'audio.sha256')
    result = {'path': audio_path, 'expected_sha256': expected_hash, 'actual_sha256': '',
              'exists': False, 'hash_matches': False}
    if audio_path:
        path = Path(audio_path).expanduser()
        if not path.is_absolute():
            path = dataset_path.parent / path
        path = path.resolve()
        result['path'] = str(path)
        result['exists'] = path.is_file()
        if result['exists']:
            result['actual_sha256'] = file_hash(path)
            result['hash_matches'] = bool(re.fullmatch(r'[a-fA-F0-9]{64}', expected_hash)) and result['actual_sha256'] == expected_hash.lower()
    return result


def reference_metadata(sample, path):
    identity = sample['id']
    status = sample.get('annotation_status', 'unverified')
    if status not in STATUSES:
        raise ValueError(f'{identity}: invalid annotation_status')
    reviewer = _string(sample.get('reviewer', ''), f'{identity}.reviewer')
    terms = _strings(sample.get('expected_terms', []), f'{identity}.expected_terms')
    if any(term not in sample['text'] for term in terms):
        raise ValueError(f'{identity}: every expected_term must literally occur in reference text')
    checks = sample.get('critical_checks', [])
    if not isinstance(checks, list):
        raise ValueError(f'{identity}: critical_checks must be a list')
    ids = set()
    for check in checks:
        if not isinstance(check, dict):
            raise ValueError(f'{identity}: critical check must be an object')
        check_id = _string(check.get('id'), 'critical_check.id', nonempty=True)
        _string(check.get('kind'), 'critical_check.kind', nonempty=True)
        phrases = _strings(check.get('accepted_phrases'), 'accepted_phrases')
        if not phrases or not any(phrase in sample['text'] for phrase in phrases):
            raise ValueError(f'{identity}/{check_id}: at least one accepted phrase must occur in reference text')
        if check_id in ids:
            raise ValueError(f'{identity}: duplicate critical_check id {check_id}')
        ids.add(check_id)
    media = media_evidence(sample, path)
    reasons = []
    if status != 'human_verified':
        reasons.append('annotation_not_human_verified')
    if not reviewer.strip():
        reasons.append('missing_reviewer')
    if not media['exists']:
        reasons.append('audio_missing')
    elif not media['hash_matches']:
        reasons.append('audio_hash_missing_or_mismatched')
    return {'annotation_status': status, 'reviewer': reviewer, 'audio': media,
            'eligible_for_audio_benchmark': not reasons, 'ineligible_reasons': reasons,
            'expected_terms': terms, 'critical_checks': checks}


def aggregate(details):
    totals = {key: sum(item['edit_counts'][key] for item in details)
              for key in ('substitutions', 'deletions', 'insertions', 'errors',
                          'reference_characters', 'hypothesis_characters', 'empty_reference_insertions')}
    totals['cer'] = totals['errors'] / totals['reference_characters'] if totals['reference_characters'] else None
    totals['sample_count'] = len(details)
    tp = sum(len(item['terms']['matched']) for item in details)
    fp = sum(len(item['terms']['false_insertions']) for item in details)
    fn = sum(len(item['terms']['missed']) for item in details)
    totals['terms'] = {'true_positives': tp, 'false_positives': fp, 'false_negatives': fn,
                       'precision': tp / (tp + fp) if tp + fp else None,
                       'recall': tp / (tp + fn) if tp + fn else None}
    checks = [check for item in details for check in item['critical_checks']]
    totals['critical_checks'] = {'checked': len(checks), 'literal_hits': sum(check['matched'] for check in checks),
                                 'semantic_accuracy': None}
    return totals


def score(reference, hypothesis):
    reference_path, reference_document, reference_samples = read_dataset(reference)
    hypothesis_path, hypothesis_document, hypothesis_samples = read_dataset(hypothesis, allow_empty=True)
    extra = sorted(set(hypothesis_samples) - set(reference_samples))
    if extra:
        raise ValueError('hypothesis contains unknown sample ids: ' + ', '.join(extra))
    missing = sorted(set(reference_samples) - set(hypothesis_samples))
    metadata = {identity: reference_metadata(sample, reference_path) for identity, sample in reference_samples.items()}
    vocabulary = list(dict.fromkeys(term for item in metadata.values() for term in item['expected_terms']))
    details = []
    for identity, sample in reference_samples.items():
        hypothesis_sample = hypothesis_samples.get(identity, {'text': ''})
        actual = hypothesis_sample['text']
        expected = sample['text']
        gold = {term for term in vocabulary if term in expected}
        predicted = {term for term in vocabulary if term in actual}
        checks = []
        for check in metadata[identity]['critical_checks']:
            matches = [phrase for phrase in check['accepted_phrases'] if phrase in actual]
            checks.append({**check, 'matched': bool(matches), 'matched_phrases': matches,
                           'measurement': 'literal_phrase_presence_only'})
        details.append({'id': identity, 'missing_hypothesis': identity in missing,
                        'reference_text': expected, 'hypothesis_text': actual,
                        **{key: value for key, value in metadata[identity].items() if key != 'critical_checks'},
                        'edit_counts': edit_counts(normalized(expected), normalized(actual)),
                        'terms': {'matched': sorted(gold & predicted), 'missed': sorted(gold - predicted),
                                  'false_insertions': sorted(predicted - gold)},
                        'critical_checks': checks,
                        'model_metadata': hypothesis_sample.get('model_metadata', hypothesis_document.get('model_metadata', {}))})
    eligible = [item for item in details if item['eligible_for_audio_benchmark']]
    return {'schema_version': 1,
            'reference': {'path': str(reference_path), 'sha256': file_hash(reference_path),
                          'annotation_status_counts': {status: sum(item['annotation_status'] == status for item in details) for status in STATUSES}},
            'hypothesis': {'path': str(hypothesis_path), 'sha256': file_hash(hypothesis_path)},
            'model_metadata': hypothesis_document.get('model_metadata', {}),
            'missing_sample_ids': missing,
            'overall': aggregate(details), 'eligible_audio_only': aggregate(eligible),
            'all_samples_audio_benchmark_eligible': len(eligible) == len(details),
            'term_vocabulary': vocabulary,
            'measurement_notes': [
                'CER uses exact character edit distance after dropping whitespace and ordinary Unicode punctuation; numeric separators/signs/percent marks, digits, case and other symbols are retained. No number-value normalization is performed.',
                'CER is weighted by reference characters; empty-reference insertions remain errors and are also reported separately. CER is null when the denominator is zero.',
                'Term precision/recall measures literal presence per sample over the union of expected_terms; it does not measure pronunciation or semantic identity.',
                'Critical checks are literal phrase presence, not semantic correctness; contradictory wording can still contain an accepted phrase.',
                'Audio eligibility checks declared human annotation, reviewer, local file existence and SHA-256 only; it does not independently verify the reviewer, audio decoding or listening quality.',
                'Synthetic/unverified labels and samples without verified audio cannot establish real-audio transcription accuracy.',
            ], 'samples': details}


def initialize(audio_paths, output):
    output = Path(output).expanduser().resolve()
    if output.exists():
        raise ValueError('init refuses to overwrite an existing dataset')
    samples = []
    for number, audio in enumerate(audio_paths, 1):
        path = Path(audio).expanduser().resolve()
        if not path.is_file():
            raise ValueError(f'audio file does not exist: {path}')
        samples.append({'id': f'sample-{number:03d}', 'audio': {'path': str(path), 'sha256': file_hash(path)},
                        'text': '', 'annotation_status': 'unverified', 'reviewer': '',
                        'expected_terms': [], 'critical_checks': []})
    if not samples:
        samples.append({'id': 'sample-001', 'text': '', 'annotation_status': 'unverified',
                        'reviewer': '', 'expected_terms': [], 'critical_checks': []})
    document = {'schema_version': 1, 'dataset_status': 'draft_requires_annotation', 'samples': samples}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return document


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest='command', required=True)
    init = subparsers.add_parser('init', help='write an unlabelled draft, without running ASR')
    init.add_argument('--audio', type=Path, action='append', default=[])
    init.add_argument('--output', type=Path, required=True)
    evaluate = subparsers.add_parser('score', help='compare supplied reference and hypothesis text')
    evaluate.add_argument('--reference', type=Path, required=True)
    evaluate.add_argument('--hypothesis', type=Path, required=True)
    evaluate.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'init':
            initialize(args.audio, args.output)
        else:
            result = score(args.reference, args.hypothesis)
            output = args.output.expanduser().resolve()
            protected = {args.reference.resolve(), args.hypothesis.resolve()}
            protected.update(Path(item['audio']['path']) for item in result['samples'] if item['audio']['path'])
            if output in protected:
                raise ValueError('output must not overwrite a dataset or source audio')
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(str(args.output.expanduser().resolve()))
    except (OSError, ValueError) as error:
        print(f'evaluate_asr: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
