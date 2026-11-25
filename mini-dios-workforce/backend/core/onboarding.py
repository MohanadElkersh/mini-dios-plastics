"""Mini-DIOS Plastics — Guided "Process-First" 5-Step Onboarding Generator (Zero Historical ERP Needed).

Models fast 3-hour factory onboarding by capturing shop-floor operating rules first, then generating
an immediately solvable plant workspace alongside a lightweight "Current Specs Only" Readiness Checklist.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .ontology import (
    Currency,
    Mold,
    PlantDataset,
    PlantPhysicsConfig,
    PressMachine,
    ProcessType,
    SolverConfig,
    WorkforceConfig,
)
from .seed import default_config, demo_dataset


class GuidedSetupRequest(BaseModel):
    # Step 1: Process & Operating Model
    plant_name: str = Field(default="6th of October & Riyadh Polymer Plant", min_length=1)
    primary_process: Literal["Injection", "BlowMolding", "Extrusion", "Hybrid"] = "Hybrid"
    operating_model: Literal["MTO", "MTS", "Hybrid"] = "Hybrid"
    currency: Currency = "EGP"

    # Step 2: Presses & Backup Logic
    press_count: int = Field(default=6, ge=2, le=12)
    tonnage_tier: Literal["small_med", "heavy", "mixed"] = "mixed"
    backup_press_enabled: bool = True
    backup_speed_factor: float = Field(default=0.92, ge=0.70, le=1.0)
    standard_pm_duration_hrs: float = Field(default=5.0, ge=2.0, le=24.0)

    # Step 3: Color/Resin Purge & Batch Rules
    light_to_dark_priority: Literal["strict", "balanced"] = "strict"
    min_batch_run_hrs: int = Field(default=8, ge=2, le=48)
    max_regrind_allowance_pct: float = Field(default=20.0, ge=0.0, le=40.0)

    # Step 4: Workforce & Tariff Rules
    shift_pattern: Literal["3x8h", "2x12h", "ramadan_4x6h"] = "3x8h"
    avoid_peak_tariff_hrs: bool = True
    max_weekly_hours_cap: float = Field(default=48.0, ge=36.0, le=60.0)

    # Step 5: Export & Warehouse Rules
    container_sync_enabled: bool = True
    fg_storage_capacity_tons: float = Field(default=24.0, ge=5.0, le=500.0)


class ReadinessChecklistItem(BaseModel):
    item_id: str
    title_en: str
    title_ar: str
    detail_en: str
    detail_ar: str
    erp_history_needed: bool = False
    status: str = "ready"


def build_current_specs_checklist(req: GuidedSetupRequest) -> list[ReadinessChecklistItem]:
    """Return the 4-item 'Current Specs Only' Readiness Checklist reassuring factories that 0 ERP history is required."""
    return [
        ReadinessChecklistItem(
            item_id="chk-presses",
            title_en=f"1. Press Fleet & kW Ratings ({req.press_count} Active Lines)",
            title_ar=f"١. قائمة الماكينات واستهلاك الكهرباء ({req.press_count} خطوط نشطة)",
            detail_en="Current clamping tonnage, process type (Injection / Blow / Extrusion), and nameplate kWh/hr. Zero past downtime logs needed.",
            detail_ar="قوة الغلق بالطن، نوع العملية (حقن / نفخ / بثق)، واستهلاك الكيلوواط الحالي. لا حاجة لسجلات الأعطال التاريخية.",
        ),
        ReadinessChecklistItem(
            item_id="chk-molds",
            title_en=f"2. Mold Cavities, Cycle Times & Backup Compatibility ({'Backup Crossover ON' if req.backup_press_enabled else 'Single-Press'})",
            title_ar=f"٢. عدد فجوات القوالب، زمن الدورة، والماكينات البديلة ({'ماكينات بديلة مفعّلة' if req.backup_press_enabled else 'ماكينة وحيدة'})",
            detail_en=f"Current active cavity count, standard cycle seconds, and current shot counter (PM block at {req.standard_pm_duration_hrs:.0f}h).",
            detail_ar=f"عدد الفجوات النشطة حالياً، زمن الدورة بالثواني، وعداد الضربات الحالي (صيانة وقائية {req.standard_pm_duration_hrs:.0f} ساعات).",
        ),
        ReadinessChecklistItem(
            item_id="chk-bom",
            title_en=f"3. Part Weights, Colors & Regrind Rule (Up to {req.max_regrind_allowance_pct:.0f}% Non-Food)",
            title_ar=f"٣. وزن القطعة بالجرام، درجة اللون، ونسبة الريجريند (حتى {req.max_regrind_allowance_pct:.0f}% لغير الغذائي)",
            detail_en="Net part weight in grams, resin grade (PP/HDPE/PET/ABS/LDPE), and pigment color rank (Natural -> Black). Zero historical ERP sales tables required.",
            detail_ar="وزن القطعة الصافي بالجرام، نوع الخامة، ودرجة اللون (من الشفاف إلى الأسود). لا حاجة لأي جداول مبيعات تاريخية من ERP.",
        ),
        ReadinessChecklistItem(
            item_id="chk-silo",
            title_en=f"4. Today's Resin Silo Stock & Warehouse Ceiling ({req.fg_storage_capacity_tons:.0f} Tons FG Cap)",
            title_ar=f"٤. رصيد صوامع الخام الحالي وسقف مخزن المنتج التام ({req.fg_storage_capacity_tons:.0f} طن)",
            detail_en="Morning virgin & regrind kg on the floor plus this week's open customer orders and container groups.",
            detail_ar="رصيد الخام البكر والمعاد تدويره صباح اليوم مع أوامر العملاء المفتوحة لهذا الأسبوع ومجموعات حاويات التصدير.",
        ),
    ]


def build_guided_plant_workspace(
    req: GuidedSetupRequest,
) -> tuple[PlantDataset, SolverConfig, list[ReadinessChecklistItem]]:
    """Deterministically build a pre-configured, solvable PlantDataset and SolverConfig from the 5-step wizard."""
    seed_ds = demo_dataset()
    cfg = default_config()

    # 1. Configure Presses according to primary_process, press_count, and tonnage_tier
    proc_map: ProcessType = (
        "Injection"
        if req.primary_process in ("Injection", "Hybrid")
        else ("BlowMolding" if req.primary_process == "BlowMolding" else "Extrusion")
    )
    presses: list[PressMachine] = []
    for idx, p in enumerate(seed_ds.presses):
        if idx >= req.press_count:
            break
        tonnage = p.tonnage
        if req.tonnage_tier == "small_med":
            tonnage = min(350, max(150, p.tonnage))
        elif req.tonnage_tier == "heavy":
            tonnage = max(450, p.tonnage)
        p_proc: ProcessType = (
            p.process_type
            if req.primary_process == "Hybrid"
            else proc_map
        )
        presses.append(
            p.model_copy(
                update={
                    "process_type": p_proc,
                    "tonnage": tonnage,
                }
            )
        )

    # If user requested more than 6 presses, clone additional lines cleanly
    while len(presses) < req.press_count:
        src = presses[len(presses) % len(seed_ds.presses)]
        new_idx = len(presses) + 1
        new_id = f"P-L{new_idx:02d}"
        presses.append(
            src.model_copy(
                update={
                    "machine_id": new_id,
                    "name": f"{src.name} #{new_idx}",
                }
            )
        )

    active_pids = [p.machine_id for p in presses]

    # 2. Configure Molds (backup press compatibility + PM duration)
    molds: list[Mold] = []
    for idx, m in enumerate(seed_ds.molds):
        compat = [pid for pid in m.compatible_machines if pid in active_pids]
        if not compat:
            compat = [active_pids[idx % len(active_pids)]]
        if req.backup_press_enabled and len(compat) == 1 and len(active_pids) >= 2:
            # Add a secondary backup press of matching hot-runner capability
            primary_p = next(p for p in presses if p.machine_id == compat[0])
            candidates = [
                p.machine_id
                for p in presses
                if p.machine_id != compat[0]
                and (not m.is_hot_runner or p.supports_hot_runner)
            ]
            if candidates:
                compat.append(candidates[0])
        elif not req.backup_press_enabled and len(compat) > 1:
            compat = [compat[0]]

        adj_cycle = round(
            m.cycle_time_sec / max(0.75, min(1.0, req.backup_speed_factor if req.backup_press_enabled else 1.0)),
            1,
        )
        molds.append(
            m.model_copy(
                update={
                    "compatible_machines": compat,
                    "pm_duration_hrs": req.standard_pm_duration_hrs,
                    "cycle_time_sec": adj_cycle if req.backup_press_enabled else m.cycle_time_sec,
                }
            )
        )

    # 3. Configure Orders (regrind allowance, container sync, MTO/MTS due dates)
    orders = []
    for o in seed_ds.orders:
        next_rg = o.max_regrind_pct
        if next_rg > 0:
            next_rg = min(40.0, req.max_regrind_allowance_pct)
        cg_id = o.container_group_id if req.container_sync_enabled else None
        due_hr = o.due_hr
        if req.operating_model == "MTS":
            due_hr = min(168.0, o.due_hr + 12.0)
        orders.append(
            o.model_copy(
                update={
                    "max_regrind_pct": next_rg,
                    "container_group_id": cg_id,
                    "due_hr": due_hr,
                }
            )
        )

    # 4. Configure Workers (overtime cap + machine certifications)
    workers = [
        w.model_copy(
            update={
                "max_weekly_hours": req.max_weekly_hours_cap,
                "certified_machine_ids": "ALL" if req.backup_press_enabled else w.certified_machine_ids,
            }
        )
        for w in seed_ds.workers
    ]

    # 5. Configure SolverConfig & Physics
    is_ramadan = req.shift_pattern == "ramadan_4x6h"
    w_scrap = 55 if req.light_to_dark_priority == "strict" else 35
    w_otif = 45 if req.operating_model == "MTO" else 35
    w_wc = 30 if req.container_sync_enabled else 15
    w_en = 25 if req.avoid_peak_tariff_hrs else 15

    next_physics: PlantPhysicsConfig = cfg.physics.model_copy(
        update={
            "fg_storage_capacity_tons": req.fg_storage_capacity_tons,
        }
    )
    next_wf: WorkforceConfig = cfg.workforce.model_copy(
        update={
            "shift_length_hrs": 6 if is_ramadan else 8,
        }
    )

    next_cfg = cfg.model_copy(
        update={
            "currency": req.currency,
            "w_changeover_scrap": w_scrap,
            "w_otif": w_otif,
            "w_energy_cost": w_en,
            "w_working_capital": w_wc,
            "avoid_peak_tariff_hrs": req.avoid_peak_tariff_hrs,
            "ramadan_shift_mode": is_ramadan,
            "autonomous_pm_window": True,
            "container_sync_enabled": req.container_sync_enabled,
            "physics": next_physics,
            "workforce": next_wf,
        }
    )

    built_ds = PlantDataset(
        name=req.plant_name.strip(),
        presses=presses,
        molds=molds,
        resins=seed_ds.resins,
        orders=orders,
        workers=workers,
    )
    checklist = build_current_specs_checklist(req)
    return built_ds, next_cfg, checklist
