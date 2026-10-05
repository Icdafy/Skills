#!/usr/bin/env python3
"""Check, package or install this self-contained skill for any Agent Skills client.

Python 3.10+; stdlib only. ``check --smoke`` additionally needs python-docx.
No host configuration or font installation is performed. ``install`` is a dry
run unless ``--apply`` is specified.

One file serves every skill in the repository: the per-skill contract lives in
PROFILES below. Edit the canonical copy in gongsi-qingkuang and run
``python tools/check_shared_scripts.py --sync``.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fnmatch
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

# Strictest limits among supported clients: claude.ai upload caps the
# description at 200 characters (Kimi Code ~240, Codex/ZCode 1024) and ZCode
# truncates skill files above 100 KB.
NAME_PATTERN = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*')
MAX_NAME = 64
MAX_DESCRIPTION = 200
MAX_SKILL_MD_BYTES = 100 * 1024
ALLOWED_FRONTMATTER = {'name', 'description', 'license', 'compatibility', 'metadata', 'allowed-tools'}

# Exact historical source files retained at the maintainer's request.
# These bytes are checked, then excluded from install/package payloads.
# The repository index is authoritative; this physical copy supports standalone use.
RETAINED_SOURCE_FONT_SHA256 = {
    'gongsi-qingkuang/assets/fonts/simfang.ttf': 'fef7cf991b458cabd184b73378918d9d15429010e1d6c804f08d394395c3c3b4',
    'gongsi-qingkuang/assets/fonts/方正小标宋简体.ttf': '5b1d10a2543c436df12aa292b05bff59ce6dae1b5351a90892599a7b3fed5904',
    'gongsi-qingkuang/assets/fonts/楷体_GB2312.ttf': '99092cbb0df301625f46509e85854db8685556551742097ab3fbbc2e2ca0778b',
    'hangye-fenxi/assets/fonts/simfang.ttf': 'fef7cf991b458cabd184b73378918d9d15429010e1d6c804f08d394395c3c3b4',
    'hangye-fenxi/assets/fonts/方正小标宋简体.ttf': '5b1d10a2543c436df12aa292b05bff59ce6dae1b5351a90892599a7b3fed5904',
    'hangye-fenxi/assets/fonts/楷体_GB2312.ttf': '99092cbb0df301625f46509e85854db8685556551742097ab3fbbc2e2ca0778b',
    'meeting-minutes-pro/assets/fonts/simfang.ttf': 'fef7cf991b458cabd184b73378918d9d15429010e1d6c804f08d394395c3c3b4',
    'meeting-minutes-pro/assets/fonts/方正小标宋简体.ttf': '5b1d10a2543c436df12aa292b05bff59ce6dae1b5351a90892599a7b3fed5904',
    'meeting-minutes-pro/assets/fonts/楷体_GB2312.ttf': '99092cbb0df301625f46509e85854db8685556551742097ab3fbbc2e2ca0778b',
    'officialese-skill/assets/fonts/simfang.ttf': 'fef7cf991b458cabd184b73378918d9d15429010e1d6c804f08d394395c3c3b4',
    'officialese-skill/assets/fonts/方正小标宋简体.ttf': '5b1d10a2543c436df12aa292b05bff59ce6dae1b5351a90892599a7b3fed5904',
    'officialese-skill/assets/fonts/楷体_GB2312.ttf': '99092cbb0df301625f46509e85854db8685556551742097ab3fbbc2e2ca0778b',
    'yiti-skill/assets/fonts/simfang.ttf': 'fef7cf991b458cabd184b73378918d9d15429010e1d6c804f08d394395c3c3b4',
    'yiti-skill/assets/fonts/方正小标宋简体.ttf': '5b1d10a2543c436df12aa292b05bff59ce6dae1b5351a90892599a7b3fed5904',
    'yiti-skill/assets/fonts/楷体_GB2312.ttf': '99092cbb0df301625f46509e85854db8685556551742097ab3fbbc2e2ca0778b',
    'zhuying-yewu-fenxi/assets/fonts/FZXiaoBiaoSongJT.ttf': '5b1d10a2543c436df12aa292b05bff59ce6dae1b5351a90892599a7b3fed5904',
    'zhuying-yewu-fenxi/assets/fonts/KaiTi_GB2312.ttf': '99092cbb0df301625f46509e85854db8685556551742097ab3fbbc2e2ca0778b',
    'zhuying-yewu-fenxi/assets/fonts/simfang.ttf': 'fef7cf991b458cabd184b73378918d9d15429010e1d6c804f08d394395c3c3b4'
}

COMMON_REQUIRED = ('README.md', 'LICENSE', 'NOTICE', 'VERSION', 'SKILL.md', 'agents/openai.yaml', 'references/agent-compatibility.md',
                   'scripts/skill_portability.py')
INVESTMENT = {
    'required': ('requirements.txt', 'references/investment-logic-review.md',
                 'references/stage-template-workflow.md', 'references/template-early.md',
                 'references/template-mid-late.md', 'assets/templates/early.json',
                 'assets/templates/mid-late.json', 'scripts/build_docx.py',
                 'scripts/style_check.py', 'scripts/ensure_fonts.py', 'scripts/embed_fonts.py',
                 'scripts/docx_format_helpers.py', 'scripts/stage_template.py'),
    'smoke': 'investment', 'stage_templates': True, 'fonts': True,
}
PROFILES = {
    'hangye-fenxi': INVESTMENT,
    'zhuying-yewu-fenxi': INVESTMENT,
    'gongsi-qingkuang': INVESTMENT,
    'officialese-skill': {
        'required': ('requirements.txt', 'references/format-rules.md',
                     'references/writing-patterns.md', 'assets/templates/文件字体格式.doc',
                     'scripts/create_official_docx.py', 'scripts/embed_fonts.py',
                     'scripts/ensure_fonts.py'),
        'smoke': 'officialese', 'fonts': True,
    },
    'yiti-skill': {
        'required': ('requirements.txt', 'references/format-rules.md',
                     'references/writing-logic.md', 'references/exit-writing-logic.md',
                     'references/gold-examples.md', 'assets/examples/exit-yiti-spec.json',
                     'assets/templates/文件字体格式.doc', 'scripts/create_yiti_docx.py',
                     'scripts/check_yiti_text.py', 'scripts/embed_fonts.py',
                     'scripts/ensure_fonts.py'),
        'smoke': 'yiti', 'fonts': True,
    },
    'meeting-minutes-pro': {
        'required': ('references/evidence-and-release.md', 'references/format-and-output.md',
                     'references/runtime.md', 'references/platforms.md',
                     'references/architecture.md', 'glossary/README.md',
                     'scripts/bootstrap_runtime.py', 'scripts/transcribe.py',
                     'scripts/refine_transcript.py', 'scripts/create_minutes_docx.py',
                     'scripts/format_spec.py', 'scripts/quality_check.py', 'scripts/check_all.py',
                     'scripts/font_preflight.py', 'scripts/embed_fonts.py',
                     'scripts/docx_format_helpers.py', 'scripts/requirements-runtime.txt',
                     'scripts/requirements-funasr.txt', 'scripts/requirements-qwen.txt'),
        'smoke': 'minutes', 'fonts': True,
        # Project glossaries and banned phrases are user data: never packaged,
        # never treated as stale files, always carried across updates.
        'private': ('glossary/*',),
        'public': ('glossary/README.md', 'glossary/industry/*'),
    },
    'soe-post-investment-report': {
        'required': ('requirements.txt', 'references/template-contract.md',
                     'references/source-intake-and-fact-ledger.md',
                     'references/writing-and-compression.md', 'references/quality-gates.md',
                     'references/platform-compatibility.md', 'assets/report-spec.example.json',
                     'assets/reference-template.docx', 'scripts/build_report.py',
                     'scripts/validate_report.py', 'scripts/render_docx.py',
                     'scripts/font_preflight.py', 'scripts/source_inventory.py'),
        'smoke': 'soe', 'fonts': False, 'table_size': False,
        'exclude': ('assets/reference-render/*',),
    },
}

# Directory-installable clients: user-level folder (under the home directory),
# project-level folder (None = no project scope) and the environment variable
# that relocates the user-level configuration root.
AGENTS = {
    'claude-code': ('.claude/skills', '.claude/skills', 'CLAUDE_CONFIG_DIR',
                    'Claude Code CLI / 桌面版 Code / IDE 扩展'),
    'codex': ('.agents/skills', '.agents/skills', None,
              'OpenAI Codex CLI、IDE 扩展及 ChatGPT 桌面版中的 Codex'),
    'chatgpt': ('.agents/skills', '.agents/skills', None,
                'ChatGPT 桌面版独立技能（与 Codex 共用 ~/.agents/skills）'),
    'codex-legacy': ('.codex/skills', None, 'CODEX_HOME', '仍读取 $CODEX_HOME/skills 的旧版 Codex'),
    'kimi-code': ('.kimi-code/skills', '.kimi-code/skills', 'KIMI_CODE_HOME',
                  'Kimi Code CLI（Kimi Work 以其为内核）'),
    'qoder-cli': ('.qoder/skills', '.qoder/skills', None, 'Qoder CLI'),
    'qoder-cn': ('.lingma/skills', '.lingma/skills', None, 'Qoder CN（通义灵码）IDE'),
    'qoderwork': ('.qoderwork/skills', None, None, 'QoderWork'),
    'trae': ('.trae/skills', '.trae/skills', None, 'TRAE 国际版'),
    'trae-cn': ('.trae-cn/skills', '.trae/skills', None, 'TRAE 中国版 / TraeCode'),
    'workbuddy': ('.workbuddy/skills', '.workbuddy/skills', None, '腾讯 WorkBuddy'),
    'codebuddy': ('.codebuddy/skills', '.codebuddy/skills', None, '腾讯 CodeBuddy IDE / CLI'),
    'zcode': ('.zcode/skills', None, None, '智谱 ZCode（GLM）'),
    'openclaw': ('.openclaw/skills', 'skills', 'OPENCLAW_STATE_DIR',
                 'OpenClaw / 智谱 AutoClaw（澳龙）'),
    'agents': ('.agents/skills', '.agents/skills', None,
               '通用 Agent Skills 目录（Codex、ChatGPT 桌面版、Kimi Code、OpenClaw 等共读）'),
}
# Configuration folders whose presence suggests the client is installed (--detect).
DETECT = {
    'claude-code': '.claude', 'codex': '.codex', 'kimi-code': '.kimi-code', 'qoder-cli': '.qoder',
    'qoder-cn': '.lingma', 'qoderwork': '.qoderwork', 'trae': '.trae', 'trae-cn': '.trae-cn',
    'workbuddy': '.workbuddy', 'codebuddy': '.codebuddy', 'zcode': '.zcode', 'openclaw': '.openclaw',
}
# Clients installed through their own interface; no configuration folder is assumed.
UI_CLIENTS = (
    ('Claude 网页/桌面 Chat', '自定义 → 技能 → “+” → 上传技能，选择本技能 ZIP；需开启代码执行'),
    ('ChatGPT（Business/Enterprise/Edu）', '技能 → 创建 → 从电脑上传，选择本技能 ZIP；等待安全扫描'),
    ('豆包电脑版（工作模式）', '插件·技能·伙伴 → 技能 → “+ 添加” → 上传技能，拖入 ZIP 或技能文件夹'),
    ('WorkBuddy', '技能 → 添加技能 → 上传技能，导入 ZIP 后在已安装列表开启'),
    ('Kimi Work', 'Work 模式 → 技能 → 上传本地技能'),
    ('Qoder 桌面版', 'Extensions → Skills → Add Skills → Upload Skill'),
    ('TRAE / TraeCode IDE', '设置 → 技能与命令 → 创建 → 导入 ZIP（全局或项目）'),
    ('智谱 ZCode', 'Settings → Skills → 右上角导入图标，选“复制”模式'),
    ('OpenClaw / AutoClaw 网关', 'Plugins → Skills → 导入 ZIP；受单文件 1 MiB、总量 8 MiB 限制，'
                                 '含字体的技能改用 --agent openclaw 目录安装'),
)

SKIP_PARTS = {'.git', '__pycache__', '.venv', 'venv', 'node_modules', '.pytest_cache',
              '.mypy_cache', '.ruff_cache', 'dist', 'skill-backups'}
SKIP_NAMES = ('*.pyc', '*.pyo', '.DS_Store', 'Thumbs.db', '~$*', '*.swp', '*~')
TEXT_SUFFIXES = ('.md', '.py', '.json', '.yaml', '.yml', '.txt', '.ps1')
FIXED_TIME = (2026, 1, 1, 0, 0, 0)


def skill_name(root):
    """Identity comes from SKILL.md: plugin caches store skills under version folders."""
    try:
        return frontmatter(root).get('name', '').strip('"\'') or root.name
    except (OSError, ValueError):
        return root.name


def profile(root):
    return PROFILES.get(skill_name(root), {})


def payload(path):
    """Normalize text to LF so Git autocrlf cannot make release ZIPs stale."""
    data = path.read_bytes()
    if path.suffix.lower() in TEXT_SUFFIXES or path.name in {'VERSION', 'LICENSE', 'NOTICE'}:
        return data.replace(b'\r\n', b'\n')
    return data


def _matches(rel, patterns):
    return any(fnmatch.fnmatchcase(rel, pattern) for pattern in patterns)


def is_private(root, rel):
    """User data (e.g. project glossaries) that stays out of packages and survives updates."""
    rules = profile(root)
    return _matches(rel, rules.get('private', ())) and not _matches(rel, rules.get('public', ()))


def included_files(root):
    rules = profile(root)
    name = skill_name(root)
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError(f'Symlinks are not portable: {path}')
        rel = path.relative_to(root)
        posix = rel.as_posix()
        if (not path.is_file() or set(rel.parts) & SKIP_PARTS
                or any(fnmatch.fnmatch(path.name, pattern) for pattern in SKIP_NAMES)
                or posix == 'skill-manifest.json' or _matches(posix, rules.get('exclude', ()))
                or is_private(root, posix)):
            continue
        retained_key = name + '/' + posix
        expected_font = RETAINED_SOURCE_FONT_SHA256.get(retained_key)
        if expected_font is not None:
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected_font:
                raise ValueError('Retained source font changed: ' + retained_key)
            continue
        yield path


def frontmatter(root):
    raw = (root / 'SKILL.md').read_text(encoding='utf-8-sig')
    front = re.match(r'\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)', raw, re.S)
    if not front:
        raise ValueError('SKILL.md must start with YAML frontmatter')
    fields = {}
    for line in front[1].splitlines():
        if not line.strip() or line[0] in ' \t#':
            continue
        key, separator, value = line.partition(':')
        if not separator:
            raise ValueError(f'Frontmatter line is not "key: value": {line[:40]}')
        fields[key.strip()] = value.strip()
    return fields


def metadata(root):
    fields = frontmatter(root)
    unknown = set(fields) - ALLOWED_FRONTMATTER
    if unknown:
        raise ValueError('Frontmatter keys rejected by strict clients: ' + ', '.join(sorted(unknown)))
    name = fields.get('name', '').strip('"\'')
    if not NAME_PATTERN.fullmatch(name) or len(name) > MAX_NAME:
        raise ValueError('name must be lowercase letters, digits and hyphens, <= 64 characters')
    if name not in PROFILES:
        raise ValueError(f'No portability profile for {name}')
    if 'anthropic' in name or 'claude' in name:
        raise ValueError('name must not contain reserved words')
    description = fields.get('description', '')
    quoted = len(description) >= 2 and description[0] == description[-1] and description[0] in '"\''
    if quoted:
        description = description[1:-1]
    elif description[:1] in tuple('[]{}&*!|>\'"%@`#,?:-') or ': ' in description or ' #' in description:
        raise ValueError('Unquoted description is not plain YAML; rephrase or quote it')
    if not 1 <= len(description) <= MAX_DESCRIPTION:
        raise ValueError(f'description must be one line of 1-{MAX_DESCRIPTION} characters '
                         f'(currently {len(description)}); claude.ai rejects longer uploads')
    if '<' in description or '>' in description:
        raise ValueError('description must not contain XML-like angle brackets')
    return {'name': name, 'description': description}


def manifest(root):
    return {'name': metadata(root)['name'], 'format': 1,
            'version': (root / 'VERSION').read_text(encoding='utf-8').strip(),
            'files': {p.relative_to(root).as_posix(): hashlib.sha256(payload(p)).hexdigest()
                      for p in included_files(root)}}


def _check_stage_templates(root, name):
    for stage in ('early', 'mid-late'):
        template = json.loads((root / 'assets/templates' / (stage + '.json')).read_text('utf-8'))
        if template.get('stage') != stage or template.get('skill') != name:
            raise ValueError('Stage template belongs to a different skill or stage')
        source_ids = [h['id'] for h in template['source_headings']]
        mapped_ids = [source for node in template['nodes'] for source in node['sources']]
        if source_ids != mapped_ids or len(source_ids) != len(set(source_ids)):
            raise ValueError('Stage template has missing, repeated or reordered source headings')


def check(root):
    fields = metadata(root)
    rules = PROFILES[fields['name']]
    skill_md = root / 'SKILL.md'
    forbidden = [p.relative_to(root).as_posix() for p in included_files(root)
                 if p.suffix.lower() in {'.ttf', '.otf', '.ttc', '.woff', '.woff2', '.odttf'}]
    if forbidden:
        raise ValueError('Restricted font distribution: ' + ', '.join(forbidden))
    if rules.get('fonts') and not (root / 'scripts/local_fonts.py').is_file():
        raise ValueError('Missing resources: scripts/local_fonts.py')
    if skill_md.stat().st_size > MAX_SKILL_MD_BYTES:
        raise ValueError('SKILL.md exceeds 100 KB; move detail into references/')
    missing = [p for p in COMMON_REQUIRED + rules['required'] if not (root / p).is_file()]
    if missing:
        raise ValueError('Missing resources: ' + ', '.join(missing))
    if not re.search(r'(?m)^\s*display_name:\s*\S', (root / 'agents/openai.yaml').read_text('utf-8-sig')):
        raise ValueError('agents/openai.yaml needs interface.display_name')
    if rules.get('stage_templates'):
        _check_stage_templates(root, fields['name'])
    # Resource paths named in SKILL.md must ship with the package.
    skill_text = re.sub(r'<[^>\s]+>/|\$\{?\w+\}?/', ' ', skill_md.read_text(encoding='utf-8-sig'))
    for target in set(re.findall(r'(?<![\w./-])((?:scripts|references|assets|agents)/[^\s`\'"()\[\]<>*{}$，。；：、）]+)', skill_text)):
        target = target.rstrip('.,;:')
        if not (root / target).exists():
            raise ValueError(f'SKILL.md names a missing resource: {target}')
    # Markdown links resolve against their containing file, never the task cwd.
    for path in included_files(root):
        if path.suffix != '.md':
            continue
        for target in re.findall(r'\]\(([^)\s]+)\)', path.read_text(encoding='utf-8-sig')):
            target = target.split('#')[0]
            if not target or '://' in target or target.startswith('mailto:'):
                continue
            resolved = (path.parent / target).resolve()
            if root.resolve() not in resolved.parents and resolved != root.resolve():
                raise ValueError(f'Link leaves the skill folder: {path.relative_to(root)} -> {target}')
            if not resolved.exists():
                raise ValueError(f'Broken relative link: {path.relative_to(root)} -> {target}')
    record = root / 'skill-manifest.json'
    current = manifest(root)
    if record.is_file() and json.loads(record.read_text(encoding='utf-8')) != current:
        raise ValueError('Package checksum mismatch; restore the complete matching package')
    print(f"[OK] {fields['name']}: metadata, resources and links ({len(current['files'])} files)")
    if root.name != fields['name']:
        print(f'[INFO] Folder "{root.name}" differs from the skill name (normal in plugin caches); '
              'installs and ZIPs always use the skill name')
    if record.is_file():
        print('[OK] Package SHA-256 manifest matches')
    if rules.get('fonts'):
        print('[INFO] Single-skill packages/install payloads exclude fonts; historical source fonts are hash-checked. Embedding uses installed licensed fonts or ICDAFY_FONT_DIR. Missing fonts are reported by the generator/preflight')
    return current


W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
NS = {'w': W[1:-1]}


def check_docx(output, table_size=True):
    """Assertions shared by every official-document generator in this repository."""
    with zipfile.ZipFile(output) as archive:
        doc = ET.fromstring(archive.read('word/document.xml'))
        settings = ET.fromstring(archive.read('word/settings.xml'))
        if settings.find('w:evenAndOddHeaders', NS) is None:
            raise ValueError('Odd/even footers not enabled')
        refs = doc.findall('.//w:footerReference', NS)
        if not {'default', 'even'} <= {r.get(W + 'type') for r in refs}:
            raise ValueError('Both footer references are required')
        if table_size:
            for run in doc.findall('.//w:tbl//w:r', NS):
                if run.find('w:t', NS) is not None and run.find('w:rPr/w:sz', NS).get(W + 'val') != '21':
                    raise ValueError('Table text is not 10.5pt')
        for fonts in doc.findall('.//w:rFonts', NS):
            if any(fonts.get(W + slot) != 'Times New Roman' for slot in ('ascii', 'hAnsi', 'cs')):
                raise ValueError('Western font normalization failed')
        footers = [n for n in archive.namelist() if re.fullmatch(r'word/footer\d+\.xml', n)]
        alignments = set()
        for name in footers:
            tree = ET.fromstring(archive.read(name))
            # 页脚 -1- 不参与 Times New Roman 统一，四个字体槽均为宋体。
            for fonts in tree.findall('.//w:rFonts', NS):
                if any(fonts.get(W + slot) != '宋体' for slot in ('ascii', 'hAnsi', 'cs', 'eastAsia')):
                    raise ValueError('Footer page number must be 宋体 in every font slot')
            alignments.add(tree.find('.//w:jc', NS).get(W + 'val'))
            if ''.join(t.text or '' for t in tree.findall('.//w:t', NS)) != '-1-':
                raise ValueError('Footer text/field cache must be -1-')
            fields = [(t.text or '').strip() for t in tree.findall('.//w:instrText', NS)]
            fields += [(f.get(W + 'instr') or '').strip() for f in tree.findall('.//w:fldSimple', NS)]
            if 'PAGE' not in fields:
                raise ValueError('Footer must contain a PAGE field')
            for run in tree.findall('.//w:r', NS):
                if run.find('w:rPr/w:sz', NS).get(W + 'val') != '28':
                    raise ValueError('Every footer run must be 14pt')
        if alignments != {'left', 'right'}:
            raise ValueError('Odd/even footer alignment mismatch')


def _run(root, cwd, script, *args, ok_codes=(0,)):
    result = subprocess.run([sys.executable, '-X', 'utf8', str(root / 'scripts' / script), *map(str, args)],
                            cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if result.returncode not in ok_codes:
        raise ValueError(f'{script} failed ({result.returncode}): {result.stdout}{result.stderr}'[-2000:])
    return result


def _smoke_investment(root, temp):
    content = {'blocks': [
        {'type': 'h1', 'text': '一、格式测试'},
        {'type': 'h4', 'text': '（1）测试标题'},
        {'type': 'p', 'text': '中文ABC 20%（括注30%）'},
        {'type': 'table', 'header': ['项目（说明）'], 'rows': [['测试值（20%）']]},
        {'type': 'pagebreak'}, {'type': 'p', 'text': '第二页'}]}
    source = temp / 'content.json'
    source.write_text(json.dumps(content, ensure_ascii=False), encoding='utf-8')
    _run(root, temp, 'build_docx.py', source, temp / 'sample.docx')
    return temp / 'sample.docx'


def _smoke_officialese(root, temp):
    spec = {'title': '关于开展格式测试的通知', 'recipient': '各部门：',
            'body': ['为验证公文生成器，现将有关事项通知如下（测试20%）。',
                     {'table': [['项目（说明）', '数值'], ['测试值（20%）', '100']]}],
            'issuer': '测试公司', 'date': '2026年9月27日'}
    source = temp / 'spec.json'
    source.write_text(json.dumps(spec, ensure_ascii=False), encoding='utf-8')
    _run(root, temp, 'create_official_docx.py', '--input', source, temp / 'sample.docx')
    return temp / 'sample.docx'


def _smoke_yiti(root, temp):
    spec = root / 'assets/examples/exit-yiti-spec.json'
    _run(root, temp, 'check_yiti_text.py', spec)
    _run(root, temp, 'create_yiti_docx.py', spec, temp / 'sample.docx')
    return temp / 'sample.docx'


def _smoke_minutes(root, temp):
    source = temp / 'minutes.txt'
    source.write_text('某公司项目沟通会议纪要\n\n　　一、会议基本情况\n　　会议时间：2026年9月1日。\n'
                      '　　会议地点：公司会议室。\n\n　　二、会议主要内容\n'
                      '　　公司介绍2025年营业收入为1.2亿元，同比增长20%（经审计口径）。\n', encoding='utf-8')
    _run(root, temp, 'create_minutes_docx.py', '--input', source, '--output', temp / 'sample.docx',
         '--mode', 'minutes')
    return temp / 'sample.docx'


def _smoke_soe(root, temp):
    spec = root / 'assets/report-spec.example.json'
    _run(root, temp, 'build_report.py', spec, temp / 'sample.docx', '--template-mode')
    _run(root, temp, 'validate_report.py', '--spec', spec, '--docx', temp / 'sample.docx', '--template-mode')
    return temp / 'sample.docx'


SMOKES = {'investment': _smoke_investment, 'officialese': _smoke_officialese, 'yiti': _smoke_yiti,
          'minutes': _smoke_minutes, 'soe': _smoke_soe}


def smoke(root):
    if importlib.util.find_spec('docx') is None:
        raise ValueError(f'python-docx missing: use this interpreter with -m pip install python-docx')
    rules = profile(root)
    with tempfile.TemporaryDirectory(prefix='skill-smoke-') as tmp:
        output = SMOKES[rules['smoke']](root, Path(tmp))
        check_docx(output, table_size=rules.get('table_size', True))
    print('[OK] DOCX smoke test from a separate cwd; no fonts installed or host settings changed')
    print('[INFO] This checks package execution, not model invocation in a target client or visual font rendering')


def _zip_info(name):
    # Fixed timestamp keeps unchanged archives byte-for-byte reproducible.
    info = zipfile.ZipInfo(name, FIXED_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    return info


def package(root, output_dir):
    record = check(root)
    output_dir = output_dir.resolve()
    if output_dir == root.resolve() or root.resolve() in output_dir.parents:
        raise ValueError('Output directory must be outside the skill folder')
    output_dir.mkdir(parents=True, exist_ok=True)
    name = record['name']
    output = output_dir / (name + '.zip')
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in included_files(root):
            archive.writestr(_zip_info(name + '/' + path.relative_to(root).as_posix()), payload(path))
        archive.writestr(_zip_info(name + '/skill-manifest.json'),
                         json.dumps(record, ensure_ascii=False, indent=2).encode('utf-8'))
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    (output_dir / (output.name + '.sha256')).write_text(f'{digest}  {output.name}\n', encoding='utf-8')
    print(f'[OK] {output} ({output.stat().st_size} bytes) SHA256={digest}')
    return output


def agent_root(agent, scope='user', project_dir=None):
    user, project, env, _label = AGENTS[agent]
    if scope == 'project':
        if not project_dir:
            raise ValueError('--project-dir is required for project scope')
        if project is None:
            raise ValueError(f'{agent} has no project-level skills folder; use user scope or its UI')
        return (Path(project_dir).expanduser().resolve() / project).resolve()
    if env and os.environ.get(env):
        return (Path(os.environ[env]).expanduser() / 'skills').resolve()
    return (Path.home() / user).resolve()


def install_roots(args):
    if args.skills_dir:
        return [Path(args.skills_dir).expanduser().resolve()]
    agents = list(args.agent or [])
    if args.detect:
        agents += [agent for agent, folder in DETECT.items() if (Path.home() / folder).is_dir()]
    if not agents:
        raise ValueError('Specify --agent, --detect or the client-confirmed --skills-dir')
    roots = []
    for agent in agents:
        root = agent_root(agent, args.scope, args.project_dir)
        if root not in roots:  # codex, chatgpt and agents share ~/.agents/skills
            roots.append(root)
    return roots


def install(root, destination_root, apply=False, replace=False):
    record = check(root)
    destination_root = destination_root.resolve()
    name = record['name']
    destination = destination_root / name
    if destination.is_symlink() or destination.resolve() != destination:
        raise ValueError('Destination must not be a symlink or junction')
    if destination == root.resolve() or root.resolve() in destination.parents or destination in root.resolve().parents:
        raise ValueError('Source and destination must be separate folders')
    print(f'[PLAN] Install {name} -> {destination}')
    if not apply:
        print('[DRY RUN] Use --apply to write; UI-only clients should import the complete ZIP')
        return destination
    backup = None
    if destination.exists():
        # Backup stays outside skills/ discovery; nothing is deleted.
        backup_root = destination_root.parent / 'skill-backups'
        backup_root.mkdir(parents=True, exist_ok=True)
        backup = backup_root / (name + '-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
        source_files = set(record['files']) | {'skill-manifest.json'}
        extras = [p.relative_to(destination).as_posix() for p in included_files(destination)
                  if p.relative_to(destination).as_posix() not in source_files]
        if extras and not replace:
            shutil.copytree(destination, backup)
            print(f'[BACKUP] {backup}')
            raise ValueError('Existing skill has extra files; preserved with backup. Resolve these, '
                             'or rerun with --replace to move the old folder aside: ' + ', '.join(extras))
        if replace:
            destination.rename(backup)
        else:
            shutil.copytree(destination, backup)
        print(f'[BACKUP] {backup}')
    destination.mkdir(parents=True, exist_ok=True)
    for path in included_files(root):
        target = destination / path.relative_to(root)
        if target.exists() and target.is_symlink():
            raise ValueError(f'Refusing symlink target: {target}')
        if destination not in target.resolve().parents:
            raise ValueError(f'Target escapes skill folder: {target}')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload(path))
    if replace and backup is not None:
        # Carry user data (e.g. project glossaries) over from the moved-aside copy.
        for path in sorted(backup.rglob('*')):
            rel = path.relative_to(backup).as_posix()
            if path.is_file() and not path.is_symlink() and is_private(root, rel):
                target = destination / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
    (destination / 'skill-manifest.json').write_text(json.dumps(record, ensure_ascii=False, indent=2),
                                                     encoding='utf-8')
    check(destination)
    print('[NEXT] Enable/reload the skill in the target client, then run the invocation acceptance prompts')
    return destination


def list_agents():
    print('目录安装（--agent）：')
    for agent, (user, project, env, label) in AGENTS.items():
        scope = f'；项目级 <项目>/{project}' if project else ''
        override = f'；设置 {env} 时为 ${env}/skills' if env else ''
        print(f'  {agent:<13} ~/{user}{scope}{override}  —  {label}')
    print('界面上传（先用 package 生成 ZIP，或下载仓库 distributions/ 中的 ZIP）：')
    for client, route in UI_CLIENTS:
        print(f'  {client}：{route}')


def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors='replace')
        except (AttributeError, OSError):
            pass
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest='command', required=True)
    check_parser = commands.add_parser('check', help='verify metadata, resources and checksums')
    check_parser.add_argument('--smoke', action='store_true', help='also generate and inspect a sample DOCX')
    package_parser = commands.add_parser('package', help='build a reproducible ZIP for UI upload')
    package_parser.add_argument('--output-dir', required=True, type=Path)
    install_parser = commands.add_parser('install', help='copy into a client skills folder')
    install_parser.add_argument('--agent', choices=AGENTS, action='append',
                                help='repeat for several clients; see the "agents" command')
    install_parser.add_argument('--detect', action='store_true',
                                help='also target every client whose configuration folder exists')
    install_parser.add_argument('--scope', choices=('user', 'project'), default='user')
    install_parser.add_argument('--project-dir')
    install_parser.add_argument('--skills-dir', help='Exact skills directory confirmed in the target client')
    install_parser.add_argument('--replace', action='store_true',
                                help='move an existing copy to skill-backups/ instead of stopping on extra files')
    install_parser.add_argument('--apply', action='store_true')
    commands.add_parser('agents', help='list supported clients, folders and upload routes')
    args = parser.parse_args()
    try:
        if args.command == 'check':
            check(ROOT)
            if args.smoke:
                smoke(ROOT)
        elif args.command == 'package':
            package(ROOT, args.output_dir)
        elif args.command == 'agents':
            list_agents()
        else:
            for destination_root in install_roots(args):
                install(ROOT, destination_root, args.apply, args.replace)
    except (ValueError, OSError, KeyError, ET.ParseError) as error:
        print(f'[FAIL] {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
