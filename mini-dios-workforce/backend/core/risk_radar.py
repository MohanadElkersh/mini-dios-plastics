"""Proactive Delay & Bottleneck Risk Radar for Mini-DIOS Plastics.

100% deterministic Python analytics (zero LLM arithmetic). Computes:
1. Late-export & tight-slack order risks with exact SAR/EGP exposure.
2. Minute-by-minute resin depletion clock & projected stockout hour.
3. High-utilization press choke points.
4. Post-week mold shot-limit trajectory alerts.
5. Workforce understaffed & zero-buffer (single-point-of-failure) shift alerts.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Optional

from .ontology import (
    DAY_NAMES,
    PlantDataset,
    ResinDepletionClock,
    RiskAlert,
    RiskRadarReport,
    RiskSeverity,
    SchedulePlan,
    SolverConfig,
    WorkforceResult,
    convert_sar_to_currency,
    order_shots,
)

DAY_NAMES_AR = ["الأحد", "الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت"]

SEVERITY_RANK = {"critical": 0, "elevated": 1, "watch": 2}


def _to_cur(sar: float, config: SolverConfig) -> float:
    return convert_sar_to_currency(sar, config.currency, config.fx_egp_per_sar)


def compute_risk_radar(
    dataset: PlantDataset,
    config: SolverConfig,
    plan: SchedulePlan,
    workforce: Optional[WorkforceResult] = None,
) -> RiskRadarReport:
    """Deterministically evaluate proactive operational risks for a solved schedule."""
    alerts: list[RiskAlert] = []
    orders_by_id = {o.order_id: o for o in dataset.orders}
    molds_by_id = {m.mold_id: m for m in dataset.molds}
    presses_by_id = {p.machine_id: p for p in dataset.presses}
    horizon_hrs = float(config.physics.horizon_hrs)
    cur = config.currency

    # ------------------------------------------------------------------
    # 1. Late-Export & Tight-Slack Order Radar
    # ------------------------------------------------------------------
    export_at_risk_count = 0
    tightest_slack_order_id: Optional[str] = None
    tightest_slack_hrs: Optional[float] = None

    for job in plan.jobs:
        order = orders_by_id.get(job.order_id)
        if not job.scheduled:
            if job.is_export:
                export_at_risk_count += 1
            alerts.append(
                RiskAlert(
                    alert_id=f"risk-unsched-{job.order_id}",
                    category="late_export",
                    severity="critical",
                    entity_type="order",
                    entity_id=job.order_id,
                    title_en=f"Unscheduled {'Export ' if job.is_export else ''}Order {job.order_id}",
                    title_ar=f"أمر {'تصدير ' if job.is_export else ''}غير مجدول {job.order_id}",
                    detail_en=(
                        f"{job.customer} ({job.sku_name}) could not be scheduled due to {job.resin_code} "
                        f"virgin inventory cap. Exposure: {job.late_penalty_cost:,.0f} {cur}."
                    ),
                    detail_ar=(
                        f"تعذرت جدولة {job.customer} ({job.sku_name}) بسبب سقف مخزون خام {job.resin_code}. "
                        f"التعرض المالي: {job.late_penalty_cost:,.0f} {cur}."
                    ),
                    metric_label="Penalty Exposure",
                    metric_value=f"{job.late_penalty_cost:,.0f} {cur}",
                    financial_exposure=round(job.late_penalty_cost, 2),
                    suggested_prompt_en=(
                        f"Allow 35% non-food regrind override, replenish virgin {job.resin_code} silo stock by 25%, "
                        f"and set OTIF weight to 85 to recover unscheduled order {job.order_id}"
                    ),
                    suggested_prompt_ar=(
                        f"اسمح برفع نسبة الريجريند الصناعي إلى 35% وعزّز مخزون خام {job.resin_code} البكر بنسبة 25% "
                        f"وارفع وزن التسليم في الموعد إلى 85 لجدولة الأمر {job.order_id}"
                    ),
                )
            )
            continue

        slack_hrs = round((job.due_hr * 60.0 - job.end_min) / 60.0, 2)
        if tightest_slack_hrs is None or slack_hrs < tightest_slack_hrs:
            tightest_slack_hrs = slack_hrs
            tightest_slack_order_id = job.order_id

        if job.tardiness_hrs > 0.01:
            if job.is_export:
                export_at_risk_count += 1
            sev = "critical" if (job.is_export or job.tardiness_hrs >= 4.0) else "elevated"
            alerts.append(
                RiskAlert(
                    alert_id=f"risk-late-{job.order_id}",
                    category="late_export",
                    severity=sev,
                    entity_type="order",
                    entity_id=job.order_id,
                    title_en=f"{'Export ' if job.is_export else ''}Order {job.order_id} Late by {job.tardiness_hrs:.1f}h",
                    title_ar=f"تأخر أمر {'تصدير ' if job.is_export else ''}{job.order_id} بمقدار {job.tardiness_hrs:.1f} ساعة",
                    detail_en=(
                        f"{job.customer} on {job.machine_id} finishes at H{job.end_min/60:.1f} vs due H{job.due_hr:.0f}. "
                        f"Late penalty: {job.late_penalty_cost:,.0f} {cur}."
                    ),
                    detail_ar=(
                        f"طلب {job.customer} على المكبس {job.machine_id} ينتهي عند س{job.end_min/60:.1f} مقابل موعد س{job.due_hr:.0f}. "
                        f"غرامة التأخير: {job.late_penalty_cost:,.0f} {cur}."
                    ),
                    metric_label="Tardiness",
                    metric_value=f"+{job.tardiness_hrs:.1f}h",
                    financial_exposure=round(job.late_penalty_cost, 2),
                    suggested_prompt_en=(
                        f"Prioritize zero late exports (set OTIF weight to 85 and working capital weight to 5) "
                        f"and enable autonomous PM co-optimization to recover late order {job.order_id} on {job.machine_id}"
                    ),
                    suggested_prompt_ar=(
                        f"أعطِ أولوية قصوى لصفر تأخير في التصدير (ارفع وزن OTIF إلى 85 وخفض رأس المال العامل إلى 5) "
                        f"وفعّل جدولة الصيانة الذاتية لإنقاذ الأمر المتأخر {job.order_id} على {job.machine_id}"
                    ),
                )
            )
        elif job.is_export and slack_hrs < 6.0:
            export_at_risk_count += 1
            pen_hr_sar = order.late_penalty_per_hr if order else 400.0
            # Potential 4h delay exposure if an unscheduled hiccup hits this press
            pot_exposure = _to_cur(4.0 * pen_hr_sar * 1.5, config)
            alerts.append(
                RiskAlert(
                    alert_id=f"risk-slack-{job.order_id}",
                    category="late_export",
                    severity="elevated",
                    entity_type="order",
                    entity_id=job.order_id,
                    title_en=f"Tight Export Cut-Off Buffer: {job.order_id} ({slack_hrs:.1f}h slack)",
                    title_ar=f"هامش أمان ضيق لأمر تصدير: {job.order_id} ({slack_hrs:.1f} ساعة)",
                    detail_en=(
                        f"{job.customer} on {job.machine_id} has only {slack_hrs:.1f}h before port cut-off H{job.due_hr:.0f}. "
                        f"A 4h press hiccup exposes {pot_exposure:,.0f} {cur}."
                    ),
                    detail_ar=(
                        f"طلب {job.customer} على {job.machine_id} لديه {slack_hrs:.1f} ساعة فقط قبل موعد التصدير س{job.due_hr:.0f}. "
                        f"أي توقف 4 ساعات يعرّض {pot_exposure:,.0f} {cur}."
                    ),
                    metric_label="Slack Buffer",
                    metric_value=f"{slack_hrs:.1f}h",
                    financial_exposure=round(pot_exposure, 2),
                    suggested_prompt_en=(
                        f"Prioritize export cut-off buffers (set OTIF weight to 80 and working capital weight to 5) "
                        f"and re-sequence {job.machine_id} to expand safety slack for export {job.order_id}"
                    ),
                    suggested_prompt_ar=(
                        f"عظّم هامش أمان التصدير (ارفع وزن OTIF إلى 80 وخفض رأس المال العامل إلى 5) "
                        f"وأعد ترتيب المكبس {job.machine_id} لزيادة هامش الأمان لطلب التصدير {job.order_id}"
                    ),
                )
            )
        elif not job.is_export and slack_hrs < 4.0:
            alerts.append(
                RiskAlert(
                    alert_id=f"risk-slack-dom-{job.order_id}",
                    category="late_export",
                    severity="watch",
                    entity_type="order",
                    entity_id=job.order_id,
                    title_en=f"Low Delivery Buffer: {job.order_id} ({slack_hrs:.1f}h slack)",
                    title_ar=f"هامش تسليم منخفض: {job.order_id} ({slack_hrs:.1f} ساعة)",
                    detail_en=f"{job.customer} on {job.machine_id} finishes {slack_hrs:.1f}h before due H{job.due_hr:.0f}.",
                    detail_ar=f"طلب {job.customer} على {job.machine_id} ينتهي قبل الموعد س{job.due_hr:.0f} بـ {slack_hrs:.1f} ساعة.",
                    metric_label="Slack Buffer",
                    metric_value=f"{slack_hrs:.1f}h",
                    financial_exposure=0.0,
                    suggested_prompt_en=(
                        f"Increase OTIF delivery weight to 75 and reduce working capital weight to 5 "
                        f"to expand delivery buffer for order {job.order_id} on {job.machine_id}"
                    ),
                    suggested_prompt_ar=(
                        f"ارفع وزن الالتزام بمواعيد التسليم OTIF إلى 75 وخفض وزن رأس المال العامل إلى 5 "
                        f"لتوسيع هامش التسليم للأمر {job.order_id} على {job.machine_id}"
                    ),
                )
            )

    # ------------------------------------------------------------------
    # 2. Minute-by-Minute Resin Depletion Clock
    # ------------------------------------------------------------------
    jobs_by_resin: dict[str, list] = defaultdict(list)
    unsched_resins: set[str] = set()
    for job in plan.jobs:
        if job.scheduled:
            jobs_by_resin[job.resin_code].append(job)
        else:
            unsched_resins.add(job.resin_code)

    resin_clocks: list[ResinDepletionClock] = []
    usage_by_code = {u.resin_code: u for u in plan.resin_usage}

    for r in dataset.resins:
        u = usage_by_code.get(r.resin_code)
        consumed_v = round((u.virgin_used_kg + u.purge_scrap_kg) if u else 0.0, 1)
        start_v = round(r.virgin_available_kg, 1)
        rem_v = round(max(0.0, start_v - consumed_v), 1)
        util_pct = round((consumed_v / max(start_v, 1.0)) * 100.0, 1)

        # Build chronological burn events to find exact hour when cumulative draw hits >=98% of stock
        events: list[tuple[int, float]] = []
        for j in jobs_by_resin.get(r.resin_code, []):
            if j.purge_scrap_kg > 0:
                events.append((j.setup_start_min, j.purge_scrap_kg))
            if j.virgin_kg > 0:
                # Approximate continuous draw by midpoint/end checkpoints (4 quarter slices)
                dur = max(1, j.end_min - j.start_min)
                chunk = j.virgin_kg / 4.0
                for q in range(1, 5):
                    events.append((j.start_min + int(round(dur * q / 4.0)), chunk))
        events.sort(key=lambda x: x[0])

        stockout_hr: Optional[float] = None
        cum_kg = 0.0
        threshold_kg = start_v * 0.98
        for ev_min, kg in events:
            cum_kg += kg
            if cum_kg >= threshold_kg and stockout_hr is None:
                stockout_hr = round(ev_min / 60.0, 1)
                break

        burn_per_hr = consumed_v / max(horizon_hrs, 1.0)
        cov_hrs = round(rem_v / burn_per_hr, 1) if burn_per_hr > 0.01 else 999.0

        has_unsched = r.resin_code in unsched_resins
        if has_unsched or util_pct >= 95.0 or (stockout_hr is not None and stockout_hr <= horizon_hrs):
            r_status: RiskSeverity = "critical"
        elif util_pct >= 85.0 or cov_hrs < 24.0:
            r_status = "elevated"
        elif util_pct >= 75.0 or cov_hrs < 48.0:
            r_status = "watch"
        else:
            r_status = "healthy"

        resin_clocks.append(
            ResinDepletionClock(
                resin_code=r.resin_code,
                starting_virgin_kg=start_v,
                consumed_virgin_plus_purge_kg=consumed_v,
                remaining_virgin_kg=rem_v,
                utilization_pct=util_pct,
                projected_stockout_hr=stockout_hr,
                coverage_hrs_remaining=cov_hrs,
                status=r_status,
            )
        )

        if r_status in ("critical", "elevated"):
            # Exposure = cost to emergency-replenish 24h buffer at spot +15%
            replenish_kg = max(0.0, burn_per_hr * 24.0 - rem_v)
            exp_val = _to_cur(replenish_kg * r.virgin_cost_per_kg * 1.15, config)
            so_text_en = f"Depletion near H{stockout_hr:.0f}" if stockout_hr is not None else f"{cov_hrs:.0f}h buffer left"
            so_text_ar = f"النفاد قرب س{stockout_hr:.0f}" if stockout_hr is not None else f"متبقي {cov_hrs:.0f} ساعة تغطية"
            alerts.append(
                RiskAlert(
                    alert_id=f"risk-resin-{r.resin_code}",
                    category="resin_stockout",
                    severity=r_status,
                    entity_type="resin",
                    entity_id=r.resin_code,
                    title_en=f"{r.resin_code} Virgin Silo at {util_pct:.0f}% ({so_text_en})",
                    title_ar=f"صومعة خام {r.resin_code} عند {util_pct:.0f}% ({so_text_ar})",
                    detail_en=(
                        f"Virgin + purge draw is {consumed_v:,.0f} kg of {start_v:,.0f} kg ({rem_v:,.0f} kg remaining). "
                        f"Emergency 24h replenishment buffer: {exp_val:,.0f} {cur}."
                    ),
                    detail_ar=(
                        f"استهلاك الخام والهدر {consumed_v:,.0f} كجم من أصل {start_v:,.0f} كجم (المتبقي {rem_v:,.0f} كجم). "
                        f"تكلفة التعزيز الطارئ لـ 24 ساعة: {exp_val:,.0f} {cur}."
                    ),
                    metric_label="Silo Draw",
                    metric_value=f"{util_pct:.0f}%",
                    financial_exposure=round(exp_val, 2),
                    suggested_prompt_en=(
                        f"Allow 35% non-food regrind override, replenish virgin {r.resin_code} silo stock by 25%, "
                        f"and maximize purge scrap reduction to relieve {r.resin_code} depletion"
                    ),
                    suggested_prompt_ar=(
                        f"فعّل رفع الريجريند الصناعي إلى 35% وعزّز صومعة خام {r.resin_code} البكر بنسبة 25% "
                        f"وعظّم خفض هالك التنظيف لتخفيف استنزاف {r.resin_code}"
                    ),
                )
            )

    # ------------------------------------------------------------------
    # 3. High-Utilization Press Choke Points
    # ------------------------------------------------------------------
    for ps in plan.press_summaries:
        press = presses_by_id.get(ps.machine_id)
        if press is None or press.status != "active":
            continue
        avail_hrs = max(1.0, horizon_hrs - ps.downtime_hrs)
        busy_pct = round(((ps.run_hrs + ps.changeover_hrs) / avail_hrs) * 100.0, 1)
        if busy_pct >= 82.0:
            sev = "critical" if busy_pct >= 92.0 else "elevated"
            alerts.append(
                RiskAlert(
                    alert_id=f"risk-press-{ps.machine_id}",
                    category="press_bottleneck",
                    severity=sev,
                    entity_type="press",
                    entity_id=ps.machine_id,
                    title_en=f"Press Choke Point: {ps.machine_id} at {busy_pct:.0f}% Capacity",
                    title_ar=f"نقطة اختناق: المكبس {ps.machine_id} عند {busy_pct:.0f}% إشغال",
                    detail_en=(
                        f"{ps.name} runs {ps.run_hrs:.1f}h + {ps.changeover_hrs:.1f}h setups "
                        f"across {ps.jobs_count} jobs ({ps.purge_scrap_kg:.0f} kg purge). Zero cushion for unplanned downtime."
                    ),
                    detail_ar=(
                        f"{ps.name} يعمل {ps.run_hrs:.1f} ساعة إنتاج + {ps.changeover_hrs:.1f} ساعة تبديل "
                        f"لـ {ps.jobs_count} أوامر ({ps.purge_scrap_kg:.0f} كجم هدر). لا يوجد هامش لأي عطل مفاجئ."
                    ),
                    metric_label="Capacity Load",
                    metric_value=f"{busy_pct:.0f}%",
                    financial_exposure=0.0,
                    suggested_prompt_en=(
                        f"Rebalance load off choke press {ps.machine_id} by setting changeover scrap weight to 70, "
                        f"enabling autonomous PM co-optimization, and clearing unplanned downtime"
                    ),
                    suggested_prompt_ar=(
                        f"أعد موازنة الحمل عن المكبس المختنق {ps.machine_id} برفع وزن خفض الهالك والتبديل إلى 70 "
                        f"وتفعيل الصيانة الذاتية وإزالة التوقفات الطارئة"
                    ),
                )
            )

    # ------------------------------------------------------------------
    # 4. Post-Week Mold Shot-Limit Trajectory
    # ------------------------------------------------------------------
    pm_done_molds = (
        {pm.mold_id for pm in (plan.mold_pm_windows or [])}
        | {lk.mold_id for lk in config.scenarios.mold_pm_locks}
        | {b.mold_id for b in plan.gantt_blocks if b.block_type == "mold_pm" and b.mold_id}
    )
    weekly_shots_by_mold: dict[str, int] = defaultdict(int)
    for job in plan.jobs:
        if not job.scheduled:
            continue
        order = orders_by_id.get(job.order_id)
        mold = molds_by_id.get(job.mold_id)
        if order and mold:
            weekly_shots_by_mold[mold.mold_id] += order_shots(order, mold)

    for mold in dataset.molds:
        if mold.mold_id in pm_done_molds:
            continue  # PM already scheduled this week
        added = weekly_shots_by_mold.get(mold.mold_id, 0)
        if added <= 0:
            continue
        post_shots = mold.current_shots + added
        post_pct = round((post_shots / max(mold.maintenance_interval_shots, 1)) * 100.0, 1)
        if post_pct >= 90.0:
            sev = "critical" if post_pct >= 100.0 else ("elevated" if post_pct >= 95.0 else "watch")
            alerts.append(
                RiskAlert(
                    alert_id=f"risk-mold-{mold.mold_id}",
                    category="mold_shot_limit",
                    severity=sev,
                    entity_type="mold",
                    entity_id=mold.mold_id,
                    title_en=f"Mold {mold.mold_id} Reaches {post_pct:.1f}% Shot Life Post-Week",
                    title_ar=f"القالب {mold.mold_id} يصل إلى {post_pct:.1f}% من عمر الضربات بعد الأسبوع",
                    detail_en=(
                        f"{mold.name} adds {added:,} shots ({mold.current_shots:,} → {post_shots:,} / "
                        f"{mold.maintenance_interval_shots:,}). Plan {mold.pm_duration_hrs:.0f}h PM proactively."
                    ),
                    detail_ar=(
                        f"{mold.name} يضيف {added:,} ضربة ({mold.current_shots:,} ← {post_shots:,} / "
                        f"{mold.maintenance_interval_shots:,}). خطط لصيانة وقائية {mold.pm_duration_hrs:.0f} ساعات مبكراً."
                    ),
                    metric_label="Projected Life",
                    metric_value=f"{post_pct:.1f}%",
                    financial_exposure=0.0,
                    suggested_prompt_en=(
                        f"Complete preventive maintenance and reset shot counter on mold {mold.mold_id} "
                        f"with autonomous PM co-optimization enabled"
                    ),
                    suggested_prompt_ar=(
                        f"أكمل الصيانة الوقائية وصفّر عداد الضربات للقالب {mold.mold_id} "
                        f"مع تفعيل جدولة الصيانة الذاتية"
                    ),
                )
            )

    # ------------------------------------------------------------------
    # 5. Workforce Understaffed & Zero-Buffer Shift Fragility
    # ------------------------------------------------------------------
    if workforce is not None:
        wk = workforce.optimized.kpis
        if wk.understaffed_slots > 0:
            role_ar_map = {
                "Press_Operator": "مشغل مكبس",
                "Mold_Technician": "فني قوالب",
                "QC_Inspector": "مراقب جودة",
                "Material_Handler": "مناول مواد",
                "Shift_Supervisor": "مشرف وردية",
            }
            short_roles = [
                r for r, pct in (wk.role_coverage_pct or {}).items() if pct < 99.9
            ] or ["QC_Inspector", "Material_Handler", "Shift_Supervisor"]
            roles_en = ", ".join(r.replace("_", " ") for r in short_roles)
            roles_ar = "، ".join(role_ar_map.get(r, r) for r in short_roles)
            alerts.append(
                RiskAlert(
                    alert_id="risk-wf-understaffed",
                    category="workforce_fragility",
                    severity="critical",
                    entity_type="shift",
                    entity_id=wk.worst_slot or "SHIFTS",
                    title_en=f"{wk.understaffed_slots} Understaffed Shift Slot(s) ({wk.coverage_pct:.1f}% Coverage)",
                    title_ar=f"{wk.understaffed_slots} وردية بها عجز عمالة (تغطية {wk.coverage_pct:.1f}%)",
                    detail_en=(
                        f"Total headcount gap of {wk.headcount_gap} slot(s). Worst bottleneck: {wk.worst_slot or 'multiple shifts'}."
                    ),
                    detail_ar=(
                        f"إجمالي العجز {wk.headcount_gap} مقعد وردية. أسوأ نقطة اختناق: {wk.worst_slot or 'عدة ورديات'}."
                    ),
                    metric_label="Coverage",
                    metric_value=f"{wk.coverage_pct:.1f}%",
                    financial_exposure=0.0,
                    suggested_prompt_en=(
                        f"Maximize workforce coverage weight to 95 and add minimum required relief staff "
                        f"for bottleneck roles ({roles_en}) to eliminate understaffed shift slots"
                    ),
                    suggested_prompt_ar=(
                        f"ارفع وزن تغطية الورديات إلى 95 وأضف الحد الأدنى من العمالة الاحتياطية للأدوار المختنقة "
                        f"({roles_ar}) لإغلاق عجز الورديات بالكامل"
                    ),
                )
            )
        else:
            # Find high-intensity Mold_Technician or >=4-press Operator slots with 0 headcount buffer
            fragile_cells = [
                c
                for c in workforce.optimized.demand
                if c.required > 0
                and c.scheduled == c.required
                and (c.role == "Mold_Technician" or (c.role == "Press_Operator" and c.active_presses >= 4))
            ]
            if fragile_cells:
                top_c = fragile_cells[0]
                day_en = DAY_NAMES[top_c.day] if 0 <= top_c.day < len(DAY_NAMES) else f"D{top_c.day}"
                day_ar = DAY_NAMES_AR[top_c.day] if 0 <= top_c.day < len(DAY_NAMES_AR) else f"يوم {top_c.day}"
                alerts.append(
                    RiskAlert(
                        alert_id=f"risk-wf-zero-buf-{top_c.day}-{top_c.shift}",
                        category="workforce_fragility",
                        severity="watch",
                        entity_type="shift",
                        entity_id=f"{day_en} {top_c.shift}",
                        title_en=f"{len(fragile_cells)} Zero-Buffer High-Load Shift Slot(s)",
                        title_ar=f"{len(fragile_cells)} وردية عالية الحمل بدون احتياطي",
                        detail_en=(
                            f"E.g., {day_en} {top_c.shift} ({top_c.role.replace('_', ' ')}, {top_c.scheduled}/{top_c.required}) "
                            f"has zero callout cushion if a technician or operator calls in sick."
                        ),
                        detail_ar=(
                            f"مثلاً وردية {day_ar} ({top_c.shift}) بتغطية {top_c.scheduled}/{top_c.required} "
                            f"ليس لديها احتياطي في حال غياب طارئ."
                        ),
                        metric_label="Fragile Slots",
                        metric_value=f"{len(fragile_cells)} slots",
                        financial_exposure=0.0,
                        suggested_prompt_en=(
                            f"Add 1 relief {top_c.role.replace('_', ' ')} and set shift coverage weight to 95 "
                            f"to build a call-out safety buffer on {day_en} {top_c.shift}"
                        ),
                        suggested_prompt_ar=(
                            f"أضف 1 عامل احتياطي وعظّم وزن تغطية الورديات إلى 95 لبناء احتياطي أمان في وردية {day_ar}"
                        ),
                    )
                )

    # Sort alerts: critical -> elevated -> watch, then highest financial exposure
    alerts.sort(key=lambda a: (SEVERITY_RANK[a.severity], -a.financial_exposure, a.alert_id))

    crit_n = sum(1 for a in alerts if a.severity == "critical")
    elev_n = sum(1 for a in alerts if a.severity == "elevated")
    watch_n = sum(1 for a in alerts if a.severity == "watch")
    cat_points: dict[str, int] = {}
    for a in alerts:
        pts = 25 if a.severity == "critical" else (10 if a.severity == "elevated" else 3)
        cat_points[a.category] = min(68, cat_points.get(a.category, 0) + pts)
    score = min(100, sum(cat_points.values()))

    if crit_n > 0 or score >= 50:
        level: RiskSeverity = "critical"
    elif elev_n > 0 or score >= 20:
        level = "elevated"
    elif watch_n > 0:
        level = "watch"
    else:
        level = "healthy"

    tot_exposure = round(sum(a.financial_exposure for a in alerts), 2)

    return RiskRadarReport(
        overall_risk_score=score,
        risk_level=level,
        critical_count=crit_n,
        elevated_count=elev_n,
        watch_count=watch_n,
        total_financial_exposure=tot_exposure,
        export_at_risk_count=export_at_risk_count,
        tightest_slack_order_id=tightest_slack_order_id,
        tightest_slack_hrs=tightest_slack_hrs,
        resin_clocks=resin_clocks,
        alerts=alerts,
    )
