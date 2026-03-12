"""
Generate HTML dashboard from DB snapshots.

Modes:
    latest  -- show the most recent snapshot
    compare -- compare two snapshots side by side
    list    -- list all available snapshots

Usage:
    python dashboard/generate_dashboard.py --mode latest
    python dashboard/generate_dashboard.py --mode compare --label1 before --label2 after
    python dashboard/generate_dashboard.py --mode compare --id1 5 --id2 6
    python dashboard/generate_dashboard.py --mode list
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import webbrowser
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "dashboard"))

from period_utils import sort_period_dicts, sort_period_items, sort_periods  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

from excel_audit.config import AuditConfig  # noqa: E402
from infrastructure.database.connection import DatabaseConfig  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

REPORTS_DIR = PROJECT_ROOT / "dashboard" / "reports"
_DEFAULT_THRESHOLD = AuditConfig().threshold


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def get_sync_engine():
    config = DatabaseConfig()
    return create_engine(config.sync_database_url, echo=False, future=True)


def load_snapshot(conn, snapshot_id: int | None = None, label: str | None = None) -> dict:
    """Load snapshot header + child rows into a plain dict."""
    if snapshot_id:
        row = conn.execute(
            text("SELECT * FROM db_snapshots WHERE id = :id"), {"id": snapshot_id}
        ).mappings().first()
    elif label:
        row = conn.execute(
            text(
                "SELECT * FROM db_snapshots WHERE label = :label "
                "ORDER BY created_at DESC LIMIT 1"
            ),
            {"label": label},
        ).mappings().first()
    else:
        row = conn.execute(
            text("SELECT * FROM db_snapshots ORDER BY created_at DESC LIMIT 1")
        ).mappings().first()

    if not row:
        return {}

    snap = dict(row)
    sid = snap["id"]

    snap["deal_periods"] = sort_period_dicts(
        [
            dict(r)
            for r in conn.execute(
                text(
                    "SELECT * FROM db_snapshot_deal_periods "
                    "WHERE snapshot_id = :sid"
                ),
                {"sid": sid},
            ).mappings().all()
        ],
        period_field="period_full_name",
    )
    snap["position_periods"] = sort_period_dicts(
        [
            dict(r)
            for r in conn.execute(
                text(
                    "SELECT * FROM db_snapshot_position_periods "
                    "WHERE snapshot_id = :sid"
                ),
                {"sid": sid},
            ).mappings().all()
        ],
        period_field="period_key",
    )

    if isinstance(snap.get("health_checks"), str):
        snap["health_checks"] = json.loads(snap["health_checks"])

    return snap


def list_snapshots(conn) -> list[dict]:
    rows = conn.execute(
        text(
            "SELECT id, label, source, deals_total_rows, pos_total_rows, created_at "
            "FROM db_snapshots ORDER BY created_at DESC LIMIT 50"
        )
    ).mappings().all()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# HTML generation helpers
# ---------------------------------------------------------------------------

def _fmt(val: Any) -> str:
    """Format a value for HTML display."""
    if val is None:
        return "-"
    if isinstance(val, Decimal):
        if val == val.to_integral_value():
            return f"{int(val):,}".replace(",", " ")
        return f"{val:,.2f}".replace(",", " ")
    if isinstance(val, float):
        return f"{val:,.2f}".replace(",", " ")
    if isinstance(val, int):
        return f"{val:,}".replace(",", " ")
    return str(val)


def _is_significant_delta(delta: Any, threshold: Decimal = _DEFAULT_THRESHOLD) -> bool:
    """Return True when absolute delta is above the configured threshold."""
    if delta is None:
        return False
    try:
        return abs(Decimal(str(delta))) > threshold
    except Exception:
        return False


def _delta_cls(delta: Any, threshold: Decimal = _DEFAULT_THRESHOLD) -> str:
    """Return CSS class for delta value using the configured threshold."""
    if delta is None:
        return ""
    try:
        d = Decimal(str(delta))
    except Exception:
        return ""
    if d == 0 or abs(d) <= threshold:
        return "ok"
    if d > 0:
        return "pos"
    return "neg"


def _status_cls(status: str) -> str:
    """Map health check status to CSS class."""
    return {"OK": "ok", "WARN": "warn", "FAIL": "fail", "INFO": "info"}.get(status, "")


CSS = """
<style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background: #f4f6f9; color: #333; padding: 20px;
    }
    h1 { font-size: 22px; margin-bottom: 6px; color: #1a1a2e; }
    h2 { font-size: 17px; margin: 24px 0 10px; color: #16213e;
         border-bottom: 2px solid #0f3460; padding-bottom: 4px; }
    h3 { font-size: 14px; margin: 16px 0 6px; color: #1a1a2e; }
    .meta { font-size: 12px; color: #666; margin-bottom: 16px; }
    .cards { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 16px; }
    .card {
        background: #fff; border-radius: 8px; padding: 14px 18px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.08); min-width: 160px; flex: 1;
    }
    .card .lbl { font-size: 11px; color: #888; text-transform: uppercase;
                 letter-spacing: 0.5px; }
    .card .val { font-size: 22px; font-weight: 700; margin-top: 4px; }
    table {
        width: 100%; border-collapse: collapse; font-size: 12px;
        background: #fff; border-radius: 6px; overflow: hidden;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06); margin-bottom: 16px;
    }
    th {
        background: #1a1a2e; color: #fff; padding: 8px 10px;
        text-align: left; font-weight: 600; white-space: nowrap;
    }
    td { padding: 6px 10px; border-bottom: 1px solid #eee; white-space: nowrap; }
    tr:nth-child(even) td { background: #fafbfc; }
    tr:hover td { background: #f0f4ff; }
    tr.totals td { font-weight: 700; background: #e8ecf1; border-top: 2px solid #1a1a2e; }
    .ok { color: #27ae60; }
    .warn { color: #e67e22; }
    .fail { color: #e74c3c; font-weight: 700; }
    .info { color: #3498db; }
    .pos { color: #27ae60; }
    .neg { color: #e74c3c; }
    .health-grid {
        display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
        gap: 10px; margin-bottom: 16px;
    }
    .health-item {
        background: #fff; border-radius: 6px; padding: 10px 14px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        border-left: 4px solid #ddd;
    }
    .health-item.ok { border-left-color: #27ae60; }
    .health-item.warn { border-left-color: #e67e22; }
    .health-item.fail { border-left-color: #e74c3c; }
    .health-item.info { border-left-color: #3498db; }
    .health-item .title { font-weight: 600; font-size: 12px; margin-bottom: 4px; }
    .health-item .detail { font-size: 11px; color: #555; }
    .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
    @media (max-width: 900px) { .two-col { grid-template-columns: 1fr; } }
    .delta-cell { font-weight: 600; }
    .delta-cell a { color: inherit; text-decoration: underline dotted; cursor: pointer; }
    .delta-cell a:hover { text-decoration: underline solid; }
    .fail a { color: inherit; text-decoration: underline dotted; cursor: pointer; }
    .fail a:hover { text-decoration: underline solid; }
    .compare-header { display: flex; gap: 20px; margin-bottom: 12px; flex-wrap: wrap; }
    .snap-badge {
        background: #fff; border-radius: 6px; padding: 10px 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06); flex: 1; min-width: 280px;
    }
    .snap-badge .snap-label { font-weight: 700; font-size: 15px; }
    .snap-badge .snap-label a {
        color: #1a1a2e; text-decoration: none; border-bottom: 2px dashed #3498db;
    }
    .snap-badge .snap-label a:hover { border-bottom-style: solid; color: #3498db; }
    .snap-badge .snap-meta { font-size: 11px; color: #666; margin-top: 2px; }
</style>
"""


# ---------------------------------------------------------------------------
# Block renderers -- latest mode
# ---------------------------------------------------------------------------

def _render_overview_cards(snap: dict) -> str:
    """Block 1: Overview cards."""
    cards = [
        ("Deals rows", snap.get("deals_total_rows", 0)),
        ("Positions rows", snap.get("pos_total_rows", 0)),
        ("Unique deal_key (D)", snap.get("deals_unique_deal_key", 0)),
        ("Unique deal_key (P)", snap.get("pos_unique_deal_key", 0)),
        ("Unique clients (D)", snap.get("deals_unique_client", 0)),
        ("Unique clients (P)", snap.get("pos_unique_client", 0)),
        ("Unique periods (D)", snap.get("deals_unique_period", 0)),
        ("Unique periods (P)", snap.get("pos_unique_period", 0)),
        ("Products", snap.get("pos_unique_product", 0)),
        ("Suppliers", snap.get("pos_unique_supplier", 0)),
    ]
    html = '<div class="cards">'
    for lbl, val in cards:
        html += f'<div class="card"><div class="lbl">{lbl}</div>'
        html += f'<div class="val">{_fmt(val)}</div></div>'
    html += "</div>"
    return html


def _render_financial_table(
    snap: dict,
    period_links: dict[str, str] | None = None,
    threshold: Decimal = _DEFAULT_THRESHOLD,
) -> str:
    """Block 2: Financial totals -- deals vs positions side by side."""
    all_href = (period_links or {}).get("__ALL__")
    rows_data = [
        ("Revenue", "deals_sum_revenue", "pos_sum_revenue"),
        ("Margin", "deals_sum_margin", "pos_sum_margin"),
        ("Cost", "deals_sum_cost", "pos_sum_cost"),
        ("Kickback", "deals_sum_kickback", None),
        ("Calc Revenue", "deals_sum_calc_revenue", None),
        ("Calc Margin", "deals_sum_calc_margin", None),
        ("Calc Cost", "deals_sum_calc_cost", None),
        ("Items Count", "deals_sum_items_count", None),
        ("Quantity", "deals_sum_quantity", "pos_sum_quantity"),
        ("has_totals_error", "deals_has_error_count", None),
    ]
    html = "<table><tr><th>Metric</th><th>read_deals</th>"
    html += "<th>read_positions</th><th>Delta</th></tr>"
    for label, dk, pk in rows_data:
        d_val = snap.get(dk, 0) or 0
        p_val = snap.get(pk, 0) if pk else None
        if p_val is not None:
            delta = Decimal(str(d_val)) - Decimal(str(p_val))
            cls = _delta_cls(delta, threshold)
            html += f"<tr><td>{label}</td><td>{_fmt(d_val)}</td>"
            if _is_significant_delta(delta, threshold) and all_href:
                html += (
                    f'<td>{_fmt(p_val)}</td>'
                    f'<td class="delta-cell {cls}">'
                    f'<a href="{all_href}" target="_blank">{_fmt(delta)}</a></td></tr>'
                )
            else:
                html += (
                    f'<td>{_fmt(p_val)}</td>'
                    f'<td class="delta-cell {cls}">{_fmt(delta)}</td></tr>'
                )
        else:
            html += f"<tr><td>{label}</td><td>{_fmt(d_val)}</td>"
            html += "<td>-</td><td>-</td></tr>"
    html += "</table>"
    return html


def _render_health(snap: dict) -> str:
    """Block 3: Health checks."""
    checks = snap.get("health_checks") or {}
    if not checks:
        return '<p class="ok">No health check data available.</p>'

    friendly_names = {
        "deals_rows_vs_deal_key": "Deals: rows vs unique deal_key",
        "deals_rows_vs_hash_key": "Deals: rows vs unique hash_key",
        "pos_rows_vs_hash_key": "Positions: rows vs unique hash_key",
        "cross_deal_key": "Cross: deal_key (deals vs positions)",
        "cross_client_name": "Cross: client_name (deals vs positions)",
        "cross_sum_revenue": "Cross: SUM revenue",
        "cross_sum_margin": "Cross: SUM margin",
        "cross_sum_cost": "Cross: SUM cost",
        "cross_sum_quantity": "Cross: SUM quantity",
        "has_totals_error_count": "has_totals_error count",
        "items_count_mismatch": "items_count vs actual positions",
        "deals_without_positions": "Deals without positions",
        "orphan_positions": "Orphan positions",
        "calc_vs_total_mismatch": "calc_* vs total_* mismatch",
    }

    html = '<div class="health-grid">'
    for key, data in checks.items():
        if not isinstance(data, dict):
            continue
        status = data.get("status", "")
        cls = _status_cls(status)
        name = friendly_names.get(key, key)
        details = " | ".join(
            f"{k}: {v}" for k, v in data.items() if k != "status"
        )
        html += f'<div class="health-item {cls}">'
        html += f'<div class="title">[{status}] {name}</div>'
        html += f'<div class="detail">{details}</div></div>'
    html += "</div>"
    return html


def _render_deal_periods_table(
    periods: list[dict],
    period_links: dict[str, str] | None = None,
    threshold: Decimal = _DEFAULT_THRESHOLD,
) -> str:
    """Block 4A: Deals by period."""
    if not periods:
        return "<p>No deal period data.</p>"
    links = period_links or {}

    cols = [
        ("Period", "period_full_name"),
        ("Rows", "rows_count"),
        ("Uniq DK", "unique_deal_key"),
        ("Uniq HK", "unique_hash_key"),
        ("Delta DK-HK", "delta_dk_hk"),
        ("Uniq Client", "unique_client"),
        ("Revenue", "sum_revenue"),
        ("Margin", "sum_margin"),
        ("Cost", "sum_cost"),
        ("Kickback", "sum_kickback"),
        ("Calc Rev", "sum_calc_revenue"),
        ("Calc Mrg", "sum_calc_margin"),
        ("Calc Cost", "sum_calc_cost"),
        ("Items", "sum_items_count"),
        ("Quantity", "sum_quantity"),
        ("Errors", "has_error_count"),
    ]

    html = "<table><tr>"
    for label, _ in cols:
        html += f"<th>{label}</th>"
    html += "</tr>"

    totals: dict[str, Any] = {}
    for p in periods:
        period_name = p.get("period_full_name", "")
        norm_period = _normalize_period_key(period_name)
        href = links.get(norm_period)
        html += "<tr>"
        for label, key in cols:
            val = p.get(key, 0)
            if key == "period_full_name":
                html += f"<td><strong>{val}</strong></td>"
            elif key == "has_error_count":
                cls = "ok" if (val or 0) == 0 else "fail"
                if (val or 0) != 0 and href:
                    html += (
                        f'<td class="{cls}">'
                        f'<a href="{href}" target="_blank">{_fmt(val)}</a></td>'
                    )
                else:
                    html += f'<td class="{cls}">{_fmt(val)}</td>'
            elif key == "delta_dk_hk":
                cls = _delta_cls(val or 0, threshold)
                html += f'<td class="{cls}">{_fmt(val)}</td>'
            else:
                html += f"<td>{_fmt(val)}</td>"
            if key != "period_full_name":
                totals[key] = (totals.get(key) or Decimal("0")) + Decimal(str(val or 0))
        html += "</tr>"

    html += '<tr class="totals"><td><strong>TOTAL</strong></td>'
    for _, key in cols[1:]:
        val = totals.get(key, 0)
        if key in ("delta_dk_hk", "has_error_count"):
            cls = _delta_cls(val, threshold)
            html += f'<td class="{cls}">{_fmt(val)}</td>'
        else:
            html += f"<td>{_fmt(val)}</td>"
    html += "</tr></table>"
    return html


def _render_position_periods_table(
    periods: list[dict],
    threshold: Decimal = _DEFAULT_THRESHOLD,
) -> str:
    """Block 4B: Positions by period."""
    if not periods:
        return "<p>No position period data.</p>"

    cols = [
        ("Period", "period_key"),
        ("Rows", "rows_count"),
        ("Uniq HK", "unique_hash_key"),
        ("Delta R-HK", "delta_rows_hk"),
        ("Uniq DK", "unique_deal_key"),
        ("Uniq Client", "unique_client"),
        ("Uniq Product", "unique_product"),
        ("Uniq Supplier", "unique_supplier"),
        ("Quantity", "sum_quantity"),
        ("Revenue", "sum_revenue"),
        ("Margin", "sum_margin"),
        ("Cost", "sum_cost"),
    ]

    html = "<table><tr>"
    for label, _ in cols:
        html += f"<th>{label}</th>"
    html += "</tr>"

    totals: dict[str, Any] = {}
    for p in periods:
        html += "<tr>"
        for label, key in cols:
            val = p.get(key, 0)
            if key == "period_key":
                html += f"<td><strong>{val}</strong></td>"
            elif key == "delta_rows_hk":
                cls = _delta_cls(val or 0, threshold)
                html += f'<td class="{cls}">{_fmt(val)}</td>'
            else:
                html += f"<td>{_fmt(val)}</td>"
            if key != "period_key":
                totals[key] = (totals.get(key) or Decimal("0")) + Decimal(str(val or 0))
        html += "</tr>"

    html += '<tr class="totals"><td><strong>TOTAL</strong></td>'
    for _, key in cols[1:]:
        val = totals.get(key, 0)
        if key == "delta_rows_hk":
            cls = _delta_cls(val, threshold)
            html += f'<td class="{cls}">{_fmt(val)}</td>'
        else:
            html += f"<td>{_fmt(val)}</td>"
    html += "</tr></table>"
    return html


def _normalize_period_key(key: str) -> str:
    """Normalize period key to a common format 'Month YYYY'.

    Handles different separators: 'Июнь 2025', 'Июнь.2025' -> 'Июнь 2025'.
    """
    return re.sub(r"[.\s]+", " ", key.strip())


def _render_cross_period_table(
    deal_periods: list[dict],
    pos_periods: list[dict],
    period_links: dict[str, str] | None = None,
    threshold: Decimal = _DEFAULT_THRESHOLD,
) -> str:
    """Block 4C: Cross-compare deals vs positions by period."""
    dp_map = {_normalize_period_key(p["period_full_name"]): p for p in deal_periods}
    pp_map = {_normalize_period_key(p["period_key"]): p for p in pos_periods}
    links = period_links or {}

    all_periods = sort_periods(set(dp_map.keys()) | set(pp_map.keys()))
    if not all_periods:
        return "<p>No period data to compare.</p>"

    html = """<table><tr>
        <th>Period</th>
        <th>D: deal_key</th><th>P: deal_key</th><th>Delta DK</th>
        <th>D: client</th><th>P: client</th><th>Delta Cl</th>
        <th>D: revenue</th><th>P: revenue</th><th>Delta Rev</th>
        <th>D: margin</th><th>P: margin</th><th>Delta Mrg</th>
        <th>D: cost</th><th>P: cost</th><th>Delta Cost</th>
        <th>D: CalcRev</th><th>P: revenue</th><th>Delta CRev</th>
        <th>D: CalcCost</th><th>P: cost</th><th>Delta CCost</th>
        <th>D: qty</th><th>P: qty</th><th>Delta Qty</th>
    </tr>"""

    for period in all_periods:
        dp = dp_map.get(period, {})
        pp = pp_map.get(period, {})
        href = links.get(period)
        html += f"<tr><td><strong>{period}</strong></td>"

        pairs = [
            (dp.get("unique_deal_key", 0), pp.get("unique_deal_key", 0)),
            (dp.get("unique_client", 0), pp.get("unique_client", 0)),
            (dp.get("sum_revenue", 0), pp.get("sum_revenue", 0)),
            (dp.get("sum_margin", 0), pp.get("sum_margin", 0)),
            (dp.get("sum_cost", 0), pp.get("sum_cost", 0)),
            (dp.get("sum_calc_revenue", 0), pp.get("sum_revenue", 0)),
            (dp.get("sum_calc_cost", 0), pp.get("sum_cost", 0)),
            (dp.get("sum_quantity", 0), pp.get("sum_quantity", 0)),
        ]
        for d_val, p_val in pairs:
            d = Decimal(str(d_val or 0))
            p = Decimal(str(p_val or 0))
            delta = d - p
            cls = _delta_cls(delta, threshold)
            html += f"<td>{_fmt(d)}</td><td>{_fmt(p)}</td>"
            if _is_significant_delta(delta, threshold) and href:
                html += (
                    f'<td class="delta-cell {cls}">'
                    f'<a href="{href}" target="_blank">{_fmt(delta)}</a></td>'
                )
            else:
                html += f'<td class="delta-cell {cls}">{_fmt(delta)}</td>'
        html += "</tr>"
    html += "</table>"
    return html


# ---------------------------------------------------------------------------
# Detail drill-down file generation
# ---------------------------------------------------------------------------

def _safe_filename(period: str) -> str:
    """Convert period name to safe filename component."""
    return re.sub(r"[^\w]", "_", period.strip())


DETAIL_CSS = """
<style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background: #f4f6f9; color: #333; padding: 20px;
    }
    h1 { font-size: 22px; margin-bottom: 6px; color: #1a1a2e; }
    h2 { font-size: 17px; margin: 24px 0 10px; color: #16213e;
         border-bottom: 2px solid #0f3460; padding-bottom: 4px; }
    .meta { font-size: 12px; color: #666; margin-bottom: 16px; }
    .back-link { font-size: 13px; margin-bottom: 16px; }
    .back-link a { color: #3498db; text-decoration: none; }
    .back-link a:hover { text-decoration: underline; }
    .summary { font-size: 13px; margin-bottom: 16px; color: #555; }
    table {
        width: 100%; border-collapse: collapse; font-size: 12px;
        background: #fff; border-radius: 6px; overflow: hidden;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06); margin-bottom: 20px;
    }
    th {
        background: #1a1a2e; color: #fff; padding: 8px 10px;
        text-align: left; font-weight: 600; white-space: nowrap;
    }
    td { padding: 6px 10px; border-bottom: 1px solid #eee; white-space: nowrap; }
    tr:hover td { background: #f0f4ff; }
    tr.deal-header td {
        background: #e8ecf1; font-weight: 700;
        border-top: 2px solid #1a1a2e;
    }
    tr.subtotal td {
        background: #f5f6fa; font-weight: 600; font-style: italic;
        border-bottom: 2px solid #ccc;
    }
    .ok { color: #27ae60; }
    .neg { color: #e74c3c; font-weight: 700; }
    .pos { color: #27ae60; }
    .delta-cell { font-weight: 600; }
</style>
"""


def _generate_detail_html(
    period: str,
    deals: list[dict],
    positions_by_deal: dict[str, list[dict]],
    dashboard_filename: str,
    threshold: Decimal = _DEFAULT_THRESHOLD,
) -> str:
    """Generate detail HTML page for a single period (or ALL)."""
    title = f"Detail: {period}" if period != "ALL" else "Detail: All Periods"
    summary_text = f"{len(deals)} deals with discrepancies"

    html = f"""<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">
<title>{title}</title>{DETAIL_CSS}</head><body>
<h1>{title}</h1>
<div class="back-link"><a href="{dashboard_filename}" target="_blank">&larr; Back to Dashboard</a></div>
<div class="summary">{summary_text}</div>
"""

    pos_cols = ["#", "Product", "Supplier", "Qty", "Revenue", "Margin", "Cost"]
    deal_cols = [
        "deal_key", "client", "D:Rev", "P:Rev", "dRev",
        "D:Mrg", "P:Mrg", "dMrg", "D:Cost", "P:Cost", "dCost",
        "D:Qty", "P:Qty", "dQty",
    ]

    current_period = None
    for deal in deals:
        dp = deal.get("period_full_name", "?")
        if dp != current_period:
            if current_period is not None:
                html += "</table>"
            current_period = dp
            html += f"<h2>{dp}</h2>"
            html += "<table><tr>"
            for col in deal_cols:
                html += f"<th>{col}</th>"
            html += "</tr>"

        d_rev = Decimal(str(deal.get("d_revenue") or 0))
        p_rev = Decimal(str(deal.get("p_revenue") or 0))
        d_mrg = Decimal(str(deal.get("d_margin") or 0))
        p_mrg = Decimal(str(deal.get("p_margin") or 0))
        d_cost = Decimal(str(deal.get("d_cost") or 0))
        p_cost = Decimal(str(deal.get("p_cost") or 0))
        d_qty = Decimal(str(deal.get("d_quantity") or 0))
        p_qty = Decimal(str(deal.get("p_quantity") or 0))

        deltas = [
            ("rev", d_rev, p_rev),
            ("mrg", d_mrg, p_mrg),
            ("cost", d_cost, p_cost),
            ("qty", d_qty, p_qty),
        ]

        html += '<tr class="deal-header">'
        html += f"<td>{deal.get('deal_key', '?')}</td>"
        html += f"<td>{deal.get('client_name', '?')}</td>"
        for _, d_val, p_val in deltas:
            delta = d_val - p_val
            cls = _delta_cls(delta, threshold)
            html += f"<td>{_fmt(d_val)}</td><td>{_fmt(p_val)}</td>"
            html += f'<td class="delta-cell {cls}">{_fmt(delta)}</td>'
        html += "</tr>"

        deal_id_str = str(deal.get("deal_id", ""))
        deal_positions = positions_by_deal.get(deal_id_str, [])

        if deal_positions:
            # Position header aligned: #->col0, Product->col1, Supplier->col2,
            # Revenue->col3(P:Rev), Margin->col6(P:Mrg),
            # Cost->col9(P:Cost), Qty->col12(P:Qty)
            html += "<tr>"
            html += "<td><strong>#</strong></td>"
            html += "<td><strong>Product</strong></td>"
            html += "<td><strong>Supplier</strong></td>"
            html += "<td><strong>Revenue</strong></td>"
            html += "<td colspan='2'></td>"
            html += "<td><strong>Margin</strong></td>"
            html += "<td colspan='2'></td>"
            html += "<td><strong>Cost</strong></td>"
            html += "<td colspan='2'></td>"
            html += "<td><strong>Qty</strong></td>"
            html += "<td></td>"
            html += "</tr>"

            sub_qty = Decimal("0")
            sub_rev = Decimal("0")
            sub_mrg = Decimal("0")
            sub_cost = Decimal("0")

            for pos in deal_positions:
                qty = Decimal(str(pos.get("quantity") or 0))
                rev = Decimal(str(pos.get("revenue_amount") or 0))
                mrg = Decimal(str(pos.get("margin_amount") or 0))
                cost = Decimal(str(pos.get("cost_amount") or 0))
                sub_qty += qty
                sub_rev += rev
                sub_mrg += mrg
                sub_cost += cost

                html += "<tr>"
                html += f"<td>{pos.get('position_number', '')}</td>"
                html += f"<td>{pos.get('product_name', '')}</td>"
                html += f"<td>{pos.get('supplier_name', '')}</td>"
                html += f"<td>{_fmt(rev)}</td>"
                html += "<td colspan='2'></td>"
                html += f"<td>{_fmt(mrg)}</td>"
                html += "<td colspan='2'></td>"
                html += f"<td>{_fmt(cost)}</td>"
                html += "<td colspan='2'></td>"
                html += f"<td>{_fmt(qty)}</td>"
                html += "<td></td>"
                html += "</tr>"

            html += '<tr class="subtotal">'
            html += "<td colspan='3'>SUBTOTAL</td>"
            html += f"<td>{_fmt(sub_rev)}</td>"
            html += "<td colspan='2'></td>"
            html += f"<td>{_fmt(sub_mrg)}</td>"
            html += "<td colspan='2'></td>"
            html += f"<td>{_fmt(sub_cost)}</td>"
            html += "<td colspan='2'></td>"
            html += f"<td>{_fmt(sub_qty)}</td>"
            html += "<td></td>"
            html += "</tr>"

    if current_period is not None:
        html += "</table>"

    html += "</body></html>"
    return html


def generate_detail_files(
    conn,
    details_dir: Path,
    dashboard_filename: str,
    threshold: Decimal = _DEFAULT_THRESHOLD,
) -> dict[str, str]:
    """Generate detail HTML files for each period with discrepancies.

    Args:
        conn: DB connection for live queries.
        details_dir: Directory to write detail files into.
        dashboard_filename: Name of main dashboard file (for back-link).

    Returns:
        Mapping {normalized_period: relative_filename} for linking.
    """
    from db_snapshot_service import collect_discrepant_deals, collect_positions_for_deals

    logger.info("Collecting discrepant deals for drill-down...")
    deals = collect_discrepant_deals(conn, threshold=threshold)
    if not deals:
        logger.info("No discrepancies found -- no detail files generated.")
        return {}

    deal_ids = [d["deal_id"] for d in deals]
    logger.info("Found %d discrepant deals, collecting positions...", len(deals))
    positions = collect_positions_for_deals(conn, deal_ids)

    positions_by_deal: dict[str, list[dict]] = defaultdict(list)
    for p in positions:
        positions_by_deal[str(p["deal_id"])].append(p)

    deals_by_period: dict[str, list[dict]] = defaultdict(list)
    for d in deals:
        deals_by_period[d["period_full_name"]].append(d)

    details_dir.mkdir(parents=True, exist_ok=True)
    details_subdir = details_dir.name
    period_links: dict[str, str] = {}

    for period, period_deals in sort_period_items(deals_by_period.items()):
        safe_name = _safe_filename(period)
        filename = f"detail_{safe_name}.html"
        html = _generate_detail_html(
            period, period_deals, positions_by_deal,
            f"../{dashboard_filename}",
            threshold=threshold,
        )
        (details_dir / filename).write_text(html, encoding="utf-8")
        norm_key = _normalize_period_key(period)
        period_links[norm_key] = f"{details_subdir}/{filename}"
        logger.info("  Detail file: %s (%d deals)", filename, len(period_deals))

    all_html = _generate_detail_html(
        "ALL", deals, positions_by_deal,
        f"../{dashboard_filename}",
        threshold=threshold,
    )
    (details_dir / "detail_ALL.html").write_text(all_html, encoding="utf-8")
    period_links["__ALL__"] = f"{details_subdir}/detail_ALL.html"
    logger.info("  Detail file: detail_ALL.html (%d deals total)", len(deals))

    return period_links


# ---------------------------------------------------------------------------
# Compare mode helpers
# ---------------------------------------------------------------------------

def _render_compare_overview(snap_a: dict, snap_b: dict) -> str:
    """Compare two snapshots side by side in cards."""
    metrics = [
        ("Deals rows", "deals_total_rows"),
        ("Positions rows", "pos_total_rows"),
        ("Unique deal_key (D)", "deals_unique_deal_key"),
        ("Unique deal_key (P)", "pos_unique_deal_key"),
        ("Unique clients (D)", "deals_unique_client"),
        ("Unique clients (P)", "pos_unique_client"),
        ("Products", "pos_unique_product"),
        ("Suppliers", "pos_unique_supplier"),
    ]
    html = "<table><tr><th>Metric</th><th>Snapshot A</th><th>Snapshot B</th><th>Delta</th></tr>"
    for label, key in metrics:
        a = snap_a.get(key, 0) or 0
        b = snap_b.get(key, 0) or 0
        delta = int(b) - int(a)
        cls = _delta_cls(delta)
        html += f"<tr><td>{label}</td><td>{_fmt(a)}</td><td>{_fmt(b)}</td>"
        html += f'<td class="delta-cell {cls}">{_fmt(delta)}</td></tr>'
    html += "</table>"
    return html


def _render_compare_financials(
    snap_a: dict,
    snap_b: dict,
    threshold: Decimal = _DEFAULT_THRESHOLD,
) -> str:
    """Compare financial totals between two snapshots."""
    rows_data = [
        ("D: Revenue", "deals_sum_revenue"),
        ("D: Margin", "deals_sum_margin"),
        ("D: Cost", "deals_sum_cost"),
        ("D: Kickback", "deals_sum_kickback"),
        ("D: Calc Revenue", "deals_sum_calc_revenue"),
        ("D: Calc Margin", "deals_sum_calc_margin"),
        ("D: Calc Cost", "deals_sum_calc_cost"),
        ("D: Quantity", "deals_sum_quantity"),
        ("D: has_error", "deals_has_error_count"),
        ("P: Revenue", "pos_sum_revenue"),
        ("P: Margin", "pos_sum_margin"),
        ("P: Cost", "pos_sum_cost"),
        ("P: Quantity", "pos_sum_quantity"),
    ]
    html = "<table><tr><th>Metric</th><th>Snapshot A</th><th>Snapshot B</th><th>Delta</th></tr>"
    for label, key in rows_data:
        a = Decimal(str(snap_a.get(key, 0) or 0))
        b = Decimal(str(snap_b.get(key, 0) or 0))
        delta = b - a
        cls = _delta_cls(delta, threshold)
        html += f"<tr><td>{label}</td><td>{_fmt(a)}</td><td>{_fmt(b)}</td>"
        html += f'<td class="delta-cell {cls}">{_fmt(delta)}</td></tr>'
    html += "</table>"
    return html


# ---------------------------------------------------------------------------
# Full page assembly
# ---------------------------------------------------------------------------

def generate_latest_html(
    snap: dict,
    period_links: dict[str, str] | None = None,
    threshold: Decimal = _DEFAULT_THRESHOLD,
) -> str:
    """Generate full HTML page for a single snapshot."""
    label = snap.get("label", "?")
    created = snap.get("created_at", "?")
    links = period_links or {}

    html = f"""<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">
<title>DB Dashboard -- {label}</title>{CSS}</head><body>
<h1>DB Dashboard</h1>
<div class="meta">Snapshot #{snap.get('id')} | Label: {label} |
    Source: {snap.get('source', '?')} | Created: {created}</div>

<h2>1. Overview</h2>
{_render_overview_cards(snap)}

<h2>2. Financial Totals (deals vs positions)</h2>
{_render_financial_table(snap, period_links=links, threshold=threshold)}

<h2>3. Data Health</h2>
{_render_health(snap)}

<h2>4A. Deals by Period</h2>
{_render_deal_periods_table(snap.get('deal_periods', []), period_links=links, threshold=threshold)}

<h2>4B. Positions by Period</h2>
{_render_position_periods_table(snap.get('position_periods', []), threshold=threshold)}

<h2>4C. Cross-compare: Deals vs Positions by Period</h2>
{_render_cross_period_table(
    snap.get('deal_periods', []),
    snap.get('position_periods', []),
    period_links=links,
    threshold=threshold,
)}

</body></html>"""
    return html


def generate_compare_html(
    snap_a: dict,
    snap_b: dict,
    file_a: str | None = None,
    file_b: str | None = None,
    threshold: Decimal = _DEFAULT_THRESHOLD,
) -> str:
    """Generate full HTML page comparing two snapshots."""
    la = snap_a.get("label", "?")
    lb = snap_b.get("label", "?")

    label_a = f'<a href="{file_a}" target="_blank">A: {la}</a>' if file_a else f"A: {la}"
    label_b = f'<a href="{file_b}" target="_blank">B: {lb}</a>' if file_b else f"B: {lb}"

    html = f"""<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">
<title>DB Dashboard Compare -- {la} vs {lb}</title>{CSS}</head><body>
<h1>DB Dashboard -- Compare</h1>
<div class="compare-header">
    <div class="snap-badge">
        <div class="snap-label">{label_a}</div>
        <div class="snap-meta">#{snap_a.get('id')} | {snap_a.get('created_at')}</div>
    </div>
    <div class="snap-badge">
        <div class="snap-label">{label_b}</div>
        <div class="snap-meta">#{snap_b.get('id')} | {snap_b.get('created_at')}</div>
    </div>
</div>

<h2>1. Overview Comparison</h2>
{_render_compare_overview(snap_a, snap_b)}

<h2>2. Financial Totals Comparison</h2>
{_render_compare_financials(snap_a, snap_b, threshold=threshold)}

<h2>3A. Data Health -- Snapshot A ({la})</h2>
{_render_health(snap_a)}

<h2>3B. Data Health -- Snapshot B ({lb})</h2>
{_render_health(snap_b)}

<h2>4A. Deals by Period -- Snapshot A ({la})</h2>
{_render_deal_periods_table(snap_a.get('deal_periods', []), threshold=threshold)}

<h2>4A. Deals by Period -- Snapshot B ({lb})</h2>
{_render_deal_periods_table(snap_b.get('deal_periods', []), threshold=threshold)}

<h2>4B. Positions by Period -- Snapshot A ({la})</h2>
{_render_position_periods_table(snap_a.get('position_periods', []), threshold=threshold)}

<h2>4B. Positions by Period -- Snapshot B ({lb})</h2>
{_render_position_periods_table(snap_b.get('position_periods', []), threshold=threshold)}

<h2>4C. Cross-compare: Deals vs Positions -- Snapshot A ({la})</h2>
{_render_cross_period_table(snap_a.get('deal_periods', []), snap_a.get('position_periods', []), threshold=threshold)}

<h2>4C. Cross-compare: Deals vs Positions -- Snapshot B ({lb})</h2>
{_render_cross_period_table(snap_b.get('deal_periods', []), snap_b.get('position_periods', []), threshold=threshold)}

</body></html>"""
    return html


def generate_list_html(snapshots: list[dict]) -> str:
    """Generate a simple listing of all snapshots."""
    html = f"""<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">
<title>DB Snapshots List</title>{CSS}</head><body>
<h1>DB Snapshots</h1>
<table><tr><th>ID</th><th>Label</th><th>Source</th>
<th>Deals Rows</th><th>Pos Rows</th><th>Created At</th></tr>"""
    for s in snapshots:
        html += f"""<tr><td>{s['id']}</td><td>{s.get('label', '-')}</td>
<td>{s.get('source', '-')}</td><td>{_fmt(s.get('deals_total_rows', 0))}</td>
<td>{_fmt(s.get('pos_total_rows', 0))}</td><td>{s.get('created_at', '-')}</td></tr>"""
    html += "</table></body></html>"
    return html


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Generate HTML dashboard from DB snapshots")
    parser.add_argument("--mode", choices=["latest", "compare", "list"], default="latest")
    parser.add_argument("--id1", type=int, default=None, help="Snapshot A id (compare mode)")
    parser.add_argument("--id2", type=int, default=None, help="Snapshot B id (compare mode)")
    parser.add_argument("--label1", type=str, default=None, help="Snapshot A label")
    parser.add_argument("--label2", type=str, default=None, help="Snapshot B label")
    parser.add_argument(
        "--output", type=str, default=None,
        help="Output HTML path. Auto-generated if omitted.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        metavar="RUBLES",
        help=(
            "Minimum absolute delta to treat as a discrepancy in dashboard output. "
            f"Default: {_DEFAULT_THRESHOLD} (from AuditConfig)."
        ),
    )
    args = parser.parse_args()
    threshold = (
        Decimal(str(args.threshold))
        if args.threshold is not None
        else _DEFAULT_THRESHOLD
    )

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    engine = get_sync_engine()
    period_links: dict[str, str] = {}
    details_dir: Path | None = None
    out_name = ""

    try:
        with engine.connect() as conn:
            if args.mode == "list":
                snaps = list_snapshots(conn)
                html = generate_list_html(snaps)
                out_name = "snapshots_list.html"
                print(f"Found {len(snaps)} snapshots.")

            elif args.mode == "compare":
                has_explicit = any([args.id1, args.id2, args.label1, args.label2])
                if has_explicit:
                    snap_a = load_snapshot(conn, snapshot_id=args.id1, label=args.label1)
                    snap_b = load_snapshot(conn, snapshot_id=args.id2, label=args.label2)
                else:
                    rows = conn.execute(
                        text(
                            "SELECT id FROM db_snapshots "
                            "ORDER BY created_at DESC LIMIT 2"
                        )
                    ).fetchall()
                    if len(rows) < 2:
                        logger.error(
                            "Need at least 2 snapshots for compare without args, "
                            "found %d.", len(rows),
                        )
                        return 1
                    snap_b = load_snapshot(conn, snapshot_id=rows[0][0])
                    snap_a = load_snapshot(conn, snapshot_id=rows[1][0])
                    logger.info(
                        "Auto-compare: A=#%s (%s) vs B=#%s (%s)",
                        snap_a.get("id"), snap_a.get("label"),
                        snap_b.get("id"), snap_b.get("label"),
                    )
                if not snap_a or not snap_b:
                    logger.error("Could not load one or both snapshots for comparison.")
                    return 1

                # Generate individual dashboards for each snapshot
                id_a = snap_a.get("id")
                id_b = snap_b.get("id")
                file_a = f"dashboard_snap_{id_a}.html"
                file_b = f"dashboard_snap_{id_b}.html"

                for snap, fname in [(snap_a, file_a), (snap_b, file_b)]:
                    sid = snap.get("id")
                    det_dir = REPORTS_DIR / f"dashboard_snap_{sid}_details"
                    links = generate_detail_files(conn, det_dir, fname, threshold=threshold)
                    snap_html = generate_latest_html(snap, period_links=links, threshold=threshold)
                    (REPORTS_DIR / fname).write_text(snap_html, encoding="utf-8")
                    logger.info("Individual dashboard: %s", fname)

                la = snap_a.get("label", id_a)
                lb = snap_b.get("label", id_b)
                html = generate_compare_html(
                    snap_a, snap_b, file_a=file_a, file_b=file_b, threshold=threshold,
                )
                out_name = f"dashboard_compare_{la}_vs_{lb}.html"

            else:
                snap = load_snapshot(conn)
                if not snap:
                    logger.error("No snapshots found in database.")
                    return 1
                ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                out_name = f"dashboard_{ts}.html"
                details_dir = REPORTS_DIR / f"dashboard_{ts}_details"
                period_links = generate_detail_files(
                    conn, details_dir, out_name, threshold=threshold,
                )
                html = generate_latest_html(snap, period_links=period_links, threshold=threshold)

    except Exception:
        logger.exception("Failed to generate dashboard")
        return 1
    finally:
        engine.dispose()

    out_path = Path(args.output) if args.output else REPORTS_DIR / out_name
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")

    print(f"\nDashboard generated: {out_path}")
    if period_links:
        print(f"Detail files: {details_dir}/")

    file_uri = out_path.resolve().as_uri()
    print(f"Open in browser: {file_uri}")
    webbrowser.open(file_uri)
    return 0


if __name__ == "__main__":
    sys.exit(main())
