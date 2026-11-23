"""Deterministic Google OR-Tools CP-SAT Plastic Manufacturing Solver + Naive FIFO Baseline.

Zero LLMs. Zero random heuristics. 100% deterministic integer programming via CP-SAT `AddCircuit` + `AddNoOverlap`.
"""
from __future__ import annotations

import hashlib
import json
import math
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

import ortools
from ortools.sat.python import cp_model

from .disruptions import apply_plant_scenarios
from .financials import compute_financial_report
from .kpi import build_schedule_plan, build_scorecard
from .ontology import (
    EXTENDED_HORIZON_MINS,
    RAMADAN_BLACKOUT_END_HR,
    RAMADAN_BLACKOUT_START_HR,
    AuditRecord,
    PlantDataset,
    ScheduledMoldPm,
    SchedulePlan,
    SolveResult,
    SolverConfig,
    ValidationReport,
    compatible_active_presses,
    order_duration_mins,
    order_gross_weight_kg,
    order_shots,
    ramadan_labor_multiplier,
    transition_penalty,
    validate_plant_data,
)
from .risk_radar import compute_risk_radar
from .verify import verify_hard_constraints
from .workforce_solver import solve_workforce


class DatasetValidationError(ValueError):
    """Raised when pre-solve validation detects blocking errors (`report.ready == False`)."""

    def __init__(self, report: ValidationReport):
        self.report = report
        msgs = "; ".join(i.message for i in report.issues if i.severity == "error")
        super().__init__(f"Plant dataset failed pre-solve validation ({report.error_count} error(s)): {msgs}")


def _overlaps_any(start_m: int, end_m: int, intervals: list[tuple[int, int]]) -> bool:
    for s, e in intervals:
        if min(end_m, e) > max(start_m, s):
            return True
    return False


def _next_feasible_start(
    earliest_prod_start: int,
    dur_mins: int,
    setup_mins: int,
    press_blocked: list[tuple[int, int]],
    mold_blocked: list[tuple[int, int]],
    ramadan_blackouts: list[tuple[int, int]],
    horizon_mins: int,
) -> int:
    """Find the earliest minute `t >= earliest_prod_start` where:
      - Press busy interval `[t - setup_mins, t + dur_mins)` avoids all `press_blocked` intervals
      - Mold run interval `[t, t + dur_mins)` avoids all `mold_blocked` intervals
      - Setup interval `[t - setup_mins, t)` avoids `ramadan_blackouts` when setup_mins > 0
    """
    t = max(earliest_prod_start, setup_mins)
    for _ in range(500):
        busy_s = t - setup_mins
        prod_e = t + dur_mins
        bumped = False

        for bs, be in press_blocked:
            if min(prod_e, be) > max(busy_s, bs):
                t = max(t + 1, be + setup_mins)
                bumped = True
                break
        if bumped:
            continue

        for ms, me in mold_blocked:
            if min(prod_e, me) > max(t, ms):
                t = max(t + 1, me)
                bumped = True
                break
        if bumped:
            continue

        if setup_mins > 0 and ramadan_blackouts:
            for rs, re_ in ramadan_blackouts:
                if min(t, re_) > max(busy_s, rs):
                    t = max(t + 1, re_ + setup_mins)
                    bumped = True
                    break
            if bumped:
                continue

        return min(t, horizon_mins - dur_mins)
    return min(t, horizon_mins - dur_mins)


def _ramadan_blackout_windows(horizon_mins: int) -> list[tuple[int, int]]:
    n_days = max(7, int(math.ceil(horizon_mins / 1440.0)))
    return [
        (d * 1440 + RAMADAN_BLACKOUT_START_HR * 60, d * 1440 + RAMADAN_BLACKOUT_END_HR * 60)
        for d in range(n_days)
    ]


def run_fifo_baseline(
    dataset: PlantDataset,
    config: SolverConfig,
    mold_pm_durations_hrs: dict[str, float],
    horizon_mins: int,
) -> SchedulePlan:
    """Naive Factory Spreadsheet FIFO Scheduler.

    Schedules orders strictly in ascending `(due_hr, order_id)` order onto the first compatible
    press that can finish the job earliest — with NO light-to-dark color grouping and NO mold batching.
    Strictly obeys all 6 hard constraints (HC1-HC6) for a 100% fair, apples-to-apples ROI comparison.
    """
    presses_by_id = {p.machine_id: p for p in dataset.presses}
    molds_by_id = {m.mold_id: m for m in dataset.molds}
    resins_by_code = {r.resin_code: r for r in dataset.resins}

    press_blocked: dict[str, list[tuple[int, int]]] = {}
    press_free_at: dict[str, int] = {}
    press_last_order: dict[str, tuple | None] = {}
    for p in dataset.presses:
        press_blocked[p.machine_id] = [
            (int(round(dw.start_hr * 60)), int(round(dw.end_hr * 60))) for dw in p.downtime_windows
        ]
        press_free_at[p.machine_id] = 0
        press_last_order[p.machine_id] = None

    mold_blocked: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for mold_id, pm_hrs in mold_pm_durations_hrs.items():
        if pm_hrs > 0:
            mold_blocked[mold_id].append((0, int(round(pm_hrs * 60))))

    rem_virgin = {r.resin_code: r.virgin_available_kg for r in dataset.resins}
    rem_regrind = {r.resin_code: r.regrind_available_kg for r in dataset.resins}
    ramadan_blks = _ramadan_blackout_windows(horizon_mins) if config.ramadan_shift_mode else []

    sorted_orders = sorted(dataset.orders, key=lambda o: (o.due_hr, o.order_id))
    raw_assignments: list[dict] = []

    for order in sorted_orders:
        mold = molds_by_id[order.mold_id]
        resin = resins_by_code[order.resin_code]
        dur_mins = order_duration_mins(order, mold)
        dry_floor = int(round(resin.drying_lead_time_hrs * 60))
        pm_floor = int(round(mold_pm_durations_hrs.get(mold.mold_id, 0.0) * 60))
        floor_min = max(dry_floor, pm_floor)

        compat = compatible_active_presses(mold, presses_by_id)
        if not compat:
            raw_assignments.append(
                {"order_id": order.order_id, "scheduled": False, "unscheduled_reason": "No compatible active press"}
            )
            continue

        # Pick press with earliest completion time (pure FIFO greedy without color/mold grouping)
        best_choice = None
        for p in compat:
            last = press_last_order[p.machine_id]
            if last is None:
                setup_m, purge_kg = 0, 0.0
            else:
                setup_m, purge_kg, _ = transition_penalty(last[0], order, last[1], mold, physics=config.physics)

            earliest = max(floor_min, press_free_at[p.machine_id] + setup_m)
            cand_start = _next_feasible_start(
                earliest_prod_start=earliest,
                dur_mins=dur_mins,
                setup_mins=setup_m,
                press_blocked=press_blocked[p.machine_id],
                mold_blocked=mold_blocked[mold.mold_id],
                ramadan_blackouts=ramadan_blks,
                horizon_mins=horizon_mins,
            )
            cand_end = cand_start + dur_mins
            if best_choice is None or (cand_end, p.machine_id) < (best_choice[1], best_choice[0].machine_id):
                best_choice = (p, cand_end, cand_start, setup_m, purge_kg)

        assert best_choice is not None
        p, end_min, start_min, setup_m, purge_kg = best_choice

        # Check resin inventory cap (use allowed regrind greedily up to cap to mirror plant reality)
        gross_kg = order_gross_weight_kg(order, mold)
        max_rg = round(gross_kg * (order.max_regrind_pct / 100.0), 2)
        rg_use = round(min(max_rg, rem_regrind[order.resin_code]), 2)
        v_use = round(gross_kg - rg_use, 2)

        if v_use + purge_kg > rem_virgin[order.resin_code] + 1e-6:
            raw_assignments.append(
                {
                    "order_id": order.order_id,
                    "scheduled": False,
                    "unscheduled_reason": f"FIFO depleted {order.resin_code} virgin stock ({rem_virgin[order.resin_code]:.1f}kg left)",
                }
            )
            continue

        rem_virgin[order.resin_code] = round(rem_virgin[order.resin_code] - (v_use + purge_kg), 2)
        rem_regrind[order.resin_code] = round(rem_regrind[order.resin_code] - rg_use, 2)

        press_blocked[p.machine_id].append((start_min - setup_m, end_min))
        press_free_at[p.machine_id] = end_min
        press_last_order[p.machine_id] = (order, mold)
        mold_blocked[mold.mold_id].append((start_min, end_min))

        raw_assignments.append(
            {
                "order_id": order.order_id,
                "scheduled": True,
                "machine_id": p.machine_id,
                "start_min": start_min,
                "end_min": end_min,
                "virgin_kg": v_use,
                "regrind_kg": rg_use,
            }
        )

    return build_schedule_plan(dataset, config, raw_assignments, mold_pm_durations_hrs)


def _solve_cpsat_model(
    dataset: PlantDataset,
    config: SolverConfig,
    mold_pm_durations_hrs: dict[str, float],
    mold_pm_reasons: dict[str, str],
    horizon_mins: int,
    baseline_plan: SchedulePlan,
) -> tuple[SchedulePlan, str, int, float, float, float, dict]:
    """Build and solve the deterministic OR-Tools CP-SAT parallel-machine scheduling model.

    Hard Constraints Enforced:
      HC1: Mold-press compatibility, active status, hot-runner support
      HC2: No press overlap + downtime & breakdown exclusion (including setup/purge)
      HC3: Physical mold exclusivity across all presses (`AddNoOverlap` per mold)
      HC4: Asymmetric sequence-dependent setup & color/resin purge (`AddCircuit` per press)
      HC5: Resin pre-drying start floor + virgin/regrind inventory caps + food-grade 0% regrind
      HC6: Mold Preventive Maintenance (PM) mandatory block before further runs
    """
    t0 = time.perf_counter()
    model = cp_model.CpModel()

    presses = dataset.presses
    presses_by_id = {p.machine_id: p for p in presses}
    molds_by_id = {m.mold_id: m for m in dataset.molds}
    resins_by_code = {r.resin_code: r for r in dataset.resins}
    orders = dataset.orders
    n_orders = len(orders)

    # Precompute per-order physics
    dur_mins = [order_duration_mins(o, molds_by_id[o.mold_id]) for o in orders]
    gross_10 = [int(round(order_gross_weight_kg(o, molds_by_id[o.mold_id]) * 10)) for o in orders]
    max_rg_10 = [int(math.floor(gross_10[i] * (orders[i].max_regrind_pct / 100.0))) for i in range(n_orders)]
    min_vg_10 = [gross_10[i] - max_rg_10[i] for i in range(n_orders)]

    # Determine which resins are scarce (so CP-SAT can leave lowest-priority jobs unscheduled rather than INFEASIBLE)
    resin_min_vg_sum: dict[str, int] = defaultdict(int)
    resin_orders_cnt: dict[str, int] = defaultdict(int)
    for i, o in enumerate(orders):
        resin_min_vg_sum[o.resin_code] += min_vg_10[i]
        resin_orders_cnt[o.resin_code] += 1

    scarce_resins: set[str] = set()
    for r in dataset.resins:
        # Leave a conservative purge buffer (35kg * orders) when deciding whether optional scheduling is needed
        avail_10 = int(round(r.virgin_available_kg * 10))
        if resin_min_vg_sum[r.resin_code] + resin_orders_cnt[r.resin_code] * 350 > avail_10:
            scarce_resins.add(r.resin_code)

    # Order variables
    scheduled: list[cp_model.IntVar] = []
    start_vars: list[cp_model.IntVar] = []
    start_lbs: list[int] = []
    end_vars: list[cp_model.IntVar] = []
    setup_vars: list[cp_model.IntVar] = []
    busy_start_vars: list[cp_model.IntVar] = []
    busy_size_vars: list[cp_model.IntVar] = []
    tardiness_vars: list[cp_model.IntVar] = []
    earliness_vars: list[cp_model.IntVar] = []
    virgin_10_vars: list[cp_model.IntVar] = []
    regrind_10_vars: list[cp_model.IntVar] = []

    compat_press_ids: list[list[str]] = []
    pres_vars: dict[tuple[int, str], cp_model.IntVar] = {}
    press_to_orders: dict[str, list[int]] = defaultdict(list)
    mold_intervals: dict[str, list[cp_model.IntervalVar]] = defaultdict(list)
    mold_to_orders: dict[str, list[int]] = defaultdict(list)

    ph = config.physics
    max_possible_setup = max(
        360,
        int(round(ph.light_to_dark_purge_mins * 1.5)) + 480,
        int(round(ph.dark_to_light_purge_mins * 1.5)) + 480,
        int(ph.incompatible_resin_purge_mins) + 480,
    )

    for i, o in enumerate(orders):
        mold = molds_by_id[o.mold_id]
        resin = resins_by_code[o.resin_code]
        compat = compatible_active_presses(mold, presses_by_id)
        c_ids = [p.machine_id for p in compat]
        compat_press_ids.append(c_ids)

        is_scarce = o.resin_code in scarce_resins
        if is_scarce:
            sch = model.NewBoolVar(f"sch_{i}")
        else:
            sch = model.NewConstant(1)
        scheduled.append(sch)

        # HC5 pre-drying floor + HC6 mold PM floor (floated when autonomous_pm_window=True)
        dry_floor = int(round(resin.drying_lead_time_hrs * 60))
        pm_floor = 0 if config.autonomous_pm_window else int(round(mold_pm_durations_hrs.get(mold.mold_id, 0.0) * 60))
        start_lb = max(dry_floor, pm_floor)

        s_var = model.NewIntVar(start_lb, horizon_mins - dur_mins[i], f"start_{i}")
        e_var = model.NewIntVar(start_lb + dur_mins[i], horizon_mins, f"end_{i}")
        model.Add(e_var == s_var + dur_mins[i])

        stp_var = model.NewIntVar(0, max_possible_setup, f"setup_{i}")
        b_start = model.NewIntVar(0, horizon_mins - dur_mins[i], f"bstart_{i}")
        b_size = model.NewIntVar(dur_mins[i], dur_mins[i] + max_possible_setup, f"bsize_{i}")
        model.Add(b_start + stp_var == s_var)
        model.Add(b_size == dur_mins[i] + stp_var)

        due_min = int(round(o.due_hr * 60))
        tard = model.NewIntVar(0, horizon_mins, f"tard_{i}")
        early_ref_min = max(0, due_min - 420) if (o.is_export and config.w_otif >= 50) else due_min
        early = model.NewIntVar(0, max(due_min, 1), f"early_{i}")
        model.Add(tard >= e_var - due_min).OnlyEnforceIf(sch)
        model.Add(early >= early_ref_min - e_var).OnlyEnforceIf(sch)

        # Virgin / regrind material split (0.1 kg precision)
        vg = model.NewIntVar(0, gross_10[i], f"vg_{i}")
        rg = model.NewIntVar(0, max_rg_10[i], f"rg_{i}")
        if is_scarce:
            model.Add(vg + rg == gross_10[i]).OnlyEnforceIf(sch)
            model.Add(vg == 0).OnlyEnforceIf(sch.Not())
            model.Add(rg == 0).OnlyEnforceIf(sch.Not())
        else:
            model.Add(vg + rg == gross_10[i])

        start_vars.append(s_var)
        start_lbs.append(start_lb)
        end_vars.append(e_var)
        setup_vars.append(stp_var)
        busy_start_vars.append(b_start)
        busy_size_vars.append(b_size)
        tardiness_vars.append(tard)
        earliness_vars.append(early)
        virgin_10_vars.append(vg)
        regrind_10_vars.append(rg)

        # HC1: Exactly one active compatible press if scheduled
        p_bools = []
        for mid in c_ids:
            pv = model.NewBoolVar(f"pres_{i}_{mid}")
            pres_vars[(i, mid)] = pv
            press_to_orders[mid].append(i)
            p_bools.append(pv)
        model.Add(sum(p_bools) == sch)

        # HC3: Physical mold exclusivity interval
        if is_scarce:
            m_iv = model.NewOptionalIntervalVar(s_var, dur_mins[i], e_var, sch, f"mold_iv_{i}")
        else:
            m_iv = model.NewIntervalVar(s_var, dur_mins[i], e_var, f"mold_iv_{i}")
        mold_intervals[o.mold_id].append(m_iv)
        mold_to_orders[o.mold_id].append(i)

    # HC3 & HC6: Enforce NoOverlap per physical mold + mandatory PM interval (Static t=0 OR Autonomous Co-Optimization)
    pm_start_vars: dict[str, tuple[cp_model.IntVar, cp_model.IntVar, float, str, Optional[float]]] = {}
    pm_tiebreak_terms = []
    base_h_mins = ph.horizon_hrs * 60
    for mold in dataset.molds:
        m_ivs = list(mold_intervals.get(mold.mold_id, []))
        pm_hrs = mold_pm_durations_hrs.get(mold.mold_id, 0.0)
        if pm_hrs > 0:
            pm_mins = int(round(pm_hrs * 60))
            if not config.autonomous_pm_window:
                m_ivs.append(model.NewFixedSizeIntervalVar(0, pm_mins, f"pm_iv_{mold.mold_id}"))
            else:
                pm_reason = mold_pm_reasons.get(
                    mold.mold_id,
                    "shot_threshold_95pct" if mold.shot_utilization_pct >= 95.0 else "manual_lock",
                )
                rem_shots = max(0, mold.maintenance_interval_shots - mold.current_shots)
                if mold.shot_utilization_pct >= 100.0:
                    pm_s = model.NewConstant(0)
                    pm_e = model.NewConstant(pm_mins)
                    pm_dl_hr = round(pm_hrs, 1)
                else:
                    pm_deadline_min = min(horizon_mins, max(pm_mins, int(round(base_h_mins * 0.75))))
                    pm_s = model.NewIntVar(0, max(0, pm_deadline_min - pm_mins), f"pm_start_{mold.mold_id}")
                    pm_e = model.NewIntVar(pm_mins, max(pm_mins, pm_deadline_min), f"pm_end_{mold.mold_id}")
                    model.Add(pm_e == pm_s + pm_mins)
                    model.AddHint(pm_s, 0)
                    pm_dl_hr = round(pm_deadline_min / 60.0, 1)
                    pm_tiebreak_terms.append(pm_s)

                m_ivs.append(model.NewFixedSizeIntervalVar(pm_s, pm_mins, f"pm_iv_{mold.mold_id}"))
                pm_start_vars[mold.mold_id] = (pm_s, pm_e, pm_hrs, pm_reason, pm_dl_hr)

                # Enforce shot-limit safety before PM executes
                m_o_idxs = mold_to_orders.get(mold.mold_id, [])
                if pm_reason in ("shot_threshold_95pct", "midweek_shot_limit") and m_o_idxs:
                    shots_before_terms = []
                    for o_idx in m_o_idxs:
                        bp = model.NewBoolVar(f"before_pm_{mold.mold_id}_{o_idx}")
                        model.Add(end_vars[o_idx] <= pm_s).OnlyEnforceIf(bp)
                        model.Add(start_vars[o_idx] >= pm_e).OnlyEnforceIf(bp.Not())
                        if orders[o_idx].resin_code in scarce_resins:
                            model.Add(bp <= scheduled[o_idx])
                        shots_before_terms.append(order_shots(orders[o_idx], mold) * bp)
                    model.Add(sum(shots_before_terms) <= rem_shots)
        if len(m_ivs) >= 2:
            model.AddNoOverlap(m_ivs)

    # HC2 & HC4: Per-press NoOverlap (with breakdowns/downtime) + AddCircuit (asymmetric setup & purge)
    purge_resin_terms_10: dict[str, list] = defaultdict(list)
    total_setup_mins_terms = []
    total_purge_cost_cents_terms = []  # SAR cents (1 SAR = 100 cents)
    ramadan_blks = _ramadan_blackout_windows(horizon_mins) if config.ramadan_shift_mode else []
    idle_vars: dict[str, cp_model.IntVar] = {}
    arc_vars: dict[tuple[str, int, int], cp_model.IntVar] = {}

    for p in presses:
        mid = p.machine_id
        o_indices = press_to_orders.get(mid, [])
        if not o_indices:
            continue

        # HC2 press busy intervals + fixed downtime/breakdown windows
        press_ivs: list[cp_model.IntervalVar] = []
        setup_ivs_for_ramadan: list[cp_model.IntervalVar] = []
        for i in o_indices:
            pv = pres_vars[(i, mid)]
            press_ivs.append(
                model.NewOptionalIntervalVar(
                    busy_start_vars[i], busy_size_vars[i], end_vars[i], pv, f"piv_{mid}_{i}"
                )
            )
            if ramadan_blks:
                setup_ivs_for_ramadan.append(
                    model.NewOptionalIntervalVar(
                        busy_start_vars[i], setup_vars[i], start_vars[i], pv, f"siv_{mid}_{i}"
                    )
                )

        for d_idx, dw in enumerate(p.downtime_windows):
            ds = int(round(dw.start_hr * 60))
            de = int(round(dw.end_hr * 60))
            if de > ds:
                press_ivs.append(model.NewFixedSizeIntervalVar(ds, de - ds, f"dw_{mid}_{d_idx}"))

        model.AddNoOverlap(press_ivs)

        # Ramadan Shift Mode: no changeovers/purges during daily 18:00-20:00 Iftar blackout
        if ramadan_blks and setup_ivs_for_ramadan:
            blk_ivs = [
                model.NewFixedSizeIntervalVar(rs, re_ - rs, f"ram_{mid}_{idx}")
                for idx, (rs, re_) in enumerate(ramadan_blks)
            ]
            model.AddNoOverlap(setup_ivs_for_ramadan + blk_ivs)

        # HC4 AddCircuit on press `mid` (node 0 = depot, node k = o_indices[k-1])
        arcs: list[tuple[int, int, cp_model.IntVar]] = []
        idle_m = model.NewBoolVar(f"idle_{mid}")
        idle_vars[mid] = idle_m
        arcs.append((0, 0, idle_m))
        # Press is idle iff no order is assigned to it
        any_on_press = [pres_vars[(i, mid)] for i in o_indices]
        model.Add(sum(any_on_press) == 0).OnlyEnforceIf(idle_m)
        model.Add(sum(any_on_press) >= 1).OnlyEnforceIf(idle_m.Not())

        for pos_i, i in enumerate(o_indices, start=1):
            pv_i = pres_vars[(i, mid)]
            # Self-loop when order i is NOT on press mid
            arcs.append((pos_i, pos_i, pv_i.Not()))

            # Depot -> order i (first job on press: 0 setup)
            a_0_i = model.NewBoolVar(f"arc_{mid}_0_{i}")
            arc_vars[(mid, -1, i)] = a_0_i
            arcs.append((0, pos_i, a_0_i))
            model.Add(setup_vars[i] == 0).OnlyEnforceIf(a_0_i)

            # Order i -> depot (last job on press)
            a_i_0 = model.NewBoolVar(f"arc_{mid}_{i}_0")
            arc_vars[(mid, i, -1)] = a_i_0
            arcs.append((pos_i, 0, a_i_0))

            # Order i -> Order j transitions
            oi = orders[i]
            mi = molds_by_id[oi.mold_id]
            for pos_j, j in enumerate(o_indices, start=1):
                if i == j:
                    continue
                oj = orders[j]
                mj = molds_by_id[oj.mold_id]
                stp_m, purge_kg, _ = transition_penalty(oi, oj, mi, mj, physics=ph)

                a_ij = model.NewBoolVar(f"arc_{mid}_{i}_{j}")
                arc_vars[(mid, i, j)] = a_ij
                arcs.append((pos_i, pos_j, a_ij))

                # Sequence precedence & exact setup assignment
                model.Add(busy_start_vars[j] >= end_vars[i]).OnlyEnforceIf(a_ij)
                model.Add(setup_vars[j] == stp_m).OnlyEnforceIf(a_ij)

                if stp_m > 0:
                    total_setup_mins_terms.append(stp_m * a_ij)
                if purge_kg > 0:
                    purge_10 = int(round(purge_kg * 10))
                    purge_resin_terms_10[oj.resin_code].append(purge_10 * a_ij)
                    resin_j = resins_by_code[oj.resin_code]
                    purge_cost_cents = int(round(purge_kg * resin_j.virgin_cost_per_kg * 100))
                    total_purge_cost_cents_terms.append(purge_cost_cents * a_ij)

        model.AddCircuit(arcs)

    # HC5: Resin Virgin & Regrind Inventory Caps (0.1 kg integer units)
    for r in dataset.resins:
        v_cap_10 = int(round(r.virgin_available_kg * 10))
        rg_cap_10 = int(round(r.regrind_available_kg * 10))
        r_order_idxs = [i for i, o in enumerate(orders) if o.resin_code == r.resin_code]
        if r_order_idxs:
            model.Add(
                sum(virgin_10_vars[i] for i in r_order_idxs)
                + sum(purge_resin_terms_10.get(r.resin_code, []))
                <= v_cap_10
            )
            model.Add(sum(regrind_10_vars[i] for i in r_order_idxs) <= rg_cap_10)

    # ------------------------------------------------------------------
    # Multi-Objective Terms (Scaled to SAR Cents for Clean Integer Arithmetic)
    # ------------------------------------------------------------------
    labor_mult = ramadan_labor_multiplier(ph) if config.ramadan_shift_mode else 1.0

    # 1. Changeover & Purge Scrap term (purge resin cost + changeover downtime cost @ ~250 SAR/hr)
    changeover_scrap_expr = (
        sum(total_purge_cost_cents_terms)
        + sum(int(round((250.0 / 60.0) * 100)) * t for t in total_setup_mins_terms)
    )

    # 2. OTIF / Late Export Penalty term (+ massive penalty for any unscheduled order)
    #    When w_otif >= 50, also protect a >=6.5h (390 min) port cut-off safety buffer on export orders.
    otif_terms = []
    unscheduled_terms = []
    for i, o in enumerate(orders):
        export_mult = 1.5 if o.is_export else 1.0
        pen_per_min_cents = max(1, int(round((o.late_penalty_per_hr * export_mult / 60.0) * 100)))
        otif_terms.append(pen_per_min_cents * tardiness_vars[i])
        if o.is_export and config.w_otif >= 50:
            due_min_i = int(round(o.due_hr * 60))
            safe_due_min = max(start_lbs[i] + dur_mins[i], due_min_i - 390)
            if safe_due_min < due_min_i:
                buf_short = model.NewIntVar(0, 390, f"exp_buf_{i}")
                model.Add(buf_short >= end_vars[i] - safe_due_min).OnlyEnforceIf(scheduled[i])
                buf_pen_cents = max(1, int(round((o.late_penalty_per_hr * 0.35 / 60.0) * 100)))
                otif_terms.append(buf_pen_cents * buf_short)
        if o.resin_code in scarce_resins:
            # High priority to keep export & high-penalty orders scheduled
            drop_pen = int(round(48.0 * o.late_penalty_per_hr * export_mult * 100 * 4))
            unscheduled_terms.append(drop_pen * (1 - scheduled[i]))
    otif_expr = sum(otif_terms) + sum(unscheduled_terms)

    # 3. Energy & Operating Cost term (including optional peak tariff surcharge)
    energy_terms = []
    n_peak_days = max(1, int(math.ceil(horizon_mins / 1440.0)))
    peak_surcharge_pct = max(0.0, ph.peak_tariff_multiplier - 1.0)
    peak_window_mins = max(60, (ph.peak_end_hr - ph.peak_start_hr) * 60)
    for i, o in enumerate(orders):
        run_hrs = dur_mins[i] / 60.0
        for mid in compat_press_ids[i]:
            p = presses_by_id[mid]
            base_energy_oper_cents = int(
                round(
                    run_hrs
                    * (p.hourly_energy_kwh * ph.energy_tariff_per_kwh + p.hourly_operating_cost * labor_mult)
                    * 100
                )
            )
            energy_terms.append(base_energy_oper_cents * pres_vars[(i, mid)])

        if config.avoid_peak_tariff_hrs and peak_surcharge_pct > 0:
            # Exact peak overlap minutes across days for order i, weighted by avg compatible press kWh
            avg_kwh = sum(presses_by_id[mid].hourly_energy_kwh for mid in compat_press_ids[i]) / max(
                len(compat_press_ids[i]), 1
            )
            peak_cents_per_min = max(
                1, int(round((avg_kwh / 60.0) * peak_surcharge_pct * ph.energy_tariff_per_kwh * 100))
            )
            for d in range(n_peak_days):
                ps = d * 1440 + ph.peak_start_hr * 60
                pe = d * 1440 + ph.peak_end_hr * 60
                if pe <= start_lbs[i] or ps >= horizon_mins:
                    continue
                ps_const = model.NewConstant(ps)
                pe_const = model.NewConstant(pe)
                mx_s = model.NewIntVar(ps, horizon_mins, f"pks_{i}_{d}")
                mn_e = model.NewIntVar(0, pe, f"pke_{i}_{d}")
                model.AddMaxEquality(mx_s, [start_vars[i], ps_const])
                model.AddMinEquality(mn_e, [end_vars[i], pe_const])
                ov = model.NewIntVar(0, peak_window_mins, f"pko_{i}_{d}")
                model.Add(ov >= mn_e - mx_s)
                energy_terms.append(peak_cents_per_min * ov)
    energy_expr = sum(energy_terms)

    # 4. Working Capital term (virgin vs. regrind resin spend + early WIP holding)
    wc_terms = []
    for i, o in enumerate(orders):
        r = resins_by_code[o.resin_code]
        # virgin_10 / regrind_10 are in 0.1 kg -> cost per 0.1 kg in cents = price * 10
        vg_cents_per_01kg = int(round(r.virgin_cost_per_kg * 10))
        rg_cents_per_01kg = int(round(r.regrind_cost_per_kg * 10))
        wc_terms.append(vg_cents_per_01kg * virgin_10_vars[i] + rg_cents_per_01kg * regrind_10_vars[i])

        # WIP earliness holding cost (in cents per minute early)
        gross_kg = gross_10[i] / 10.0
        wip_cents_per_min = (
            max(1, int(round((gross_kg * ph.holding_cost_per_kg_per_day / 1440.0) * 100)))
            if ph.holding_cost_per_kg_per_day > 0
            else 0
        )
        if wip_cents_per_min > 0:
            wc_terms.append(wip_cents_per_min * earliness_vars[i])
    wc_expr = sum(wc_terms)

    # Combine with the 4 executive weights (scale by weight + small floor so non-active objectives stay clean)
    # Use baseline magnitudes to balance the 4 objective scales nicely.
    pm_tiebreak_expr = sum(pm_tiebreak_terms) if pm_tiebreak_terms else 0
    model.Minimize(
        (config.w_changeover_scrap * 3 + 1) * changeover_scrap_expr
        + (config.w_otif * 3 + 1) * otif_expr
        + (config.w_energy_cost * 2 + 1) * energy_expr
        + (config.w_working_capital * 2 + 1) * wc_expr
        + pm_tiebreak_expr
    )

    # Full feasible warm-start hint from FIFO baseline (scheduled, press assignment, AddCircuit arcs,
    # start/setup timing, and exact 0.1kg virgin/regrind split) for instant feasible incumbent.
    fifo_by_oid = {j.order_id: j for j in baseline_plan.jobs}
    fifo_press_seq: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for i, o in enumerate(orders):
        fj = fifo_by_oid.get(o.order_id)
        is_fifo_sch = bool(fj and fj.scheduled and (i, fj.machine_id) in pres_vars)
        if o.resin_code in scarce_resins:
            model.AddHint(scheduled[i], 1 if is_fifo_sch else 0)
        for mid in compat_press_ids[i]:
            model.AddHint(pres_vars[(i, mid)], 1 if (is_fifo_sch and fj.machine_id == mid) else 0)
        if is_fifo_sch:
            s_hint = max(start_lbs[i], min(horizon_mins - dur_mins[i], int(fj.start_min)))
            model.AddHint(start_vars[i], s_hint)
            rg_hint = min(max_rg_10[i], max(0, int(round(fj.regrind_kg * 10))))
            vg_hint = gross_10[i] - rg_hint
            model.AddHint(virgin_10_vars[i], vg_hint)
            model.AddHint(regrind_10_vars[i], rg_hint)
            fifo_press_seq[fj.machine_id].append((s_hint, i))
        elif o.resin_code in scarce_resins:
            model.AddHint(virgin_10_vars[i], 0)
            model.AddHint(regrind_10_vars[i], 0)

    # Hint AddCircuit arcs per press strictly matching the chronological FIFO order
    for mid, idle_m in idle_vars.items():
        seq_pairs = sorted(fifo_press_seq.get(mid, []), key=lambda x: (x[0], x[1]))
        seq = [idx for _, idx in seq_pairs]
        active_arcs: set[tuple[int, int]] = set()
        if not seq:
            model.AddHint(idle_m, 1)
        else:
            model.AddHint(idle_m, 0)
            active_arcs.add((-1, seq[0]))
            active_arcs.add((seq[-1], -1))
            for k in range(len(seq) - 1):
                active_arcs.add((seq[k], seq[k + 1]))
        for (amid, u, v), avar in arc_vars.items():
            if amid == mid:
                model.AddHint(avar, 1 if (u, v) in active_arcs else 0)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(config.max_solve_seconds)
    solver.parameters.num_search_workers = int(config.num_workers)
    solver.parameters.random_seed = int(config.random_seed)
    solver.parameters.relative_gap_limit = 0.001
    solver.parameters.log_search_progress = False

    status_code = solver.Solve(model)
    solve_ms = max(1, int((time.perf_counter() - t0) * 1000))

    status_map = {
        cp_model.OPTIMAL: "OPTIMAL",
        cp_model.FEASIBLE: "FEASIBLE",
        cp_model.INFEASIBLE: "INFEASIBLE",
        cp_model.MODEL_INVALID: "MODEL_INVALID",
        cp_model.UNKNOWN: "UNKNOWN",
    }
    status_str = status_map.get(status_code, "UNKNOWN")

    solver_params = {
        "max_time_in_seconds": config.max_solve_seconds,
        "num_search_workers": config.num_workers,
        "random_seed": config.random_seed,
        "horizon_hrs": ph.horizon_hrs,
        "horizon_mins": horizon_mins,
        "scarce_resins": sorted(scarce_resins),
    }

    if status_code not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        # Fallback safely to FIFO baseline plan if extreme scenario hit solver timeout/infeasibility
        return baseline_plan, status_str, solve_ms, 0.0, 0.0, 0.0, solver_params

    raw_assignments: list[dict] = []
    for i, o in enumerate(orders):
        is_sch = bool(solver.Value(scheduled[i]))
        if not is_sch:
            raw_assignments.append(
                {
                    "order_id": o.order_id,
                    "scheduled": False,
                    "unscheduled_reason": f"Unscheduled due to {o.resin_code} virgin resin shortage cap",
                }
            )
            continue

        chosen_mid = next(
            (mid for mid in compat_press_ids[i] if solver.Value(pres_vars[(i, mid)]) == 1),
            compat_press_ids[i][0],
        )
        raw_assignments.append(
            {
                "order_id": o.order_id,
                "scheduled": True,
                "machine_id": chosen_mid,
                "start_min": int(solver.Value(start_vars[i])),
                "end_min": int(solver.Value(end_vars[i])),
                "virgin_kg": round(solver.Value(virgin_10_vars[i]) / 10.0, 2),
                "regrind_kg": round(solver.Value(regrind_10_vars[i]) / 10.0, 2),
            }
        )

    mold_pm_windows: list[ScheduledMoldPm] = []
    if config.autonomous_pm_window:
        for mid_mold, (pm_s, pm_e, pm_hrs, pm_reason, pm_dl_hr) in pm_start_vars.items():
            mold = molds_by_id[mid_mold]
            mold_pm_windows.append(
                ScheduledMoldPm(
                    mold_id=mid_mold,
                    mold_name=mold.name,
                    machine_id=mold.compatible_machines[0] if mold.compatible_machines else presses[0].machine_id,
                    start_min=int(solver.Value(pm_s)),
                    end_min=int(solver.Value(pm_e)),
                    duration_hrs=pm_hrs,
                    mode="autonomous",
                    trigger_reason=pm_reason,
                    deadline_hr=pm_dl_hr,
                )
            )

    opt_plan = build_schedule_plan(
        dataset,
        config,
        raw_assignments,
        mold_pm_durations_hrs,
        mold_pm_windows=mold_pm_windows or None,
    )
    obj_val = round(float(solver.ObjectiveValue()), 2)
    best_bound = round(float(solver.BestObjectiveBound()), 2)
    gap_pct = round(abs(obj_val - best_bound) / max(abs(obj_val), 1.0) * 100.0, 2) if status_code == cp_model.FEASIBLE else 0.0

    return opt_plan, status_str, solve_ms, obj_val, best_bound, gap_pct, solver_params


def solve_plant_schedule(dataset: PlantDataset, config: SolverConfig) -> SolveResult:
    """Full deterministic Mini-DIOS Plastics optimization pipeline:
    1. Validate raw dataset + scenarios (`validate_plant_data`).
    2. Apply composable scenarios (`apply_plant_scenarios`).
    3. Run Naive FIFO Baseline Scheduler (`run_fifo_baseline`).
    4. Run OR-Tools CP-SAT Solver (`_solve_cpsat_model`).
    5. Verify all 6 Hard Constraints independently on both plans.
    6. Compute side-by-side ROI Scorecard & cryptographic SHA-256 audit hashes.
    """
    validation = validate_plant_data(dataset, config)
    if not validation.ready:
        raise DatasetValidationError(validation)

    eff_state = apply_plant_scenarios(dataset, config)
    eff_ds = eff_state.dataset
    pm_map = eff_state.mold_pm_durations_hrs

    # Dynamic horizon driven by PlantPhysicsConfig.horizon_hrs with extended scheduling tail
    # so extreme breakdowns or rush orders stay schedulable and accurately penalized.
    molds_by_id = {m.mold_id: m for m in eff_ds.molds}
    total_dur = sum(order_duration_mins(o, molds_by_id[o.mold_id]) for o in eff_ds.orders)
    total_bd = sum(
        int(round((dw.end_hr - dw.start_hr) * 60))
        for p in eff_ds.presses
        for dw in p.downtime_windows
    )
    base_horizon_mins = config.physics.horizon_hrs * 60
    min_tail_mins = EXTENDED_HORIZON_MINS if config.physics.horizon_hrs == 168 else int(round(base_horizon_mins * 1.5))
    horizon_mins = max(base_horizon_mins, min_tail_mins, total_dur + total_bd + 2880)

    baseline_plan = run_fifo_baseline(eff_ds, config, pm_map, horizon_mins)
    opt_plan, status_str, solve_ms, obj_val, best_bound, gap_pct, solver_params = _solve_cpsat_model(
        eff_ds, config, pm_map, eff_state.mold_pm_reasons, horizon_mins, baseline_plan
    )

    scorecard = build_scorecard(baseline_plan, opt_plan, config)
    # Coupled floor-workforce CP-SAT: demand is derived from the solved Press Gantt above.
    workforce = solve_workforce(eff_ds, config, opt_plan)
    financials = compute_financial_report(eff_ds, config, baseline_plan, opt_plan, workforce)
    risk_radar = compute_risk_radar(eff_ds, config, opt_plan, workforce)
    opt_checks = verify_hard_constraints(eff_ds, config, opt_plan, pm_map)
    base_checks = verify_hard_constraints(eff_ds, config, baseline_plan, pm_map)
    all_passed = all(c.passed for c in opt_checks)

    inputs_canonical = json.dumps(
        {"dataset": dataset.model_dump(mode="json"), "config": config.model_dump(mode="json")},
        sort_keys=True,
    )
    schedule_canonical = json.dumps(
        [
            (j.order_id, j.machine_id, j.start_min, j.end_min, j.virgin_kg, j.regrind_kg)
            for j in opt_plan.jobs
        ],
        sort_keys=True,
    )
    inputs_sha = hashlib.sha256(inputs_canonical.encode("utf-8")).hexdigest()
    schedule_sha = hashlib.sha256(schedule_canonical.encode("utf-8")).hexdigest()

    run_id = f"PL-{uuid.uuid4().hex[:8].upper()}"
    created_at = datetime.now(timezone.utc).isoformat()

    audit = AuditRecord(
        inputs_sha256=inputs_sha,
        schedule_sha256=schedule_sha,
        weights={
            "w_changeover_scrap": config.w_changeover_scrap,
            "w_otif": config.w_otif,
            "w_energy_cost": config.w_energy_cost,
            "w_working_capital": config.w_working_capital,
        },
        config=config,
        solver_params=solver_params,
        ortools_version=getattr(ortools, "__version__", "unknown"),
        constraints_verified=opt_checks,
        baseline_constraints_verified=base_checks,
        all_hard_constraints_passed=all_passed,
    )

    return SolveResult(
        run_id=run_id,
        created_at=created_at,
        dataset_name=dataset.name,
        currency=config.currency,
        fx_egp_per_sar=config.fx_egp_per_sar,
        status=status_str,  # type: ignore[arg-type]
        solve_time_ms=solve_ms,
        objective=obj_val,
        best_bound=best_bound,
        gap_pct=gap_pct,
        validation=validation,
        applied_scenarios=eff_state.applied_scenarios,
        optimized=opt_plan,
        baseline=baseline_plan,
        scorecard=scorecard,
        financials=financials,
        audit=audit,
        workforce=workforce,
        risk_radar=risk_radar,
    )
