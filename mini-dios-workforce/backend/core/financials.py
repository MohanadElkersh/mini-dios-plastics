"""Deterministic Financial Engine for Mini-DIOS Plastics (Zero LLM Math).

Computes side-by-side revenue, itemized production costs, gross & net profit margins,
weekly/monthly/annualized savings (CP-SAT Optimized vs. Naive FIFO Baseline), and
per-order profitability in the active currency (SAR or EGP).
"""
from __future__ import annotations

from typing import Optional

from .ontology import (
    FinancialReport,
    OrderProfitabilityItem,
    PlanFinancials,
    PlantDataset,
    SavingsBreakdown,
    SchedulePlan,
    SolverConfig,
    WorkforceResult,
    convert_sar_to_currency,
)


def _compute_plan_financials(
    dataset: PlantDataset,
    plan: SchedulePlan,
    config: SolverConfig,
    total_booked_rev: float,
    labor_cost: float = 0.0,
) -> PlanFinancials:
    cur = config.currency
    fx = config.fx_egp_per_sar
    to_cur = lambda sar: convert_sar_to_currency(sar, cur, fx)
    ph = config.physics

    scheduled_ids = {j.order_id for j in plan.jobs if j.scheduled}
    recognized_sar = sum(
        o.quantity_pcs * o.unit_selling_price * (1.0 - o.discount_pct / 100.0)
        for o in dataset.orders
        if o.order_id in scheduled_ids
    )
    recognized_rev = to_cur(recognized_sar)
    at_risk_rev = round(max(0.0, total_booked_rev - recognized_rev), 2)

    k = plan.kpis
    direct_resin = round(k.resin_material_cost, 2)
    purge_gross = round(k.purge_scrap_cost, 2)
    recovery_credit = round(purge_gross * (ph.scrap_regrind_recovery_pct / 100.0), 2)
    purge_net = round(purge_gross - recovery_credit, 2)
    energy_and_oper = round(k.energy_cost + k.operating_cost, 2)
    late_pen = round(k.late_penalty_cost, 2)
    wip_cost = round(k.wip_holding_cost, 2)

    labor_cost = round(labor_cost, 2)
    variable_cost = round(
        direct_resin + purge_net + energy_and_oper + late_pen + wip_cost + labor_cost, 2
    )
    fixed_overhead = to_cur(ph.weekly_fixed_overhead)
    total_operating_cost = round(variable_cost + fixed_overhead, 2)

    gross_profit = round(recognized_rev - variable_cost, 2)
    gross_margin_pct = (
        round((gross_profit / recognized_rev) * 100.0, 2) if recognized_rev > 1e-6 else 0.0
    )
    net_operating_profit = round(gross_profit - fixed_overhead, 2)
    net_margin_pct = (
        round((net_operating_profit / recognized_rev) * 100.0, 2)
        if recognized_rev > 1e-6
        else 0.0
    )

    return PlanFinancials(
        total_booked_revenue=total_booked_rev,
        recognized_revenue=recognized_rev,
        at_risk_or_unscheduled_revenue=at_risk_rev,
        direct_resin_cost=direct_resin,
        purge_scrap_cost=purge_net,
        purge_scrap_gross_cost=purge_gross,
        purge_scrap_recovery_credit=recovery_credit,
        energy_and_press_operating_cost=energy_and_oper,
        late_delivery_penalties=late_pen,
        wip_holding_cost=wip_cost,
        direct_labor_and_overtime_cost=labor_cost,
        variable_production_cost=variable_cost,
        weekly_fixed_overhead=fixed_overhead,
        total_operating_cost=total_operating_cost,
        gross_profit=gross_profit,
        gross_margin_pct=gross_margin_pct,
        net_operating_profit=net_operating_profit,
        net_margin_pct=net_margin_pct,
    )


def compute_financial_report(
    dataset: PlantDataset,
    config: SolverConfig,
    baseline: SchedulePlan,
    optimized: SchedulePlan,
    workforce: Optional[WorkforceResult] = None,
) -> FinancialReport:
    """Compute complete side-by-side FinancialReport for Baseline vs. CP-SAT Optimized."""
    cur = config.currency
    fx = config.fx_egp_per_sar
    to_cur = lambda sar: convert_sar_to_currency(sar, cur, fx)
    ph = config.physics

    total_booked_sar = sum(
        o.quantity_pcs * o.unit_selling_price * (1.0 - o.discount_pct / 100.0)
        for o in dataset.orders
    )
    total_booked_rev = to_cur(total_booked_sar)

    base_labor = workforce.baseline.kpis.total_labor_cost if workforce else 0.0
    opt_labor = workforce.optimized.kpis.total_labor_cost if workforce else 0.0
    base_fin = _compute_plan_financials(dataset, baseline, config, total_booked_rev, base_labor)
    opt_fin = _compute_plan_financials(dataset, optimized, config, total_booked_rev, opt_labor)

    unlocked_hrs = round(
        max(0.0, baseline.kpis.changeover_hours - optimized.kpis.changeover_hours), 2
    )
    avg_hr_rev_rate = (
        opt_fin.recognized_revenue / max(optimized.kpis.total_run_hours, 1e-6)
        if optimized.kpis.total_run_hours > 1e-6
        else 0.0
    )
    unlocked_rev_potential = round(unlocked_hrs * avg_hr_rev_rate, 2)

    total_weekly_savings = round(
        (base_fin.total_operating_cost - opt_fin.total_operating_cost)
        + (opt_fin.recognized_revenue - base_fin.recognized_revenue),
        2,
    )

    if abs(base_fin.net_operating_profit) > 1e-6:
        profit_lift_pct = round(
            ((opt_fin.net_operating_profit - base_fin.net_operating_profit)
             / abs(base_fin.net_operating_profit))
            * 100.0,
            2,
        )
    else:
        profit_lift_pct = 0.0

    savings_breakdown = SavingsBreakdown(
        purge_scrap_saved=round(base_fin.purge_scrap_cost - opt_fin.purge_scrap_cost, 2),
        energy_and_operating_saved=round(
            base_fin.energy_and_press_operating_cost - opt_fin.energy_and_press_operating_cost,
            2,
        ),
        avoided_late_penalties=round(
            base_fin.late_delivery_penalties - opt_fin.late_delivery_penalties, 2
        ),
        wip_holding_saved=round(base_fin.wip_holding_cost - opt_fin.wip_holding_cost, 2),
        regrind_blend_savings=round(
            base_fin.direct_resin_cost - opt_fin.direct_resin_cost, 2
        ),
        labor_and_overtime_saved=round(
            base_fin.direct_labor_and_overtime_cost - opt_fin.direct_labor_and_overtime_cost, 2
        ),
    )

    monthly_projected = round(total_weekly_savings * 4.33, 2)
    annual_projected = round(total_weekly_savings * ph.annual_operating_weeks, 2)

    orders_by_id = {o.order_id: o for o in dataset.orders}
    recovery_factor = 1.0 - (ph.scrap_regrind_recovery_pct / 100.0)
    order_profitability: list[OrderProfitabilityItem] = []

    for job in optimized.jobs:
        o = orders_by_id.get(job.order_id)
        if o is None:
            continue
        unit_price_cur = to_cur(o.unit_selling_price)
        order_rev = (
            to_cur(o.quantity_pcs * o.unit_selling_price * (1.0 - o.discount_pct / 100.0))
            if job.scheduled
            else 0.0
        )
        direct_resin = round(job.resin_cost, 2)
        alloc_energy = round(job.energy_cost + job.operating_cost, 2)
        alloc_purge = round(job.purge_cost * recovery_factor, 2)
        late_pen = round(job.late_penalty_cost, 2)
        net_profit = round(
            order_rev - (direct_resin + alloc_energy + alloc_purge + late_pen), 2
        )
        margin_pct = (
            round((net_profit / order_rev) * 100.0, 1)
            if order_rev > 1e-6
            else (-100.0 if late_pen > 0 else 0.0)
        )
        order_profitability.append(
            OrderProfitabilityItem(
                order_id=o.order_id,
                customer=o.customer,
                sku_name=o.sku_name,
                quantity_pcs=o.quantity_pcs,
                unit_selling_price=unit_price_cur,
                discount_pct=o.discount_pct,
                order_revenue=order_rev,
                direct_resin_cost=direct_resin,
                allocated_energy_cost=alloc_energy,
                allocated_purge_cost=alloc_purge,
                late_penalty=late_pen,
                net_order_profit=net_profit,
                order_margin_pct=margin_pct,
                scheduled=job.scheduled,
            )
        )

    return FinancialReport(
        currency=cur,
        annual_operating_weeks=ph.annual_operating_weeks,
        scrap_regrind_recovery_pct=ph.scrap_regrind_recovery_pct,
        baseline=base_fin,
        optimized=opt_fin,
        unlocked_capacity_hours=unlocked_hrs,
        unlocked_capacity_revenue_potential=unlocked_rev_potential,
        total_weekly_savings=total_weekly_savings,
        profit_lift_pct=profit_lift_pct,
        savings_breakdown=savings_breakdown,
        monthly_projected_savings=monthly_projected,
        annual_projected_savings=annual_projected,
        order_profitability=order_profitability,
    )
