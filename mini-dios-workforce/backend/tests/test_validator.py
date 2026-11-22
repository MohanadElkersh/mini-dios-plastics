"""Tests for Mini-DIOS Plastics Pre-Solve Anomaly Validator (`validate_plant_data`)."""
from __future__ import annotations

from core.ontology import (
    MoldPmLock,
    ProductionOrder,
    ResinShortage,
    ScenarioDisruptions,
    SolverConfig,
    validate_plant_data,
)
from core.seed import default_config, demo_dataset


def test_demo_plant_is_ready_and_flags_m04_pm_warning():
    ds = demo_dataset()
    rep = validate_plant_data(ds, default_config())
    assert rep.ready is True
    assert rep.error_count == 0
    assert rep.summary["presses_total"] == 6
    assert rep.summary["molds_total"] == 10
    assert rep.summary["resins_total"] == 5
    assert rep.summary["orders_total"] == 24
    codes = [i.code for i in rep.issues]
    assert "MOLD_PM_THRESHOLD_EXCEEDED" in codes
    m04_issue = next(i for i in rep.issues if i.code == "MOLD_PM_THRESHOLD_EXCEEDED")
    assert m04_issue.entity_id == "M-04"


def test_detects_order_with_zero_active_compatible_presses():
    ds = demo_dataset()
    # Mark both P-150T and P-250T down -> M-01 orders have zero compatible active presses
    for p in ds.presses:
        if p.machine_id in ("P-150T", "P-250T"):
            p.status = "down"
    rep = validate_plant_data(ds, default_config())
    assert rep.ready is False
    assert rep.error_count >= 1
    assert any(i.code == "ORDER_NO_COMPATIBLE_PRESS" for i in rep.issues)


def test_detects_hot_runner_press_incompatibility():
    ds = demo_dataset()
    # Assign a hot-runner mold M-01 exclusively to cold-runner press P-500T
    for m in ds.molds:
        if m.mold_id == "M-01":
            m.compatible_machines = ["P-500T"]
    rep = validate_plant_data(ds, default_config())
    assert rep.ready is False
    assert any(i.code == "ORDER_NO_COMPATIBLE_PRESS" for i in rep.issues)


def test_detects_resin_inventory_deficit_under_shortage():
    ds = demo_dataset()
    cfg = SolverConfig(
        scenarios=ScenarioDisruptions(
            resin_shortages=[ResinShortage(resin_code="HDPE", available_pct_reduction=80.0)]
        )
    )
    rep = validate_plant_data(ds, cfg)
    assert rep.ready is True  # Warning (solver handles scarcity gracefully)
    assert any(i.code == "RESIN_INVENTORY_DEFICIT" and i.entity_id == "HDPE" for i in rep.issues)


def test_detects_impossible_drying_plus_run_deadline():
    ds = demo_dataset()
    # PET requires 6h pre-drying + ~15h production -> due_hr=10h is physically impossible
    ds.orders.append(
        ProductionOrder(
            order_id="ORD-IMPOSSIBLE",
            customer="Rush Test",
            sku_name="Impossible PET Preform",
            mold_id="M-05",
            resin_code="PET",
            color="Natural",
            quantity_pcs=50_000,
            part_weight_g=28.0,
            max_regrind_pct=0.0,
            due_hr=10.0,
            late_penalty_per_hr=500.0,
            is_export=True,
        )
    )
    rep = validate_plant_data(ds, default_config())
    assert any(i.code == "IMPOSSIBLE_DEADLINE" and i.entity_id == "ORD-IMPOSSIBLE" for i in rep.issues)


def test_manual_pm_lock_clears_unscheduled_pm_warning():
    ds = demo_dataset()
    cfg = SolverConfig(
        scenarios=ScenarioDisruptions(mold_pm_locks=[MoldPmLock(mold_id="M-04", duration_hrs=6.0)])
    )
    rep = validate_plant_data(ds, cfg)
    assert not any(i.code == "MOLD_PM_THRESHOLD_EXCEEDED" and i.entity_id == "M-04" for i in rep.issues)
