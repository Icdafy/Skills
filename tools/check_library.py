#!/usr/bin/env python3
"""Validate collection, entry points, source resources, links and distribution licenses.

Standard library only. Never rebuilds packages or edits a client. Default checks
sources and any cached release ZIPs; --release-assets fetches and verifies every
published ZIP in the ignored work/releases/ cache.
"""
import argparse
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import re
import struct
import sys
from urllib.parse import unquote
import zipfile

import check_shared_scripts
import package_skills
from skill_catalog import REPO, load_index
import sync_catalog

FONT_SUFFIXES = {'.ttf', '.otf', '.ttc', '.woff', '.woff2', '.odttf', '.eot'}
SFNT_SIGNATURES = (b'\x00\x01\x00\x00', b'OTTO', b'true', b'ttcf', b'wOFF', b'wOF2')
SKIP = {'.git', 'work', '__pycache__', '.pytest_cache'}


def ole_streams(data):
    """Read CFB stream bytes, including mini streams, without an OLE dependency."""
    if len(data) < 512:
        raise ValueError('Truncated CFB document')
    sector_size = 1 << struct.unpack_from('<H', data, 30)[0]
    mini_size = 1 << struct.unpack_from('<H', data, 32)[0]
    def sector(number):
        start = (number + 1) * sector_size
        chunk = data[start:start + sector_size]
        if len(chunk) != sector_size:
            raise ValueError('Invalid CFB sector')
        return chunk
    fat_sectors = list(struct.unpack_from('<109I', data, 76))
    difat_next, difat_count = struct.unpack_from('<II', data, 68)
    for _ in range(difat_count):
        items = struct.unpack('<' + 'I' * (sector_size // 4), sector(difat_next))
        fat_sectors.extend(items[:-1])
        difat_next = items[-1]
    fat = []
    for number in fat_sectors:
        if number < 0xFFFFFFFA:
            fat.extend(struct.unpack('<' + 'I' * (sector_size // 4), sector(number)))
    def chain(first, table, getter):
        pieces, seen = [], set()
        while first < 0xFFFFFFFA:
            if first in seen or first >= len(table):
                raise ValueError('Invalid/cyclic CFB chain')
            seen.add(first)
            pieces.append(getter(first))
            first = table[first]
        return b''.join(pieces)
    directory = chain(struct.unpack_from('<I', data, 48)[0], fat, sector)
    entries = []
    for start in range(0, len(directory), 128):
        item = directory[start:start + 128]
        if len(item) < 128 or item[66] not in (2, 5):
            continue
        length = struct.unpack_from('<H', item, 64)[0]
        name = item[:max(0, length - 2)].decode('utf-16-le', errors='replace')
        entries.append((name, item[66], struct.unpack_from('<I', item, 116)[0],
                        struct.unpack_from('<Q', item, 120)[0]))
    mini_data = b''
    for _, kind, first, size in entries:
        if kind == 5:
            mini_data = chain(first, fat, sector)[:size]
    mini_fat_bytes = chain(struct.unpack_from('<I', data, 60)[0], fat, sector)
    mini_fat = list(struct.unpack('<' + 'I' * (len(mini_fat_bytes) // 4), mini_fat_bytes))
    cutoff = struct.unpack_from('<I', data, 56)[0]
    for name, kind, first, size in entries:
        if kind != 2:
            continue
        if size < cutoff:
            body = chain(first, mini_fat, lambda n: mini_data[n * mini_size:(n + 1) * mini_size])[:size]
        else:
            body = chain(first, fat, sector)[:size]
        yield name, body


def scan_payload(label, data, forbidden_hashes, depth=0, findings=None):
    if findings is None:
        findings = []
    if depth > 6:
        raise ValueError(f'Archive nesting exceeds limit: {label}')
    suffix = Path(label.rsplit('!', 1)[-1]).suffix.lower()
    if suffix in FONT_SUFFIXES or data.startswith(SFNT_SIGNATURES) or hashlib.sha256(data).hexdigest() in forbidden_hashes:
        findings.append(label)
        return findings
    if data.startswith(b'PK\x03\x04'):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for entry in archive.infolist():
                if entry.file_size > 64 * 1024 * 1024:
                    raise ValueError(f'Oversized nested archive entry: {label}!{entry.filename}')
                if not entry.is_dir():
                    scan_payload(label + '!' + entry.filename, archive.read(entry), forbidden_hashes, depth + 1, findings)
            # Catch renamed obfuscated font parts via their relationships/content type.
            if 'word/fontTable.xml' in archive.namelist():
                table = archive.read('word/fontTable.xml')
                if re.search(rb'<w:embed(?:Regular|Bold|Italic|BoldItalic)\b', table):
                    findings.append(label + '!word/fontTable.xml (embedded font relationship)')
    elif data.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'):
        for name, body in ole_streams(data):
            scan_payload(label + '!' + name, body, forbidden_hashes, depth + 1, findings)
            if re.search(r'(?i)(fontdata|embeddedfont|fontfile)', name):
                findings.append(label + '!' + name + ' (font stream)')
    return findings


def files(root):
    for path in root.rglob('*'):
        relative = path.relative_to(root)
        if set(relative.parts) & SKIP or not path.is_file():
            continue
        yield path


def check_links(root):
    broken = []
    for path in files(root):
        if path.suffix.lower() != '.md':
            continue
        text = path.read_text(encoding='utf-8-sig')
        for match in re.finditer(r'\]\((<[^>]+>|[^)\s]+)(?:\s+"[^"]*")?\)', text):
            target = unquote(match[1].strip('<>')).split('#', 1)[0]
            if not target or re.match(r'[a-z]+:', target, re.I):
                continue
            resolved = (path.parent / target).resolve()
            if not resolved.is_relative_to(root.resolve()) or not resolved.exists():
                broken.append(f'{path.relative_to(root)} -> {target}')
    if broken:
        raise ValueError('Broken links: ' + '; '.join(broken))
    print('[OK] Local Markdown links: broken=0')


def check_distribution(root):
    restricted = json.loads((root / 'docs/source-fonts.json').read_text(encoding='utf-8'))
    policy = load_index(root).get('font_policy', {})
    if (policy.get('retained_source_fonts') != restricted
            or policy.get('single_skill_zip_fonts') is not False
            or policy.get('redistribution_authorization_confirmed') is not False):
        raise ValueError('Source font retention policy differs from baseline or distribution scope')
    retained = {f['path']: f['sha256'] for f in restricted}
    if package_skills.portable.RETAINED_SOURCE_FONT_SHA256 != retained:
        raise ValueError('Standalone font retention contract differs from index')
    for item in restricted:
        path = root / item['path']
        if path.is_symlink() or not path.is_file():
            raise ValueError('Retained source font missing: ' + item['path'])
        body = path.read_bytes()
        if len(body) != item['bytes'] or hashlib.sha256(body).hexdigest() != item['sha256']:
            raise ValueError('Retained source font changed: ' + item['path'])
    hashes = set(retained.values())
    findings = []
    scanned = 0
    for path in files(root):
        if path.is_symlink():
            raise ValueError('Symlink in delivered tree: ' + str(path))
        label = path.relative_to(root).as_posix()
        if label in retained:
            continue  # Only these exact top-level source paths were checked above.
        scan_payload(label, path.read_bytes(), hashes, findings=findings)
        scanned += 1
    if findings:
        raise ValueError('Restricted font distribution: ' + '; '.join(findings))
    print(f'[OK] Retained source fonts: {len(retained)} exact paths/SHA-256; unchanged')
    print(f'[OK] Distribution scan: {scanned} other files including ZIP/OOXML/CFB streams; restricted-font hits=0')
    print('[INFO] Source fonts have separate licensing; see THIRD_PARTY_NOTICES.md. Validation does not certify public licensing.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release-assets', action='store_true',
                        help='Fetch published assets into work/ and require all release ZIPs to match')
    args = parser.parse_args()
    index = load_index()
    ids = {e['id'] for e in index['skills']}
    actual = {p.parent.relative_to(REPO).as_posix() for p in REPO.rglob('SKILL.md')
              if not (set(p.relative_to(REPO).parts) & SKIP)}
    expected = {e['source'] for e in index['skills']}
    if actual != expected:
        raise ValueError(f'Skill set differs: actual={sorted(actual)} expected={sorted(expected)}')
    if len({e['name_zh'].casefold() for e in index['skills']}) != len(ids):
        raise ValueError('Duplicate Chinese skill name')
    if sync_catalog.main(['--check']):
        raise ValueError('Index/README/marketplace mismatch')
    check_distribution(REPO)
    verified_releases = 0
    missing_releases = []
    for entry in index['skills']:
        root = REPO / entry['source']
        if (root / 'VERSION').read_text(encoding='utf-8').strip() != entry['version']:
            raise ValueError('Source VERSION differs from index: ' + entry['id'])
        if (root / 'LICENSE').read_text(encoding='utf-8') != (REPO / 'LICENSE').read_text(encoding='utf-8'):
            raise ValueError('Missing/different Apache-2.0 text: ' + entry['id'])
        if entry['version'] not in (root / 'CHANGELOG.md').read_text(encoding='utf-8'):
            raise ValueError('Version missing from CHANGELOG: ' + entry['id'])
        if not entry.get('verification') or not (REPO / entry['verification']['evidence']).is_file():
            raise ValueError('Verification state/evidence missing: ' + entry['id'])
        with redirect_stdout(io.StringIO()):
            if package_skills.portable.metadata(root)['name'] != entry['id']:
                raise ValueError('SKILL.md name differs from index: ' + entry['id'])
            package_skills.portable.check(root)
            archive = package_skills.archive_path(entry['id'])
            checksum = archive.with_name(archive.name + '.sha256')
            if args.release_assets:
                package_skills.download(entry['id'], force=True)
            if args.release_assets or archive.exists() or checksum.exists():
                package_skills.verify(entry['id'])
                verified_releases += 1
            else:
                missing_releases.append(entry['id'])
    for group in index['shared_groups']:
        if group['canonical'] not in group['skills'] or not set(group['skills']) <= ids:
            raise ValueError('Invalid shared group: ' + group['file'])
        if group['file'] == 'scripts/embed_fonts.py' and 'meeting-minutes-pro' in group['skills']:
            raise ValueError('Minutes-specific embed_fonts must not be synchronized into the other group')
        consistent, messages = check_shared_scripts.check_group(group, False)
        if not consistent:
            raise ValueError('Shared copy drift: ' + '; '.join(messages))
    print(f"[OK] Source resources, versions and {len(index['shared_groups'])} shared groups agree: {len(ids)} skills")
    print(f'[OK] Published ZIP byte locks and manifests verified: {verified_releases}/{len(ids)}')
    if missing_releases:
        print('[INFO] Release ZIPs absent from local cache: ' + ', '.join(missing_releases))
        print('[INFO] Source checks passed; release contents were not fully verified. Use --release-assets for published ZIP verification.')
    check_links(REPO)
    for name in ('LICENSE', 'NOTICE', 'THIRD_PARTY_NOTICES.md'):
        if not (REPO / name).is_file():
            raise ValueError('Missing distribution notice: ' + name)
    print('[PASS] Library validation passed. Model invocation and visual rendering are separately recorded.')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError, zipfile.BadZipFile, struct.error) as error:
        print(f'[FAIL] {error}', file=sys.stderr)
        raise SystemExit(1)
