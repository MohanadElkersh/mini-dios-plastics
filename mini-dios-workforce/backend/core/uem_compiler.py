"""Universal Execution Model (UEM) — Deterministic OR-Tools CP-SAT Compiler.

Compiles any domain-agnostic 6-primitive `UEMGraph` into an OR-Tools `cp_model.CpModel`
and returns a `UEMSolution`. Zero domain-specific vocabulary or logic lives here.
"""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Optional

from ortools.sat.python import cp_model

from .uem import (
    ActivityNode,
    TransitionEntry,
    UEMGraph,
    UEMScheduledActivity,
    UEMScheduledMaintenance,
    UEMSolution,
)


def compile_and_solve_uem(graph: UEMGraph) -> UEMSolution:
    """Compile a 6-primitive `UEMGraph` into OR-Tools CP-SAT and solve deterministically."""
    t0 = time.perf_counter()
    model = cp_model.CpModel()

    horizon_mins = graph.horizon_mins
    activities = graph.activities
    n_acts = len(activities)
    act_idx_by_id = {a.activity_id: idx for idx, a in enumerate(activities)}

    primary_resources = [r for r in graph.resources if r.kind == "primary_unary"]
    secondary_resources = [r for r in graph.resources if r.kind == "secondary_exclusive"]

    # Build fast lookup for TransitionMatrix entries
    trans_lookup: dict[tuple[str, str], TransitionEntry] = {
        (e.from_activity_id, e.to_activity_id): e for e in graph.transitions.entries
    }
    max_setup = max(360, int(graph.transitions.max_possible_setup_mins))

    # ------------------------------------------------------------------
    # Primitive 2: ActivityNode Decision Variables
    # ------------------------------------------------------------------
    scheduled: list[cp_model.IntVar] = []
    start_vars: list[cp_model.IntVar] = []
    start_lbs: list[int] = []
    end_vars: list[cp_model.IntVar] = []
    setup_vars: list[cp_model.IntVar] = []
    busy_start_vars: list[cp_model.IntVar] = []
    busy_size_vars: list[cp_model.IntVar] = []
    tardiness_vars: list[cp_model.IntVar] = []
    earliness_vars: list[cp_model.IntVar] = []
    pri_cons_vars: list[cp_model.IntVar] = []
    sec_cons_vars: list[cp_model.IntVar] = []

    pres_vars: dict[tuple[int, str], cp_model.IntVar] = {}
    primary_to_acts: dict[str, list[int]] = defaultdict(list)
    secondary_intervals: dict[str, list[cp_model.IntervalVar]] = defaultdict(list)
    secondary_to_acts: dict[str, list[int]] = defaultdict(list)

    for i, act in enumerate(activities):
        dur = act.duration_mins
        if act.optional:
            sch = model.NewBoolVar(f"sch_{i}")
        else:
            sch = model.NewConstant(1)
        scheduled.append(sch)

        lb = min(act.earliest_start_min, max(0, horizon_mins - dur))
        s_var = model.NewIntVar(lb, horizon_mins - dur, f"start_{i}")
        e_var = model.NewIntVar(lb + dur, horizon_mins, f"end_{i}")
        model.Add(e_var == s_var + dur)

        stp_var = model.NewIntVar(0, max_setup, f"setup_{i}")
        b_start = model.NewIntVar(0, horizon_mins - dur, f"bstart_{i}")
        b_size = model.NewIntVar(dur, dur + max_setup, f"bsize_{i}")
        model.Add(b_start + stp_var == s_var)
        model.Add(b_size == dur + stp_var)

        tard = model.NewIntVar(0, horizon_mins, f"tard_{i}")
        early = model.NewIntVar(0, max(act.due_min, 1), f"early_{i}")
        model.Add(tard >= e_var - act.due_min).OnlyEnforceIf(sch)
        model.Add(early >= act.earliness_ref_min - e_var).OnlyEnforceIf(sch)

        gross_10 = act.gross_consumable_units_10
        max_sec_10 = min(gross_10, act.max_secondary_consumable_units_10)
        pc = model.NewIntVar(0, gross_10, f"pcons_{i}")
        sc = model.NewIntVar(0, max_sec_10, f"scons_{i}")
        if act.optional:
            model.Add(pc + sc == gross_10).OnlyEnforceIf(sch)
            model.Add(pc == 0).OnlyEnforceIf(sch.Not())
            model.Add(sc == 0).OnlyEnforceIf(sch.Not())
        else:
            model.Add(pc + sc == gross_10)

        start_vars.append(s_var)
        start_lbs.append(lb)
        end_vars.append(e_var)
        setup_vars.append(stp_var)
        busy_start_vars.append(b_start)
        busy_size_vars.append(b_size)
        tardiness_vars.append(tard)
        earliness_vars.append(early)
        pri_cons_vars.append(pc)
        sec_cons_vars.append(sc)

        # Primary resource assignment (Primitive 1 + Primitive 2)
        p_bools = []
        for rid in act.compatible_primary_ids:
            pv = model.NewBoolVar(f"pres_{i}_{rid}")
            pres_vars[(i, rid)] = pv
            primary_to_acts[rid].append(i)
            p_bools.append(pv)
        if p_bools:
            model.Add(sum(p_bools) == sch)
        else:
            model.Add(sch == 0)

        # Secondary shared resource exclusivity interval
        if act.secondary_resource_id:
            s_rid = act.secondary_resource_id
            if act.optional:
                s_iv = model.NewOptionalIntervalVar(s_var, dur, e_var, sch, f"sec_iv_{i}")
            else:
                s_iv = model.NewIntervalVar(s_var, dur, e_var, f"sec_iv_{i}")
            secondary_intervals[s_rid].append(s_iv)
            secondary_to_acts[s_rid].append(i)

    # ------------------------------------------------------------------
    # Primitive 5 (Part A): Secondary Resource Exclusivity & Maintenance Sync
    # ------------------------------------------------------------------
    maint_vars: dict[str, tuple[cp_model.IntVar, cp_model.IntVar, int, str, Optional[int], str]] = {}
    pm_tiebreak_terms = []

    for sg in graph.sync_groups:
        if sg.kind == "fixed_maintenance" and sg.resource_id and sg.maintenance_duration_mins > 0:
            s_rid = sg.resource_id
            m_mins = sg.maintenance_duration_mins
            secondary_intervals[s_rid].append(
                model.NewFixedSizeIntervalVar(0, m_mins, f"fixed_maint_{sg.group_id}")
            )
        elif sg.kind == "floating_maintenance" and sg.resource_id and sg.maintenance_duration_mins > 0:
            s_rid = sg.resource_id
            m_mins = sg.maintenance_duration_mins
            dl_min = sg.maintenance_deadline_min if sg.maintenance_deadline_min > 0 else horizon_mins
            if sg.force_start_at_zero:
                pm_s = model.NewConstant(0)
                pm_e = model.NewConstant(m_mins)
                eff_dl = m_mins
            else:
                eff_dl = min(horizon_mins, max(m_mins, dl_min))
                pm_s = model.NewIntVar(0, max(0, eff_dl - m_mins), f"pm_start_{s_rid}")
                pm_e = model.NewIntVar(m_mins, max(m_mins, eff_dl), f"pm_end_{s_rid}")
                model.Add(pm_e == pm_s + m_mins)
                model.AddHint(pm_s, 0)
                pm_tiebreak_terms.append(pm_s)

            secondary_intervals[s_rid].append(
                model.NewFixedSizeIntervalVar(pm_s, m_mins, f"float_maint_{sg.group_id}")
            )
            maint_vars[sg.group_id] = (pm_s, pm_e, m_mins, sg.trigger_reason, eff_dl, s_rid)

            if sg.max_cycles_before_maintenance is not None:
                rem_cycles = max(0, int(sg.max_cycles_before_maintenance))
                s_act_idxs = secondary_to_acts.get(s_rid, [])
                if s_act_idxs:
                    cycles_before_terms = []
                    for o_idx in s_act_idxs:
                        bp = model.NewBoolVar(f"before_maint_{s_rid}_{o_idx}")
                        model.Add(end_vars[o_idx] <= pm_s).OnlyEnforceIf(bp)
                        model.Add(start_vars[o_idx] >= pm_e).OnlyEnforceIf(bp.Not())
                        if activities[o_idx].optional:
                            model.Add(bp <= scheduled[o_idx])
                        cycles_before_terms.append(activities[o_idx].usage_cycles * bp)
                    model.Add(sum(cycles_before_terms) <= rem_cycles)

    for s_res in secondary_resources:
        s_ivs = secondary_intervals.get(s_res.resource_id, [])
        if len(s_ivs) >= 2:
            model.AddNoOverlap(s_ivs)

    # ------------------------------------------------------------------
    # Primitive 1 & 3: Primary Unary Resource NoOverlap + AddCircuit Transitions
    # ------------------------------------------------------------------
    transition_waste_terms_10: dict[str, list] = defaultdict(list)
    total_setup_mins_terms = []
    total_transition_waste_cost_cents_terms = []
    setup_blackouts = graph.transitions.setup_blackout_windows
    idle_vars: dict[str, cp_model.IntVar] = {}
    arc_vars: dict[tuple[str, int, int], cp_model.IntVar] = {}

    for p_res in primary_resources:
        rid = p_res.resource_id
        o_indices = primary_to_acts.get(rid, [])
        if not o_indices:
            continue

        res_ivs: list[cp_model.IntervalVar] = []
        setup_ivs_for_blackout: list[cp_model.IntervalVar] = []
        for i in o_indices:
            pv = pres_vars[(i, rid)]
            res_ivs.append(
                model.NewOptionalIntervalVar(
                    busy_start_vars[i], busy_size_vars[i], end_vars[i], pv, f"piv_{rid}_{i}"
                )
            )
            if setup_blackouts:
                setup_ivs_for_blackout.append(
                    model.NewOptionalIntervalVar(
                        busy_start_vars[i], setup_vars[i], start_vars[i], pv, f"siv_{rid}_{i}"
                    )
                )

        for w_idx, bw in enumerate(p_res.blocked_windows):
            if bw.end_min > bw.start_min:
                res_ivs.append(
                    model.NewFixedSizeIntervalVar(
                        bw.start_min, bw.end_min - bw.start_min, f"bw_{rid}_{w_idx}"
                    )
                )

        model.AddNoOverlap(res_ivs)

        if setup_blackouts and setup_ivs_for_blackout:
            blk_ivs = [
                model.NewFixedSizeIntervalVar(
                    bw.start_min, bw.end_min - bw.start_min, f"sblk_{rid}_{idx}"
                )
                for idx, bw in enumerate(setup_blackouts)
                if bw.end_min > bw.start_min
            ]
            if blk_ivs:
                model.AddNoOverlap(setup_ivs_for_blackout + blk_ivs)

        # AddCircuit for sequence-dependent transitions on unary resource `rid`
        arcs: list[tuple[int, int, cp_model.IntVar]] = []
        idle_r = model.NewBoolVar(f"idle_{rid}")
        idle_vars[rid] = idle_r
        arcs.append((0, 0, idle_r))
        any_on_res = [pres_vars[(i, rid)] for i in o_indices]
        model.Add(sum(any_on_res) == 0).OnlyEnforceIf(idle_r)
        model.Add(sum(any_on_res) >= 1).OnlyEnforceIf(idle_r.Not())

        for pos_i, i in enumerate(o_indices, start=1):
            pv_i = pres_vars[(i, rid)]
            arcs.append((pos_i, pos_i, pv_i.Not()))

            a_0_i = model.NewBoolVar(f"arc_{rid}_0_{i}")
            arc_vars[(rid, -1, i)] = a_0_i
            arcs.append((0, pos_i, a_0_i))
            model.Add(setup_vars[i] == 0).OnlyEnforceIf(a_0_i)

            a_i_0 = model.NewBoolVar(f"arc_{rid}_{i}_0")
            arc_vars[(rid, i, -1)] = a_i_0
            arcs.append((pos_i, 0, a_i_0))

            act_i = activities[i]
            for pos_j, j in enumerate(o_indices, start=1):
                if i == j:
                    continue
                act_j = activities[j]
                t_entry = trans_lookup.get((act_i.activity_id, act_j.activity_id))
                stp_m = t_entry.setup_mins if t_entry else 0
                waste_10 = t_entry.consumable_waste_units_10 if t_entry else 0
                waste_cost_cents = t_entry.transition_Waste_cost_cents if t_entry else 0
                pool_id = (t_entry.consumable_pool_id if t_entry else None) or act_j.consumable_pool_id

                a_ij = model.NewBoolVar(f"arc_{rid}_{i}_{j}")
                arc_vars[(rid, i, j)] = a_ij
                arcs.append((pos_i, pos_j, a_ij))

                model.Add(busy_start_vars[j] >= end_vars[i]).OnlyEnforceIf(a_ij)
                model.Add(setup_vars[j] == stp_m).OnlyEnforceIf(a_ij)

                if stp_m > 0:
                    total_setup_mins_terms.append(stp_m * a_ij)
                if waste_10 > 0 and pool_id:
                    transition_waste_terms_10[pool_id].append(waste_10 * a_ij)
                if waste_cost_cents > 0:
                    total_transition_waste_cost_cents_terms.append(waste_cost_cents * a_ij)

        model.AddCircuit(arcs)

    # ------------------------------------------------------------------
    # Primitive 4: CumulativeEnvelope (CUMULATIVE_CAP)
    # ------------------------------------------------------------------
    tariff_overlap_terms = []
    shift_overflow_terms = []
    shift_overflow_vars: dict[str, cp_model.IntVar] = {}

    for env in graph.cumulative_envelopes:
        if env.kind == "consumable_cap" and env.resource_id:
            pool_id = env.resource_id
            pool_act_idxs = [i for i, a in enumerate(activities) if a.consumable_pool_id == pool_id]
            if pool_act_idxs:
                model.Add(
                    sum(pri_cons_vars[i] for i in pool_act_idxs)
                    + sum(transition_waste_terms_10.get(pool_id, []))
                    <= env.primary_cap_units_10
                )
                model.Add(
                    sum(sec_cons_vars[i] for i in pool_act_idxs)
                    <= env.secondary_cap_units_10
                )

        elif env.kind == "time_window_tariff" and env.window is not None:
            ps = env.window.start_min
            pe = env.window.end_min
            win_len = max(60, pe - ps)
            for i, act in enumerate(activities):
                if pe <= start_lbs[i] or ps >= horizon_mins:
                    continue
                surcharge = env.activity_surcharge_cents_per_min.get(
                    act.activity_id, env.surcharge_cents_per_min
                )
                if surcharge <= 0:
                    continue
                ps_const = model.NewConstant(ps)
                pe_const = model.NewConstant(pe)
                mx_s = model.NewIntVar(ps, horizon_mins, f"tws_{env.envelope_id}_{i}")
                mn_e = model.NewIntVar(0, pe, f"twe_{env.envelope_id}_{i}")
                model.AddMaxEquality(mx_s, [start_vars[i], ps_const])
                model.AddMinEquality(mn_e, [end_vars[i], pe_const])
                ov = model.NewIntVar(0, win_len, f"two_{env.envelope_id}_{i}")
                model.Add(ov >= mn_e - mx_s)
                tariff_overlap_terms.append(surcharge * ov)

        elif env.kind == "shift_capacity_cap" and env.window is not None:
            ws = env.window.start_min
            we = env.window.end_min
            if we <= ws or ws >= horizon_mins:
                continue
            # Count primary resources concurrently active during [ws, we)
            res_active_bools = []
            for p_res in primary_resources:
                rid = p_res.resource_id
                o_indices = primary_to_acts.get(rid, [])
                if not o_indices:
                    continue
                act_ov_bools = []
                for i in o_indices:
                    if start_lbs[i] >= we:
                        continue
                    # Activity i overlaps [ws, we) on resource rid if pres_vars[(i, rid)] and busy_start < we and end > ws
                    ov_b = model.NewBoolVar(f"sh_ov_{env.envelope_id}_{rid}_{i}")
                    # If activity i is assigned to rid and overlaps [ws, we), ov_b must be 1
                    b_after = model.NewBoolVar(f"sh_aft_{env.envelope_id}_{rid}_{i}")
                    b_before = model.NewBoolVar(f"sh_bef_{env.envelope_id}_{rid}_{i}")
                    model.Add(busy_start_vars[i] >= we).OnlyEnforceIf(b_after)
                    model.Add(busy_start_vars[i] <= we - 1).OnlyEnforceIf(b_after.Not())
                    model.Add(end_vars[i] <= ws).OnlyEnforceIf(b_before)
                    model.Add(end_vars[i] >= ws + 1).OnlyEnforceIf(b_before.Not())
                    # pres_vars[(i, rid)] AND NOT b_after AND NOT b_before => ov_b
                    model.AddBoolOr([pres_vars[(i, rid)].Not(), b_after, b_before, ov_b])
                    model.Add(ov_b <= pres_vars[(i, rid)])
                    act_ov_bools.append(ov_b)
                if act_ov_bools:
                    r_act = model.NewBoolVar(f"sh_res_{env.envelope_id}_{rid}")
                    for ob in act_ov_bools:
                        model.Add(r_act >= ob)
                    model.Add(r_act <= sum(act_ov_bools))
                    res_active_bools.append(r_act)

            if res_active_bools:
                cap = max(0, int(env.max_concurrent_activities))
                if env.soft_overflow_allowed:
                    max_ov = max(0, len(primary_resources) - cap)
                    ov_var = model.NewIntVar(0, max_ov, f"sh_overflow_{env.envelope_id}")
                    model.Add(sum(res_active_bools) <= cap + ov_var)
                    shift_overflow_vars[env.envelope_id] = ov_var
                    if env.soft_overflow_cost_cents_per_unit > 0:
                        shift_overflow_terms.append(env.soft_overflow_cost_cents_per_unit * ov_var)
                else:
                    model.Add(sum(res_active_bools) <= cap)

    # ------------------------------------------------------------------
    # Primitive 5 (Part B): Barrier Consolidation Synchronization Groups
    # ------------------------------------------------------------------
    cg_ship_vars: dict[str, cp_model.IntVar] = {}
    cg_wait_vars: dict[tuple[str, int], cp_model.IntVar] = {}
    cg_to_idxs: dict[str, list[int]] = {}
    barrier_wait_terms = []

    for sg in graph.sync_groups:
        if sg.kind != "barrier_consolidation":
            continue
        idxs = [act_idx_by_id[aid] for aid in sg.activity_ids if aid in act_idx_by_id]
        if len(idxs) < 2:
            continue
        cg_to_idxs[sg.group_id] = idxs
        cg_ship = model.NewIntVar(0, horizon_mins, f"cg_ship_{sg.group_id}")
        cg_ship_vars[sg.group_id] = cg_ship
        for i in idxs:
            aid = activities[i].activity_id
            model.Add(cg_ship >= end_vars[i]).OnlyEnforceIf(scheduled[i])
            wait_i = model.NewIntVar(0, horizon_mins, f"cg_wait_{sg.group_id}_{i}")
            cg_wait_vars[(sg.group_id, i)] = wait_i
            model.Add(wait_i >= cg_ship - end_vars[i]).OnlyEnforceIf(scheduled[i])
            wait_rate = sg.wait_holding_cents_per_min_by_activity.get(aid, 0)
            if wait_rate > 0:
                barrier_wait_terms.append(wait_rate * wait_i)

    # ------------------------------------------------------------------
    # Primitive 6: ObjectiveTermSpec Multi-Objective Assembly
    # ------------------------------------------------------------------
    obj = graph.objective
    setup_rate = graph.transitions.setup_downtime_cost_cents_per_min
    transition_expr = (
        sum(total_transition_waste_cost_cents_terms)
        + sum(setup_rate * t for t in total_setup_mins_terms)
    )

    timeliness_terms = []
    unscheduled_terms = []
    for i, act in enumerate(activities):
        timeliness_terms.append(act.tardiness_penalty_cents_per_min * tardiness_vars[i])
        if act.safety_buffer_mins > 0 and act.safety_buffer_penalty_cents_per_min > 0:
            safe_due_min = max(start_lbs[i] + act.duration_mins, act.due_min - act.safety_buffer_mins)
            if safe_due_min < act.due_min:
                buf_short = model.NewIntVar(0, act.safety_buffer_mins, f"sbuf_{i}")
                model.Add(buf_short >= end_vars[i] - safe_due_min).OnlyEnforceIf(scheduled[i])
                timeliness_terms.append(act.safety_buffer_penalty_cents_per_min * buf_short)
        if act.optional and act.unscheduled_penalty_cents > 0:
            unscheduled_terms.append(act.unscheduled_penalty_cents * (1 - scheduled[i]))
    timeliness_expr = sum(timeliness_terms) + sum(unscheduled_terms)

    oper_terms = []
    for i, act in enumerate(activities):
        for rid in act.compatible_primary_ids:
            key = f"{act.activity_id}::{rid}"
            cost_cents = obj.assignment_operating_cost_cents.get(key, 0)
            if cost_cents > 0:
                oper_terms.append(cost_cents * pres_vars[(i, rid)])
    operating_energy_expr = sum(oper_terms) + sum(tariff_overlap_terms)

    wc_terms = []
    for i, act in enumerate(activities):
        if act.consumable_pool_id:
            p_cost = obj.primary_consumable_cost_cents_per_unit_10.get(act.consumable_pool_id, 0)
            s_cost = obj.secondary_consumable_cost_cents_per_unit_10.get(act.consumable_pool_id, 0)
            wc_terms.append(p_cost * pri_cons_vars[i] + s_cost * sec_cons_vars[i])
        if act.earliness_holding_cents_per_min > 0:
            wc_terms.append(act.earliness_holding_cents_per_min * earliness_vars[i])
    wc_expr = sum(wc_terms) + sum(barrier_wait_terms)

    labor_env_expr = sum(shift_overflow_terms) if shift_overflow_terms else 0
    pm_tiebreak_expr = sum(pm_tiebreak_terms) if pm_tiebreak_terms else 0

    model.Minimize(
        obj.transition_weight_multiplier * transition_expr
        + obj.timeliness_weight_multiplier * timeliness_expr
        + obj.operating_energy_weight_multiplier * operating_energy_expr
        + obj.working_capital_weight_multiplier * wc_expr
        + obj.labor_envelope_weight_multiplier * labor_env_expr
        + pm_tiebreak_expr
    )

    # ------------------------------------------------------------------
    # Warm-Start Hints from Baseline Schedule
    # ------------------------------------------------------------------
    if graph.hints:
        hints_by_aid = {h.activity_id: h for h in graph.hints}
        hint_res_seq: dict[str, list[tuple[int, int]]] = defaultdict(list)
        for i, act in enumerate(activities):
            h = hints_by_aid.get(act.activity_id)
            is_h_sch = bool(h and h.scheduled and h.primary_resource_id and (i, h.primary_resource_id) in pres_vars)
            if act.optional:
                model.AddHint(scheduled[i], 1 if is_h_sch else 0)
            for rid in act.compatible_primary_ids:
                model.AddHint(pres_vars[(i, rid)], 1 if (is_h_sch and h.primary_resource_id == rid) else 0)
            if is_h_sch and h is not None and h.primary_resource_id is not None:
                s_hint = max(start_lbs[i], min(horizon_mins - act.duration_mins, int(h.start_min)))
                model.AddHint(start_vars[i], s_hint)
                max_sec_10 = min(act.gross_consumable_units_10, act.max_secondary_consumable_units_10)
                sc_hint = min(max_sec_10, max(0, int(h.secondary_consumable_units_10)))
                pc_hint = act.gross_consumable_units_10 - sc_hint
                model.AddHint(pri_cons_vars[i], pc_hint)
                model.AddHint(sec_cons_vars[i], sc_hint)
                hint_res_seq[h.primary_resource_id].append((s_hint, i))
            elif act.optional:
                model.AddHint(pri_cons_vars[i], 0)
                model.AddHint(sec_cons_vars[i], 0)

        for rid, idle_r in idle_vars.items():
            seq_pairs = sorted(hint_res_seq.get(rid, []), key=lambda x: (x[0], x[1]))
            seq = [idx for _, idx in seq_pairs]
            active_arcs: set[tuple[int, int]] = set()
            if not seq:
                model.AddHint(idle_r, 1)
            else:
                model.AddHint(idle_r, 0)
                active_arcs.add((-1, seq[0]))
                active_arcs.add((seq[-1], -1))
                for k in range(len(seq) - 1):
                    active_arcs.add((seq[k], seq[k + 1]))
            for (arid, u, v), avar in arc_vars.items():
                if arid == rid:
                    model.AddHint(avar, 1 if (u, v) in active_arcs else 0)

        for cg_id, cg_ship in cg_ship_vars.items():
            idxs = cg_to_idxs.get(cg_id, [])
            end_hints: dict[int, int] = {}
            for i in idxs:
                h = hints_by_aid.get(activities[i].activity_id)
                if h and h.scheduled:
                    s_h = max(start_lbs[i], min(horizon_mins - activities[i].duration_mins, int(h.start_min)))
                    end_hints[i] = s_h + activities[i].duration_mins
                else:
                    end_hints[i] = start_lbs[i] + activities[i].duration_mins
            ship_hint = max(end_hints.values()) if end_hints else 0
            model.AddHint(cg_ship, min(horizon_mins, ship_hint))
            for i in idxs:
                wait_var = cg_wait_vars.get((cg_id, i))
                if wait_var is not None:
                    model.AddHint(wait_var, max(0, min(horizon_mins, ship_hint - end_hints[i])))

    # ------------------------------------------------------------------
    # Execute CP-SAT Solver
    # ------------------------------------------------------------------
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(graph.max_solve_seconds)
    solver.parameters.num_search_workers = int(graph.num_workers)
    solver.parameters.random_seed = int(graph.random_seed)
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
        "engine": "uem_cpsat_v1",
        "max_time_in_seconds": graph.max_solve_seconds,
        "num_search_workers": graph.num_workers,
        "random_seed": graph.random_seed,
        "horizon_mins": horizon_mins,
        "base_horizon_mins": graph.base_horizon_mins,
        "primitive_counts": graph.primitive_counts(),
    }

    if status_code not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return UEMSolution(
            status=status_str,  # type: ignore[arg-type]
            solve_time_ms=solve_ms,
            objective_value=0.0,
            best_bound=0.0,
            gap_pct=0.0,
            activities=[],
            maintenance_windows=[],
            envelope_overflows={},
            solver_params=solver_params,
        )

    # Extract solved activities and their transition waste along active AddCircuit arcs
    solved_acts: list[UEMScheduledActivity] = []
    by_primary_seq: dict[str, list[tuple[int, int]]] = defaultdict(list)
    chosen_primary_by_idx: dict[int, str] = {}

    for i, act in enumerate(activities):
        is_sch = bool(solver.Value(scheduled[i]))
        if not is_sch:
            solved_acts.append(
                UEMScheduledActivity(
                    activity_id=act.activity_id,
                    scheduled=False,
                    secondary_resource_id=act.secondary_resource_id,
                    unscheduled_reason=act.attributes.get(
                        "unscheduled_reason_default",
                        f"Unscheduled due to {act.consumable_pool_id or 'resource'} capacity cap",
                    ),
                )
            )
            continue

        chosen_rid = next(
            (rid for rid in act.compatible_primary_ids if solver.Value(pres_vars[(i, rid)]) == 1),
            act.compatible_primary_ids[0],
        )
        chosen_primary_by_idx[i] = chosen_rid
        s_val = int(solver.Value(start_vars[i]))
        by_primary_seq[chosen_rid].append((s_val, i))

    waste_by_idx: dict[int, int] = defaultdict(int)
    for rid, pairs in by_primary_seq.items():
        pairs.sort(key=lambda x: (x[0], x[1]))
        for k in range(1, len(pairs)):
            prev_i = pairs[k - 1][1]
            cur_i = pairs[k][1]
            t_entry = trans_lookup.get((activities[prev_i].activity_id, activities[cur_i].activity_id))
            if t_entry:
                waste_by_idx[cur_i] = t_entry.consumable_waste_units_10

    solved_acts = []
    for i, act in enumerate(activities):
        is_sch = bool(solver.Value(scheduled[i]))
        if not is_sch:
            solved_acts.append(
                UEMScheduledActivity(
                    activity_id=act.activity_id,
                    scheduled=False,
                    secondary_resource_id=act.secondary_resource_id,
                    unscheduled_reason=act.attributes.get(
                        "unscheduled_reason_default",
                        f"Unscheduled due to {act.consumable_pool_id or 'resource'} capacity cap",
                    ),
                )
            )
            continue

        s_val = int(solver.Value(start_vars[i]))
        e_val = int(solver.Value(end_vars[i]))
        stp_val = int(solver.Value(setup_vars[i]))
        solved_acts.append(
            UEMScheduledActivity(
                activity_id=act.activity_id,
                scheduled=True,
                primary_resource_id=chosen_primary_by_idx[i],
                secondary_resource_id=act.secondary_resource_id,
                setup_start_min=s_val - stp_val,
                start_min=s_val,
                end_min=e_val,
                setup_mins=stp_val,
                primary_consumable_units_10=int(solver.Value(pri_cons_vars[i])),
                secondary_consumable_units_10=int(solver.Value(sec_cons_vars[i])),
                transition_waste_units_10=waste_by_idx.get(i, 0),
            )
        )

    maint_windows: list[UEMScheduledMaintenance] = []
    for gid, (pm_s, pm_e, m_mins, reason, dl_min, s_rid) in maint_vars.items():
        maint_windows.append(
            UEMScheduledMaintenance(
                group_id=gid,
                resource_id=s_rid,
                start_min=int(solver.Value(pm_s)),
                end_min=int(solver.Value(pm_e)),
                duration_mins=m_mins,
                mode="autonomous",
                trigger_reason=reason,
                deadline_min=dl_min,
            )
        )

    overflows = {
        env_id: int(solver.Value(ov_var))
        for env_id, ov_var in shift_overflow_vars.items()
        if solver.Value(ov_var) > 0
    }

    obj_val = round(float(solver.ObjectiveValue()), 2)
    best_bound = round(float(solver.BestObjectiveBound()), 2)
    gap_pct = (
        round(abs(obj_val - best_bound) / max(abs(obj_val), 1.0) * 100.0, 2)
        if status_code == cp_model.FEASIBLE
        else 0.0
    )

    return UEMSolution(
        status=status_str,  # type: ignore[arg-type]
        solve_time_ms=solve_ms,
        objective_value=obj_val,
        best_bound=best_bound,
        gap_pct=gap_pct,
        activities=solved_acts,
        maintenance_windows=maint_windows,
        envelope_overflows=overflows,
        solver_params=solver_params,
    )
