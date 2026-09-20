#!/usr/bin/env python3
"""Check, package or install this self-contained skill. Python 3.10+; stdlib only.

check --smoke additionally needs python-docx. No host configuration or font
installation is performed. Install is a dry run unless --apply is specified.
Edit this canonical copy and run tools/check_shared_scripts.py --sync.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SUPPORTED = ('hangye-fenxi', 'zhuying-yewu-fenxi', 'gongsi-qingkuang')
DIRECTORIES = {
    'claude-code': '.claude/skills',
    'kimi-code': '.kimi-code/skills',
    'qoder-cli': '.qoder/skills',
    'qoder-cn': '.lingma/skills',
    'qoderwork': '.qoderwork/skills',
    'trae-cn': '.trae-cn/skills',
    'agents': '.agents/skills',
}
SKIP = {'.git', '__pycache__', '.venv', 'node_modules'}
REQUIRED = ('SKILL.md', 'requirements.txt', 'references/agent-compatibility.md',
            'references/investment-logic-review.md', 'scripts/build_docx.py',
            'scripts/style_check.py', 'scripts/ensure_fonts.py',
            'scripts/embed_fonts.py', 'scripts/docx_format_helpers.py',
            'scripts/skill_portability.py')


def payload(path):
    """Normalize text to LF so Git autocrlf cannot make release ZIPs stale."""
    data = path.read_bytes()
    if path.suffix.lower() in ('.md', '.py', '.json', '.yaml', '.yml', '.txt', '.ps1'):
        return data.replace(b'\r\n', b'\n')
    return data


def included_files(root):
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError(f'Symlinks are not portable: {path}')
        rel = path.relative_to(root)
        if path.is_file() and not (set(rel.parts) & SKIP) and path.suffix not in ('.pyc', '.pyo'):
            if rel.as_posix() != 'skill-manifest.json':
                yield path


def metadata(root):
    raw = (root / 'SKILL.md').read_text(encoding='utf-8')
    front = re.match(r'\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)', raw, re.S)
    if not front:
        raise ValueError('Missing YAML frontmatter')
    fields = {}
    for line in front[1].splitlines():
        key, separator, value = line.partition(':')
        if separator:
            fields[key.strip()] = value.strip().strip('"\'')
    if fields.get('name') not in SUPPORTED or fields['name'] != root.name:
        raise ValueError('Folder name must equal the supported skill name')
    if not 1 <= len(fields.get('description', '')) <= 200:
        raise ValueError('Use a single-line description of 1–200 characters')
    return fields


def manifest(root):
    return {'name': metadata(root)['name'], 'format': 1,
            'files': {p.relative_to(root).as_posix(): hashlib.sha256(payload(p)).hexdigest()
                      for p in included_files(root)}}


def check(root):
    fields = metadata(root)
    missing = [p for p in REQUIRED if not (root / p).is_file()]
    if missing:
        raise ValueError('Missing resources: ' + ', '.join(missing))
    # Markdown links resolve against their containing file, never the task cwd.
    for path in root.rglob('*.md'):
        for target in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
            target = target.split('#')[0]
            if not target or '://' in target or target.startswith('mailto:'):
                continue
            if not (path.parent / target).exists():
                raise ValueError(f'Broken relative link: {path.relative_to(root)} -> {target}')
    record = root / 'skill-manifest.json'
    current = manifest(root)
    if record.is_file() and json.loads(record.read_text(encoding='utf-8')) != current:
        raise ValueError('Package checksum mismatch; restore the complete matching package')
    print(f"[OK] {fields['name']}: metadata, resources and links ({len(current['files'])} files)")
    if record.is_file():
        print('[OK] Package SHA-256 manifest matches')
    return current


def smoke(root):
    if importlib.util.find_spec('docx') is None:
        raise ValueError(f'python-docx missing: use this interpreter with -m pip install -r "{root / "requirements.txt"}"')
    content = {'blocks': [
        {'type': 'h1', 'text': '一、格式测试'},
        {'type': 'h4', 'text': '（1）测试标题'},
        {'type': 'p', 'text': '中文ABC 20%（括注30%）'},
        {'type': 'table', 'header': ['项目（说明）'], 'rows': [['测试值（20%）']]},
        {'type': 'pagebreak'}, {'type': 'p', 'text': '第二页'}]}
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    w = '{' + ns['w'] + '}'
    with tempfile.TemporaryDirectory(prefix='skill-smoke-') as tmp:
        temp = Path(tmp)
        source, output = temp / 'content.json', temp / 'sample.docx'
        source.write_text(json.dumps(content, ensure_ascii=False), encoding='utf-8')
        result = subprocess.run([sys.executable, '-X', 'utf8', str(root / 'scripts/build_docx.py'),
                                 str(source), str(output)], cwd=temp, capture_output=True,
                                text=True, encoding='utf-8', errors='replace')
        if result.returncode:
            raise ValueError(result.stdout + result.stderr)
        with zipfile.ZipFile(output) as archive:
            doc = ET.fromstring(archive.read('word/document.xml'))
            settings = ET.fromstring(archive.read('word/settings.xml'))
            if settings.find('w:evenAndOddHeaders', ns) is None:
                raise ValueError('Odd/even footers not enabled')
            refs = doc.findall('.//w:footerReference', ns)
            if {r.get(w + 'type') for r in refs} != {'default', 'even'}:
                raise ValueError('Both footer references are required')
            for run in doc.findall('.//w:tbl//w:r', ns):
                if run.find('w:t', ns) is not None and run.find('w:rPr/w:sz', ns).get(w + 'val') != '21':
                    raise ValueError('Table text is not 10.5pt')
            footers = [n for n in archive.namelist() if re.fullmatch(r'word/footer\d+\.xml', n)]
            alignments = set()
            for name in ['word/document.xml', *footers]:
                tree = ET.fromstring(archive.read(name))
                for fonts in tree.findall('.//w:rFonts', ns):
                    if any(fonts.get(w + slot) != 'Times New Roman' for slot in ('ascii', 'hAnsi', 'cs')):
                        raise ValueError('Western font normalization failed')
                if name in footers:
                    alignments.add(tree.find('.//w:jc', ns).get(w + 'val'))
                    if ''.join(t.text or '' for t in tree.findall('.//w:t', ns)) != '-1-':
                        raise ValueError('Footer text/field cache must be -1-')
                    if not any((t.text or '').strip() == 'PAGE' for t in tree.findall('.//w:instrText', ns)):
                        raise ValueError('Footer must contain a PAGE field')
                    for run in tree.findall('.//w:r', ns):
                        if run.find('w:rPr/w:sz', ns).get(w + 'val') != '28':
                            raise ValueError('Every footer run must be 14pt')
            if alignments != {'left', 'right'}:
                raise ValueError('Odd/even footer alignment mismatch')
    print('[OK] DOCX smoke test from a separate cwd; no fonts installed or host settings changed')
    print('[INFO] This checks package execution, not model invocation in a target client or visual font rendering')


def package(root, output_dir):
    record = check(root)
    output_dir = output_dir.resolve()
    if output_dir == root or root in output_dir.parents:
        raise ValueError('Output directory must be outside the skill folder')
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / (root.name + '.zip')
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in included_files(root):
            # Fixed timestamp keeps unchanged archives byte-for-byte reproducible.
            info = zipfile.ZipInfo(root.name + '/' + path.relative_to(root).as_posix(), (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, payload(path))
        info = zipfile.ZipInfo(root.name + '/skill-manifest.json', (2026, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        archive.writestr(info, json.dumps(record, ensure_ascii=False, indent=2).encode('utf-8'))
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    (output_dir / (output.name + '.sha256')).write_text(f'{digest}  {output.name}\n', encoding='utf-8')
    print(f'[OK] {output} ({output.stat().st_size} bytes) SHA256={digest}')
    return output


def install_root(args):
    if args.skills_dir:
        return Path(args.skills_dir).expanduser().resolve()
    if not args.agent:
        raise ValueError('Specify --agent or the client-confirmed --skills-dir')
    folder = DIRECTORIES[args.agent]
    if args.scope == 'project':
        if not args.project_dir:
            raise ValueError('--project-dir is required for project scope')
        if args.agent == 'qoderwork':
            raise ValueError('QoderWork: use its user directory or UI upload')
        if args.agent == 'trae-cn':
            folder = '.trae/skills'
        return (Path(args.project_dir).expanduser().resolve() / folder).resolve()
    if args.agent == 'kimi-code' and os.environ.get('KIMI_CODE_HOME'):
        return (Path(os.environ['KIMI_CODE_HOME']).expanduser() / 'skills').resolve()
    return (Path.home() / folder).resolve()


def install(root, destination_root, apply=False):
    record = check(root)
    destination_root = destination_root.resolve()
    destination = destination_root / root.name
    if destination.is_symlink() or destination.resolve() != destination:
        raise ValueError('Destination must not be a symlink or junction')
    if destination == root or root in destination.parents or destination in root.parents:
        raise ValueError('Source and destination must be separate folders')
    print(f'[PLAN] Install {root.name} -> {destination}')
    if not apply:
        print('[DRY RUN] Use --apply to write; UI-only clients should import the complete ZIP')
        return
    if destination.exists():
        # Backup stays outside skills/ discovery; never delete or move user files.
        backup_root = destination_root.parent / 'skill-backups'
        backup_root.mkdir(parents=True, exist_ok=True)
        backup = backup_root / (root.name + '-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
        shutil.copytree(destination, backup)
        print(f'[BACKUP] {backup}')
        source_files = set(record['files']) | {'skill-manifest.json'}
        extras = [p.relative_to(destination).as_posix() for p in included_files(destination)
                  if p.relative_to(destination).as_posix() not in source_files]
        if extras:
            raise ValueError('Existing skill has extra files; preserved with backup. Resolve these before updating: ' + ', '.join(extras))
    destination.mkdir(parents=True, exist_ok=True)
    for path in included_files(root):
        target = destination / path.relative_to(root)
        if target.exists() and target.is_symlink():
            raise ValueError(f'Refusing symlink target: {target}')
        if destination not in target.resolve().parents:
            raise ValueError(f'Target escapes skill folder: {target}')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload(path))
    (destination / 'skill-manifest.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    check(destination)
    print('[NEXT] Enable/reload the skill in the target client, then run the invocation acceptance prompts')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    check_parser = commands.add_parser('check')
    check_parser.add_argument('--smoke', action='store_true')
    package_parser = commands.add_parser('package')
    package_parser.add_argument('--output-dir', required=True, type=Path)
    install_parser = commands.add_parser('install')
    install_parser.add_argument('--agent', choices=DIRECTORIES)
    install_parser.add_argument('--scope', choices=('user', 'project'), default='user')
    install_parser.add_argument('--project-dir')
    install_parser.add_argument('--skills-dir', help='Exact skills directory confirmed in the target client')
    install_parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        if args.command == 'check':
            check(ROOT)
            if args.smoke:
                smoke(ROOT)
        elif args.command == 'package':
            package(ROOT, args.output_dir)
        else:
            install(ROOT, install_root(args), args.apply)
    except (ValueError, OSError, KeyError, ET.ParseError) as error:
        print(f'[FAIL] {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
