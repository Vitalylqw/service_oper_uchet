"""
Database snapshot service -- collects aggregated metrics from read_deals and read_positions.

Core module used by create_db_snapshot.py and generate_dashboard.py.
Uses sync SQLAlchemy (psycopg2) for simplicity in standalone scripts.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from period_utils import period_sort_key
from sqlalchemy import text
from sqlalchemy.engine import Connection

from excel_audit.config import AuditConfig

logger = logging.getLogger(__name__)
_DEFAULT_THRESHOLD = AuditConfig().threshold


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class DealPeriodRow:
    """Aggregated metrics for read_deals grouped by period_full_name."""

    period_full_name: str = ""
    rows_count: int = 0
    unique_deal_key: int = 0
    unique_hash_key: int = 0
    delta_dk_hk: int = 0
    unique_client: int = 0
    sum_revenue: Decimal = Decimal("0")
    sum_margin: Decimal = Decimal("0")
    sum_cost: Decimal = Decimal("0")
    sum_kickback: Decimal = Decimal("0")
    sum_calc_revenue: Decimal = Decimal("0")
    sum_calc_margin: Decimal = Decimal("0")
    sum_calc_cost: Decimal = Decimal("0")
    sum_items_count: int = 0
    sum_quantity: Decimal = Decimal("0")
    has_error_count: int = 0


@dataclass
class PositionPeriodRow:
    """Aggregated metrics for read_positions grouped by period_month+period_year."""

    period_key: str = ""
    rows_count: int = 0
    unique_hash_key: int = 0
    delta_rows_hk: int = 0
    unique_deal_key: int = 0
    unique_client: int = 0
    unique_product: int = 0
    unique_supplier: int = 0
    sum_quantity: Decimal = Decimal("0")
    sum_revenue: Decimal = Decimal("0")
    sum_margin: Decimal = Decimal("0")
    sum_cost: Decimal = Decimal("0")


@dataclass
class SnapshotData:
    """Complete snapshot payload ready for DB insertion."""

    label: str = ""
    source: str = "manual"

    # read_deals totals
    deals_total_rows: int = 0
    deals_unique_deal_key: int = 0
    deals_unique_hash_key: int = 0
    deals_unique_client: int = 0
    deals_unique_period: int = 0
    deals_sum_revenue: Decimal = Decimal("0")
    deals_sum_margin: Decimal = Decimal("0")
    deals_sum_cost: Decimal = Decimal("0")
    deals_sum_kickback: Decimal = Decimal("0")
    deals_sum_calc_revenue: Decimal = Decimal("0")
    deals_sum_calc_margin: Decimal = Decimal("0")
    deals_sum_calc_cost: Decimal = Decimal("0")
    deals_sum_items_count: int = 0
    deals_sum_quantity: Decimal = Decimal("0")
    deals_has_error_count: int = 0

    # read_positions totals
    pos_total_rows: int = 0
    pos_unique_deal_key: int = 0
    pos_unique_hash_key: int = 0
    pos_unique_client: int = 0
    pos_unique_product: int = 0
    pos_unique_supplier: int = 0
    pos_unique_period: int = 0
    pos_sum_quantity: Decimal = Decimal("0")
    pos_sum_revenue: Decimal = Decimal("0")
    pos_sum_margin: Decimal = Decimal("0")
    pos_sum_cost: Decimal = Decimal("0")

    health_checks: dict[str, Any] = field(default_factory=dict)
    deal_periods: list[DealPeriodRow] = field(default_factory=list)
    position_periods: list[PositionPeriodRow] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Collectors
# ---------------------------------------------------------------------------

def _dec(val: Any) -> Decimal:
    """Safe Decimal conversion for nullable DB values."""
    if val is None:
        return Decimal("0")
    return Decimal(str(val))


def collect_deals_totals(conn: Connection) -> dict[str, Any]:
    """Collect aggregate totals from read_deals."""
    sql = text("""
        SELECT
            COUNT(*)                                     AS total_rows,
            COUNT(DISTINCT deal_key)                     AS unique_deal_key,
            COUNT(DISTINCT hash_key)                     AS unique_hash_key,
            COUNT(DISTINCT client_name)                  AS unique_client,
            COUNT(DISTINCT period_full_name)              AS unique_period,
            COALESCE(SUM(total_revenue_amount), 0)       AS sum_revenue,
            COALESCE(SUM(total_margin_amount), 0)        AS sum_margin,
            COALESCE(SUM(total_cost_amount), 0)          AS sum_cost,
            COALESCE(SUM(kickback_amount_value), 0)      AS sum_kickback,
            COALESCE(SUM(calc_revenue_amount), 0)        AS sum_calc_revenue,
            COALESCE(SUM(calc_margin_amount), 0)         AS sum_calc_margin,
            COALESCE(SUM(calc_cost_amount), 0)           AS sum_calc_cost,
            COALESCE(SUM(items_count), 0)                AS sum_items_count,
            COALESCE(SUM(total_quantity), 0)             AS sum_quantity,
            COALESCE(SUM(CASE WHEN has_totals_error THEN 1 ELSE 0 END), 0)
                                                         AS has_error_count
        FROM read_deals
    """)
    row = conn.execute(sql).mappings().first()
    if not row:
        return {}
    return dict(row)


def collect_positions_totals(conn: Connection) -> dict[str, Any]:
    """Collect aggregate totals from read_positions."""
    sql = text("""
        SELECT
            COUNT(*)                                AS total_rows,
            COUNT(DISTINCT deal_key)                AS unique_deal_key,
            COUNT(DISTINCT hash_key)                AS unique_hash_key,
            COUNT(DISTINCT client_name)             AS unique_client,
            COUNT(DISTINCT product_name)            AS unique_product,
            COUNT(DISTINCT supplier_name)           AS unique_supplier,
            COUNT(DISTINCT (period_month || '.' || period_year))
                                                    AS unique_period,
            COALESCE(SUM(quantity), 0)              AS sum_quantity,
            COALESCE(SUM(revenue_amount), 0)        AS sum_revenue,
            COALESCE(SUM(margin_amount), 0)         AS sum_margin,
            COALESCE(SUM(cost_amount), 0)           AS sum_cost
        FROM read_positions
    """)
    row = conn.execute(sql).mappings().first()
    if not row:
        return {}
    return dict(row)


def collect_deals_by_period(conn: Connection) -> list[DealPeriodRow]:
    """Collect read_deals metrics grouped by period_full_name."""
    sql = text("""
        SELECT
            period_full_name,
            COUNT(*)                                     AS rows_count,
            COUNT(DISTINCT deal_key)                     AS unique_deal_key,
            COUNT(DISTINCT hash_key)                     AS unique_hash_key,
            COUNT(DISTINCT deal_key) - COUNT(DISTINCT hash_key) AS delta_dk_hk,
            COUNT(DISTINCT client_name)                  AS unique_client,
            COALESCE(SUM(total_revenue_amount), 0)       AS sum_revenue,
            COALESCE(SUM(total_margin_amount), 0)        AS sum_margin,
            COALESCE(SUM(total_cost_amount), 0)          AS sum_cost,
            COALESCE(SUM(kickback_amount_value), 0)      AS sum_kickback,
            COALESCE(SUM(calc_revenue_amount), 0)        AS sum_calc_revenue,
            COALESCE(SUM(calc_margin_amount), 0)         AS sum_calc_margin,
            COALESCE(SUM(calc_cost_amount), 0)           AS sum_calc_cost,
            COALESCE(SUM(items_count), 0)                AS sum_items_count,
            COALESCE(SUM(total_quantity), 0)             AS sum_quantity,
            COALESCE(SUM(CASE WHEN has_totals_error THEN 1 ELSE 0 END), 0)
                                                         AS has_error_count
        FROM read_deals
        GROUP BY period_full_name
        ORDER BY period_full_name
    """)
    rows = conn.execute(sql).mappings().all()
    result = []
    for r in rows:
        result.append(DealPeriodRow(
            period_full_name=r["period_full_name"],
            rows_count=r["rows_count"],
            unique_deal_key=r["unique_deal_key"],
            unique_hash_key=r["unique_hash_key"],
            delta_dk_hk=r["delta_dk_hk"],
            unique_client=r["unique_client"],
            sum_revenue=_dec(r["sum_revenue"]),
            sum_margin=_dec(r["sum_margin"]),
            sum_cost=_dec(r["sum_cost"]),
            sum_kickback=_dec(r["sum_kickback"]),
            sum_calc_revenue=_dec(r["sum_calc_revenue"]),
            sum_calc_margin=_dec(r["sum_calc_margin"]),
            sum_calc_cost=_dec(r["sum_calc_cost"]),
            sum_items_count=r["sum_items_count"],
            sum_quantity=_dec(r["sum_quantity"]),
            has_error_count=r["has_error_count"],
        ))
    result.sort(key=lambda r: period_sort_key(r.period_full_name), reverse=True)
    return result


def collect_positions_by_period(conn: Connection) -> list[PositionPeriodRow]:
    """Collect read_positions metrics grouped by period_month.period_year."""
    sql = text("""
        SELECT
            period_month || '.' || period_year       AS period_key,
            COUNT(*)                                 AS rows_count,
            COUNT(DISTINCT hash_key)                 AS unique_hash_key,
            COUNT(*) - COUNT(DISTINCT hash_key)      AS delta_rows_hk,
            COUNT(DISTINCT deal_key)                 AS unique_deal_key,
            COUNT(DISTINCT client_name)              AS unique_client,
            COUNT(DISTINCT product_name)             AS unique_product,
            COUNT(DISTINCT supplier_name)            AS unique_supplier,
            COALESCE(SUM(quantity), 0)               AS sum_quantity,
            COALESCE(SUM(revenue_amount), 0)         AS sum_revenue,
            COALESCE(SUM(margin_amount), 0)          AS sum_margin,
            COALESCE(SUM(cost_amount), 0)            AS sum_cost
        FROM read_positions
        GROUP BY period_month, period_year
        ORDER BY period_year, period_month
    """)
    rows = conn.execute(sql).mappings().all()
    result = []
    for r in rows:
        result.append(PositionPeriodRow(
            period_key=r["period_key"],
            rows_count=r["rows_count"],
            unique_hash_key=r["unique_hash_key"],
            delta_rows_hk=r["delta_rows_hk"],
            unique_deal_key=r["unique_deal_key"],
            unique_client=r["unique_client"],
            unique_product=r["unique_product"],
            unique_supplier=r["unique_supplier"],
            sum_quantity=_dec(r["sum_quantity"]),
            sum_revenue=_dec(r["sum_revenue"]),
            sum_margin=_dec(r["sum_margin"]),
            sum_cost=_dec(r["sum_cost"]),
        ))
    result.sort(key=lambda r: period_sort_key(r.period_key), reverse=True)
    return result


def collect_health_checks(conn: Connection) -> dict[str, Any]:
    """Run all data integrity checks and return results dict."""
    checks: dict[str, Any] = {}

    # 1. Uniqueness checks (deals)
    row = conn.execute(text("""
        SELECT
            COUNT(*) AS total,
            COUNT(DISTINCT deal_key) AS uniq_dk,
            COUNT(DISTINCT hash_key) AS uniq_hk
        FROM read_deals
    """)).mappings().first()
    if row:
        checks["deals_rows_vs_deal_key"] = {
            "total": row["total"], "unique": row["uniq_dk"],
            "delta": row["total"] - row["uniq_dk"],
            "status": "OK" if row["total"] == row["uniq_dk"] else "FAIL",
        }
        checks["deals_rows_vs_hash_key"] = {
            "total": row["total"], "unique": row["uniq_hk"],
            "delta": row["total"] - row["uniq_hk"],
            "status": "OK" if row["total"] == row["uniq_hk"] else "FAIL",
        }

    # 2. Uniqueness checks (positions)
    row = conn.execute(text("""
        SELECT
            COUNT(*) AS total,
            COUNT(DISTINCT hash_key) AS uniq_hk
        FROM read_positions
    """)).mappings().first()
    if row:
        checks["pos_rows_vs_hash_key"] = {
            "total": row["total"], "unique": row["uniq_hk"],
            "delta": row["total"] - row["uniq_hk"],
            "status": "OK" if row["total"] == row["uniq_hk"] else "FAIL",
        }

    # 3. Cross-table: deal_key consistency
    row = conn.execute(text("""
        SELECT
            (SELECT COUNT(DISTINCT deal_key) FROM read_deals)     AS deals_dk,
            (SELECT COUNT(DISTINCT deal_key) FROM read_positions) AS pos_dk
    """)).mappings().first()
    if row:
        checks["cross_deal_key"] = {
            "deals": row["deals_dk"], "positions": row["pos_dk"],
            "delta": row["deals_dk"] - row["pos_dk"],
            "status": "OK" if row["deals_dk"] == row["pos_dk"] else "WARN",
        }

    # 4. Cross-table: client_name consistency
    row = conn.execute(text("""
        SELECT
            (SELECT COUNT(DISTINCT client_name) FROM read_deals)     AS deals_cl,
            (SELECT COUNT(DISTINCT client_name) FROM read_positions) AS pos_cl
    """)).mappings().first()
    if row:
        checks["cross_client_name"] = {
            "deals": row["deals_cl"], "positions": row["pos_cl"],
            "delta": row["deals_cl"] - row["pos_cl"],
            "status": "OK" if row["deals_cl"] == row["pos_cl"] else "WARN",
        }

    # 5. Cross-table: financial sums
    row = conn.execute(text("""
        SELECT
            COALESCE((SELECT SUM(total_revenue_amount) FROM read_deals), 0)  AS d_rev,
            COALESCE((SELECT SUM(revenue_amount) FROM read_positions), 0)    AS p_rev,
            COALESCE((SELECT SUM(total_margin_amount) FROM read_deals), 0)   AS d_mrg,
            COALESCE((SELECT SUM(margin_amount) FROM read_positions), 0)     AS p_mrg,
            COALESCE((SELECT SUM(total_cost_amount) FROM read_deals), 0)     AS d_cost,
            COALESCE((SELECT SUM(cost_amount) FROM read_positions), 0)       AS p_cost,
            COALESCE((SELECT SUM(total_quantity) FROM read_deals), 0)        AS d_qty,
            COALESCE((SELECT SUM(quantity) FROM read_positions), 0)          AS p_qty
    """)).mappings().first()
    if row:
        for label, d_key, p_key in [
            ("revenue", "d_rev", "p_rev"),
            ("margin", "d_mrg", "p_mrg"),
            ("cost", "d_cost", "p_cost"),
            ("quantity", "d_qty", "p_qty"),
        ]:
            d_val = _dec(row[d_key])
            p_val = _dec(row[p_key])
            delta = d_val - p_val
            checks[f"cross_sum_{label}"] = {
                "deals": str(d_val), "positions": str(p_val),
                "delta": str(delta),
                "status": "OK" if delta == 0 else "WARN",
            }

    # 6. has_totals_error count
    row = conn.execute(text("""
        SELECT COUNT(*) AS cnt FROM read_deals WHERE has_totals_error = true
    """)).mappings().first()
    if row:
        checks["has_totals_error_count"] = {
            "count": row["cnt"],
            "status": "OK" if row["cnt"] == 0 else "WARN",
        }

    # 7. items_count vs actual positions count
    row = conn.execute(text("""
        SELECT COUNT(*) AS cnt
        FROM (
            SELECT d.id, d.items_count, COUNT(p.id) AS actual_count
            FROM read_deals d
            LEFT JOIN read_positions p ON p.deal_id = d.id
            GROUP BY d.id, d.items_count
            HAVING d.items_count != COUNT(p.id)
        ) sub
    """)).mappings().first()
    if row:
        checks["items_count_mismatch"] = {
            "count": row["cnt"],
            "status": "OK" if row["cnt"] == 0 else "FAIL",
        }

    # 8. Deals without positions
    row = conn.execute(text("""
        SELECT COUNT(*) AS cnt
        FROM read_deals d
        LEFT JOIN read_positions p ON p.deal_id = d.id
        WHERE p.id IS NULL
    """)).mappings().first()
    if row:
        checks["deals_without_positions"] = {
            "count": row["cnt"],
            "status": "OK" if row["cnt"] == 0 else "WARN",
        }

    # 9. Orphan positions (deal_id not in read_deals)
    row = conn.execute(text("""
        SELECT COUNT(*) AS cnt
        FROM read_positions p
        LEFT JOIN read_deals d ON d.id = p.deal_id
        WHERE d.id IS NULL
    """)).mappings().first()
    if row:
        checks["orphan_positions"] = {
            "count": row["cnt"],
            "status": "OK" if row["cnt"] == 0 else "FAIL",
        }

    # 10. calc vs total discrepancy count
    row = conn.execute(text("""
        SELECT COUNT(*) AS cnt
        FROM read_deals
        WHERE calc_revenue_amount != COALESCE(total_revenue_amount, 0)
           OR calc_margin_amount  != COALESCE(total_margin_amount, 0)
           OR calc_cost_amount    != COALESCE(total_cost_amount, 0)
    """)).mappings().first()
    if row:
        checks["calc_vs_total_mismatch"] = {
            "count": row["cnt"],
            "status": "OK" if row["cnt"] == 0 else "INFO",
        }

    return checks


# ---------------------------------------------------------------------------
# Drill-down detail collectors (used by generate_dashboard for detail files)
# ---------------------------------------------------------------------------

def collect_discrepant_deals(
    conn: Connection,
    threshold: Decimal = _DEFAULT_THRESHOLD,
) -> list[dict]:
    """Collect deals where totals differ from aggregated position sums.

    Returns list of dicts with deal-level fields and aggregated position sums,
    sorted by period_full_name, deal_key.
    """
    sql = text("""
        SELECT
            d.id                            AS deal_id,
            d.deal_key,
            d.client_name,
            d.period_full_name,
            d.total_revenue_amount          AS d_revenue,
            d.total_margin_amount           AS d_margin,
            d.total_cost_amount             AS d_cost,
            d.total_quantity                AS d_quantity,
            d.has_totals_error,
            d.items_count,
            COALESCE(SUM(p.revenue_amount), 0) AS p_revenue,
            COALESCE(SUM(p.margin_amount), 0)  AS p_margin,
            COALESCE(SUM(p.cost_amount), 0)    AS p_cost,
            COALESCE(SUM(p.quantity), 0)       AS p_quantity,
            COUNT(p.id)                        AS p_count
        FROM read_deals d
        LEFT JOIN read_positions p ON p.deal_id = d.id
        GROUP BY d.id, d.deal_key, d.client_name, d.period_full_name,
                 d.total_revenue_amount, d.total_margin_amount,
                 d.total_cost_amount, d.total_quantity,
                 d.has_totals_error, d.items_count
        HAVING
            ABS(COALESCE(d.total_revenue_amount, 0)
                - COALESCE(SUM(p.revenue_amount), 0)) > :threshold
            OR ABS(COALESCE(d.total_margin_amount, 0)
                - COALESCE(SUM(p.margin_amount), 0)) > :threshold
            OR ABS(COALESCE(d.total_cost_amount, 0)
                - COALESCE(SUM(p.cost_amount), 0)) > :threshold
            OR ABS(COALESCE(d.total_quantity, 0)
                - COALESCE(SUM(p.quantity), 0)) > :threshold
        ORDER BY d.period_full_name, d.deal_key
    """)
    rows = conn.execute(sql, {"threshold": threshold}).mappings().all()
    return [dict(r) for r in rows]


def collect_positions_for_deals(
    conn: Connection, deal_ids: list,
) -> list[dict]:
    """Collect positions for given deal IDs.

    Returns list of dicts with position-level fields,
    sorted by deal_key, position_number.
    """
    if not deal_ids:
        return []
    sql = text("""
        SELECT
            p.deal_id,
            p.deal_key,
            p.position_number,
            p.product_name,
            p.supplier_name,
            p.quantity,
            p.revenue_amount,
            p.margin_amount,
            p.cost_amount
        FROM read_positions p
        WHERE p.deal_id = ANY(:deal_ids)
        ORDER BY p.deal_key, p.position_number
    """)
    rows = conn.execute(sql, {"deal_ids": deal_ids}).mappings().all()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Snapshot creation
# ---------------------------------------------------------------------------

def collect_snapshot(conn: Connection, label: str, source: str = "manual") -> SnapshotData:
    """Collect all metrics into a SnapshotData object."""
    logger.info("Collecting snapshot data (label=%s, source=%s)...", label, source)

    snap = SnapshotData(label=label, source=source)

    # Deals totals
    dt = collect_deals_totals(conn)
    if dt:
        snap.deals_total_rows = dt["total_rows"]
        snap.deals_unique_deal_key = dt["unique_deal_key"]
        snap.deals_unique_hash_key = dt["unique_hash_key"]
        snap.deals_unique_client = dt["unique_client"]
        snap.deals_unique_period = dt["unique_period"]
        snap.deals_sum_revenue = _dec(dt["sum_revenue"])
        snap.deals_sum_margin = _dec(dt["sum_margin"])
        snap.deals_sum_cost = _dec(dt["sum_cost"])
        snap.deals_sum_kickback = _dec(dt["sum_kickback"])
        snap.deals_sum_calc_revenue = _dec(dt["sum_calc_revenue"])
        snap.deals_sum_calc_margin = _dec(dt["sum_calc_margin"])
        snap.deals_sum_calc_cost = _dec(dt["sum_calc_cost"])
        snap.deals_sum_items_count = dt["sum_items_count"]
        snap.deals_sum_quantity = _dec(dt["sum_quantity"])
        snap.deals_has_error_count = dt["has_error_count"]

    # Positions totals
    pt = collect_positions_totals(conn)
    if pt:
        snap.pos_total_rows = pt["total_rows"]
        snap.pos_unique_deal_key = pt["unique_deal_key"]
        snap.pos_unique_hash_key = pt["unique_hash_key"]
        snap.pos_unique_client = pt["unique_client"]
        snap.pos_unique_product = pt["unique_product"]
        snap.pos_unique_supplier = pt["unique_supplier"]
        snap.pos_unique_period = pt["unique_period"]
        snap.pos_sum_quantity = _dec(pt["sum_quantity"])
        snap.pos_sum_revenue = _dec(pt["sum_revenue"])
        snap.pos_sum_margin = _dec(pt["sum_margin"])
        snap.pos_sum_cost = _dec(pt["sum_cost"])

    # Period breakdowns
    snap.deal_periods = collect_deals_by_period(conn)
    snap.position_periods = collect_positions_by_period(conn)

    # Health checks
    snap.health_checks = collect_health_checks(conn)

    logger.info(
        "Snapshot collected: deals=%d rows, positions=%d rows, periods(d)=%d, periods(p)=%d",
        snap.deals_total_rows, snap.pos_total_rows,
        len(snap.deal_periods), len(snap.position_periods),
    )
    return snap


def save_snapshot(conn: Connection, snap: SnapshotData) -> int:
    """Save SnapshotData to db_snapshots + child tables. Returns snapshot id."""
    import json

    result = conn.execute(text("""
        INSERT INTO db_snapshots (
            label, source,
            deals_total_rows, deals_unique_deal_key, deals_unique_hash_key,
            deals_unique_client, deals_unique_period,
            deals_sum_revenue, deals_sum_margin, deals_sum_cost, deals_sum_kickback,
            deals_sum_calc_revenue, deals_sum_calc_margin, deals_sum_calc_cost,
            deals_sum_items_count, deals_sum_quantity, deals_has_error_count,
            pos_total_rows, pos_unique_deal_key, pos_unique_hash_key,
            pos_unique_client, pos_unique_product, pos_unique_supplier, pos_unique_period,
            pos_sum_quantity, pos_sum_revenue, pos_sum_margin, pos_sum_cost,
            health_checks
        ) VALUES (
            :label, :source,
            :deals_total_rows, :deals_unique_deal_key, :deals_unique_hash_key,
            :deals_unique_client, :deals_unique_period,
            :deals_sum_revenue, :deals_sum_margin, :deals_sum_cost, :deals_sum_kickback,
            :deals_sum_calc_revenue, :deals_sum_calc_margin, :deals_sum_calc_cost,
            :deals_sum_items_count, :deals_sum_quantity, :deals_has_error_count,
            :pos_total_rows, :pos_unique_deal_key, :pos_unique_hash_key,
            :pos_unique_client, :pos_unique_product, :pos_unique_supplier, :pos_unique_period,
            :pos_sum_quantity, :pos_sum_revenue, :pos_sum_margin, :pos_sum_cost,
            :health_checks
        ) RETURNING id
    """), {
        "label": snap.label,
        "source": snap.source,
        "deals_total_rows": snap.deals_total_rows,
        "deals_unique_deal_key": snap.deals_unique_deal_key,
        "deals_unique_hash_key": snap.deals_unique_hash_key,
        "deals_unique_client": snap.deals_unique_client,
        "deals_unique_period": snap.deals_unique_period,
        "deals_sum_revenue": str(snap.deals_sum_revenue),
        "deals_sum_margin": str(snap.deals_sum_margin),
        "deals_sum_cost": str(snap.deals_sum_cost),
        "deals_sum_kickback": str(snap.deals_sum_kickback),
        "deals_sum_calc_revenue": str(snap.deals_sum_calc_revenue),
        "deals_sum_calc_margin": str(snap.deals_sum_calc_margin),
        "deals_sum_calc_cost": str(snap.deals_sum_calc_cost),
        "deals_sum_items_count": snap.deals_sum_items_count,
        "deals_sum_quantity": str(snap.deals_sum_quantity),
        "deals_has_error_count": snap.deals_has_error_count,
        "pos_total_rows": snap.pos_total_rows,
        "pos_unique_deal_key": snap.pos_unique_deal_key,
        "pos_unique_hash_key": snap.pos_unique_hash_key,
        "pos_unique_client": snap.pos_unique_client,
        "pos_unique_product": snap.pos_unique_product,
        "pos_unique_supplier": snap.pos_unique_supplier,
        "pos_unique_period": snap.pos_unique_period,
        "pos_sum_quantity": str(snap.pos_sum_quantity),
        "pos_sum_revenue": str(snap.pos_sum_revenue),
        "pos_sum_margin": str(snap.pos_sum_margin),
        "pos_sum_cost": str(snap.pos_sum_cost),
        "health_checks": json.dumps(snap.health_checks),
    })
    snapshot_id = result.scalar_one()

    # Save deal periods
    for dp in snap.deal_periods:
        conn.execute(text("""
            INSERT INTO db_snapshot_deal_periods (
                snapshot_id, period_full_name,
                rows_count, unique_deal_key, unique_hash_key, delta_dk_hk, unique_client,
                sum_revenue, sum_margin, sum_cost, sum_kickback,
                sum_calc_revenue, sum_calc_margin, sum_calc_cost,
                sum_items_count, sum_quantity, has_error_count
            ) VALUES (
                :sid, :period,
                :rows_count, :unique_deal_key, :unique_hash_key, :delta_dk_hk, :unique_client,
                :sum_revenue, :sum_margin, :sum_cost, :sum_kickback,
                :sum_calc_revenue, :sum_calc_margin, :sum_calc_cost,
                :sum_items_count, :sum_quantity, :has_error_count
            )
        """), {
            "sid": snapshot_id,
            "period": dp.period_full_name,
            "rows_count": dp.rows_count,
            "unique_deal_key": dp.unique_deal_key,
            "unique_hash_key": dp.unique_hash_key,
            "delta_dk_hk": dp.delta_dk_hk,
            "unique_client": dp.unique_client,
            "sum_revenue": str(dp.sum_revenue),
            "sum_margin": str(dp.sum_margin),
            "sum_cost": str(dp.sum_cost),
            "sum_kickback": str(dp.sum_kickback),
            "sum_calc_revenue": str(dp.sum_calc_revenue),
            "sum_calc_margin": str(dp.sum_calc_margin),
            "sum_calc_cost": str(dp.sum_calc_cost),
            "sum_items_count": dp.sum_items_count,
            "sum_quantity": str(dp.sum_quantity),
            "has_error_count": dp.has_error_count,
        })

    # Save position periods
    for pp in snap.position_periods:
        conn.execute(text("""
            INSERT INTO db_snapshot_position_periods (
                snapshot_id, period_key,
                rows_count, unique_hash_key, delta_rows_hk, unique_deal_key,
                unique_client, unique_product, unique_supplier,
                sum_quantity, sum_revenue, sum_margin, sum_cost
            ) VALUES (
                :sid, :period,
                :rows_count, :unique_hash_key, :delta_rows_hk, :unique_deal_key,
                :unique_client, :unique_product, :unique_supplier,
                :sum_quantity, :sum_revenue, :sum_margin, :sum_cost
            )
        """), {
            "sid": snapshot_id,
            "period": pp.period_key,
            "rows_count": pp.rows_count,
            "unique_hash_key": pp.unique_hash_key,
            "delta_rows_hk": pp.delta_rows_hk,
            "unique_deal_key": pp.unique_deal_key,
            "unique_client": pp.unique_client,
            "unique_product": pp.unique_product,
            "unique_supplier": pp.unique_supplier,
            "sum_quantity": str(pp.sum_quantity),
            "sum_revenue": str(pp.sum_revenue),
            "sum_margin": str(pp.sum_margin),
            "sum_cost": str(pp.sum_cost),
        })

    conn.commit()
    logger.info("Snapshot saved: id=%d, label=%s", snapshot_id, snap.label)
    return snapshot_id
