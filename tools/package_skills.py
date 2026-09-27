#!/usr/bin/env python3
"""Build or verify the downloadable, self-contained skill ZIP archives.

    python tools/package_skills.py            # rebuild every ZIP under distributions/
    python tools/package_skills.py --check    # fail if a ZIP is missing, stale or corrupt
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import zipfile

REPO = Path(__file__).resolve().parents[1]
GROUPS = {
    'investment-report-skills': ('hangye-fenxi', 'zhuying-yewu-fenxi', 'gongsi-qingkuang'),
    'office-skills': ('officialese-skill', 'yiti-skill', 'meeting-minutes-pro', 'soe-post-investment-report'),
}
spec = importlib.util.spec_from_file_location('portable', REPO / 'gongsi-qingkuang/scripts/skill_portability.py')
portable = importlib.util.module_from_spec(spec)
spec.loader.exec_module(portable)


def verify(name, output_dir):
    record = portable.check(REPO / name)
    archive = output_dir / (name + '.zip')
    expected_digest = (output_dir / (name + '.zip.sha256')).read_text(encoding='utf-8').split()[0]
    if hashlib.sha256(archive.read_bytes()).hexdigest() != expected_digest:
        raise ValueError(f'{name}: ZIP checksum mismatch')
    with zipfile.ZipFile(archive) as zipped:
        actual = json.loads(zipped.read(name + '/skill-manifest.json'))
        if actual != record:
            raise ValueError(f'{name}: ZIP is stale; rebuild')
        expected_names = {name + '/' + path for path in record['files']} | {name + '/skill-manifest.json'}
        if len(zipped.namelist()) != len(expected_names) or set(zipped.namelist()) != expected_names:
            raise ValueError(f'{name}: unexpected or missing archive entries')
        for path, digest in record['files'].items():
            if hashlib.sha256(zipped.read(name + '/' + path)).hexdigest() != digest:
                raise ValueError(f'{name}: content mismatch: {path}')
    print(f'[OK] {name}: downloadable archive matches current source')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true', help='Fail if a ZIP is missing, stale or corrupt')
    parser.add_argument('--group', choices=GROUPS, action='append', help='Limit to one distribution folder')
    args = parser.parse_args(argv)
    try:
        for group in args.group or GROUPS:
            output_dir = REPO / 'distributions' / group
            for name in GROUPS[group]:
                if args.check:
                    verify(name, output_dir)
                else:
                    portable.package(REPO / name, output_dir)
    except (ValueError, OSError, KeyError) as error:
        print(f'[FAIL] {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
