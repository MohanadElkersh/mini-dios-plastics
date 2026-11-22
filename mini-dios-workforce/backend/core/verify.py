"""Independent Post-Solve Hard Constraint Verifier (HC1-HC6) for Mini-DIOS Plastics."""
from __future__ import annotations

from collections import defaultdict

from .ontology import (
    ConstraintCheck,
    PlantDataset,
    SchedulePlan,
    SolverConfig,
    compatible_active_presses,
    order_shots,
    transition_penalty,
)


def verify_hard_constraints(
    dataset: PlantDataset,
    config: SolverConfig,
    plan: SchedulePlan,
    mold_pm_durations_hrs: dict[str, float],
) -> list[ConstraintCheck]:
    """Deterministically verify all 6 Industrial Plastics Hard Constraints with zero tolerance."""
    presses_by_id = {p.machine_id: p for p in dataset.presses}
    molds_by_id = {m.mold_id: m for m in dataset.molds}
    resins_by_code = {r.resin_code: r for r in dataset.resins}
    orders_by_id = {o.order_id: o for o in dataset.orders}

    scheduled = [j for j in plan.jobs if j.scheduled]

    # ------------------------------------------------------------------
    # HC1: Mold-Press Compatibility, Active Status & Hot-Runner Fit
    # ------------------------------------------------------------------
    hc1_v: list[str] = []
    for j in scheduled:
        mold = molds_by_id[j.mold_id]
        compat_ids = {p.machine_id for p in compatible_active_presses(mold, presses_by_id)}
        if j.machine_id not in compat_ids:
            hc1_v.append(f"{j.order_id}: press {j.machine_id} incompatible or inactive for mold {j.mold_id}")

    # ------------------------------------------------------------------
    # HC2: No Press Overlap & Zero Work/Purge During Downtime/Breakdowns
    # ------------------------------------------------------------------
    hc2_v: list[str] = []
    by_press: dict[str, list] = defaultdict(list)
    for j in scheduled:
        by_press[j.machine_id].append(j)

    for mid, jobs in by_press.items():
        jobs.sort(key=lambda x: (x.start_min, x.end_min))
        press = presses_by_id[mid]
        for idx in range(1, len(jobs)):
            prev_j, cur_j = jobs[idx - 1], jobs[idx]
            if cur_j.setup_start_min < prev_j.end_min:
                hc2_v.append(
                    f"Press {mid}: {cur_j.order_id} busy start {cur_j.setup_start_min}m < {prev_j.order_id} end {prev_j.end_min}m"
                )
        for j in jobs:
            for dw in press.downtime_windows:
                ds, de = int(round(dw.start_hr * 60)), int(round(dw.end_hr * 60))
                if min(j.end_min, de) > max(j.setup_start_min, ds):
                    hc2_v.append(
                        f"Press {mid}: {j.order_id} [{j.setup_start_min}..{j.end_min}m] overlaps downtime [{ds}..{de}m] ({dw.reason})"
                    )

    # ------------------------------------------------------------------
    # HC3: Physical Mold Exclusivity Across Presses
    # ------------------------------------------------------------------
    hc3_v: list[str] = []
    by_mold: dict[str, list] = defaultdict(list)
    for j in scheduled:
        by_mold[j.mold_id].append(j)

    for mold_id, jobs in by_mold.items():
        jobs.sort(key=lambda x: (x.start_min, x.end_min))
        for idx in range(1, len(jobs)):
            prev_j, cur_j = jobs[idx - 1], jobs[idx]
            if cur_j.start_min < prev_j.end_min:
                hc3_v.append(
                    f"Mold {mold_id}: concurrent run {prev_j.order_id} ({prev_j.machine_id}, end {prev_j.end_min}m) "
                    f"& {cur_j.order_id} ({cur_j.machine_id}, start {cur_j.start_min}m)"
                )

    # ------------------------------------------------------------------
    # HC4: Asymmetric Sequence-Dependent Changeover & Color/Resin Purge Gap
    # ------------------------------------------------------------------
    hc4_v: list[str] = []
    for mid, jobs in by_press.items():
        jobs.sort(key=lambda x: (x.start_min, x.end_min))
        for idx in range(1, len(jobs)):
            prev_j, cur_j = jobs[idx - 1], jobs[idx]
            req_setup, _, _ = transition_penalty(
                orders_by_id[prev_j.order_id],
                orders_by_id[cur_j.order_id],
                molds_by_id[prev_j.mold_id],
                molds_by_id[cur_j.mold_id],
                physics=config.physics,
            )
            actual_gap = cur_j.start_min - prev_j.end_min
            if actual_gap < req_setup:
                hc4_v.append(
                    f"Press {mid}: {prev_j.order_id}->{cur_j.order_id} gap {actual_gap}m < required setup/purge {req_setup}m"
                )

    # ------------------------------------------------------------------
    # HC5: Resin Pre-Drying Floor, Food-Grade Regrind Safety & Inventory Cap
    # ------------------------------------------------------------------
    hc5_v: list[str] = []
    virgin_used_by_resin: dict[str, float] = defaultdict(float)
    regrind_used_by_resin: dict[str, float] = defaultdict(float)
    for j in scheduled:
        resin = resins_by_code[j.resin_code]
        order = orders_by_id[j.order_id]
        dry_floor_min = int(round(resin.drying_lead_time_hrs * 60))
        if j.start_min < dry_floor_min:
            hc5_v.append(
                f"{j.order_id}: start {j.start_min}m violates {j.resin_code} drying floor {dry_floor_min}m"
            )
        if order.max_regrind_pct <= 0 and j.regrind_kg > 0.05:
            hc5_v.append(f"{j.order_id}: food/pharma order assigned {j.regrind_kg}kg regrind (must be 0)")
        virgin_used_by_resin[j.resin_code] += j.virgin_kg + j.purge_scrap_kg
        regrind_used_by_resin[j.resin_code] += j.regrind_kg

    for r in dataset.resins:
        v_tot = virgin_used_by_resin[r.resin_code]
        rg_tot = regrind_used_by_resin[r.resin_code]
        if v_tot > r.virgin_available_kg + 0.5:
            hc5_v.append(
                f"Resin {r.resin_code}: virgin + purge {v_tot:.1f}kg exceeds stock {r.virgin_available_kg:.1f}kg"
            )
        if rg_tot > r.regrind_available_kg + 0.5:
            hc5_v.append(
                f"Resin {r.resin_code}: regrind {rg_tot:.1f}kg exceeds stock {r.regrind_available_kg:.1f}kg"
            )

    # ------------------------------------------------------------------
    # HC6: Mold Preventive Maintenance Block (Static t=0 OR Autonomous Window)
    # ------------------------------------------------------------------
    hc6_v: list[str] = []
    pm_windows_by_mold = {pm.mold_id: pm for pm in plan.mold_pm_windows}
    for mold_id, pm_hrs in mold_pm_durations_hrs.items():
        if pm_hrs <= 0:
            continue
        req_pm_mins = int(round(pm_hrs * 60))
        mold = molds_by_id.get(mold_id)
        pm_win = pm_windows_by_mold.get(mold_id)

        if pm_win is not None and pm_win.mode == "autonomous":
            # 1. Duration check
            if (pm_win.end_min - pm_win.start_min) < req_pm_mins:
                hc6_v.append(
                    f"Mold {mold_id}: autonomous PM duration {pm_win.end_min - pm_win.start_min}m < required {req_pm_mins}m"
                )
            # 2. Zero overlap between PM block and any production job on that mold
            shots_before_pm = 0
            for j in by_mold.get(mold_id, []):
                if min(j.end_min, pm_win.end_min) > max(j.start_min, pm_win.start_min):
                    hc6_v.append(
                        f"Mold {mold_id}: {j.order_id} [{j.start_min}..{j.end_min}m] overlaps autonomous PM [{pm_win.start_min}..{pm_win.end_min}m]"
                    )
                if j.end_min <= pm_win.start_min and mold is not None:
                    order = orders_by_id.get(j.order_id)
                    if order is not None:
                        shots_before_pm += order_shots(order, mold)
            # 3. Shot-limit safety before PM executes
            if mold is not None and pm_win.trigger_reason in ("shot_threshold_95pct", "midweek_shot_limit"):
                rem_shots = max(0, mold.maintenance_interval_shots - mold.current_shots)
                if shots_before_pm > rem_shots:
                    hc6_v.append(
                        f"Mold {mold_id}: {shots_before_pm:,} shots scheduled before PM exceeds remaining shot budget {rem_shots:,}"
                    )
        else:
            pm_end_min = req_pm_mins
            for j in by_mold.get(mold_id, []):
                if j.start_min < pm_end_min:
                    hc6_v.append(
                        f"Mold {mold_id}: {j.order_id} starts at {j.start_min}m before {pm_end_min}m PM block finishes"
                    )

    return [
        ConstraintCheck(
            id="HC1",
            name="Mold–Press Compatibility & Hot-Runner Fit",
            violations=len(hc1_v),
            passed=len(hc1_v) == 0,
            details=hc1_v[:5],
        ),
        ConstraintCheck(
            id="HC2",
            name="No Press Overlap & Breakdown/Downtime Exclusion",
            violations=len(hc2_v),
            passed=len(hc2_v) == 0,
            details=hc2_v[:5],
        ),
        ConstraintCheck(
            id="HC3",
            name="Physical Mold Exclusivity Across Presses",
            violations=len(hc3_v),
            passed=len(hc3_v) == 0,
            details=hc3_v[:5],
        ),
        ConstraintCheck(
            id="HC4",
            name="Asymmetric Changeover & Color/Resin Purge Sequencing",
            violations=len(hc4_v),
            passed=len(hc4_v) == 0,
            details=hc4_v[:5],
        ),
        ConstraintCheck(
            id="HC5",
            name="Resin Pre-Drying Floor & Virgin/Regrind Inventory Cap",
            violations=len(hc5_v),
            passed=len(hc5_v) == 0,
            details=hc5_v[:5],
        ),
        ConstraintCheck(
            id="HC6",
            name="Mold Preventive Maintenance (PM) Shot-Count Block",
            violations=len(hc6_v),
            passed=len(hc6_v) == 0,
            details=hc6_v[:5],
        ),
    ]
