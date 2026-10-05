"""Repository skill collection and paths come only from skills-index.json."""
import json
from pathlib import Path
import re

REPO = Path(__file__).resolve().parents[1]


def load_index(repo=REPO):
    repo = Path(repo).resolve()
    index = json.loads((repo / 'skills-index.json').read_text(encoding='utf-8'))
    if index.get('schema_version') != 1 or not index.get('skills'):
        raise ValueError('Unsupported or empty skills-index.json')
    seen = set()
    for entry in index['skills']:
        name = entry['id']
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name) or name in seen:
            raise ValueError(f'Duplicate or invalid skill ID: {name}')
        seen.add(name)
        if entry['source'] != 'skills/' + name:
            raise ValueError(f'Incorrect index source path: {name}')
        for key in ('source', 'readme', 'archive'):
            path = (repo / entry[key]).resolve()
            if not path.is_relative_to(repo):
                raise ValueError(f'Index path escapes repository: {entry[key]}')
        expected = f"distributions/{entry['distribution']}/{name}.zip"
        if entry['archive'] != expected:
            raise ValueError(f'Incorrect archive path: {name}')
        if not re.fullmatch(r'\d+\.\d+\.\d+', entry['version']):
            raise ValueError(f'Invalid version: {name}')
    return index


def entries(repo=REPO):
    return {entry['id']: entry for entry in load_index(repo)['skills']}


def source_path(name, repo=REPO):
    return Path(repo) / entries(repo)[name]['source']
