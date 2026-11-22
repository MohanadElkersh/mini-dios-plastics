"""Tests for Mini-DIOS Plastics Deterministic OR-Tools CP-SAT Solver (HC1-HC6 & ROI vs. FIFO)."""
from __future__ import annotations

from core.ontology import (
    MachineBreakdown,
    MoldPmLock,
    PlantPhysicsConfig,
    PressMachine,
    ProductionOrder,
    ResinShortage,
    ScenarioDisruptions,
    SolverConfig,
)
from core.seed import default_config, demo_dataset
from core.solver import solve_plant_schedule


def test_demo_solve_passes_all_6_hard_constraints_and_beats_fifo_baseline():
    ds = demo_dataset()
    cfg = default_config()
    res = solve_plant_schedule(ds, cfg)

    assert res.status in ("OPTIMAL", "FEASIBLE")
    assert res.audit.all_hard_constraints_passed is True
    assert len(res.audit.constraints_verified) == 6
    assert all(c.passed and c.violations == 0 for c in res.audit.constraints_verified)
    assert all(c.passed and c.violations == 0 for c in res.audit.baseline_constraints_verified)

    # All 24 orders must be scheduled in normal stock conditions
    assert res.optimized.kpis.unscheduled_orders == 0
    assert len([j for j in res.optimized.jobs if j.scheduled]) == 24

    # CP-SAT light-to-dark color sequencing + mold grouping MUST beat naive FIFO baseline
    assert res.scorecard.purge_scrap_kg_saved > 0
    assert res.scorecard.changeover_hours_saved > 0
    assert res.scorecard.cash_savings > 0
    assert res.optimized.kpis.purge_scrap_kg < res.baseline.kpis.purge_scrap_kg
    assert res.optimized.kpis.changeover_hours < res.baseline.kpis.changeover_hours


def test_drying_lead_time_and_auto_mold_pm_strictly_enforced():
    ds = demo_dataset()
    res = solve_plant_schedule(ds, default_config())

    # PET & ABS require 6h (360 min) drying floor before production starts
    for j in res.optimized.jobs:
        if not j.scheduled:
            continue
        if j.resin_code in ("PET", "ABS"):
            assert j.start_min >= 360, f"{j.order_id} ({j.resin_code}) started at {j.start_min}m < 360m"
        # M-04 is at 96.4% shot life -> 6h (360 min) mandatory PM block before first run
        if j.mold_id == "M-04":
            assert j.start_min >= 360, f"M-04 order {j.order_id} started at {j.start_min}m during PM block"


def test_composable_breakdown_pm_lock_and_rush_order_simultaneously():
    ds = demo_dataset()
    cfg = SolverConfig(
        w_changeover_scrap=35,
        w_otif=35,
        w_energy_cost=15,
        w_working_capital=15,
        scenarios=ScenarioDisruptions(
            machine_breakdowns=[MachineBreakdown(machine_id="P-500T", start_hr=48.0, duration_hrs=18.0)],
            mold_pm_locks=[MoldPmLock(mold_id="M-01", duration_hrs=8.0)],
            rush_orders=[
                ProductionOrder(
                    order_id="RUSH-CAP-01",
                    customer="Almarai Urgent Export",
                    sku_name="28mm CSD Cap — White Rush",
                    mold_id="M-01",
                    resin_code="HDPE",
                    color="White",
                    quantity_pcs=40_000,
                    part_weight_g=2.8,
                    max_regrind_pct=0.0,
                    due_hr=108.0,
                    late_penalty_per_hr=750.0,
                    is_export=True,
                )
            ],
        ),
    )
    res = solve_plant_schedule(ds, cfg)
    assert res.status in ("OPTIMAL", "FEASIBLE")
    assert res.audit.all_hard_constraints_passed is True

    # Verify zero overlap with P-500T breakdown [2880..3960m]
    for j in res.optimized.jobs:
        if j.scheduled and j.machine_id == "P-500T":
            assert j.end_min <= 2880 or j.setup_start_min >= 3960
        if j.scheduled and j.mold_id == "M-01":
            assert j.start_min >= 480  # 8h PM lock

    # Rush order must be present and scheduled
    rush_job = next(j for j in res.optimized.jobs if j.order_id == "RUSH-CAP-01")
    assert rush_job.scheduled is True


def test_resin_shortage_enforces_virgin_cap_and_protects_food_regrind():
    ds = demo_dataset()
    # Severe 60% HDPE virgin cut + 30% non-food regrind override
    cfg = SolverConfig(
        scenarios=ScenarioDisruptions(
            resin_shortages=[ResinShortage(resin_code="HDPE", available_pct_reduction=60.0, virgin_price_spike_pct=25.0)],
            allow_regrind_override_pct=30.0,
        )
    )
    res = solve_plant_schedule(ds, cfg)
    assert res.status in ("OPTIMAL", "FEASIBLE")
    assert res.audit.all_hard_constraints_passed is True

    hdpe_usage = next(r for r in res.optimized.resin_usage if r.resin_code == "HDPE")
    # Effective HDPE virgin stock = 18500 * 0.40 = 7400 kg
    assert hdpe_usage.virgin_available_kg == 7400.0
    assert hdpe_usage.virgin_used_kg + hdpe_usage.purge_scrap_kg <= 7400.5

    # Verify food-grade HDPE orders (max_regrind_pct == 0) NEVER get regrind even with override
    food_ids = {o.order_id for o in ds.orders if o.max_regrind_pct == 0.0}
    for j in res.optimized.jobs:
        if j.order_id in food_ids and j.scheduled:
            assert j.regrind_kg == 0.0


def test_ramadan_and_peak_tariff_modes_solve_cleanly():
    ds = demo_dataset()
    cfg = SolverConfig(avoid_peak_tariff_hrs=True, ramadan_shift_mode=True)
    res = solve_plant_schedule(ds, cfg)
    assert res.status in ("OPTIMAL", "FEASIBLE")
    assert res.audit.all_hard_constraints_passed is True
    types = {a.type for a in res.applied_scenarios}
    assert "peak_tariff_avoidance" in types
    assert "ramadan_shift_mode" in types


def test_plant_physics_config_deterministically_changes_kpis_and_edited_entities():
    ds = demo_dataset()
    base_res = solve_plant_schedule(ds, default_config())

    # 1. Doubling dark_to_light_purge_kg increases FIFO purge scrap kg & cost deterministically
    cfg_double_purge = SolverConfig(physics=PlantPhysicsConfig(dark_to_light_purge_kg=64.0))
    purge_res = solve_plant_schedule(ds, cfg_double_purge)
    assert purge_res.audit.all_hard_constraints_passed is True
    assert purge_res.baseline.kpis.purge_scrap_kg >= base_res.baseline.kpis.purge_scrap_kg + 150.0
    assert purge_res.baseline.kpis.purge_scrap_cost > base_res.baseline.kpis.purge_scrap_cost

    # 2. Doubling energy_tariff_per_kwh doubles energy cost deterministically
    cfg_double_energy = SolverConfig(physics=PlantPhysicsConfig(energy_tariff_per_kwh=0.64))
    energy_res = solve_plant_schedule(ds, cfg_double_energy)
    assert energy_res.audit.all_hard_constraints_passed is True
    assert energy_res.optimized.kpis.energy_cost > base_res.optimized.kpis.energy_cost * 1.8

    # 3. Increasing holding_cost_per_kg_per_day raises WIP holding cost
    cfg_high_wip = SolverConfig(physics=PlantPhysicsConfig(holding_cost_per_kg_per_day=2.5))
    wip_res = solve_plant_schedule(ds, cfg_high_wip)
    assert wip_res.audit.all_hard_constraints_passed is True
    assert wip_res.optimized.kpis.wip_holding_cost > base_res.optimized.kpis.wip_holding_cost * 5.0

    # 4. Ramadan shift hours (4h vs 6h) increases shift labor operating cost
    cfg_ram_6 = SolverConfig(ramadan_shift_mode=True, physics=PlantPhysicsConfig(ramadan_shift_hours=6))
    cfg_ram_4 = SolverConfig(ramadan_shift_mode=True, physics=PlantPhysicsConfig(ramadan_shift_hours=4))
    ram_6_res = solve_plant_schedule(ds, cfg_ram_6)
    ram_4_res = solve_plant_schedule(ds, cfg_ram_4)
    assert ram_4_res.optimized.kpis.operating_cost > ram_6_res.optimized.kpis.operating_cost

    # 5. Adding an extra press + order + 240h horizon is reflected directly in solve output
    edited_ds = ds.model_copy(deep=True)
    edited_ds.presses.append(
        PressMachine(
            machine_id="P-400T",
            name="Engel 400T Studio Press",
            process_type="Injection",
            tonnage=400,
            supports_hot_runner=True,
            hourly_energy_kwh=62.0,
            hourly_operating_cost=240.0,
            status="active",
        )
    )
    edited_ds.molds[0].compatible_machines.append("P-400T")
    edited_ds.orders.append(
        ProductionOrder(
            order_id="ORD-25",
            customer="Studio Test Client",
            sku_name="28mm Studio Cap — Yellow",
            mold_id="M-01",
            resin_code="HDPE",
            color="Yellow",
            quantity_pcs=50_000,
            part_weight_g=2.8,
            max_regrind_pct=0.0,
            due_hr=210.0,
            late_penalty_per_hr=400.0,
            is_export=True,
        )
    )
    edited_res = solve_plant_schedule(
        edited_ds,
        SolverConfig(physics=PlantPhysicsConfig(horizon_hrs=240, max_solve_seconds=3.0)),
    )
    assert edited_res.audit.all_hard_constraints_passed is True
    assert edited_res.optimized.kpis.total_orders == 25
    assert edited_res.audit.solver_params["horizon_hrs"] == 240
    assert any(p.machine_id == "P-400T" for p in edited_res.optimized.press_summaries)
    assert any(j.order_id == "ORD-25" and j.scheduled for j in edited_res.optimized.jobs)
