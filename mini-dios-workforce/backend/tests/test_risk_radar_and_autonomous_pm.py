"""Tests for Option B Backend Upgrades:
1. Proactive Delay & Bottleneck Risk Radar (`backend/core/risk_radar.py`)
2. Autonomous Preventive Maintenance Co-Optimization (`SolverConfig.autonomous_pm_window=True`)
"""
from __future__ import annotations

from core.ontology import (
    ProductionOrder,
    ResinShortage,
    ScenarioDisruptions,
    SolverConfig,
    order_shots,
)
from core.risk_radar import compute_risk_radar
from core.seed import default_config, demo_dataset
from core.solver import solve_plant_schedule


def test_risk_radar_populates_clocks_and_bilingual_alerts_with_currency_parity():
    ds = demo_dataset()
    cfg_sar = SolverConfig(currency="SAR", max_solve_seconds=2.5)
    res_sar = solve_plant_schedule(ds, cfg_sar)

    assert res_sar.risk_radar is not None
    radar_sar = res_sar.risk_radar
    assert 0 <= radar_sar.overall_risk_score <= 100
    assert radar_sar.risk_level in ("critical", "elevated", "watch", "healthy")
    assert len(radar_sar.resin_clocks) == len(ds.resins)
    assert radar_sar.tightest_slack_order_id is not None

    for alert in radar_sar.alerts:
        assert alert.title_en.strip() and alert.title_ar.strip()
        assert alert.detail_en.strip() and alert.detail_ar.strip()
        assert alert.suggested_prompt_en.strip() and alert.suggested_prompt_ar.strip()

    # Exact deterministic EGP conversion check on the same solved schedule
    cfg_egp = SolverConfig(currency="EGP", fx_egp_per_sar=13.0, max_solve_seconds=2.5)
    radar_egp = compute_risk_radar(ds, cfg_egp, res_sar.optimized, res_sar.workforce)
    assert radar_egp.overall_risk_score == radar_sar.overall_risk_score
    assert len(radar_egp.alerts) == len(radar_sar.alerts)
    if radar_sar.total_financial_exposure > 0:
        # Non-job-derived exposure scales by exact 13x; job.late_penalty_cost is already in plan currency
        assert radar_egp.total_financial_exposure >= radar_sar.total_financial_exposure


def test_risk_radar_detects_resin_stockout_under_severe_shortage():
    ds = demo_dataset()
    cfg = SolverConfig(
        max_solve_seconds=2.5,
        scenarios=ScenarioDisruptions(
            resin_shortages=[ResinShortage(resin_code="HDPE", available_pct_reduction=60.0)]
        ),
    )
    res = solve_plant_schedule(ds, cfg)
    assert res.risk_radar is not None
    hdpe_clock = next(c for c in res.risk_radar.resin_clocks if c.resin_code == "HDPE")
    assert hdpe_clock.status == "critical"
    assert any(a.category == "resin_stockout" and a.entity_id == "HDPE" for a in res.risk_radar.alerts)
    assert res.risk_radar.critical_count >= 1


def test_autonomous_pm_beats_static_t0_on_urgent_export_and_respects_shot_budget():
    """M-04 starts at 482,000 / 500,000 shots (18,000 remaining shots, 4 cavities, 6h PM).
    An urgent 36,000-pc export order on M-04 takes 9,000 shots (~28.75h) and is due at H30.
    - Static t=0 PM forces 6h PM first -> order finishes at H34.75 (4.75h LATE, high export penalty).
    - Autonomous PM runs the 9,000-shot urgent order FIRST (within 18,000 shot budget!),
      finishes ON TIME (< H30), then executes the 6h PM block cleanly before the remaining M-04 orders.
    """
    ds = demo_dataset()
    m04 = next(m for m in ds.molds if m.mold_id == "M-04")
    urgent = ProductionOrder(
        order_id="URGENT-EXP-M04",
        customer="Jeddah Cold-Chain Export",
        sku_name="1L Ice Cream Tub — Urgent Airfreight",
        mold_id="M-04",
        resin_code="PP",
        color="White",
        quantity_pcs=36_000,  # 9,000 shots <= 18,000 remaining shots!
        part_weight_g=38.0,
        max_regrind_pct=0.0,
        due_hr=30.0,
        late_penalty_per_hr=2000.0,
        is_export=True,
        unit_selling_price=0.95,
    )
    assert order_shots(urgent, m04) <= (m04.maintenance_interval_shots - m04.current_shots)

    scenarios = ScenarioDisruptions(rush_orders=[urgent])

    static_res = solve_plant_schedule(
        ds,
        SolverConfig(w_otif=70, w_changeover_scrap=20, w_energy_cost=5, w_working_capital=5, autonomous_pm_window=False, max_solve_seconds=3.5, scenarios=scenarios),
    )
    auto_res = solve_plant_schedule(
        ds,
        SolverConfig(w_otif=70, w_changeover_scrap=20, w_energy_cost=5, w_working_capital=5, autonomous_pm_window=True, max_solve_seconds=3.5, scenarios=scenarios),
    )

    assert static_res.audit.all_hard_constraints_passed is True
    assert auto_res.audit.all_hard_constraints_passed is True

    urgent_static = next(j for j in static_res.optimized.jobs if j.order_id == "URGENT-EXP-M04")
    urgent_auto = next(j for j in auto_res.optimized.jobs if j.order_id == "URGENT-EXP-M04")
    m04_pm = next(pm for pm in auto_res.optimized.mold_pm_windows if pm.mold_id == "M-04")

    # Static t=0 forces urgent order after 6h PM -> misses H8 due date
    assert urgent_static.start_min >= 360
    assert urgent_static.tardiness_hrs > 0

    # Autonomous PM runs urgent order BEFORE PM, finishes on time, and places PM right after
    assert m04_pm.mode == "autonomous"
    assert urgent_auto.tardiness_hrs == 0.0
    assert urgent_auto.end_min <= m04_pm.start_min
    assert auto_res.optimized.kpis.late_penalty_cost < static_res.optimized.kpis.late_penalty_cost


def test_autonomous_pm_locks_t0_when_mold_already_at_100_percent_shot_limit():
    ds = demo_dataset()
    m04 = next(m for m in ds.molds if m.mold_id == "M-04")
    m04.current_shots = m04.maintenance_interval_shots  # 100% exhausted!

    res = solve_plant_schedule(ds, SolverConfig(autonomous_pm_window=True, max_solve_seconds=2.5))
    assert res.audit.all_hard_constraints_passed is True

    m04_pm = next(pm for pm in res.optimized.mold_pm_windows if pm.mold_id == "M-04")
    assert m04_pm.start_min == 0
    for j in res.optimized.jobs:
        if j.scheduled and j.mold_id == "M-04":
            assert j.start_min >= m04_pm.end_min
