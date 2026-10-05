"""
行业分析内部一致性机械校验脚本——把 01-framework.md"内部一致性核验矩阵"里能用算术
核验的部分，从人工核对升级为程序验证。

用法：
    python scripts/reconcile_check.py 行业分析.md

只做机械核验（CAGR 重算、占比求和=100%、CRn≤100%、同一事实在文中与表格里
是否只有一个数值），不做任何措辞、逻辑或投资判断层面的检查——那些交给
05-quality-checklist.md 人工过一遍，以及 06-red-flags.md 的红旗扫描。

输入是行业分析正文（Markdown，标准管道分隔表格），不依赖任何第三方库。
"""

import io
import re
import sys


TOLERANCE_PCT = 0.5        # 百分比求和容差（个百分点）——文字稿的舍入误差比结构化数据大，放宽于 gongsi-qingkuang 版本
TOLERANCE_CAGR_PCT = 0.5   # CAGR 重算与声称值的容差（个百分点）
TOLERANCE_AMT_REL = 0.01   # 金额/数值类比较的相对容差（1%）

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def parse_num(cell):
    """把单元格或文本片段解析成 float；解析不出（含占位符）时返回 None。"""
    if cell is None:
        return None
    s = str(cell).strip()
    if s == "" or s in ("-", "—", "/", "无", "×", "××", "XX", "N/A", "待补充"):
        return None
    s = re.sub(r"[（(].*?[）)]", "", s)
    s = s.replace(",", "").replace("，", "")
    s = s.replace("万元", "").replace("亿元", "").replace("元", "")
    s = s.replace("%", "").strip()
    s = s.rstrip("E")  # 预测年份数值有时带 E 后缀（如 "1030E"），去掉后仍取数值本身
    if s == "" or re.search(r"[×xX]", s):
        return None
    try:
        return float(s)
    except ValueError:
        return None


TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
SEP_ROW_RE = re.compile(r"^\s*\|?[\s:|-]+\|[\s:|-]*\|?\s*$")


def split_row(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def parse_markdown_tables(text):
    """扫描全文，返回 [{header, rows, start, end, context_before, context_after}]。"""
    lines = text.split("\n")
    tables = []
    i = 0
    while i < len(lines):
        if TABLE_ROW_RE.match(lines[i]) and i + 1 < len(lines) and SEP_ROW_RE.match(lines[i + 1]):
            header = split_row(lines[i])
            j = i + 2
            rows = []
            while j < len(lines) and TABLE_ROW_RE.match(lines[j]):
                rows.append(split_row(lines[j]))
                j += 1
            context_before = "\n".join(lines[max(0, i - 6):i])
            context_after = "\n".join(lines[j:j + 6])
            tables.append({
                "header": header, "rows": rows,
                "start": i, "end": j,
                "context_before": context_before, "context_after": context_after,
            })
            i = j
        else:
            i += 1
    return tables


def find_col(header, *keywords):
    for idx, h in enumerate(header):
        for kw in keywords:
            if kw in h:
                return idx
    return None


def is_total_row(row, name_col=0):
    label = str(row[name_col]) if name_col < len(row) else ""
    return any(k in label for k in ("合计", "总计", "小计"))


def is_other_row(row, name_col=0):
    label = str(row[name_col]) if name_col < len(row) else ""
    return "其他" in label


class Report:
    def __init__(self):
        self.items = []

    def add(self, status, code, message):
        self.items.append((status, code, message))

    def render(self):
        counts = {"PASS": 0, "FAIL": 0, "SKIP": 0, "REVIEW": 0}
        lines = []
        marks = {"PASS": "PASS", "FAIL": "FAIL", "SKIP": "SKIP", "REVIEW": "REVIEW"}
        for status, code, message in self.items:
            counts[status] += 1
            lines.append(f"[{marks[status]}] {code}  {message}")
        summary = (
            f"\n共 {len(self.items)} 项：通过 {counts['PASS']} / 不一致 {counts['FAIL']} / "
            f"需人工复核 {counts['REVIEW']} / 跳过（数据不足）{counts['SKIP']}"
        )
        if counts["FAIL"] > 0:
            summary += "\n\n存在硬性不一致项，对照 01-framework.md「内部一致性核验矩阵」逐项核实原始数据后再交付。"
        if counts["REVIEW"] > 0:
            summary += "\n\n存在需人工判断的疑似不一致（文本抽取具有模糊性，脚本无法自动确认），逐条人工核对。"
        if counts["PASS"] + counts["FAIL"] + counts["REVIEW"] == 0:
            summary += "\n\n未发现任何可核验的数值表格或数据表述，补齐数据后重新运行。"
        return "\n".join(lines) + summary


def check_percentage_sum(report, code, table, pct_col, name_col=0, expect=100.0, label=""):
    rows = [r for r in table["rows"] if not is_total_row(r, name_col) and not is_other_row(r, name_col)]
    other_rows = [r for r in table["rows"] if is_other_row(r, name_col)]
    vals = [parse_num(r[pct_col]) for r in rows if pct_col < len(r)]
    vals = [v for v in vals if v is not None]
    other_vals = [parse_num(r[pct_col]) for r in other_rows if pct_col < len(r)]
    other_vals = [v for v in other_vals if v is not None]
    if len(vals) < 2:
        report.add("SKIP", code, f"{label}：可解析的百分比数据不足，跳过求和校验")
        return
    total = sum(vals) + sum(other_vals)
    if abs(total - expect) <= TOLERANCE_PCT:
        report.add("PASS", code, f"{label}：Σ={total:.2f}%，与 {expect}% 相符")
    else:
        report.add(
            "FAIL", code,
            f"{label}：Σ={total:.2f}%，与预期 {expect}% 相差 {total - expect:+.2f} 个百分点——数据口径不一致，需进一步核实"
        )


def check_market_share_table(report, table, path_hint=""):
    header = table["header"]
    if find_col(header, "企业", "公司", "厂商") is None:
        return
    share_col = find_col(header, "市占率", "份额", "占比")
    if share_col is None:
        return
    check_percentage_sum(report, "竞争格局-市占率求和", table, share_col, expect=100.0,
                          label=f"竞争格局表市占率求和{path_hint}")
    # CRn 交叉核对：在表格前后文本中找 "CR3约45%" 这类表述，与表内前 N 名份额之和比对
    text = table["context_before"] + "\n" + table["context_after"]
    for m in re.finditer(r"CR(\d+)\D{0,6}?([\d.]+)\s*%", text):
        n, claimed = int(m.group(1)), float(m.group(2))
        detail_rows = [r for r in table["rows"] if not is_total_row(r) and not is_other_row(r)]
        vals = [parse_num(r[share_col]) for r in detail_rows if share_col < len(r)]
        vals = [v for v in vals if v is not None]
        vals_sorted = sorted(vals, reverse=True)
        if len(vals_sorted) >= n:
            top_n_sum = sum(vals_sorted[:n])
            if abs(top_n_sum - claimed) <= TOLERANCE_PCT * 2:
                report.add("PASS", "CRn-交叉核对", f"正文声称 CR{n}={claimed}%，表内前{n}名份额之和={top_n_sum:.2f}%，相符")
            else:
                report.add("REVIEW", "CRn-交叉核对",
                            f"正文声称 CR{n}={claimed}%，表内前{n}名份额之和={top_n_sum:.2f}%，相差较大——"
                            f"核对是否统计口径不同或表格数据不全")
        else:
            report.add("SKIP", "CRn-交叉核对", f"正文提及 CR{n}={claimed}%，但表内可比较的企业行数不足 {n} 行，跳过")


def check_generic_composition_table(report, table, path_hint=""):
    """通用占比构成表：表头含"占比"字样的表，明细行占比应求和=100%（用于产业链成本结构、
    细分市场结构等）。已被市场份额表专门处理的不重复。"""
    header = table["header"]
    if find_col(header, "企业", "公司", "厂商") is not None:
        return  # 交给 check_market_share_table
    pct_col = find_col(header, "占比")
    if pct_col is None:
        return
    name_col = 0
    check_percentage_sum(report, "构成表-占比求和", table, pct_col, name_col=name_col,
                          label=f"占比构成表求和{path_hint}")


def check_market_size_table(report, table, path_hint=""):
    header = table["header"]
    year_col = find_col(header, "年份", "年度")
    size_col = find_col(header, "市场规模", "规模")
    if year_col is None or size_col is None:
        return
    points = []
    for row in table["rows"]:
        if year_col >= len(row) or size_col >= len(row):
            continue
        year_m = re.search(r"(20\d{2})", str(row[year_col]))
        val = parse_num(row[size_col])
        if year_m and val is not None:
            points.append((int(year_m.group(1)), val))
    if len(points) < 2:
        report.add("SKIP", "CAGR-重算", f"市场规模表{path_hint}：可用年份数据点不足2个，跳过 CAGR 重算")
        return
    points.sort()
    start_year, start_val = points[0]
    end_year, end_val = points[-1]
    n = end_year - start_year
    if n <= 0 or start_val <= 0:
        report.add("SKIP", "CAGR-重算", f"市场规模表{path_hint}：年份跨度或起始值异常，跳过")
        return
    recomputed = ((end_val / start_val) ** (1 / n) - 1) * 100
    text = table["context_before"] + "\n" + table["context_after"]

    # 引言句 vs 表格首末值：范文实证错误"正文598.70亿 vs 表内587.90亿"就是这一类——
    # 正文常见"从X亿元增长至Y亿元"式表述，X/Y 应分别等于表格首/末年数值
    intro_m = re.search(
        r"从\s*([\d,]+\.?\d*)\s*(?:亿元|万元)[^，。]{0,15}?(?:增长|增至|升至)(?:至|到)?\s*([\d,]+\.?\d*)\s*(?:亿元|万元)",
        text
    )
    if intro_m:
        intro_start = float(intro_m.group(1).replace(",", ""))
        intro_end = float(intro_m.group(2).replace(",", ""))
        if abs(intro_start - start_val) / max(abs(start_val), 1e-9) > TOLERANCE_AMT_REL:
            report.add("FAIL", "引言句-表格首值核对",
                        f"市场规模表{path_hint}：正文引言写{start_year}年为{intro_start}，表格{start_year}年为{start_val}——"
                        f"同一事实只能有一个数，需核实并统一")
        else:
            report.add("PASS", "引言句-表格首值核对", f"市场规模表{path_hint}：正文引言{start_year}年数值与表格相符")
        if abs(intro_end - end_val) / max(abs(end_val), 1e-9) > TOLERANCE_AMT_REL:
            report.add("FAIL", "引言句-表格末值核对",
                        f"市场规模表{path_hint}：正文引言写{end_year}年为{intro_end}，表格{end_year}年为{end_val}——"
                        f"同一事实只能有一个数，需核实并统一")
        else:
            report.add("PASS", "引言句-表格末值核对", f"市场规模表{path_hint}：正文引言{end_year}年数值与表格相符")

    claims = re.findall(r"(?:复合增长率|CAGR)\D{0,6}?([\d.]+)\s*%", text)
    if not claims:
        report.add("REVIEW", "CAGR-重算",
                    f"市场规模表{path_hint}：按 {start_year}-{end_year} 年数据重算 CAGR={recomputed:.2f}%，"
                    f"未在附近文本中找到声称值，请人工核对正文中的 CAGR 表述是否与此一致")
        return
    for claimed_str in claims:
        claimed = float(claimed_str)
        diff = recomputed - claimed
        if abs(diff) <= TOLERANCE_CAGR_PCT:
            report.add("PASS", "CAGR-重算", f"市场规模表{path_hint}：{start_year}-{end_year}年重算CAGR={recomputed:.2f}%，与声称值{claimed}%相符")
        else:
            report.add("FAIL", "CAGR-重算",
                        f"市场规模表{path_hint}：{start_year}-{end_year}年按首末值重算CAGR={recomputed:.2f}%，"
                        f"与正文声称值{claimed}%相差{diff:+.2f}个百分点——需重新核算并统一口径")


def check_cross_table_duplicate_year_values(report, tables):
    """同一份文档里若出现表头高度相似（同一 non-year 列名）且都含年份列的两张表，
    比对同一年份下的数值是否一致——用于捕捉"图表数据与正文/另一张表数字打架"这类错误。"""
    def signature(t):
        return tuple(h for h in t["header"] if not any(k in h for k in ("年份", "年度")))

    size_tables = []
    for t in tables:
        year_col = find_col(t["header"], "年份", "年度")
        if year_col is not None:
            size_tables.append((t, year_col))

    for i in range(len(size_tables)):
        for j in range(i + 1, len(size_tables)):
            t1, yc1 = size_tables[i]
            t2, yc2 = size_tables[j]
            if signature(t1) != signature(t2):
                continue
            value_col1 = 1 if yc1 != 1 else 0
            value_col2 = 1 if yc2 != 1 else 0
            years1 = {}
            for row in t1["rows"]:
                m = re.search(r"(20\d{2})", str(row[yc1])) if yc1 < len(row) else None
                if m and value_col1 < len(row):
                    v = parse_num(row[value_col1])
                    if v is not None:
                        years1[m.group(1)] = v
            for row in t2["rows"]:
                m = re.search(r"(20\d{2})", str(row[yc2])) if yc2 < len(row) else None
                if m and value_col2 < len(row):
                    v = parse_num(row[value_col2])
                    if v is not None and m.group(1) in years1:
                        v1 = years1[m.group(1)]
                        if abs(v - v1) / max(abs(v1), 1e-9) > TOLERANCE_AMT_REL:
                            report.add("FAIL", "同年份跨表数值核对",
                                        f"{m.group(1)}年：表A(行{t1['start']})={v1}，表B(行{t2['start']})={v}，不一致——"
                                        f"同一事实全文只能有一个数（或需并列口径说明）")


def main():
    if len(sys.argv) != 2:
        print("用法：python reconcile_check.py 行业分析.md")
        sys.exit(1)
    path = sys.argv[1]
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    tables = parse_markdown_tables(text)
    report = Report()

    if not tables:
        print("未在文档中找到任何 Markdown 表格，无法核验。")
        sys.exit(1)

    for idx, t in enumerate(tables):
        hint = f"（第{idx + 1}张表，源文件第{t['start'] + 1}行）"
        check_market_size_table(report, t, hint)
        check_market_share_table(report, t, hint)
        check_generic_composition_table(report, t, hint)

    check_cross_table_duplicate_year_values(report, tables)

    print(f"共扫描 {len(tables)} 张表格。\n")
    print(report.render())

    if any(status == "FAIL" for status, _, _ in report.items):
        sys.exit(2)


if __name__ == "__main__":
    main()
