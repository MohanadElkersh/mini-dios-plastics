"""Workforce (Tab 6) CP-SAT scheduler tests: hard constraints, Ramadan clamp, mold-change readiness,
baseline beat, Tab 5 P&L flow-through, Copilot call-outs, determinism, API and back-compat."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.routes import set_audit_store
from core.audit import AuditStore
from core.copilot import run_offline_composable_copilot
from core.ontology import (
    FactoryWorker,
    PlantDataset,
    SolveResult,
    WorkforceCallout,
)
from core.seed import default_config, demo_dataset, demo_workers
from core.solver import solve_plant_schedule
from core.workforce_solver import (
    derive_demand,
    shift_layout,
    solve_workforce,
    solve_workforce_with_callouts,
    verify_workforce,
)
from main import app


@pytest.fixture(scope="module")
def ds() -> PlantDataset:
    return demo_dataset()


@pytest.fixture(scope="module")
def res(ds: PlantDataset) -> SolveResult:
    return solve_plant_schedule(ds, default_config())


@pytest.fixture(scope="module")
def ramadan_res(ds: PlantDataset) -> SolveResult:
    cfg = default_config()
    cfg.ramadan_shift_mode = True
    return solve_plant_schedule(ds, cfg)


def _worker_map(ds: PlantDataset) -> dict[str, FactoryWorker]:
    return {w.worker_id: w for w in ds.workers}


# ---------------------------------------------------------------- seed & schema
def test_seed_has_28_workers_with_expected_role_mix():
    ws = demo_workers()
    assert len(ws) == 28
    by_role: dict[str, int] = {}
    for w in ws:
        by_role[w.role] = by_role.get(w.role, 0) + 1
    assert by_role == {
        "Press_Operator": 14,
        "Mold_Technician": 5,
        "QC_Inspector": 4,
        "Material_Handler": 3,
        "Shift_Supervisor": 2,
    }
    assert any(w.approved_leave_days for w in ws)
    assert all(w.overtime_multiplier == 1.5 and w.max_weekly_hours == 48 for w in ws)


def test_demo_dataset_carries_workers_and_old_payloads_still_load(ds: PlantDataset):
    assert len(ds.workers) == 28
    legacy = ds.model_dump(mode="json")
    legacy.pop("workers")
    loaded = PlantDataset.model_validate(legacy)
    assert loaded.workers == []


def test_no_workers_means_no_workforce_and_zero_labor_line(ds: PlantDataset):
    empty = ds.model_copy(update={"workers": []})
    r = solve_plant_schedule(empty, default_config())
    assert r.workforce is None
    assert r.financials.optimized.direct_labor_and_overtime_cost == 0.0
    assert r.financials.savings_breakdown.labor_and_overtime_saved == 0.0


# ---------------------------------------------------------------- 5 hard constraints
def test_all_five_hard_constraints_verified_zero_violations(res: SolveResult):
    wf = res.workforce
    assert wf is not None
    assert [c.id for c in wf.constraints_verified] == ["WHC1", "WHC2", "WHC3", "WHC4", "WHC5"]
    assert all(c.passed and c.violations == 0 for c in wf.constraints_verified)
    assert wf.all_hard_constraints_passed
    assert wf.optimized.kpis.violations == 0
    assert wf.status in ("OPTIMAL", "FEASIBLE")


def test_zero_night_to_morning_or_short_rest_violations(ds: PlantDataset, res: SolveResult):
    wf = res.workforce
    cfg = default_config()
    layout = shift_layout(cfg)
    ends = {sh.name: sh.end_hr for sh in layout}
    starts = {sh.name: sh.start_hr for sh in layout}
    checked = 0
    for row in wf.optimized.rosters:
        for d in range(6):
            a, b = row.cells[d], row.cells[d + 1]
            if a in ends and b in starts:
                checked += 1
                assert not (a == "Night" and b == "Morning"), f"{row.worker_id} Night->Morning on day {d}"
                gap = (d + 1) * 24 + starts[b] - (d * 24 + ends[a])
                assert gap >= cfg.workforce.min_rest_hours, f"{row.worker_id} {a}->{b} only {gap}h rest"
    assert checked > 20  # the roster really has consecutive working days to test


def test_no_shifts_on_leave_days_or_for_sick_workers(ds: PlantDataset, res: SolveResult):
    workers = _worker_map(ds)
    for row in res.workforce.optimized.rosters:
        w = workers[row.worker_id]
        for d in w.approved_leave_days:
            assert row.cells[d] == "LEAVE", f"{row.worker_id} not on leave day {d}"

    # Mark a Mold Technician and a Press Operator sick, then re-solve the labor roster.
    sick_ds = ds.model_copy(deep=True)
    for w in sick_ds.workers:
        if w.worker_id in ("MT-02", "OP-03"):
            w.status = "sick"
    wf = solve_workforce(sick_ds, default_config(), res.optimized)
    rows = {r.worker_id: r for r in wf.optimized.rosters}
    for wid in ("MT-02", "OP-03"):
        assert rows[wid].cells == ["SICK"] * 7
        assert rows[wid].shifts_worked == 0 and rows[wid].weekly_hours == 0
    assert wf.all_hard_constraints_passed


def test_max_one_shift_per_day_and_weekly_caps(res: SolveResult, ds: PlantDataset):
    workers = _worker_map(ds)
    for row in res.workforce.optimized.rosters:
        worked = [c for c in row.cells if c not in ("OFF", "LEAVE", "SICK")]
        assert row.shifts_worked == len(worked)
        assert row.weekly_hours <= workers[row.worker_id].max_weekly_hours
        assert "OFF" in row.cells or "LEAVE" in row.cells or "SICK" in row.cells  # >=1 day off


def test_min_two_consecutive_days_off_is_enforced(ds: PlantDataset, res: SolveResult):
    cfg = default_config()
    cfg.workforce.min_consecutive_days_off = 2
    wf = solve_workforce(ds, cfg, res.optimized)
    assert wf.all_hard_constraints_passed
    for row in wf.optimized.rosters:
        off = [c in ("OFF", "LEAVE", "SICK") for c in row.cells]
        assert any(off[i] and off[i + 1] for i in range(6)), row.worker_id


def test_independent_verifier_catches_injected_violations(ds: PlantDataset, res: SolveResult):
    cfg = default_config()
    layout = shift_layout(cfg)
    slots = derive_demand(res.optimized, cfg, layout)
    morning = next(i for i, s in enumerate(layout) if s.name == "Morning")
    night = next(i for i, s in enumerate(layout) if s.name == "Night")
    afternoon = next(i for i, s in enumerate(layout) if s.name == "Afternoon")
    bad = {w.worker_id: [] for w in ds.workers}
    bad["OP-03"] = [(0, night), (1, morning), (1, afternoon)]  # Night->Morning, Night->Afternoon, 2 shifts on a day
    bad["OP-05"] = [(2, morning)]  # OP-05 is on approved leave on day 2
    checks = {c.id: c for c in verify_workforce(bad, ds.workers, slots, layout, cfg, {})}
    assert checks["WHC3"].violations >= 2
    assert checks["WHC5"].violations == 1
    assert checks["WHC4"].violations >= 1


# ---------------------------------------------------------------- Ramadan
def test_ramadan_mode_enforces_strict_6h_shifts_and_36h_cap(ramadan_res: SolveResult, ds: PlantDataset):
    wf = ramadan_res.workforce
    assert wf is not None and wf.ramadan_mode
    assert wf.shift_hours == 6
    assert wf.shift_names == ["Night", "Morning", "Afternoon", "Evening"]
    assert all(c.passed for c in wf.constraints_verified)
    for row in wf.optimized.rosters + wf.baseline.rosters:
        assert row.weekly_hours == pytest.approx(6.0 * row.shifts_worked)
        assert row.weekly_hours <= 36.0
        assert row.regular_hours <= 30.0 + 1e-9


# ---------------------------------------------------------------- demand derivation & mold readiness
def test_demand_is_derived_from_the_solved_gantt(res: SolveResult):
    cfg = default_config()
    layout = shift_layout(cfg)
    slots = derive_demand(res.optimized, cfg, layout)
    assert len(slots) == 21
    ppo = cfg.workforce.presses_per_operator
    for s in slots:
        n = len(s.active_presses)
        assert s.required["Press_Operator"] == -(-n // ppo)
        assert s.required["Shift_Supervisor"] == (1 if n else 0)
        if n:
            assert s.required["QC_Inspector"] >= 1 and s.required["Material_Handler"] >= 1
            if n >= 4 or s.hygroscopic:
                assert s.required["QC_Inspector"] >= 2
        if s.mold_change:
            assert s.required["Mold_Technician"] >= 1
        else:
            assert s.required["Mold_Technician"] == 0
    assert any(s.mold_change for s in slots)


def test_mold_technicians_are_scheduled_on_every_changeover_shift(res: SolveResult, ds: PlantDataset):
    wf = res.workforce
    tech_cells = [c for c in wf.optimized.demand if c.role == "Mold_Technician" and c.mold_change and c.required > 0]
    assert tech_cells, "expected mold-changeover / PM shifts in the solved Gantt"
    for c in tech_cells:
        assert c.scheduled >= 1, f"no Mold Technician on day {c.day} {c.shift}"
    assert wf.optimized.kpis.changeover_readiness_pct == 100.0

    workers = _worker_map(ds)
    rows = {r.worker_id: r for r in wf.optimized.rosters}
    for c in tech_cells:
        staffed = [
            wid for wid, r in rows.items() if workers[wid].role == "Mold_Technician" and r.cells[c.day] == c.shift
        ]
        assert staffed


# ---------------------------------------------------------------- baseline beat & P&L flow
def test_cpsat_beats_naive_static_rotation(res: SolveResult):
    wf = res.workforce
    o, b = wf.optimized.kpis, wf.baseline.kpis
    assert o.total_labor_cost < b.total_labor_cost
    assert o.overtime_hours < b.overtime_hours
    assert o.overtime_cost < b.overtime_cost
    assert o.coverage_pct >= b.coverage_pct
    assert o.changeover_readiness_pct >= b.changeover_readiness_pct
    assert wf.objective <= wf.baseline_objective
    assert wf.labor_cost_saved == pytest.approx(b.total_labor_cost - o.total_labor_cost, abs=0.01)
    assert wf.overtime_hours_cut == pytest.approx(b.overtime_hours - o.overtime_hours, abs=0.01)
    assert wf.labor_cost_saved > 0 and wf.overtime_hours_cut > 0
    assert o.violations == 0


def test_workforce_cost_flows_into_financials(res: SolveResult):
    wf, fin = res.workforce, res.financials
    assert fin.baseline.direct_labor_and_overtime_cost == pytest.approx(wf.baseline.kpis.total_labor_cost, abs=0.01)
    assert fin.optimized.direct_labor_and_overtime_cost == pytest.approx(wf.optimized.kpis.total_labor_cost, abs=0.01)
    assert fin.savings_breakdown.labor_and_overtime_saved == pytest.approx(wf.labor_cost_saved, abs=0.01)
    for p in (fin.optimized, fin.baseline):
        parts = (
            p.direct_resin_cost
            + p.purge_scrap_cost
            + p.energy_and_press_operating_cost
            + p.late_delivery_penalties
            + p.wip_holding_cost
            + p.direct_labor_and_overtime_cost
        )
        assert p.variable_production_cost == pytest.approx(parts, abs=0.05)
        assert p.total_operating_cost == pytest.approx(p.variable_production_cost + p.weekly_fixed_overhead, abs=0.05)
    expected_total = (fin.baseline.total_operating_cost - fin.optimized.total_operating_cost) + (
        fin.optimized.recognized_revenue - fin.baseline.recognized_revenue
    )
    assert fin.total_weekly_savings == pytest.approx(expected_total, abs=0.05)
    assert fin.total_weekly_savings > fin.savings_breakdown.labor_and_overtime_saved > 0
    assert fin.annual_projected_savings == pytest.approx(fin.total_weekly_savings * fin.annual_operating_weeks, abs=0.05)


def test_egp_currency_conversion_of_labor_costs(ds: PlantDataset, res: SolveResult):
    cfg = default_config()
    cfg.currency = "EGP"
    wf_egp = solve_workforce(ds, cfg, res.optimized)
    wf_sar = res.workforce
    assert wf_egp.currency == "EGP"
    ratio = wf_egp.optimized.kpis.total_labor_cost / wf_sar.optimized.kpis.total_labor_cost
    assert ratio == pytest.approx(cfg.fx_egp_per_sar, rel=0.02)


def test_deterministic_same_input_same_roster(ds: PlantDataset, res: SolveResult):
    a = solve_workforce(ds, default_config(), res.optimized)
    b = solve_workforce(ds, default_config(), res.optimized)
    assert a.all_hard_constraints_passed is True
    assert b.all_hard_constraints_passed is True
    assert a.objective == b.objective
    assert a.optimized.kpis.total_labor_cost == b.optimized.kpis.total_labor_cost
    assert a.optimized.kpis.coverage_pct == b.optimized.kpis.coverage_pct


# ---------------------------------------------------------------- call-outs / Copilot / API
def test_role_callouts_remove_the_rostered_workers_and_hit_coverage(ds: PlantDataset, res: SolveResult):
    callouts = [
        WorkforceCallout(role="Mold_Technician", count=2, day=2),
        WorkforceCallout(role="Press_Operator", count=3, day=2),
    ]
    wf = solve_workforce_with_callouts(ds, default_config(), res.optimized, callouts)
    assert wf.reference_kpis is not None
    assert len(wf.callouts_applied) == 2
    rows = {r.worker_id: r for r in wf.optimized.rosters}
    absent = [wid for wid, r in rows.items() if r.cells[2] == "SICK"]
    assert len(absent) == 5
    assert wf.all_hard_constraints_passed
    assert wf.optimized.kpis.coverage_pct <= wf.reference_kpis.coverage_pct + 1e-9


def test_copilot_workforce_callout_english_and_arabic(ds: PlantDataset, res: SolveResult):
    cfg = default_config()
    q = (
        "What happens to our shift coverage, overtime cost, and weekly net profit if "
        "2 Mold Technicians and 3 Press Operators call out on Tuesday?"
    )
    out = run_offline_composable_copilot(q, ds, cfg, res, "en")
    assert out.action == "simulate_plant_scenario"
    wf = out.result.workforce
    assert wf is not None and len(wf.callouts_applied) == 2
    rows = {r.worker_id: r for r in wf.optimized.rosters}
    assert sum(1 for r in rows.values() if r.cells[2] == "SICK") == 5
    assert "shift coverage" in out.reply.lower() and "net profit" in out.reply.lower()
    assert f"{wf.optimized.kpis.coverage_pct:.1f}%" in out.reply
    assert out.result.financials.optimized.direct_labor_and_overtime_cost == pytest.approx(
        wf.optimized.kpis.total_labor_cost, abs=0.01
    )

    out_ar = run_offline_composable_copilot(
        "ماذا يحدث لتغطية الورديات وتكلفة العمالة وصافي الربح لو تغيب 2 فنيين و3 مشغلين يوم الثلاثاء؟",
        ds,
        cfg,
        res,
        "ar",
    )
    wf_ar = out_ar.result.workforce
    assert wf_ar is not None and len(wf_ar.callouts_applied) == 2
    assert sum(1 for r in wf_ar.optimized.rosters if r.cells[2] == "SICK") == 5
    assert "تغطية الورديات" in out_ar.reply


def test_workforce_solve_endpoint_updates_roster_and_financials(tmp_path, ds: PlantDataset, res: SolveResult):
    set_audit_store(AuditStore(tmp_path / "wf_audit.db"))
    client = TestClient(app)
    cfg = default_config().model_dump(mode="json")
    sick_ds = ds.model_copy(deep=True)
    for w in sick_ds.workers:
        if w.worker_id == "MT-01":
            w.status = "sick"
    r = client.post(
        "/api/workforce/solve",
        json={
            "dataset": sick_ds.model_dump(mode="json"),
            "config": cfg,
            "result": res.model_dump(mode="json"),
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    mt01 = next(x for x in body["workforce"]["optimized"]["rosters"] if x["worker_id"] == "MT-01")
    assert mt01["cells"] == ["SICK"] * 7
    fin = body["financials"]
    assert fin["optimized"]["direct_labor_and_overtime_cost"] == pytest.approx(
        body["workforce"]["optimized"]["kpis"]["total_labor_cost"], abs=0.01
    )

    r2 = client.post(
        "/api/workforce/solve",
        json={
            "dataset": ds.model_dump(mode="json"),
            "config": cfg,
            "result": res.model_dump(mode="json"),
            "worker_callouts": [{"role": "Mold_Technician", "count": 2, "day": 2}],
        },
    )
    assert r2.status_code == 200
    assert len(r2.json()["workforce"]["callouts_applied"]) == 1


def test_solve_endpoint_returns_workforce_and_default_workspace_gets_workers(tmp_path):
    store = AuditStore(tmp_path / "ws_audit.db")
    set_audit_store(store)
    client = TestClient(app)
    ws = client.get("/api/workspaces/default").json()
    assert len(ws["dataset"]["workers"]) == 28
    d = client.get("/api/demo-data").json()
    s = client.post("/api/solve", json={"dataset": d["dataset"], "config": d["default_config"]})
    assert s.status_code == 200
    assert s.json()["workforce"]["all_hard_constraints_passed"] is True
