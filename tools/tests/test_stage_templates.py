"""Behavioral checks for stage routing, source coverage and fixed heading output."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
import xml.etree.ElementTree as ET

REPO = Path(__file__).resolve().parents[2]
NAMES = ('hangye-fenxi', 'zhuying-yewu-fenxi', 'gongsi-qingkuang')
spec = importlib.util.spec_from_file_location('stage_templates_test', REPO / NAMES[2] / 'scripts/stage_template.py')
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)


def filled(root, selected):
    template = stage.load_template(selected, root)
    bindings = stage.binding_example(template)
    for key, value in bindings.items():
        if isinstance(value, list):
            bindings[key] = [{k: '虚构测试' + k for k in value[0]} for _ in range(2)]
        else:
            bindings[key] = '虚构测试' + key
    content = stage.initialize(selected, bindings, root)
    for block in content['blocks']:
        if block['type'] == 'p':
            block['text'] = '测试材料仅用于程序回归，不代表实际项目结论。'
    return content


class StageTemplateTests(unittest.TestCase):
    def test_all_original_headings_have_template_mappings(self):
        counts = {'hangye-fenxi': (15, 12), 'zhuying-yewu-fenxi': (28, 40), 'gongsi-qingkuang': (30, 95)}
        for name in NAMES:
            for selected, count in zip(('early', 'mid-late'), counts[name]):
                with self.subTest(name=name, stage=selected):
                    template = stage.load_template(selected, REPO / name)
                    sources = template['source_headings']
                    self.assertEqual(len(sources), count)
                    self.assertEqual(len(template['source']['sha256']), 64)
                    mapped = [s for n in template['nodes'] for s in n['sources']]
                    self.assertEqual(mapped, [h['id'] for h in sources])
                    self.assertEqual(len(mapped), len(set(mapped)))
                    self.assertTrue(all(h['text'].strip() and h['level'] in range(1, 5) for h in sources))
        mid = stage.load_template('mid-late', REPO / NAMES[2])
        self.assertEqual([h['text'] for h in mid['source_headings'] if h['level'] == 1],
                         ['二、公司情况介绍', '五、拟投资主体相关情况'])
        self.assertIn('（1）2015 年 4 月，西安翔舟航空技术有限公司（以下简称“翔舟航空”）设立',
                      [h['text'] for h in mid['source_headings']])
        self.assertEqual(mid['source_headings'][-1]['text'], '（2）北交所标准')

    def test_all_six_templates_accept_filled_sections(self):
        for name in NAMES:
            for selected in ('early', 'mid-late'):
                with self.subTest(name=name, stage=selected):
                    root = REPO / name
                    self.assertGreater(stage.validate(filled(root, selected), root), 0)

    def test_no_implicit_stage_and_no_unfilled_delivery(self):
        root = REPO / NAMES[2]
        for bad in (None, '', 'A轮', 'auto'):
            with self.subTest(stage=bad), self.assertRaises(ValueError):
                stage.initialize(bad, root=root)
        with self.assertRaisesRegex(ValueError, '占位'):
            stage.validate(stage.initialize('early', root=root), root)
        with self.assertRaisesRegex(ValueError, 'report_template'):
            stage.validate({'blocks': []}, root)

    def test_title_deletion_reordering_renaming_and_wrong_stage_are_rejected(self):
        root = REPO / NAMES[0]
        content = filled(root, 'early')
        for action in ('delete', 'rename', 'reorder', 'insert', 'stage', 'skill', 'empty'):
            bad = copy.deepcopy(content)
            if action == 'delete': bad['blocks'].pop(0)
            if action == 'rename': bad['blocks'][0]['text'] = '二、自拟标题'
            if action == 'reorder': bad['blocks'][0], bad['blocks'][1] = bad['blocks'][1], bad['blocks'][0]
            if action == 'insert': bad['blocks'].append({'type': 'h5', 'text': '自增标题'})
            if action == 'stage': bad['report_template']['stage'] = 'mid-late'
            if action == 'skill': bad['report_template']['skill'] = NAMES[1]
            if action == 'empty': bad['blocks'][-1]['text'] = ''
            with self.subTest(action=action), self.assertRaises(ValueError):
                stage.validate(bad, root)

    def test_repeat_counts_follow_current_company_without_changing_generic_titles(self):
        root = REPO / NAMES[2]
        content = filled(root, 'early')
        bindings = content['report_template']['bindings']
        bindings['team'] = [{'name': '虚构甲', 'role': '总经理'}, {'name': '虚构乙', 'role': '总工程师'}, {'name': '虚构丙', 'role': '财务负责人'}]
        bindings['financial_issues'] = []
        draft = stage.initialize('early', bindings, root)
        for block in draft['blocks']:
            if block['type'] == 'p':block['text'] = '此处为虚构核验事实。'
        stage.validate(draft, root)
        self.assertIn('（3）虚构丙，财务负责人', [b['text'] for b in draft['blocks']])
        self.assertNotIn('（1）持续亏损', [b['text'] for b in draft['blocks']])
        bindings['team'] = []
        with self.assertRaisesRegex(ValueError, '数量不足'):
            stage.initialize('early', bindings, root)

    def test_bindings_reject_hidden_headings_and_extra_fields(self):
        root = REPO / NAMES[0]
        bindings = filled(root, 'early')['report_template']['bindings']
        for value in ('正文\n新增标题', '', ['非法列表']):
            invalid = dict(bindings, necessity_heading=value)
            with self.assertRaises(ValueError):
                stage.initialize('early', invalid, root)
        with self.assertRaises(ValueError):
            stage.initialize('early', dict(bindings, extra='新标题'), root)

    def test_cli_from_chinese_space_path_requires_stage(self):
        script = REPO / NAMES[0] / 'scripts/stage_template.py'
        with tempfile.TemporaryDirectory(prefix='阶段 模板 ') as tmp:
            out = Path(tmp) / '工作 稿.json'
            missing = subprocess.run([sys.executable, str(script), 'init', '--output', str(out)], cwd=tmp, capture_output=True)
            self.assertNotEqual(missing.returncode, 0)
            self.assertFalse(out.exists())
            done = subprocess.run([sys.executable, '-X', 'utf8', str(script), 'init', '--stage', '中后期', '--output', str(out)], cwd=tmp, capture_output=True)
            self.assertEqual(done.returncode, 0, done.stderr)
            data = json.loads(out.read_text('utf8'))
            self.assertEqual(data['blocks'][0]['text'], '三、所属行业分析')
            check = subprocess.run([sys.executable, '-X', 'utf8', str(script), 'check', str(out)], cwd=tmp, capture_output=True)
            self.assertNotEqual(check.returncode, 0)

    def test_docx_renderer_rejects_template_drift_before_writing(self):
        root = REPO / NAMES[0]
        invalid = filled(root, 'early')
        invalid['blocks'][0]['text'] = '错误标题'
        with tempfile.TemporaryDirectory() as tmp:
            source, target = Path(tmp) / 'content.json', Path(tmp) / 'output.docx'
            source.write_text(json.dumps(invalid, ensure_ascii=False), encoding='utf8')
            result = subprocess.run([sys.executable, '-X', 'utf8', str(root / 'scripts/build_docx.py'), str(source), str(target)], cwd=tmp, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(target.exists())

    def test_all_six_templates_preserve_headings_in_saved_docx(self):
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        for name in NAMES:
            for selected in ('early', 'mid-late'):
                with self.subTest(skill=name, stage=selected), tempfile.TemporaryDirectory() as tmp:
                    root = REPO / name
                    content = filled(root, selected)
                    source, target = Path(tmp) / 'content.json', Path(tmp) / 'report.docx'
                    source.write_text(json.dumps(content, ensure_ascii=False), encoding='utf8')
                    run = subprocess.run([sys.executable, '-X', 'utf8', str(root / 'scripts/build_docx.py'), str(source), str(target)], cwd=tmp, capture_output=True)
                    self.assertEqual(run.returncode, 0, run.stderr)
                    with zipfile.ZipFile(target) as archive:
                        xml = ET.fromstring(archive.read('word/document.xml'))
                    actual = [''.join(t.text or '' for t in p.findall('.//w:t', ns))
                              for p in xml.findall('.//w:body/w:p', ns)
                              if p.find('w:pPr/w:outlineLvl', ns) is not None]
                    expected = [b['text'] for b in content['blocks'] if b['type'].startswith('h')]
                    self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
