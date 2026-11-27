"""Independent Post-Solve Universal Execution Model (UEM) Verifier (`uem_verify.py`).

Independently checks any `UEMSolution` against the 6 primitives of a `UEMGraph` with zero
solver trust and zero domain-specific logic:
  - UEM-P1: Primary Resource Compatibility & Active Status
  - UEM-P2: Unary Primary Resource Non-Overlap & Blocked/Blackout Window Exclusion
  - UEM-P3: Secondary Shared Resource Exclusivity Across Primary Resources
  - UEM-P4: Asymmetric Sequence-Dependent Transition & Setup Gap Verification
  - UEM-P5: Release Floor, Secondary Consumable Split Safety & Consumable Pool Cap
  - UEM-P6: Synchronization Group & Maintenance Cycle-Budget Verification
"""
from __future__ import annotations

from collections import defaultdict

from .uem import (
    TransitionEntry,
    UEMGraph,
    UEMScheduledActivity,
    UEMSolution,
    UEMVerificationCheck,
)


def verify_uem_solution(graph: UEMGraph, solution: UEMSolution) -> list[UEMVerificationCheck]:
    """Deterministically verify all 6 UEM primitive invariants on a `UEMSolution`."""
    res_by_id = {r.resource_id: r for r in graph.resources}
    act_by_id = {a.activity_id: a for a in graph.activities}
    trans_lookup: dict[tuple[str, str], TransitionEntry] = {
        (e.from_activity_id, e.to_activity_id): e for e in graph.transitions.entries
    }

    scheduled: list[UEMScheduledActivity] = [a for a in solution.activities if a.scheduled]

    # ------------------------------------------------------------------
    # UEM-P1: Primary Resource Compatibility & Active Status
    # ------------------------------------------------------------------
    p1_v: list[str] = []
    for sa in scheduled:
        spec = act_by_id.get(sa.activity_id)
        if spec is None:
            p1_v.append(f"Unknown activity_id '{sa.activity_id}' in solution")
            continue
        if sa.primary_resource_id not in spec.compatible_primary_ids:
            p1_v.append(
                f"{sa.activity_id}: primary resource {sa.primary_resource_id} not in compatible list"
            )
            continue
        res = res_by_id.get(sa.primary_resource_id or "")
        if res is None or not res.active:
            p1_v.append(f"{sa.activity_id}: primary resource {sa.primary_resource_id} is inactive or missing")

    # ------------------------------------------------------------------
    # UEM-P2: Unary Primary Resource Non-Overlap & Blocked Window Exclusion
    # ------------------------------------------------------------------
    p2_v: list[str] = []
    by_primary: dict[str, list[UEMScheduledActivity]] = defaultdict(list)
    for sa in scheduled:
        if sa.primary_resource_id:
            by_primary[sa.primary_resource_id].append(sa)

    for rid, jobs in by_primary.items():
        jobs.sort(key=lambda x: (x.start_min, x.end_min))
        res = res_by_id.get(rid)
        for idx in range(1, len(jobs)):
            prev_j, cur_j = jobs[idx - 1], jobs[idx]
            if cur_j.setup_start_min < prev_j.end_min:
                p2_v.append(
                    f"Resource {rid}: {cur_j.activity_id} busy start {cur_j.setup_start_min}m < {prev_j.activity_id} end {prev_j.end_min}m"
                )
        if res is not None:
            for j in jobs:
                for bw in res.blocked_windows:
                    if min(j.end_min, bw.end_min) > max(j.setup_start_min, bw.start_min):
                        p2_v.append(
                            f"Resource {rid}: {j.activity_id} [{j.setup_start_min}..{j.end_min}m] overlaps blocked window [{bw.start_min}..{bw.end_min}m] ({bw.label})"
                        )
        if graph.transitions.setup_blackout_windows:
            for j in jobs:
                if j.setup_mins > 0:
                    for sbw in graph.transitions.setup_blackout_windows:
                        if min(j.start_min, sbw.end_min) > max(j.setup_start_min, sbw.start_min):
                            p2_v.append(
                                f"Resource {rid}: {j.activity_id} setup [{j.setup_start_min}..{j.start_min}m] overlaps setup blackout [{sbw.start_min}..{sbw.end_min}m]"
                            )

    # ------------------------------------------------------------------
    # UEM-P3: Secondary Shared Resource Exclusivity Across Primary Resources
    # ------------------------------------------------------------------
    p3_v: list[str] = []
    by_secondary: dict[str, list[UEMScheduledActivity]] = defaultdict(list)
    for sa in scheduled:
        if sa.secondary_resource_id:
            by_secondary[sa.secondary_resource_id].append(sa)

    for srid, jobs in by_secondary.items():
        jobs.sort(key=lambda x: (x.start_min, x.end_min))
        for idx in range(1, len(jobs)):
            prev_j, cur_j = jobs[idx - 1], jobs[idx]
            if cur_j.start_min < prev_j.end_min:
                p3_v.append(
                    f"Secondary resource {srid}: concurrent run {prev_j.activity_id} (end {prev_j.end_min}m) & {cur_j.activity_id} (start {cur_j.start_min}m)"
                )

    # ------------------------------------------------------------------
    # UEM-P4: Asymmetric Sequence-Dependent Transition & Setup Gap
    # ------------------------------------------------------------------
    p4_v: list[str] = []
    for rid, jobs in by_primary.items():
        jobs.sort(key=lambda x: (x.start_min, x.end_min))
        for idx in range(1, len(jobs)):
            prev_j, cur_j = jobs[idx - 1], jobs[idx]
            t_entry = trans_lookup.get((prev_j.activity_id, cur_j.activity_id))
            req_setup = t_entry.setup_mins if t_entry else 0
            actual_gap = cur_j.start_min - prev_j.end_min
            if actual_gap < req_setup:
                p4_v.append(
                    f"Resource {rid}: {prev_j.activity_id}->{cur_j.activity_id} gap {actual_gap}m < required transition setup {req_setup}m"
                )

    # ------------------------------------------------------------------
    # UEM-P5: Release Floor, Secondary Split Quota & Consumable Pool Caps
    # ------------------------------------------------------------------
    p5_v: list[str] = []
    pri_used_10: dict[str, int] = defaultdict(int)
    sec_used_10: dict[str, int] = defaultdict(int)

    for sa in scheduled:
        spec = act_by_id.get(sa.activity_id)
        if spec is None:
            continue
        pool_res = res_by_id.get(spec.consumable_pool_id or "")
        lead_floor = pool_res.lead_time_floor_mins if pool_res else spec.earliest_start_min
        if sa.start_min < lead_floor:
            p5_v.append(
                f"{sa.activity_id}: start {sa.start_min}m violates release/lead-time floor {lead_floor}m"
            )
        if spec.max_secondary_consumable_units_10 <= 0 and sa.secondary_consumable_units_10 > 0:
            p5_v.append(
                f"{sa.activity_id}: assigned {sa.secondary_consumable_units_10 / 10.0:.1f} secondary consumable units when max allowed is 0"
            )
        if spec.consumable_pool_id:
            pri_used_10[spec.consumable_pool_id] += sa.primary_consumable_units_10 + sa.transition_waste_units_10
            sec_used_10[spec.consumable_pool_id] += sa.secondary_consumable_units_10

    for env in graph.cumulative_envelopes:
        if env.kind == "consumable_cap" and env.resource_id:
            pid = env.resource_id
            if pri_used_10[pid] > env.primary_cap_units_10 + 5:
                p5_v.append(
                    f"Consumable pool {pid}: primary usage {pri_used_10[pid] / 10.0:.1f} exceeds cap {env.primary_cap_units_10 / 10.0:.1f}"
                )
            if sec_used_10[pid] > env.secondary_cap_units_10 + 5:
                p5_v.append(
                    f"Consumable pool {pid}: secondary usage {sec_used_10[pid] / 10.0:.1f} exceeds cap {env.secondary_cap_units_10 / 10.0:.1f}"
                )

    # ------------------------------------------------------------------
    # UEM-P6: Synchronization Group & Maintenance Cycle-Budget Verification
    # ------------------------------------------------------------------
    p6_v: list[str] = []
    maint_by_gid = {mw.group_id: mw for mw in solution.maintenance_windows}
    for sg in graph.sync_groups:
        if sg.kind not in ("fixed_maintenance", "floating_maintenance") or not sg.resource_id:
            continue
        req_mins = sg.maintenance_duration_mins
        if req_mins <= 0:
            continue
        srid = sg.resource_id
        mw = maint_by_gid.get(sg.group_id)
        if mw is not None and mw.mode == "autonomous":
            if (mw.end_min - mw.start_min) < req_mins:
                p6_v.append(
                    f"Resource {srid}: autonomous maintenance {mw.end_min - mw.start_min}m < required {req_mins}m"
                )
            cycles_before = 0
            for j in by_secondary.get(srid, []):
                if min(j.end_min, mw.end_min) > max(j.start_min, mw.start_min):
                    p6_v.append(
                        f"Resource {srid}: {j.activity_id} [{j.start_min}..{j.end_min}m] overlaps maintenance [{mw.start_min}..{mw.end_min}m]"
                    )
                if j.end_min <= mw.start_min:
                    spec = act_by_id.get(j.activity_id)
                    if spec is not None:
                        cycles_before += spec.usage_cycles
            if sg.max_cycles_before_maintenance is not None and cycles_before > sg.max_cycles_before_maintenance:
                p6_v.append(
                    f"Resource {srid}: {cycles_before:,} cycles scheduled before maintenance exceeds budget {sg.max_cycles_before_maintenance:,}"
                )
        else:
            for j in by_secondary.get(srid, []):
                if j.start_min < req_mins:
                    p6_v.append(
                        f"Resource {srid}: {j.activity_id} starts at {j.start_min}m before {req_mins}m fixed maintenance finishes"
                    )

    return [
        UEMVerificationCheck(
            primitive_id="UEM-P1",
            name="Primary Resource Compatibility & Active Status",
            passed=len(p1_v) == 0,
            violations=len(p1_v),
            details=p1_v[:5],
        ),
        UEMVerificationCheck(
            primitive_id="UEM-P2",
            name="Unary Primary Resource Non-Overlap & Blocked Window Exclusion",
            passed=len(p2_v) == 0,
            violations=len(p2_v),
            details=p2_v[:5],
        ),
        UEMVerificationCheck(
            primitive_id="UEM-P3",
            name="Secondary Shared Resource Exclusivity Across Primary Resources",
            passed=len(p3_v) == 0,
            violations=len(p3_v),
            details=p3_v[:5],
        ),
        UEMVerificationCheck(
            primitive_id="UEM-P4",
            name="Asymmetric Sequence-Dependent Transition & Setup Gap",
            passed=len(p4_v) == 0,
            violations=len(p4_v),
            details=p4_v[:5],
        ),
        UEMVerificationCheck(
            primitive_id="UEM-P5",
            name="Release Floor, Secondary Split Quota & Consumable Pool Caps",
            passed=len(p5_v) == 0,
            violations=len(p5_v),
            details=p5_v[:5],
        ),
        UEMVerificationCheck(
            primitive_id="UEM-P6",
            name="Synchronization Group & Maintenance Cycle-Budget Verification",
            passed=len(p6_v) == 0,
            violations=len(p6_v),
            details=p6_v[:5],
        ),
    ]
