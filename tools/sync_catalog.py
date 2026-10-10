#!/usr/bin/env python3
"""Generate or check README skill tables and Claude marketplace from the index."""
import argparse
import importlib.util
import json
import re
import sys

from skill_catalog import REPO, load_index, release_asset_url


def table(index, distribution=None):
    rows = [e for e in index['skills'] if distribution is None or e['distribution'] == distribution]
    result = []
    for category in dict.fromkeys(e['category'] for e in rows):
        result += [f'### {category}', '', '| 技能 / 做什么 | 源码 | 说明与调用 | 下载 | 版本 |',
                   '|---|---|---|---|---|']
        for e in rows:
            if e['category'] == category:
                result.append(f"| {e['name_zh']}（`{e['id']}`） | [源码]({e['source']}/) | "
                              f"[README]({e['readme']}) | [ZIP]({release_asset_url(e)}) | {e['version']} |")
        result.append('')
    return '\n'.join(result).rstrip() + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    index = load_index()
    failure = False
    targets = [(REPO / 'README.md', None)]
    for path, group in targets:
        content = path.read_text(encoding='utf-8')
        expected = '<!-- skills:begin -->\n' + table(index, group) + '<!-- skills:end -->'
        pattern = r'<!-- skills:begin -->[\s\S]*?<!-- skills:end -->'
        found = re.search(pattern, content)
        if not found:
            raise ValueError(f'Missing catalog markers: {path.relative_to(REPO)}')
        if found[0] != expected:
            if args.check:
                print(f'[FAIL] Catalog differs from index: {path.relative_to(REPO)}')
                failure = True
            else:
                path.write_bytes(re.sub(pattern, lambda _: expected, content).encode('utf-8'))
    marketplace = REPO / '.claude-plugin/marketplace.json'
    current = json.loads(marketplace.read_text(encoding='utf-8'))
    plugins = []
    for entry in index['skills']:
        skill = REPO / entry['source']
        spec = importlib.util.spec_from_file_location('catalog_metadata', skill / 'scripts/skill_portability.py')
        portable = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(portable)
        plugins.append({'name': entry['id'], 'source': './' + entry['source'],
                        'description': portable.metadata(skill)['description'],
                        'version': entry['version'], 'strict': False, 'skills': ['./']})
    if current['plugins'] != plugins:
        if args.check:
            print('[FAIL] Marketplace differs from index/source metadata')
            failure = True
        else:
            current['plugins'] = plugins
            marketplace.write_bytes((json.dumps(current, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    if not failure:
        print(f"[OK] Index, Chinese catalog and marketplace agree: {len(index['skills'])} skills")
    return int(failure)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, OSError) as error:
        print(f'[FAIL] {error}', file=sys.stderr)
        raise SystemExit(1)
