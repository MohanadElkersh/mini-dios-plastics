"""Deterministic Plastics KPI Evaluator, Gantt Builder & Executive ROI Scorecard."""
from __future__ import annotations

from collections import defaultdict
from typing import Optional

from .ontology import (
    GanttBlock,
    KpiBlock,
    MetricCompare,
    PlantDataset,
    PressSummary,
    ResinUsageSummary,
    ScheduledJob,
    ScheduledMoldPm,
    SchedulePlan,
    Scorecard,
    SolverConfig,
    convert_sar_to_currency,
    order_duration_mins,
    order_gross_weight_kg,
    peak_overlap_mins,
    ramadan_labor_multiplier,
    transition_penalty,
)

WIP_HOLDING_RATE_PER_HR = 0.0004  # ~0.04% of order resin value per hour of early WIP holding


def build_schedule_plan(
    dataset: PlantDataset,
    config: SolverConfig,
    raw_assignments: list[dict],
    mold_pm_durations_hrs: dict[str, float],
    mold_pm_windows: Optional[list[ScheduledMoldPm]] = None,
) -> SchedulePlan:
    """Evaluate a deterministic list of scheduled (and unscheduled) job placements into a full
    `SchedulePlan` with exact costs in `config.currency`, Gantt blocks, resin balance, press OEE, and KPIs.

    Each item in `raw_assignments` has:
      - `order_id`: str
      - `scheduled`: bool
      - `unscheduled_reason`: Optional[str]
      - `machine_id`: Optional[str]
      - `start_min`: int
      - `end_min`: int
      - `virgin_kg`: float
      - `regrind_kg`: float
    """
    presses_by_id = {p.machine_id: p for p in dataset.presses}
    molds_by_id = {m.mold_id: m for m in dataset.molds}
    resins_by_code = {r.resin_code: r for r in dataset.resins}
    orders_by_id = {o.order_id: o for o in dataset.orders}

    cur = config.currency
    fx = config.fx_egp_per_sar
    to_cur = lambda sar: convert_sar_to_currency(sar, cur, fx)
    ph = config.physics
    labor_mult = ramadan_labor_multiplier(ph) if config.ramadan_shift_mode else 1.0

    # Group scheduled jobs by press ordered chronologically so transitions are computed identically everywhere
    by_press: dict[str, list[dict]] = defaultdict(list)
    unscheduled_items: list[dict] = []
    for item in raw_assignments:
        if item.get("scheduled") and item.get("machine_id"):
            by_press[item["machine_id"]].append(item)
        else:
            unscheduled_items.append(item)

    for mid in by_press:
        by_press[mid].sort(key=lambda x: (x["start_min"], x["order_id"]))

    scheduled_jobs: list[ScheduledJob] = []
    gantt_blocks: list[GanttBlock] = []

    # Track per-resin and per-press accumulators
    resin_virgin_used: dict[str, float] = defaultdict(float)
    resin_regrind_used: dict[str, float] = defaultdict(float)
    resin_purge_scrap: dict[str, float] = defaultdict(float)

    press_jobs_cnt: dict[str, int] = defaultdict(int)
    press_run_mins: dict[str, int] = defaultdict(int)
    press_setup_mins: dict[str, int] = defaultdict(int)
    press_purge_kg: dict[str, float] = defaultdict(float)
    press_kwh: dict[str, float] = defaultdict(float)
    press_energy_sar: dict[str, float] = defaultdict(float)

    # Totals in SAR (converted at boundary)
    tot_resin_sar = 0.0
    tot_purge_sar = 0.0
    tot_energy_sar = 0.0
    tot_oper_sar = 0.0
    tot_late_sar = 0.0
    tot_wip_sar = 0.0
    tot_setup_mins = 0
    tot_purge_kg = 0.0
    tot_energy_kwh = 0.0
    tot_peak_mins = 0
    tot_run_mins = 0
    tot_tardiness_hrs = 0.0
    on_time_cnt = 0
    late_cnt = 0

    for mid, items in by_press.items():
        press = presses_by_id[mid]
        prev_order = None
        prev_mold = None

        for seq_idx, item in enumerate(items, start=1):
            order = orders_by_id[item["order_id"]]
            mold = molds_by_id[order.mold_id]
            resin = resins_by_code[order.resin_code]
            start_min = int(item["start_min"])
            dur_mins = order_duration_mins(order, mold)
            end_min = start_min + dur_mins

            if prev_order is None or prev_mold is None:
                setup_m, purge_kg, ttype = 0, 0.0, "initial_setup"
            else:
                setup_m, purge_kg, ttype = transition_penalty(prev_order, order, prev_mold, mold, physics=ph)

            setup_start_min = max(0, start_min - setup_m)

            # Virgin/regrind split
            gross_kg = order_gross_weight_kg(order, mold)
            v_kg = round(float(item.get("virgin_kg", gross_kg)), 2)
            rg_kg = round(float(item.get("regrind_kg", 0.0)), 2)

            resin_virgin_used[order.resin_code] += v_kg
            resin_regrind_used[order.resin_code] += rg_kg
            resin_purge_scrap[order.resin_code] += purge_kg

            # Costs in SAR
            resin_sar = v_kg * resin.virgin_cost_per_kg + rg_kg * resin.regrind_cost_per_kg
            purge_sar = purge_kg * resin.virgin_cost_per_kg

            run_hrs = dur_mins / 60.0
            setup_hrs = setup_m / 60.0
            # Barrel heaters stay on during changeover/purge at ~55% of full molding kWh
            kwh_run = run_hrs * press.hourly_energy_kwh
            kwh_setup = setup_hrs * press.hourly_energy_kwh * 0.55
            job_kwh = kwh_run + kwh_setup

            pk_mins = peak_overlap_mins(start_min, end_min, ph.peak_start_hr, ph.peak_end_hr)
            peak_surcharge = max(0.0, ph.peak_tariff_multiplier - 1.0)
            pk_surcharge_kwh = (pk_mins / 60.0) * press.hourly_energy_kwh * (
                peak_surcharge if config.avoid_peak_tariff_hrs else 0.0
            )
            energy_sar = (job_kwh + pk_surcharge_kwh) * ph.energy_tariff_per_kwh
            oper_sar = (run_hrs + setup_hrs) * press.hourly_operating_cost * labor_mult

            due_min = int(round(order.due_hr * 60))
            tard_hrs = max(0.0, (end_min - due_min) / 60.0)
            early_hrs = max(0.0, (due_min - end_min) / 60.0)
            export_mult = 1.5 if order.is_export else 1.0
            late_sar = tard_hrs * order.late_penalty_per_hr * export_mult
            wip_sar = early_hrs * gross_kg * (ph.holding_cost_per_kg_per_day / 24.0)

            tot_resin_sar += resin_sar
            tot_purge_sar += purge_sar
            tot_energy_sar += energy_sar
            tot_oper_sar += oper_sar
            tot_late_sar += late_sar
            tot_wip_sar += wip_sar
            tot_setup_mins += setup_m
            tot_purge_kg += purge_kg
            tot_energy_kwh += job_kwh
            tot_peak_mins += pk_mins
            tot_run_mins += dur_mins
            tot_tardiness_hrs += tard_hrs

            if tard_hrs <= 1e-6:
                on_time_cnt += 1
            else:
                late_cnt += 1

            press_jobs_cnt[mid] += 1
            press_run_mins[mid] += dur_mins
            press_setup_mins[mid] += setup_m
            press_purge_kg[mid] += purge_kg
            press_kwh[mid] += job_kwh
            press_energy_sar[mid] += energy_sar

            scheduled_jobs.append(
                ScheduledJob(
                    order_id=order.order_id,
                    customer=order.customer,
                    sku_name=order.sku_name,
                    machine_id=press.machine_id,
                    machine_name=press.name,
                    mold_id=mold.mold_id,
                    mold_name=mold.name,
                    resin_code=order.resin_code,
                    color=order.color,
                    color_rank=order.color_rank,
                    quantity_pcs=order.quantity_pcs,
                    is_export=order.is_export,
                    scheduled=True,
                    sequence_index=seq_idx,
                    setup_start_min=setup_start_min,
                    start_min=start_min,
                    end_min=end_min,
                    duration_mins=dur_mins,
                    setup_mins=setup_m,
                    purge_scrap_kg=round(purge_kg, 1),
                    transition_type=ttype,
                    due_hr=order.due_hr,
                    tardiness_hrs=round(tard_hrs, 2),
                    earliness_hrs=round(early_hrs, 2),
                    late_penalty_cost=to_cur(late_sar),
                    virgin_kg=round(v_kg, 1),
                    regrind_kg=round(rg_kg, 1),
                    resin_cost=to_cur(resin_sar),
                    purge_cost=to_cur(purge_sar),
                    energy_kwh=round(job_kwh, 1),
                    energy_cost=to_cur(energy_sar),
                    operating_cost=to_cur(oper_sar),
                    peak_overlap_mins=pk_mins,
                )
            )

            # Emit changeover/purge Gantt block if > 0
            if setup_m > 0:
                gantt_blocks.append(
                    GanttBlock(
                        block_id=f"chg-{order.order_id}",
                        machine_id=press.machine_id,
                        block_type="changeover",
                        label=f"{ttype.replace('_', ' ').title()} ({setup_m}m / {purge_kg:.0f}kg)",
                        start_min=setup_start_min,
                        end_min=start_min,
                        order_id=order.order_id,
                        mold_id=mold.mold_id,
                        resin_code=order.resin_code,
                        color=order.color,
                        purge_scrap_kg=round(purge_kg, 1),
                        transition_type=ttype,
                    )
                )

            # Emit color-coded production Gantt block
            gantt_blocks.append(
                GanttBlock(
                    block_id=f"prod-{order.order_id}",
                    machine_id=press.machine_id,
                    block_type="production",
                    label=f"{order.order_id} • {order.sku_name}",
                    start_min=start_min,
                    end_min=end_min,
                    order_id=order.order_id,
                    mold_id=mold.mold_id,
                    resin_code=order.resin_code,
                    color=order.color,
                    purge_scrap_kg=0.0,
                    is_export=order.is_export,
                    tardiness_hrs=round(tard_hrs, 2),
                )
            )

            prev_order = order
            prev_mold = mold

    # Add unscheduled orders (e.g., severe virgin resin shortage)
    unscheduled_ids: list[str] = []
    for item in unscheduled_items:
        order = orders_by_id[item["order_id"]]
        mold = molds_by_id[order.mold_id]
        unscheduled_ids.append(order.order_id)
        # Unscheduled orders incur a flat 48h equivalent late penalty for fair financial comparison
        export_mult = 1.5 if order.is_export else 1.0
        unsched_pen_sar = 48.0 * order.late_penalty_per_hr * export_mult
        tot_late_sar += unsched_pen_sar
        scheduled_jobs.append(
            ScheduledJob(
                order_id=order.order_id,
                customer=order.customer,
                sku_name=order.sku_name,
                machine_id="UNSCHEDULED",
                machine_name="Unscheduled (Resin Cap)",
                mold_id=mold.mold_id,
                mold_name=mold.name,
                resin_code=order.resin_code,
                color=order.color,
                color_rank=order.color_rank,
                quantity_pcs=order.quantity_pcs,
                is_export=order.is_export,
                scheduled=False,
                unscheduled_reason=item.get("unscheduled_reason") or f"Insufficient {order.resin_code} virgin resin inventory",
                due_hr=order.due_hr,
                late_penalty_cost=to_cur(unsched_pen_sar),
            )
        )

    # Add press downtime & breakdown Gantt blocks
    press_down_mins: dict[str, int] = defaultdict(int)
    for p in dataset.presses:
        for idx, dw in enumerate(p.downtime_windows):
            s_m = int(round(dw.start_hr * 60))
            e_m = int(round(dw.end_hr * 60))
            press_down_mins[p.machine_id] += max(0, e_m - s_m)
            is_bd = "breakdown" in dw.reason.lower()
            gantt_blocks.append(
                GanttBlock(
                    block_id=f"dw-{p.machine_id}-{idx}",
                    machine_id=p.machine_id,
                    block_type="breakdown" if is_bd else "maintenance",
                    label=dw.reason,
                    start_min=s_m,
                    end_min=e_m,
                )
            )

    # Add Mold PM Gantt blocks onto the primary press used by that mold (or first compatible press)
    pm_win_by_mold = {pm.mold_id: pm for pm in (mold_pm_windows or [])}
    resolved_pm_windows: list[ScheduledMoldPm] = []
    for mid_mold, pm_hrs in mold_pm_durations_hrs.items():
        if pm_hrs <= 0:
            continue
        mold = molds_by_id.get(mid_mold)
        if mold is None:
            continue
        target_press = next(
            (j.machine_id for j in scheduled_jobs if j.scheduled and j.mold_id == mid_mold),
            mold.compatible_machines[0] if mold.compatible_machines else dataset.presses[0].machine_id,
        )
        pm_win = pm_win_by_mold.get(mid_mold)
        if pm_win is not None:
            start_m, end_m = pm_win.start_min, pm_win.end_min
            pm_mode = pm_win.mode
            resolved = pm_win.model_copy(update={"machine_id": target_press})
        else:
            start_m, end_m = 0, int(round(pm_hrs * 60))
            pm_mode = "static_t0"
            resolved = ScheduledMoldPm(
                mold_id=mid_mold,
                mold_name=mold.name,
                machine_id=target_press,
                start_min=start_m,
                end_min=end_m,
                duration_hrs=pm_hrs,
                mode="static_t0",
                trigger_reason="shot_threshold_95pct" if mold.shot_utilization_pct >= 95.0 else "manual_lock",
            )
        resolved_pm_windows.append(resolved)
        tag = "Auto PM" if pm_mode == "autonomous" else "Mold PM"
        gantt_blocks.append(
            GanttBlock(
                block_id=f"pm-{mid_mold}",
                machine_id=target_press,
                block_type="mold_pm",
                label=f"{tag}: {mid_mold} ({pm_hrs:.0f}h)",
                start_min=start_m,
                end_min=end_m,
                mold_id=mid_mold,
            )
        )

    gantt_blocks.sort(key=lambda b: (b.machine_id, b.start_min, b.block_type))
    scheduled_jobs.sort(key=lambda j: (0 if j.scheduled else 1, j.machine_id, j.start_min, j.order_id))

    # Build ResinUsageSummary list
    resin_usage: list[ResinUsageSummary] = []
    for r in dataset.resins:
        v_used = round(resin_virgin_used[r.resin_code], 1)
        rg_used = round(resin_regrind_used[r.resin_code], 1)
        p_scrap = round(resin_purge_scrap[r.resin_code], 1)
        total_v_out = round(v_used + p_scrap, 1)
        rem_v = round(max(0.0, r.virgin_available_kg - total_v_out), 1)
        total_avail = r.virgin_available_kg + r.regrind_available_kg
        util = round(((v_used + rg_used + p_scrap) / max(total_avail, 1.0)) * 100.0, 1)
        resin_usage.append(
            ResinUsageSummary(
                resin_code=r.resin_code,
                virgin_available_kg=round(r.virgin_available_kg, 1),
                regrind_available_kg=round(r.regrind_available_kg, 1),
                virgin_used_kg=v_used,
                regrind_used_kg=rg_used,
                purge_scrap_kg=p_scrap,
                total_consumed_kg=round(v_used + rg_used + p_scrap, 1),
                remaining_virgin_kg=rem_v,
                utilization_pct=util,
                virgin_cost_per_kg=to_cur(r.virgin_cost_per_kg),
            )
        )

    # Build PressSummary list & Plant OEE
    press_summaries: list[PressSummary] = []
    oee_num = 0.0
    oee_den = 0.0
    for p in dataset.presses:
        r_hrs = round(press_run_mins[p.machine_id] / 60.0, 2)
        c_hrs = round(press_setup_mins[p.machine_id] / 60.0, 2)
        d_hrs = round(press_down_mins[p.machine_id] / 60.0, 2)
        busy = r_hrs + c_hrs + d_hrs
        # OEE Availability × Quality proxy: productive run time / (run + changeover + downtime)
        p_oee = round((r_hrs / busy) * 100.0, 1) if busy > 0 else 0.0
        if p.status == "active" and busy > 0:
            oee_num += r_hrs
            oee_den += busy
        press_summaries.append(
            PressSummary(
                machine_id=p.machine_id,
                name=p.name,
                process_type=p.process_type,
                tonnage=p.tonnage,
                status=p.status,
                jobs_count=press_jobs_cnt[p.machine_id],
                run_hrs=r_hrs,
                changeover_hrs=c_hrs,
                downtime_hrs=d_hrs,
                oee_pct=p_oee,
                purge_scrap_kg=round(press_purge_kg[p.machine_id], 1),
                energy_kwh=round(press_kwh[p.machine_id], 1),
                energy_cost=to_cur(press_energy_sar[p.machine_id]),
            )
        )

    total_orders = len(dataset.orders)
    otif_pct = round((on_time_cnt / max(total_orders, 1)) * 100.0, 1)
    plant_oee_pct = round((oee_num / max(oee_den, 1e-6)) * 100.0, 1) if oee_den > 0 else 0.0

    # Total Controllable Factory Cost = Resin Material + Purge Scrap + Energy + Press Operating + Late Penalties + WIP
    total_cost_sar = tot_resin_sar + tot_purge_sar + tot_energy_sar + tot_oper_sar + tot_late_sar + tot_wip_sar

    kpis = KpiBlock(
        total_cost=to_cur(total_cost_sar),
        resin_material_cost=to_cur(tot_resin_sar),
        purge_scrap_cost=to_cur(tot_purge_sar),
        energy_cost=to_cur(tot_energy_sar),
        operating_cost=to_cur(tot_oper_sar),
        late_penalty_cost=to_cur(tot_late_sar),
        wip_holding_cost=to_cur(tot_wip_sar),
        changeover_hours=round(tot_setup_mins / 60.0, 2),
        purge_scrap_kg=round(tot_purge_kg, 1),
        total_energy_kwh=round(tot_energy_kwh, 1),
        peak_energy_hrs=round(tot_peak_mins / 60.0, 2),
        total_run_hours=round(tot_run_mins / 60.0, 2),
        oee_pct=plant_oee_pct,
        otif_pct=otif_pct,
        on_time_orders=on_time_cnt,
        late_orders=late_cnt,
        unscheduled_orders=len(unscheduled_ids),
        total_orders=total_orders,
        total_tardiness_hrs=round(tot_tardiness_hrs, 2),
        virgin_resin_used_kg=round(sum(resin_virgin_used.values()), 1),
        regrind_resin_used_kg=round(sum(resin_regrind_used.values()), 1),
        weighted_objective=0.0,
    )

    return SchedulePlan(
        jobs=scheduled_jobs,
        gantt_blocks=gantt_blocks,
        resin_usage=resin_usage,
        press_summaries=press_summaries,
        unscheduled_order_ids=unscheduled_ids,
        mold_pm_windows=resolved_pm_windows,
        kpis=kpis,
    )


def _cmp(base: float, opt: float) -> MetricCompare:
    delta = round(opt - base, 2)
    pct = round(((opt - base) / base) * 100.0, 1) if abs(base) > 1e-6 else 0.0
    return MetricCompare(baseline=round(base, 2), optimized=round(opt, 2), delta=delta, delta_pct=pct)


def build_scorecard(
    baseline: SchedulePlan, optimized: SchedulePlan, config: SolverConfig
) -> Scorecard:
    """Compute exact side-by-side ROI Scorecard comparing Naive FIFO Baseline vs. CP-SAT Optimized."""
    bk = baseline.kpis
    ok = optimized.kpis

    # Compute comparable normalized composite weighted objective (baseline = 100.0 reference)
    w_sum = max(1, config.w_changeover_scrap + config.w_otif + config.w_energy_cost + config.w_working_capital)

    def _norm(val: float, ref: float) -> float:
        return (val / ref) * 100.0 if ref > 1e-6 else (0.0 if val <= 1e-6 else 100.0)

    b_chg_term = bk.purge_scrap_cost + bk.changeover_hours * 250.0
    o_chg_term = ok.purge_scrap_cost + ok.changeover_hours * 250.0
    b_en_term = bk.energy_cost + bk.operating_cost
    o_en_term = ok.energy_cost + ok.operating_cost
    b_wc_term = bk.resin_material_cost + bk.wip_holding_cost
    o_wc_term = ok.resin_material_cost + ok.wip_holding_cost

    base_obj = round(
        (
            config.w_changeover_scrap * _norm(b_chg_term, max(b_chg_term, 1.0))
            + config.w_otif * _norm(bk.late_penalty_cost + 1.0, max(bk.late_penalty_cost + 1.0, 1.0))
            + config.w_energy_cost * _norm(b_en_term, max(b_en_term, 1.0))
            + config.w_working_capital * _norm(b_wc_term, max(b_wc_term, 1.0))
        )
        / w_sum,
        2,
    )
    opt_obj = round(
        (
            config.w_changeover_scrap * _norm(o_chg_term, max(b_chg_term, 1.0))
            + config.w_otif * _norm(ok.late_penalty_cost + 1.0, max(bk.late_penalty_cost + 1.0, 1.0))
            + config.w_energy_cost * _norm(o_en_term, max(b_en_term, 1.0))
            + config.w_working_capital * _norm(o_wc_term, max(b_wc_term, 1.0))
        )
        / w_sum,
        2,
    )
    bk.weighted_objective = base_obj
    ok.weighted_objective = opt_obj

    cash_savings = round(bk.total_cost - ok.total_cost, 2)
    cash_savings_pct = round((cash_savings / bk.total_cost) * 100.0, 1) if bk.total_cost > 1e-6 else 0.0
    purge_kg_saved = round(bk.purge_scrap_kg - ok.purge_scrap_kg, 1)
    purge_cost_saved = round(bk.purge_scrap_cost - ok.purge_scrap_cost, 2)
    chg_hrs_saved = round(bk.changeover_hours - ok.changeover_hours, 2)
    energy_and_late_saved = round(
        (bk.energy_cost + bk.late_penalty_cost) - (ok.energy_cost + ok.late_penalty_cost), 2
    )

    return Scorecard(
        total_cost=_cmp(bk.total_cost, ok.total_cost),
        cash_savings=cash_savings,
        cash_savings_pct=cash_savings_pct,
        purge_scrap_kg=_cmp(bk.purge_scrap_kg, ok.purge_scrap_kg),
        purge_scrap_kg_saved=purge_kg_saved,
        purge_scrap_cost_saved=purge_cost_saved,
        changeover_hours=_cmp(bk.changeover_hours, ok.changeover_hours),
        changeover_hours_saved=chg_hrs_saved,
        energy_and_late_savings=energy_and_late_saved,
        energy_cost=_cmp(bk.energy_cost, ok.energy_cost),
        late_penalty_cost=_cmp(bk.late_penalty_cost, ok.late_penalty_cost),
        oee_pct=_cmp(bk.oee_pct, ok.oee_pct),
        otif_pct=_cmp(bk.otif_pct, ok.otif_pct),
        weighted_objective=_cmp(base_obj, opt_obj),
    )
