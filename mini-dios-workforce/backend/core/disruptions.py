"""Composable Scenario Engine for Mini-DIOS Plastics.

Transforms a base `PlantDataset` + `SolverConfig.scenarios` into an effective dataset,
mold PM schedule map, and structured `AppliedScenario` audit log without mutating caller state.
"""
from __future__ import annotations

from dataclasses import dataclass

from .ontology import (
    AppliedScenario,
    DowntimeWindow,
    PlantDataset,
    ProductionOrder,
    SolverConfig,
    order_shots,
)


@dataclass
class EffectivePlantState:
    dataset: PlantDataset
    mold_pm_durations_hrs: dict[str, float]
    mold_pm_reasons: dict[str, str]
    applied_scenarios: list[AppliedScenario]


def apply_plant_scenarios(dataset: PlantDataset, config: SolverConfig) -> EffectivePlantState:
    """Apply ANY simultaneous combination of breakdowns, resin shortages, mold PM locks,
    rush orders, regrind override, peak tariff avoidance, and Ramadan shift mode."""
    eff = dataset.model_copy(deep=True)
    applied: list[AppliedScenario] = []
    sc = config.scenarios

    presses_by_id = {p.machine_id: p for p in eff.presses}
    molds_by_id = {m.mold_id: m for m in eff.molds}
    resins_by_code = {r.resin_code: r for r in eff.resins}

    # 1. Machine Breakdowns -> appended as blocked downtime windows on target presses
    for bd in sc.machine_breakdowns:
        press = presses_by_id.get(bd.machine_id)
        if press is None:
            continue
        end_hr = bd.start_hr + bd.duration_hrs
        press.downtime_windows.append(
            DowntimeWindow(
                start_hr=bd.start_hr,
                end_hr=end_hr,
                reason=f"Breakdown ({bd.duration_hrs:.0f}h)",
            )
        )
        applied.append(
            AppliedScenario(
                type="machine_breakdown",
                description=(
                    f"Press {press.machine_id} ({press.name}) breakdown from "
                    f"H{bd.start_hr:.0f} to H{end_hr:.0f} ({bd.duration_hrs:.0f}h offline)."
                ),
                affected_ids=[press.machine_id],
            )
        )

    # 2. Resin Shortages & Virgin Price Spikes
    for rs in sc.resin_shortages:
        resin = resins_by_code.get(rs.resin_code)
        if resin is None:
            continue
        orig_kg = resin.virgin_available_kg
        orig_price = resin.virgin_cost_per_kg
        if rs.available_pct_reduction > 0:
            resin.virgin_available_kg = round(orig_kg * max(0.0, 1.0 - rs.available_pct_reduction / 100.0), 1)
        if rs.virgin_price_spike_pct > 0:
            resin.virgin_cost_per_kg = round(orig_price * (1.0 + rs.virgin_price_spike_pct / 100.0), 3)
        parts: list[str] = []
        if rs.available_pct_reduction > 0:
            parts.append(
                f"virgin stock -{rs.available_pct_reduction:.0f}% ({orig_kg:,.0f} -> {resin.virgin_available_kg:,.0f} kg)"
            )
        if rs.virgin_price_spike_pct > 0:
            parts.append(
                f"virgin price +{rs.virgin_price_spike_pct:.0f}% ({orig_price:.2f} -> {resin.virgin_cost_per_kg:.2f} SAR/kg)"
            )
        applied.append(
            AppliedScenario(
                type="resin_shortage",
                description=f"Resin {rs.resin_code} shock: {', '.join(parts) or 'no change'}.",
                affected_ids=[rs.resin_code],
            )
        )

    # 3. Mold PM Locks (merged with automatic >=95% shot-count threshold & mid-week shot-limit enforcement)
    mold_pm_durations: dict[str, float] = {}
    mold_pm_reasons: dict[str, str] = {}
    weekly_shots_by_mold: dict[str, int] = {}
    for o in eff.orders:
        m = molds_by_id.get(o.mold_id)
        if m is not None:
            weekly_shots_by_mold[o.mold_id] = weekly_shots_by_mold.get(o.mold_id, 0) + order_shots(o, m)

    for m in eff.molds:
        projected_shots = m.current_shots + weekly_shots_by_mold.get(m.mold_id, 0)
        if m.shot_utilization_pct >= 95.0:
            mold_pm_durations[m.mold_id] = m.pm_duration_hrs
            mold_pm_reasons[m.mold_id] = "shot_threshold_95pct"
            pm_verb = (
                "autonomous CP-SAT window before shot limit"
                if config.autonomous_pm_window
                else "mandatory PM before production"
            )
            applied.append(
                AppliedScenario(
                    type="auto_mold_pm",
                    description=(
                        f"Auto HC6 PM block on Mold {m.mold_id} ({m.shot_utilization_pct:.1f}% shot life): "
                        f"{m.pm_duration_hrs:.0f}h {pm_verb}."
                    ),
                    affected_ids=[m.mold_id],
                )
            )
        elif config.autonomous_pm_window and m.pm_duration_hrs > 0 and projected_shots > m.maintenance_interval_shots:
            mold_pm_durations[m.mold_id] = m.pm_duration_hrs
            mold_pm_reasons[m.mold_id] = "midweek_shot_limit"
            applied.append(
                AppliedScenario(
                    type="auto_mold_pm",
                    description=(
                        f"Autonomous HC6 PM on Mold {m.mold_id}: projected {projected_shots:,} shots exceed "
                        f"{m.maintenance_interval_shots:,} limit — {m.pm_duration_hrs:.0f}h PM co-optimized mid-week."
                    ),
                    affected_ids=[m.mold_id],
                )
            )

    for lk in sc.mold_pm_locks:
        mold = molds_by_id.get(lk.mold_id)
        if mold is None:
            continue
        mold_pm_durations[lk.mold_id] = max(mold_pm_durations.get(lk.mold_id, 0.0), lk.duration_hrs)
        mold_pm_reasons.setdefault(lk.mold_id, "manual_lock")
        applied.append(
            AppliedScenario(
                type="mold_pm_lock",
                description=f"Manual PM Lock on Mold {lk.mold_id} ({mold.name}): {lk.duration_hrs:.0f}h locked.",
                affected_ids=[lk.mold_id],
            )
        )

    # 4. Injected Rush Orders
    existing_ids = {o.order_id for o in eff.orders}
    for idx, ro in enumerate(sc.rush_orders, start=1):
        rush_copy = ro.model_copy(deep=True)
        if rush_copy.order_id in existing_ids:
            rush_copy.order_id = f"{rush_copy.order_id}-R{idx}"
        existing_ids.add(rush_copy.order_id)
        eff.orders.append(rush_copy)
        applied.append(
            AppliedScenario(
                type="rush_order",
                description=(
                    f"Rush Order {rush_copy.order_id}: {rush_copy.quantity_pcs:,} pcs {rush_copy.color} "
                    f"{rush_copy.sku_name} ({rush_copy.mold_id}/{rush_copy.resin_code}) due H{rush_copy.due_hr:.0f}."
                ),
                affected_ids=[rush_copy.order_id, rush_copy.mold_id],
            )
        )

    # 5. Global Non-Food Regrind Override
    if sc.allow_regrind_override_pct is not None and sc.allow_regrind_override_pct > 0:
        affected_orders: list[str] = []
        for o in eff.orders:
            if o.max_regrind_pct > 0:
                new_pct = min(40.0, max(o.max_regrind_pct, float(sc.allow_regrind_override_pct)))
                if new_pct > o.max_regrind_pct:
                    o.max_regrind_pct = new_pct
                    affected_orders.append(o.order_id)
        applied.append(
            AppliedScenario(
                type="regrind_override",
                description=(
                    f"Non-food regrind override enabled up to {sc.allow_regrind_override_pct:.0f}% "
                    f"({len(affected_orders)} industrial orders boosted; food/pharma kept at 0%)."
                ),
                affected_ids=affected_orders,
            )
        )

    # 6. Operational Modes (Peak Tariff & Ramadan Shift Mode)
    ph = config.physics
    if config.avoid_peak_tariff_hrs:
        surcharge_pct = round(max(0.0, ph.peak_tariff_multiplier - 1.0) * 100.0)
        applied.append(
            AppliedScenario(
                type="peak_tariff_avoidance",
                description=(
                    f"Peak Electricity Tariff Avoidance ON "
                    f"({ph.peak_start_hr:02d}:00-{ph.peak_end_hr:02d}:00 daily +{surcharge_pct}% kWh surcharge)."
                ),
                affected_ids=[],
            )
        )
    if config.ramadan_shift_mode:
        labor_pct = round(max(0.0, (8.0 - float(ph.ramadan_shift_hours)) * 0.075) * 100.0)
        applied.append(
            AppliedScenario(
                type="ramadan_shift_mode",
                description=(
                    f"Ramadan Shift Mode ON ({ph.ramadan_shift_hours}h shift, "
                    f"18:00-20:00 daily Iftar changeover blackout, +{labor_pct}% shift labor)."
                ),
                affected_ids=[],
            )
        )

    if config.autonomous_pm_window:
        applied.append(
            AppliedScenario(
                type="autonomous_pm_window",
                description="Autonomous Preventive Maintenance Co-Optimization enabled: CP-SAT schedules mold PM in the lowest-cost non-overlapping window before shot limits.",
                affected_ids=sorted(mold_pm_durations.keys()),
            )
        )

    return EffectivePlantState(
        dataset=eff,
        mold_pm_durations_hrs=mold_pm_durations,
        mold_pm_reasons=mold_pm_reasons,
        applied_scenarios=applied,
    )
