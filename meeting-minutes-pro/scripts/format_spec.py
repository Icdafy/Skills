#!/usr/bin/env python3
"""Single source of truth for the fixed meeting-minutes layout.

The heading grammar, role→font mapping, western-run rule, type sizes, page
geometry and font catalogue live here and nowhere else. ``quality_check.py``
(validation), ``create_minutes_docx.py`` (rendering), ``render_docx.py``
(font-substitution check), ``font_preflight.py`` (font install) and
``embed_fonts.py`` (DOCX embedding) all import from this module, so the rules
can never drift between the layer that validates the text and the layer that
renders it — a single edit here reaches every stage.

``references/format-and-output.md`` is the human-readable statement of the same
spec; ``tests/test_format_spec.py`` guards the constants below against it.
"""

from __future__ import annotations

import re

# --- Indentation -----------------------------------------------------------
# Every line except the centred title (and optional subtitle) starts with two
# ideographic spaces in the plain text; the DOCX realises this as a first-line
# indent (see FIRST_LINE_INDENT_PT) rather than literal spaces.
INDENT = "　　"

# --- Localised East Asian family names -------------------------------------
# Chinese-UI Word resolves East Asian fonts by their localised names; the
# English names (KaiTi_GB2312 …) fall through the registry FontSubstitutes
# table and get silently replaced by the system KaiTi/FangSong. The renderer
# must therefore write these exact strings as w:eastAsia.
TITLE_FONT = "方正小标宋简体"   # 大标题：二号方正小标宋简体
KAI_FONT = "楷体_GB2312"        # 二级标题（加粗）、副标题
FANGSONG_FONT = "仿宋_GB2312"   # 正文、三/四级标题、页码
HEI_FONT = "SimHei"             # 一级标题：三号黑体（SimHei 为系统字体，不入替换表）
NUMBER_FONT = "Times New Roman"  # 西文字母与阿拉伯数字

# --- Heading grammar: 一、/（一）/1./（1） ---------------------------------
FIRST_LEVEL = re.compile(r"^[一二三四五六七八九十]+、")
SECOND_LEVEL = re.compile(r"^（[一二三四五六七八九十]+）")
# ``(?!\d)`` keeps a decimal-led body line such as "3.5亿元…" from being read as
# a third-level heading "3." — the dot must not be followed by another digit.
THIRD_LEVEL = re.compile(r"^\d+\.(?!\d)")
FOURTH_LEVEL = re.compile(r"^（\d+）")


def level_number(text: str) -> int | None:
    """Return 1–4 for a heading line, or None for body/metadata/Q-A text."""
    if FIRST_LEVEL.match(text):
        return 1
    if SECOND_LEVEL.match(text):
        return 2
    if THIRD_LEVEL.match(text):
        return 3
    if FOURTH_LEVEL.match(text):
        return 4
    return None


def paragraph_role(text: str) -> tuple[str, str, bool]:
    """Map a line (indent already stripped) to (role, east-asia font, bold)."""
    level = level_number(text)
    if level == 1:
        return "first", HEI_FONT, False
    if level == 2:
        return "second", KAI_FONT, True
    if level == 3:
        return "third", FANGSONG_FONT, True
    if level == 4:
        return "fourth", FANGSONG_FONT, False
    return "body", FANGSONG_FONT, False


# --- Western run -----------------------------------------------------------
# A maximal run of ASCII letters and digits (with internal . , - / and a
# trailing %) is set in Times New Roman at the size of the surrounding text.
# 公文惯例：中文用仿宋，西文字母与阿拉伯数字统一 Times New Roman；这样
# "5G""A4""T3""COO""Qwen3""2024-2025""1,234.56%" 都作为整体走西文字体，
# 不再把字母留在中文字体里、把数字单独切出来。
WESTERN_SEGMENT = re.compile(r"[0-9A-Za-z]+(?:[.,\-/][0-9A-Za-z]+)*%?")

# --- Type sizes (pt) -------------------------------------------------------
TITLE_SIZE = 22          # 二号
SUBTITLE_SIZE = 16       # 三号
BODY_SIZE = 16           # 三号
PAGE_NUMBER_SIZE = 16    # 三号

# --- Exact line spacing (pt) ----------------------------------------------
TITLE_LINE_SPACING = 30
SUBTITLE_LINE_SPACING = 28
BODY_LINE_SPACING = 28

# --- First-line indent (pt) ------------------------------------------------
# Two full-width characters at the body size. Kept as an explicit measure so
# the plain-text "　　" prefix is never emitted as literal spaces in the DOCX.
FIRST_LINE_INDENT_PT = 32.4

# --- Page geometry (cm) — A4 portrait, GB/T 9704 margins ------------------
PAGE_WIDTH_CM = 21.0
PAGE_HEIGHT_CM = 29.7
TOP_MARGIN_CM = 3.7
BOTTOM_MARGIN_CM = 3.5
LEFT_MARGIN_CM = 2.8
RIGHT_MARGIN_CM = 2.6


# --- Font catalogue --------------------------------------------------------
# One row per family the fixed format touches. Consumed by font_preflight
# (install/check), render_docx (PDF marker / substitution alerts) and
# embed_fonts (which of the bundled faces may be embedded in the DOCX).
#
#   family            English/registry family, used for install detection
#   run_name          name written into the DOCX (w:eastAsia / w:font w:name)
#   aliases           strings that prove the family is installed
#   asset             bundled TTF filename under assets/fonts, or None (system)
#   registry_name     Windows "… (TrueType)" registry value name, or None
#   embeddable        bundled AND OS/2 fsType permits DOCX embedding
#   pdf_marker        PostScript name that must appear in a faithful PDF
#   substitute_alert  bare PostScript name that proves a silent substitution
FONT_CATALOG: tuple[dict[str, object], ...] = (
    {
        "family": "FZXiaoBiaoSong-B05S",
        "run_name": TITLE_FONT,
        "aliases": ("FZXiaoBiaoSong-B05S", "方正小标宋简体"),
        "asset": "方正小标宋简体.ttf",
        "registry_name": "方正小标宋简体 (TrueType)",
        # fsType=2 (restricted): embedding is forbidden; the title is outlined
        # in the PDF and must not be embedded in the DOCX either.
        "embeddable": False,
        "pdf_marker": None,
        "substitute_alert": None,
    },
    {
        "family": "KaiTi_GB2312",
        "run_name": KAI_FONT,
        "aliases": ("KaiTi_GB2312", "楷体_GB2312"),
        "asset": "楷体_GB2312.ttf",
        "registry_name": "楷体_GB2312 (TrueType)",
        "embeddable": True,   # fsType=0
        "pdf_marker": "KaiTi_GB2312",
        "substitute_alert": "KaiTi",
    },
    {
        "family": "FangSong_GB2312",
        "run_name": FANGSONG_FONT,
        "aliases": ("FangSong_GB2312", "仿宋_GB2312"),
        "asset": "simfang.ttf",
        "registry_name": "仿宋_GB2312 (TrueType)",
        "embeddable": True,   # fsType=0
        "pdf_marker": "FangSong_GB2312",
        "substitute_alert": "FangSong",
    },
    {
        "family": "SimHei",
        "run_name": HEI_FONT,
        "aliases": ("SimHei", "simhei.ttf"),
        "asset": None,        # system font, not bundled
        "registry_name": None,
        "embeddable": False,
        "pdf_marker": None,
        "substitute_alert": None,
    },
    {
        "family": "Times New Roman",
        "run_name": NUMBER_FONT,
        "aliases": ("Times New Roman", "times.ttf", "timesnewroman"),
        "asset": None,        # ubiquitous system font
        "registry_name": None,
        "embeddable": False,
        "pdf_marker": None,
        "substitute_alert": None,
    },
)


def embeddable_fonts() -> dict[str, str]:
    """{run_name: bundled TTF filename} for fonts allowed to be embedded."""
    return {
        str(entry["run_name"]): str(entry["asset"])
        for entry in FONT_CATALOG
        if entry["embeddable"] and entry["asset"]
    }


def pdf_required_markers() -> tuple[str, ...]:
    return tuple(str(e["pdf_marker"]) for e in FONT_CATALOG if e["pdf_marker"])


def pdf_substitute_alerts() -> tuple[str, ...]:
    return tuple(
        str(e["substitute_alert"]) for e in FONT_CATALOG if e["substitute_alert"]
    )
