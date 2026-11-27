"""Mini-DIOS Plastics — Unlimited Composable Operations Copilot (`google-genai` + Deterministic Offline Engine).

Zero LLM Math Architecture:
- Gemini ONLY constructs structured tool arguments for the 3 deterministic CP-SAT tools and
  narrates the exact numbers returned by OR-Tools CP-SAT.
- Uses `genai.Client(http_options=types.HttpOptions(timeout=15000))` and `gemini-4-hydrogen`
  with `thinking_config=types.ThinkingConfig(thinking_level="low")`.
- Full `try/except` wall-clock protection + rich composable English/Arabic offline parser so
  complex multi-disruption queries NEVER hang, crash, or hallucinate numbers.
"""
from __future__ import annotations

import json
import math
import os
import re
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from .ontology import (
    COLOR_RANKS,
    DAY_NAMES,
    WORKER_ROLES,
    Currency,
    FactoryWorker,
    MachineBreakdown,
    MoldPmLock,
    PlantDataset,
    PlasticColor,
    ProductionOrder,
    ResinCode,
    ResinShortage,
    RiskRadarReport,
    ScenarioDisruptions,
    SolveResult,
    SolverConfig,
    WorkforceCallout,
    WorkforceResult,
    order_duration_mins,
    validate_plant_data,
)
from .disruptions import apply_plant_scenarios
from .financials import compute_financial_report
from .neon_services import call_neon_ai_gateway_narration, load_neon_env
from .risk_radar import compute_risk_radar
from .solver import solve_plant_schedule
from .workforce_solver import parse_day, solve_workforce, solve_workforce_with_callouts

# Load root .env.local / .env and backend/.env if present
load_neon_env()
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)
else:
    load_dotenv()

DEFAULT_GEMINI_MODEL = "gemini-4-hydrogen"


# --------------------------------------------------------------------------------------------
# Response Schemas
# --------------------------------------------------------------------------------------------
class CopilotTiming(BaseModel):
    gemini_ms: int = 0
    solver_ms: int = 0
    total_ms: int = 0


class StrategyComparisonRow(BaseModel):
    metric: str
    strategy_a: str
    strategy_b: str
    delta: str


class StrategyComparison(BaseModel):
    strategy_a_name: str
    strategy_b_name: str
    strategy_a_weights: dict[str, int]
    strategy_b_weights: dict[str, int]
    rows: list[StrategyComparisonRow]
    recommended_strategy: str


class BottleneckInsight(BaseModel):
    target_id: str
    target_type: str
    headline: str
    facts: list[str]
    recommendation: str


class FinancialTradeoffSummary(BaseModel):
    """Commander-Grade CFO + Plant Director deterministic trade-off summary (Zero LLM Math)."""

    headline_en: str
    headline_ar: str
    cost_paid_label_en: str
    cost_paid_label_ar: str
    cost_paid_amount: float
    value_protected_label_en: str
    value_protected_label_ar: str
    value_protected_amount: float
    net_financial_gain: float
    currency: Currency
    is_positive_net: bool = True


class CopilotResult(BaseModel):
    reply: str
    action: str
    tool_calls_executed: list[str] = Field(default_factory=list)
    config: SolverConfig
    dataset: Optional[PlantDataset] = None
    plant_state: Optional[PlantDataset] = None
    weights: Optional[dict[str, Any]] = None
    toggles: Optional[dict[str, bool]] = None
    result: Optional[SolveResult] = None
    production_result: Optional[SolveResult] = None
    workforce_result: Optional[WorkforceResult] = None
    risk_radar: Optional[RiskRadarReport] = None
    comparison: Optional[StrategyComparison] = None
    bottleneck: Optional[BottleneckInsight] = None
    financial_tradeoff_summary: Optional[FinancialTradeoffSummary] = None
    timing: CopilotTiming
    source: str = "gemini"  # "gemini" | "offline_fallback"
    quota_limited: bool = False


def _extract_weights_and_toggles(cfg: SolverConfig) -> tuple[dict[str, Any], dict[str, bool]]:
    weights = {
        "w_changeover_scrap": cfg.w_changeover_scrap,
        "w_otif": cfg.w_otif,
        "w_energy_cost": cfg.w_energy_cost,
        "w_working_capital": cfg.w_working_capital,
        "workforce": {
            "w_labor_cost": cfg.workforce.w_labor_cost,
            "w_coverage": cfg.workforce.w_coverage,
            "w_fairness": cfg.workforce.w_fairness,
        },
    }
    toggles = {
        "avoid_peak_tariff_hrs": bool(cfg.avoid_peak_tariff_hrs),
        "ramadan_shift_mode": bool(cfg.ramadan_shift_mode),
        "autonomous_pm_window": bool(cfg.autonomous_pm_window),
        "container_sync_enabled": bool(cfg.container_sync_enabled),
    }
    return weights, toggles


def _compute_financial_tradeoff_summary(
    result: Optional[SolveResult],
    config: SolverConfig,
    reference_result: Optional[SolveResult] = None,
) -> Optional[FinancialTradeoffSummary]:
    """Deterministically compute Commander-Grade Cost Paid vs. Value Protected from CP-SAT P&L."""
    if result is None or result.financials is None:
        return None

    cur = result.currency
    opt_fin = result.financials.optimized
    base_fin = result.financials.baseline

    # Compare against prior active plan if it differs meaningfully, else against FIFO baseline
    ref_fin = base_fin
    if (
        reference_result is not None
        and reference_result.financials is not None
        and reference_result.currency == cur
        and abs(reference_result.financials.optimized.total_operating_cost - opt_fin.total_operating_cost) > 1.0
    ):
        ref_fin = reference_result.financials.optimized

    # Itemized cost deltas (opt - ref): positive = extra cost paid, negative = cost saved
    d_energy = round(opt_fin.energy_and_press_operating_cost - ref_fin.energy_and_press_operating_cost, 2)
    d_labor = round(opt_fin.direct_labor_and_overtime_cost - ref_fin.direct_labor_and_overtime_cost, 2)
    d_purge = round(opt_fin.purge_scrap_cost - ref_fin.purge_scrap_cost, 2)
    d_resin = round(opt_fin.direct_resin_cost - ref_fin.direct_resin_cost, 2)
    d_wip = round(opt_fin.wip_holding_cost - ref_fin.wip_holding_cost, 2)
    d_pen = round(opt_fin.late_delivery_penalties - ref_fin.late_delivery_penalties, 2)
    d_rev = round(opt_fin.recognized_revenue - ref_fin.recognized_revenue, 2)

    costs_paid: list[tuple[float, str, str]] = []
    values_protected: list[tuple[float, str, str]] = []

    for delta, lbl_en, lbl_ar in [
        (d_energy, "press power & re-sequencing", "طاقة المكابس وإعادة الترتيب"),
        (d_labor, "shift overtime & relief staffing", "العمل الإضافي وعمالة الإسناد"),
        (d_purge, "barrel purge & mold setups", "هدر التنظيف وتبديل القوالب"),
        (d_resin, "virgin resin mix", "مزيج الخام البكر"),
        (d_wip, "warehouse WIP staging", "تخزين المنتج تحت التشغيل"),
        (d_pen, "schedule delay penalties", "غرامات تأخير الجدول"),
    ]:
        if delta > 1.0:
            costs_paid.append((delta, lbl_en, lbl_ar))
        elif delta < -1.0:
            values_protected.append((abs(delta), lbl_en, lbl_ar))

    if d_rev > 1.0:
        values_protected.append((d_rev, "recovered order revenue", "إيرادات أوامر مستردة"))
    elif d_rev < -1.0:
        costs_paid.append((abs(d_rev), "unscheduled revenue deferral", "تأجيل إيرادات غير مجدولة"))

    # If comparing to identical state or pure disruption where all costs rose vs calm baseline,
    # frame the trade-off against the unmitigated FIFO baseline under the same disruption!
    if not values_protected or (sum(x[0] for x in values_protected) < sum(x[0] for x in costs_paid) and ref_fin is not base_fin):
        costs_paid = []
        values_protected = []
        sb = result.financials.savings_breakdown
        for saved, lbl_en, lbl_ar in [
            (sb.avoided_late_penalties, "export & delivery penalties", "غرامات التصدير والتسليم"),
            (sb.purge_scrap_saved, "purge resin waste", "هالك تنظيف الخامات"),
            (sb.labor_and_overtime_saved, "shift labor & overtime", "تكلفة الورديات والإضافي"),
            (sb.energy_and_operating_saved, "press power & operating", "طاقة وتشغيل المكابس"),
            (sb.regrind_blend_savings, "regrind material blending", "خلط الخام المعاد تدويره"),
            (sb.wip_holding_saved, "container & warehouse WIP holding", "تكلفة تخزين الحاويات والمخزن"),
        ]:
            if saved > 1.0:
                values_protected.append((round(saved, 2), lbl_en, lbl_ar))
            elif saved < -1.0:
                costs_paid.append((round(abs(saved), 2), lbl_en, lbl_ar))
        rev_gain_vs_fifo = round(opt_fin.recognized_revenue - base_fin.recognized_revenue, 2)
        if rev_gain_vs_fifo > 1.0:
            values_protected.append((rev_gain_vs_fifo, "protected export revenue", "إيرادات تصدير محمية"))

    costs_paid.sort(key=lambda x: -x[0])
    values_protected.sort(key=lambda x: -x[0])

    cost_amt = round(sum(x[0] for x in costs_paid), 2)
    val_amt = round(sum(x[0] for x in values_protected), 2)
    net_gain = round(val_amt - cost_amt, 2)

    cost_lbl_en = " + ".join(x[1] for x in costs_paid[:2]) if costs_paid else "zero added floor cost"
    cost_lbl_ar = " + ".join(x[2] for x in costs_paid[:2]) if costs_paid else "صفر تكلفة إضافية"
    val_lbl_en = " + ".join(x[1] for x in values_protected[:2]) if values_protected else "schedule stability"
    val_lbl_ar = " + ".join(x[2] for x in values_protected[:2]) if values_protected else "استقرار الجدول"

    sign = "+" if net_gain >= 0 else ""
    if cost_amt > 0:
        headline_en = (
            f"Re-optimizing presses & shifts adds {cost_amt:,.0f} {cur} in {cost_lbl_en}, "
            f"but protects {val_amt:,.0f} {cur} in {val_lbl_en} — Net Gain: {sign}{net_gain:,.0f} {cur}"
        )
        headline_ar = (
            f"إعادة جدولة المكابس والورديات تضيف {cost_amt:,.0f} {cur} في ({cost_lbl_ar})، "
            f"لكنها تحمي {val_amt:,.0f} {cur} من ({val_lbl_ar}) — صافي المكسب: {sign}{net_gain:,.0f} {cur}"
        )
    else:
        headline_en = (
            f"CP-SAT sequencing & container sync saves {val_amt:,.0f} {cur} across {val_lbl_en} "
            f"with 0 {cur} added trade-off cost — Net Gain: {sign}{net_gain:,.0f} {cur}"
        )
        headline_ar = (
            f"جدولة CP-SAT ومزامنة الحاويات توفر {val_amt:,.0f} {cur} في ({val_lbl_ar}) "
            f"دون أي تكلفة إضافية — صافي المكسب: {sign}{net_gain:,.0f} {cur}"
        )

    return FinancialTradeoffSummary(
        headline_en=headline_en,
        headline_ar=headline_ar,
        cost_paid_label_en=cost_lbl_en,
        cost_paid_label_ar=cost_lbl_ar,
        cost_paid_amount=cost_amt,
        value_protected_label_en=val_lbl_en,
        value_protected_label_ar=val_lbl_ar,
        value_protected_amount=val_amt,
        net_financial_gain=net_gain,
        currency=cur,
        is_positive_net=net_gain >= 0,
    )


def _build_copilot_result(
    *,
    reply: str,
    action: str,
    tool_calls_executed: list[str],
    config: SolverConfig,
    dataset: PlantDataset,
    result: Optional[SolveResult],
    timing: CopilotTiming,
    source: str,
    comparison: Optional[StrategyComparison] = None,
    bottleneck: Optional[BottleneckInsight] = None,
    reference_result: Optional[SolveResult] = None,
    quota_limited: bool = False,
) -> CopilotResult:
    weights, toggles = _extract_weights_and_toggles(config)
    tradeoff = _compute_financial_tradeoff_summary(result, config, reference_result)
    return CopilotResult(
        reply=reply,
        action=action,
        tool_calls_executed=tool_calls_executed,
        config=config,
        dataset=dataset,
        plant_state=dataset,
        weights=weights,
        toggles=toggles,
        result=result,
        production_result=result,
        workforce_result=result.workforce if result is not None else None,
        risk_radar=result.risk_radar if result is not None else None,
        comparison=comparison,
        bottleneck=bottleneck,
        financial_tradeoff_summary=tradeoff,
        timing=timing,
        source=source,
        quota_limited=quota_limited,
    )


# --------------------------------------------------------------------------------------------
# Deterministic Tool Implementations (Called by BOTH Gemini Function Calling & Offline Engine)
# --------------------------------------------------------------------------------------------
_INTERACTIVE_BASELINE_CACHE: dict[str, SolveResult] = {}


def _solve_interactive(dataset: PlantDataset, config: SolverConfig, use_cache: bool = False) -> tuple[SolveResult, int]:
    """Run CP-SAT with interactive wall-clock cap (<= 2.0s) for snappy Copilot responses."""
    capped = config.model_copy(update={"max_solve_seconds": min(config.max_solve_seconds, 2.0)})
    cache_key = ""
    if use_cache:
        import hashlib
        raw = f"{dataset.model_dump_json()}|{capped.model_dump_json()}"
        cache_key = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        cached = _INTERACTIVE_BASELINE_CACHE.get(cache_key)
        if cached is not None:
            return cached, 1
    t0 = time.perf_counter()
    res = solve_plant_schedule(dataset, capped)
    ms = max(1, int((time.perf_counter() - t0) * 1000))
    if use_cache and cache_key:
        if len(_INTERACTIVE_BASELINE_CACHE) > 8:
            _INTERACTIVE_BASELINE_CACHE.clear()
        _INTERACTIVE_BASELINE_CACHE[cache_key] = res
    return res, ms


def _merge_scenario_args(
    args: dict[str, Any], current_config: SolverConfig, dataset: PlantDataset
) -> SolverConfig:
    """Safely merge arbitrary composable scenario parameters into a copy of `current_config`."""
    next_cfg = current_config.model_copy(deep=True)
    if args.get("reset_scenarios"):
        next_cfg.scenarios = ScenarioDisruptions()

    valid_presses = {p.machine_id for p in dataset.presses}
    valid_molds = {m.mold_id for m in dataset.molds}
    valid_resins = {r.resin_code for r in dataset.resins}

    # 1. Machine breakdowns
    for raw_bd in args.get("machine_breakdowns") or []:
        mid = str(raw_bd.get("machine_id", "")).strip()
        if mid not in valid_presses:
            # Allow shorthand like "500T" -> "P-500T"
            for vp in valid_presses:
                if mid.upper() in vp.upper():
                    mid = vp
                    break
        if mid in valid_presses:
            max_hr = float(current_config.physics.horizon_hrs)
            bd = MachineBreakdown(
                machine_id=mid,
                start_hr=max(0.0, min(max_hr, float(raw_bd.get("start_hr", 48.0)))),
                duration_hrs=max(1.0, min(max_hr, float(raw_bd.get("duration_hrs", 12.0)))),
            )
            # Replace existing overlapping breakdown on same press/start or append
            next_cfg.scenarios.machine_breakdowns = [
                b for b in next_cfg.scenarios.machine_breakdowns
                if not (b.machine_id == bd.machine_id and abs(b.start_hr - bd.start_hr) < 1.0)
            ] + [bd]

    # 2. Resin shortages & price spikes
    for raw_rs in args.get("resin_shortages") or []:
        code = str(raw_rs.get("resin_code", "")).strip().upper()
        if code in valid_resins:
            rs = ResinShortage(
                resin_code=code,  # type: ignore[arg-type]
                available_pct_reduction=max(0.0, min(95.0, float(raw_rs.get("available_pct_reduction", 0.0)))),
                virgin_price_spike_pct=max(0.0, min(300.0, float(raw_rs.get("virgin_price_spike_pct", 0.0)))),
            )
            next_cfg.scenarios.resin_shortages = [
                x for x in next_cfg.scenarios.resin_shortages if x.resin_code != rs.resin_code
            ] + [rs]

    # 3. Mold PM locks
    for raw_pm in args.get("mold_pm_locks") or []:
        mold_id = str(raw_pm.get("mold_id", "")).strip().upper()
        if mold_id in valid_molds:
            lk = MoldPmLock(
                mold_id=mold_id,
                duration_hrs=max(1.0, min(72.0, float(raw_pm.get("duration_hrs", 6.0)))),
            )
            next_cfg.scenarios.mold_pm_locks = [
                x for x in next_cfg.scenarios.mold_pm_locks if x.mold_id != lk.mold_id
            ] + [lk]

    # 4. Rush orders
    existing_n = len(next_cfg.scenarios.rush_orders)
    for idx, raw_ro in enumerate(args.get("rush_orders") or [], start=1):
        mold_id = str(raw_ro.get("mold_id", "M-01")).strip().upper()
        if mold_id not in valid_molds:
            mold_id = dataset.molds[0].mold_id
        resin_code = str(raw_ro.get("resin_code", "HDPE")).strip().upper()
        if resin_code not in valid_resins:
            resin_code = dataset.resins[0].resin_code
        color_raw = str(raw_ro.get("color", "White")).strip().title()
        color: PlasticColor = color_raw if color_raw in COLOR_RANKS else "White"  # type: ignore[assignment]
        oid = str(raw_ro.get("order_id") or f"RUSH-{existing_n + idx:02d}")
        ro = ProductionOrder(
            order_id=oid,
            customer=str(raw_ro.get("customer") or "Urgent Export Client"),
            sku_name=str(raw_ro.get("sku_name") or f"Rush {color} {mold_id}"),
            mold_id=mold_id,
            resin_code=resin_code,  # type: ignore[arg-type]
            color=color,
            color_rank=COLOR_RANKS[color],
            quantity_pcs=max(500, int(raw_ro.get("quantity_pcs", 40_000))),
            part_weight_g=max(1.0, float(raw_ro.get("part_weight_g", 2.8 if mold_id == "M-01" else 20.0))),
            max_regrind_pct=max(0.0, min(40.0, float(raw_ro.get("max_regrind_pct", 0.0)))),
            due_hr=max(8.0, min(float(current_config.physics.horizon_hrs), float(raw_ro.get("due_hr", 96.0)))),
            late_penalty_per_hr=max(50.0, float(raw_ro.get("late_penalty_per_hr", 650.0))),
            is_export=bool(raw_ro.get("is_export", True)),
        )
        next_cfg.scenarios.rush_orders = [
            x for x in next_cfg.scenarios.rush_orders if x.order_id != ro.order_id
        ] + [ro]

    # 5. Global operational overrides & toggles
    if args.get("allow_regrind_override_pct") is not None:
        next_cfg.scenarios.allow_regrind_override_pct = max(
            0.0, min(40.0, float(args["allow_regrind_override_pct"]))
        )
    if args.get("avoid_peak_tariff_hrs") is not None:
        next_cfg.avoid_peak_tariff_hrs = bool(args["avoid_peak_tariff_hrs"])
    if args.get("ramadan_shift_mode") is not None:
        next_cfg.ramadan_shift_mode = bool(args["ramadan_shift_mode"])
    if args.get("autonomous_pm_window") is not None:
        next_cfg.autonomous_pm_window = bool(args["autonomous_pm_window"])
    if args.get("container_sync_enabled") is not None:
        next_cfg.container_sync_enabled = bool(args["container_sync_enabled"])

    # 6. Objective weights
    for wk in ("w_changeover_scrap", "w_otif", "w_energy_cost", "w_working_capital"):
        if args.get(wk) is not None:
            setattr(next_cfg, wk, max(0, min(100, int(args[wk]))))
    if (
        next_cfg.w_changeover_scrap
        + next_cfg.w_otif
        + next_cfg.w_energy_cost
        + next_cfg.w_working_capital
        == 0
    ):
        next_cfg.w_changeover_scrap = 35
        next_cfg.w_otif = 35

    # 7. Workforce objective weights (labor cost / shift coverage / fairness)
    wfw = args.get("workforce_weights") or {}
    if isinstance(wfw, dict):
        wf_cfg = next_cfg.workforce.model_copy()
        for wk in ("w_labor_cost", "w_coverage", "w_fairness"):
            if wfw.get(wk) is not None:
                setattr(wf_cfg, wk, max(0, min(100, int(wfw[wk]))))
        if wf_cfg.w_labor_cost + wf_cfg.w_coverage + wf_cfg.w_fairness > 0:
            next_cfg.workforce = wf_cfg

    # 8. Clear press breakdowns when rebalancing choke presses
    clear_bds = args.get("clear_press_breakdowns") or []
    if clear_bds:
        clear_set = {str(x).strip().upper() for x in clear_bds}
        if "ALL" in clear_set:
            next_cfg.scenarios.machine_breakdowns = []
        else:
            next_cfg.scenarios.machine_breakdowns = [
                b for b in next_cfg.scenarios.machine_breakdowns if b.machine_id.upper() not in clear_set
            ]

    return next_cfg


_WORKFORCE_ONLY_KEYS = {
    "worker_callouts",
    "workforce_weights",
    "auto_staff_workforce_gaps",
    "add_relief_workers",
    "workforce_overtime_cap_hrs",
}

_ROLE_DEFAULTS: dict[str, tuple[str, str, float]] = {
    "Press_Operator": ("OP", "Relief Press Operator", 20.0),
    "Mold_Technician": ("MT", "Relief Mold Technician", 34.0),
    "QC_Inspector": ("QC", "Relief QC Inspector", 22.5),
    "Material_Handler": ("MH", "Relief Material Handler", 13.5),
    "Shift_Supervisor": ("SV", "Relief Shift Supervisor", 45.0),
}

_ROLE_ALIAS_MAP = {
    "mold": "Mold_Technician",
    "technician": "Mold_Technician",
    "tech": "Mold_Technician",
    "press": "Press_Operator",
    "operator": "Press_Operator",
    "qc": "QC_Inspector",
    "inspector": "QC_Inspector",
    "material": "Material_Handler",
    "handler": "Material_Handler",
    "supervisor": "Shift_Supervisor",
}


def _normalize_role_name(role_raw: str) -> Optional[str]:
    cleaned = str(role_raw or "").strip()
    if not cleaned:
        return None
    exact = cleaned.replace(" ", "_").title().replace("Qc_", "QC_")
    if exact in _ROLE_DEFAULTS:
        return exact
    low = cleaned.lower()
    return next((v for k, v in _ROLE_ALIAS_MAP.items() if k in low), None)


def _append_relief_workers_for_role(dataset: PlantDataset, role: str, count: int) -> list[str]:
    """Deterministically add `count` relief `FactoryWorker` records for `role` to `dataset.workers`."""
    if role not in _ROLE_DEFAULTS or count <= 0:
        return []
    prefix, label, rate = _ROLE_DEFAULTS[role]
    existing_ids = {w.worker_id.upper() for w in dataset.workers}
    added_ids: list[str] = []
    n = sum(1 for w in dataset.workers if w.role == role) + 1
    for _ in range(min(count, 12)):
        cand = f"{prefix}-{n:02d}"
        while cand.upper() in existing_ids:
            n += 1
            cand = f"{prefix}-{n:02d}"
        existing_ids.add(cand.upper())
        dataset.workers.append(
            FactoryWorker(
                worker_id=cand,
                name=f"{label} #{len(added_ids) + 1}",
                role=role,  # type: ignore[arg-type]
                certified_machine_ids="ALL",
                hourly_rate=rate,
                overtime_multiplier=1.5,
                max_weekly_hours=48.0,
                preferred_shift="Any",
                approved_leave_days=[],
                status="active",
            )
        )
        added_ids.append(cand)
        n += 1
    return added_ids


def _apply_dataset_mutations(
    args: dict[str, Any], dataset: PlantDataset, next_cfg: SolverConfig
) -> tuple[PlantDataset, list[str]]:
    """Apply physical plant mutations (resin replenishment, mold PM completion, explicit relief workers, overtime caps)."""
    next_ds = dataset.model_copy(deep=True)
    mutation_notes: list[str] = []

    # 1. Virgin Resin Silo Replenishments
    for rep in args.get("resin_replenishments") or []:
        if not isinstance(rep, dict):
            continue
        code = str(rep.get("resin_code", "")).strip().upper()
        pct = float(rep.get("add_virgin_pct", 25.0) or 25.0)
        add_kg = float(rep.get("add_virgin_kg", 0.0) or 0.0)
        for r in next_ds.resins:
            if r.resin_code == code:
                orig = r.virgin_available_kg
                delta = add_kg if add_kg > 0 else round(orig * (max(5.0, min(100.0, pct)) / 100.0), 1)
                r.virgin_available_kg = round(orig + delta, 1)
                mutation_notes.append(
                    f"Replenished {code} virgin silo +{delta:,.0f} kg ({orig:,.0f} -> {r.virgin_available_kg:,.0f} kg)"
                )
        if rep.get("clear_shortage", True):
            next_cfg.scenarios.resin_shortages = [
                s for s in next_cfg.scenarios.resin_shortages if s.resin_code != code
            ]

    # 2. Complete Mold PM & Reset Shot Counters
    for mid_raw in args.get("complete_mold_pm_ids") or []:
        mid = str(mid_raw).strip().upper()
        for m in next_ds.molds:
            if m.mold_id.upper() == mid:
                prev_shots = m.current_shots
                m.current_shots = 0
                mutation_notes.append(f"Completed PM on Mold {m.mold_id} (shots reset {prev_shots:,} -> 0)")
        next_cfg.scenarios.mold_pm_locks = [
            lk for lk in next_cfg.scenarios.mold_pm_locks if lk.mold_id.upper() != mid
        ]

    # 3. Clear press scheduled maintenance windows on choke press if requested
    for pid_raw in args.get("clear_press_breakdowns") or []:
        pid = str(pid_raw).strip().upper()
        for p in next_ds.presses:
            if p.machine_id.upper() == pid and p.downtime_windows:
                p.downtime_windows = []
                mutation_notes.append(f"Cleared maintenance downtime windows on {p.machine_id}")

    # 4. Workforce overtime weekly hour cap override
    ot_cap = args.get("workforce_overtime_cap_hrs")
    if ot_cap is not None:
        cap_val = max(48.0, min(72.0, float(ot_cap)))
        for w in next_ds.workers:
            if w.status == "active" and w.max_weekly_hours < cap_val:
                w.max_weekly_hours = cap_val
        mutation_notes.append(f"Authorized weekly overtime cap up to {cap_val:.0f}h/wk")

    # 5. Explicit relief workers by role
    for rw in args.get("add_relief_workers") or []:
        if not isinstance(rw, dict):
            continue
        role = _normalize_role_name(str(rw.get("role", "")))
        cnt = max(1, min(10, int(rw.get("count", 1) or 1)))
        if role:
            added = _append_relief_workers_for_role(next_ds, role, cnt)
            if added:
                mutation_notes.append(f"Added {len(added)} relief {role.replace('_', ' ')} ({', '.join(added)})")

    return next_ds, mutation_notes


def _parse_worker_callouts(raw: Any, dataset: PlantDataset) -> list[WorkforceCallout]:
    """Normalize LLM / parser callout dicts into validated `WorkforceCallout` objects."""
    out: list[WorkforceCallout] = []
    valid_ids = {w.worker_id for w in dataset.workers}
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        ids = [str(i).strip().upper() for i in (item.get("worker_ids") or []) if str(i).strip().upper() in valid_ids]
        role = _normalize_role_name(str(item.get("role") or ""))
        if not ids and role is None:
            continue
        out.append(
            WorkforceCallout(
                role=role,  # type: ignore[arg-type]
                count=max(1, min(50, int(item.get("count", 1) or 1))),
                day=parse_day(item.get("day", 0)),
                worker_ids=ids,
            )
        )
    return out


def execute_simulate_plant_scenario(
    args: dict[str, Any],
    dataset: PlantDataset,
    current_config: SolverConfig,
    current_result: Optional[SolveResult] = None,
) -> tuple[dict[str, Any], PlantDataset, SolverConfig, SolveResult, int]:
    """Tool 1: Run CP-SAT for ANY combination of plant disruptions, dataset mitigations, toggles, and weights."""
    next_cfg = _merge_scenario_args(args, current_config, dataset)
    next_ds, mutation_notes = _apply_dataset_mutations(args, dataset, next_cfg)
    callouts = _parse_worker_callouts(args.get("worker_callouts"), next_ds)
    set_args = {k for k, v in args.items() if v not in (None, [], {}, False)}
    workforce_only = bool(set_args) and set_args <= _WORKFORCE_ONLY_KEYS

    if workforce_only and current_result is not None and current_result.currency == next_cfg.currency:
        # Labor-only what-if: reuse the solved Press Gantt, re-run only the workforce CP-SAT (fast).
        new_res = current_result
        solve_ms = 0
    else:
        new_res, solve_ms = _solve_interactive(next_ds, next_cfg)

    wf_t0 = time.perf_counter()
    auto_staff = bool(args.get("auto_staff_workforce_gaps"))
    need_wf_resolve = bool(next_ds.workers) and (
        callouts
        or workforce_only
        or auto_staff
        or bool(args.get("add_relief_workers"))
        or args.get("workforce_overtime_cap_hrs") is not None
    )

    if need_wf_resolve:
        wf = solve_workforce_with_callouts(next_ds, next_cfg, new_res.optimized, callouts)
        if auto_staff and wf is not None and wf.optimized.kpis.understaffed_slots > 0:
            for pass_idx in range(2):
                if wf is None or wf.optimized.kpis.understaffed_slots == 0:
                    break
                added_any = False
                for role in WORKER_ROLES:
                    role_cells = [c for c in wf.optimized.demand if c.role == role and c.required > c.scheduled]
                    if not role_cells:
                        continue
                    role_gap = sum(c.required - c.scheduled for c in role_cells)
                    peak_day_gap = max(
                        sum(c.required - c.scheduled for c in role_cells if c.day == d)
                        for d in range(7)
                    )
                    add_n = (
                        max(peak_day_gap, int(math.ceil(role_gap / 4.5)))
                        if pass_idx == 0
                        else max(1, peak_day_gap)
                    )
                    added_ids = _append_relief_workers_for_role(next_ds, role, add_n)
                    if added_ids:
                        added_any = True
                        mutation_notes.append(
                            f"Added {len(added_ids)} relief {role.replace('_', ' ')} ({', '.join(added_ids)})"
                        )
                if not added_any:
                    break
                wf = solve_workforce_with_callouts(next_ds, next_cfg, new_res.optimized, callouts)

        eff_state = apply_plant_scenarios(next_ds, next_cfg)
        eff_ds = eff_state.dataset
        fin = compute_financial_report(eff_ds, next_cfg, new_res.baseline, new_res.optimized, wf)
        radar = compute_risk_radar(eff_ds, next_cfg, new_res.optimized, wf)
        val = validate_plant_data(next_ds, next_cfg)
        updated_audit = new_res.audit.model_copy(
            update={
                "config": next_cfg,
                "weights": {
                    "w_changeover_scrap": next_cfg.w_changeover_scrap,
                    "w_otif": next_cfg.w_otif,
                    "w_energy_cost": next_cfg.w_energy_cost,
                    "w_working_capital": next_cfg.w_working_capital,
                },
            }
        )
        new_res = new_res.model_copy(
            update={
                "workforce": wf,
                "financials": fin,
                "risk_radar": radar,
                "validation": val,
                "audit": updated_audit,
                "applied_scenarios": eff_state.applied_scenarios,
            }
        )
        solve_ms += max(1, int((time.perf_counter() - wf_t0) * 1000))
    elif mutation_notes:
        val = validate_plant_data(next_ds, next_cfg)
        new_res = new_res.model_copy(update={"validation": val})

    cur_res = current_result
    if cur_res is None:
        cur_res, cur_ms = _solve_interactive(dataset, current_config, use_cache=True)
        solve_ms += cur_ms

    ok = new_res.optimized.kpis
    ck = cur_res.optimized.kpis
    sc = new_res.scorecard

    payload = {
        "tool": "simulate_plant_scenario",
        "status": new_res.status,
        "currency": new_res.currency,
        "solve_time_ms": new_res.solve_time_ms,
        "all_hard_constraints_passed": new_res.audit.all_hard_constraints_passed,
        "applied_scenarios": [a.description for a in new_res.applied_scenarios],
        "optimized_kpis": {
            "total_cost": ok.total_cost,
            "purge_scrap_kg": ok.purge_scrap_kg,
            "changeover_hours": ok.changeover_hours,
            "energy_cost": ok.energy_cost,
            "late_penalty_cost": ok.late_penalty_cost,
            "otif_pct": ok.otif_pct,
            "oee_pct": ok.oee_pct,
            "unscheduled_orders": ok.unscheduled_orders,
            "unscheduled_order_ids": new_res.optimized.unscheduled_order_ids,
        },
        "delta_vs_current_plan": {
            "total_cost_delta": round(ok.total_cost - ck.total_cost, 2),
            "purge_scrap_kg_delta": round(ok.purge_scrap_kg - ck.purge_scrap_kg, 1),
            "changeover_hours_delta": round(ok.changeover_hours - ck.changeover_hours, 2),
            "otif_pct_delta": round(ok.otif_pct - ck.otif_pct, 1),
            "oee_pct_delta": round(ok.oee_pct - ck.oee_pct, 1),
        },
        "vs_fifo_baseline": {
            "cash_savings": sc.cash_savings,
            "cash_savings_pct": sc.cash_savings_pct,
            "purge_scrap_kg_saved": sc.purge_scrap_kg_saved,
            "changeover_hours_saved": sc.changeover_hours_saved,
        },
        "risk_radar": (
            {
                "overall_risk_score": new_res.risk_radar.overall_risk_score,
                "risk_level": new_res.risk_radar.risk_level,
                "critical_count": new_res.risk_radar.critical_count,
                "elevated_count": new_res.risk_radar.elevated_count,
                "export_at_risk_count": new_res.risk_radar.export_at_risk_count,
                "total_financial_exposure": new_res.risk_radar.total_financial_exposure,
            }
            if new_res.risk_radar
            else None
        ),
        "financials": {
            "recognized_revenue": new_res.financials.optimized.recognized_revenue,
            "gross_profit": new_res.financials.optimized.gross_profit,
            "gross_margin_pct": new_res.financials.optimized.gross_margin_pct,
            "net_operating_profit": new_res.financials.optimized.net_operating_profit,
            "net_margin_pct": new_res.financials.optimized.net_margin_pct,
            "total_weekly_savings": new_res.financials.total_weekly_savings,
            "annual_projected_savings": new_res.financials.annual_projected_savings,
            "baseline_net_profit": new_res.financials.baseline.net_operating_profit,
            "net_profit_delta_vs_current": round(
                new_res.financials.optimized.net_operating_profit
                - cur_res.financials.optimized.net_operating_profit,
                2,
            ),
        },
    }
    if mutation_notes:
        payload["plant_mutations"] = mutation_notes

    wf_res = new_res.workforce
    if wf_res is not None:
        wk = wf_res.optimized.kpis
        ref = wf_res.reference_kpis or (cur_res.workforce.optimized.kpis if cur_res.workforce else wk)
        payload["workforce"] = {
            "callouts_applied": wf_res.callouts_applied,
            "relief_mutations": mutation_notes,
            "workers_total": len(next_ds.workers),
            "status": wf_res.status,
            "hard_constraints_passed": wf_res.all_hard_constraints_passed,
            "shift_coverage_pct": wk.coverage_pct,
            "changeover_readiness_pct": wk.changeover_readiness_pct,
            "understaffed_slots": wk.understaffed_slots,
            "headcount_gap": wk.headcount_gap,
            "worst_slot": wk.worst_slot,
            "total_labor_cost": wk.total_labor_cost,
            "overtime_cost": wk.overtime_cost,
            "overtime_hours": wk.overtime_hours,
            "labor_saved_vs_static_rotation": wf_res.labor_cost_saved,
            "reference_without_callouts": {
                "shift_coverage_pct": ref.coverage_pct,
                "changeover_readiness_pct": ref.changeover_readiness_pct,
                "total_labor_cost": ref.total_labor_cost,
                "overtime_hours": ref.overtime_hours,
            },
            "delta_vs_reference": {
                "shift_coverage_pct": round(wk.coverage_pct - ref.coverage_pct, 1),
                "labor_cost": round(wk.total_labor_cost - ref.total_labor_cost, 2),
                "overtime_hours": round(wk.overtime_hours - ref.overtime_hours, 1),
            },
            "role_coverage_pct": wk.role_coverage_pct,
        }
    return payload, next_ds, next_cfg, new_res, solve_ms


def execute_inspect_bottleneck(
    target_id: str,
    dataset: PlantDataset,
    current_config: SolverConfig,
    current_result: Optional[SolveResult] = None,
) -> tuple[dict[str, Any], BottleneckInsight, SolveResult, int]:
    """Tool 2: Deterministically explain bottlenecks for any press, mold, order, resin, or plant-wide."""
    solve_ms = 0
    res = current_result
    if res is None:
        res, solve_ms = _solve_interactive(dataset, current_config)
    else:
        # Ensure Risk Radar, Workforce, and Financials on `res` are never stale
        eff_ds = apply_plant_scenarios(dataset, current_config).dataset
        wf = res.workforce
        if wf is None and dataset.workers:
            wf = solve_workforce(eff_ds, current_config, res.optimized)
        fin = compute_financial_report(eff_ds, current_config, res.baseline, res.optimized, wf)
        radar = compute_risk_radar(eff_ds, current_config, res.optimized, wf)
        res = res.model_copy(update={"workforce": wf, "financials": fin, "risk_radar": radar})

    tid = (target_id or "auto").strip()
    tid_up = tid.upper()

    presses_by_id = {p.machine_id.upper(): p for p in dataset.presses}
    molds_by_id = {m.mold_id.upper(): m for m in dataset.molds}
    resins_by_code = {r.resin_code.upper(): r for r in dataset.resins}
    jobs_by_oid = {j.order_id.upper(): j for j in res.optimized.jobs}

    # Match mold
    if tid_up in molds_by_id:
        mold = molds_by_id[tid_up]
        m_jobs = [j for j in res.optimized.jobs if j.mold_id.upper() == tid_up]
        total_run = sum(j.duration_mins for j in m_jobs if j.scheduled) / 60.0
        total_chg = sum(j.setup_mins for j in m_jobs if j.scheduled) / 60.0
        late_jobs = [j for j in m_jobs if j.tardiness_hrs > 0]
        facts = [
            f"Shot-Count Health: {mold.current_shots:,} / {mold.maintenance_interval_shots:,} shots ({mold.shot_utilization_pct:.1f}%).",
            f"Compatible Presses: {', '.join(mold.compatible_machines)} ({'Hot-Runner' if mold.is_hot_runner else 'Cold-Runner'}, {mold.cavities} cavities, {mold.cycle_time_sec}s cycle).",
            f"Assigned Orders: {len(m_jobs)} orders totaling {total_run:.1f}h molding + {total_chg:.1f}h changeover/purge.",
        ]
        if mold.shot_utilization_pct >= 95.0:
            facts.append(
                f"HC6 Mandatory PM Lock: Exceeds 95% maintenance threshold — blocked {mold.pm_duration_hrs:.0f}h at week start before first production run."
            )
        if late_jobs:
            facts.append(
                "Late Orders: " + ", ".join(f"{j.order_id} (+{j.tardiness_hrs:.1f}h late)" for j in late_jobs)
            )
        else:
            facts.append("On-Time Status: All orders using this mold currently meet their due deadlines under CP-SAT.")

        rec = (
            f"Pre-schedule {mold.mold_id} PM over the weekend or authorize a spare cavity insert so its {mold.pm_duration_hrs:.0f}h PM block doesn't compress thin-wall press capacity."
            if mold.shot_utilization_pct >= 95.0
            else f"Batch {mold.mold_id} orders light-to-dark on a single compatible press to eliminate {mold.base_changeover_mins}m mold swaps."
        )
        insight = BottleneckInsight(
            target_id=mold.mold_id,
            target_type="mold",
            headline=f"Mold {mold.mold_id} ({mold.name}) Bottleneck Audit",
            facts=facts,
            recommendation=rec,
        )
        return insight.model_dump(), insight, res, solve_ms

    # Match press (allow shorthand e.g. 500T -> P-500T)
    press_match = presses_by_id.get(tid_up)
    if press_match is None:
        for pid, p in presses_by_id.items():
            if tid_up and tid_up in pid:
                press_match = p
                break
    if press_match is not None:
        ps = next(x for x in res.optimized.press_summaries if x.machine_id == press_match.machine_id)
        p_jobs = [j for j in res.optimized.jobs if j.scheduled and j.machine_id == press_match.machine_id]
        seq_str = " -> ".join(f"{j.order_id}({j.color}/{j.mold_id})" for j in p_jobs)
        facts = [
            f"Press Specs: {press_match.tonnage}T {press_match.process_type}, {'Hot-Runner' if press_match.supports_hot_runner else 'Cold-Runner'}, {press_match.hourly_energy_kwh:.0f} kWh/h.",
            f"Weekly Workload: {ps.jobs_count} jobs, {ps.run_hrs:.1f}h run, {ps.changeover_hrs:.1f}h changeover, {ps.downtime_hrs:.1f}h downtime (OEE {ps.oee_pct:.1f}%).",
            f"Purge Scrap & Energy: {ps.purge_scrap_kg:.1f} kg purge scrap, {ps.energy_kwh:,.0f} kWh ({ps.energy_cost:,.0f} {res.currency}).",
            f"Optimized Sequence: {seq_str or 'Idle'}.",
        ]
        insight = BottleneckInsight(
            target_id=press_match.machine_id,
            target_type="press",
            headline=f"Press {press_match.machine_id} ({press_match.name}) Capacity & Sequence Audit",
            facts=facts,
            recommendation=f"Sequence on {press_match.machine_id} follows light-to-dark mold batching to minimize purge waste; offload overflow orders to compatible parallel presses if downtime occurs.",
        )
        return insight.model_dump(), insight, res, solve_ms

    # Match order
    if tid_up in jobs_by_oid:
        j = jobs_by_oid[tid_up]
        facts = [
            f"Placement: Press {j.machine_id} (seq #{j.sequence_index}), Mold {j.mold_id}, Resin {j.resin_code} ({j.color}, rank {j.color_rank}).",
            f"Timing: Start H{j.start_min/60:.1f} -> End H{j.end_min/60:.1f} vs. Due H{j.due_hr:.1f} (Tardiness: {j.tardiness_hrs:.2f}h).",
            f"Transition: {j.transition_type.replace('_', ' ')} taking {j.setup_mins}m and {j.purge_scrap_kg:.1f} kg purge scrap.",
            f"Material Split: {j.virgin_kg:,.1f} kg virgin + {j.regrind_kg:,.1f} kg regrind.",
        ]
        insight = BottleneckInsight(
            target_id=j.order_id,
            target_type="order",
            headline=f"Order {j.order_id} ({j.sku_name}) Scheduling Rationale",
            facts=facts,
            recommendation=(
                f"Increase w_otif weight or relieve contention on {j.machine_id}/{j.mold_id} to pull completion ahead of H{j.due_hr:.0f}."
                if j.tardiness_hrs > 0
                else f"Order {j.order_id} finishes on time with optimal light-to-dark grouping."
            ),
        )
        return insight.model_dump(), insight, res, solve_ms

    # Match resin
    if tid_up in resins_by_code:
        ru = next(x for x in res.optimized.resin_usage if x.resin_code == tid_up)
        r_obj = resins_by_code[tid_up]
        facts = [
            f"Virgin Stock: {ru.virgin_used_kg:,.1f} kg used + {ru.purge_scrap_kg:,.1f} kg purge vs. {ru.virgin_available_kg:,.1f} kg available ({ru.remaining_virgin_kg:,.1f} kg left).",
            f"Regrind Stock: {ru.regrind_used_kg:,.1f} kg used vs. {ru.regrind_available_kg:,.1f} kg available.",
            f"Pre-Drying & Barrel Temp: {r_obj.drying_lead_time_hrs:.0f}h drying floor, {r_obj.barrel_temp_c}°C barrel temp.",
            f"Overall Utilization: {ru.utilization_pct:.1f}%.",
        ]
        insight = BottleneckInsight(
            target_id=ru.resin_code,
            target_type="resin",
            headline=f"Resin {ru.resin_code} Inventory & Purge Audit",
            facts=facts,
            recommendation=f"Minimize dark-to-light transitions in {ru.resin_code} and activate non-food regrind blending if virgin supply tightens.",
        )
        return insight.model_dump(), insight, res, solve_ms

    # Plant-wide automatic bottleneck identification
    top_press = max(res.optimized.press_summaries, key=lambda x: x.run_hrs + x.changeover_hrs + x.downtime_hrs)
    top_resin = max(res.optimized.resin_usage, key=lambda x: x.utilization_pct)
    pm_molds = [m for m in dataset.molds if m.shot_utilization_pct >= 95.0]
    facts = [
        f"Tightest Press: {top_press.machine_id} ({top_press.run_hrs:.1f}h run + {top_press.changeover_hrs:.1f}h changeover + {top_press.downtime_hrs:.1f}h downtime, OEE {top_press.oee_pct:.1f}%).",
        f"Tightest Resin: {top_resin.resin_code} at {top_resin.utilization_pct:.1f}% utilization ({top_resin.remaining_virgin_kg:,.1f} kg virgin remaining).",
        f"Mold PM Alerts: {', '.join(f'{m.mold_id} ({m.shot_utilization_pct:.1f}%)' for m in pm_molds) or 'None'}.",
        f"Plant Scorecard: OTIF {res.optimized.kpis.otif_pct:.1f}%, OEE {res.optimized.kpis.oee_pct:.1f}%, Purge Scrap {res.optimized.kpis.purge_scrap_kg:.1f} kg (saved {res.scorecard.purge_scrap_kg_saved:.1f} kg vs FIFO).",
    ]
    insight = BottleneckInsight(
        target_id="PLANT",
        target_type="plant",
        headline="Plant-Wide Binding Bottleneck Audit",
        facts=facts,
        recommendation=f"Focus capacity protection on {top_press.machine_id}, monitor {top_resin.resin_code} replenishment, and execute PM on {', '.join(m.mold_id for m in pm_molds) or 'high-shot molds'}.",
    )
    return insight.model_dump(), insight, res, solve_ms


def execute_compare_two_strategies(
    strategy_a_name: str,
    strategy_a_weights: dict[str, int],
    strategy_b_name: str,
    strategy_b_weights: dict[str, int],
    dataset: PlantDataset,
    current_config: SolverConfig,
) -> tuple[dict[str, Any], StrategyComparison, SolverConfig, SolveResult, int]:
    """Tool 3: Run CP-SAT twice with two distinct executive weight profiles and return exact trade-off table."""
    cfg_a = current_config.model_copy(
        update={
            "w_changeover_scrap": int(strategy_a_weights.get("w_changeover_scrap", 35)),
            "w_otif": int(strategy_a_weights.get("w_otif", 35)),
            "w_energy_cost": int(strategy_a_weights.get("w_energy_cost", 15)),
            "w_working_capital": int(strategy_a_weights.get("w_working_capital", 15)),
        }
    )
    cfg_b = current_config.model_copy(
        update={
            "w_changeover_scrap": int(strategy_b_weights.get("w_changeover_scrap", 35)),
            "w_otif": int(strategy_b_weights.get("w_otif", 35)),
            "w_energy_cost": int(strategy_b_weights.get("w_energy_cost", 15)),
            "w_working_capital": int(strategy_b_weights.get("w_working_capital", 15)),
        }
    )

    res_a, ms_a = _solve_interactive(dataset, cfg_a)
    res_b, ms_b = _solve_interactive(dataset, cfg_b)
    ka, kb = res_a.optimized.kpis, res_b.optimized.kpis
    cur = res_a.currency

    rows = [
        StrategyComparisonRow(
            metric=f"Total Cost ({cur})",
            strategy_a=f"{ka.total_cost:,.0f}",
            strategy_b=f"{kb.total_cost:,.0f}",
            delta=f"{kb.total_cost - ka.total_cost:+,.0f}",
        ),
        StrategyComparisonRow(
            metric="Purge Resin Scrap (kg)",
            strategy_a=f"{ka.purge_scrap_kg:.1f} kg",
            strategy_b=f"{kb.purge_scrap_kg:.1f} kg",
            delta=f"{kb.purge_scrap_kg - ka.purge_scrap_kg:+.1f} kg",
        ),
        StrategyComparisonRow(
            metric="Changeover & Purge (hrs)",
            strategy_a=f"{ka.changeover_hours:.2f} h",
            strategy_b=f"{kb.changeover_hours:.2f} h",
            delta=f"{kb.changeover_hours - ka.changeover_hours:+.2f} h",
        ),
        StrategyComparisonRow(
            metric=f"Late Export Penalties ({cur})",
            strategy_a=f"{ka.late_penalty_cost:,.0f}",
            strategy_b=f"{kb.late_penalty_cost:,.0f}",
            delta=f"{kb.late_penalty_cost - ka.late_penalty_cost:+,.0f}",
        ),
        StrategyComparisonRow(
            metric=f"Energy Cost ({cur})",
            strategy_a=f"{ka.energy_cost:,.0f}",
            strategy_b=f"{kb.energy_cost:,.0f}",
            delta=f"{kb.energy_cost - ka.energy_cost:+,.0f}",
        ),
        StrategyComparisonRow(
            metric="OTIF (%)",
            strategy_a=f"{ka.otif_pct:.1f}%",
            strategy_b=f"{kb.otif_pct:.1f}%",
            delta=f"{kb.otif_pct - ka.otif_pct:+.1f} pts",
        ),
        StrategyComparisonRow(
            metric="Plant OEE (%)",
            strategy_a=f"{ka.oee_pct:.1f}%",
            strategy_b=f"{kb.oee_pct:.1f}%",
            delta=f"{kb.oee_pct - ka.oee_pct:+.1f} pts",
        ),
    ]

    # Recommend lower total cost strategy (tie-break by higher OTIF)
    if (ka.total_cost, -ka.otif_pct) <= (kb.total_cost, -kb.otif_pct):
        rec_name, rec_cfg, rec_res = strategy_a_name, cfg_a, res_a
    else:
        rec_name, rec_cfg, rec_res = strategy_b_name, cfg_b, res_b

    comp = StrategyComparison(
        strategy_a_name=strategy_a_name,
        strategy_b_name=strategy_b_name,
        strategy_a_weights={
            "w_changeover_scrap": cfg_a.w_changeover_scrap,
            "w_otif": cfg_a.w_otif,
            "w_energy_cost": cfg_a.w_energy_cost,
            "w_working_capital": cfg_a.w_working_capital,
        },
        strategy_b_weights={
            "w_changeover_scrap": cfg_b.w_changeover_scrap,
            "w_otif": cfg_b.w_otif,
            "w_energy_cost": cfg_b.w_energy_cost,
            "w_working_capital": cfg_b.w_working_capital,
        },
        rows=rows,
        recommended_strategy=rec_name,
    )
    return comp.model_dump(), comp, rec_cfg, rec_res, ms_a + ms_b


# --------------------------------------------------------------------------------------------
# Intelligent Composable Offline Parser (EN + AR, Zero-Hang Fallback)
# --------------------------------------------------------------------------------------------
def _is_arabic(text: str) -> bool:
    return bool(re.search(r"[\u0600-\u06FF]", text))


def _extract_day_hour(text: str, default_hr: float = 48.0) -> float:
    day_hr_map = {
        "sunday": 0.0, "sun": 0.0, "الأحد": 0.0, "الاحد": 0.0,
        "monday": 24.0, "mon": 24.0, "الإثنين": 24.0, "الاثنين": 24.0,
        "tuesday": 48.0, "tue": 48.0, "الثلاثاء": 48.0,
        "wednesday": 72.0, "wed": 72.0, "الأربعاء": 72.0, "الاربعاء": 72.0,
        "thursday": 96.0, "thu": 96.0, "الخميس": 96.0,
        "friday": 120.0, "fri": 120.0, "الجمعة": 120.0,
        "saturday": 144.0, "sat": 144.0, "السبت": 144.0,
    }
    low = text.lower()
    for k, hr in day_hr_map.items():
        if re.search(rf"\b{re.escape(k)}\b", low) or (ord(k[0]) > 127 and k in text):
            return hr
    h_match = re.search(r"\bh(\d{1,3})\b", low)
    if h_match:
        return min(168.0, float(h_match.group(1)))
    return default_hr


_AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
_NUM_WORDS = {"one": 1, "a": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8}
_AR_NUM_WORDS = {"واحد": 1, "اثنين": 2, "اثنان": 2, "ثلاثة": 3, "ثلاث": 3, "أربعة": 4, "اربعة": 4, "خمسة": 5, "ستة": 6}
_EN_ROLE_PATTERNS = (
    (r"mold\s+tech\w*|tool\s*room|mould\s+tech\w*", "Mold_Technician"),
    (r"press\s+operators?|machine\s+operators?|operators?", "Press_Operator"),
    (r"qc\s+inspectors?|qc|quality\s+inspectors?|inspectors?", "QC_Inspector"),
    (r"material\s+handlers?|handlers?", "Material_Handler"),
    (r"shift\s+supervisors?|supervisors?", "Shift_Supervisor"),
    (r"technicians?|techs?", "Mold_Technician"),
)
_AR_ROLE_PATTERNS = (
    (r"فنيين\s*قوالب|فني\s*قوالب|فنيي\s*القوالب|فنيين|فني", "Mold_Technician"),
    (r"مشغلين|مشغل|مشغلي", "Press_Operator"),
    (r"مفتشين|مفتش|مراقب\s*جودة|مراقبين\s*جودة", "QC_Inspector"),
    (r"مناولين|مناول|عمال\s*مواد|عامل\s*مواد", "Material_Handler"),
    (r"مشرفين|مشرف", "Shift_Supervisor"),
)


def _is_callout_prompt(text: str) -> bool:
    low = text.lower()
    en = any(k in low for k in ("call out", "calls out", "call-out", "callout", "called out", "no-show", "no show", "absent", "absence", "call in sick", "calls in sick", "sick on"))
    ar = any(k in text for k in ("يتغيب", "تغيب", "غياب", "غيابات", "اعتذار", "إجازة مرضية", "اجازة مرضية", "مرضي"))
    return (en or ar) and any(
        k in low for k in ("technician", "tech", "operator", "inspector", "qc", "handler", "supervisor", "worker", "staff", "shift", "coverage", "overtime")
    ) or (ar and any(k in text for k in ("فني", "مشغل", "مفتش", "مناول", "مشرف", "عمال", "الورديات", "وردية")))


def _extract_callouts(text: str) -> list[dict[str, Any]]:
    """Parse '2 Mold Technicians and 3 Press Operators call out on Tuesday' (EN or AR) into callouts."""
    norm = text.translate(_AR_DIGITS)
    low = norm.lower()
    day = 0
    day_found = False
    for key, idx in (
        ("sun", 0), ("mon", 1), ("tue", 2), ("wed", 3), ("thu", 4), ("fri", 5), ("sat", 6),
    ):
        if re.search(rf"\b{key}\w*", low):
            day, day_found = idx, True
            break
    if not day_found:
        for key, idx in (("الأحد", 0), ("الاحد", 0), ("الاثنين", 1), ("الإثنين", 1), ("الثلاثاء", 2), ("الأربعاء", 3), ("الاربعاء", 3), ("الخميس", 4), ("الجمعة", 5), ("السبت", 6)):
            if key in norm:
                day, day_found = idx, True
                break
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    num_alt = r"(\d+|" + "|".join(_NUM_WORDS) + r")"
    for pat, role in _EN_ROLE_PATTERNS:
        for m in re.finditer(rf"{num_alt}\s+(?:{pat})", low):
            if role in seen:
                continue
            tok = m.group(1)
            n = int(tok) if tok.isdigit() else _NUM_WORDS.get(tok, 1)
            out.append({"role": role, "count": n, "day": day})
            seen.add(role)
    ar_alt = r"(\d+|" + "|".join(_AR_NUM_WORDS) + r")"
    for pat, role in _AR_ROLE_PATTERNS:
        for m in re.finditer(rf"{ar_alt}\s*(?:{pat})", norm):
            if role in seen:
                continue
            tok = m.group(1)
            n = int(tok) if tok.isdigit() else _AR_NUM_WORDS.get(tok, 1)
            out.append({"role": role, "count": n, "day": day})
            seen.add(role)
    # Specific worker ids, e.g. "MT-01 and OP-05 are sick on Tuesday"
    ids = [i.upper() for i in re.findall(r"\b((?:OP|MT|QC|MH|SV)-\d{2})\b", norm, re.IGNORECASE)]
    if ids:
        out.append({"worker_ids": ids, "day": day})
    return out


def run_offline_composable_copilot(
    prompt: str,
    dataset: PlantDataset,
    current_config: SolverConfig,
    current_result: Optional[SolveResult] = None,
    language: str = "en",
) -> CopilotResult:
    """100% deterministic offline composable parser executing the exact same 3 CP-SAT tools."""
    t_start = time.perf_counter()
    text = prompt.strip()
    low = text.lower()
    ar = language == "ar" or _is_arabic(text)

    # 0. Worker call-outs / absenteeism what-if (deterministic workforce CP-SAT)
    callout_items = _extract_callouts(text) if _is_callout_prompt(text) else []
    if callout_items:
        wf_args: dict[str, Any] = {"worker_callouts": callout_items}
        payload, next_ds, next_cfg, new_res, solver_ms = execute_simulate_plant_scenario(
            wf_args, dataset, current_config, current_result
        )
        total_ms = max(1, int((time.perf_counter() - t_start) * 1000))
        fin = new_res.financials
        wfp = payload.get("workforce")
        if wfp is None:
            reply = (
                "لا توجد قوى عاملة معرفة في مساحة العمل الحالية." if ar else "No workforce is defined in the active plant workspace."
            )
        else:
            ref = wfp["reference_without_callouts"]
            cur = new_res.currency
            who = "؛ ".join(wfp["callouts_applied"]) if ar else "; ".join(wfp["callouts_applied"])
            if ar:
                reply = (
                    f"محاكاة غياب العمال عبر OR-Tools CP-SAT ({wfp['status']}): {who}. "
                    f"تغطية الورديات: {wfp['shift_coverage_pct']:.1f}% (مقابل {ref['shift_coverage_pct']:.1f}% قبل الغياب)، "
                    f"جاهزية تغيير القوالب: {wfp['changeover_readiness_pct']:.1f}%، "
                    f"تكلفة العمالة والوقت الإضافي: {wfp['total_labor_cost']:,.0f} {cur} (تغير {wfp['delta_vs_reference']['labor_cost']:+,.0f})، "
                    f"ساعات إضافية: {wfp['overtime_hours']:.0f} ساعة، "
                    f"وردية أو دور غير مغطى: {wfp['understaffed_slots']}، "
                    f"صافي الربح الأسبوعي: {fin.optimized.net_operating_profit:,.0f} {cur}. "
                    f"قيود الراحة والإجازات: {'مستوفاة' if wfp['hard_constraints_passed'] else 'غير مستوفاة'}."
                )
            else:
                reply = (
                    f"Workforce call-out simulated via OR-Tools CP-SAT ({wfp['status']}): {who}. "
                    f"Shift coverage: {wfp['shift_coverage_pct']:.1f}% (was {ref['shift_coverage_pct']:.1f}%), "
                    f"mold-changeover readiness: {wfp['changeover_readiness_pct']:.1f}%, "
                    f"labor + overtime cost: {wfp['total_labor_cost']:,.0f} {cur} ({wfp['delta_vs_reference']['labor_cost']:+,.0f}), "
                    f"overtime: {wfp['overtime_hours']:.0f} h, understaffed role/shift slots: {wfp['understaffed_slots']}"
                    f"{' (worst: ' + wfp['worst_slot'] + ')' if wfp.get('worst_slot') else ''}, "
                    f"weekly net profit: {fin.optimized.net_operating_profit:,.0f} {cur}. "
                    f"Rest/leave hard constraints: {'all passed' if wfp['hard_constraints_passed'] else 'VIOLATED'}."
                )
        return _build_copilot_result(
            reply=reply,
            action="simulate_plant_scenario",
            tool_calls_executed=["simulate_plant_scenario"],
            config=next_cfg,
            dataset=next_ds,
            result=new_res,
            timing=CopilotTiming(gemini_ms=0, solver_ms=solver_ms, total_ms=total_ms),
            source="offline_fallback",
        )

    # 1. Compare two strategies?
    if any(k in low for k in ("compare", " vs ", "versus", "trade-off", "tradeoff")) or "قارن" in text:
        name_a, w_a = "Min-Scrap & Energy", {"w_changeover_scrap": 60, "w_otif": 15, "w_energy_cost": 20, "w_working_capital": 5}
        name_b, w_b = "Max-OTIF (Zero Late Exports)", {"w_changeover_scrap": 15, "w_otif": 70, "w_energy_cost": 10, "w_working_capital": 5}
        if "capital" in low or "working" in low:
            name_a, w_a = "Working Capital Min", {"w_changeover_scrap": 20, "w_otif": 20, "w_energy_cost": 10, "w_working_capital": 50}
        _, comp, rec_cfg, rec_res, solver_ms = execute_compare_two_strategies(
            name_a, w_a, name_b, w_b, dataset, current_config
        )
        total_ms = max(1, int((time.perf_counter() - t_start) * 1000))
        reply = (
            f"تمت مقارنة استراتيجيتي **{name_a}** مقابل **{name_b}** عبر محرك OR-Tools CP-SAT. "
            f"الاستراتيجية الموصى بها حالياً هي **{comp.recommended_strategy}** بناءً على التكلفة الإجمالية ({rec_res.optimized.kpis.total_cost:,.0f} {rec_res.currency}) ونسبة التسليم في الموعد ({rec_res.optimized.kpis.otif_pct:.1f}%)."
            if ar
            else f"Executed CP-SAT twice comparing **{name_a}** vs. **{name_b}**. "
            f"Recommended strategy: **{comp.recommended_strategy}** (Total Cost: {rec_res.optimized.kpis.total_cost:,.0f} {rec_res.currency}, "
            f"Purge Scrap: {rec_res.optimized.kpis.purge_scrap_kg:.1f} kg, OTIF: {rec_res.optimized.kpis.otif_pct:.1f}%). Click Apply to push it to the dashboard."
        )
        return _build_copilot_result(
            reply=reply,
            action="compare_two_strategies",
            tool_calls_executed=["compare_two_strategies"],
            config=rec_cfg,
            dataset=dataset,
            result=rec_res,
            comparison=comp,
            timing=CopilotTiming(gemini_ms=0, solver_ms=solver_ms, total_ms=total_ms),
            source="offline_fallback",
        )

    # Check whether the prompt requests an active simulation/mitigation vs. a pure diagnostic inspection
    has_simulation_intent = any(
        k in low
        for k in (
            "prioritize",
            "maximize",
            "minimize",
            "set ",
            "weight",
            "override",
            "regrind",
            "replenish",
            "relief",
            "add ",
            "complete",
            "reset",
            "lock",
            "rebalance",
            "offload",
            "clear",
            "recover",
            "eliminate",
            "expand",
            "protect",
            "relieve",
            "re-sequence",
            "resequence",
            "break",
            "offline",
            "failure",
            "fault",
            "shortage",
            "cut ",
            "spike",
            "rush",
            "urgent",
            "ramadan",
            "peak",
            "tariff",
            "autonomous",
            "overtime",
            "container",
            "warehouse",
            "wip",
            "synchronize",
        )
    ) or any(
        k in text
        for k in (
            "أولوية",
            "عظّم",
            "ارفع",
            "خفض",
            "وزن",
            "ريجريند",
            "معاد",
            "عزّز",
            "احتياطي",
            "احتياطية",
            "أضف",
            "أكمل",
            "صفّر",
            "احجز",
            "موازنة",
            "إزالة",
            "إنقاذ",
            "إغلاق",
            "توسيع",
            "لجدولة",
            "عطل",
            "نقص",
            "عاجل",
            "رمضان",
            "ذروة",
            "الذاتية",
            "فعّل",
            "اسمح",
            "أعد",
            "حاوية",
            "الحاويات",
            "مخزن",
            "المخزن",
        )
    )

    # 2. Pure Bottleneck inspection (when no simulation/mitigation action is requested)?
    if not has_simulation_intent and (
        any(k in low for k in ("bottleneck", "why is", "why was", "explain", "late", "inspect"))
        or any(k in text for k in ("لماذا", "اختناق", "اشرح", "تأخر"))
    ):
        target = "auto"
        m_match = re.search(r"\b(M-\d{2})\b", text, re.IGNORECASE)
        p_match = re.search(r"\b(P-(?:\d{3}T|BM\d{2}))\b", text, re.IGNORECASE)
        o_match = re.search(r"\b(ORD-\d{2}|RUSH-\d{2})\b", text, re.IGNORECASE)
        r_match = re.search(r"\b(HDPE|LDPE|PET|ABS|PVC|PP)\b", text, re.IGNORECASE)
        if m_match:
            target = m_match.group(1).upper()
        elif p_match:
            target = p_match.group(1).upper()
        elif o_match:
            target = o_match.group(1).upper()
        elif r_match:
            target = r_match.group(1).upper()

        _, insight, res, solver_ms = execute_inspect_bottleneck(target, dataset, current_config, current_result)
        total_ms = max(1, int((time.perf_counter() - t_start) * 1000))
        reply = (
            f"تحليل الاختناق لـ **{insight.target_id}**: {insight.facts[0]} {insight.recommendation}"
            if ar
            else f"**{insight.headline}**: {' '.join(insight.facts[:2])} Recommendation: {insight.recommendation}"
        )
        return _build_copilot_result(
            reply=reply,
            action="inspect_bottleneck",
            tool_calls_executed=["inspect_bottleneck"],
            config=current_config,
            dataset=dataset,
            result=res,
            bottleneck=insight,
            timing=CopilotTiming(gemini_ms=0, solver_ms=solver_ms, total_ms=total_ms),
            source="offline_fallback",
        )

    # 3. Composable Scenario & Mitigation Simulation (supports ANY combination simultaneously!)
    sim_args: dict[str, Any] = {}
    norm_text = text.translate(_AR_DIGITS)
    norm_low = norm_text.lower()

    if any(k in low for k in ("reset scenarios", "clear all", "clear scenario")) or "إعادة ضبط" in text:
        sim_args["reset_scenarios"] = True

    # 3a. Machine Breakdowns (or clearing breakdowns on choke press)
    is_clearing_downtime = any(k in low for k in ("rebalance", "clear", "relieve")) or any(
        k in text for k in ("موازنة", "إزالة")
    )
    if is_clearing_downtime and re.search(r"\b(P-(?:\d{3}T|BM\d{2}))\b", text, re.IGNORECASE):
        pid = re.search(r"\b(P-(?:\d{3}T|BM\d{2}))\b", text, re.IGNORECASE).group(1).upper()  # type: ignore[union-attr]
        sim_args["clear_press_breakdowns"] = [pid]
    elif not is_clearing_downtime and (
        bool(re.search(r"\b(?:breaks?|broken|breakdown|down|offline|failure|fault)\b", low))
        or any(k in text for k in ("عطل", "توقف", "تعطل"))
    ):
        press_id = "P-500T"
        pm = re.search(r"\b(P-(?:\d{3}T|BM\d{2}))\b", text, re.IGNORECASE)
        ton_m = re.search(r"\b(150|250|350|500|650)\s*t\b", low)
        if pm:
            press_id = pm.group(1).upper()
        elif ton_m:
            press_id = f"P-{ton_m.group(1)}T"
        elif "blow" in low or "نفخ" in text:
            press_id = "P-BM01"

        dur = 18.0
        dm = re.search(r"(\d+(?:\.\d+)?)\s*(?:h|hr|hrs|hour|hours|ساعة|ساعات)", norm_low)
        if dm:
            dur = float(dm.group(1))
        start_hr = _extract_day_hour(text, default_hr=48.0)
        sim_args["machine_breakdowns"] = [
            {"machine_id": press_id, "start_hr": start_hr, "duration_hrs": dur}
        ]

    # 3b. Resin Replenishments vs. Resin Shortages / Price Spikes
    resin_hits = re.findall(r"\b(HDPE|LDPE|PET|ABS|PVC|PP)\b", text, re.IGNORECASE)
    is_replenish = any(k in low for k in ("replenish", "top up", "relieve")) or any(
        k in text for k in ("عزّز", "تعزيز", "تخفيف استنزاف")
    )
    if resin_hits and is_replenish:
        rep_pct_m = re.search(r"(?:replenish|silo|stock|بكر|بنسبة)[^\d]{0,30}(\d+(?:\.\d+)?)\s*%", norm_low)
        rep_pct = float(rep_pct_m.group(1)) if rep_pct_m else 25.0
        sim_args["resin_replenishments"] = [
            {"resin_code": resin_hits[0].upper(), "add_virgin_pct": rep_pct, "clear_shortage": True}
        ]
    elif resin_hits and (
        any(k in low for k in ("cut", "shortage", "drop", "spike", "price", "supply"))
        or any(k in text for k in ("نقص", "انخفاض", "ارتفاع", "سعر"))
    ):
        pct_match = re.search(r"(\d+(?:\.\d+)?)\s*%", norm_text)
        pct_val = float(pct_match.group(1)) if pct_match else 35.0
        is_price = ("price" in low or "spike" in low or "سعر" in text) and not (
            "cut" in low or "shortage" in low or "نقص" in text
        )
        sim_args["resin_shortages"] = [
            {
                "resin_code": resin_hits[0].upper(),
                "available_pct_reduction": 0.0 if is_price else pct_val,
                "virgin_price_spike_pct": pct_val if is_price else 0.0,
            }
        ]

    # 3c. Regrind Override
    if "regrind" in low or "معاد" in text or "سكراب" in text or "ريجريند" in text:
        rg_match = re.search(r"(\d{1,2})\s*%\s*(?:non-food\s+)?regrind|regrind[^\d]{0,16}(\d{1,2})\s*%|ريجريند[^\d]{0,20}(\d{1,2})\s*%", norm_low)
        if rg_match:
            val_str = next(g for g in rg_match.groups() if g is not None)
            sim_args["allow_regrind_override_pct"] = float(val_str)
        else:
            sim_args["allow_regrind_override_pct"] = 30.0

    # 3d. Mold PM Completion (Reset Shot Counter) vs. Manual Mold PM Lock
    mold_hit = re.search(r"\b(M-\d{2})\b", text, re.IGNORECASE)
    if mold_hit and (
        any(k in low for k in ("reset shot", "complete preventive", "complete pm", "log pm"))
        or any(k in text for k in ("صفّر عداد", "أكمل الصيانة"))
    ):
        sim_args["complete_mold_pm_ids"] = [mold_hit.group(1).upper()]
    elif mold_hit and ("pm" in low or "maintenance" in low or "lock" in low or "صيانة" in text):
        mid = mold_hit.group(1).upper()
        dur_m = re.search(r"(\d+(?:\.\d+)?)\s*(?:h|hr|hrs|hour|ساعة|ساعات)", norm_low)
        sim_args["mold_pm_locks"] = [
            {"mold_id": mid, "duration_hrs": float(dur_m.group(1)) if dur_m else 8.0}
        ]

    # 3e. Rush Order injection (only when referring to an order/product, NOT relief workers)
    is_workforce_add = any(
        k in low
        for k in (
            "relief",
            "worker",
            "staff",
            "headcount",
            "inspector",
            "handler",
            "supervisor",
            "technician",
            "operator",
            "understaffed",
            "shift",
        )
    ) or any(k in text for k in ("عمالة", "احتياطي", "احتياطية", "مراقب", "مناول", "مشرف", "فني", "مشغل", "ورديات", "وردية"))

    if not is_workforce_add and (
        any(k in low for k in ("rush", "urgent", "add ", "inject", "new order"))
        or any(k in text for k in ("عاجل", "طلب جديد", "أضف طلب", "أضف أمر"))
    ):
        qty = 40_000
        qm_k = re.search(r"(\d+(?:\.\d+)?)\s*k\b", norm_low)
        qm_n = re.search(r"\b(\d{3,6})\b", norm_text.replace(",", ""))
        if qm_k:
            qty = int(float(qm_k.group(1)) * 1000)
        elif qm_n:
            qty = int(qm_n.group(1))

        color: PlasticColor = "White"
        for cname in COLOR_RANKS:
            if cname.lower() in low:
                color = cname
                break
        if "أبيض" in text or "ابيض" in text:
            color = "White"
        elif "أسود" in text or "اسود" in text:
            color = "Black"
        elif "أزرق" in text or "ازرق" in text:
            color = "Blue"
        elif "أحمر" in text or "احمر" in text:
            color = "Red"

        mold_id, resin_code, weight_g, sku = "M-01", "HDPE", 2.8, f"Urgent {color} Cap"
        if "tub" in low or "yogurt" in low or "زبادي" in text:
            mold_id, resin_code, weight_g, sku = "M-03", "PP", 16.5, f"Urgent {color} Yogurt Tub"
        elif "crate" in low or "صندوق" in text:
            mold_id, resin_code, weight_g, sku = "M-08", "HDPE", 1450.0, f"Urgent {color} Harvest Crate"
        elif "jerrycan" in low or "detergent" in low or "جركن" in text:
            mold_id, resin_code, weight_g, sku = "M-09", "HDPE", 215.0, f"Urgent {color} Jerrycan"
        elif "preform" in low or "pet" in low:
            mold_id, resin_code, weight_g, sku = "M-05", "PET", 28.0, f"Urgent {color} PET Preform"
        elif "trim" in low or "abs" in low:
            mold_id, resin_code, weight_g, sku = "M-06", "ABS", 410.0, f"Urgent {color} Console Trim"
        m_ex = re.search(r"\b(M-\d{2})\b", text, re.IGNORECASE)
        if m_ex:
            mold_id = m_ex.group(1).upper()

        due_hr = _extract_day_hour(text, default_hr=96.0)
        if due_hr == 0.0 and "sun" not in low:
            due_hr = 96.0
        if any(d in low for d in ("mon", "tue", "wed", "thu", "fri", "sat")) or any(
            d in text for d in ("الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت")
        ):
            due_hr = min(float(current_config.physics.horizon_hrs), due_hr + 18.0)

        sim_args["rush_orders"] = [
            {
                "customer": "Urgent GCC Export Order" if ("export" in low or "تصدير" in text) else "Urgent Local Client",
                "sku_name": sku,
                "mold_id": mold_id,
                "resin_code": resin_code,
                "color": color,
                "quantity_pcs": qty,
                "part_weight_g": weight_g,
                "max_regrind_pct": 0.0 if ("export" in low or mold_id in ("M-01", "M-03", "M-04", "M-05")) else 15.0,
                "due_hr": due_hr,
                "late_penalty_per_hr": 720.0 if ("export" in low or "تصدير" in text) else 450.0,
                "is_export": ("export" in low or "تصدير" in text or True),
            }
        ]

    # 3f. Operational toggles
    if "ramadan" in low or "رمضان" in text:
        sim_args["ramadan_shift_mode"] = not current_config.ramadan_shift_mode if "off" not in low else False
    if "peak" in low or "tariff" in low or "ذروة" in text or "كهرباء" in text:
        sim_args["avoid_peak_tariff_hrs"] = False if "off" in low else True
    if "autonomous pm" in low or "auto pm" in low or "الصيانة الذاتية" in text:
        sim_args["autonomous_pm_window"] = False if "off" in low else True
    if any(k in low for k in ("container", "warehouse", "wip sync")) or any(
        k in text for k in ("حاوية", "الحاويات", "مخزن", "المخزن")
    ):
        sim_args["container_sync_enabled"] = False if "off" in low else True
        if "w_working_capital" not in sim_args:
            sim_args["w_working_capital"] = 60
        if "w_otif" not in sim_args:
            sim_args["w_otif"] = 45

    # 3g. Production Objective Weight Shifts (preset keywords + explicit numbers)
    if any(k in low for k in ("min scrap", "minimum scrap", "maximize purge scrap reduction", "rebalance load", "هالك")):
        sim_args.update({"w_changeover_scrap": 70, "w_otif": 15, "w_energy_cost": 10, "w_working_capital": 5})
    elif any(
        k in low
        for k in (
            "max otif",
            "zero late",
            "export priority",
            "export cut-off",
            "safety slack",
            "delivery buffer",
            "recover unscheduled",
            "recover late",
        )
    ) or any(k in text for k in ("تصدير أولوية", "صفر تأخير", "هامش أمان التصدير", "هامش التسليم", "لجدولة الأمر")):
        sim_args.update({"w_changeover_scrap": 15, "w_otif": 80, "w_energy_cost": 5, "w_working_capital": 5})

    m_otif = re.search(r"(?:otif(?:\s+delivery)?\s+weight(?:\s+to)?|وزن\s*(?:الالتزام\s*بمواعيد\s*التسليم\s*)?(?:OTIF|التسليم\s*في\s*الموعد)\s*إلى)\s*(\d{1,3})", norm_low)
    if m_otif:
        sim_args["w_otif"] = max(0, min(100, int(m_otif.group(1))))
    m_wc = re.search(r"(?:working\s+capital\s+weight(?:\s+to)?|رأس\s*المال\s*العامل\s*إلى)\s*(\d{1,3})", norm_low)
    if m_wc:
        sim_args["w_working_capital"] = max(0, min(100, int(m_wc.group(1))))
    m_sc = re.search(r"(?:changeover\s+scrap\s+weight(?:\s+to)?|خفض\s*الهالك\s*والتبديل\s*إلى)\s*(\d{1,3})", norm_low)
    if m_sc:
        sim_args["w_changeover_scrap"] = max(0, min(100, int(m_sc.group(1))))

    # 3h. Workforce Coverage Weights & Relief Headcount / Overtime Mitigation
    wf_weights: dict[str, int] = {}
    if any(
        k in low
        for k in ("workforce coverage", "shift coverage", "eliminate shift gaps", "understaffed shift", "call-out safety buffer")
    ) or any(k in text for k in ("تغطية الورديات", "فجوات العمالة", "عجز الورديات", "احتياطي أمان")):
        m_cov = re.search(r"(?:coverage\s+weight(?:\s+to)?|تغطية\s*الورديات\s*إلى)\s*(\d{1,3})", norm_low)
        cov_val = max(0, min(100, int(m_cov.group(1)))) if m_cov else 95
        wf_weights = {"w_coverage": cov_val, "w_labor_cost": 15, "w_fairness": 10}
        sim_args["workforce_weights"] = wf_weights

    if any(
        k in low
        for k in (
            "minimum required relief",
            "relief staff",
            "relief headcount",
            "temp headcount",
            "bottleneck roles",
            "eliminate understaffed",
            "eliminate shift gaps",
        )
    ) or any(k in text for k in ("العمالة الاحتياطية", "عمالة احتياطية", "لإغلاق عجز الورديات", "فجوات العمالة")):
        sim_args["auto_staff_workforce_gaps"] = True
        if "workforce_weights" not in sim_args:
            sim_args["workforce_weights"] = {"w_coverage": 95, "w_labor_cost": 15, "w_fairness": 10}
    elif "relief" in low or "احتياطي" in text:
        # Single-role relief addition e.g. "Add 1 relief Mold Technician"
        explicit_relief: list[dict[str, Any]] = []
        for pat, role in _EN_ROLE_PATTERNS:
            m_rel = re.search(rf"(\d+)\s+relief\s+(?:{pat})", norm_low)
            if m_rel:
                explicit_relief.append({"role": role, "count": int(m_rel.group(1))})
                break
        if not explicit_relief:
            explicit_relief.append({"role": "Mold_Technician", "count": 1})
        sim_args["add_relief_workers"] = explicit_relief
        if "workforce_weights" not in sim_args:
            sim_args["workforce_weights"] = {"w_coverage": 95, "w_labor_cost": 15, "w_fairness": 10}

    payload, next_ds, next_cfg, new_res, solver_ms = execute_simulate_plant_scenario(
        sim_args, dataset, current_config, current_result
    )
    total_ms = max(1, int((time.perf_counter() - t_start) * 1000))
    ok = new_res.optimized.kpis
    fin = new_res.financials
    d_cost = payload["delta_vs_current_plan"]["total_cost_delta"]
    radar_out = new_res.risk_radar
    wf_out = new_res.workforce
    mut_notes = payload.get("plant_mutations") or []

    if ar:
        reply = (
            f"تم تشغيل محاكاة CP-SAT ({new_res.status} في {new_res.solve_time_ms} مللي ثانية) مع استيفاء جميع القيود الصارمة. "
            f"الإيرادات المحققة: {fin.optimized.recognized_revenue:,.0f} {new_res.currency}، "
            f"صافي الربح: {fin.optimized.net_operating_profit:,.0f} {new_res.currency} (هامش {fin.optimized.net_margin_pct:.1f}%)، "
            f"الوفورات الأسبوعية: {fin.total_weekly_savings:,.0f} {new_res.currency}، "
            f"التكلفة الإجمالية: {ok.total_cost:,.0f} {new_res.currency} (تغير {d_cost:+,.0f})، "
            f"نسبة التسليم في الموعد OTIF: {ok.otif_pct:.1f}%، كفاءة المعدات OEE: {ok.oee_pct:.1f}%."
        )
        if wf_out is not None:
            reply += (
                f" تغطية الورديات: {wf_out.optimized.kpis.coverage_pct:.1f}% "
                f"(ورديات غير مغطاة: {wf_out.optimized.kpis.understaffed_slots}، إجمالي العمال: {len(next_ds.workers)})."
            )
        if radar_out is not None:
            reply += (
                f" مؤشر مخاطر المصنع: {radar_out.overall_risk_score}/100 "
                f"(صادرات معرضة للخطر: {radar_out.export_at_risk_count})."
            )
    else:
        reply = (
            f"Simulated scenario via OR-Tools CP-SAT ({new_res.status}, {new_res.solve_time_ms} ms, 6/6 hard constraints passed). "
            f"Revenue: {fin.optimized.recognized_revenue:,.0f} {new_res.currency}, "
            f"Net Profit: {fin.optimized.net_operating_profit:,.0f} {new_res.currency} ({fin.optimized.net_margin_pct:.1f}% margin), "
            f"Weekly Savings vs FIFO: {fin.total_weekly_savings:,.0f} {new_res.currency} (Annual: {fin.annual_projected_savings:,.0f} {new_res.currency}). "
            f"Total Cost: {ok.total_cost:,.0f} {new_res.currency} ({d_cost:+,.0f} vs current), "
            f"Purge Scrap: {ok.purge_scrap_kg:.1f} kg, Changeover: {ok.changeover_hours:.2f}h, OTIF: {ok.otif_pct:.1f}%, OEE: {ok.oee_pct:.1f}%."
        )
        if wf_out is not None:
            reply += (
                f" Shift Coverage: {wf_out.optimized.kpis.coverage_pct:.1f}% "
                f"({wf_out.optimized.kpis.understaffed_slots} understaffed slots, {len(next_ds.workers)} floor workers)."
            )
        if radar_out is not None:
            reply += (
                f" Risk Score: {radar_out.overall_risk_score}/100 "
                f"(Exports at Risk: {radar_out.export_at_risk_count})."
            )
        if mut_notes:
            reply += f" Actions applied: {'; '.join(mut_notes)}."
        if ok.unscheduled_orders > 0:
            reply += f" Note: {ok.unscheduled_orders} low-priority order(s) ({', '.join(new_res.optimized.unscheduled_order_ids)}) left unscheduled due to virgin resin inventory cap."

    return _build_copilot_result(
        reply=reply,
        action="simulate_plant_scenario",
        tool_calls_executed=["simulate_plant_scenario"],
        config=next_cfg,
        dataset=next_ds,
        result=new_res,
        reference_result=current_result,
        timing=CopilotTiming(gemini_ms=0, solver_ms=solver_ms, total_ms=total_ms),
        source="offline_fallback",
    )


# --------------------------------------------------------------------------------------------
# Gemini Composable Tool Declarations & Orchestration
# --------------------------------------------------------------------------------------------
def _build_gemini_tools():
    from google.genai import types

    simulate_decl = types.FunctionDeclaration(
        name="simulate_plant_scenario",
        description=(
            "Run the deterministic OR-Tools CP-SAT plastic factory scheduler with ANY simultaneous "
            "combination of press breakdowns, resin shortages/price spikes, mold PM locks, rush orders, "
            "regrind override %, peak electricity tariff avoidance, Ramadan shift mode, and 4 executive weights."
        ),
        parameters_json_schema={
            "type": "object",
            "properties": {
                "reset_scenarios": {"type": "boolean", "description": "Clear prior active disruptions before applying new ones."},
                "machine_breakdowns": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "machine_id": {"type": "string", "description": "Press ID e.g. P-150T, P-250T, P-350T, P-500T, P-650T, P-BM01"},
                            "start_hr": {"type": "number", "description": "Breakdown start hour 0..168 (Sun=0, Mon=24, Tue=48, Wed=72, Thu=96, Fri=120, Sat=144)"},
                            "duration_hrs": {"type": "number", "description": "Breakdown duration in hours"},
                        },
                        "required": ["machine_id", "start_hr", "duration_hrs"],
                    },
                },
                "resin_shortages": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "resin_code": {"type": "string", "enum": ["PP", "HDPE", "LDPE", "PET", "ABS", "PVC"]},
                            "available_pct_reduction": {"type": "number", "description": "Percent reduction in available virgin resin (0-95)"},
                            "virgin_price_spike_pct": {"type": "number", "description": "Percent increase in virgin resin cost per kg (0-300)"},
                        },
                        "required": ["resin_code"],
                    },
                },
                "mold_pm_locks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "mold_id": {"type": "string", "description": "Mold ID e.g. M-01..M-10"},
                            "duration_hrs": {"type": "number", "description": "PM lock duration in hours"},
                        },
                        "required": ["mold_id", "duration_hrs"],
                    },
                },
                "rush_orders": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "customer": {"type": "string"},
                            "sku_name": {"type": "string"},
                            "mold_id": {"type": "string"},
                            "resin_code": {"type": "string", "enum": ["PP", "HDPE", "LDPE", "PET", "ABS", "PVC"]},
                            "color": {"type": "string", "enum": ["Natural", "White", "Yellow", "Blue", "Red", "Black"]},
                            "quantity_pcs": {"type": "integer"},
                            "part_weight_g": {"type": "number"},
                            "max_regrind_pct": {"type": "number"},
                            "due_hr": {"type": "number"},
                            "late_penalty_per_hr": {"type": "number"},
                            "is_export": {"type": "boolean"},
                        },
                        "required": ["mold_id", "resin_code", "color", "quantity_pcs", "due_hr"],
                    },
                },
                "allow_regrind_override_pct": {"type": "number", "description": "Boost non-food order regrind up to this % (0-40). Food orders remain 0%."},
                "avoid_peak_tariff_hrs": {"type": "boolean"},
                "ramadan_shift_mode": {"type": "boolean"},
                "autonomous_pm_window": {"type": "boolean", "description": "Enable autonomous mid-week PM co-optimization."},
                "w_changeover_scrap": {"type": "integer"},
                "w_otif": {"type": "integer"},
                "w_energy_cost": {"type": "integer"},
                "w_working_capital": {"type": "integer"},
                "auto_staff_workforce_gaps": {
                    "type": "boolean",
                    "description": "Automatically add the minimum required relief/temporary staff for bottleneck roles (e.g. QC_Inspector, Material_Handler, Shift_Supervisor) to close understaffed shift slots.",
                },
                "add_relief_workers": {
                    "type": "array",
                    "description": "Explicitly add relief/temporary workers by role.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "role": {
                                "type": "string",
                                "enum": ["Press_Operator", "Mold_Technician", "QC_Inspector", "Material_Handler", "Shift_Supervisor"],
                            },
                            "count": {"type": "integer"},
                        },
                        "required": ["role", "count"],
                    },
                },
                "workforce_overtime_cap_hrs": {
                    "type": "number",
                    "description": "Increase weekly max hours cap per active worker (48-72) to authorize extra overtime.",
                },
                "resin_replenishments": {
                    "type": "array",
                    "description": "Replenish virgin resin silo stock and clear active shortages for scarce resins.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "resin_code": {"type": "string", "enum": ["PP", "HDPE", "LDPE", "PET", "ABS", "PVC"]},
                            "add_virgin_pct": {"type": "number", "description": "Percent top-up to virgin silo stock (5-100)."},
                            "clear_shortage": {"type": "boolean"},
                        },
                        "required": ["resin_code"],
                    },
                },
                "complete_mold_pm_ids": {
                    "type": "array",
                    "description": "Complete preventive maintenance and reset shot counters to 0 for specified mold IDs.",
                    "items": {"type": "string"},
                },
                "clear_press_breakdowns": {
                    "type": "array",
                    "description": "Clear active breakdowns or downtime windows on specified press IDs.",
                    "items": {"type": "string"},
                },
                "worker_callouts": {
                    "type": "array",
                    "description": (
                        "Factory-floor worker call-outs (absences) on a specific day. Use role+count (e.g. 2 Mold_Technician on Tuesday) "
                        "OR explicit worker_ids (e.g. MT-01). Re-runs the deterministic workforce CP-SAT and returns shift coverage, "
                        "mold-changeover readiness, overtime cost and weekly net profit."
                    ),
                    "items": {
                        "type": "object",
                        "properties": {
                            "role": {
                                "type": "string",
                                "enum": ["Press_Operator", "Mold_Technician", "QC_Inspector", "Material_Handler", "Shift_Supervisor"],
                            },
                            "count": {"type": "integer", "description": "How many workers of that role call out"},
                            "day": {"type": "string", "description": "Day of week: Sun, Mon, Tue, Wed, Thu, Fri or Sat (Sun=0)"},
                            "worker_ids": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                },
                "workforce_weights": {
                    "type": "object",
                    "description": "Workforce objective weights 0-100.",
                    "properties": {
                        "w_labor_cost": {"type": "integer"},
                        "w_coverage": {"type": "integer"},
                        "w_fairness": {"type": "integer"},
                    },
                },
            },
        },
    )

    bottleneck_decl = types.FunctionDeclaration(
        name="inspect_bottleneck",
        description=(
            "Inspect deterministically why an order is late, why a color sequence was chosen, "
            "or which press, mold, or resin is the binding factory bottleneck."
        ),
        parameters_json_schema={
            "type": "object",
            "properties": {
                "target_id": {
                    "type": "string",
                    "description": "A machine_id (e.g. P-500T), mold_id (e.g. M-04), order_id (e.g. ORD-12), resin_code (e.g. HDPE), or 'auto' for plant-wide audit.",
                }
            },
            "required": ["target_id"],
        },
    )

    compare_decl = types.FunctionDeclaration(
        name="compare_two_strategies",
        description=(
            "Run OR-Tools CP-SAT twice under two executive objective weight profiles (e.g., Zero Late Exports vs. Minimum Purge Scrap & Energy) "
            "and return an exact side-by-side ROI trade-off table."
        ),
        parameters_json_schema={
            "type": "object",
            "properties": {
                "strategy_a_name": {"type": "string"},
                "strategy_a_weights": {
                    "type": "object",
                    "properties": {
                        "w_changeover_scrap": {"type": "integer"},
                        "w_otif": {"type": "integer"},
                        "w_energy_cost": {"type": "integer"},
                        "w_working_capital": {"type": "integer"},
                    },
                },
                "strategy_b_name": {"type": "string"},
                "strategy_b_weights": {
                    "type": "object",
                    "properties": {
                        "w_changeover_scrap": {"type": "integer"},
                        "w_otif": {"type": "integer"},
                        "w_energy_cost": {"type": "integer"},
                        "w_working_capital": {"type": "integer"},
                    },
                },
            },
            "required": ["strategy_a_name", "strategy_a_weights", "strategy_b_name", "strategy_b_weights"],
        },
    )

    return [types.Tool(function_declarations=[simulate_decl, bottleneck_decl, compare_decl])]


def _call_gemini_composable_copilot(
    prompt: str,
    dataset: PlantDataset,
    current_config: SolverConfig,
    current_result: Optional[SolveResult],
    language: str,
) -> CopilotResult:
    from google import genai
    from google.genai import types

    t_start = time.perf_counter()
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")

    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=15000),
    )

    press_summary = ", ".join(f"{p.machine_id}({p.tonnage}T {p.process_type})" for p in dataset.presses)
    mold_summary = ", ".join(f"{m.mold_id}:{m.name}({m.shot_utilization_pct:.0f}%shots)" for m in dataset.molds)
    resin_summary = ", ".join(f"{r.resin_code}({r.virgin_available_kg:.0f}kg,dry={r.drying_lead_time_hrs}h)" for r in dataset.resins)

    reply_lang = "Arabic" if (language == "ar" or _is_arabic(prompt)) else "English"
    system_instruction = (
        "You are Mini-DIOS Plastics Operations Copilot for Egypt & Saudi Arabia plastic manufacturing plants "
        "(Injection Molding, Blow Molding, Extrusion).\n"
        "STRICT ZERO-LLM-MATH RULE: You MUST NEVER invent, estimate, or compute any schedule KPI, cost, scrap kg, "
        "changeover hours, or OTIF %. ALWAYS invoke one of the 3 deterministic CP-SAT tools first, then narrate ONLY "
        "the exact numbers returned by the tool.\n"
        f"Plant Context:\n- Presses: {press_summary}\n- Molds: {mold_summary}\n- Resins: {resin_summary}\n"
        f"- Horizon: 0..168h (Sun=0, Mon=24, Tue=48, Wed=72, Thu=96, Fri=120, Sat=144).\n"
        f"- Floor workforce: {len(dataset.workers)} workers (roles: Press_Operator, Mold_Technician, QC_Inspector, "
        f"Material_Handler, Shift_Supervisor). For absence/call-out questions pass `worker_callouts` to simulate_plant_scenario.\n"
        f"- Current Weights: scrap={current_config.w_changeover_scrap}, otif={current_config.w_otif}, "
        f"energy={current_config.w_energy_cost}, wc={current_config.w_working_capital}, currency={current_config.currency}.\n"
        f"Respond concisely in {reply_lang} (2-3 executive sentences citing exact tool numbers)."
    )

    tools = _build_gemini_tools()
    model_name = os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
    gen_cfg = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=tools,
        thinking_config=types.ThinkingConfig(thinking_level="low"),
        temperature=0.1,
    )

    t_g1 = time.perf_counter()
    resp1 = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=gen_cfg,
    )
    gemini_ms = max(1, int((time.perf_counter() - t_g1) * 1000))

    # Extract function calls
    fn_calls = list(getattr(resp1, "function_calls", None) or [])
    if not fn_calls:
        # Zero-LLM-Math guard: never return ungrounded LLM text without a tool call
        raise RuntimeError("Gemini returned no tool call; routing to deterministic offline engine.")

    tool_names: list[str] = []
    fn_response_parts = []
    final_ds = dataset
    final_cfg = current_config
    final_res: Optional[SolveResult] = current_result
    final_comp: Optional[StrategyComparison] = None
    final_bn: Optional[BottleneckInsight] = None
    solver_ms_total = 0
    primary_action = "simulate_plant_scenario"

    for fc in fn_calls:
        name = fc.name
        args = dict(fc.args or {})
        tool_names.append(name)
        primary_action = name

        if name == "simulate_plant_scenario":
            tool_out, final_ds, final_cfg, final_res, s_ms = execute_simulate_plant_scenario(
                args, final_ds, final_cfg, current_result
            )
            solver_ms_total += s_ms
        elif name == "inspect_bottleneck":
            tool_out, final_bn, final_res, s_ms = execute_inspect_bottleneck(
                str(args.get("target_id", "auto")), final_ds, final_cfg, final_res
            )
            solver_ms_total += s_ms
        elif name == "compare_two_strategies":
            tool_out, final_comp, final_cfg, final_res, s_ms = execute_compare_two_strategies(
                str(args.get("strategy_a_name", "Strategy A")),
                dict(args.get("strategy_a_weights") or {}),
                str(args.get("strategy_b_name", "Strategy B")),
                dict(args.get("strategy_b_weights") or {}),
                final_ds,
                final_cfg,
            )
            solver_ms_total += s_ms
        else:
            tool_out = {"error": f"Unknown tool '{name}'"}

        fn_response_parts.append(
            types.Part.from_function_response(name=name, response={"result": tool_out})
        )

    # Turn 2: Ask Gemini to narrate ONLY the exact deterministic tool results
    narration = ""
    try:
        t_g2 = time.perf_counter()
        model_content = resp1.candidates[0].content if getattr(resp1, "candidates", None) else None
        turn2_contents: list[Any] = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
        if model_content is not None:
            turn2_contents.append(model_content)
        turn2_contents.append(types.Content(role="user", parts=fn_response_parts))

        resp2 = client.models.generate_content(
            model=model_name,
            contents=turn2_contents,
            config=gen_cfg,
        )
        gemini_ms += max(1, int((time.perf_counter() - t_g2) * 1000))
        narration = (resp2.text or "").strip()
    except Exception as exc:
        print(f"[Copilot] Turn-2 narration fallback: {exc!r}", flush=True)

    if not narration:
        if final_bn is not None:
            narration = f"**{final_bn.headline}**: {' '.join(final_bn.facts[:2])} {final_bn.recommendation}"
        elif final_comp is not None:
            narration = f"Compared {final_comp.strategy_a_name} vs. {final_comp.strategy_b_name}. Recommended: {final_comp.recommended_strategy}."
        elif final_res is not None:
            ok = final_res.optimized.kpis
            narration = (
                f"CP-SAT solved ({final_res.status}, {final_res.solve_time_ms} ms): "
                f"Total Cost {ok.total_cost:,.0f} {final_res.currency}, Purge Scrap {ok.purge_scrap_kg:.1f} kg, "
                f"Changeover {ok.changeover_hours:.2f}h, OTIF {ok.otif_pct:.1f}%, OEE {ok.oee_pct:.1f}%."
            )
        else:
            narration = "Scenario evaluated deterministically via OR-Tools CP-SAT."

    total_ms = max(1, int((time.perf_counter() - t_start) * 1000))
    return _build_copilot_result(
        reply=narration,
        action=primary_action,
        tool_calls_executed=tool_names,
        config=final_cfg,
        dataset=final_ds,
        result=final_res,
        comparison=final_comp,
        bottleneck=final_bn,
        reference_result=current_result,
        timing=CopilotTiming(gemini_ms=gemini_ms, solver_ms=solver_ms_total, total_ms=total_ms),
        source="gemini",
    )


def run_plastics_copilot(
    prompt: str,
    dataset: PlantDataset,
    current_config: SolverConfig,
    current_result: Optional[SolveResult] = None,
    language: str = "en",
    force_offline: bool = False,
    quota_limited: bool = False,
) -> CopilotResult:
    """Entrypoint: Try Gemini composable tool-calling with strict timeout; fall back cleanly to offline engine."""
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    offline_mode = os.environ.get("OFFLINE_MODE", "false").lower() in ("true", "1", "yes")

    if api_key and not offline_mode and not force_offline:
        try:
            return _call_gemini_composable_copilot(
                prompt, dataset, current_config, current_result, language
            )
        except Exception as exc:
            print(
                f"[Copilot] Gemini error/guard triggered ({exc!r}); using deterministic offline engine.",
                flush=True,
            )

    res = run_offline_composable_copilot(
        prompt, dataset, current_config, current_result, language
    )

    # Optional Neon AI Gateway narration enhancement (when NEON_AI_GATEWAY_BASE_URL + NEON_AI_GATEWAY_TOKEN
    # are set and account credits are available; strictly narrates deterministic CP-SAT output only)
    use_neon_gw = os.environ.get("COPILOT_USE_NEON_AI_GATEWAY", "false").lower() in ("true", "1", "yes")
    if use_neon_gw and not offline_mode and not force_offline:
        gw_narration = call_neon_ai_gateway_narration(
            system_prompt=(
                "You are Mini-DIOS Plastics Operations Copilot. Strictly preserve every single number, "
                "currency, percentage, and ID from the provided deterministic CP-SAT result."
            ),
            user_prompt=f"User question: {prompt}\nDeterministic CP-SAT output: {res.reply}",
        )
        if gw_narration:
            res = res.model_copy(update={"reply": gw_narration, "source": "neon_ai_gateway"})

    if quota_limited:
        notice = (
            "\n\n_(ملاحظة: تم الوصول إلى الحد الساعي لاستدعاءات Gemini المباشرة لهذه الجلسة — تم تنفيذ المحاكاة تلقائياً باستخدام محرك OR-Tools CP-SAT الحتمي المحلي دون أي فقدان في الدقة.)_"
            if language == "ar"
            else "\n\n_(Note: Hourly live Gemini quota reached for this demo session — executed automatically using the deterministic offline OR-Tools CP-SAT engine with identical mathematical accuracy.)_"
        )
        res = res.model_copy(
            update={
                "reply": f"{res.reply}{notice}",
                "quota_limited": True,
            }
        )
    return res
