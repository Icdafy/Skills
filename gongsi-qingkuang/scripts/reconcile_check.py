"""
勾稽机械校验脚本——把 data-and-tables.md 第三节"勾稽自检清单"从人工核对升级为程序核验。

用法：
    python scripts/reconcile_check.py content.json

只做机械算术核验（求和=100%、分项之和=合计、资产=负债+权益等），不做任何文字或
措辞判断。查不到对应表格的检查项会显式标注"未找到/数据为空，跳过"，不会被当作通过。
这是起草流程第 7 步"成稿自检"的一个辅助工具，不能替代人工通读与 red-flags.md 扫描。

仅用标准库，无需安装依赖。
"""

import io
import json
import re
import sys

# Windows 控制台默认 gbk 编码，报告里含中文标点与箭头符号，强制 utf-8 输出避免编码错误
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


TOLERANCE_PCT = 0.05      # 百分比求和的容差（个百分点），对应 data-and-tables.md 的 ±0.01% 精神，
                           # 但实际表格常有舍入误差，放宽到 0.05 个百分点更实用
TOLERANCE_AMT_REL = 0.005 # 金额类求和的相对容差（0.5%），覆盖千分位/四舍五入误差


def parse_num(cell):
    """把表格单元格文本解析成 float；解析不出（含占位符、空值）时返回 None。"""
    if cell is None:
        return None
    s = str(cell).strip()
    if s == "" or s in ("-", "—", "/", "无", "×", "××", "XX", "N/A"):
        return None
    # 去掉常见单位与修饰：万元、亿元、元、%、逗号、括号内注释
    s = re.sub(r"[（(].*?[）)]", "", s)
    s = s.replace(",", "").replace("，", "")
    s = s.replace("万元", "").replace("亿元", "").replace("元", "")
    is_pct = "%" in s
    s = s.replace("%", "").strip()
    if s == "" or "×" in s or "X" in s.upper():
        return None
    try:
        val = float(s)
    except ValueError:
        return None
    return val


def find_col(header, *keywords):
    """在表头里找第一个包含全部关键词之一分组的列索引；返回 None 表示未找到。"""
    for i, h in enumerate(header):
        for kw in keywords:
            if kw in h:
                return i
    return None


def collect_tables(blocks):
    """遍历 content.json 的 blocks，收集所有 table，并记录其前置标题路径便于报告定位。"""
    tables = []
    heading_stack = []
    for b in blocks:
        t = b.get("type")
        if t in ("h1", "h2", "h3", "h4"):
            level = int(t[1])
            heading_stack = heading_stack[: level - 1] + [b.get("text", "")]
        elif t == "table":
            tables.append({
                "path": " / ".join(heading_stack),
                "header": b.get("header", []),
                "rows": b.get("rows", []),
                "widths": b.get("widths"),
            })
    return tables


def is_total_row(row, name_col=0):
    label = str(row[name_col]) if name_col < len(row) else ""
    return any(k in label for k in ("合计", "总计", "小计"))


class Report:
    def __init__(self):
        self.items = []  # (status, code, message)  status: PASS/FAIL/SKIP

    def add(self, status, code, message):
        self.items.append((status, code, message))

    def render(self):
        lines = []
        counts = {"PASS": 0, "FAIL": 0, "SKIP": 0}
        for status, code, message in self.items:
            counts[status] += 1
            mark = {"PASS": "✓", "FAIL": "✗", "SKIP": "·"}[status]
            lines.append(f"[{mark} {status}] {code}  {message}")
        summary = (
            f"\n共 {len(self.items)} 项：通过 {counts['PASS']} / "
            f"不一致 {counts['FAIL']} / 跳过（数据不足）{counts['SKIP']}"
        )
        if counts["FAIL"] > 0:
            summary += "\n\n存在不一致项，对照 data-and-tables.md 第三节逐项核实原始数据后再交付。"
        elif counts["SKIP"] == len(self.items):
            summary += "\n\n未发现任何可核验的数值表格（内容可能仍是骨架占位），补齐数据后重新运行。"
        return "\n".join(lines) + summary


def check_percentage_sum(report, code, table, pct_col, name_col=0, expect=100.0, label=""):
    rows = [r for r in table["rows"] if not is_total_row(r, name_col)]
    vals = [parse_num(r[pct_col]) for r in rows if pct_col < len(r)]
    vals = [v for v in vals if v is not None]
    if len(vals) < 2:
        report.add("SKIP", code, f"{label}（{table['path']}）：可解析的百分比数据不足，跳过求和校验")
        return
    total = sum(vals)
    if abs(total - expect) <= TOLERANCE_PCT:
        report.add("PASS", code, f"{label}（{table['path']}）：Σ={total:.4f}%，与 {expect}% 相符")
    else:
        report.add(
            "FAIL", code,
            f"{label}（{table['path']}）：Σ={total:.4f}%，与预期 {expect}% 相差 {total - expect:+.4f} 个百分点——"
            f"数据口径不一致，需进一步核实"
        )


def check_amount_sum_vs_total(report, code, table, amt_col, name_col=0, label=""):
    detail_rows = [r for r in table["rows"] if not is_total_row(r, name_col)]
    total_rows = [r for r in table["rows"] if is_total_row(r, name_col)]
    detail_vals = [parse_num(r[amt_col]) for r in detail_rows if amt_col < len(r)]
    detail_vals = [v for v in detail_vals if v is not None]
    if len(detail_vals) < 1:
        report.add("SKIP", code, f"{label}（{table['path']}）：明细金额数据不足，跳过")
        return
    detail_sum = sum(detail_vals)
    if not total_rows:
        report.add("SKIP", code, f"{label}（{table['path']}）：未找到合计行，明细之和={detail_sum:.2f}，无法比对")
        return
    total_val = parse_num(total_rows[0][amt_col]) if amt_col < len(total_rows[0]) else None
    if total_val is None:
        report.add("SKIP", code, f"{label}（{table['path']}）：合计行未填数值，跳过")
        return
    rel_diff = abs(detail_sum - total_val) / total_val if total_val else 0
    if rel_diff <= TOLERANCE_AMT_REL:
        report.add("PASS", code, f"{label}（{table['path']}）：明细之和={detail_sum:.2f}，合计行={total_val:.2f}，相符")
    else:
        report.add(
            "FAIL", code,
            f"{label}（{table['path']}）：明细之和={detail_sum:.2f} 与合计行={total_val:.2f} 不符——"
            f"重算为准，正文与表格需一并核实"
        )


def check_shareholder_table(report, table):
    header = table["header"]
    pct_col = find_col(header, "持股比例", "股权比例")
    if pct_col is not None:
        check_percentage_sum(report, "T10/T12-持股比例求和", table, pct_col, label="股东/股权变动表持股比例")
    subscribed_col = find_col(header, "认缴出资")
    paid_col = find_col(header, "实缴出资")
    for col, tag in ((subscribed_col, "认缴出资"), (paid_col, "实缴出资")):
        if col is not None:
            check_amount_sum_vs_total(report, f"T10/T12-{tag}求和", table, col, label=f"股东/股权变动表{tag}")


def check_personnel_table(report, table):
    header = table["header"]
    if find_col(header, "专业") is None:
        return
    count_col = find_col(header, "人数")
    pct_col = find_col(header, "占比")
    if count_col is not None:
        check_amount_sum_vs_total(report, "T3-人员数求和", table, count_col, label="人员专业结构表人数")
    if pct_col is not None:
        check_percentage_sum(report, "T3-人员占比求和", table, pct_col, label="人员专业结构表占比")


def check_customer_supplier_table(report, table):
    header = table["header"]
    if find_col(header, "客户名称") is None and find_col(header, "供应商名称") is None:
        return
    amt_col = find_col(header, "销售金额", "采购金额")
    if amt_col is None:
        return
    # 按"年度"列分组分别核验合计（同一张表可能含多个年度的明细+合计）
    year_col = find_col(header, "年度")
    if year_col is None:
        check_amount_sum_vs_total(report, "T8/T9-金额求和", table, amt_col, label="客户/供应商表金额")
        return
    groups = {}
    for row in table["rows"]:
        year = row[year_col] if year_col < len(row) else ""
        groups.setdefault(year, []).append(row)
    for year, rows in groups.items():
        sub_table = {"path": f"{table['path']}［{year or '未标注年度'}］", "rows": rows}
        check_amount_sum_vs_total(report, "T8/T9-金额求和", sub_table, amt_col, label="客户/供应商表金额")


def check_financial_table(report, table):
    header = table["header"]
    if not header or "财务指标" not in str(header[0]):
        return
    period_cols = list(range(1, len(header)))
    row_index = {row[0]: row for row in table["rows"] if row}
    for col in period_cols:
        period_label = header[col]
        assets = parse_num(row_index.get("资产总计", [None] * 10)[col]) if "资产总计" in row_index else None
        liab = parse_num(row_index.get("负债合计", [None] * 10)[col]) if "负债合计" in row_index else None
        equity = parse_num(row_index.get("所有者权益合计", [None] * 10)[col]) if "所有者权益合计" in row_index else None
        if assets is not None and liab is not None and equity is not None:
            diff = assets - (liab + equity)
            rel = abs(diff) / assets if assets else 0
            if rel <= TOLERANCE_AMT_REL:
                report.add("PASS", "T14-资产负债恒等式", f"{table['path']}［{period_label}］：资产≈负债+权益（差 {diff:+.2f} 万元）")
            else:
                report.add("FAIL", "T14-资产负债恒等式", f"{table['path']}［{period_label}］：资产={assets:.2f}，负债+权益={liab + equity:.2f}，差 {diff:+.2f} 万元——需核实")
        else:
            report.add("SKIP", "T14-资产负债恒等式", f"{table['path']}［{period_label}］：资产/负债/权益数据不全，跳过")

        revenue = parse_num(row_index.get("营业收入", [None] * 10)[col]) if "营业收入" in row_index else None
        cost = parse_num(row_index.get("营业成本", [None] * 10)[col]) if "营业成本" in row_index else None
        margin = parse_num(row_index.get("毛利率", [None] * 10)[col]) if "毛利率" in row_index else None
        if revenue is not None and cost is not None and margin is not None and revenue != 0:
            recomputed = (revenue - cost) / revenue * 100
            diff = recomputed - margin
            if abs(diff) <= TOLERANCE_PCT * 4:  # 毛利率反算容差略放宽（原始数据常四舍五入）
                report.add("PASS", "T14-毛利率反算", f"{table['path']}［{period_label}］：反算 {recomputed:.2f}% ≈ 表列 {margin:.2f}%")
            else:
                report.add("FAIL", "T14-毛利率反算", f"{table['path']}［{period_label}］：反算 {recomputed:.2f}% 与表列 {margin:.2f}% 相差 {diff:+.2f} 个百分点——需核实")
        else:
            report.add("SKIP", "T14-毛利率反算", f"{table['path']}［{period_label}］：收入/成本/毛利率数据不全，跳过")


def check_business_registration_cross(report, tables):
    biz_table = None
    shareholder_tables = []
    for t in tables:
        header = t["header"]
        if find_col(header, "项目") is not None and any("内容" in h for h in header):
            biz_table = t
        if find_col(header, "持股比例") is not None and find_col(header, "认缴出资") is not None:
            shareholder_tables.append(t)
    if biz_table is None or not shareholder_tables:
        report.add("SKIP", "T1↔T10-注册资本一致性", "未同时找到工商信息表与股东结构表，跳过")
        return
    reg_capital = None
    paid_capital = None
    for row in biz_table["rows"]:
        if len(row) < 2:
            continue
        if "注册资本" in str(row[0]):
            reg_capital = parse_num(row[1])
        if "实缴资本" in str(row[0]):
            paid_capital = parse_num(row[1])
    st = shareholder_tables[0]
    header = st["header"]
    sub_col = find_col(header, "认缴出资")
    paid_col = find_col(header, "实缴出资")
    if reg_capital is not None and sub_col is not None:
        detail_vals = [parse_num(r[sub_col]) for r in st["rows"] if not is_total_row(r) and sub_col < len(r)]
        detail_vals = [v for v in detail_vals if v is not None]
        if detail_vals:
            total = sum(detail_vals)
            rel = abs(total - reg_capital) / reg_capital if reg_capital else 0
            if rel <= TOLERANCE_AMT_REL:
                report.add("PASS", "T1↔T10-注册资本一致性", f"工商表注册资本={reg_capital:.2f}，股东表认缴合计={total:.2f}，相符")
            else:
                report.add("FAIL", "T1↔T10-注册资本一致性", f"工商表注册资本={reg_capital:.2f} 与股东表认缴合计={total:.2f} 不一致——需进一步核实")
        else:
            report.add("SKIP", "T1↔T10-注册资本一致性", "股东表认缴数据不足，跳过")
    else:
        report.add("SKIP", "T1↔T10-注册资本一致性", "工商表或股东表数据缺失，跳过")

    if paid_capital is not None and paid_col is not None:
        detail_vals = [parse_num(r[paid_col]) for r in st["rows"] if not is_total_row(r) and paid_col < len(r)]
        detail_vals = [v for v in detail_vals if v is not None]
        if detail_vals:
            total = sum(detail_vals)
            rel = abs(total - paid_capital) / paid_capital if paid_capital else 0
            if rel <= TOLERANCE_AMT_REL:
                report.add("PASS", "T1↔T10-实缴资本一致性", f"工商表实缴资本={paid_capital:.2f}，股东表实缴合计={total:.2f}，相符")
            else:
                report.add("FAIL", "T1↔T10-实缴资本一致性", f"工商表实缴资本={paid_capital:.2f} 与股东表实缴合计={total:.2f} 不一致——需进一步核实")
        else:
            report.add("SKIP", "T1↔T10-实缴资本一致性", "股东表实缴数据不足，跳过")
    else:
        report.add("SKIP", "T1↔T10-实缴资本一致性", "工商表或股东表实缴数据缺失，跳过")


def main():
    if len(sys.argv) != 2:
        print("用法：python reconcile_check.py content.json")
        sys.exit(1)
    path = sys.argv[1]
    with open(path, "r", encoding="utf-8") as f:
        content = json.load(f)

    blocks = content.get("blocks", [])
    tables = collect_tables(blocks)
    if not tables:
        print("未在 content.json 中找到任何 table 块，无法核验。")
        sys.exit(1)

    report = Report()
    for t in tables:
        check_shareholder_table(report, t)
        check_personnel_table(report, t)
        check_customer_supplier_table(report, t)
        check_financial_table(report, t)
    check_business_registration_cross(report, tables)

    print(f"共扫描 {len(tables)} 张表格。\n")
    print(report.render())

    if any(status == "FAIL" for status, _, _ in report.items):
        sys.exit(2)


if __name__ == "__main__":
    main()
