"""HTML report generator for Excel audit results.

Produces a single self-contained HTML file with:
- Metadata header and overview summary cards
- JS-powered tabs, one per period
- Section 2: Health Check (duplicates + totals consistency)
- Section 3: Excel vs DB comparison (aggregates + per-deal diff tables)
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from .comparator import DealDiff, OnlySideDeal, PeriodComparison
from .config import AuditConfig
from .health_checker import PeriodHealthReport

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ZERO = Decimal("0")
_DEFAULT_CONFIG = AuditConfig()
_DEFAULT_THRESHOLD = _DEFAULT_CONFIG.threshold
_DEFAULT_SHOW_WARNINGS = _DEFAULT_CONFIG.show_warnings


def _fmt(value: Decimal | None, decimals: int = 2) -> str:
    """Format Decimal as a locale-style number string."""
    if value is None:
        return "—"
    return f"{value:,.{decimals}f}".replace(",", " ")


def _delta_class(delta: Decimal | None, threshold: Decimal = _DEFAULT_THRESHOLD) -> str:
    """CSS class based on absolute delta relative to threshold."""
    if delta is None:
        return ""
    if delta == _ZERO:
        return "ok"
    if delta <= threshold:
        return "warn"
    return "fail"


def _pct(a: Decimal, b: Decimal) -> str:
    """Format percentage difference (a-b)/b * 100."""
    if b == _ZERO:
        return "—"
    pct = (a - b) / abs(b) * 100
    sign = "+" if pct > 0 else ""
    return f"{sign}{pct:.2f}%"


# ---------------------------------------------------------------------------
# CSS + JS
# ---------------------------------------------------------------------------

_CSS = """
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Segoe UI', system-ui, sans-serif;
    background: #f0f2f5;
    color: #1a1a2e;
    font-size: 14px;
    line-height: 1.5;
  }
  /* ---- header ---- */
  .page-header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 60%, #0f3460 100%);
    color: #e0e0e0;
    padding: 24px 32px 20px;
    border-bottom: 3px solid #e94560;
  }
  .page-header h1 { font-size: 22px; font-weight: 700; letter-spacing: .5px; }
  .page-header .meta { font-size: 12px; color: #9eb3c2; margin-top: 6px; }
  .page-header .meta span { margin-right: 20px; }

  /* ---- overview cards ---- */
  .cards { display: flex; flex-wrap: wrap; gap: 14px; padding: 20px 32px; }
  .card {
    background: #fff;
    border-radius: 8px;
    padding: 16px 20px;
    min-width: 160px;
    box-shadow: 0 2px 8px rgba(0,0,0,.08);
    border-top: 4px solid #0f3460;
  }
  .card.card-ok   { border-top-color: #27ae60; }
  .card.card-warn { border-top-color: #f39c12; }
  .card.card-fail { border-top-color: #e74c3c; }
  .card .card-val { font-size: 28px; font-weight: 700; color: #1a1a2e; }
  .card .card-lbl { font-size: 12px; color: #7f8c8d; margin-top: 4px; }

  /* ---- tab navigation ---- */
  .tabs-nav {
    display: flex; flex-wrap: wrap; gap: 4px;
    padding: 0 32px;
    border-bottom: 2px solid #dde1e7;
    background: #fff;
  }
  .tab-btn {
    padding: 10px 18px;
    border: none; border-bottom: 3px solid transparent;
    background: transparent;
    cursor: pointer; font-size: 13px; font-weight: 600;
    color: #7f8c8d;
    margin-bottom: -2px;
    transition: color .15s, border-color .15s;
  }
  .tab-btn:hover { color: #0f3460; }
  .tab-btn.active { color: #0f3460; border-bottom-color: #e94560; }
  .tab-badge {
    display: inline-block;
    background: #e94560; color: #fff;
    border-radius: 10px; font-size: 10px; font-weight: 700;
    padding: 1px 6px; margin-left: 5px;
  }
  .tab-badge.ok { background: #27ae60; }

  /* ---- tab panels ---- */
  .tab-panel { display: none; padding: 24px 32px; }
  .tab-panel.active { display: block; }

  /* ---- section titles ---- */
  .section { margin-bottom: 28px; }
  .section-title {
    font-size: 15px; font-weight: 700;
    color: #1a1a2e;
    padding: 8px 0 8px 12px;
    border-left: 4px solid #0f3460;
    margin-bottom: 14px;
  }
  .subsection { margin-bottom: 20px; }
  .subsection-title {
    font-size: 13px; font-weight: 600;
    color: #34495e;
    margin-bottom: 8px;
  }
  .summary-line {
    font-size: 13px;
    color: #555;
    background: #f7f9fc;
    padding: 8px 14px;
    border-radius: 6px;
    margin-bottom: 10px;
    border-left: 3px solid #bdc3c7;
  }
  .summary-line.ok   { border-left-color: #27ae60; color: #1e8449; }
  .summary-line.warn { border-left-color: #f39c12; color: #9a6700; }
  .summary-line.fail { border-left-color: #e74c3c; color: #922b21; }

  /* ---- tables ---- */
  .tbl-wrap { overflow-x: auto; }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
    background: #fff;
    border-radius: 6px;
    overflow: hidden;
    box-shadow: 0 1px 4px rgba(0,0,0,.06);
  }
  thead th {
    background: #1a1a2e;
    color: #e0e0e0;
    padding: 9px 12px;
    text-align: left;
    font-weight: 600;
    white-space: nowrap;
  }
  tbody tr:nth-child(even) { background: #f7f9fc; }
  tbody tr:hover { background: #eef2f7; }
  td { padding: 7px 12px; border-bottom: 1px solid #ecf0f1; vertical-align: middle; }
  td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }

  /* ---- status badges ---- */
  .badge {
    display: inline-block;
    padding: 2px 8px; border-radius: 10px;
    font-size: 11px; font-weight: 700; text-transform: uppercase;
  }
  .badge.ok   { background: #d5f5e3; color: #1e8449; }
  .badge.warn { background: #fef9e7; color: #9a6700; }
  .badge.fail { background: #fadbd8; color: #922b21; }
  .badge.info { background: #d6eaf8; color: #1a5276; }

  /* ---- delta coloring ---- */
  .ok   { color: #1e8449; }
  .warn { color: #9a6700; font-weight: 600; }
  .fail { color: #922b21; font-weight: 700; }

  /* ---- empty state ---- */
  .empty {
    text-align: center; color: #aaa;
    padding: 20px; font-style: italic;
  }

  /* ---- aggregates diff table ---- */
  .agg-table thead th { background: #0f3460; }

  /* ---- footer ---- */
  .page-footer {
    text-align: center;
    padding: 16px;
    font-size: 11px;
    color: #aaa;
    border-top: 1px solid #dde1e7;
    margin-top: 20px;
  }
</style>
"""

_JS = """
<script>
  function showTab(periodId) {
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('panel-' + periodId).classList.add('active');
    document.getElementById('btn-' + periodId).classList.add('active');
  }
  // Activate first tab on load
  document.addEventListener('DOMContentLoaded', function() {
    var first = document.querySelector('.tab-btn');
    if (first) first.click();
  });
</script>
"""


# ---------------------------------------------------------------------------
# Render helpers
# ---------------------------------------------------------------------------

def _safe_id(period_name: str) -> str:
    """Convert period name to a safe HTML id (replace spaces/non-ascii)."""
    return period_name.replace(" ", "_").replace("/", "_")


def _render_overview_cards(
    health_reports: list[PeriodHealthReport],
    comparisons: list[PeriodComparison],
    show_warnings: bool = _DEFAULT_SHOW_WARNINGS,
) -> str:
    """Render the top-level summary cards."""
    total_deals = sum(h.total_deals for h in health_reports)
    total_positions = sum(h.total_positions for h in health_reports)
    total_dups = sum(len(h.duplicates) for h in health_reports)
    total_fails = sum(h.fail_count for h in health_reports)
    total_warns = sum(h.warn_count for h in health_reports)
    total_only_excel = sum(len(c.only_in_excel) for c in comparisons)
    total_only_db = sum(len(c.only_in_db) for c in comparisons)
    total_diffs = sum(len(c.diffs) for c in comparisons)

    def card(val: Any, label: str, kind: str = "") -> str:
        klass = f"card card-{kind}" if kind else "card"
        return f'<div class="{klass}"><div class="card-val">{val}</div><div class="card-lbl">{label}</div></div>'

    health_kind = "ok" if (total_dups == 0 and total_fails == 0) else (
        "warn" if total_fails == 0 else "fail"
    )
    cmp_kind = "ok" if (total_only_excel == 0 and total_only_db == 0 and total_diffs == 0) else "fail"

    if show_warnings:
        health_card = card(
            f"{total_fails} / {total_warns}",
            "Ошибок / Предупреждений итогов",
            health_kind,
        )
    else:
        health_card = card(
            total_fails,
            "Ошибок итогов (FAIL)",
            "ok" if total_fails == 0 else "fail",
        )

    cards = [
        card(len(health_reports), "Периодов"),
        card(total_deals, "Сделок в Excel"),
        card(total_positions, "Позиций в Excel"),
        card(total_dups, "Дублей deal_key", "ok" if total_dups == 0 else "fail"),
        health_card,
        card(total_only_excel, "Только в Excel", cmp_kind if total_only_excel else "ok"),
        card(total_only_db, "Только в БД", cmp_kind if total_only_db else "ok"),
        card(total_diffs, "Расхождений по сделкам", cmp_kind if total_diffs else "ok"),
    ]
    return '<div class="cards">' + "".join(cards) + "</div>"


def _render_tab_nav(
    health_reports: list[PeriodHealthReport],
    comparisons: list[PeriodComparison],
    show_warnings: bool = _DEFAULT_SHOW_WARNINGS,
) -> str:
    """Render the tab navigation bar."""
    cmp_map = {c.period_name: c for c in comparisons}
    buttons = []
    for h in health_reports:
        pid = _safe_id(h.period_name)
        issues = len(h.duplicates) + h.fail_count
        if show_warnings:
            issues += h.warn_count
        c = cmp_map.get(h.period_name)
        cmp_issues = (len(c.only_in_excel) + len(c.only_in_db) + len(c.diffs)) if c else 0
        total_issues = issues + cmp_issues
        if total_issues == 0:
            badge = '<span class="tab-badge ok">OK</span>'
        else:
            badge = f'<span class="tab-badge">{total_issues}</span>'
        buttons.append(
            f'<button class="tab-btn" id="btn-{pid}" onclick="showTab(\'{pid}\')">'
            f'{h.period_name}{badge}</button>'
        )
    return '<div class="tabs-nav">' + "\n".join(buttons) + "</div>"


# --- Section 2: Health Check ---

def _render_duplicates(report: PeriodHealthReport) -> str:
    if not report.duplicates:
        return '<p class="empty">Дублей не обнаружено</p>'
    rows = "".join(
        f"<tr><td>{d.deal_key}</td><td class='num'>{d.count}</td></tr>"
        for d in report.duplicates
    )
    return (
        '<div class="tbl-wrap"><table>'
        "<thead><tr><th>deal_key</th><th class='num'>Кол-во вхождений</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></div>"
    )


def _render_totals_issues(
    report: PeriodHealthReport,
    show_warnings: bool = _DEFAULT_SHOW_WARNINGS,
) -> str:
    issues = report.totals_issues
    if not show_warnings:
        issues = [i for i in issues if i.level != "WARN"]
    if not issues:
        return '<p class="empty">Расхождений итогов не обнаружено</p>'

    field_labels = {"revenue": "Выручка", "margin": "Маржа", "cost": "Себестоимость"}
    rows = []
    for i in issues:
        lvl_badge = f'<span class="badge {i.level.lower()}">{i.level}</span>'
        rows.append(
            f"<tr>"
            f"<td>{i.deal_key}</td>"
            f"<td>{field_labels.get(i.field, i.field)}</td>"
            f"<td class='num'>{_fmt(i.master_value)}</td>"
            f"<td class='num'>{_fmt(i.calc_value)}</td>"
            f"<td class='num {i.level.lower()}'>{_fmt(i.delta)}</td>"
            f"<td>{lvl_badge}</td>"
            f"</tr>"
        )
    return (
        '<div class="tbl-wrap"><table>'
        "<thead><tr>"
        "<th>deal_key</th><th>Поле</th>"
        "<th class='num'>Значение мастер-строки</th><th class='num'>Сумма позиций</th>"
        "<th class='num'>Δ</th><th>Уровень</th>"
        "</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def _render_health_section(
    report: PeriodHealthReport,
    show_warnings: bool = _DEFAULT_SHOW_WARNINGS,
) -> str:
    fails = report.fail_count
    warns = report.warn_count
    visible_issues_count = fails + (warns if show_warnings else 0)
    total_issues = len(report.duplicates) + visible_issues_count

    if total_issues == 0:
        summary_cls, summary_txt = "ok", "Здоровье файла: все проверки пройдены"
    elif fails > 0:
        summary_cls = "fail"
        parts = [f"Дублей: {len(report.duplicates)}", f"Расхождений (FAIL): {fails}"]
        if show_warnings:
            parts.append(f"Предупреждений (WARN): {warns}")
        summary_txt = " | ".join(parts)
    else:
        summary_cls = "warn"
        summary_txt = (
            f"Дублей: {len(report.duplicates)} | "
            f"Предупреждений (WARN): {warns}"
        )

    visible_totals_count = visible_issues_count

    return f"""
<div class="section">
  <div class="section-title">2. Проверка здоровья Excel</div>
  <div class="summary-line {summary_cls}">{summary_txt}</div>

  <div class="subsection">
    <div class="subsection-title">2.1 Дубли по deal_key ({len(report.duplicates)})</div>
    {_render_duplicates(report)}
  </div>

  <div class="subsection">
    <div class="subsection-title">
      2.2 Расхождение итогов мастер-строки и позиций ({visible_totals_count})
    </div>
    {_render_totals_issues(report, show_warnings)}
  </div>
</div>
"""


# --- Section 3: Comparison ---

def _render_aggregates_table(
    cmp: PeriodComparison,
    threshold: Decimal = _DEFAULT_THRESHOLD,
) -> str:
    xl = cmp.excel_agg
    db = cmp.db_agg

    def row(label: str, xl_val: Decimal, db_val: Decimal) -> str:
        delta = xl_val - db_val
        cls = _delta_class(abs(delta), threshold)
        sign = "+" if delta > _ZERO else ""
        return (
            f"<tr><td>{label}</td>"
            f"<td class='num'>{_fmt(xl_val)}</td>"
            f"<td class='num'>{_fmt(db_val)}</td>"
            f"<td class='num {cls}'>{sign}{_fmt(delta)}</td>"
            f"<td class='num {cls}'>{_pct(xl_val, db_val)}</td>"
            "</tr>"
        )

    rows = [
        row("Выручка", xl.revenue, db.revenue),
        row("Маржа", xl.margin, db.margin),
        row("Себестоимость", xl.cost, db.cost),
        f"<tr><td>Сделок</td>"
        f"<td class='num'>{xl.deal_count}</td>"
        f"<td class='num'>{db.deal_count}</td>"
        f"<td class='num {_delta_class(abs(Decimal(xl.deal_count - db.deal_count)), threshold)}'>"
        f"{xl.deal_count - db.deal_count:+d}</td><td>—</td></tr>",
        f"<tr><td>Позиций</td>"
        f"<td class='num'>{xl.position_count}</td>"
        f"<td class='num'>{db.position_count}</td>"
        f"<td class='num {_delta_class(abs(Decimal(xl.position_count - db.position_count)), threshold)}'>"
        f"{xl.position_count - db.position_count:+d}</td><td>—</td></tr>",
    ]

    return (
        '<div class="tbl-wrap"><table class="agg-table">'
        "<thead><tr><th>Метрика</th><th class='num'>Excel</th><th class='num'>БД</th><th class='num'>Δ</th><th class='num'>Δ%</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def _render_one_side_table(deals: list[OnlySideDeal], side: str) -> str:
    if not deals:
        return f'<p class="empty">Нет сделок только в {side}</p>'
    rows = "".join(
        f"<tr>"
        f"<td>{d.deal_key}</td>"
        f"<td class='num'>{_fmt(d.revenue)}</td>"
        f"<td class='num'>{_fmt(d.margin)}</td>"
        f"<td class='num'>{_fmt(d.cost)}</td>"
        f"</tr>"
        for d in deals
    )
    return (
        '<div class="tbl-wrap"><table>'
        "<thead><tr><th>deal_key</th>"
        "<th class='num'>Выручка</th><th class='num'>Маржа</th><th class='num'>Себестоимость</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></div>"
    )


def _render_diffs_table(
    diffs: list[DealDiff],
    threshold: Decimal = _DEFAULT_THRESHOLD,
) -> str:
    if not diffs:
        return '<p class="empty">Расхождений по сделкам не обнаружено</p>'

    def delta_cell(a: Decimal | None, b: Decimal | None) -> str:
        if a is None and b is None:
            return "<td class='num'>—</td>"
        if a is None or b is None:
            return "<td class='num fail'>нет данных</td>"
        d = a - b
        cls = _delta_class(abs(d), threshold)
        sign = "+" if d > _ZERO else ""
        return f"<td class='num {cls}'>{sign}{_fmt(d)}</td>"

    rows = []
    for diff in diffs:
        rows.append(
            f"<tr>"
            f"<td>{diff.deal_key}</td>"
            f"<td class='num'>{_fmt(diff.revenue_excel)}</td>"
            f"<td class='num'>{_fmt(diff.revenue_db)}</td>"
            f"{delta_cell(diff.revenue_excel, diff.revenue_db)}"
            f"<td class='num'>{_fmt(diff.margin_excel)}</td>"
            f"<td class='num'>{_fmt(diff.margin_db)}</td>"
            f"{delta_cell(diff.margin_excel, diff.margin_db)}"
            f"<td class='num'>{_fmt(diff.cost_excel)}</td>"
            f"<td class='num'>{_fmt(diff.cost_db)}</td>"
            f"{delta_cell(diff.cost_excel, diff.cost_db)}"
            f"</tr>"
        )
    return (
        '<div class="tbl-wrap"><table>'
        "<thead><tr>"
        "<th>deal_key</th>"
        "<th class='num'>Выручка Excel</th><th class='num'>Выручка БД</th><th class='num'>Δ Выручка</th>"
        "<th class='num'>Маржа Excel</th><th class='num'>Маржа БД</th><th class='num'>Δ Маржа</th>"
        "<th class='num'>Себест. Excel</th><th class='num'>Себест. БД</th><th class='num'>Δ Себест.</th>"
        "</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def _render_comparison_section(
    cmp: PeriodComparison,
    threshold: Decimal = _DEFAULT_THRESHOLD,
) -> str:
    total_issues = len(cmp.only_in_excel) + len(cmp.only_in_db) + len(cmp.diffs)
    if total_issues == 0:
        summary_cls, summary_txt = "ok", "Данные Excel и БД совпадают по всем сделкам"
    else:
        summary_cls = "fail"
        summary_txt = (
            f"Только в Excel: {len(cmp.only_in_excel)} | "
            f"Только в БД: {len(cmp.only_in_db)} | "
            f"Расхождений: {len(cmp.diffs)}"
        )

    return f"""
<div class="section">
  <div class="section-title">3. Сравнение Excel vs БД</div>
  <div class="summary-line {summary_cls}">{summary_txt}</div>

  <div class="subsection">
    <div class="subsection-title">3.1 Агрегаты периода</div>
    <p style="font-size:12px;color:#7f8c8d;margin-bottom:8px;">
      Excel — задекларированные итоги мастер-строки; БД — total_revenue_amount из read_deals.
    </p>
    {_render_aggregates_table(cmp, threshold)}
  </div>

  <div class="subsection">
    <div class="subsection-title">
      3.2 Сделки только в Excel ({len(cmp.only_in_excel)})
    </div>
    {_render_one_side_table(cmp.only_in_excel, "Excel")}
  </div>

  <div class="subsection">
    <div class="subsection-title">
      3.3 Сделки только в БД ({len(cmp.only_in_db)})
    </div>
    {_render_one_side_table(cmp.only_in_db, "БД")}
  </div>

  <div class="subsection">
    <div class="subsection-title">
      3.4 Расхождения по сделкам ({len(cmp.diffs)})
    </div>
    {_render_diffs_table(cmp.diffs, threshold)}
  </div>
</div>
"""


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def render_full_report(
    excel_path: str,
    health_reports: list[PeriodHealthReport],
    comparisons: list[PeriodComparison],
    generated_at: datetime | None = None,
    threshold: Decimal = _DEFAULT_THRESHOLD,
    show_warnings: bool = _DEFAULT_SHOW_WARNINGS,
) -> str:
    """Build the full HTML report string.

    Args:
        excel_path: Path to the source Excel file (shown in header).
        health_reports: One PeriodHealthReport per period, in display order.
        comparisons: One PeriodComparison per period, in the same order.
        generated_at: Report generation timestamp; defaults to now.
        threshold: Minimum absolute delta to treat as a real discrepancy.
        show_warnings: Whether to display WARN-level issues in the report.

    Returns:
        str: Complete self-contained HTML document.
    """
    generated_at = generated_at or datetime.now()
    ts = generated_at.strftime("%d.%m.%Y %H:%M:%S")
    cmp_map = {c.period_name: c for c in comparisons}

    # ---- overview ----
    overview_html = _render_overview_cards(health_reports, comparisons, show_warnings)

    # ---- tab nav ----
    tabs_nav_html = _render_tab_nav(health_reports, comparisons, show_warnings)

    # ---- tab panels ----
    panels = []
    for idx, h in enumerate(health_reports):
        pid = _safe_id(h.period_name)
        active_cls = "active" if idx == 0 else ""
        cmp = cmp_map.get(h.period_name)
        comparison_html = _render_comparison_section(cmp, threshold) if cmp else (
            '<div class="section">'
            '<div class="section-title">3. Сравнение Excel vs БД</div>'
            '<p class="empty">Данные БД недоступны для этого периода</p>'
            "</div>"
        )
        panels.append(f"""
<div class="tab-panel {active_cls}" id="panel-{pid}">
  {_render_health_section(h, show_warnings)}
  {comparison_html}
</div>
""")

    panels_html = "\n".join(panels)

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Excel Audit Report — {generated_at.strftime('%Y-%m-%d')}</title>
  {_CSS}
</head>
<body>

<div class="page-header">
  <h1>Excel Audit Report</h1>
  <div class="meta">
    <span>Файл: <b>{excel_path}</b></span>
    <span>Сформирован: <b>{ts}</b></span>
    <span>Периодов: <b>{len(health_reports)}</b></span>
  </div>
</div>

{overview_html}

{tabs_nav_html}

{panels_html}

<div class="page-footer">
  Excel Audit Dashboard &nbsp;|&nbsp; {ts}
</div>

{_JS}
</body>
</html>
"""
