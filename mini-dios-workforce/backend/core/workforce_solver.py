"""Factory-floor workforce scheduling engine for Mini-DIOS Plastics (Tab 6).

Deterministic Google OR-Tools CP-SAT roster optimizer **coupled to the solved Press Gantt**:

1. `derive_demand`   - shift-by-shift required headcount per role from the Press Gantt
                       (active presses, mold changeovers / PM blocks, hygroscopic resin, load).
2. `solve_workforce` - CP-SAT roster with 5 hard constraints (role & certification, hour caps,
                       inter-shift rest gap, leave / sick / days-off lock, max one shift per day)
                       and a weighted objective (labor + overtime cost, coverage gaps, fairness).
3. `build_naive_roster` - Naive Static Rotation baseline (fixed shift per worker, fixed 6-day week)
                       that ignores press-load swings and mold-change peaks.
4. `verify_workforce` - independent re-check of the 5 hard constraints on any roster.

Conventions
-----------
* Day index 0..6 = Sun..Sat (same calendar as the Press Gantt; minute 0 = Sunday 00:00).
* Standard layout (8h): Morning 06-14, Afternoon 14-22, Night 22-06(+1). The shift belongs to the
  day it *starts* on. The Sun 00:00-06:00 stub is treated as carry-in and is not scheduled.
* Ramadan layout (6h): Night 00-06, Morning 06-12, Afternoon 12-18, Evening 18-24.
* Money: worker rates are stored in SAR; KPI money is returned in the active currency.
"""
from __future__ import annotations

import math
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from ortools.sat.python import cp_model

from .ontology import (
    DAYS,
    RAMADAN_MAX_WEEKLY_HOURS,
    RAMADAN_STANDARD_WEEKLY_HOURS,
    WORKER_ROLES,
    ConstraintCheck,
    FactoryWorker,
    GanttBlock,
    PlantDataset,
    SchedulePlan,
    ShiftDemandCell,
    SolverConfig,
    WorkerWeek,
    WorkforceCallout,
    WorkforceConfig,
    WorkforceKpis,
    WorkforcePlan,
    WorkforceResult,
    convert_sar_to_currency,
)

HYGROSCOPIC_RESINS = frozenset({"PET", "ABS"})
HIGH_LOAD_ACTIVE_PRESSES = 4
HORIZON_MINS_7D = DAYS * 24 * 60

# Objective unit prices in SAR-cents (so every term is an exact integer).
GAP_CENTS = 150_000  # one missing head-shift ~ SAR 1,500 of pain
CERT_GAP_CENTS = 90_000  # an active press with no certified operator
MISMATCH_CENTS = 15_000  # one shift outside the worker's preference
SPREAD_CENTS = 40_000  # one unit of night-shift spread (max - min) within a role
MOLD_TECH_CRITICALITY = 2

# CP-SAT search parameters (deterministic-time limits => reproducible results)
SOLVER_NUM_WORKERS = 8
DET_TIME_FACTOR = 1.5
REL_GAP = 0.01

DAY_LABELS = ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")
NON_WORK_LABELS = ("OFF", "LEAVE", "SICK")


# --------------------------------------------------------------------------------------------
# Shift layout & effective limits
# --------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class ShiftDef:
    name: str
    start_hr: int
    end_hr: int  # may exceed 24 for the standard Night shift

    @property
    def hours(self) -> int:
        return self.end_hr - self.start_hr

    @property
    def window_label(self) -> str:
        return f"{self.start_hr % 24:02d}:00-{self.end_hr % 24:02d}:00"


def shift_layout(config: SolverConfig) -> list[ShiftDef]:
    wf = config.workforce
    if config.ramadan_shift_mode or wf.shift_length_hrs == 6:
        return [
            ShiftDef("Night", 0, 6),
            ShiftDef("Morning", 6, 12),
            ShiftDef("Afternoon", 12, 18),
            ShiftDef("Evening", 18, 24),
        ]
    return [ShiftDef("Morning", 6, 14), ShiftDef("Afternoon", 14, 22), ShiftDef("Night", 22, 30)]


def effective_hour_limits(worker: FactoryWorker, config: SolverConfig) -> tuple[float, float]:
    """Return (weekly_hour_cap, standard_weekly_hours) after Ramadan clamping."""
    cap = float(worker.max_weekly_hours)
    std = float(config.workforce.standard_weekly_hours)
    if config.ramadan_shift_mode:
        cap = min(cap, float(RAMADAN_MAX_WEEKLY_HOURS))
        std = min(std, float(RAMADAN_STANDARD_WEEKLY_HOURS))
    return cap, min(std, cap)


def _pref_match(worker: FactoryWorker, shift_name: str) -> bool:
    if worker.preferred_shift == "Any":
        return True
    if shift_name == "Evening":
        return worker.preferred_shift == "Afternoon"
    return worker.preferred_shift == shift_name


def _certified(worker: FactoryWorker, press_ids: set[str] | frozenset[str]) -> bool:
    """True if the worker is certified on at least one press in `press_ids` (or `press_ids` is empty)."""
    if not press_ids:
        return True
    if worker.certified_machine_ids == "ALL":
        return True
    return bool(set(worker.certified_machine_ids) & set(press_ids))


def _certified_on(worker: FactoryWorker, press_id: str) -> bool:
    return worker.certified_machine_ids == "ALL" or press_id in worker.certified_machine_ids


# --------------------------------------------------------------------------------------------
# Demand derivation from the solved Press Gantt
# --------------------------------------------------------------------------------------------
@dataclass
class SlotDemand:
    day: int
    shift_idx: int
    shift: str
    active_presses: list[str]
    changeovers: int
    pm_blocks: int
    hygroscopic: bool
    required: dict[str, int]
    reasons: dict[str, list[str]]

    @property
    def mold_change(self) -> bool:
        return (self.changeovers + self.pm_blocks) > 0


def _overlaps(b: GanttBlock, w0: int, w1: int) -> bool:
    return b.start_min < w1 and b.end_min > w0


def derive_demand(
    plan: SchedulePlan, config: SolverConfig, layout: Optional[list[ShiftDef]] = None
) -> list[SlotDemand]:
    """Derive exact required headcount per (day, shift, role) from the solved Press Gantt."""
    layout = layout or shift_layout(config)
    ppo = max(1, config.workforce.presses_per_operator)
    blocks = [b for b in plan.gantt_blocks if b.block_type in ("production", "changeover", "mold_pm")]
    slots: list[SlotDemand] = []

    for d in range(DAYS):
        for si, sh in enumerate(layout):
            w0 = (d * 24 + sh.start_hr) * 60
            w1 = min((d * 24 + sh.end_hr) * 60, HORIZON_MINS_7D)
            active: set[str] = set()
            changeovers = 0
            pms = 0
            hygro = False
            if w1 > w0:
                for b in blocks:
                    if not _overlaps(b, w0, w1):
                        continue
                    if b.block_type in ("production", "changeover"):
                        active.add(b.machine_id)
                    if b.block_type == "changeover":
                        changeovers += 1
                    elif b.block_type == "mold_pm":
                        pms += 1
                    elif b.block_type == "production" and b.resin_code in HYGROSCOPIC_RESINS:
                        hygro = True
            n_act = len(active)
            required = {r: 0 for r in WORKER_ROLES}
            reasons: dict[str, list[str]] = {r: [] for r in WORKER_ROLES}

            if n_act > 0:
                required["Press_Operator"] = math.ceil(n_act / ppo)
                reasons["Press_Operator"].append(f"{n_act} active press(es) / {ppo} per operator")
                required["Shift_Supervisor"] = 1
                reasons["Shift_Supervisor"].append("1 per active operating shift")
                extra = n_act >= HIGH_LOAD_ACTIVE_PRESSES or hygro
                for role, why in (("QC_Inspector", "QC"), ("Material_Handler", "handling")):
                    required[role] = 1 + (1 if extra else 0)
                    reasons[role].append(f"press(es) running -> min 1 {why}")
                    if n_act >= HIGH_LOAD_ACTIVE_PRESSES:
                        reasons[role].append(f"high load ({n_act} presses) +1")
                    if hygro:
                        reasons[role].append("hygroscopic PET/ABS resin drying +1")
            n_events = changeovers + pms
            if n_events > 0:
                required["Mold_Technician"] = 2 if n_events >= 3 else 1
                if changeovers:
                    reasons["Mold_Technician"].append(f"{changeovers} mold changeover(s)")
                if pms:
                    reasons["Mold_Technician"].append(f"{pms} mold PM block(s)")

            slots.append(
                SlotDemand(
                    day=d,
                    shift_idx=si,
                    shift=sh.name,
                    active_presses=sorted(active),
                    changeovers=changeovers,
                    pm_blocks=pms,
                    hygroscopic=hygro,
                    required=required,
                    reasons=reasons,
                )
            )
    return slots


# --------------------------------------------------------------------------------------------
# Availability helpers
# --------------------------------------------------------------------------------------------
Assignments = dict[str, list[tuple[int, int]]]  # worker_id -> [(day, shift_idx), ...]


def worker_unavailable_label(
    worker: FactoryWorker, day: int, unavailable: dict[str, set[int]]
) -> Optional[str]:
    if worker.status == "sick":
        return "SICK"
    if worker.status == "on_leave":
        return "LEAVE"
    if day in worker.approved_leave_days:
        return "LEAVE"
    if day in unavailable.get(worker.worker_id, set()):
        return "SICK"
    return None


# --------------------------------------------------------------------------------------------
# Roster evaluation (shared by optimized & baseline so KPIs are apples-to-apples)
# --------------------------------------------------------------------------------------------
def evaluate_roster(
    assignments: Assignments,
    workers: list[FactoryWorker],
    slots: list[SlotDemand],
    layout: list[ShiftDef],
    config: SolverConfig,
    unavailable: dict[str, set[int]],
    violations: int = 0,
) -> WorkforcePlan:
    cur = config.currency
    fx = config.fx_egp_per_sar
    to_cur = lambda sar: convert_sar_to_currency(sar, cur, fx)
    shift_len = layout[0].hours

    rosters: list[WorkerWeek] = []
    reg_cost_sar = ot_cost_sar = 0.0
    reg_hours = ot_hours = 0.0
    total_assigned = 0
    matches = 0
    nights_by_role: dict[str, list[int]] = defaultdict(list)

    placed: dict[tuple[str, int, int], bool] = {}
    for w in workers:
        cells: list[str] = []
        by_day = {d: si for (d, si) in assignments.get(w.worker_id, [])}
        n_shifts = 0
        w_match = 0
        w_nights = 0
        for d in range(DAYS):
            lab = worker_unavailable_label(w, d, unavailable)
            if d in by_day and lab is None:
                sh = layout[by_day[d]]
                cells.append(sh.name)
                n_shifts += 1
                placed[(w.worker_id, d, by_day[d])] = True
                if _pref_match(w, sh.name):
                    w_match += 1
                if sh.name == "Night":
                    w_nights += 1
            else:
                cells.append(lab or "OFF")
        cap, std = effective_hour_limits(w, config)
        hours = float(n_shifts * shift_len)
        reg = min(hours, std)
        ot = max(0.0, hours - std)
        pay = w.hourly_rate * hours
        ot_prem = w.hourly_rate * (w.overtime_multiplier - 1.0) * ot
        reg_cost_sar += pay
        ot_cost_sar += ot_prem
        reg_hours += reg
        ot_hours += ot
        total_assigned += n_shifts
        matches += w_match
        if w.status == "active":
            nights_by_role[w.role].append(w_nights)
        rosters.append(
            WorkerWeek(
                worker_id=w.worker_id,
                name=w.name,
                role=w.role,
                cells=cells,
                shifts_worked=n_shifts,
                weekly_hours=round(hours, 1),
                regular_hours=round(reg, 1),
                overtime_hours=round(ot, 1),
                night_shifts=w_nights,
                labor_cost=round(to_cur(pay + ot_prem), 2),
                preference_matches=w_match,
            )
        )
        _ = cap

    by_id = {w.worker_id: w for w in workers}
    demand_cells: list[ShiftDemandCell] = []
    short_total = 0
    understaffed = 0
    req_total = 0
    filled_total = 0
    tech_slots = 0
    tech_ready = 0
    worst: Optional[tuple[int, str]] = None
    role_req: dict[str, int] = defaultdict(int)
    role_fill: dict[str, int] = defaultdict(int)

    assigned_by_slot: dict[tuple[int, int, str], list[FactoryWorker]] = defaultdict(list)
    for (wid, d, si) in placed:
        w = by_id[wid]
        assigned_by_slot[(d, si, w.role)].append(w)

    for s in slots:
        for role in WORKER_ROLES:
            req = s.required[role]
            ws = assigned_by_slot.get((s.day, s.shift_idx, role), [])
            uncertified: list[str] = []
            if role == "Press_Operator":
                eligible = [w for w in ws if _certified(w, frozenset(s.active_presses))]
                for pid in s.active_presses:
                    if not any(_certified_on(w, pid) for w in ws):
                        uncertified.append(pid)
            else:
                eligible = ws
            sched = len(eligible)
            if req == 0 and sched == 0:
                continue
            cell_short = max(0, req - sched)
            if req > 0:
                req_total += req
                filled_total += min(sched, req)
                role_req[role] += req
                role_fill[role] += min(sched, req)
                short_total += cell_short
                if cell_short > 0 or uncertified:
                    understaffed += 1
                    sev = cell_short * 10 + len(uncertified)
                    if worst is None or sev > worst[0]:
                        worst = (
                            sev,
                            f"{DAY_LABELS[s.day]} {s.shift} - {role.replace('_', ' ')} "
                            f"({sched}/{req})",
                        )
            if role == "Mold_Technician" and req > 0:
                tech_slots += 1
                if sched >= req:
                    tech_ready += 1
            demand_cells.append(
                ShiftDemandCell(
                    day=s.day,
                    shift=s.shift,
                    role=role,  # type: ignore[arg-type]
                    required=req,
                    scheduled=sched,
                    reasons=list(s.reasons[role]),
                    mold_change=s.mold_change,
                    active_presses=len(s.active_presses),
                    uncertified_presses=uncertified,
                )
            )

    spread = 0
    for _, nights in nights_by_role.items():
        if len(nights) >= 2:
            spread += max(nights) - min(nights)

    kpis = WorkforceKpis(
        regular_labor_cost=round(to_cur(reg_cost_sar), 2),
        overtime_cost=round(to_cur(ot_cost_sar), 2),
        total_labor_cost=round(to_cur(reg_cost_sar + ot_cost_sar), 2),
        regular_hours=round(reg_hours, 1),
        overtime_hours=round(ot_hours, 1),
        total_hours=round(reg_hours + ot_hours, 1),
        coverage_pct=round(filled_total / req_total * 100.0, 1) if req_total else 100.0,
        changeover_readiness_pct=round(tech_ready / tech_slots * 100.0, 1) if tech_slots else 100.0,
        preference_match_pct=round(matches / total_assigned * 100.0, 1) if total_assigned else 100.0,
        understaffed_slots=understaffed,
        headcount_gap=short_total,
        night_spread=spread,
        violations=violations,
        worst_slot=worst[1] if worst else None,
        role_coverage_pct={
            r: round(role_fill[r] / role_req[r] * 100.0, 1) if role_req[r] else 100.0 for r in WORKER_ROLES
        },
    )
    return WorkforcePlan(rosters=rosters, demand=demand_cells, kpis=kpis)


# --------------------------------------------------------------------------------------------
# Independent hard-constraint verification
# --------------------------------------------------------------------------------------------
def verify_workforce(
    assignments: Assignments,
    workers: list[FactoryWorker],
    slots: list[SlotDemand],
    layout: list[ShiftDef],
    config: SolverConfig,
    unavailable: dict[str, set[int]],
) -> list[ConstraintCheck]:
    wf = config.workforce
    by_slot = {(s.day, s.shift_idx): s for s in slots}
    role_viol: list[str] = []
    cap_viol: list[str] = []
    rest_viol: list[str] = []
    leave_viol: list[str] = []
    off_viol: list[str] = []
    day_viol: list[str] = []

    for w in workers:
        asg = assignments.get(w.worker_id, [])
        # HC1 role & certification: operators may not be rostered into a running slot on presses
        # they are not certified for; non-operators must hold a role present in the demand model.
        for (d, si) in asg:
            if w.role not in WORKER_ROLES:
                role_viol.append(f"{w.worker_id} has unknown role {w.role}")
            elif w.role == "Press_Operator":
                s = by_slot[(d, si)]
                if s.active_presses and not _certified(w, frozenset(s.active_presses)):
                    role_viol.append(f"{w.worker_id} not certified for {DAY_LABELS[d]} {s.shift} presses")

        # HC2 hour caps + shift length
        cap, _ = effective_hour_limits(w, config)
        hours = 0.0
        for (d, si) in asg:
            hours += layout[si].hours
            if config.ramadan_shift_mode and layout[si].hours != 6:
                cap_viol.append(f"{w.worker_id} Ramadan shift != 6h")
        if hours > cap + 1e-9:
            cap_viol.append(f"{w.worker_id} {hours:.0f}h > cap {cap:.0f}h")

        # HC3 rest gap between consecutive days' shifts
        by_day = defaultdict(list)
        for (d, si) in asg:
            by_day[d].append(si)
        for d in range(DAYS - 1):
            for s1 in by_day.get(d, []):
                for s2 in by_day.get(d + 1, []):
                    gap = (d + 1) * 24 + layout[s2].start_hr - (d * 24 + layout[s1].end_hr)
                    if gap < wf.min_rest_hours:
                        rest_viol.append(
                            f"{w.worker_id} {DAY_LABELS[d]} {layout[s1].name} -> "
                            f"{DAY_LABELS[d + 1]} {layout[s2].name} ({gap}h rest)"
                        )

        # HC4 leave / sick lock + consecutive days off
        for (d, si) in asg:
            if worker_unavailable_label(w, d, unavailable) is not None:
                leave_viol.append(f"{w.worker_id} scheduled while unavailable on {DAY_LABELS[d]}")
        worked_days = {d for (d, _) in asg}
        off = [d not in worked_days for d in range(DAYS)]
        if any(worker_unavailable_label(w, d, unavailable) is None for d in range(DAYS)):
            k = wf.min_consecutive_days_off
            ok = any(all(off[j : j + k]) for j in range(0, DAYS - k + 1))
            if not ok:
                off_viol.append(f"{w.worker_id} lacks {k} consecutive day(s) off")

        # HC5 max one shift per day
        for d, lst in by_day.items():
            if len(lst) > 1:
                day_viol.append(f"{w.worker_id} has {len(lst)} shifts on {DAY_LABELS[d]}")

    def chk(cid: str, name: str, details: list[str]) -> ConstraintCheck:
        return ConstraintCheck(id=cid, name=name, violations=len(details), passed=not details, details=details[:12])

    return [
        chk("WHC1", "Role & Machine Certification Match", role_viol),
        chk("WHC2", "Labor-Law & Ramadan Hour Caps", cap_viol),
        chk("WHC3", "Mandatory Inter-Shift Rest Gap", rest_viol),
        chk("WHC4", "Leave, Sick Callout & Days-Off Lock", leave_viol + off_viol),
        chk("WHC5", "Max One Shift Per Day", day_viol),
    ]


# --------------------------------------------------------------------------------------------
# Naive Static Rotation baseline
# --------------------------------------------------------------------------------------------
def build_naive_roster(
    workers: list[FactoryWorker],
    slots: list[SlotDemand],
    layout: list[ShiftDef],
    config: SolverConfig,
    unavailable: dict[str, set[int]],
) -> Assignments:
    """Fixed shift per worker (round-robin within role) and a fixed staggered 6-day week.

    Ignores press-load swings and mold-change peaks. It respects sick/leave status, hour caps and
    the rest/day-off rules (a static rotation is legal - just wasteful and blind to demand).
    """
    by_slot = {(s.day, s.shift_idx): s for s in slots}
    wf = config.workforce
    # 6-day week for 1 day off, 5-day week for 2 consecutive days off
    work_days = 6 if wf.min_consecutive_days_off == 1 else 5
    out: Assignments = {}
    role_idx: dict[str, int] = defaultdict(int)
    n_shifts = len(layout)
    for w in sorted(workers, key=lambda x: (x.role, x.worker_id)):
        i = role_idx[w.role]
        role_idx[w.role] += 1
        out[w.worker_id] = []
        if w.status != "active":
            continue
        si = i % n_shifts
        off_days = {(i + k) % DAYS for k in range(DAYS - work_days)}
        cap, _ = effective_hour_limits(w, config)
        max_shifts = int(cap // layout[si].hours)
        days = [d for d in range(DAYS) if d not in off_days]
        days = [d for d in days if worker_unavailable_label(w, d, unavailable) is None]
        days = days[:max_shifts]
        for d in days:
            s = by_slot[(d, si)]
            if w.role == "Press_Operator" and s.active_presses and not _certified(w, frozenset(s.active_presses)):
                continue  # an uncertified operator would be stood down, not rostered
            out[w.worker_id].append((d, si))
    return out


# --------------------------------------------------------------------------------------------
# CP-SAT roster optimizer (exact role-by-role decomposition)
# --------------------------------------------------------------------------------------------
def _solve_role_roster(
    role: str,
    role_workers: list[FactoryWorker],
    slots: list[SlotDemand],
    layout: list[ShiftDef],
    config: SolverConfig,
    unavailable: dict[str, set[int]],
    hint: Assignments,
    time_limit_s: float,
) -> tuple[Assignments, str, float]:
    """Solve one role's roster independently (exact: zero cross-role constraints or couplings)."""
    if not role_workers:
        return {}, "OPTIMAL", 0.0

    wf = config.workforce
    model = cp_model.CpModel()
    n_sh = len(layout)
    shift_len = layout[0].hours
    by_slot = {(s.day, s.shift_idx): s for s in slots}
    by_id = {w.worker_id: w for w in role_workers}

    # ---- decision variables --------------------------------------------------------------
    x: dict[tuple[str, int, int], cp_model.IntVar] = {}
    for w in role_workers:
        for d in range(DAYS):
            if worker_unavailable_label(w, d, unavailable) is not None:
                continue
            for si in range(n_sh):
                s = by_slot[(d, si)]
                if (
                    w.role == "Press_Operator"
                    and s.active_presses
                    and not _certified(w, frozenset(s.active_presses))
                ):
                    continue  # HC1: never roster an uncertified operator onto a running slot
                x[(w.worker_id, d, si)] = model.NewBoolVar(f"x_{w.worker_id}_{d}_{si}")

    def xv(wid: str, d: int, si: int):
        return x.get((wid, d, si))

    # ---- per-worker hard constraints ------------------------------------------------------
    labor_terms = []
    for w in role_workers:
        day_vars: dict[int, list[cp_model.IntVar]] = defaultdict(list)
        for d in range(DAYS):
            for si in range(n_sh):
                v = xv(w.worker_id, d, si)
                if v is not None:
                    day_vars[d].append(v)
        # HC5: max one shift per day
        for d, vs in day_vars.items():
            if len(vs) > 1:
                model.Add(sum(vs) <= 1)
        all_vars = [v for vs in day_vars.values() for v in vs]
        if not all_vars:
            continue
        cap, std = effective_hour_limits(w, config)
        n_work = sum(all_vars)
        # HC2: weekly hour cap (Ramadan clamps shift length via layout and cap to 36h)
        model.Add(n_work <= int(cap // shift_len))
        # HC3: inter-shift rest gap on consecutive days
        for d in range(DAYS - 1):
            for s1 in range(n_sh):
                a = xv(w.worker_id, d, s1)
                if a is None:
                    continue
                for s2 in range(n_sh):
                    b = xv(w.worker_id, d + 1, s2)
                    if b is None:
                        continue
                    gap = (d + 1) * 24 + layout[s2].start_hr - (d * 24 + layout[s1].end_hr)
                    if gap < wf.min_rest_hours:
                        model.Add(a + b <= 1)
        # HC4: days off - at least k consecutive off days in the 7-day cycle
        off_flags = []
        for d in range(DAYS):
            if d in day_vars:
                o = model.NewBoolVar(f"off_{w.worker_id}_{d}")
                model.Add(sum(day_vars[d]) + o == 1)
                off_flags.append(o)
            else:
                off_flags.append(1)  # leave / callout day counts as off
        k = wf.min_consecutive_days_off
        pair_vars = []
        const_true = False
        for j in range(0, DAYS - k + 1):
            window = off_flags[j : j + k]
            if all(isinstance(f, int) for f in window):
                const_true = True
                break
            p = model.NewBoolVar(f"pair_{w.worker_id}_{j}")
            for f in window:
                if not isinstance(f, int):
                    model.AddImplication(p, f)
            pair_vars.append(p)
        if not const_true:
            model.AddBoolOr(pair_vars)

        # overtime accounting
        std_shifts_hours = int(std)
        ot = model.NewIntVar(0, int(cap), f"ot_{w.worker_id}")
        model.Add(ot >= n_work * shift_len - std_shifts_hours)
        rate_c = int(round(w.hourly_rate * 100))
        prem_c = int(round(w.hourly_rate * 100 * (w.overtime_multiplier - 1.0)))
        labor_terms.append(rate_c * shift_len * n_work + prem_c * ot)

    # ---- coverage (soft, per slot for this role) ------------------------------------------
    gap_terms = []
    for s in slots:
        req = s.required[role]
        if req == 0:
            continue
        elig = []
        for w in role_workers:
            v = xv(w.worker_id, s.day, s.shift_idx)
            if v is not None:
                elig.append(v)
        short = model.NewIntVar(0, req, f"short_{s.day}_{s.shift_idx}_{role}")
        model.Add(sum(elig) + short >= req)
        crit = MOLD_TECH_CRITICALITY if role == "Mold_Technician" else 1
        gap_terms.append(GAP_CENTS * crit * short)
        if role == "Press_Operator":
            for pid in s.active_presses:
                cert_vars = [
                    xv(w.worker_id, s.day, s.shift_idx)
                    for w in role_workers
                    if _certified_on(w, pid) and xv(w.worker_id, s.day, s.shift_idx) is not None
                ]
                cshort = model.NewBoolVar(f"cshort_{s.day}_{s.shift_idx}_{pid}")
                model.Add(sum(cert_vars) + cshort >= 1)
                gap_terms.append(CERT_GAP_CENTS * cshort)

    # ---- fairness: preference mismatch + night-shift spread ------------------------------------
    fair_terms = []
    night_idx = next((i for i, sh in enumerate(layout) if sh.name == "Night"), None)
    for (wid, d, si), v in x.items():
        if not _pref_match(by_id[wid], layout[si].name):
            fair_terms.append(MISMATCH_CENTS * v)
    if night_idx is not None:
        active = [w for w in role_workers if w.status == "active"]
        if len(active) >= 2:
            nights = []
            for w in active:
                vs = [xv(w.worker_id, d, night_idx) for d in range(DAYS)]
                vs = [v for v in vs if v is not None]
                nights.append(sum(vs) if vs else 0)
            hi = model.NewIntVar(0, DAYS, f"hi_{role}")
            lo = model.NewIntVar(0, DAYS, f"lo_{role}")
            for n in nights:
                model.Add(hi >= n)
                model.Add(lo <= n)
            fair_terms.append(SPREAD_CENTS * (hi - lo))

    # ---- symmetry breaking for strictly identical workers in this role --------------------
    # Two workers with identical status, certifications, pay/OT/cap, shift preference, and
    # unavailable days are interchangeable; ordering (total_shifts, night_shifts) non-increasingly
    # prunes factorial permutation symmetry without cutting off any optimal solution.
    sym_groups: dict[tuple, list[FactoryWorker]] = defaultdict(list)
    for w in sorted(role_workers, key=lambda x: x.worker_id):
        certs = "ALL" if w.certified_machine_ids == "ALL" else tuple(sorted(w.certified_machine_ids))
        unavail_days = tuple(d for d in range(DAYS) if worker_unavailable_label(w, d, unavailable) is not None)
        sig = (
            w.status,
            certs,
            round(w.hourly_rate, 4),
            round(w.overtime_multiplier, 4),
            round(w.max_weekly_hours, 4),
            w.preferred_shift,
            unavail_days,
        )
        sym_groups[sig].append(w)

    def _worker_sym_expr(wid: str):
        all_w = [xv(wid, d, si) for d in range(DAYS) for si in range(n_sh)]
        all_w = [v for v in all_w if v is not None]
        n_tot = sum(all_w) if all_w else 0
        if night_idx is not None:
            n_vars = [xv(wid, d, night_idx) for d in range(DAYS)]
            n_vars = [v for v in n_vars if v is not None]
            n_night = sum(n_vars) if n_vars else 0
        else:
            n_night = 0
        return n_tot * (DAYS + 1) + n_night

    # Reorder warm-start hint within each symmetry group so the hint satisfies symmetry breaking
    aligned_hint: dict[str, list[tuple[int, int]]] = {wid: list(hint.get(wid, [])) for wid in by_id}
    for grp in sym_groups.values():
        if len(grp) < 2:
            continue
        for k in range(len(grp) - 1):
            model.Add(_worker_sym_expr(grp[k].worker_id) >= _worker_sym_expr(grp[k + 1].worker_id))
        grp_schedules = [aligned_hint[w.worker_id] for w in grp]
        grp_schedules.sort(
            key=lambda asg: (
                len(asg),
                sum(1 for (_, si) in asg if night_idx is not None and si == night_idx),
            ),
            reverse=True,
        )
        for w, sched in zip(grp, grp_schedules):
            aligned_hint[w.worker_id] = sched

    model.Minimize(
        wf.w_labor_cost * sum(labor_terms)
        + wf.w_coverage * sum(gap_terms)
        + wf.w_fairness * sum(fair_terms)
    )

    # ---- warm start from the naive baseline (feasible by construction & symmetry-aligned) -------
    hinted = {(wid, d, si) for wid in by_id for (d, si) in aligned_hint.get(wid, [])}
    for key, v in x.items():
        model.AddHint(v, 1 if key in hinted else 0)

    solver = cp_model.CpSolver()
    solver.parameters.num_workers = 4
    solver.parameters.interleave_search = True
    solver.parameters.random_seed = int(config.random_seed)
    solver.parameters.max_deterministic_time = min(0.22, float(time_limit_s) * 0.55)
    solver.parameters.max_time_in_seconds = max(0.45, float(time_limit_s))
    solver.parameters.relative_gap_limit = REL_GAP
    status = solver.Solve(model)
    status_name = {
        cp_model.OPTIMAL: "OPTIMAL",
        cp_model.FEASIBLE: "FEASIBLE",
        cp_model.INFEASIBLE: "INFEASIBLE",
        cp_model.MODEL_INVALID: "MODEL_INVALID",
    }.get(status, "UNKNOWN")

    out: Assignments = {w.worker_id: [] for w in role_workers}
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for (wid, d, si), v in x.items():
            if solver.Value(v):
                out[wid].append((d, si))
        for wid in out:
            out[wid].sort()
        return out, status_name, float(solver.ObjectiveValue())

    out = {w.worker_id: list(hint.get(w.worker_id, [])) for w in role_workers}
    return out, f"FALLBACK_{status_name}", 0.0


def _solve_roster(
    workers: list[FactoryWorker],
    slots: list[SlotDemand],
    layout: list[ShiftDef],
    config: SolverConfig,
    unavailable: dict[str, set[int]],
    hint: Assignments,
    time_limit_s: float,
) -> tuple[Assignments, str, float]:
    workers_by_role: dict[str, list[FactoryWorker]] = defaultdict(list)
    for w in workers:
        workers_by_role[w.role].append(w)

    out: Assignments = {w.worker_id: [] for w in workers}
    statuses: list[str] = []
    total_obj = 0.0
    per_role_budget = max(0.3, float(time_limit_s) / max(1, len(workers_by_role)))

    for role in WORKER_ROLES:
        r_workers = workers_by_role.get(role, [])
        if not r_workers:
            continue
        r_asg, r_status, r_obj = _solve_role_roster(
            role, r_workers, slots, layout, config, unavailable, hint, per_role_budget
        )
        out.update(r_asg)
        statuses.append(r_status)
        total_obj += r_obj

    if not statuses or all(s == "OPTIMAL" for s in statuses):
        agg_status = "OPTIMAL"
    elif all(s in ("OPTIMAL", "FEASIBLE") for s in statuses):
        agg_status = "FEASIBLE"
    else:
        agg_status = statuses[0]
    return out, agg_status, total_obj


def _objective_of(plan: WorkforcePlan, config: SolverConfig, workers: list[FactoryWorker], layout: list[ShiftDef]) -> float:
    """Re-score any plan with the SAME weights (SAR-cents scale) for an apples-to-apples comparison."""
    wf = config.workforce
    fx = config.fx_egp_per_sar if config.currency == "EGP" else 1.0
    labor_sar = plan.kpis.total_labor_cost / fx
    mism = sum(r.shifts_worked - r.preference_matches for r in plan.rosters)
    gap = 0
    for c in plan.demand:
        if c.required > 0:
            crit = MOLD_TECH_CRITICALITY if c.role == "Mold_Technician" else 1
            gap += max(0, c.required - c.scheduled) * crit * GAP_CENTS
            gap += len(c.uncertified_presses) * CERT_GAP_CENTS
    return (
        wf.w_labor_cost * labor_sar * 100.0
        + wf.w_coverage * gap
        + wf.w_fairness * (mism * MISMATCH_CENTS + plan.kpis.night_spread * SPREAD_CENTS)
    )


# --------------------------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------------------------
def solve_workforce(
    dataset: PlantDataset,
    config: SolverConfig,
    plan: SchedulePlan,
    *,
    unavailable: Optional[dict[str, set[int]]] = None,
    time_limit_s: float = 2.0,
    callouts_applied: Optional[list[str]] = None,
) -> Optional[WorkforceResult]:
    """Optimize the 7-day roster against the solved Press Gantt. Returns None if there are no workers."""
    workers = list(dataset.workers)
    if not workers:
        return None
    unavailable = unavailable or {}
    t0 = time.perf_counter()
    layout = shift_layout(config)
    slots = derive_demand(plan, config, layout)

    base_asg = build_naive_roster(workers, slots, layout, config, unavailable)
    opt_asg, status, _raw_obj = _solve_roster(
        workers, slots, layout, config, unavailable, base_asg, time_limit_s
    )

    opt_checks = verify_workforce(opt_asg, workers, slots, layout, config, unavailable)
    base_checks = verify_workforce(base_asg, workers, slots, layout, config, unavailable)
    opt_plan = evaluate_roster(
        opt_asg, workers, slots, layout, config, unavailable, sum(c.violations for c in opt_checks)
    )
    base_plan = evaluate_roster(
        base_asg, workers, slots, layout, config, unavailable, sum(c.violations for c in base_checks)
    )
    opt_obj = _objective_of(opt_plan, config, workers, layout)
    base_obj = _objective_of(base_plan, config, workers, layout)

    notes: list[str] = []
    if opt_plan.kpis.coverage_pct < 100.0:
        notes.append(
            f"Coverage {opt_plan.kpis.coverage_pct:.1f}% - {opt_plan.kpis.headcount_gap} head-shift(s) "
            f"cannot be filled within hard limits (worst: {opt_plan.kpis.worst_slot})."
        )
    if config.ramadan_shift_mode:
        notes.append("Ramadan mode: 4x6h shifts, weekly cap 36h, standard hours 30h.")

    return WorkforceResult(
        currency=config.currency,
        ramadan_mode=config.ramadan_shift_mode,
        shift_names=[sh.name for sh in layout],
        shift_hours=layout[0].hours,
        shift_windows={sh.name: sh.window_label for sh in layout},
        status=status,
        solve_time_ms=max(1, int((time.perf_counter() - t0) * 1000)),
        objective=round(opt_obj, 2),
        baseline_objective=round(base_obj, 2),
        optimized=opt_plan,
        baseline=base_plan,
        constraints_verified=opt_checks,
        baseline_constraints_verified=base_checks,
        all_hard_constraints_passed=all(c.passed for c in opt_checks),
        labor_cost_saved=round(base_plan.kpis.total_labor_cost - opt_plan.kpis.total_labor_cost, 2),
        overtime_hours_cut=round(base_plan.kpis.overtime_hours - opt_plan.kpis.overtime_hours, 1),
        callouts_applied=callouts_applied or [],
        notes=notes,
    )


def resolve_callouts(
    callouts: list[WorkforceCallout],
    workers: list[FactoryWorker],
    reference: Optional[WorkforcePlan],
) -> tuple[dict[str, set[int]], list[str]]:
    """Turn role/count/day callouts into concrete (worker_id -> unavailable days).

    For role callouts, absent workers are the first `count` (by worker_id) of that role who are
    actually rostered on that day in the reference roster - i.e. the callout hurts.
    """
    unavailable: dict[str, set[int]] = defaultdict(set)
    desc: list[str] = []
    by_id = {w.worker_id: w for w in workers}
    rows = {r.worker_id: r for r in reference.rosters} if reference else {}

    for co in callouts:
        picked: list[str] = []
        if co.worker_ids:
            picked = [wid for wid in co.worker_ids if wid in by_id]
        elif co.role:
            pool = sorted((w for w in workers if w.role == co.role and w.status == "active"), key=lambda w: w.worker_id)
            rostered = [
                w.worker_id
                for w in pool
                if w.worker_id in rows and rows[w.worker_id].cells[co.day] not in NON_WORK_LABELS
            ]
            rest = [w.worker_id for w in pool if w.worker_id not in rostered]
            picked = (rostered + rest)[: co.count]
        for wid in picked:
            unavailable[wid].add(co.day)
        if picked:
            who = ", ".join(f"{by_id[p].name} ({p})" for p in picked)
            role_txt = co.role.replace("_", " ") if co.role else "worker"
            desc.append(f"{len(picked)} {role_txt}(s) call out on {DAY_LABELS[co.day]}: {who}")
    return dict(unavailable), desc


def solve_workforce_with_callouts(
    dataset: PlantDataset,
    config: SolverConfig,
    plan: SchedulePlan,
    callouts: list[WorkforceCallout],
    *,
    time_limit_s: float = 2.0,
) -> Optional[WorkforceResult]:
    """Solve the reference roster, then re-solve with day-specific callouts applied."""
    ref = solve_workforce(dataset, config, plan, time_limit_s=time_limit_s)
    if ref is None or not callouts:
        return ref
    unavailable, desc = resolve_callouts(callouts, dataset.workers, ref.optimized)
    res = solve_workforce(
        dataset, config, plan, unavailable=unavailable, time_limit_s=time_limit_s, callouts_applied=desc
    )
    if res is not None:
        res.reference_kpis = ref.optimized.kpis
    return res


def parse_day(value) -> int:
    """Accept 0..6, 'Tue', 'Tuesday', or Arabic day names; default 0."""
    if isinstance(value, (int, float)):
        return max(0, min(6, int(value)))
    s = str(value or "").strip().lower()
    names = {
        0: ("sun", "الأحد", "الاحد"),
        1: ("mon", "الاثنين", "الإثنين"),
        2: ("tue", "الثلاثاء"),
        3: ("wed", "الأربعاء", "الاربعاء"),
        4: ("thu", "الخميس"),
        5: ("fri", "الجمعة"),
        6: ("sat", "السبت"),
    }
    for idx, keys in names.items():
        if any(s.startswith(k) or k in s for k in keys):
            return idx
    try:
        return max(0, min(6, int(s)))
    except ValueError:
        return 0
