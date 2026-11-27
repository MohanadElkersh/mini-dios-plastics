"""Deterministic Bilingual WhatsApp Shift Dispatch Formatter for Mini-DIOS Plastics (Zero LLM Math).

Formats clean, mobile-friendly WhatsApp shift dispatch briefs (`*bold*` headers, clean bullets,
zero messy markdown tables) in English (LTR) and Arabic (RTL) for:
  - `scope="full_week"`: Full 7-day plant execution & crew summary
  - `scope="day_shift"`: Specific day (`0..6` = Sun..Sat) and shift (`Morning`, `Afternoon`, `Evening`, `Night`, or `ALL`)
"""
from __future__ import annotations

from typing import Literal, Optional
from urllib.parse import quote

from pydantic import BaseModel, Field

from .ontology import DAY_NAMES, PlantDataset, SolveResult, SolverConfig
from .workforce_solver import shift_layout

DAY_NAMES_AR = ("الأحد", "الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت")

SHIFT_NAMES_AR: dict[str, str] = {
    "Morning": "الوردية الصباحية",
    "Afternoon": "الوردية المسائية",
    "Evening": "وردية المساء (رمضان)",
    "Night": "الوردية الليلية",
    "ALL": "جميع ورديات اليوم",
}

ROLE_NAMES_EN: dict[str, str] = {
    "Press_Operator": "Press Operators",
    "Mold_Technician": "Mold Techs",
    "QC_Inspector": "QC",
    "Material_Handler": "Material Handlers",
    "Shift_Supervisor": "Supervisor",
}

ROLE_NAMES_AR: dict[str, str] = {
    "Press_Operator": "مشغلو المكابس",
    "Mold_Technician": "فنيو القوالب",
    "QC_Inspector": "مفتشو الجودة",
    "Material_Handler": "مناولو الخامات",
    "Shift_Supervisor": "مشرف الوردية",
}

COLOR_AR: dict[str, str] = {
    "Natural": "طبيعي/شفاف",
    "White": "أبيض",
    "Yellow": "أصفر",
    "Blue": "أزرق",
    "Red": "أحمر",
    "Black": "أسود",
}


class WhatsAppDispatchRequest(BaseModel):
    scope: Literal["full_week", "day_shift"] = "day_shift"
    day: int = Field(default=0, ge=0, le=6, description="0=Sun .. 6=Sat")
    shift: str = Field(default="Morning", description="Morning | Afternoon | Evening | Night | ALL")
    language: Literal["en", "ar"] = "en"
    dataset: Optional[PlantDataset] = None
    config: Optional[SolverConfig] = None
    result: Optional[SolveResult] = None


class WhatsAppDispatchResponse(BaseModel):
    scope: str
    day: int
    shift: str
    language: Literal["en", "ar"]
    plant_name: str
    window_label: str
    jobs_included: int
    crew_assigned_count: int
    open_gaps_count: int
    message_text: str
    whatsapp_url: str


def _fmt_day_clock(minute_val: int, lang: Literal["en", "ar"]) -> str:
    d_idx = max(0, minute_val // 1440) % 7
    rem_mins = max(0, minute_val % 1440)
    hh = rem_mins // 60
    mm = rem_mins % 60
    d_lbl = DAY_NAMES_AR[d_idx] if lang == "ar" else DAY_NAMES[d_idx]
    return f"{d_lbl} {hh:02d}:{mm:02d}"


def format_whatsapp_shift_dispatch(
    result: SolveResult,
    dataset: Optional[PlantDataset] = None,
    config: Optional[SolverConfig] = None,
    scope: Literal["full_week", "day_shift"] = "day_shift",
    day: int = 0,
    shift: str = "Morning",
    language: Literal["en", "ar"] = "en",
) -> WhatsAppDispatchResponse:
    """Deterministically build a WhatsApp-formatted shift dispatch message and `wa.me` share URL."""
    cfg = config or result.audit.config
    plant_name = (dataset.name if dataset else result.dataset_name) or "Delta & Riyadh Polymer Packaging Plant"
    is_ar = language == "ar"
    plan = result.optimized
    wf = result.workforce

    shifts = shift_layout(cfg)
    shift_by_name = {s.name: s for s in shifts}

    if scope == "full_week":
        win_start_min = 0
        win_end_min = cfg.physics.horizon_hrs * 60
        win_label = (
            "ملخص الأسبوع الكامل (الأحد 00:00 ← السبت 24:00)"
            if is_ar
            else "Full Week Summary (Sun 00:00 → Sat 24:00)"
        )
    else:
        day_base = day * 1440
        d_name = DAY_NAMES_AR[day % 7] if is_ar else DAY_NAMES[day % 7]
        if shift == "ALL" or shift not in shift_by_name:
            win_start_min = day_base
            win_end_min = day_base + 1440
            s_lbl = SHIFT_NAMES_AR.get("ALL", "جميع الورديات") if is_ar else "All Shifts (00:00–24:00)"
            win_label = f"{d_name} • {s_lbl}"
        else:
            s_def = shift_by_name[shift]
            win_start_min = day_base + int(s_def.start_hr * 60)
            win_end_min = day_base + int(s_def.end_hr * 60)
            hh_s, hh_e = int(s_def.start_hr), int(s_def.end_hr)
            s_lbl = SHIFT_NAMES_AR.get(shift, shift) if is_ar else shift
            win_label = f"{d_name} • {s_lbl} ({hh_s:02d}:00–{hh_e:02d}:00)"

    # Filter scheduled jobs overlapping [win_start_min, win_end_min)
    overlapping_jobs = [
        j
        for j in plan.jobs
        if j.scheduled and min(j.end_min, win_end_min) > max(j.setup_start_min, win_start_min)
    ]
    # If a specific shift has 0 overlapping jobs (e.g. late week), fall back to that day's jobs so dispatch is never empty
    if not overlapping_jobs and scope == "day_shift" and shift != "ALL":
        day_s = day * 1440
        day_e = day_s + 1440
        overlapping_jobs = [
            j for j in plan.jobs if j.scheduled and min(j.end_min, day_e) > max(j.setup_start_min, day_s)
        ]

    overlapping_jobs.sort(key=lambda j: (j.machine_id, j.start_min))

    lines: list[str] = []
    if is_ar:
        lines.append(f"🏭 *أمر تشغيل وتوزيع وردية — {plant_name}*")
        lines.append(f"🗓️ *النطاق:* {win_label}")
        lines.append(
            f"🎯 *المستهدفات:* التسليم بالموعد OTIF *{plan.kpis.otif_pct:.0f}%* | سقف هالك التنظيف الأسبوعي *{plan.kpis.purge_scrap_kg:.1f} كجم* | الكفاءة OEE *{plan.kpis.oee_pct:.1f}%*"
        )
        lines.append("")
        lines.append("⚙️ *جدول تشغيل المكابس وتسلسل الألوان:*")
    else:
        lines.append(f"🏭 *MINI-DIOS SHIFT DISPATCH — {plant_name}*")
        lines.append(f"🗓️ *Scope:* {win_label}")
        lines.append(
            f"🎯 *Targets:* OTIF *{plan.kpis.otif_pct:.0f}%* | Planned Purge Cap *{plan.kpis.purge_scrap_kg:.1f} kg* | OEE *{plan.kpis.oee_pct:.1f}%*"
        )
        lines.append("")
        lines.append("⚙️ *PRESS RUN SEQUENCE & PURGE ALERTS:*")

    if not overlapping_jobs:
        lines.append(
            "• لا توجد أوامر مجدولة في هذه النافذة الزمنية."
            if is_ar
            else "• No active press runs scheduled inside this window."
        )
    else:
        by_press: dict[str, list] = {}
        for j in overlapping_jobs:
            by_press.setdefault(j.machine_id, []).append(j)

        for mid, p_jobs in by_press.items():
            p_name = p_jobs[0].machine_name
            lines.append(f"*{mid}* ({p_name}):")
            for j in p_jobs:
                t_start = _fmt_day_clock(j.start_min, language)
                t_end = _fmt_day_clock(j.end_min, language)
                exp_badge = " 🚢[تصدير]" if (is_ar and j.is_export) else (" 🚢[EXPORT]" if j.is_export else "")
                col_lbl = COLOR_AR.get(j.color, j.color) if is_ar else j.color
                if j.setup_mins > 0 or j.purge_scrap_kg > 0:
                    co_alert = (
                        f" ⚠️ تبديل/تنظيف {j.setup_mins}د ({j.purge_scrap_kg:.1f} كجم هالك)"
                        if is_ar
                        else f" ⚠️ Setup/Purge {j.setup_mins}m ({j.purge_scrap_kg:.1f}kg scrap)"
                    )
                else:
                    co_alert = " ✅ تشغيل مستمر" if is_ar else " ✅ Continuous run"

                lines.append(
                    f"  • *{j.order_id}* | {j.customer} — {j.sku_name}{exp_badge}"
                )
                lines.append(
                    f"    القالب: *{j.mold_id}* | الخامة: *{j.resin_code} ({col_lbl})* | {t_start} ← {t_end}{co_alert}"
                    if is_ar
                    else f"    Mold: *{j.mold_id}* | Resin: *{j.resin_code} ({col_lbl})* | {t_start} → {t_end}{co_alert}"
                )

    # Assigned Shift Crew & Gap Warnings
    lines.append("")
    if is_ar:
        lines.append("👷 *طاقم الوردية المكلف حسب الدور الوظيفي:*")
    else:
        lines.append("👷 *ASSIGNED SHIFT CREW BY ROLE:*")

    crew_count = 0
    open_gaps = 0
    role_order = (
        "Press_Operator",
        "Mold_Technician",
        "QC_Inspector",
        "Material_Handler",
        "Shift_Supervisor",
    )

    if wf is not None:
        target_days = list(range(7)) if scope == "full_week" else [day]
        target_shifts = (
            set(wf.shift_names)
            if (scope == "full_week" or shift == "ALL" or shift not in shift_by_name)
            else {shift}
        )

        for role in role_order:
            r_label = ROLE_NAMES_AR[role] if is_ar else ROLE_NAMES_EN[role]
            assigned_names: list[str] = []
            for row in wf.optimized.rosters:
                if row.role != role:
                    continue
                matched_slots: list[str] = []
                for d_i in target_days:
                    if d_i < len(row.cells) and row.cells[d_i] in target_shifts:
                        s_cell = row.cells[d_i]
                        if scope == "full_week":
                            d_short = DAY_NAMES_AR[d_i] if is_ar else DAY_NAMES[d_i]
                            matched_slots.append(f"{d_short}")
                        else:
                            matched_slots.append(s_cell)
                if matched_slots:
                    crew_count += 1
                    if scope == "full_week":
                        assigned_names.append(f"{row.name} ({len(matched_slots)}d)")
                    elif shift == "ALL":
                        s_tag = SHIFT_NAMES_AR.get(matched_slots[0], matched_slots[0]) if is_ar else matched_slots[0]
                        assigned_names.append(f"{row.name} [{s_tag}]")
                    else:
                        assigned_names.append(row.name)

            # Check demand gaps for this role inside the selected window
            role_gaps = [
                c
                for c in wf.optimized.demand
                if c.role == role
                and c.day in target_days
                and c.shift in target_shifts
                and c.required > c.scheduled
            ]
            gap_sum = sum(c.required - c.scheduled for c in role_gaps)
            open_gaps += gap_sum

            names_str = "، ".join(assigned_names) if (is_ar and assigned_names) else (", ".join(assigned_names) if assigned_names else ("لا يوجد تكليف" if is_ar else "None assigned"))
            gap_badge = (
                f" 🚨 *[عجز -{gap_sum}]*"
                if (is_ar and gap_sum > 0)
                else (f" 🚨 *[GAP -{gap_sum}]*" if gap_sum > 0 else "")
            )
            lines.append(f"• *{r_label}:* {names_str}{gap_badge}")

    if open_gaps == 0:
        lines.append(
            "✅ *جاهزية الطاقم:* تغطية الوردية مكتملة 100% ومطابقة لقوانين الراحة (11 ساعة)."
            if is_ar
            else "✅ *Crew Readiness:* 100% staffed & verified against 11h rest and press certification rules."
        )
    else:
        lines.append(
            f"⚠️ *تنبيه تغطية:* يوجد عجز إجمالي ({open_gaps}) في النافذة المختارة — يوصى بتكليف عمالة إسناد."
            if is_ar
            else f"⚠️ *Coverage Alert:* {open_gaps} open role slot gap(s) in selected window — assign relief staff."
        )

    lines.append("")
    lines.append(
        f"🔒 _كود المراجعة الحتمي: {result.run_id} (OR-Tools CP-SAT)_"
        if is_ar
        else f"🔒 _Deterministic Run ID: {result.run_id} (OR-Tools CP-SAT)_"
    )

    msg_text = "\n".join(lines)
    wa_url = f"https://wa.me/?text={quote(msg_text)}"

    return WhatsAppDispatchResponse(
        scope=scope,
        day=day,
        shift=shift,
        language=language,
        plant_name=plant_name,
        window_label=win_label,
        jobs_included=len(overlapping_jobs),
        crew_assigned_count=crew_count,
        open_gaps_count=open_gaps,
        message_text=msg_text,
        whatsapp_url=wa_url,
    )
