#!/usr/bin/env python3
"""Validate text prepared by the meeting-minutes-pro skill."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from format_spec import INDENT, level_number  # noqa: E402  (needs path shim)

SKILL_DIR = Path(__file__).resolve().parent.parent
# 机构自定义禁词文件：每行一条短语，# 开头为注释；与项目术语文件一样属
# 本地配置（glossary/* 已被 .gitignore 排除），不随技能分发。
CUSTOM_BANNED_FILE = SKILL_DIR / "glossary" / "banned-phrases.txt"
# 公文正文使用全角标点；紧邻中文字符的半角标点视为格式错误。纯数字场景
# （千分位 1,234 等）两侧无中文字符，不受影响。
HALFWIDTH_PUNCT_NEAR_CJK = re.compile(
    r"[一-鿿][,;:?!()]|[,;:?!()][一-鿿]"
)
INTERVIEW_METADATA = ("访谈时间：", "访谈地点：", "访谈对象：", "访谈人员：")
SUMMARY_MARKERS = (
    "完整总结概述",
    "总体情况概述",
    "主要内容概述",
    "访谈主要内容",
    "会议主要内容",
    "核心结论摘要",
    "核心结论",
    "综合摘要",
    "会议摘要",
    "访谈摘要",
    "尽调摘要",
    "总结与研判",
)
QA_SECTION_MARKERS = (
    "完整问答纪要",
    "完整问答",
    "访谈重点问答",
    "访谈问答",
    "重点问答",
    "问答纪要",
    "问答环节",
)

# 纪要本身已经承载该场访谈内容，正文不得反复添加泛化的发言主体或
# “据其介绍/其表示”“个人估计/判断/印象”一类归因套话。固定基本信息
# 字段“访谈对象：”单独豁免；正文命中后不可用 --allow-line 放行。
REDUNDANT_ATTRIBUTION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"受访人|受访者|被访人|被访者|被访谈人|被访谈者|被访谈对象|"
            r"被采访人|被采访者|被采访对象|受访方|受访嘉宾|采访对象|访谈对象|"
            r"回答者|回答方|答复人|答复方"
        ),
        "泛化的受访主体",
    ),
    (
        re.compile(
            r"据(?:其|对方|本人)(?:个人)?(?:介绍|表示|认为|判断|估计|自述|所述|说法)"
        ),
        "“据其介绍/自述/估计”类归因套话",
    ),
    (
        re.compile(r"(?:其|对方|本人)(?:表示|认为|介绍|判断|估计|提到|指出|透露|称)"),
        "“其表示/对方认为”类归因套话",
    ),
    (
        re.compile(
            r"(?:我|本人)?个人(?:的)?(?:初步|大致|主观)?"
            r"(?:估计|判断|印象|认为|看法|观点|理解|感觉|推测|意见)|"
            r"(?:我|本人)(?:的)?(?:初步|大致|主观)?"
            r"(?:估计|判断|印象|看法|观点|理解|感觉|推测|意见)"
        ),
        "“个人估计/判断/印象”类归因套话",
    ),
]

# Detect prohibited paired conjunctions anywhere within the same sentence.
CLAUSE = r"[^\r\n。！？!?]*?"
CONTRAST_PATTERNS = [
    re.compile("不" + "是" + CLAUSE + "而" + "是"),
    re.compile("并" + "非" + CLAUSE + "而" + "是"),
    re.compile("不" + "仅" + CLAUSE + "而" + "是"),
    re.compile("不" + "仅" + CLAUSE + "而" + "且"),
    re.compile("不" + "仅" + CLAUSE + "还"),
    re.compile("不" + "但" + CLAUSE + "而" + "且"),
    re.compile("不" + "但" + CLAUSE + "还"),
]

# 硬性禁用：记录人员附注式的“待核实/待核验/待落实”、以及主观判断和指导性
# 表述。纪要只客观陈述会议内容；仅当相同表述确为转录稿中真实谈及的会议
# 内容（如原话确为“最终时间以合同约定为准”）时，才可用 --allow-line <行号> 放行。
PENDING_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # 负向断言排除“期待核心”“接待核心”“现有待遇”等正常词语的误中。
    (
        re.compile(r"(?<!期)(?<!接)待核|待落实|待验证|待证实|待确认|待查证"),
        "“待核/待核实/待落实”类标注",
    ),
    (re.compile(r"有待(?!遇)|尚待"), "“有待/尚待”类表述"),
    (re.compile(r"(?:尚|仍)需(?:核实|核验|验证|确认|落实)"), "“尚需核实”类表述"),
    (re.compile(r"需(?:要)?(?:进一步)?(?:核实|核验|验证|落实)"), "“需核实/需核验/需落实”类表述"),
    (re.compile(r"进一步(?:核实|核验|验证|查证|比对)"), "“进一步核实”类表述"),
    (
        re.compile(r"(?:需|须|应|建议)结合[^\r\n。！？]{0,30}(?:核实|核验|验证|确认|比对)"),
        "“需结合……核实”类表述",
    ),
    (re.compile(r"以[^\r\n。！？，；、]{1,20}为准"), "“以……为准”类表述"),
    (
        re.compile(r"(?:需要?|应予?|后续需?要?|建议)重点关注|建议关注|值得关注"),
        "“需重点关注/建议关注”类表述",
    ),
    (
        re.compile(r"建议(?:下一步|后续|跟进|补充|进一步)|下一步建议|值得注意的是"),
        "“下一步建议”类指导性表述",
    ),
]

# 完整总结概述中禁止出现的板块标题（更新规则：总结概述只客观归纳会议
# 内容，不设“主要风险”“待核实事项”“后续需重点关注”等记录人员自设板块）。
SUMMARY_BANNED_HEADING = re.compile(
    r"主要风险|风险提示|风险与|风险及|风险、|待核|重点关注|后续关注|需关注"
)

# 访谈对象行中出现单位或职务信息但未使用（）括注时给出错误。
AFFILIATION_HINT = re.compile(
    r"公司|集团|银行|基金|证券|研究院|研究所|大学|学院|中心|部门|单位|科技|有限|"
    r"董事|监事|经理|总裁|总监|主任|部长|处长|科长|组长|负责人|创始人|合伙人|"
    r"工程师|会计师|分析师|顾问|CEO|CFO|CTO|COO"
)


def load_custom_banned() -> list[str]:
    try:
        lines = CUSTOM_BANNED_FILE.read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return []
    return [line.strip() for line in lines
            if line.strip() and not line.strip().startswith("#")]


def _bigrams(text: str) -> set[str]:
    cleaned = re.sub(r"[^\w]", "", text)
    if len(cleaned) < 2:
        return {cleaned} if cleaned else set()
    return {cleaned[i:i + 2] for i in range(len(cleaned) - 1)}


def _similarity(a: str, b: str) -> float:
    grams_a, grams_b = _bigrams(a), _bigrams(b)
    if not grams_a or not grams_b:
        return 0.0
    return len(grams_a & grams_b) / min(len(grams_a), len(grams_b))


def validate(
    path: Path,
    mode: str,
    allowed_lines: frozenset[int] | set[int] = frozenset(),
    custom_banned: list[str] | None = None,
) -> list[str]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    visible = [(index + 1, line) for index, line in enumerate(lines) if line.strip()]
    errors: list[str] = []

    if len(visible) < 2:
        return ["正文至少应包含标题和一段纪要内容。"]

    title_line, title = visible[0]
    if title.startswith(INDENT):
        errors.append(f"第 {title_line} 行标题不应首行缩进。")

    last_level = 0
    first_heading_line: int | None = None
    interview_metadata: list[tuple[int, int, str]] = []
    seen_interview_metadata: dict[str, int] = {}
    qa_labels: list[tuple[int, str]] = []
    question_lines_seen: list[tuple[int, str]] = []
    headings: list[tuple[int, int, str]] = []
    body_lines: list[tuple[int, str]] = []
    for line_number, line in visible[1:]:
        if not line.startswith(INDENT):
            errors.append(f"第 {line_number} 行未以两个全角空格起首。")
        content = line.removeprefix(INDENT).strip()
        level = level_number(content)
        if level is not None:
            headings.append((line_number, level, content))
            if first_heading_line is None:
                first_heading_line = line_number
            if last_level == 0 and level > 1:
                errors.append(f"第 {line_number} 行在缺少上级标题时使用第 {level} 级标题。")
            elif last_level and level > last_level + 1:
                errors.append(f"第 {line_number} 行层级从第 {last_level} 级跳至第 {level} 级。")
            last_level = level
        else:
            body_lines.append((line_number, content))
        for field_index, field in enumerate(INTERVIEW_METADATA):
            if content.startswith(field):
                if field in seen_interview_metadata:
                    errors.append(
                        f"第 {line_number} 行重复出现“{field.removesuffix('：')}”，"
                        f"首次出现于第 {seen_interview_metadata[field]} 行。"
                    )
                else:
                    seen_interview_metadata[field] = line_number
                    interview_metadata.append((field_index, line_number, field))
        if content.startswith("问："):
            qa_labels.append((line_number, "问"))
            question_lines_seen.append((line_number, content.removeprefix("问：").strip()))
            # 更新规则：连续问答时每组之间必须空一行；紧随各级标题的首问除外。
            previous_raw = lines[line_number - 2] if line_number >= 2 else ""
            previous_content = previous_raw.removeprefix(INDENT).strip()
            if previous_content and level_number(previous_content) is None:
                errors.append(
                    f"第 {line_number} 行新一组问答开始前应空一行，"
                    "与上一组问答或正文以空行分隔。"
                )
        if content.startswith("答："):
            qa_labels.append((line_number, "答"))
        if content.startswith("访谈对象："):
            subject_value = content.removeprefix("访谈对象：").strip()
            if (
                subject_value
                and "（" not in subject_value
                and "(" not in subject_value
                and AFFILIATION_HINT.search(subject_value)
            ):
                errors.append(
                    f"第 {line_number} 行访谈对象的单位、职务或补充说明"
                    "应置于人名后的（）内，如“张某某（某某公司总经理）”。"
                )

    if interview_metadata:
        field_indexes = [field_index for field_index, _, _ in interview_metadata]
        if field_indexes != sorted(field_indexes):
            errors.append("访谈基本信息顺序应为：访谈时间、访谈地点、访谈对象、访谈人员。")
        if first_heading_line is not None:
            misplaced = [
                (line_number, field)
                for _, line_number, field in interview_metadata
                if line_number > first_heading_line
            ]
            for line_number, field in misplaced:
                errors.append(
                    f"第 {line_number} 行“{field.removesuffix('：')}”应置于第一个正文标题之前。"
                )

    document = "\n".join(lines)
    if any(pattern.search(document) for pattern in CONTRAST_PATTERNS):
        errors.append("存在禁用的对照式连词组合。")

    # 泛化受访主体和归因套话在总结、问答及其他正文中一律禁止。此规则
    # 不读取 allowed_lines，确保 --allow-line 无法绕过用户要求的硬约束。
    for line_number, line in visible:
        content = line.removeprefix(INDENT).strip()
        if content.startswith(INTERVIEW_METADATA):
            continue
        for pattern, label in REDUNDANT_ATTRIBUTION_PATTERNS:
            if pattern.search(content):
                errors.append(
                    f"第 {line_number} 行出现冗余归因表述（{label}）；"
                    "请删除归因外壳并完整保留后续实质内容。完整总结概述不得添加泛化主体前缀，"
                    "完整问答纪要的“答：”后应直接写答复；此规则不可用 "
                    "--allow-line 放行。"
                )
                break

    # 更新规则：纪要只客观陈述会议内容，任何“待核实/待核验/待落实”“以……
    # 为准”“需重点关注”等核验提示句、主观判断和指导性意见一律禁止。
    for line_number, line in visible:
        if line_number in allowed_lines:
            continue
        content = line.removeprefix(INDENT).strip()
        for pattern, label in PENDING_PATTERNS:
            if pattern.search(content):
                errors.append(
                    f"第 {line_number} 行出现禁用的核验或指导类表述（{label}）；"
                    "纪要只客观陈述会议内容。仅当该表述确为转录稿中真实谈及的"
                    f"会议内容时，用 --allow-line {line_number} 放行并向用户说明。"
                )
                break

    # 机构自定义禁词（glossary/banned-phrases.txt）：命中即失败，出口与
    # 内置禁用表述一致（--allow-line，仅限转录稿真实内容）。
    banned_phrases = load_custom_banned() if custom_banned is None else list(custom_banned)
    if banned_phrases:
        for line_number, line in visible:
            if line_number in allowed_lines:
                continue
            content = line.removeprefix(INDENT).strip()
            for phrase in banned_phrases:
                if phrase and phrase in content:
                    errors.append(
                        f"第 {line_number} 行出现自定义禁用表述「{phrase}」"
                        "（glossary/banned-phrases.txt）；仅当其确为转录稿真实"
                        f"内容时，用 --allow-line {line_number} 放行并向用户说明。"
                    )
                    break

    # 半角标点紧邻中文：公文正文应使用全角标点。
    for line_number, line in visible:
        content = line.removeprefix(INDENT).strip()
        found = HALFWIDTH_PUNCT_NEAR_CJK.search(content)
        if found:
            errors.append(
                f"第 {line_number} 行中文内容中混用了半角标点（…{found.group()}…），"
                "公文正文应使用全角标点。"
            )

    # 纪要内部重复问答：几乎相同的两问多为起草时的重复粘贴。
    for i in range(len(question_lines_seen)):
        for j in range(i + 1, len(question_lines_seen)):
            line_i, text_i = question_lines_seen[i]
            line_j, text_j = question_lines_seen[j]
            if line_j in allowed_lines:
                continue
            if (min(len(text_i), len(text_j)) >= 8
                    and _similarity(text_i, text_j) >= 0.9):
                errors.append(
                    f"第 {line_j} 行问题与第 {line_i} 行几乎相同（疑似重复问答）；"
                    f"确为两次相似提问时用 --allow-line {line_j} 放行。"
                )

    qa_detected = bool(qa_labels)
    # Every explicit Q/A label must be paired, regardless of the selected mode.
    # The legacy ``qa`` mode is retained as a compatibility alias but no longer
    # permits a pure-QA deliverable.
    if qa_detected or mode in ("qa", "qa-summary"):
        if not qa_labels:
            errors.append("问答纪要必须同时包含“问：”和“答：”。")
        else:
            waiting_for_answer = False
            question_line = 0
            for line_number, label in qa_labels:
                if label == "问":
                    if waiting_for_answer:
                        errors.append(f"第 {question_line} 行“问：”后缺少对应“答：”。")
                    waiting_for_answer = True
                    question_line = line_number
                elif not waiting_for_answer:
                    errors.append(f"第 {line_number} 行“答：”前缺少对应“问：”。")
                else:
                    waiting_for_answer = False
            if waiting_for_answer:
                errors.append(f"第 {question_line} 行“问：”后缺少对应“答：”。")

    # A minutes deliverable containing Q/A must always begin with a standalone,
    # comprehensive thematic overview. Pure Q/A is not a valid output shape.
    summary_required = qa_detected or mode in ("qa", "qa-summary")
    if summary_required:
        if not qa_detected:
            errors.append("组合式问答纪要必须包含完整的“问：/答：”内容。")
        else:
            question_lines = [
                line_number for line_number, label in qa_labels if label == "问"
            ]
            if not question_lines:
                return errors
            first_question_line = min(question_lines)
            summary_candidates = [
                (line_number, content)
                for line_number, level, content in headings
                if level == 1
                and line_number < first_question_line
                and any(marker in content for marker in SUMMARY_MARKERS)
            ]
            qa_section_candidates = [
                (line_number, content)
                for line_number, level, content in headings
                if level == 1
                and line_number < first_question_line
                and any(marker in content for marker in QA_SECTION_MARKERS)
            ]
            if not summary_candidates:
                errors.append(
                    "含问答的纪要须在完整问答前设置一级标题“完整总结概述”（或同义标题）。"
                )
            if not qa_section_candidates:
                errors.append(
                    "组合式问答纪要须在首个问题前设置一级标题“完整问答纪要”（或同义标题）。"
                )
            if summary_candidates and qa_section_candidates:
                summary_line = summary_candidates[0][0]
                qa_section_line = qa_section_candidates[-1][0]
                if summary_line >= qa_section_line:
                    errors.append("“完整总结概述”必须置于“完整问答纪要”之前。")
                else:
                    for heading_line, _, heading_content in headings:
                        if (
                            summary_line < heading_line < qa_section_line
                            and heading_line not in allowed_lines
                            and SUMMARY_BANNED_HEADING.search(heading_content)
                        ):
                            errors.append(
                                f"第 {heading_line} 行：完整总结概述中不得设置"
                                "“主要风险”“待核实事项”“重点关注”类板块，"
                                "只按材料实际主题客观归纳。"
                            )
                    summary_body = [
                        content
                        for line_number, content in body_lines
                        if summary_line < line_number < qa_section_line
                        and not content.startswith(INTERVIEW_METADATA)
                    ]
                    qa_body = [
                        content
                        for line_number, content in body_lines
                        if line_number >= first_question_line
                    ]
                    summary_chars = sum(len(content) for content in summary_body)
                    qa_chars = sum(len(content) for content in qa_body)
                    # Scale with the Q/A volume: a two-hour interview carries
                    # thousands of characters of Q/A and deserves far more than
                    # a token overview, hence the 2000-character ceiling.
                    minimum_summary_chars = min(2000, max(120, qa_chars // 10))
                    if summary_chars < minimum_summary_chars:
                        errors.append(
                            "“完整总结概述”内容不足：当前正文约 "
                            f"{summary_chars} 字，按问答篇幅至少应达到约 "
                            f"{minimum_summary_chars} 字，并覆盖整份转录稿的主要主题。"
                        )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Check meeting-minutes-pro text output.")
    parser.add_argument("input", type=Path, help="UTF-8 plain-text minutes file")
    parser.add_argument(
        "--mode", choices=("auto", "minutes", "qa", "qa-summary"), default="auto"
    )
    parser.add_argument(
        "--allow-line",
        type=int,
        action="append",
        default=[],
        metavar="行号",
        help=(
            "放行该行的禁用核验/指导类表述；仅限转录稿中真实谈及的会议内容；"
            "不适用于泛化受访主体和归因套话"
        ),
    )
    args = parser.parse_args()

    if args.mode == "qa":
        print(
            "提示：纯 QA 模式已停用；--mode qa 现按 qa-summary 兼容校验。",
            file=sys.stderr,
        )

    if not args.input.is_file():
        parser.error(f"找不到文件：{args.input}")

    allowed_lines = frozenset(args.allow_line)
    errors = validate(args.input, args.mode, allowed_lines)
    if errors:
        print("纪要文本校验未通过：")
        for error in errors:
            print(f"- {error}")
        return 1

    text = args.input.read_text(encoding="utf-8-sig")
    qa_pairs = len(re.findall(r"^\s*　　问：", text, re.MULTILINE))
    print("纪要文本校验通过。")
    print("提示：冗余归因表述检查：0 处残留。")
    if allowed_lines:
        released = "、".join(str(number) for number in sorted(allowed_lines))
        print(f"提示：第 {released} 行的表述已按转录稿真实内容放行，交付前向用户说明。")
    print(f"提示：问答 {qa_pairs} 组。数字事实核对请另行运行 fact_check.py。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
