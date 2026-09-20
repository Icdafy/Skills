#!/usr/bin/env python3
"""Build or verify the three downloadable, self-contained skill ZIP archives."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import zipfile

REPO = Path(__file__).resolve().parents[1]
NAMES = ('hangye-fenxi', 'zhuying-yewu-fenxi', 'gongsi-qingkuang')
spec = importlib.util.spec_from_file_location('portable', REPO / 'gongsi-qingkuang/scripts/skill_portability.py')
portable = importlib.util.module_from_spec(spec)
spec.loader.exec_module(portable)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Fail if a ZIP is missing, stale or corrupt')
    parser.add_argument('--output-dir', type=Path, default=REPO / 'distributions/investment-report-skills')
    args = parser.parse_args()
    for name in NAMES:
        root = REPO / name
        if not args.check:
            portable.package(root, args.output_dir)
            continue
        record = portable.check(root)
        archive = args.output_dir / (name + '.zip')
        expected_digest = (args.output_dir / (name + '.zip.sha256')).read_text(encoding='utf-8').split()[0]
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
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
