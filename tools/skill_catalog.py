"""Repository skill collection and paths come only from skills-index.json."""
import json
from pathlib import Path
import re
from urllib.parse import quote

REPO = Path(__file__).resolve().parents[1]
REPOSITORY_URL = 'https://github.com/Icdafy/Skills'


def load_index(repo=REPO):
    repo = Path(repo).resolve()
    index = json.loads((repo / 'skills-index.json').read_text(encoding='utf-8'))
    if index.get('schema_version') != 2 or not index.get('skills'):
        raise ValueError('Unsupported or empty skills-index.json')
    seen = set()
    for entry in index['skills']:
        name = entry['id']
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name) or name in seen:
            raise ValueError(f'Duplicate or invalid skill ID: {name}')
        seen.add(name)
        if entry['source'] != name:
            raise ValueError(f'Incorrect index source path: {name}')
        for key in ('source', 'readme'):
            path = (repo / entry[key]).resolve()
            if not path.is_relative_to(repo):
                raise ValueError(f'Index path escapes repository: {entry[key]}')
        if not re.fullmatch(r'\d+\.\d+\.\d+', entry['version']):
            raise ValueError(f'Invalid version: {name}')
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', entry['distribution']):
            raise ValueError(f'Invalid compatibility package group: {name}')
        release = entry['release']
        if release['tag'] != f"{name}/v{entry['version']}":
            raise ValueError(f'Release tag differs from skill version: {name}')
        if release['asset'] != f'{name}.zip':
            raise ValueError(f'Incorrect release asset name: {name}')
        if not re.fullmatch(r'[0-9a-f]{64}', release['sha256']):
            raise ValueError(f'Invalid published asset SHA-256: {name}')
        if 'archive' in entry:
            raise ValueError(f'Legacy tracked archive path remains: {name}')
    return index


def entries(repo=REPO):
    return {entry['id']: entry for entry in load_index(repo)['skills']}


def source_path(name, repo=REPO):
    return Path(repo) / entries(repo)[name]['source']


def release_archive_path(entry, repo=REPO):
    """Local build/cache only; release ZIPs are never tracked in the source tree."""
    return Path(repo) / 'work' / 'releases' / entry['id'] / entry['version'] / entry['release']['asset']


def release_asset_url(entry, checksum=False):
    release = entry['release']
    asset = release['asset'] + ('.sha256' if checksum else '')
    return f"{REPOSITORY_URL}/releases/download/{quote(release['tag'], safe='')}/{quote(asset, safe='')}"
