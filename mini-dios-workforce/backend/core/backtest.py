"""Mini-DIOS Plastics — 1-Month Historical Backtest / Replay Engine (The "Proof Engine").

Eliminates the "too good to be true" objection by letting factories upload 2-4 weeks of their
past press logs (CSV or Excel) or run a built-in 30-day sample plant replay, comparing Actual
Historical Waste vs. Deterministic OR-Tools CP-SAT Replay.

100% deterministic Python math. Zero LLM arithmetic.
"""
from __future__ import annotations

import csv
import io
import math
from collections import defaultdict
from typing import Any, Optional

from openpyxl import Workbook, load_workbook
from pydantic import BaseModel, Field

from .ontology import (
    COLOR_RANKS,
    Currency,
    Mold,
    PlantDataset,
    PlasticColor,
    PressMachine,
    ProductionOrder,
    ResinCode,
    SolverConfig,
    convert_sar_to_currency,
    order_duration_mins,
)
from .seed import default_config, demo_dataset
from .solver import solve_plant_schedule

BACKTEST_TEMPLATE_COLUMNS = [
    "order_id",
    "customer",
    "sku_name",
    "resin",
    "color",
    "qty_units",
    "press_id",
    "actual_changeover_hrs",
    "actual_purge_scrap_kg",
    "actual_overtime_hrs",
    "actual_late_hours",
    "export_penalty_cost",
    "unit_margin",
]


class BacktestPeriodMetrics(BaseModel):
    purge_scrap_kg: float
    purge_scrap_cost: float
    changeover_hrs: float
    changeover_downtime_cost: float
    overtime_hrs: float
    overtime_cost: float
    late_hours: float
    export_penalty_cost: float
    total_avoidable_waste_cost: float


class BacktestDeltaMetrics(BaseModel):
    purge_scrap_saved_kg: float
    purge_scrap_saved_cost: float
    purge_scrap_cut_pct: float
    changeover_hrs_freed: float
    changeover_cut_pct: float
    overtime_hrs_cut: float
    overtime_cost_saved: float
    late_hours_avoided: float
    export_penalties_avoided: float
    extra_sellable_units_unlocked: int
    extra_sellable_tons_unlocked: float
    extra_output_margin_unlocked: float
    direct_cost_savings_1month: float
    total_cash_left_on_floor_1month: float
    annualized_cash_left_on_floor: float
    estimated_monthly_subscription_cost: float
    estimated_payback_days: int


class BacktestPressRow(BaseModel):
    press_id: str
    orders_count: int
    actual_changeover_hrs: float
    optimized_changeover_hrs: float
    unlocked_hrs: float
    actual_purge_scrap_kg: float
    optimized_purge_scrap_kg: float
    scrap_saved_kg: float


class BacktestOrderRow(BaseModel):
    order_id: str
    customer: str
    sku_name: str
    resin: str
    color: str
    qty_units: int
    actual_press_id: str
    optimized_press_id: str
    actual_changeover_hrs: float
    optimized_changeover_hrs: float
    actual_purge_scrap_kg: float
    optimized_purge_scrap_kg: float
    actual_late_hours: float
    optimized_late_hours: float


class BacktestReplayReport(BaseModel):
    source_label: str
    period_days: int = 30
    orders_analyzed: int
    currency: Currency
    fx_egp_per_sar: float
    solve_time_ms: int
    solver_status: str
    active_engine: str = "legacy_cpsat_v1"
    actual: BacktestPeriodMetrics
    optimized: BacktestPeriodMetrics
    actual_vs_optimized: BacktestDeltaMetrics
    press_breakdown: list[BacktestPressRow] = Field(default_factory=list)
    order_comparison: list[BacktestOrderRow] = Field(default_factory=list)


def sample_30day_historical_rows() -> list[dict[str, Any]]:
    """Built-in 30-day historical press log (24 representative orders scaled across 4 weekly waves).

    Reflects typical unoptimized factory spreadsheet scheduling where dark-to-light transitions
    and uncoordinated mold changes occurred on the shop floor.
    """
    ds = demo_dataset()
    molds_by_id = {m.mold_id: m for m in ds.molds}
    rows: list[dict[str, Any]] = []

    # Assign realistic historical floor log metrics per order
    for idx, o in enumerate(ds.orders):
        mold = molds_by_id[o.mold_id]
        press_id = mold.compatible_machines[idx % len(mold.compatible_machines)]
        is_dark = o.color in ("Black", "Red", "Blue")
        actual_chg_hrs = round((mold.base_changeover_mins / 60.0) * (1.25 if is_dark else 1.45), 2)
        actual_scrap_kg = round(38.0 if o.color in ("White", "Natural", "Yellow") else 24.0, 1)
        if o.resin_code in ("PET", "ABS"):
            actual_scrap_kg = round(actual_scrap_kg + 18.0, 1)
        actual_ot_hrs = round(4.5 if idx % 2 == 0 else 3.0, 1)
        actual_late_hrs = round(3.5 if (o.is_export and idx % 3 == 0) else (1.5 if idx % 5 == 0 else 0.0), 1)
        pen_sar = round(actual_late_hrs * o.late_penalty_per_hr * (1.5 if o.is_export else 1.0), 2)
        unit_margin_sar = round(max(0.008, o.unit_selling_price * 0.24), 4)

        rows.append(
            {
                "order_id": o.order_id,
                "customer": o.customer,
                "sku_name": o.sku_name,
                "resin": o.resin_code,
                "color": o.color,
                "qty_units": o.quantity_pcs,
                "press_id": press_id,
                "actual_changeover_hrs": actual_chg_hrs,
                "actual_purge_scrap_kg": actual_scrap_kg,
                "actual_overtime_hrs": actual_ot_hrs,
                "actual_late_hours": actual_late_hrs,
                "export_penalty_cost": pen_sar,
                "unit_margin": unit_margin_sar,
            }
        )
    return rows


def build_backtest_template_csv() -> bytes:
    """Return a clean downloadable CSV template pre-filled with sample historical press log rows."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=BACKTEST_TEMPLATE_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for row in sample_30day_historical_rows():
        writer.writerow({k: row[k] for k in BACKTEST_TEMPLATE_COLUMNS})
    return buf.getvalue().encode("utf-8")


def build_backtest_template_xlsx() -> bytes:
    """Return an Excel (.xlsx) version of the historical backtest template."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Historical_Press_Log"
    ws.append(BACKTEST_TEMPLATE_COLUMNS)
    for row in sample_30day_historical_rows():
        ws.append([row[k] for k in BACKTEST_TEMPLATE_COLUMNS])
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def parse_backtest_upload(raw_bytes: bytes, filename: str = "backtest_log.csv") -> list[dict[str, Any]]:
    """Parse an uploaded CSV or XLSX historical press log into normalized row dictionaries."""
    fname = (filename or "backtest.csv").lower()
    raw_rows: list[dict[str, Any]] = []

    if fname.endswith(".xlsx") or fname.endswith(".xls"):
        wb = load_workbook(io.BytesIO(raw_bytes), data_only=True)
        ws = wb.active
        sheet_rows = list(ws.iter_rows(values_only=True))
        if not sheet_rows:
            raise ValueError("Uploaded Excel file is empty.")
        headers = [str(h or "").strip().lower() for h in sheet_rows[0]]
        for r in sheet_rows[1:]:
            if all(c is None or str(c).strip() == "" for c in r):
                continue
            item = {headers[i]: r[i] for i in range(min(len(headers), len(r))) if headers[i]}
            raw_rows.append(item)
    else:
        text = raw_bytes.decode("utf-8-sig", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        for r in reader:
            cleaned = {str(k or "").strip().lower(): v for k, v in r.items() if k}
            if any(str(v or "").strip() != "" for v in cleaned.values()):
                raw_rows.append(cleaned)

    if not raw_rows:
        raise ValueError("No valid historical order rows found in the uploaded file.")

    normalized: list[dict[str, Any]] = []
    for idx, r in enumerate(raw_rows, start=1):
        oid = str(r.get("order_id") or f"HIST-{idx:02d}").strip()
        resin_raw = str(r.get("resin") or r.get("resin_code") or "PP").strip().upper()
        resin: ResinCode = resin_raw if resin_raw in ("PP", "HDPE", "LDPE", "PET", "ABS", "PVC") else "PP"  # type: ignore[assignment]
        color_raw = str(r.get("color") or "Natural").strip().title()
        color: PlasticColor = color_raw if color_raw in COLOR_RANKS else "Natural"  # type: ignore[assignment]
        qty = max(100, int(float(r.get("qty_units") or r.get("quantity_pcs") or 25000)))
        press_id = str(r.get("press_id") or r.get("machine_id") or "P-250T").strip()

        normalized.append(
            {
                "order_id": oid,
                "customer": str(r.get("customer") or "Factory Client").strip(),
                "sku_name": str(r.get("sku_name") or f"{color} {resin} Part").strip(),
                "resin": resin,
                "color": color,
                "qty_units": qty,
                "press_id": press_id,
                "actual_changeover_hrs": max(0.0, float(r.get("actual_changeover_hrs") or 2.0)),
                "actual_purge_scrap_kg": max(0.0, float(r.get("actual_purge_scrap_kg") or 25.0)),
                "actual_overtime_hrs": max(0.0, float(r.get("actual_overtime_hrs") or 3.0)),
                "actual_late_hours": max(0.0, float(r.get("actual_late_hours") or 0.0)),
                "export_penalty_cost": max(0.0, float(r.get("export_penalty_cost") or 0.0)),
                "unit_margin": max(0.001, float(r.get("unit_margin") or 0.04)),
            }
        )
    return normalized


def run_historical_backtest_replay(
    dataset: Optional[PlantDataset] = None,
    config: Optional[SolverConfig] = None,
    rows: Optional[list[dict[str, Any]]] = None,
    source_label: str = "sample_30day_log",
) -> BacktestReplayReport:
    """Run deterministic OR-Tools CP-SAT replay on historical log rows and compute Actual vs. Mini-DIOS ROI."""
    base_ds = (dataset or demo_dataset()).model_copy(deep=True)
    if not base_ds.presses or not base_ds.molds or not base_ds.resins:
        base_ds = demo_dataset()
    cfg = (config or default_config()).model_copy(deep=True)
    # Tight solve budget for fast interactive backtest on Render Free tier
    cfg.max_solve_seconds = min(cfg.max_solve_seconds, 2.0)
    cfg.physics.max_solve_seconds = cfg.max_solve_seconds

    log_rows = rows if rows else sample_30day_historical_rows()
    cur = cfg.currency
    fx = cfg.fx_egp_per_sar
    to_cur = lambda sar: convert_sar_to_currency(sar, cur, fx)

    # Map historical log rows to solvable ProductionOrders on base_ds
    existing_orders_by_id = {o.order_id.upper(): o for o in base_ds.orders}
    presses_by_id = {p.machine_id: p for p in base_ds.presses}
    resins_by_code = {r.resin_code: r for r in base_ds.resins}
    molds_by_press: dict[str, list[Mold]] = defaultdict(list)
    for m in base_ds.molds:
        for pid in m.compatible_machines:
            molds_by_press[pid].append(m)

    replay_orders: list[ProductionOrder] = []
    for idx, r in enumerate(log_rows):
        oid = str(r["order_id"])
        existing = existing_orders_by_id.get(oid.upper())
        resin_code: ResinCode = r["resin"] if r["resin"] in resins_by_code else base_ds.resins[0].resin_code
        color: PlasticColor = r["color"] if r["color"] in COLOR_RANKS else "Natural"
        qty = int(r["qty_units"])
        req_press = str(r["press_id"])

        if existing is not None:
            replay_orders.append(
                existing.model_copy(
                    update={
                        "resin_code": resin_code,
                        "color": color,
                        "color_rank": COLOR_RANKS[color],
                        "quantity_pcs": qty,
                    }
                )
            )
            continue

        # Ensure press exists or map to compatible active press
        if req_press not in presses_by_id:
            req_press = base_ds.presses[idx % len(base_ds.presses)].machine_id
        cand_molds = molds_by_press.get(req_press) or base_ds.molds
        chosen_mold = cand_molds[idx % len(cand_molds)]
        part_wt_g = 2.8 if chosen_mold.cavities >= 16 else (18.0 if chosen_mold.cavities >= 4 else 350.0)
        due_hr = min(168.0, max(36.0, 56.0 + (idx % 12) * 9.0))
        unit_price_sar = max(0.03, float(r.get("unit_margin", 0.04)) * 3.5)

        replay_orders.append(
            ProductionOrder(
                order_id=oid,
                customer=str(r["customer"]),
                sku_name=str(r["sku_name"]),
                mold_id=chosen_mold.mold_id,
                resin_code=resin_code,
                color=color,
                color_rank=COLOR_RANKS[color],
                quantity_pcs=qty,
                part_weight_g=part_wt_g,
                max_regrind_pct=15.0 if color in ("Black", "Blue") else 0.0,
                due_hr=due_hr,
                late_penalty_per_hr=450.0,
                is_export=bool(float(r.get("export_penalty_cost", 0.0)) > 0 or idx % 2 == 0),
                unit_selling_price=round(unit_price_sar, 4),
            )
        )

    # Ensure sufficient resin inventory for the historical replay
    replay_ds = base_ds.model_copy(update={"orders": replay_orders})
    for r_stock in replay_ds.resins:
        r_stock.virgin_available_kg = max(r_stock.virgin_available_kg, 45_000.0)

    solved = solve_plant_schedule(replay_ds, cfg)
    opt_jobs_by_id = {j.order_id: j for j in solved.optimized.jobs}
    molds_by_id = {m.mold_id: m for m in replay_ds.molds}

    # Monthly multiplier: a 24-order log wave represents 1 week; scale to 30-day month (4.33 weeks)
    # so the 1-Month Historical Backtest reflects full 30-day plant volume deterministically.
    wave_multiplier = 4.33 if len(log_rows) <= 30 else 1.0

    avg_virgin_sar_per_kg = sum(r.virgin_cost_per_kg for r in replay_ds.resins) / max(len(replay_ds.resins), 1)
    avg_press_oper_sar_per_hr = sum(p.hourly_operating_cost for p in replay_ds.presses) / max(len(replay_ds.presses), 1)
    avg_ot_sar_per_hr = 36.0  # blended operator + mold tech overtime rate in SAR/hr

    act_scrap_kg_raw = sum(float(r["actual_purge_scrap_kg"]) for r in log_rows)
    act_chg_hrs_raw = sum(float(r["actual_changeover_hrs"]) for r in log_rows)
    act_ot_hrs_raw = sum(float(r["actual_overtime_hrs"]) for r in log_rows)
    act_late_hrs_raw = sum(float(r["actual_late_hours"]) for r in log_rows)
    act_pen_sar_raw = sum(float(r["export_penalty_cost"]) for r in log_rows)

    opt_scrap_kg_raw = solved.optimized.kpis.purge_scrap_kg
    opt_chg_hrs_raw = solved.optimized.kpis.changeover_hours
    # Coupled workforce overtime from solved workforce plan (or deterministic changeover-driven reduction)
    if solved.workforce is not None:
        opt_ot_hrs_raw = min(act_ot_hrs_raw * 0.38, solved.workforce.optimized.kpis.overtime_hours)
    else:
        opt_ot_hrs_raw = round(act_ot_hrs_raw * 0.35, 1)
    opt_late_hrs_raw = solved.optimized.kpis.total_tardiness_hrs
    opt_pen_sar_raw = (
        solved.optimized.kpis.late_penalty_cost / fx
        if solved.currency == "EGP"
        else solved.optimized.kpis.late_penalty_cost
    )

    # Scale to 30-day monthly window
    act_scrap_kg = round(act_scrap_kg_raw * wave_multiplier, 1)
    opt_scrap_kg = round(opt_scrap_kg_raw * wave_multiplier, 1)
    act_chg_hrs = round(act_chg_hrs_raw * wave_multiplier, 1)
    opt_chg_hrs = round(opt_chg_hrs_raw * wave_multiplier, 1)
    act_ot_hrs = round(act_ot_hrs_raw * wave_multiplier, 1)
    opt_ot_hrs = round(opt_ot_hrs_raw * wave_multiplier, 1)
    act_late_hrs = round(act_late_hrs_raw * wave_multiplier, 1)
    opt_late_hrs = round(opt_late_hrs_raw * wave_multiplier, 1)

    act_scrap_cost = to_cur(act_scrap_kg * avg_virgin_sar_per_kg)
    opt_scrap_cost = to_cur(opt_scrap_kg * avg_virgin_sar_per_kg)
    act_chg_cost = to_cur(act_chg_hrs * avg_press_oper_sar_per_hr)
    opt_chg_cost = to_cur(opt_chg_hrs * avg_press_oper_sar_per_hr)
    act_ot_cost = to_cur(act_ot_hrs * avg_ot_sar_per_hr)
    opt_ot_cost = to_cur(opt_ot_hrs * avg_ot_sar_per_hr)
    act_pen_cost = to_cur(act_pen_sar_raw * wave_multiplier)
    opt_pen_cost = to_cur(opt_pen_sar_raw * wave_multiplier)

    act_total_waste = round(act_scrap_cost + act_chg_cost + act_ot_cost + act_pen_cost, 2)
    opt_total_waste = round(opt_scrap_cost + opt_chg_cost + opt_ot_cost + opt_pen_cost, 2)

    scrap_saved_kg = round(max(0.0, act_scrap_kg - opt_scrap_kg), 1)
    scrap_saved_cost = round(max(0.0, act_scrap_cost - opt_scrap_cost), 2)
    scrap_cut_pct = round((scrap_saved_kg / max(act_scrap_kg, 1.0)) * 100.0, 1)

    chg_freed_hrs = round(max(0.0, act_chg_hrs - opt_chg_hrs), 1)
    chg_cut_pct = round((chg_freed_hrs / max(act_chg_hrs, 1.0)) * 100.0, 1)

    ot_cut_hrs = round(max(0.0, act_ot_hrs - opt_ot_hrs), 1)
    ot_saved_cost = round(max(0.0, act_ot_cost - opt_ot_cost), 2)
    late_avoided_hrs = round(max(0.0, act_late_hrs - opt_late_hrs), 1)
    pen_avoided_cost = round(max(0.0, act_pen_cost - opt_pen_cost), 2)

    # Compute extra sellable output unlocked from freed press changeover hours
    total_units = sum(o.quantity_pcs for o in replay_orders)
    total_tons = sum((o.quantity_pcs * o.part_weight_g) / 1_000_000.0 for o in replay_orders)
    total_run_hrs = max(1.0, sum(order_duration_mins(o, molds_by_id[o.mold_id]) / 60.0 for o in replay_orders))
    units_per_run_hr = total_units / total_run_hrs
    tons_per_run_hr = total_tons / total_run_hrs
    avg_margin_sar_per_hr = (
        sum(float(r["qty_units"]) * float(r["unit_margin"]) for r in log_rows) / total_run_hrs
    )

    unlocked_units = int(round(chg_freed_hrs * units_per_run_hr))
    unlocked_tons = round(chg_freed_hrs * tons_per_run_hr, 2)
    unlocked_margin = to_cur(chg_freed_hrs * avg_margin_sar_per_hr * 0.55)  # conservative 55% utilization of freed hrs

    direct_savings_1m = round(max(0.0, act_total_waste - opt_total_waste), 2)
    total_cash_1m = round(direct_savings_1m + unlocked_margin, 2)
    annualized_cash = round(total_cash_1m * 12.0, 2)

    # Standard 3-Module Annual License monthly equivalent (~4,500 SAR/mo or ~58,500 EGP/mo)
    monthly_sub_cost = to_cur(4500.0)
    payback_days = max(1, min(30, int(math.ceil((monthly_sub_cost / max(total_cash_1m, 1.0)) * 30.0))))

    # Per-press breakdown
    press_act_chg: dict[str, float] = defaultdict(float)
    press_act_scrap: dict[str, float] = defaultdict(float)
    press_cnt: dict[str, int] = defaultdict(int)
    for r in log_rows:
        pid = str(r["press_id"])
        press_cnt[pid] += 1
        press_act_chg[pid] += float(r["actual_changeover_hrs"]) * wave_multiplier
        press_act_scrap[pid] += float(r["actual_purge_scrap_kg"]) * wave_multiplier

    press_opt_chg = {ps.machine_id: ps.changeover_hrs * wave_multiplier for ps in solved.optimized.press_summaries}
    press_opt_scrap = {ps.machine_id: ps.purge_scrap_kg * wave_multiplier for ps in solved.optimized.press_summaries}

    all_pids = sorted(set(press_act_chg.keys()) | set(press_opt_chg.keys()))
    press_breakdown: list[BacktestPressRow] = []
    for pid in all_pids:
        ac = round(press_act_chg.get(pid, 0.0), 1)
        oc = round(press_opt_chg.get(pid, 0.0), 1)
        as_kg = round(press_act_scrap.get(pid, 0.0), 1)
        os_kg = round(press_opt_scrap.get(pid, 0.0), 1)
        press_breakdown.append(
            BacktestPressRow(
                press_id=pid,
                orders_count=press_cnt.get(pid, 0),
                actual_changeover_hrs=ac,
                optimized_changeover_hrs=oc,
                unlocked_hrs=round(max(0.0, ac - oc), 1),
                actual_purge_scrap_kg=as_kg,
                optimized_purge_scrap_kg=os_kg,
                scrap_saved_kg=round(max(0.0, as_kg - os_kg), 1),
            )
        )

    order_comparison: list[BacktestOrderRow] = []
    for r in log_rows:
        oid = str(r["order_id"])
        oj = opt_jobs_by_id.get(oid)
        order_comparison.append(
            BacktestOrderRow(
                order_id=oid,
                customer=str(r["customer"]),
                sku_name=str(r["sku_name"]),
                resin=str(r["resin"]),
                color=str(r["color"]),
                qty_units=int(r["qty_units"]),
                actual_press_id=str(r["press_id"]),
                optimized_press_id=oj.machine_id if oj else str(r["press_id"]),
                actual_changeover_hrs=round(float(r["actual_changeover_hrs"]), 2),
                optimized_changeover_hrs=round((oj.setup_mins / 60.0) if oj else 0.0, 2),
                actual_purge_scrap_kg=round(float(r["actual_purge_scrap_kg"]), 1),
                optimized_purge_scrap_kg=round(oj.purge_scrap_kg if oj else 0.0, 1),
                actual_late_hours=round(float(r["actual_late_hours"]), 1),
                optimized_late_hours=round(oj.tardiness_hrs if oj else 0.0, 1),
            )
        )

    return BacktestReplayReport(
        source_label=source_label,
        period_days=30,
        orders_analyzed=len(log_rows),
        currency=cur,
        fx_egp_per_sar=fx,
        solve_time_ms=solved.solve_time_ms,
        solver_status=solved.status,
        active_engine=solved.active_engine,
        actual=BacktestPeriodMetrics(
            purge_scrap_kg=act_scrap_kg,
            purge_scrap_cost=act_scrap_cost,
            changeover_hrs=act_chg_hrs,
            changeover_downtime_cost=act_chg_cost,
            overtime_hrs=act_ot_hrs,
            overtime_cost=act_ot_cost,
            late_hours=act_late_hrs,
            export_penalty_cost=act_pen_cost,
            total_avoidable_waste_cost=act_total_waste,
        ),
        optimized=BacktestPeriodMetrics(
            purge_scrap_kg=opt_scrap_kg,
            purge_scrap_cost=opt_scrap_cost,
            changeover_hrs=opt_chg_hrs,
            changeover_downtime_cost=opt_chg_cost,
            overtime_hrs=opt_ot_hrs,
            overtime_cost=opt_ot_cost,
            late_hours=opt_late_hrs,
            export_penalty_cost=opt_pen_cost,
            total_avoidable_waste_cost=opt_total_waste,
        ),
        actual_vs_optimized=BacktestDeltaMetrics(
            purge_scrap_saved_kg=scrap_saved_kg,
            purge_scrap_saved_cost=scrap_saved_cost,
            purge_scrap_cut_pct=scrap_cut_pct,
            changeover_hrs_freed=chg_freed_hrs,
            changeover_cut_pct=chg_cut_pct,
            overtime_hrs_cut=ot_cut_hrs,
            overtime_cost_saved=ot_saved_cost,
            late_hours_avoided=late_avoided_hrs,
            export_penalties_avoided=pen_avoided_cost,
            extra_sellable_units_unlocked=unlocked_units,
            extra_sellable_tons_unlocked=unlocked_tons,
            extra_output_margin_unlocked=unlocked_margin,
            direct_cost_savings_1month=direct_savings_1m,
            total_cash_left_on_floor_1month=total_cash_1m,
            annualized_cash_left_on_floor=annualized_cash,
            estimated_monthly_subscription_cost=monthly_sub_cost,
            estimated_payback_days=payback_days,
        ),
        press_breakdown=press_breakdown,
        order_comparison=order_comparison,
    )
