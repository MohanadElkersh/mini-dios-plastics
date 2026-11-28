"""Capable-to-Promise (CTP) Non-Destructive Rush-Order Quoter for Mini-DIOS Plastics.

Answers in seconds without mutating the active schedule or database:
  1. Can we take this urgent order (`ON_TIME` | `LATE` | `INFEASIBLE`)?
  2. Which press runs it and when can it ship (`scheduled_start_hr`, `scheduled_end_hr`, `slack_or_delay_hrs`)?
  3. What does it really cost us (`direct_resin_cost`, `extra_purge_cost`, `extra_changeover_cost`,
     `extra_electricity_cost`, `extra_overtime_labor_cost`, `extra_wip_holding_cost`,
     `total_marginal_cost`, `net_profit_contribution`, `min_breakeven_unit_price`)?
  4. Whose existing confirmed order gets bumped (`bumped_orders`, highlighting any export cut-off breaches)?
"""
from __future__ import annotations

import copy
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from .ontology import (
     COLOR_RANKS,
    Currency,
    Mold,
    PlasticColor,
    PlantDataset,
    ProductionOrder,
    ResinCode,
    SolveResult,
    SolverConfig,
    convert_sar_to_currency,
    order_duration_mins,
    order_gross_weight_kg,
)
from .seed import default_config, demo_dataset
from .solver import DatasetValidationError, solve_plant_schedule

CTPVerdict = Literal["ON_TIME", "LATE", "INFEASIBLE"]


class CTPQuoteRequest(BaseModel):
    """Input payload for `POST /api/quote/ctp`."""

    customer: str = Field(default="Al-Marai / Gulf Retail Export", min_length=1)
    sku_name: str = Field(default="28mm Tamper-Evident Dairy Cap (Rush)", min_length=1)
    mold_id: str = Field(default="M-01", min_length=1)
    qty_units: int = Field(default=40_000, gt=0)
    quantity_pcs: Optional[int] = Field(default=None, gt=0)
    part_weight_g: Optional[float] = Field(default=None, gt=0)
    resin: Optional[ResinCode] = None
    resin_code: Optional[ResinCode] = None
    color: PlasticColor = "White"
    target_due_hour: float = Field(default=96.0, ge=4.0, le=336.0)
    due_hr: Optional[float] = Field(default=None, ge=4.0, le=336.0)
    unit_price: Optional[float] = Field(default=None, ge=0.0, description="Selling price per unit in active currency")
    unit_selling_price: Optional[float] = Field(default=None, ge=0.0)
    is_export: bool = True
    max_regrind_pct: float = Field(default=0.0, ge=0.0, le=50.0)
    allow_peak_or_overtime: bool = True
    late_penalty_per_hr: Optional[float] = Field(default=None, ge=0.0)
    currency: Optional[Currency] = None
    dataset: Optional[PlantDataset] = None
    config: Optional[SolverConfig] = None
    current_result: Optional[SolveResult] = None

    @model_validator(mode="after")
    def _normalize_aliases(self) -> "CTPQuoteRequest":
        if self.quantity_pcs is not None and self.qty_units == 40_000:
            self.qty_units = self.quantity_pcs
        if self.resin is None and self.resin_code is not None:
            self.resin = self.resin_code
        if self.due_hr is not None and abs(self.target_due_hour - 96.0) < 1e-6:
            self.target_due_hour = self.due_hr
        if self.unit_price is None and self.unit_selling_price is not None:
            self.unit_price = self.unit_selling_price
        return self


class CTPFinancialImpact(BaseModel):
    currency: Currency
    gross_revenue: float
    offered_unit_price: float
    direct_resin_cost: float
    extra_purge_scrap_kg: float
    extra_purge_cost: float
    extra_changeover_hrs: float
    extra_changeover_cost: float
    extra_electricity_cost: float
    extra_overtime_labor_cost: float
    extra_wip_holding_cost: float
    extra_late_penalty_cost: float = 0.0
    total_marginal_cost: float
    net_profit_contribution: float
    margin_pct: float
    min_breakeven_unit_price: float


class CTPBumpedOrder(BaseModel):
    order_id: str
    customer: str
    sku_name: str
    old_end_hr: float
    new_end_hr: float
    due_hr: float
    delay_hrs: float
    breaches_cutoff: bool
    is_export: bool


class CTPQuoteResult(BaseModel):
    verdict: CTPVerdict
    order_id: str
    customer: str
    sku_name: str
    mold_id: str
    mold_name: str
    resin_code: ResinCode
    color: PlasticColor
    qty_units: int
    part_weight_g: float
    gross_weight_kg: float
    est_run_hrs: float
    assigned_press_id: Optional[str] = None
    assigned_press_name: Optional[str] = None
    scheduled_start_hr: Optional[float] = None
    scheduled_end_hr: Optional[float] = None
    target_due_hour: float
    slack_or_delay_hrs: float
    financial_impact: CTPFinancialImpact
    bumped_orders: list[CTPBumpedOrder] = Field(default_factory=list)
    export_cutoffs_breached: int = 0
    risk_score_before: int = 0
    risk_score_after: int = 0
    solve_time_ms: int = 0
    active_engine: str = "legacy_cpsat_v1"
    tradeoff_summary_en: str
    tradeoff_summary_ar: str
    candidate_order: ProductionOrder


def _infer_mold_defaults(
    dataset: PlantDataset, mold: Mold
) -> tuple[ResinCode, float, float]:
    """Infer default `(resin_code, part_weight_g, unit_selling_price_sar)` from existing orders on `mold`."""
    matching = [o for o in dataset.orders if o.mold_id == mold.mold_id]
    if matching:
        ref = matching[0]
        price_sar = ref.unit_selling_price if ref.unit_selling_price > 0 else round(max(0.05, ref.part_weight_g * 0.014), 4)
        return ref.resin_code, ref.part_weight_g, price_sar
    # Sensible physics fallback based on cavity count
    if mold.cavities >= 16:
        return "HDPE", 3.2, 0.055
    if mold.cavities >= 4:
        return "PP", 28.0, 0.42
    return "HDPE", 140.0, 2.15


def evaluate_ctp_rush_order(
    req: CTPQuoteRequest,
    fallback_dataset: Optional[PlantDataset] = None,
    fallback_config: Optional[SolverConfig] = None,
) -> CTPQuoteResult:
    """Run a 100% deterministic, strictly non-destructive Capable-to-Promise (CTP) evaluation.

    Deep-copies the plant state in memory so live workspace data is never mutated.
    """
    base_ds = copy.deepcopy(req.dataset or fallback_dataset or demo_dataset())
    base_cfg = copy.deepcopy(req.config or fallback_config or default_config())
    if req.currency in ("SAR", "EGP"):
        base_cfg = base_cfg.model_copy(update={"currency": req.currency})

    cur: Currency = base_cfg.currency
    fx = base_cfg.fx_egp_per_sar
    to_cur = lambda sar: convert_sar_to_currency(sar, cur, fx)
    to_sar = lambda val: round(val / fx, 6) if cur == "EGP" else round(val, 6)

    molds_by_id = {m.mold_id: m for m in base_ds.molds}
    mold = molds_by_id.get(req.mold_id)
    if mold is None:
        if not base_ds.molds:
            raise ValueError("Plant dataset contains no molds to quote against.")
        mold = base_ds.molds[0]

    def_resin, def_weight_g, def_price_sar = _infer_mold_defaults(base_ds, mold)
    chosen_resin: ResinCode = req.resin or def_resin
    resins_by_code = {r.resin_code: r for r in base_ds.resins}
    if chosen_resin not in resins_by_code and base_ds.resins:
        chosen_resin = base_ds.resins[0].resin_code

    part_weight_g = float(req.part_weight_g if req.part_weight_g is not None else def_weight_g)
    if req.unit_price is not None and req.unit_price > 0:
        unit_price_sar = to_sar(float(req.unit_price))
        offered_unit_price_cur = round(float(req.unit_price), 4)
    else:
        unit_price_sar = def_price_sar
        offered_unit_price_cur = round(to_cur(unit_price_sar), 4)

    late_pen_sar = (
        to_sar(req.late_penalty_per_hr)
        if req.late_penalty_per_hr is not None
        else (750.0 if req.is_export else 420.0)
    )

    # Generate a non-colliding rush order ID
    existing_ids = {o.order_id for o in base_ds.orders} | {o.order_id for o in base_cfg.scenarios.rush_orders}
    seq = 1
    while f"CTP-RUSH-{seq:02d}" in existing_ids:
        seq += 1
    rush_order_id = f"CTP-RUSH-{seq:02d}"

    candidate_order = ProductionOrder(
        order_id=rush_order_id,
        customer=req.customer.strip() or "Rush Export Customer",
        sku_name=req.sku_name.strip() or f"Rush {req.color} {mold.name}",
        mold_id=mold.mold_id,
        resin_code=chosen_resin,
        color=req.color,
        color_rank=COLOR_RANKS[req.color],
        quantity_pcs=int(req.qty_units),
        part_weight_g=part_weight_g,
        max_regrind_pct=0.0 if req.is_export else float(req.max_regrind_pct),
        due_hr=float(req.target_due_hour),
        late_penalty_per_hr=round(float(late_pen_sar), 2),
        is_export=bool(req.is_export),
        container_group_id=None,
        unit_selling_price=round(float(unit_price_sar), 6),
        discount_pct=0.0,
    )

    est_run_hrs = round(order_duration_mins(candidate_order, mold) / 60.0, 2)
    gross_kg = order_gross_weight_kg(candidate_order, mold)

    # Keep CP-SAT tightly bounded (<= 2.2s per solve) for Render Free-Tier 0.1 CPU / 512MB RAM budget
    bounded_solve_secs = min(float(base_cfg.max_solve_seconds), 2.2)
    quote_base_cfg = copy.deepcopy(base_cfg)
    quote_base_cfg.max_solve_seconds = bounded_solve_secs
    quote_base_cfg.physics.max_solve_seconds = bounded_solve_secs

    # 1. Baseline ("Before") solve
    if (
        req.current_result is not None
        and len(req.current_result.optimized.jobs) == len(base_ds.orders) + len(base_cfg.scenarios.rush_orders)
        and req.current_result.currency == cur
    ):
        before_result = req.current_result
    else:
        before_result = solve_plant_schedule(base_ds, quote_base_cfg)

    # 2. Candidate ("After") solve on deep-copied dataset
    cand_ds = copy.deepcopy(base_ds)
    cand_ds.orders.append(copy.deepcopy(candidate_order))
    cand_cfg = copy.deepcopy(quote_base_cfg)
    if req.allow_peak_or_overtime and cand_cfg.avoid_peak_tariff_hrs:
        cand_cfg.avoid_peak_tariff_hrs = False

    try:
        after_result = solve_plant_schedule(cand_ds, cand_cfg)
    except DatasetValidationError:
        after_result = None

    risk_before = before_result.risk_radar.overall_risk_score if before_result.risk_radar else 0
    presses_by_id = {p.machine_id: p for p in base_ds.presses}
    resin_stock = resins_by_code.get(chosen_resin)
    virgin_cost_per_kg_sar = resin_stock.virgin_cost_per_kg if resin_stock else 4.8

    gross_rev_cur = round(to_cur(candidate_order.quantity_pcs * candidate_order.unit_selling_price), 2)

    # Handle unscheduled or infeasible rush job
    rush_job = (
        next((j for j in after_result.optimized.jobs if j.order_id == rush_order_id), None)
        if after_result is not None
        else None
    )

    if (
        after_result is None
        or rush_job is None
        or not rush_job.scheduled
        or after_result.status in ("INFEASIBLE", "MODEL_INVALID", "UNKNOWN")
    ):
        est_resin_cost_cur = round(to_cur(gross_kg * virgin_cost_per_kg_sar), 2)
        min_be_price = round(est_resin_cost_cur / max(1, candidate_order.quantity_pcs), 4)
        reason_en = (
            rush_job.unscheduled_reason
            if (rush_job and rush_job.unscheduled_reason)
            else f"Insufficient {chosen_resin} virgin resin inventory or active press capacity for {mold.mold_id}."
        )
        fin_impact = CTPFinancialImpact(
            currency=cur,
            gross_revenue=gross_rev_cur,
            offered_unit_price=offered_unit_price_cur,
            direct_resin_cost=est_resin_cost_cur,
            extra_purge_scrap_kg=0.0,
            extra_purge_cost=0.0,
            extra_changeover_hrs=0.0,
            extra_changeover_cost=0.0,
            extra_electricity_cost=0.0,
            extra_overtime_labor_cost=0.0,
            extra_wip_holding_cost=0.0,
            extra_late_penalty_cost=0.0,
            total_marginal_cost=est_resin_cost_cur,
            net_profit_contribution=round(gross_rev_cur - est_resin_cost_cur, 2),
            margin_pct=0.0,
            min_breakeven_unit_price=min_be_price,
        )
        return CTPQuoteResult(
            verdict="INFEASIBLE",
            order_id=rush_order_id,
            customer=candidate_order.customer,
            sku_name=candidate_order.sku_name,
            mold_id=mold.mold_id,
            mold_name=mold.name,
            resin_code=chosen_resin,
            color=req.color,
            qty_units=candidate_order.quantity_pcs,
            part_weight_g=part_weight_g,
            gross_weight_kg=gross_kg,
            est_run_hrs=est_run_hrs,
            assigned_press_id=None,
            assigned_press_name=None,
            scheduled_start_hr=None,
            scheduled_end_hr=None,
            target_due_hour=req.target_due_hour,
            slack_or_delay_hrs=round(-est_run_hrs, 2),
            financial_impact=fin_impact,
            bumped_orders=[],
            export_cutoffs_breached=0,
            risk_score_before=risk_before,
            risk_score_after=after_result.risk_radar.overall_risk_score if (after_result and after_result.risk_radar) else risk_before,
            solve_time_ms=after_result.solve_time_ms if after_result else 0,
            active_engine=after_result.active_engine if after_result else before_result.active_engine,
            tradeoff_summary_en=f"CANNOT PROMISE: {reason_en} Replenish {chosen_resin} silo stock or enable non-food regrind override first.",
            tradeoff_summary_ar=f"تعذر الوعد بالتسليم: مخزون خام {chosen_resin} البكر أو سعة المكابس المتوافقة مع القالب {mold.mold_id} لا يكفي. عزز مخزون الصوامع أو ارفع نسبة الريجريند الصناعي أولاً.",
            candidate_order=candidate_order,
        )

    # Scheduled rush job details
    start_hr = round(rush_job.start_min / 60.0, 2)
    end_hr = round(rush_job.end_min / 60.0, 2)
    slack_or_delay_hrs = round(req.target_due_hour - end_hr, 2)
    assigned_press = presses_by_id.get(rush_job.machine_id)

    # Compute bumped / impacted existing orders
    before_jobs_by_id = {j.order_id: j for j in before_result.optimized.jobs}
    bumped_orders: list[CTPBumpedOrder] = []
    for after_job in after_result.optimized.jobs:
        if after_job.order_id == rush_order_id:
            continue
        old_job = before_jobs_by_id.get(after_job.order_id)
        if old_job is None:
            continue
        old_end_hr = round(old_job.end_min / 60.0, 1)
        new_end_hr = round(after_job.end_min / 60.0, 1) if after_job.scheduled else round(cand_cfg.physics.horizon_hrs + 24.0, 1)
        delay_hrs = round(new_end_hr - old_end_hr, 1)
        newly_unscheduled = old_job.scheduled and not after_job.scheduled
        if delay_hrs >= 0.3 or newly_unscheduled:
            breaches = bool(newly_unscheduled or (new_end_hr > after_job.due_hr + 0.05))
            bumped_orders.append(
                CTPBumpedOrder(
                    order_id=after_job.order_id,
                    customer=after_job.customer,
                    sku_name=after_job.sku_name,
                    old_end_hr=old_end_hr,
                    new_end_hr=new_end_hr,
                    due_hr=round(after_job.due_hr, 1),
                    delay_hrs=max(0.1, delay_hrs),
                    breaches_cutoff=breaches,
                    is_export=after_job.is_export,
                )
            )

    bumped_orders.sort(key=lambda b: (not b.breaches_cutoff, not b.is_export, -b.delay_hrs))
    export_breaches = sum(1 for b in bumped_orders if b.is_export and b.breaches_cutoff)

    # Determine Verdict (`ON_TIME` vs `LATE` vs `INFEASIBLE`)
    if end_hr <= req.target_due_hour + 0.05 and export_breaches == 0:
        verdict: CTPVerdict = "ON_TIME"
    else:
        verdict = "LATE"

    # Compute Marginal Financial Impact (all in active currency `cur`)
    # Note: job.resin_cost, job.energy_cost, etc. in SchedulePlan are already converted to `config.currency` by `kpi.py`!
    direct_resin_cur = round(rush_job.resin_cost, 2)

    extra_purge_kg = round(
        max(0.0, after_result.optimized.kpis.purge_scrap_kg - before_result.optimized.kpis.purge_scrap_kg),
        2,
    )
    extra_purge_cost_cur = round(
        max(
            0.0,
            after_result.financials.optimized.purge_scrap_cost
            - before_result.financials.optimized.purge_scrap_cost,
        ),
        2,
    )

    extra_co_hrs = round(
        max(0.0, after_result.optimized.kpis.changeover_hours - before_result.optimized.kpis.changeover_hours),
        2,
    )
    press_oper_rate_sar = assigned_press.hourly_operating_cost if assigned_press else 200.0
    extra_changeover_cost_cur = round(to_cur(extra_co_hrs * press_oper_rate_sar), 2)

    # Total energy + press operating delta minus changeover operating portion to prevent any overlap
    raw_energy_oper_delta_cur = round(
        max(
            0.0,
            after_result.financials.optimized.energy_and_press_operating_cost
            - before_result.financials.optimized.energy_and_press_operating_cost,
        ),
        2,
    )
    extra_electricity_cost_cur = round(
        max(round(rush_job.energy_cost + rush_job.operating_cost, 2), raw_energy_oper_delta_cur),
        2,
    )

    extra_ot_labor_cur = round(
        max(
            0.0,
            after_result.financials.optimized.direct_labor_and_overtime_cost
            - before_result.financials.optimized.direct_labor_and_overtime_cost,
        ),
        2,
    )

    extra_wip_cur = round(
        max(
            0.0,
            after_result.financials.optimized.wip_holding_cost
            - before_result.financials.optimized.wip_holding_cost,
        ),
        2,
    )

    extra_late_pen_cur = round(
        max(
            0.0,
            after_result.financials.optimized.late_delivery_penalties
            - before_result.financials.optimized.late_delivery_penalties,
        ),
        2,
    )

    total_marginal_cost_cur = round(
        direct_resin_cur
        + extra_purge_cost_cur
        + extra_changeover_cost_cur
        + extra_electricity_cost_cur
        + extra_ot_labor_cur
        + extra_wip_cur
        + extra_late_pen_cur,
        2,
    )

    net_profit_cur = round(gross_rev_cur - total_marginal_cost_cur, 2)
    margin_pct = round((net_profit_cur / gross_rev_cur) * 100.0, 1) if gross_rev_cur > 1e-6 else 0.0
    min_breakeven_unit_price = round(total_marginal_cost_cur / max(1, candidate_order.quantity_pcs), 4)

    risk_after = after_result.risk_radar.overall_risk_score if after_result.risk_radar else risk_before

    # Commander-Grade Bilingual Trade-Off Explanations
    if verdict == "ON_TIME":
        bump_clause_en = (
            f"shifts {len(bumped_orders)} existing order(s) with 0 export cut-off breaches"
            if bumped_orders
            else "causes zero delays to existing orders"
        )
        bump_clause_ar = (
            f"يزحزح {len(bumped_orders)} أمر قائم بدون أي خرق لمواعيد التصدير"
            if bumped_orders
            else "لا يسبب أي تأخير للأوامر القائمة"
        )
        summary_en = (
            f"CAPABLE TO PROMISE (ON TIME): Assigns to {rush_job.machine_id} finishing at H{end_hr:.1f} "
            f"({slack_or_delay_hrs:+.1f}h buffer vs H{req.target_due_hour:.0f} due), adds {extra_purge_kg:.1f}kg purge scrap, "
            f"{bump_clause_en}, and yields {cur} {net_profit_cur:,.0f} net profit ({margin_pct:.1f}% margin; break-even floor {cur} {min_breakeven_unit_price:.3f}/pc)."
        )
        summary_ar = (
            f"قابل للوعد والتسليم بالموعد: يُجدول على الماكينة {rush_job.machine_id} وينتهي عند س{end_hr:.1f} "
            f"(بفائض أمان {slack_or_delay_hrs:+.1f} ساعة قبل الموعد س{req.target_due_hour:.0f})، يضيف {extra_purge_kg:.1f} كجم هالك تنظيف، "
            f"{bump_clause_ar}، ويحقق صافي ربح {net_profit_cur:,.0f} {cur} (هامش {margin_pct:.1f}% • سعر التعادل الأدنى {min_breakeven_unit_price:.3f} {cur}/قطعة)."
        )
    else:
        late_hrs = round(max(0.0, end_hr - req.target_due_hour), 1)
        breach_clause_en = (
            f"and pushes {export_breaches} confirmed export order(s) past port cut-off"
            if export_breaches > 0
            else f"(+{late_hrs:.1f}h past requested H{req.target_due_hour:.0f} target)"
        )
        breach_clause_ar = (
            f"ويدفع {export_breaches} أمر تصدير مؤكد لتجاوز موعد قطع الميناء"
            if export_breaches > 0
            else f"(بتأخير +{late_hrs:.1f} ساعة بعد الموعد المطلوب س{req.target_due_hour:.0f})"
        )
        summary_en = (
            f"CAUTION — LATE / CUT-OFF IMPACT: Earliest completion on {rush_job.machine_id} is H{end_hr:.1f} "
            f"{breach_clause_en}. Total marginal cost is {cur} {total_marginal_cost_cur:,.0f} "
            f"(break-even floor {cur} {min_breakeven_unit_price:.3f}/pc; net contribution {cur} {net_profit_cur:,.0f})."
        )
        summary_ar = (
            f"تنبيه — تأخير أو تأثير على التصدير: أقرب اكتمال على الماكينة {rush_job.machine_id} عند س{end_hr:.1f} "
            f"{breach_clause_ar}. التكلفة الحدية الإجمالية {total_marginal_cost_cur:,.0f} {cur} "
            f"(سعر التعادل الأدنى {min_breakeven_unit_price:.3f} {cur}/قطعة • الصافي {net_profit_cur:,.0f} {cur})."
        )

    fin_impact = CTPFinancialImpact(
        currency=cur,
        gross_revenue=gross_rev_cur,
        offered_unit_price=offered_unit_price_cur,
        direct_resin_cost=direct_resin_cur,
        extra_purge_scrap_kg=extra_purge_kg,
        extra_purge_cost=extra_purge_cost_cur,
        extra_changeover_hrs=extra_co_hrs,
        extra_changeover_cost=extra_changeover_cost_cur,
        extra_electricity_cost=extra_electricity_cost_cur,
        extra_overtime_labor_cost=extra_ot_labor_cur,
        extra_wip_holding_cost=extra_wip_cur,
        extra_late_penalty_cost=extra_late_pen_cur,
        total_marginal_cost=total_marginal_cost_cur,
        net_profit_contribution=net_profit_cur,
        margin_pct=margin_pct,
        min_breakeven_unit_price=min_breakeven_unit_price,
    )

    return CTPQuoteResult(
        verdict=verdict,
        order_id=rush_order_id,
        customer=candidate_order.customer,
        sku_name=candidate_order.sku_name,
        mold_id=mold.mold_id,
        mold_name=mold.name,
        resin_code=chosen_resin,
        color=req.color,
        qty_units=candidate_order.quantity_pcs,
        part_weight_g=part_weight_g,
        gross_weight_kg=gross_kg,
        est_run_hrs=est_run_hrs,
        assigned_press_id=rush_job.machine_id,
        assigned_press_name=rush_job.machine_name,
        scheduled_start_hr=start_hr,
        scheduled_end_hr=end_hr,
        target_due_hour=req.target_due_hour,
        slack_or_delay_hrs=slack_or_delay_hrs,
        financial_impact=fin_impact,
        bumped_orders=bumped_orders,
        export_cutoffs_breached=export_breaches,
        risk_score_before=risk_before,
        risk_score_after=risk_after,
        solve_time_ms=after_result.solve_time_ms,
        active_engine=after_result.active_engine,
        tradeoff_summary_en=summary_en,
        tradeoff_summary_ar=summary_ar,
        candidate_order=candidate_order,
    )
