"""Deterministic financial engine unit tests for Mini-DIOS Plastics."""
from __future__ import annotations

import pytest

from core.seed import default_config, demo_dataset
from core.solver import solve_plant_schedule


def test_unit_selling_price_delta_flows_to_revenue_and_net_profit():
    ds_base = demo_dataset()
    cfg = default_config()
    res_base = solve_plant_schedule(ds_base, cfg)

    # Increase unit_selling_price on ORD-01 (guaranteed scheduled) by +0.01 SAR/pc
    ds_up = demo_dataset()
    target_order = next(o for o in ds_up.orders if o.order_id == "ORD-01")
    delta_price = 0.01
    expected_rev_delta = round(
        target_order.quantity_pcs * delta_price * (1.0 - target_order.discount_pct / 100.0),
        2,
    )
    target_order.unit_selling_price = round(target_order.unit_selling_price + delta_price, 4)

    res_up = solve_plant_schedule(ds_up, cfg)

    actual_rev_delta = round(
        res_up.financials.optimized.recognized_revenue
        - res_base.financials.optimized.recognized_revenue,
        2,
    )
    actual_profit_delta = round(
        res_up.financials.optimized.net_operating_profit
        - res_base.financials.optimized.net_operating_profit,
        2,
    )

    assert actual_rev_delta == pytest.approx(expected_rev_delta, abs=0.5)
    assert actual_profit_delta == pytest.approx(expected_rev_delta, abs=0.5)


def test_weekly_fixed_overhead_reduces_net_profit_one_for_one():
    ds = demo_dataset()
    cfg_base = default_config()
    res_base = solve_plant_schedule(ds, cfg_base)

    overhead_bump = 5000.0
    cfg_high = default_config()
    cfg_high.physics.weekly_fixed_overhead += overhead_bump
    res_high = solve_plant_schedule(ds, cfg_high)

    # Gross profit and total weekly savings must be unchanged
    assert res_high.financials.optimized.gross_profit == pytest.approx(
        res_base.financials.optimized.gross_profit, abs=0.01
    )
    assert res_high.financials.total_weekly_savings == pytest.approx(
        res_base.financials.total_weekly_savings, abs=0.01
    )

    # Net operating profit drops 1-for-1 by overhead_bump
    profit_drop = round(
        res_base.financials.optimized.net_operating_profit
        - res_high.financials.optimized.net_operating_profit,
        2,
    )
    assert profit_drop == pytest.approx(overhead_bump, abs=0.01)


def test_annual_projected_savings_formula():
    ds = demo_dataset()
    cfg = default_config()
    cfg.physics.annual_operating_weeks = 48
    res = solve_plant_schedule(ds, cfg)

    fin = res.financials
    assert fin.annual_operating_weeks == 48
    assert fin.annual_projected_savings == pytest.approx(
        round(fin.total_weekly_savings * 48, 2), abs=0.02
    )
    assert fin.monthly_projected_savings == pytest.approx(
        round(fin.total_weekly_savings * 4.33, 2), abs=0.02
    )


def test_cpsat_net_profit_beats_fifo_baseline():
    ds = demo_dataset()
    cfg = default_config()
    res = solve_plant_schedule(ds, cfg)

    fin = res.financials
    assert fin.optimized.net_operating_profit > fin.baseline.net_operating_profit
    assert fin.total_weekly_savings > 0
    assert 15.0 <= fin.optimized.gross_margin_pct <= 40.0
    assert len(fin.order_profitability) == len(ds.orders)
