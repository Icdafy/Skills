#!/usr/bin/env python3
"""Build or verify independent GitHub Release ZIPs in the ignored work/ cache.

    python tools/package_skills.py --skill yiti-skill
    python tools/package_skills.py --check --download  # verify published assets
    python tools/package_skills.py --all              # explicit all-skill build
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request
import zipfile
from skill_catalog import REPO, entries, load_index, source_path, release_archive_path, release_asset_url

CATALOG = entries()
# This legacy field is a selection group, not a tracked download directory.
GROUPS = {}
for name, entry in CATALOG.items():
    GROUPS.setdefault(entry['distribution'], []).append(name)
canonical = next(g['canonical'] for g in load_index()['shared_groups']
                 if g['file'] == 'scripts/skill_portability.py')
spec = importlib.util.spec_from_file_location('portable', source_path(canonical) / 'scripts/skill_portability.py')
portable = importlib.util.module_from_spec(spec)
spec.loader.exec_module(portable)


def archive_path(name, output_dir=None):
    if output_dir is not None:
        return Path(output_dir) / CATALOG[name]['release']['asset']
    return release_archive_path(CATALOG[name], REPO)


def _checksum(body, asset):
    parts = body.decode('utf-8-sig').split()
    if (len(parts) != 2 or not re.fullmatch(r'[0-9a-f]{64}', parts[0])
            or parts[1].lstrip('*') != asset):
        raise ValueError(f'{asset}: invalid SHA-256 sidecar')
    return parts[0]


def _check_digest(name, archive_body, checksum_body):
    release = CATALOG[name]['release']
    expected_digest = _checksum(checksum_body, release['asset'])
    if expected_digest != release['sha256']:
        raise ValueError(f'{name}: published SHA-256 differs from index')
    if hashlib.sha256(archive_body).hexdigest() != expected_digest:
        raise ValueError(f'{name}: ZIP checksum mismatch')


def download(name, output_dir=None, force=False):
    """Fetch a published asset and sidecar only after their byte lock agrees."""
    archive = archive_path(name, output_dir)
    checksum_path = archive.with_name(archive.name + '.sha256')
    if not force and archive.is_file() and checksum_path.is_file():
        try:
            _check_digest(name, archive.read_bytes(), checksum_path.read_bytes())
            return archive
        except ValueError:
            pass  # Replace a corrupt cache only with verified published bytes.
    payloads = []
    for checksum in (False, True):
        request = urllib.request.Request(
            release_asset_url(CATALOG[name], checksum),
            headers={'User-Agent': 'Icdafy-Skills-release-check'})
        with urllib.request.urlopen(request, timeout=30) as response:
            payloads.append(response.read())
    _check_digest(name, payloads[0], payloads[1])
    archive.parent.mkdir(parents=True, exist_ok=True)
    archive.write_bytes(payloads[0])
    checksum_path.write_bytes(payloads[1])
    print(f'[OK] {name}: published assets cached under work/releases/')
    return archive


def verify(name, output_dir=None):
    record = portable.check(source_path(name, REPO))
    archive = archive_path(name, output_dir)
    checksum_path = archive.with_name(archive.name + '.sha256')
    _check_digest(name, archive.read_bytes(), checksum_path.read_bytes())
    with zipfile.ZipFile(archive) as zipped:
        actual = json.loads(zipped.read(name + '/skill-manifest.json'))
        if actual != record:
            raise ValueError(f'{name}: release ZIP is stale; build and publish this skill')
        expected_names = {name + '/' + path for path in record['files']} | {name + '/skill-manifest.json'}
        if len(zipped.namelist()) != len(expected_names) or set(zipped.namelist()) != expected_names:
            raise ValueError(f'{name}: unexpected or missing archive entries')
        for path, digest in record['files'].items():
            if hashlib.sha256(zipped.read(name + '/' + path)).hexdigest() != digest:
                raise ValueError(f'{name}: content mismatch: {path}')
    print(f'[OK] {name}: published byte lock and ZIP manifest match current source')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
                                     allow_abbrev=False)
    parser.add_argument('--check', action='store_true', help='Read-only verification of cached published ZIPs')
    parser.add_argument('--download', action='store_true', help='With --check, fetch missing/corrupt release assets into work/')
    parser.add_argument('--group', choices=GROUPS, action='append', help='Filter by a legacy package group; not a directory')
    parser.add_argument('--skill', choices=CATALOG, action='append', help='Select only these skills; repeatable')
    parser.add_argument('--all', action='store_true', help='Explicitly build all selected skills')
    args = parser.parse_args(argv)
    if args.download and not args.check:
        parser.error('--download requires --check')
    if args.all and args.skill:
        parser.error('Use --skill or --all, not both')
    if not args.check and not (args.skill or args.all):
        parser.error('A build requires --skill <name> or an explicit --all')
    selected = [name for name, entry in CATALOG.items()
                if (not args.group or entry['distribution'] in args.group)
                and (not args.skill or name in args.skill)]
    if not selected:
        parser.error('No skills match --group and --skill')
    try:
        for name in selected:
            if args.check:
                if args.download:
                    download(name)
                verify(name)
            else:
                archive = portable.package(source_path(name, REPO), archive_path(name).parent)
                digest = hashlib.sha256(archive.read_bytes()).hexdigest()
                if digest != CATALOG[name]['release']['sha256']:
                    print(f'[INFO] {name}: register release.sha256={digest} before publishing and --check')
        if not args.check:
            print('[NEXT] Publish only these skill tags with their ZIP/SHA-256 assets; no release is created automatically.')
    except (ValueError, OSError, KeyError, zipfile.BadZipFile, urllib.error.URLError) as error:
        print(f'[FAIL] {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
