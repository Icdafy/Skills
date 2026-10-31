#!/usr/bin/env python3
"""Read project glossaries and prepare bounded, inspectable ASR hints.

Legacy TXT files remain whitespace-separated confirmed terms. Structured JSON
keeps phrases and separates confirmed aliases from review-only misrecognitions.
No function modifies a source glossary or discovers unrelated industry files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import unicodedata


ENTRY_FIELDS = {
    'term', 'aliases', 'misrecognitions', 'category', 'project', 'status',
    'source', 'confirmed_at', 'priority',
}


def _text(value, field: str, location: str, *, required: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f'{location}: {field} must be a string')
    if any(ord(char) < 32 and char != '\t' for char in value):
        raise ValueError(f'{location}: {field} must not contain control characters')
    result = unicodedata.normalize('NFC', ' '.join(value.split()))
    if required and not result:
        raise ValueError(f'{location}: {field} must not be empty')
    return result


def _forms(value, field: str, location: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f'{location}: {field} must be a list of strings')
    return list(dict.fromkeys(_text(item, field, location, required=True) for item in value))


def _legacy_terms(text: str, minimum_length=2) -> list[str]:
    return [term for line in text.splitlines() if not line.lstrip().startswith('#')
            for term in line.split() if len(term) >= minimum_length]


def load_entries(paths) -> list[dict]:
    """Read only explicitly supplied TXT/JSON files, in stable input order."""
    entries = []
    for given_path in paths:
        path = Path(given_path).expanduser().resolve()
        content = path.read_text(encoding='utf-8-sig')
        base = {'path': str(path), 'scope': 'industry' if path.parent.name == 'industry' else 'project'}
        if path.suffix.lower() != '.json':
            entries.extend({**base, 'term': term, 'aliases': [], 'misrecognitions': [],
                            'category': '', 'project': '', 'status': 'confirmed',
                            'source': 'legacy_txt', 'confirmed_at': '', 'priority': 0}
                           for term in _legacy_terms(content))
            continue
        try:
            document = json.loads(content)
        except json.JSONDecodeError as error:
            raise ValueError(f'{path}: invalid glossary JSON: {error.msg}') from error
        if not isinstance(document, dict) or set(document) != {'schema_version', 'entries'}:
            raise ValueError(f'{path}: glossary JSON requires schema_version and entries only')
        if type(document['schema_version']) is not int or document['schema_version'] != 1:
            raise ValueError(f'{path}: unsupported glossary schema_version (expected 1)')
        if not isinstance(document['entries'], list):
            raise ValueError(f'{path}: entries must be a list')
        for number, raw in enumerate(document['entries'], 1):
            location = f'{path}: entries[{number - 1}]'
            if not isinstance(raw, dict) or set(raw) - ENTRY_FIELDS:
                raise ValueError(f'{location}: invalid entry or unknown fields')
            entry = {**base, 'term': _text(raw.get('term'), 'term', location, required=True)}
            for field in ('aliases', 'misrecognitions'):
                entry[field] = _forms(raw.get(field, []), field, location)
            for field in ('category', 'project', 'source', 'confirmed_at'):
                entry[field] = _text(raw.get(field, ''), field, location)
            entry['status'] = raw.get('status', 'candidate')
            if entry['status'] not in ('confirmed', 'candidate'):
                raise ValueError(f'{location}: status must be confirmed or candidate')
            entry['priority'] = raw.get('priority', 0)
            if type(entry['priority']) is not int:
                raise ValueError(f'{location}: priority must be an integer')
            entries.append(entry)
    return entries


def collect_terms(paths, extra_terms) -> list[str]:
    """Return confirmed canonical terms and aliases, never misrecognitions."""
    terms = [form for entry in load_entries(paths) if entry['status'] == 'confirmed'
             for form in [entry['term'], *entry['aliases']]]
    # Explicit --term retains the legacy minimum-length and order behavior.
    terms.extend(term for term in extra_terms if len(term) >= 2)
    return list(dict.fromkeys(terms))


def collect_risk_terms(paths, extra_terms=()) -> list[str]:
    """Review-selection hints only: include known errors of confirmed entries.

    These strings must not be fed back as ASR hotwords or used for automatic
    replacement. They merely identify passages needing evidence-based review.
    """
    terms = [form for entry in load_entries(paths) if entry['status'] == 'confirmed'
             for form in [entry['term'], *entry['aliases'], *entry['misrecognitions']]]
    terms.extend(term for term in extra_terms if len(term) >= 2)
    return list(dict.fromkeys(terms))


def prepare_context(paths, context='', limit=400, engine='qwen', project='', extra_terms=()) -> dict:
    """Select complete terms: explicit context, project, then supplied industry.

    ``limit`` is this caller's character budget, not a model capability claim.
    Candidate/project-mismatched terms and known wrong spellings are excluded.
    Only files supplied by the caller are considered; no industry auto-discovery.
    """
    if type(limit) is not int or limit < 0:
        raise ValueError('context limit must be a nonnegative integer')
    if engine not in ('qwen', 'funasr'):
        raise ValueError('engine must be qwen or funasr')
    if not isinstance(context, str) or not isinstance(project, str):
        raise ValueError('context and project must be strings')
    paths = [Path(path).expanduser().resolve() for path in paths]
    entries = load_entries(paths)
    choices = []
    dropped = []
    explicit_terms = _legacy_terms(context, minimum_length=1) + [
        _text(term, 'extra_terms', 'explicit context', required=True) for term in extra_terms]
    for term in explicit_terms:
        choices.append({'term': term, 'canonical': term, 'origin': 'explicit',
                        'path': '', 'category': '', 'project': project, 'status': 'confirmed',
                        'source': 'explicit_context', 'confirmed_at': '', 'priority': 0,
                        'tier': 0})
    for entry in entries:
        record = {key: value for key, value in entry.items()
                  if key not in ('aliases', 'misrecognitions', 'scope')}
        for index, term in enumerate([entry['term'], *entry['aliases']]):
            item = {**record, 'term': term, 'canonical': entry['term'],
                    'origin': 'canonical' if index == 0 else 'alias',
                    'tier': 2 if entry['scope'] == 'industry' else 1}
            if entry['status'] != 'confirmed':
                dropped.append({**item, 'reason': 'candidate'})
            elif project and entry['project'] and entry['project'] != project:
                dropped.append({**item, 'reason': 'project_mismatch'})
            else:
                choices.append(item)
        # Keep excluded error variants inspectable without using them as hints.
        dropped.extend({**record, 'term': wrong, 'canonical': entry['term'],
                        'origin': 'misrecognition', 'reason': 'review_only'}
                       for wrong in entry['misrecognitions'])
    choices.sort(key=lambda item: (item['tier'], -item['priority']))
    selected = []
    seen = set()
    used = 0
    for item in choices:
        term = item['term']
        if term in seen:
            dropped.append({**item, 'reason': 'duplicate'})
            continue
        seen.add(term)
        cost = len(term) + bool(selected)
        if used + cost > limit:
            dropped.append({**item, 'reason': 'budget'})
            continue
        selected.append(item)
        used += cost
    terms = [item['term'] for item in selected]
    notes = []
    if engine == 'funasr' and any(any(char.isspace() for char in term) for term in terms):
        notes.append('SeacoParaformer 的字符串 hotword 接口按空白分词；含空格短语'
                     '在词库和清单中保留，但不能保证作为一个模型热词传入。')
    notes.append('上下文只是识别提示；选中词条不表示音频中出现过，也不保证识别正确。')
    return {
        'schema_version': 1, 'engine': engine, 'project': project, 'limit': limit,
        'context': ' '.join(terms), 'terms': terms, 'selected': selected,
        'dropped': dropped, 'adapter_notes': notes,
        'input_files': [{'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                        for path in paths],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--glossary', type=Path, action='append', default=[])
    parser.add_argument('--context', default='', help='explicit whitespace-separated priority terms')
    parser.add_argument('--term', action='append', default=[], help='an explicit complete term, including spaces')
    parser.add_argument('--limit', type=int, default=400)
    parser.add_argument('--engine', choices=('qwen', 'funasr'), default='qwen')
    parser.add_argument('--project', default='')
    parser.add_argument('--output', type=Path, help='optional JSON manifest; stdout otherwise')
    args = parser.parse_args(argv)
    try:
        result = prepare_context(args.glossary, args.context, args.limit, args.engine, args.project, args.term)
        content = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
        if args.output:
            output = args.output.expanduser().resolve()
            if output in [path.expanduser().resolve() for path in args.glossary]:
                raise ValueError('output must not overwrite a source glossary')
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(content, encoding='utf-8')
        else:
            print(content, end='')
    except (OSError, ValueError) as error:
        print(f'glossary: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
