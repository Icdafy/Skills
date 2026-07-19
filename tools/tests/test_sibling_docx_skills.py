#!/usr/bin/env python3
"""五个公文 DOCX 技能的仓库级回归测试。

这些技能自包含、可独立分发，但**测试是开发期资产、不随分发**，所以不把同一份
测试复制五遍塞进各技能，而是集中在仓库级统一覆盖。

各生成器一律以**子进程调用其 CLI**：既贴近真实调用路径，也避免多个技能的
`embed_fonts` 在同一进程内因 `sys.modules` 同名而互相串味（那样会误用别的技能
的 assets/fonts，测试就失去意义）。

运行：
    python -m unittest discover -s tools/tests
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SKILLS = ("gongsi-qingkuang", "hangye-fenxi", "zhuying-yewu-fenxi",
          "officialese-skill", "yiti-skill")

try:
    import docx  # noqa: F401
    HAS_DOCX = True
except ImportError:  # pragma: no cover
    HAS_DOCX = False


def load_embed_fonts(skill: str):
    """按技能加载其自带的 embed_fonts（模块名带技能后缀，避免互相覆盖）。"""
    path = REPO / skill / "scripts" / "embed_fonts.py"
    name = "embed_fonts_" + skill.replace("-", "_")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# 各技能的 CLI 调用方式与一份内容较丰富的样例（含表格、分页、附件等）。
def _trio_cmd(skill: str, out: Path, tmp: Path) -> list[str]:
    content = {
        "summary": "公司成立于2019年，主营 5G 模组。\n注册资本 3000 万元。",
        "blocks": [
            {"type": "h1", "text": "一、公司基本情况"},
            {"type": "h2", "text": "（一）工商信息"},
            {"type": "p", "text": "统一社会信用代码 91330100X，注册资本 3000 万元。"},
            {"type": "h3", "text": "1.股权结构"},
            {"type": "table", "header": ["股东", "持股比例"],
             "rows": [[f"股东{i}", f"{i}%"] for i in range(1, 30)]},
            {"type": "tnote", "text": "单位：万元", "align": "right"},
            {"type": "pagebreak"},
            {"type": "h2", "text": "（二）核心团队"},
            {"type": "bullet", "items": ["张某某（总经理）", "李某某（CTO）"]},
        ],
    }
    spec = tmp / "content.json"
    spec.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")
    return [sys.executable, str(REPO / skill / "scripts" / "build_docx.py"),
            str(spec), str(out)]


def _officialese_cmd(skill: str, out: Path, tmp: Path) -> list[str]:
    return [sys.executable,
            str(REPO / skill / "scripts" / "create_official_docx.py"), str(out),
            "--title", "关于2026年5G项目管理的通知", "--subtitle", "综合办公室",
            "--recipient", "各部门：",
            "--body", "2026年投入 3000 万元，由 COO 牵头，A4 幅面归档。",
            "--attachment", "附件一", "--attachment", "附件二",
            "--issuer", "某某公司", "--date", "2026年7月19日"]


def _yiti_cmd(skill: str, out: Path, tmp: Path) -> list[str]:
    spec = tmp / "yiti.json"
    spec.write_text(json.dumps({
        "title": "审议关于某某公司2026年第一次临时股东会参会及表决事项的议题",
        "submit_line": "提交部门/子公司：投管公司", "recipient": "投委会：",
        "intro": "某某公司为参股企业，现将有关事项报请审议，具体如下：",
        "page_numbers": True,
        "blocks": [
            {"type": "h1", "text": "一、会议基本信息"},
            {"type": "para", "text": "**会议名称：**某某公司临时股东会"},
            {"type": "table", "caption": "近三年主要财务指标：",
             "header": ["指标", "2024年", "2025年"],
             "rows": [[f"指标{i}", "6,963.89", "8,189.79"] for i in range(1, 25)]},
        ],
        "attachments": ["会议通知", "议案", "表决票"],
    }, ensure_ascii=False), encoding="utf-8")
    return [sys.executable,
            str(REPO / skill / "scripts" / "create_yiti_docx.py"),
            str(spec), str(out)]


BUILDERS = {
    "gongsi-qingkuang": _trio_cmd,
    "hangye-fenxi": _trio_cmd,
    "zhuying-yewu-fenxi": _trio_cmd,
    "officialese-skill": _officialese_cmd,
    "yiti-skill": _yiti_cmd,
}


def embedded_entries(docx_path: Path) -> list[tuple[str, str]]:
    """[(字体名, charset)] —— 该 DOCX 中真正带嵌入字体的条目。"""
    with zipfile.ZipFile(docx_path) as archive:
        table = archive.read("word/fontTable.xml").decode("utf-8")
    out = []
    for name, block in re.findall(
            r'<w:font\s+w:name="([^"]+)"\s*>(.*?)</w:font>', table, re.S):
        if "<w:embedRegular" not in block:
            continue
        charset = re.search(r'<w:charset w:val="([^"]+)"/>', block)
        out.append((name, charset.group(1) if charset else ""))
    return out


class BundledFontResolutionTests(unittest.TestCase):
    def test_every_skill_resolves_both_gb2312_faces(self) -> None:
        for skill in SKILLS:
            with self.subTest(skill=skill):
                resolved = load_embed_fonts(skill).resolve_bundled_fonts()
                self.assertIn("仿宋_GB2312", resolved)
                self.assertIn("楷体_GB2312", resolved)
                for path in resolved.values():
                    self.assertTrue(Path(path).is_file(), path)

    def test_title_face_is_gated_by_fs_type(self) -> None:
        module = load_embed_fonts("gongsi-qingkuang")
        resolved = module.resolve_bundled_fonts()
        title = resolved.get("方正小标宋简体")
        if title is not None:  # bundled everywhere today, but stay tolerant
            self.assertFalse(module.is_embeddable(
                module.read_fs_type(Path(title).read_bytes())))

    def test_descriptor_declares_gb2312_charset(self) -> None:
        for skill in SKILLS:
            with self.subTest(skill=skill):
                module = load_embed_fonts(skill)
                raw = Path(module.resolve_bundled_fonts()["仿宋_GB2312"]).read_bytes()
                self.assertIn('<w:charset w:val="86"/>', module.font_descriptor(raw))


class ObfuscationTests(unittest.TestCase):
    def test_round_trip_reconstructs_font_exactly(self) -> None:
        module = load_embed_fonts("gongsi-qingkuang")
        raw = Path(module.resolve_bundled_fonts()["仿宋_GB2312"]).read_bytes()
        guid = module.new_font_key()
        self.assertEqual(module.deobfuscate(module.obfuscate(raw, guid), guid), raw)


@unittest.skipUnless(HAS_DOCX, "python-docx not installed")
class GeneratorEmbeddingTests(unittest.TestCase):
    """每个生成器 CLI 产出的 DOCX 必须真正带上可用的嵌入字体。"""

    def test_each_generator_embeds_and_verifies(self) -> None:
        for skill in SKILLS:
            with self.subTest(skill=skill), tempfile.TemporaryDirectory() as tmp:
                tmp_path = Path(tmp)
                out = tmp_path / "out.docx"
                proc = subprocess.run(BUILDERS[skill](skill, out, tmp_path),
                                      capture_output=True, text=True,
                                      encoding="utf-8", errors="replace")
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertTrue(out.is_file(), proc.stdout)

                entries = embedded_entries(out)
                names = {n for n, _ in entries}
                self.assertEqual(names, {"仿宋_GB2312", "楷体_GB2312"})
                # 缺 charset 时 Word 会忽略嵌入字体并回退系统字体。
                for name, charset in entries:
                    self.assertEqual(charset, "86", f"{skill}/{name}")

                module = load_embed_fonts(skill)
                self.assertTrue(module.verify_embedded_fonts(out)["ok"], skill)

    def test_restricted_title_face_is_never_embedded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            out = tmp_path / "out.docx"
            # 生成器输出为中文，必须显式 utf-8，否则读取线程按 GBK 解码会炸。
            subprocess.run(BUILDERS["gongsi-qingkuang"]("gongsi-qingkuang", out, tmp_path),
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
            self.assertNotIn("方正小标宋简体", {n for n, _ in embedded_entries(out)})


class SharedScriptConsistencyTests(unittest.TestCase):
    def test_shared_copies_are_identical(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(REPO / "tools" / "check_shared_scripts.py")],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
