"""Mini-DIOS Plastics Reference Domain Adapter for the 5-Layer DI + 6-Primitive UEM Engine.

All plastics-specific domain rules, ontology mappings, OMG DMN 1.3 tables, OMG BPMN 2.0 templates,
two-way bounded workforce-press coupling, and Causal Decision Diagram definitions live here.
"""
from __future__ import annotations

import hashlib
import json
import math
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Optional

import ortools

from core.di import (
    ArchitectureValidationReport,
    BPMNFlowNode,
    BPMNProcessTemplate,
    BPMNSequenceFlow,
    BusinessOntologyGraph,
    CausalDecisionModel,
    CausalEdge,
    DMNDecisionTable,
    DMNInputColumn,
    DMNOutputColumn,
    DMNRegistry,
    DMNRule,
    DecisionLever,
    DecisionOutcome,
    EntityInstance,
    EntityTypeSpec,
    IntermediateMetric,
    InvariantViolation,
    SemanticInvariantSpec,
    TypedRelationship,
    validate_business_architecture,
)
from core.disruptions import apply_plant_scenarios
from core.financials import compute_financial_report
from core.kpi import build_schedule_plan, build_scorecard
from core.ontology import (
    DAYS,
    EXTENDED_HORIZON_MINS,
    RAMADAN_BLACKOUT_END_HR,
    RAMADAN_BLACKOUT_START_HR,
    AuditRecord,
    ConstraintCheck,
    PlantDataset,
    SchedulePlan,
    ScheduledMoldPm,
    SolveResult,
    SolverConfig,
    ValidationReport,
    compatible_active_presses,
    is_incompatible_resin_switch,
    order_duration_mins,
    order_gross_weight_kg,
    order_shots,
    ramadan_labor_multiplier,
    transition_penalty,
    validate_plant_data,
)
from core.risk_radar import compute_risk_radar
from core.seed import default_config, demo_dataset
from core.solver import DatasetValidationError, run_fifo_baseline
from core.uem import (
    ActivityNode,
    CumulativeEnvelope,
    ObjectiveTermSpec,
    ResourceNode,
    SynchronizationGroup,
    TimeWindow,
    TransitionEntry,
    TransitionMatrix,
    UEMActivityHint,
    UEMGraph,
    UEMSolution,
)
from core.uem_compiler import compile_and_solve_uem
from core.uem_verify import verify_uem_solution
from core.verify import verify_hard_constraints
from core.workforce_solver import shift_layout, solve_workforce, worker_unavailable_label


# --------------------------------------------------------------------------------------------
# Layer 1: Plastics Formal Business Ontology Builder
# --------------------------------------------------------------------------------------------
def build_plastics_ontology_graph(dataset: PlantDataset, config: SolverConfig) -> BusinessOntologyGraph:
    """Compile a `PlantDataset` + `SolverConfig` into a formal Layer 1 `BusinessOntologyGraph`."""
    entity_types = [
        EntityTypeSpec(
            type_id="PressMachine",
            label="Injection / Blow-Molding Press Machine",
            ontology_role="primary_resource",
            required_attributes=["tonnage", "hourly_energy_kwh", "hourly_operating_cost", "supports_hot_runner"],
            description="Unary primary molding machine with clamping tonnage and hot-runner manifold capability.",
        ),
        EntityTypeSpec(
            type_id="Mold",
            label="Physical Steel Mold Tooling",
            ontology_role="secondary_resource",
            required_attributes=["cavities", "cycle_time_sec", "base_changeover_mins", "maintenance_interval_shots"],
            description="Exclusive physical mold shared across compatible presses with finite shot-life PM interval.",
        ),
        EntityTypeSpec(
            type_id="ResinStock",
            label="Polymer Resin Silo & Regrind Pool",
            ontology_role="consumable_pool",
            required_attributes=["virgin_available_kg", "regrind_available_kg", "drying_lead_time_hrs"],
            description="Dual-tier virgin/regrind polymer inventory with pre-drying floor and barrel temperature profile.",
        ),
        EntityTypeSpec(
            type_id="ProductionOrder",
            label="Customer Production Order",
            ontology_role="demand_activity",
            required_attributes=["mold_id", "resin_code", "color", "quantity_pcs", "due_hr"],
            description="Customer batch demand requiring a compatible press, physical mold, and resin allocation.",
        ),
        EntityTypeSpec(
            type_id="FactoryWorker",
            label="Certified Shop-Floor Worker",
            ontology_role="workforce_actor",
            required_attributes=["role", "hourly_rate", "max_weekly_hours"],
            description="Role-certified floor operator, mold technician, QC inspector, handler, or supervisor.",
        ),
        EntityTypeSpec(
            type_id="ExportContainerGroup",
            label="Multi-SKU Export Container Consolidation Group",
            ontology_role="sync_container",
            required_attributes=["member_order_ids"],
            description="Port container shipment group requiring all member SKUs to finish before container release.",
        ),
    ]

    entities: list[EntityInstance] = []
    relationships: list[TypedRelationship] = []
    presses_by_id = {p.machine_id: p for p in dataset.presses}
    molds_by_id = {m.mold_id: m for m in dataset.molds}

    for p in dataset.presses:
        entities.append(
            EntityInstance(
                entity_id=p.machine_id,
                type_id="PressMachine",
                label=p.name,
                ontology_role="primary_resource",
                active=(p.status == "active"),
                attributes={
                    "tonnage": p.tonnage,
                    "process_type": p.process_type,
                    "supports_hot_runner": p.supports_hot_runner,
                    "hourly_energy_kwh": p.hourly_energy_kwh,
                    "hourly_operating_cost": p.hourly_operating_cost,
                    "status": p.status,
                },
            )
        )

    for m in dataset.molds:
        entities.append(
            EntityInstance(
                entity_id=m.mold_id,
                type_id="Mold",
                label=m.name,
                ontology_role="secondary_resource",
                active=True,
                attributes={
                    "cavities": m.cavities,
                    "cycle_time_sec": m.cycle_time_sec,
                    "is_hot_runner": m.is_hot_runner,
                    "base_changeover_mins": m.base_changeover_mins,
                    "current_shots": m.current_shots,
                    "maintenance_interval_shots": m.maintenance_interval_shots,
                    "shot_utilization_pct": m.shot_utilization_pct,
                    "pm_duration_hrs": m.pm_duration_hrs,
                },
            )
        )
        for mid in m.compatible_machines:
            p = presses_by_id.get(mid)
            if p is not None:
                hr_ok = (not m.is_hot_runner) or p.supports_hot_runner
                relationships.append(
                    TypedRelationship(
                        relationship_id=f"rel_mold_press_{m.mold_id}_{mid}",
                        relation_type="COMPATIBLE_WITH_PRIMARY",
                        source_id=m.mold_id,
                        target_id=mid,
                        cardinality="M:N",
                        attributes={"capability_match": hr_ok},
                    )
                )

    for r in dataset.resins:
        entities.append(
            EntityInstance(
                entity_id=r.resin_code,
                type_id="ResinStock",
                label=f"{r.resin_code} Polymer Pool",
                ontology_role="consumable_pool",
                active=True,
                attributes={
                    "virgin_available_kg": r.virgin_available_kg,
                    "regrind_available_kg": r.regrind_available_kg,
                    "virgin_cost_per_kg": r.virgin_cost_per_kg,
                    "regrind_cost_per_kg": r.regrind_cost_per_kg,
                    "drying_lead_time_hrs": r.drying_lead_time_hrs,
                    "barrel_temp_c": r.barrel_temp_c,
                },
            )
        )

    cg_members: dict[str, list[str]] = defaultdict(list)
    for o in dataset.orders:
        entities.append(
            EntityInstance(
                entity_id=o.order_id,
                type_id="ProductionOrder",
                label=f"{o.order_id} ({o.sku_name})",
                ontology_role="demand_activity",
                active=True,
                attributes={
                    "customer": o.customer,
                    "mold_id": o.mold_id,
                    "resin_code": o.resin_code,
                    "color": o.color,
                    "color_rank": o.color_rank,
                    "quantity_pcs": o.quantity_pcs,
                    "due_hr": o.due_hr,
                    "is_export": o.is_export,
                    "max_regrind_pct": o.max_regrind_pct,
                },
            )
        )
        if o.mold_id in molds_by_id:
            relationships.append(
                TypedRelationship(
                    relationship_id=f"rel_ord_mold_{o.order_id}_{o.mold_id}",
                    relation_type="REQUIRES_SECONDARY",
                    source_id=o.order_id,
                    target_id=o.mold_id,
                    cardinality="N:1",
                )
            )
            for p in compatible_active_presses(molds_by_id[o.mold_id], presses_by_id):
                relationships.append(
                    TypedRelationship(
                        relationship_id=f"rel_ord_press_{o.order_id}_{p.machine_id}",
                        relation_type="CAPABLE_ON_PRIMARY",
                        source_id=o.order_id,
                        target_id=p.machine_id,
                        cardinality="M:N",
                    )
                )
        relationships.append(
            TypedRelationship(
                relationship_id=f"rel_ord_resin_{o.order_id}_{o.resin_code}",
                relation_type="CONSUMES_FROM_POOL",
                source_id=o.order_id,
                target_id=o.resin_code,
                cardinality="N:1",
            )
        )
        if o.container_group_id:
            cg_members[o.container_group_id].append(o.order_id)

    for cg_id, oids in cg_members.items():
        entities.append(
            EntityInstance(
                entity_id=cg_id,
                type_id="ExportContainerGroup",
                label=f"Export Container {cg_id}",
                ontology_role="sync_container",
                active=True,
                attributes={"member_order_ids": oids},
            )
        )
        for oid in oids:
            relationships.append(
                TypedRelationship(
                    relationship_id=f"rel_ord_cg_{oid}_{cg_id}",
                    relation_type="CONSOLIDATED_IN_CONTAINER",
                    source_id=oid,
                    target_id=cg_id,
                    cardinality="N:1",
                )
            )

    for w in dataset.workers:
        entities.append(
            EntityInstance(
                entity_id=w.worker_id,
                type_id="FactoryWorker",
                label=w.name,
                ontology_role="workforce_actor",
                active=(w.status == "active"),
                attributes={
                    "role": w.role,
                    "hourly_rate": w.hourly_rate,
                    "max_weekly_hours": w.max_weekly_hours,
                    "certified_machine_ids": w.certified_machine_ids,
                    "status": w.status,
                },
            )
        )
        cert_ids = [p.machine_id for p in dataset.presses] if w.certified_machine_ids == "ALL" else list(w.certified_machine_ids)
        for mid in cert_ids:
            if mid in presses_by_id:
                relationships.append(
                    TypedRelationship(
                        relationship_id=f"rel_wrk_press_{w.worker_id}_{mid}",
                        relation_type="CERTIFIED_ON_PRIMARY",
                        source_id=w.worker_id,
                        target_id=mid,
                        cardinality="M:N",
                    )
                )

    invariants = [
        SemanticInvariantSpec(
            invariant_id="INV-HC1",
            name="Mold–Press Compatibility & Hot-Runner Manifold Invariant",
            category="capability",
            severity="error",
            expression_summary="forall order: exists active press in mold.compatible_machines where mold.is_hot_runner => press.supports_hot_runner",
        ),
        SemanticInvariantSpec(
            invariant_id="INV-HC2",
            name="Unary Press Non-Overlap & Breakdown Exclusion Invariant",
            category="structural",
            severity="error",
            expression_summary="forall press: NoOverlap(busy_intervals union downtime_windows) and Ramadan setup exclusion",
        ),
        SemanticInvariantSpec(
            invariant_id="INV-HC3",
            name="Physical Mold Exclusivity Invariant",
            category="structural",
            severity="error",
            expression_summary="forall mold: NoOverlap(active_runs_across_all_presses)",
        ),
        SemanticInvariantSpec(
            invariant_id="INV-HC4",
            name="Asymmetric Color & Polymer Purge Circuit Invariant",
            category="policy",
            severity="error",
            expression_summary="forall sequential (job_i, job_j) on press: start(job_j) - end(job_i) >= DMN_BARREL_PURGE_TRANSITION(job_i, job_j)",
        ),
        SemanticInvariantSpec(
            invariant_id="INV-HC5",
            name="Resin Pre-Drying Floor, Food-Grade Zero-Regrind & Silo Cap Invariant",
            category="policy",
            severity="error",
            expression_summary="start >= drying_lead_time and (max_regrind_pct == 0 => regrind_kg == 0) and sum(virgin + purge) <= virgin_available_kg",
        ),
        SemanticInvariantSpec(
            invariant_id="INV-HC6",
            name="Mold Shot-Life Preventive Maintenance Block Invariant",
            category="policy",
            severity="error",
            expression_summary="forall mold requiring PM: NoOverlap(pm_window, mold_runs) and shots_before_pm <= remaining_shot_budget",
        ),
    ]

    return BusinessOntologyGraph(
        ontology_id="ONT-MINI-DIOS-PLASTICS-V1",
        domain_name=dataset.name,
        version="1.5.0",
        entity_types=entity_types,
        entities=entities,
        relationships=relationships,
        invariants=invariants,
    )


# --------------------------------------------------------------------------------------------
# Layer 2: Plastics Pre-Solve Business Architecture Validator
# --------------------------------------------------------------------------------------------
def validate_plastics_architecture(
    dataset: PlantDataset, config: SolverConfig
) -> tuple[BusinessOntologyGraph, ArchitectureValidationReport, ValidationReport]:
    """Run Layer 1 ontology construction + Layer 2 Business Architecture Validation + Domain Validation."""
    ont_graph = build_plastics_ontology_graph(dataset, config)
    domain_report = validate_plant_data(dataset, config)

    def _bridge_domain_issues(_: BusinessOntologyGraph) -> list[InvariantViolation]:
        mapped: list[InvariantViolation] = []
        for iss in domain_report.issues:
            cat = "capability" if "COMPAT" in iss.code or "PRESS" in iss.code else "policy"
            mapped.append(
                InvariantViolation(
                    invariant_id=iss.code,
                    category=cat,  # type: ignore[arg-type]
                    severity=iss.severity,
                    entity_id=iss.entity_id,
                    message=iss.message,
                )
            )
        return mapped

    arch_report = validate_business_architecture(ont_graph, custom_evaluators=[_bridge_domain_issues])
    return ont_graph, arch_report, domain_report


# --------------------------------------------------------------------------------------------
# Layer 4: Plastics OMG DMN 1.3 Decision Tables
# --------------------------------------------------------------------------------------------
def build_plastics_dmn_registry(config: Optional[SolverConfig] = None) -> DMNRegistry:
    """Construct the formal OMG DMN 1.3 Decision Table Registry for Mini-DIOS Plastics."""
    cfg = config or default_config()
    ph = cfg.physics

    # Table 1: Asymmetric Barrel Color & Polymer Purge Decision Table (Hit Policy: FIRST)
    t_purge = DMNDecisionTable(
        table_id="DMN_BARREL_PURGE_TRANSITION",
        name="Barrel Polymer & Color Purge Transition Rules",
        hit_policy="FIRST",
        description="Determines setup mode, purge duration, and purge scrap kg between consecutive press jobs.",
        inputs=[
            DMNInputColumn(input_id="in_incompat_resin", label="Incompatible Polymer Switch", expression="incompatible_resin", type_ref="boolean"),
            DMNInputColumn(input_id="in_diff_resin", label="Different Compatible Polyolefin", expression="different_resin", type_ref="boolean"),
            DMNInputColumn(input_id="in_color_dir", label="Color Rank Direction", expression="color_direction", type_ref="string"),
        ],
        outputs=[
            DMNOutputColumn(output_id="out_purge_mode", label="Purge Mode", name="purge_mode", type_ref="string"),
            DMNOutputColumn(output_id="out_purge_mins", label="Base Purge Minutes", name="purge_mins", type_ref="number"),
            DMNOutputColumn(output_id="out_purge_kg", label="Base Purge Scrap (kg)", name="purge_kg", type_ref="number"),
        ],
        rules=[
            DMNRule(
                rule_id="R_PURGE_1",
                description="Incompatible polymer family switch requires full barrel teardown & heavy purge",
                input_entries=["true", "-", "-"],
                output_entries={
                    "purge_mode": "incompatible_resin",
                    "purge_mins": int(ph.incompatible_resin_purge_mins),
                    "purge_kg": float(ph.incompatible_resin_purge_kg),
                },
            ),
            DMNRule(
                rule_id="R_PURGE_2",
                description="Dark-to-Light pigment transition requires aggressive screw & manifold purge",
                input_entries=["false", "-", '"dark_to_light"'],
                output_entries={
                    "purge_mode": "dark_to_light",
                    "purge_mins": int(ph.dark_to_light_purge_mins),
                    "purge_kg": float(ph.dark_to_light_purge_kg),
                },
            ),
            DMNRule(
                rule_id="R_PURGE_3",
                description="Light-to-Dark pigment progression requires quick forward flush",
                input_entries=["false", "-", '"light_to_dark"'],
                output_entries={
                    "purge_mode": "light_to_dark",
                    "purge_mins": int(ph.light_to_dark_purge_mins),
                    "purge_kg": float(ph.light_to_dark_purge_kg),
                },
            ),
            DMNRule(
                rule_id="R_PURGE_4",
                description="Same pigment rank across compatible polyolefins (PP/HDPE/LDPE) requires mild thermal flush",
                input_entries=["false", "true", '"same_color"'],
                output_entries={
                    "purge_mode": "polyolefin_grade_flush",
                    "purge_mins": int(round(ph.light_to_dark_purge_mins * 1.4)),
                    "purge_kg": round(ph.light_to_dark_purge_kg * 1.5, 1),
                },
            ),
            DMNRule(
                rule_id="R_PURGE_5",
                description="Identical resin and identical color requires zero barrel purge",
                input_entries=["false", "false", '"same_color"'],
                output_entries={
                    "purge_mode": "none",
                    "purge_mins": 0,
                    "purge_kg": 0.0,
                },
            ),
        ],
    )

    # Table 2: Mold Preventive Maintenance (PM) Governance Table (Hit Policy: FIRST)
    t_pm = DMNDecisionTable(
        table_id="DMN_MOLD_PM_POLICY",
        name="Mold Preventive Maintenance Trigger & Window Policy",
        hit_policy="FIRST",
        description="Governs mandatory mold PM execution mode (static t=0 vs. autonomous floating window).",
        inputs=[
            DMNInputColumn(input_id="in_shot_util", label="Current Shot Utilization %", expression="shot_utilization_pct", type_ref="number"),
            DMNInputColumn(input_id="in_manual_lock", label="Manual PM Lock Active", expression="has_manual_lock", type_ref="boolean"),
            DMNInputColumn(input_id="in_auto_pm", label="Autonomous PM Window Toggle", expression="autonomous_pm_window", type_ref="boolean"),
        ],
        outputs=[
            DMNOutputColumn(output_id="out_pm_mode", label="Sync Group Kind", name="sync_kind", type_ref="string"),
            DMNOutputColumn(output_id="out_force_t0", label="Force Start at t=0", name="force_start_at_zero", type_ref="boolean"),
        ],
        rules=[
            DMNRule(
                rule_id="R_PM_1",
                description="Mold at or above 100% shot limit must lock immediately at t=0 before any run",
                input_entries=["[100..999]", "-", "true"],
                output_entries={"sync_kind": "floating_maintenance", "force_start_at_zero": True},
            ),
            DMNRule(
                rule_id="R_PM_2",
                description="Autonomous PM enabled below 100% shot limit floats PM within 75% horizon budget",
                input_entries=["< 100", "-", "true"],
                output_entries={"sync_kind": "floating_maintenance", "force_start_at_zero": False},
            ),
            DMNRule(
                rule_id="R_PM_3",
                description="Standard static PM locks mold at start of week (t=0)",
                input_entries=["-", "-", "false"],
                output_entries={"sync_kind": "fixed_maintenance", "force_start_at_zero": True},
            ),
        ],
    )

    # Table 3: Food-Grade & Export Regrind Safety Policy (Hit Policy: FIRST)
    t_regrind = DMNDecisionTable(
        table_id="DMN_FOOD_GRADE_REGRIND_SAFETY",
        name="Food-Contact & Export Regrind Allowance Policy",
        hit_policy="FIRST",
        description="Protects food/pharma/export orders with 0% regrind specification from scenario overrides.",
        inputs=[
            DMNInputColumn(input_id="in_max_rg", label="Order Max Regrind %", expression="max_regrind_pct", type_ref="number"),
            DMNInputColumn(input_id="in_is_export", label="Export Order Flag", expression="is_export", type_ref="boolean"),
        ],
        outputs=[
            DMNOutputColumn(output_id="out_allow_rg", label="Regrind Allowed", name="allow_regrind", type_ref="boolean"),
            DMNOutputColumn(output_id="out_tier", label="Quality Compliance Tier", name="compliance_tier", type_ref="string"),
        ],
        rules=[
            DMNRule(
                rule_id="R_RG_1",
                description="Zero-regrind orders (food/pharma/dairy) strictly require 100% virgin polymer",
                input_entries=["<= 0", "-"],
                output_entries={"allow_regrind": False, "compliance_tier": "food_pharma_100pct_virgin"},
            ),
            DMNRule(
                rule_id="R_RG_2",
                description="Industrial orders with positive max_regrind_pct permit granulated regrind blend",
                input_entries=["> 0", "-"],
                output_entries={"allow_regrind": True, "compliance_tier": "industrial_regrind_eligible"},
            ),
        ],
    )

    # Table 4: Shift Workforce Role Headcount Policy (Hit Policy: FIRST)
    t_workforce = DMNDecisionTable(
        table_id="DMN_SHIFT_WORKFORCE_HEADCOUNT",
        name="Shift Role Headcount Derivation Policy",
        hit_policy="FIRST",
        description="Derives auxiliary floor staffing (Supervisor, QC, Material Handler, Mold Tech) per shift.",
        inputs=[
            DMNInputColumn(input_id="in_act_presses", label="Active Presses in Shift", expression="active_press_count", type_ref="number"),
            DMNInputColumn(input_id="in_high_or_hygro", label="High Load (>=4) or Hygroscopic PET/ABS", expression="high_load_or_hygro", type_ref="boolean"),
            DMNInputColumn(input_id="in_mold_events", label="Mold Changeovers + PM Blocks", expression="mold_events", type_ref="number"),
        ],
        outputs=[
            DMNOutputColumn(output_id="out_sup", label="Shift Supervisors", name="shift_supervisors", type_ref="number"),
            DMNOutputColumn(output_id="out_qc", label="QC Inspectors", name="qc_inspectors", type_ref="number"),
            DMNOutputColumn(output_id="out_mh", label="Material Handlers", name="material_handlers", type_ref="number"),
            DMNOutputColumn(output_id="out_mt", label="Mold Technicians", name="mold_technicians", type_ref="number"),
        ],
        rules=[
            DMNRule(
                rule_id="R_WF_IDLE",
                description="Idle shift with zero active presses and zero mold events",
                input_entries=["== 0", "-", "== 0"],
                output_entries={"shift_supervisors": 0, "qc_inspectors": 0, "material_handlers": 0, "mold_technicians": 0},
            ),
            DMNRule(
                rule_id="R_WF_HIGH_HEAVY_MOLD",
                description="High-load or hygroscopic shift with >= 3 mold changeover/PM events",
                input_entries=[">= 1", "true", ">= 3"],
                output_entries={"shift_supervisors": 1, "qc_inspectors": 2, "material_handlers": 2, "mold_technicians": 2},
            ),
            DMNRule(
                rule_id="R_WF_HIGH_STD_MOLD",
                description="High-load or hygroscopic shift with 1-2 mold changeover/PM events",
                input_entries=[">= 1", "true", "[1..2]"],
                output_entries={"shift_supervisors": 1, "qc_inspectors": 2, "material_handlers": 2, "mold_technicians": 1},
            ),
            DMNRule(
                rule_id="R_WF_HIGH_NO_MOLD",
                description="High-load or hygroscopic shift with zero mold events",
                input_entries=[">= 1", "true", "== 0"],
                output_entries={"shift_supervisors": 1, "qc_inspectors": 2, "material_handlers": 2, "mold_technicians": 0},
            ),
            DMNRule(
                rule_id="R_WF_STD_HEAVY_MOLD",
                description="Standard-load shift with >= 3 mold changeover/PM events",
                input_entries=[">= 1", "false", ">= 3"],
                output_entries={"shift_supervisors": 1, "qc_inspectors": 1, "material_handlers": 1, "mold_technicians": 2},
            ),
            DMNRule(
                rule_id="R_WF_STD_MOLD",
                description="Standard-load shift with 1-2 mold changeover/PM events",
                input_entries=[">= 1", "false", "[1..2]"],
                output_entries={"shift_supervisors": 1, "qc_inspectors": 1, "material_handlers": 1, "mold_technicians": 1},
            ),
            DMNRule(
                rule_id="R_WF_STD_NO_MOLD",
                description="Standard-load shift with zero mold events",
                input_entries=[">= 1", "false", "== 0"],
                output_entries={"shift_supervisors": 1, "qc_inspectors": 1, "material_handlers": 1, "mold_technicians": 0},
            ),
        ],
    )

    return DMNRegistry(
        registry_id="DMN-MINI-DIOS-PLASTICS-V1",
        tables=[t_purge, t_pm, t_regrind, t_workforce],
    )


# --------------------------------------------------------------------------------------------
# Layer 3: Plastics OMG BPMN 2.0 Process Template
# --------------------------------------------------------------------------------------------
def build_plastics_bpmn_template() -> BPMNProcessTemplate:
    """Build the formal OMG BPMN 2.0 executable workflow template for Mini-DIOS Plastics."""
    nodes = [
        BPMNFlowNode(
            node_id="Start_Weekly_MPS_Cycle",
            name="Start Weekly Plant Scheduling & Roster Cycle",
            kind="startEvent",
        ),
        BPMNFlowNode(
            node_id="Task_Architecture_Validation_Gate",
            name="Pre-Solve Ontology & Architecture Validation Gate",
            kind="serviceTask",
            compiles_to_primitive="ValidatorGate",
        ),
        BPMNFlowNode(
            node_id="Task_DMN_FoodGrade_Regrind_Policy",
            name="Evaluate Food-Grade Regrind & Silo Inventory Caps",
            kind="businessRuleTask",
            dmn_table_id="DMN_FOOD_GRADE_REGRIND_SAFETY",
            compiles_to_primitive="CumulativeEnvelope",
        ),
        BPMNFlowNode(
            node_id="Task_DMN_Mold_PM_Gate",
            name="Evaluate Mold Shot-Life Preventive Maintenance Policy",
            kind="businessRuleTask",
            dmn_table_id="DMN_MOLD_PM_POLICY",
            compiles_to_primitive="SynchronizationGroup",
        ),
        BPMNFlowNode(
            node_id="Gw_Mold_PM_Mode",
            name="Autonomous vs. Static Mold PM Window?",
            kind="exclusiveGateway",
        ),
        BPMNFlowNode(
            node_id="Task_DMN_Sequence_Purge_Matrix",
            name="Compile Asymmetric Color & Polymer Purge Circuit Matrix",
            kind="businessRuleTask",
            dmn_table_id="DMN_BARREL_PURGE_TRANSITION",
            compiles_to_primitive="TransitionMatrix",
        ),
        BPMNFlowNode(
            node_id="Task_Press_Execution_Schedule",
            name="Compile & Solve Parallel-Press UEMGraph in OR-Tools CP-SAT",
            kind="serviceTask",
            compiles_to_primitive="ActivityNode",
        ),
        BPMNFlowNode(
            node_id="Timer_Export_Port_Cutoff",
            name="Port Container Cut-Off & 168h Horizon Timer",
            kind="boundaryTimerEvent",
            attached_to_ref="Task_Press_Execution_Schedule",
            timer_duration_iso="PT168H",
            compiles_to_primitive="ObjectiveTermSpec",
        ),
        BPMNFlowNode(
            node_id="Gw_Container_And_Workforce_Fork",
            name="Couple Export Containers & 5-Role Floor Workforce",
            kind="parallelGateway",
        ),
        BPMNFlowNode(
            node_id="Task_Export_Container_Barrier_Sync",
            name="Synchronize Multi-SKU Export Container Release Barriers",
            kind="serviceTask",
            compiles_to_primitive="SynchronizationGroup",
        ),
        BPMNFlowNode(
            node_id="Task_DMN_Shift_Workforce_Demand",
            name="Derive & Solve Coupled 5-Role Workforce Shift Envelopes",
            kind="businessRuleTask",
            dmn_table_id="DMN_SHIFT_WORKFORCE_HEADCOUNT",
            compiles_to_primitive="CumulativeEnvelope",
        ),
        BPMNFlowNode(
            node_id="Gw_TwoWay_Labor_Feedback",
            name="Two-Way Bounded Labor Feedback Check (Max 1 Iteration <=2.0s)",
            kind="exclusiveGateway",
        ),
        BPMNFlowNode(
            node_id="Task_PostSolve_UEM_Verification",
            name="Independent Post-Solve Verification (uem_verify.py + HC1-HC6)",
            kind="serviceTask",
            compiles_to_primitive="ValidatorGate",
        ),
        BPMNFlowNode(
            node_id="End_Verified_Plant_Schedule",
            name="Emit Verified Schedule, P&L Reconciliation & Causal Decision Diagram",
            kind="endEvent",
        ),
    ]

    flows = [
        BPMNSequenceFlow(flow_id="f1", source_ref="Start_Weekly_MPS_Cycle", target_ref="Task_Architecture_Validation_Gate"),
        BPMNSequenceFlow(flow_id="f2", source_ref="Task_Architecture_Validation_Gate", target_ref="Task_DMN_FoodGrade_Regrind_Policy"),
        BPMNSequenceFlow(flow_id="f3", source_ref="Task_DMN_FoodGrade_Regrind_Policy", target_ref="Task_DMN_Mold_PM_Gate"),
        BPMNSequenceFlow(flow_id="f4", source_ref="Task_DMN_Mold_PM_Gate", target_ref="Gw_Mold_PM_Mode"),
        BPMNSequenceFlow(
            flow_id="f5_auto",
            source_ref="Gw_Mold_PM_Mode",
            target_ref="Task_DMN_Sequence_Purge_Matrix",
            name="Autonomous Floating PM",
            condition_expression="config.autonomous_pm_window == true",
        ),
        BPMNSequenceFlow(
            flow_id="f5_static",
            source_ref="Gw_Mold_PM_Mode",
            target_ref="Task_DMN_Sequence_Purge_Matrix",
            name="Static t=0 PM Lock",
            condition_expression="config.autonomous_pm_window == false",
        ),
        BPMNSequenceFlow(flow_id="f6", source_ref="Task_DMN_Sequence_Purge_Matrix", target_ref="Task_Press_Execution_Schedule"),
        BPMNSequenceFlow(flow_id="f7", source_ref="Task_Press_Execution_Schedule", target_ref="Gw_Container_And_Workforce_Fork"),
        BPMNSequenceFlow(flow_id="f7_timer", source_ref="Timer_Export_Port_Cutoff", target_ref="Gw_Container_And_Workforce_Fork"),
        BPMNSequenceFlow(flow_id="f8_a", source_ref="Gw_Container_And_Workforce_Fork", target_ref="Task_Export_Container_Barrier_Sync"),
        BPMNSequenceFlow(flow_id="f8_b", source_ref="Gw_Container_And_Workforce_Fork", target_ref="Task_DMN_Shift_Workforce_Demand"),
        BPMNSequenceFlow(flow_id="f9_a", source_ref="Task_Export_Container_Barrier_Sync", target_ref="Gw_TwoWay_Labor_Feedback"),
        BPMNSequenceFlow(flow_id="f9_b", source_ref="Task_DMN_Shift_Workforce_Demand", target_ref="Gw_TwoWay_Labor_Feedback"),
        BPMNSequenceFlow(
            flow_id="f10_converged",
            source_ref="Gw_TwoWay_Labor_Feedback",
            target_ref="Task_PostSolve_UEM_Verification",
            name="Workforce Coverage Converged",
            condition_expression="shortage_shifts == 0 or feedback_iterations >= 1",
        ),
        BPMNSequenceFlow(flow_id="f11", source_ref="Task_PostSolve_UEM_Verification", target_ref="End_Verified_Plant_Schedule"),
    ]

    return BPMNProcessTemplate(
        process_id="BPMN_MiniDIOS_Plastics_Execution_V1",
        name="Mini-DIOS Plastics Order-to-Container & Workforce Optimization Process",
        is_executable=True,
        nodes=nodes,
        sequence_flows=flows,
    )


# --------------------------------------------------------------------------------------------
# Compilation of Plastics Ontology + BPMN + DMN into 6-Primitive UEMGraph
# --------------------------------------------------------------------------------------------
def _ramadan_blackout_time_windows(horizon_mins: int) -> list[TimeWindow]:
    n_days = max(7, int(math.ceil(horizon_mins / 1440.0)))
    return [
        TimeWindow(
            start_min=d * 1440 + RAMADAN_BLACKOUT_START_HR * 60,
            end_min=d * 1440 + RAMADAN_BLACKOUT_END_HR * 60,
            label="Ramadan Iftar Changeover Blackout",
        )
        for d in range(n_days)
    ]


def compile_plastics_to_uem_graph(
    eff_ds: PlantDataset,
    config: SolverConfig,
    mold_pm_durations_hrs: dict[str, float],
    mold_pm_reasons: dict[str, str],
    horizon_mins: int,
    baseline_plan: Optional[SchedulePlan] = None,
    dmn_registry: Optional[DMNRegistry] = None,
    tightened_shift_caps: Optional[dict[tuple[int, int], int]] = None,
    max_solve_seconds_override: Optional[float] = None,
) -> UEMGraph:
    """Compile effective `PlantDataset` + `SolverConfig` + DMN rules into a 6-primitive `UEMGraph`."""
    dmn = dmn_registry or build_plastics_dmn_registry(config)
    ph = config.physics
    presses = eff_ds.presses
    presses_by_id = {p.machine_id: p for p in presses}
    molds_by_id = {m.mold_id: m for m in eff_ds.molds}
    resins_by_code = {r.resin_code: r for r in eff_ds.resins}
    orders = eff_ds.orders

    # 1. Primitive 1: ResourceNode (Primary Presses, Secondary Molds, Consumable Resin Pools)
    resources: list[ResourceNode] = []
    for p in presses:
        bws = [
            TimeWindow(
                start_min=int(round(dw.start_hr * 60)),
                end_min=int(round(dw.end_hr * 60)),
                label=dw.reason,
            )
            for dw in p.downtime_windows
            if int(round(dw.end_hr * 60)) > int(round(dw.start_hr * 60))
        ]
        resources.append(
            ResourceNode(
                resource_id=p.machine_id,
                name=p.name,
                kind="primary_unary",
                active=(p.status == "active"),
                hourly_power_rate=p.hourly_energy_kwh,
                hourly_operating_cost=p.hourly_operating_cost,
                blocked_windows=bws,
                attributes={"tonnage": p.tonnage, "supports_hot_runner": p.supports_hot_runner},
            )
        )

    for m in eff_ds.molds:
        resources.append(
            ResourceNode(
                resource_id=m.mold_id,
                name=m.name,
                kind="secondary_exclusive",
                active=True,
                attributes={
                    "cavities": m.cavities,
                    "cycle_time_sec": m.cycle_time_sec,
                    "shot_utilization_pct": m.shot_utilization_pct,
                },
            )
        )

    for r in eff_ds.resins:
        resources.append(
            ResourceNode(
                resource_id=r.resin_code,
                name=f"{r.resin_code} Silo Pool",
                kind="consumable_pool",
                active=True,
                capacity=r.virgin_available_kg,
                secondary_capacity=r.regrind_available_kg,
                unit_primary_cost=r.virgin_cost_per_kg,
                unit_secondary_cost=r.regrind_cost_per_kg,
                lead_time_floor_mins=int(round(r.drying_lead_time_hrs * 60)),
            )
        )

    # Identify scarce resin pools so optional scheduling is enabled when needed
    dur_mins = [order_duration_mins(o, molds_by_id[o.mold_id]) for o in orders]
    gross_10 = [int(round(order_gross_weight_kg(o, molds_by_id[o.mold_id]) * 10)) for o in orders]
    max_rg_10 = [int(math.floor(gross_10[i] * (orders[i].max_regrind_pct / 100.0))) for i in range(len(orders))]
    min_vg_10 = [gross_10[i] - max_rg_10[i] for i in range(len(orders))]

    resin_min_vg_sum: dict[str, int] = defaultdict(int)
    resin_orders_cnt: dict[str, int] = defaultdict(int)
    for i, o in enumerate(orders):
        resin_min_vg_sum[o.resin_code] += min_vg_10[i]
        resin_orders_cnt[o.resin_code] += 1

    scarce_resins: set[str] = set()
    for r in eff_ds.resins:
        avail_10 = int(round(r.virgin_available_kg * 10))
        if resin_min_vg_sum[r.resin_code] + resin_orders_cnt[r.resin_code] * 350 > avail_10:
            scarce_resins.add(r.resin_code)

    # 2. Primitive 2: ActivityNode
    activities: list[ActivityNode] = []
    compat_press_ids_by_order: list[list[str]] = []
    for i, o in enumerate(orders):
        mold = molds_by_id[o.mold_id]
        resin = resins_by_code[o.resin_code]
        compat = compatible_active_presses(mold, presses_by_id)
        c_ids = [p.machine_id for p in compat]
        compat_press_ids_by_order.append(c_ids)

        # Evaluate Layer 4 DMN Food-Grade Regrind policy
        rg_decision = dmn.evaluate(
            "DMN_FOOD_GRADE_REGRIND_SAFETY",
            {"max_regrind_pct": o.max_regrind_pct, "is_export": o.is_export},
        )
        eff_max_rg_10 = max_rg_10[i] if rg_decision.get("allow_regrind", True) else 0

        dry_floor = int(round(resin.drying_lead_time_hrs * 60))
        pm_floor = 0 if config.autonomous_pm_window else int(round(mold_pm_durations_hrs.get(mold.mold_id, 0.0) * 60))
        start_lb = max(dry_floor, pm_floor)

        due_min = int(round(o.due_hr * 60))
        early_ref_min = max(0, due_min - 420) if (o.is_export and config.w_otif >= 50) else due_min
        export_mult = 1.5 if o.is_export else 1.0
        pen_per_min_cents = max(1, int(round((o.late_penalty_per_hr * export_mult / 60.0) * 100)))

        safety_buf_mins = 390 if (o.is_export and config.w_otif >= 50) else 0
        safety_buf_pen = (
            max(1, int(round((o.late_penalty_per_hr * 0.35 / 60.0) * 100)))
            if safety_buf_mins > 0
            else 0
        )

        is_scarce = o.resin_code in scarce_resins
        drop_pen = (
            int(round(48.0 * o.late_penalty_per_hr * export_mult * 100 * 4))
            if is_scarce
            else 0
        )

        gross_kg = gross_10[i] / 10.0
        wip_cents_per_min = (
            max(1, int(round((gross_kg * ph.holding_cost_per_kg_per_day / 1440.0) * 100)))
            if ph.holding_cost_per_kg_per_day > 0
            else 0
        )

        activities.append(
            ActivityNode(
                activity_id=o.order_id,
                name=o.sku_name,
                duration_mins=dur_mins[i],
                earliest_start_min=start_lb,
                due_min=due_min,
                earliness_ref_min=early_ref_min,
                compatible_primary_ids=c_ids,
                secondary_resource_id=o.mold_id,
                consumable_pool_id=o.resin_code,
                gross_consumable_units_10=gross_10[i],
                max_secondary_consumable_units_10=eff_max_rg_10,
                usage_cycles=order_shots(o, mold),
                optional=is_scarce,
                tardiness_penalty_cents_per_min=pen_per_min_cents,
                earliness_holding_cents_per_min=wip_cents_per_min,
                safety_buffer_mins=safety_buf_mins,
                safety_buffer_penalty_cents_per_min=safety_buf_pen,
                unscheduled_penalty_cents=drop_pen,
                sync_group_id=o.container_group_id,
                attributes={
                    "unscheduled_reason_default": f"Unscheduled due to {o.resin_code} virgin resin shortage cap",
                    "compliance_tier": rg_decision.get("compliance_tier", "standard"),
                },
            )
        )

    # 3. Primitive 3: TransitionMatrix (compiled via DMN_BARREL_PURGE_TRANSITION + transition_penalty)
    max_possible_setup = max(
        360,
        int(round(ph.light_to_dark_purge_mins * 1.5)) + 480,
        int(round(ph.dark_to_light_purge_mins * 1.5)) + 480,
        int(ph.incompatible_resin_purge_mins) + 480,
    )
    trans_entries: list[TransitionEntry] = []
    # Only generate transition entries for pairs that share at least one compatible active press
    for i, oi in enumerate(orders):
        set_i = set(compat_press_ids_by_order[i])
        if not set_i:
            continue
        mi = molds_by_id[oi.mold_id]
        for j, oj in enumerate(orders):
            if i == j:
                continue
            if not (set_i & set(compat_press_ids_by_order[j])):
                continue
            mj = molds_by_id[oj.mold_id]
            color_dir = (
                "dark_to_light"
                if oj.color_rank < oi.color_rank
                else ("light_to_dark" if oj.color_rank > oi.color_rank else "same_color")
            )
            dmn_purge = dmn.evaluate(
                "DMN_BARREL_PURGE_TRANSITION",
                {
                    "incompatible_resin": is_incompatible_resin_switch(oi.resin_code, oj.resin_code),
                    "different_resin": oi.resin_code != oj.resin_code,
                    "color_direction": color_dir,
                },
            )
            stp_m, purge_kg, reason = transition_penalty(oi, oj, mi, mj, physics=ph)
            purge_10 = int(round(purge_kg * 10))
            resin_j = resins_by_code[oj.resin_code]
            purge_cost_cents = int(round(purge_kg * resin_j.virgin_cost_per_kg * 100)) if purge_kg > 0 else 0
            trans_entries.append(
                TransitionEntry(
                    from_activity_id=oi.order_id,
                    to_activity_id=oj.order_id,
                    setup_mins=stp_m,
                    consumable_waste_units_10=purge_10,
                    consumable_pool_id=oj.resin_code,
                    transition_Waste_cost_cents=purge_cost_cents,
                    reason=str(dmn_purge.get("purge_mode", reason)),
                )
            )

    setup_blackouts = _ramadan_blackout_time_windows(horizon_mins) if config.ramadan_shift_mode else []
    transitions = TransitionMatrix(
        entries=trans_entries,
        max_possible_setup_mins=max_possible_setup,
        setup_downtime_cost_cents_per_min=int(round((250.0 / 60.0) * 100)),
        setup_blackout_windows=setup_blackouts,
    )

    # 4. Primitive 4: CumulativeEnvelope (Resin Pool Caps, Peak Tariff Envelopes & Shift Workforce Envelopes)
    envelopes: list[CumulativeEnvelope] = []
    for r in eff_ds.resins:
        envelopes.append(
            CumulativeEnvelope(
                envelope_id=f"env_resin_{r.resin_code}",
                kind="consumable_cap",
                resource_id=r.resin_code,
                primary_cap_units_10=int(round(r.virgin_available_kg * 10)),
                secondary_cap_units_10=int(round(r.regrind_available_kg * 10)),
            )
        )

    peak_surcharge_pct = max(0.0, ph.peak_tariff_multiplier - 1.0)
    if config.avoid_peak_tariff_hrs and peak_surcharge_pct > 0:
        n_peak_days = max(1, int(math.ceil(horizon_mins / 1440.0)))
        act_surcharges: dict[str, int] = {}
        for i, o in enumerate(orders):
            c_ids = compat_press_ids_by_order[i]
            if not c_ids:
                continue
            avg_kwh = sum(presses_by_id[mid].hourly_energy_kwh for mid in c_ids) / len(c_ids)
            act_surcharges[o.order_id] = max(
                1, int(round((avg_kwh / 60.0) * peak_surcharge_pct * ph.energy_tariff_per_kwh * 100))
            )
        for d in range(n_peak_days):
            ps = d * 1440 + ph.peak_start_hr * 60
            pe = d * 1440 + ph.peak_end_hr * 60
            if ps < horizon_mins:
                envelopes.append(
                    CumulativeEnvelope(
                        envelope_id=f"env_peak_day_{d}",
                        kind="time_window_tariff",
                        window=TimeWindow(start_min=ps, end_min=pe, label=f"Day {d} Peak Tariff Window"),
                        activity_surcharge_cents_per_min=act_surcharges,
                    )
                )

    # Two-Way Workforce-to-Press Shift Availability Envelopes (soft-overflow CUMULATIVE_CAP)
    n_active_presses = sum(1 for p in presses if p.status == "active")
    ppo = max(1, config.workforce.presses_per_operator)
    layout = shift_layout(config)
    operators = [w for w in eff_ds.workers if w.role == "Press_Operator"]

    for d in range(DAYS):
        avail_ops = sum(1 for w in operators if worker_unavailable_label(w, d, {}) is None)
        for si, sh in enumerate(layout):
            w0 = (d * 24 + sh.start_hr) * 60
            w1 = min((d * 24 + sh.end_hr) * 60, DAYS * 24 * 60)
            if w1 <= w0:
                continue
            if tightened_shift_caps and (d, si) in tightened_shift_caps:
                max_press_cap = tightened_shift_caps[(d, si)]
                overflow_cost = 450_000  # High penalty on feedback iteration to shift jobs out of shortage shift
                should_add = True
            else:
                # Only add forward shift envelope if total available operators on day `d` cannot staff all active presses
                max_press_cap = avail_ops * ppo
                overflow_cost = 180_000
                should_add = (len(operators) > 0) and (max_press_cap < n_active_presses)

            if should_add:
                envelopes.append(
                    CumulativeEnvelope(
                        envelope_id=f"env_shift_cap_d{d}_s{si}",
                        kind="shift_capacity_cap",
                        window=TimeWindow(start_min=w0, end_min=w1, label=f"Day {d} {sh.name} Operator Envelope"),
                        max_concurrent_activities=max_press_cap,
                        soft_overflow_allowed=True,
                        soft_overflow_cost_cents_per_unit=overflow_cost,
                        attributes={"day": d, "shift_idx": si, "shift_name": sh.name},
                    )
                )

    # 5. Primitive 5: SynchronizationGroup (Mold PM Blocks + Multi-SKU Export Container Consolidation)
    sync_groups: list[SynchronizationGroup] = []
    base_h_mins = ph.horizon_hrs * 60
    for mold in eff_ds.molds:
        pm_hrs = mold_pm_durations_hrs.get(mold.mold_id, 0.0)
        if pm_hrs <= 0:
            continue
        pm_mins = int(round(pm_hrs * 60))
        pm_reason = mold_pm_reasons.get(
            mold.mold_id,
            "shot_threshold_95pct" if mold.shot_utilization_pct >= 95.0 else "manual_lock",
        )
        pm_decision = dmn.evaluate(
            "DMN_MOLD_PM_POLICY",
            {
                "shot_utilization_pct": mold.shot_utilization_pct,
                "has_manual_lock": (pm_reason == "manual_lock"),
                "autonomous_pm_window": config.autonomous_pm_window,
            },
        )
        sync_kind = pm_decision.get("sync_kind", "fixed_maintenance")
        force_t0 = bool(pm_decision.get("force_start_at_zero", True))
        pm_deadline_min = min(horizon_mins, max(pm_mins, int(round(base_h_mins * 0.75))))
        rem_shots = (
            max(0, mold.maintenance_interval_shots - mold.current_shots)
            if pm_reason in ("shot_threshold_95pct", "midweek_shot_limit")
            else None
        )
        sync_groups.append(
            SynchronizationGroup(
                group_id=f"pm_sync_{mold.mold_id}",
                kind=sync_kind,  # type: ignore[arg-type]
                resource_id=mold.mold_id,
                maintenance_duration_mins=pm_mins,
                maintenance_deadline_min=pm_deadline_min,
                max_cycles_before_maintenance=rem_shots,
                force_start_at_zero=force_t0,
                trigger_reason=pm_reason,
            )
        )

    if config.container_sync_enabled and config.w_working_capital > 25:
        cg_map: dict[str, list[int]] = defaultdict(list)
        for i, o in enumerate(orders):
            if o.container_group_id:
                cg_map[o.container_group_id].append(i)
        for cg_id, idxs in cg_map.items():
            if len(idxs) < 2:
                continue
            wait_rates: dict[str, int] = {}
            for i in idxs:
                gross_tons = (gross_10[i] / 10.0) / 1000.0
                daily_hold_sar = gross_tons * ph.wip_holding_cost_per_ton_day
                wait_rates[orders[i].order_id] = max(1, int(round((daily_hold_sar / 1440.0) * 100)))
            sync_groups.append(
                SynchronizationGroup(
                    group_id=cg_id,
                    kind="barrier_consolidation",
                    activity_ids=[orders[i].order_id for i in idxs],
                    wait_holding_cents_per_min_by_activity=wait_rates,
                )
            )

    # 6. Primitive 6: ObjectiveTermSpec
    labor_mult = ramadan_labor_multiplier(ph) if config.ramadan_shift_mode else 1.0
    assign_costs: dict[str, int] = {}
    for i, o in enumerate(orders):
        run_hrs = dur_mins[i] / 60.0
        for mid in compat_press_ids_by_order[i]:
            p = presses_by_id[mid]
            assign_costs[f"{o.order_id}::{mid}"] = int(
                round(
                    run_hrs
                    * (p.hourly_energy_kwh * ph.energy_tariff_per_kwh + p.hourly_operating_cost * labor_mult)
                    * 100
                )
            )

    pri_cons_costs = {r.resin_code: int(round(r.virgin_cost_per_kg * 10)) for r in eff_ds.resins}
    sec_cons_costs = {r.resin_code: int(round(r.regrind_cost_per_kg * 10)) for r in eff_ds.resins}

    objective = ObjectiveTermSpec(
        transition_weight_multiplier=config.w_changeover_scrap * 3 + 1,
        timeliness_weight_multiplier=config.w_otif * 3 + 1,
        operating_energy_weight_multiplier=config.w_energy_cost * 2 + 1,
        working_capital_weight_multiplier=config.w_working_capital * 2 + 1,
        labor_envelope_weight_multiplier=max(1, config.workforce.w_coverage * 2),
        assignment_operating_cost_cents=assign_costs,
        primary_consumable_cost_cents_per_unit_10=pri_cons_costs,
        secondary_consumable_cost_cents_per_unit_10=sec_cons_costs,
    )

    # Warm-start hints from FIFO baseline
    hints: list[UEMActivityHint] = []
    if baseline_plan is not None:
        for fj in baseline_plan.jobs:
            hints.append(
                UEMActivityHint(
                    activity_id=fj.order_id,
                    scheduled=fj.scheduled,
                    primary_resource_id=fj.machine_id if fj.scheduled else None,
                    start_min=int(fj.start_min) if fj.scheduled else 0,
                    primary_consumable_units_10=int(round(fj.virgin_kg * 10)) if fj.scheduled else 0,
                    secondary_consumable_units_10=int(round(fj.regrind_kg * 10)) if fj.scheduled else 0,
                )
            )

    return UEMGraph(
        graph_id="UEM-MINI-DIOS-PLASTICS-V1",
        domain_name=eff_ds.name,
        horizon_mins=horizon_mins,
        base_horizon_mins=base_h_mins,
        max_solve_seconds=float(max_solve_seconds_override or config.max_solve_seconds),
        num_workers=config.num_workers,
        random_seed=config.random_seed,
        resources=resources,
        activities=activities,
        transitions=transitions,
        cumulative_envelopes=envelopes,
        sync_groups=sync_groups,
        objective=objective,
        hints=hints,
        metadata={"scarce_resins": sorted(scarce_resins)},
    )


def _uem_solution_to_schedule_plan(
    eff_ds: PlantDataset,
    config: SolverConfig,
    mold_pm_durations_hrs: dict[str, float],
    solution: UEMSolution,
    baseline_plan: SchedulePlan,
) -> SchedulePlan:
    """Convert a `UEMSolution` back into a `SchedulePlan` for downstream KPIs and P&L reconciliation."""
    if solution.status not in ("OPTIMAL", "FEASIBLE") or not solution.activities:
        return baseline_plan

    molds_by_id = {m.mold_id: m for m in eff_ds.molds}
    raw_assignments: list[dict] = []
    for sa in solution.activities:
        if not sa.scheduled:
            raw_assignments.append(
                {
                    "order_id": sa.activity_id,
                    "scheduled": False,
                    "unscheduled_reason": sa.unscheduled_reason or "Unscheduled due to resource shortage cap",
                }
            )
        else:
            raw_assignments.append(
                {
                    "order_id": sa.activity_id,
                    "scheduled": True,
                    "machine_id": sa.primary_resource_id,
                    "start_min": sa.start_min,
                    "end_min": sa.end_min,
                    "virgin_kg": round(sa.primary_consumable_units_10 / 10.0, 2),
                    "regrind_kg": round(sa.secondary_consumable_units_10 / 10.0, 2),
                }
            )

    mold_pm_windows: list[ScheduledMoldPm] = []
    if config.autonomous_pm_window:
        for mw in solution.maintenance_windows:
            mold = molds_by_id.get(mw.resource_id)
            if mold is None:
                continue
            mold_pm_windows.append(
                ScheduledMoldPm(
                    mold_id=mold.mold_id,
                    mold_name=mold.name,
                    machine_id=mold.compatible_machines[0] if mold.compatible_machines else eff_ds.presses[0].machine_id,
                    start_min=mw.start_min,
                    end_min=mw.end_min,
                    duration_hrs=round(mw.duration_mins / 60.0, 2),
                    mode="autonomous",
                    trigger_reason=mw.trigger_reason,  # type: ignore[arg-type]
                    deadline_hr=round(mw.deadline_min / 60.0, 1) if mw.deadline_min is not None else None,
                )
            )

    return build_schedule_plan(
        eff_ds,
        config,
        raw_assignments,
        mold_pm_durations_hrs,
        mold_pm_windows=mold_pm_windows or None,
    )


# --------------------------------------------------------------------------------------------
# Layer 5: Plastics Causal Decision Diagram (Levers -> Intermediates -> Outcomes)
# --------------------------------------------------------------------------------------------
def build_plastics_causal_decision_model(
    config: SolverConfig,
    result: Optional[SolveResult] = None,
) -> CausalDecisionModel:
    """Build the Layer 5 Decision Intelligence Causal Decision Diagram (CDD)."""
    levers = [
        DecisionLever(
            lever_id="L_W_CHANGEOVER_SCRAP",
            name="Changeover & Purge Scrap Priority Weight",
            category="objective_weight",
            current_value=config.w_changeover_scrap,
            default_value=35,
            min_value=0,
            max_value=100,
            unit="weight_pts",
            description="Controls AddCircuit campaign batching by mold and light-to-dark color progression.",
        ),
        DecisionLever(
            lever_id="L_W_OTIF",
            name="On-Time In-Full (OTIF) & Export Cut-Off Weight",
            category="objective_weight",
            current_value=config.w_otif,
            default_value=35,
            min_value=0,
            max_value=100,
            unit="weight_pts",
            description="Penalizes tardiness and enforces >=6.5h port safety buffer on export orders when >=50.",
        ),
        DecisionLever(
            lever_id="L_W_ENERGY_COST",
            name="Energy & Press Operating Efficiency Weight",
            category="objective_weight",
            current_value=config.w_energy_cost,
            default_value=15,
            min_value=0,
            max_value=100,
            unit="weight_pts",
            description="Routes molds to energy-efficient presses and penalizes peak electricity tariff overlap.",
        ),
        DecisionLever(
            lever_id="L_W_WORKING_CAPITAL",
            name="Working Capital, Regrind & Container Sync Weight",
            category="objective_weight",
            current_value=config.w_working_capital,
            default_value=15,
            min_value=0,
            max_value=100,
            unit="weight_pts",
            description="Maximizes allowed industrial regrind blend and aligns multi-SKU export container completion.",
        ),
        DecisionLever(
            lever_id="L_AVOID_PEAK_TARIFF",
            name="Avoid Peak Electricity Window (13:00-17:00)",
            category="operational_toggle",
            current_value=config.avoid_peak_tariff_hrs,
            default_value=False,
            unit="bool",
            description="Activates time-windowed tariff surcharge envelopes during daily 13:00-17:00 peak hours.",
        ),
        DecisionLever(
            lever_id="L_RAMADAN_SHIFT_MODE",
            name="Ramadan 6h Shift & Iftar Changeover Blackout Mode",
            category="operational_toggle",
            current_value=config.ramadan_shift_mode,
            default_value=False,
            unit="bool",
            description="Enforces daily 18:00-20:00 changeover blackouts and 4x6h (36h/wk max) workforce shifts.",
        ),
        DecisionLever(
            lever_id="L_AUTONOMOUS_PM_WINDOW",
            name="Autonomous Floating Mold PM Co-Optimization",
            category="operational_toggle",
            current_value=config.autonomous_pm_window,
            default_value=False,
            unit="bool",
            description="Floats mold preventive maintenance windows within 75% horizon while guarding shot budgets.",
        ),
        DecisionLever(
            lever_id="L_CONTAINER_SYNC",
            name="Multi-SKU Export Container Consolidation Sync",
            category="operational_toggle",
            current_value=config.container_sync_enabled,
            default_value=True,
            unit="bool",
            description="Couples companion SKUs sharing an export container group to minimize warehouse staging time.",
        ),
    ]

    if result is not None:
        b_kpis = result.baseline.kpis
        o_kpis = result.optimized.kpis
        b_fin = result.financials.baseline
        o_fin = result.financials.optimized
        wf_b = result.workforce.baseline.kpis if result.workforce else None
        wf_o = result.workforce.optimized.kpis if result.workforce else None
        risk_o = result.risk_radar.overall_risk_score if result.risk_radar else 0.0
    else:
        b_kpis = o_kpis = b_fin = o_fin = wf_b = wf_o = None
        risk_o = 0.0

    intermediates = [
        IntermediateMetric(
            metric_id="I_PURGE_SCRAP_KG",
            name="Barrel Purge Scrap Volume",
            baseline_value=b_kpis.purge_scrap_kg if b_kpis else 0.0,
            optimized_value=o_kpis.purge_scrap_kg if o_kpis else 0.0,
            delta_value=round((o_kpis.purge_scrap_kg - b_kpis.purge_scrap_kg), 2) if (b_kpis and o_kpis) else 0.0,
            unit="kg",
            formula_summary="sum(DMN_BARREL_PURGE_TRANSITION.purge_kg * active_circuit_arc)",
        ),
        IntermediateMetric(
            metric_id="I_CHANGEOVER_HOURS",
            name="Mold & Barrel Changeover Downtime",
            baseline_value=b_kpis.changeover_hours if b_kpis else 0.0,
            optimized_value=o_kpis.changeover_hours if o_kpis else 0.0,
            delta_value=round((o_kpis.changeover_hours - b_kpis.changeover_hours), 2) if (b_kpis and o_kpis) else 0.0,
            unit="hrs",
            formula_summary="sum(setup_mins) / 60.0 across active press transitions",
        ),
        IntermediateMetric(
            metric_id="I_LATE_ORDER_HOURS",
            name="Cumulative Order Tardiness",
            baseline_value=b_kpis.total_tardiness_hrs if b_kpis else 0.0,
            optimized_value=o_kpis.total_tardiness_hrs if o_kpis else 0.0,
            delta_value=round((o_kpis.total_tardiness_hrs - b_kpis.total_tardiness_hrs), 2) if (b_kpis and o_kpis) else 0.0,
            unit="hrs",
            formula_summary="sum(max(0, end_hr - due_hr)) across scheduled orders",
        ),
        IntermediateMetric(
            metric_id="I_CONTAINER_WAIT_HRS",
            name="Export Container Multi-SKU Staging Wait",
            baseline_value=b_kpis.container_wait_delay_hrs if b_kpis else 0.0,
            optimized_value=o_kpis.container_wait_delay_hrs if o_kpis else 0.0,
            delta_value=round((o_kpis.container_wait_delay_hrs - b_kpis.container_wait_delay_hrs), 2) if (b_kpis and o_kpis) else 0.0,
            unit="hrs",
            formula_summary="sum(cg_ship_hr - job_end_hr) across multi-SKU container groups",
        ),
        IntermediateMetric(
            metric_id="I_PEAK_WAREHOUSE_TONS",
            name="Peak Finished-Goods Warehouse Inventory",
            baseline_value=b_kpis.peak_warehouse_tons if b_kpis else 0.0,
            optimized_value=o_kpis.peak_warehouse_tons if o_kpis else 0.0,
            delta_value=round((o_kpis.peak_warehouse_tons - b_kpis.peak_warehouse_tons), 2) if (b_kpis and o_kpis) else 0.0,
            unit="tons",
            formula_summary="max_t(cumulative finished tons staged in warehouse before shipment release)",
        ),
        IntermediateMetric(
            metric_id="I_OVERTIME_LABOR_HOURS",
            name="Floor Workforce Overtime Hours",
            baseline_value=wf_b.overtime_hours if wf_b else 0.0,
            optimized_value=wf_o.overtime_hours if wf_o else 0.0,
            delta_value=round((wf_o.overtime_hours - wf_b.overtime_hours), 2) if (wf_b and wf_o) else 0.0,
            unit="hrs",
            formula_summary="sum(max(0, worker_weekly_hours - standard_weekly_hours))",
        ),
    ]

    cur = config.currency
    outcomes = [
        DecisionOutcome(
            outcome_id="O_NET_OPERATING_PROFIT",
            name="Weekly Net Operating Profit",
            category="financial",
            direction="maximize",
            baseline_value=b_fin.net_operating_profit if b_fin else 0.0,
            optimized_value=o_fin.net_operating_profit if o_fin else 0.0,
            delta_value=round(o_fin.net_operating_profit - b_fin.net_operating_profit, 2) if (b_fin and o_fin) else 0.0,
            improvement_pct=result.financials.profit_lift_pct if result else 0.0,
            unit=cur,
        ),
        DecisionOutcome(
            outcome_id="O_TOTAL_WEEKLY_SAVINGS",
            name="Total Weekly Cost & Margin Lift vs. FIFO",
            category="financial",
            direction="maximize",
            baseline_value=0.0,
            optimized_value=result.financials.total_weekly_savings if result else 0.0,
            delta_value=result.financials.total_weekly_savings if result else 0.0,
            improvement_pct=result.financials.profit_lift_pct if result else 0.0,
            unit=cur,
        ),
        DecisionOutcome(
            outcome_id="O_OTIF_SERVICE_LEVEL",
            name="On-Time In-Full (OTIF) Delivery Rate",
            category="service_level",
            direction="maximize",
            baseline_value=b_kpis.otif_pct if b_kpis else 0.0,
            optimized_value=o_kpis.otif_pct if o_kpis else 0.0,
            delta_value=round((o_kpis.otif_pct - b_kpis.otif_pct), 2) if (b_kpis and o_kpis) else 0.0,
            unit="%",
        ),
        DecisionOutcome(
            outcome_id="O_WORKFORCE_COVERAGE",
            name="Certified Shift Workforce Coverage",
            category="service_level",
            direction="maximize",
            baseline_value=wf_b.coverage_pct if wf_b else 100.0,
            optimized_value=wf_o.coverage_pct if wf_o else 100.0,
            delta_value=round((wf_o.coverage_pct - wf_b.coverage_pct), 2) if (wf_b and wf_o) else 0.0,
            unit="%",
        ),
        DecisionOutcome(
            outcome_id="O_PLANT_RISK_SCORE",
            name="Overall Plant Operational Risk Radar Score",
            category="operational_risk",
            direction="minimize",
            baseline_value=max(risk_o, 35.0),
            optimized_value=float(risk_o),
            delta_value=round(float(risk_o) - max(risk_o, 35.0), 1),
            unit="risk_pts",
        ),
    ]

    edges = [
        CausalEdge(
            edge_id="CE_01",
            source_id="L_W_CHANGEOVER_SCRAP",
            target_id="I_PURGE_SCRAP_KG",
            polarity="-",
            mechanism="Higher changeover/scrap weight groups light-to-dark colors and identical molds along AddCircuit arcs",
            governed_by_primitive="TransitionMatrix",
        ),
        CausalEdge(
            edge_id="CE_02",
            source_id="L_W_CHANGEOVER_SCRAP",
            target_id="I_CHANGEOVER_HOURS",
            polarity="-",
            mechanism="Reduces mechanical crane mold swaps across compatible presses",
            governed_by_primitive="TransitionMatrix",
        ),
        CausalEdge(
            edge_id="CE_03",
            source_id="L_W_OTIF",
            target_id="I_LATE_ORDER_HOURS",
            polarity="-",
            mechanism="Prioritizes tight due-date and export cut-off orders on fastest-cycling presses",
            governed_by_primitive="ObjectiveTermSpec",
        ),
        CausalEdge(
            edge_id="CE_04",
            source_id="L_AUTONOMOUS_PM_WINDOW",
            target_id="I_LATE_ORDER_HOURS",
            polarity="-",
            mechanism="Defers non-emergency mold PM after urgent export runs within remaining shot budget",
            governed_by_primitive="SynchronizationGroup",
        ),
        CausalEdge(
            edge_id="CE_05",
            source_id="L_CONTAINER_SYNC",
            target_id="I_CONTAINER_WAIT_HRS",
            polarity="-",
            mechanism="Aligns completion times of companion SKUs sharing a container_group_id",
            governed_by_primitive="SynchronizationGroup",
        ),
        CausalEdge(
            edge_id="CE_06",
            source_id="L_W_WORKING_CAPITAL",
            target_id="I_PEAK_WAREHOUSE_TONS",
            polarity="-",
            mechanism="Penalizes early WIP staging and unsynchronized container waiting inventory",
            governed_by_primitive="SynchronizationGroup",
        ),
        CausalEdge(
            edge_id="CE_07",
            source_id="L_RAMADAN_SHIFT_MODE",
            target_id="I_OVERTIME_LABOR_HOURS",
            polarity="-",
            mechanism="Clamps shift durations to 6h and weekly cap to 36h with Iftar setup blackout",
            governed_by_primitive="CumulativeEnvelope",
        ),
        CausalEdge(
            edge_id="CE_08",
            source_id="I_PURGE_SCRAP_KG",
            target_id="O_NET_OPERATING_PROFIT",
            polarity="-",
            mechanism="Virgin polymer wasted during barrel purging directly reduces gross margin",
            governed_by_primitive="ObjectiveTermSpec",
        ),
        CausalEdge(
            edge_id="CE_09",
            source_id="I_CHANGEOVER_HOURS",
            target_id="O_TOTAL_WEEKLY_SAVINGS",
            polarity="-",
            mechanism="Every avoided changeover hour saves downtime cost and mold technician load",
            governed_by_primitive="TransitionMatrix",
        ),
        CausalEdge(
            edge_id="CE_10",
            source_id="I_LATE_ORDER_HOURS",
            target_id="O_OTIF_SERVICE_LEVEL",
            polarity="-",
            mechanism="Eliminating tardiness raises on-time delivery percentage and avoids SLA penalties",
            governed_by_primitive="ActivityNode",
        ),
        CausalEdge(
            edge_id="CE_11",
            source_id="I_LATE_ORDER_HOURS",
            target_id="O_NET_OPERATING_PROFIT",
            polarity="-",
            mechanism="Contractual late delivery penalties erode net operating profit",
            governed_by_primitive="ObjectiveTermSpec",
        ),
        CausalEdge(
            edge_id="CE_12",
            source_id="I_CONTAINER_WAIT_HRS",
            target_id="O_NET_OPERATING_PROFIT",
            polarity="-",
            mechanism="Container staging wait incurs daily per-ton warehouse WIP holding charges",
            governed_by_primitive="SynchronizationGroup",
        ),
        CausalEdge(
            edge_id="CE_13",
            source_id="I_PEAK_WAREHOUSE_TONS",
            target_id="O_PLANT_RISK_SCORE",
            polarity="+",
            mechanism="High staged finished-goods tonnage drives warehouse congestion risk",
            governed_by_primitive="SynchronizationGroup",
        ),
        CausalEdge(
            edge_id="CE_14",
            source_id="I_OVERTIME_LABOR_HOURS",
            target_id="O_WORKFORCE_COVERAGE",
            polarity="+",
            mechanism="Balanced shift allocation and bounded two-way labor feedback close shift coverage gaps",
            governed_by_primitive="CumulativeEnvelope",
        ),
        CausalEdge(
            edge_id="CE_15",
            source_id="L_CONTAINER_SYNC",
            target_id="I_PEAK_WAREHOUSE_TONS",
            polarity="-",
            mechanism="Synchronized multi-SKU container completion prevents early single-SKU batches from piling up in warehouse storage",
            governed_by_primitive="SynchronizationGroup",
        ),
    ]

    return CausalDecisionModel(
        model_id="DI-CDD-MINI-DIOS-PLASTICS-V1",
        domain_name="Mini-DIOS Plastics",
        levers=levers,
        intermediates=intermediates,
        outcomes=outcomes,
        causal_edges=edges,
    )


# --------------------------------------------------------------------------------------------
# Full End-to-End 5-Layer UEM + DI Plastics Optimization Pipeline (with Two-Way Labor Coupling)
# --------------------------------------------------------------------------------------------
def solve_plastics_via_uem(dataset: PlantDataset, config: SolverConfig) -> SolveResult:
    """Execute the full 5-Layer Decision Intelligence + 6-Primitive UEMGraph Plastics Solver:

    1. Layer 1 & 2: Build `BusinessOntologyGraph` & run `validate_plastics_architecture`.
    2. Apply composable disruptions (`apply_plant_scenarios`).
    3. Run Naive FIFO Baseline Scheduler (`run_fifo_baseline`).
    4. Layer 3 & 4: Compile BPMN 2.0 workflow + DMN 1.3 decision tables into 6-primitive `UEMGraph`.
    5. Pass 1 Solve: Compile `UEMGraph` into OR-Tools CP-SAT (`compile_and_solve_uem`) + coupled `solve_workforce`.
    6. Two-Way Bounded Labor Feedback (Max 1 conditional re-solve capped at 2.0s if shift shortage detected).
    7. Verify all 6 UEM Primitives (`verify_uem_solution`) and all 6 Plastics Hard Constraints (`HC1-HC6`).
    8. Compute side-by-side Scorecard, P&L Reconciliation, Risk Radar, and SHA-256 Audit Record.
    """
    ont_graph, arch_report, validation = validate_plastics_architecture(dataset, config)
    if not validation.ready:
        raise DatasetValidationError(validation)

    eff_state = apply_plant_scenarios(dataset, config)
    eff_ds = eff_state.dataset
    pm_map = eff_state.mold_pm_durations_hrs

    molds_by_id = {m.mold_id: m for m in eff_ds.molds}
    total_dur = sum(order_duration_mins(o, molds_by_id[o.mold_id]) for o in eff_ds.orders)
    total_bd = sum(
        int(round((dw.end_hr - dw.start_hr) * 60))
        for p in eff_ds.presses
        for dw in p.downtime_windows
    )
    base_horizon_mins = config.physics.horizon_hrs * 60
    min_tail_mins = EXTENDED_HORIZON_MINS if config.physics.horizon_hrs == 168 else int(round(base_horizon_mins * 1.5))
    horizon_mins = max(base_horizon_mins, min_tail_mins, total_dur + total_bd + 2880)

    baseline_plan = run_fifo_baseline(eff_ds, config, pm_map, horizon_mins)
    dmn_registry = build_plastics_dmn_registry(config)

    # Pass 1: Compile into 6-Primitive UEMGraph and Solve
    uem_graph = compile_plastics_to_uem_graph(
        eff_ds=eff_ds,
        config=config,
        mold_pm_durations_hrs=pm_map,
        mold_pm_reasons=eff_state.mold_pm_reasons,
        horizon_mins=horizon_mins,
        baseline_plan=baseline_plan,
        dmn_registry=dmn_registry,
    )
    uem_sol = compile_and_solve_uem(uem_graph)
    opt_plan = _uem_solution_to_schedule_plan(eff_ds, config, pm_map, uem_sol, baseline_plan)
    workforce = solve_workforce(eff_ds, config, opt_plan)

    # Two-Way Bounded Labor Coupling: check if Pass 1 left Press_Operator shift shortages
    # when spare operator capacity exists on other shifts in the week (Max 1 re-solve capped at 2.0s)
    feedback_triggered = False
    feedback_adopted = False
    total_solve_ms = uem_sol.solve_time_ms

    if (
        workforce is not None
        and workforce.optimized.kpis.understaffed_slots > 0
        and uem_sol.status in ("OPTIMAL", "FEASIBLE")
    ):
        ppo = max(1, config.workforce.presses_per_operator)
        shift_name_to_idx = {sh.name: idx for idx, sh in enumerate(shift_layout(config))}
        op_shortage_cells = [
            c
            for c in workforce.optimized.demand
            if c.role == "Press_Operator" and c.required > c.scheduled and c.shift in shift_name_to_idx
        ]
        if op_shortage_cells:
            feedback_triggered = True
            tightened_caps: dict[tuple[int, int], int] = {
                (c.day, shift_name_to_idx[c.shift]): max(0, c.scheduled * ppo)
                for c in op_shortage_cells
            }
            fb_graph = compile_plastics_to_uem_graph(
                eff_ds=eff_ds,
                config=config,
                mold_pm_durations_hrs=pm_map,
                mold_pm_reasons=eff_state.mold_pm_reasons,
                horizon_mins=horizon_mins,
                baseline_plan=opt_plan,
                dmn_registry=dmn_registry,
                tightened_shift_caps=tightened_caps,
                max_solve_seconds_override=min(float(config.max_solve_seconds), 2.0),
            )
            fb_sol = compile_and_solve_uem(fb_graph)
            total_solve_ms += fb_sol.solve_time_ms

            if fb_sol.status in ("OPTIMAL", "FEASIBLE"):
                fb_plan = _uem_solution_to_schedule_plan(eff_ds, config, pm_map, fb_sol, baseline_plan)
                fb_wf = solve_workforce(eff_ds, config, fb_plan)
                fb_sch_cnt = fb_plan.kpis.total_orders - fb_plan.kpis.unscheduled_orders
                opt_sch_cnt = opt_plan.kpis.total_orders - opt_plan.kpis.unscheduled_orders
                if (
                    fb_wf is not None
                    and fb_sch_cnt >= opt_sch_cnt
                    and (
                        fb_wf.optimized.kpis.headcount_gap < workforce.optimized.kpis.headcount_gap
                        or fb_wf.optimized.kpis.understaffed_slots < workforce.optimized.kpis.understaffed_slots
                    )
                ):
                    uem_graph = fb_graph
                    uem_sol = fb_sol
                    opt_plan = fb_plan
                    workforce = fb_wf
                    feedback_adopted = True

    uem_checks = verify_uem_solution(uem_graph, uem_sol)
    opt_checks = verify_hard_constraints(eff_ds, config, opt_plan, pm_map)
    base_checks = verify_hard_constraints(eff_ds, config, baseline_plan, pm_map)
    all_passed = all(c.passed for c in opt_checks) and all(uc.passed for uc in uem_checks)

    scorecard = build_scorecard(baseline_plan, opt_plan, config)
    financials = compute_financial_report(eff_ds, config, baseline_plan, opt_plan, workforce)
    risk_radar = compute_risk_radar(eff_ds, config, opt_plan, workforce)

    inputs_canonical = json.dumps(
        {"dataset": dataset.model_dump(mode="json"), "config": config.model_dump(mode="json")},
        sort_keys=True,
    )
    schedule_canonical = json.dumps(
        [
            (j.order_id, j.machine_id, j.start_min, j.end_min, j.virgin_kg, j.regrind_kg)
            for j in opt_plan.jobs
        ],
        sort_keys=True,
    )
    inputs_sha = hashlib.sha256(inputs_canonical.encode("utf-8")).hexdigest()
    schedule_sha = hashlib.sha256(schedule_canonical.encode("utf-8")).hexdigest()

    run_id = f"PL-{uuid.uuid4().hex[:8].upper()}"
    created_at = datetime.now(timezone.utc).isoformat()

    solver_params = {
        **uem_sol.solver_params,
        "active_engine": "uem_di_v1",
        "horizon_hrs": config.physics.horizon_hrs,
        "scarce_resins": uem_graph.metadata.get("scarce_resins", []),
        "ontology_summary": ont_graph.summary_counts(),
        "architecture_gates_passed": arch_report.ready,
        "dmn_tables_evaluated": [t.table_id for t in dmn_registry.tables],
        "two_way_labor_coupling": {
            "enabled": True,
            "feedback_triggered": feedback_triggered,
            "feedback_adopted": feedback_adopted,
            "feedback_iterations": 1 if feedback_triggered else 0,
            "envelope_overflows": uem_sol.envelope_overflows,
        },
        "uem_primitives_verified": [uc.model_dump() for uc in uem_checks],
    }

    audit = AuditRecord(
        inputs_sha256=inputs_sha,
        schedule_sha256=schedule_sha,
        weights={
            "w_changeover_scrap": config.w_changeover_scrap,
            "w_otif": config.w_otif,
            "w_energy_cost": config.w_energy_cost,
            "w_working_capital": config.w_working_capital,
        },
        config=config,
        solver_params=solver_params,
        ortools_version=getattr(ortools, "__version__", "unknown"),
        constraints_verified=opt_checks,
        baseline_constraints_verified=base_checks,
        all_hard_constraints_passed=all_passed,
    )

    return SolveResult(
        run_id=run_id,
        created_at=created_at,
        dataset_name=dataset.name,
        currency=config.currency,
        fx_egp_per_sar=config.fx_egp_per_sar,
        status=uem_sol.status,
        solve_time_ms=total_solve_ms,
        objective=uem_sol.objective_value,
        best_bound=uem_sol.best_bound,
        gap_pct=uem_sol.gap_pct,
        active_engine="uem_di_v1",
        validation=validation,
        applied_scenarios=eff_state.applied_scenarios,
        optimized=opt_plan,
        baseline=baseline_plan,
        scorecard=scorecard,
        financials=financials,
        audit=audit,
        workforce=workforce,
        risk_radar=risk_radar,
    )


def build_plastics_blueprint(
    dataset: Optional[PlantDataset] = None,
    config: Optional[SolverConfig] = None,
    result: Optional[SolveResult] = None,
) -> dict[str, Any]:
    """Assemble the complete 5-Layer Decision Intelligence + 6-Primitive UEMGraph Blueprint JSON."""
    ds = dataset or demo_dataset()
    cfg = config or default_config()

    ont_graph, arch_report, _ = validate_plastics_architecture(ds, cfg)
    bpmn_template = build_plastics_bpmn_template()
    bpmn_validation = bpmn_template.validate_topology()
    dmn_registry = build_plastics_dmn_registry(cfg)

    eff_state = apply_plant_scenarios(ds, cfg)
    base_horizon_mins = cfg.physics.horizon_hrs * 60
    uem_graph = compile_plastics_to_uem_graph(
        eff_ds=eff_state.dataset,
        config=cfg,
        mold_pm_durations_hrs=eff_state.mold_pm_durations_hrs,
        mold_pm_reasons=eff_state.mold_pm_reasons,
        horizon_mins=max(base_horizon_mins, EXTENDED_HORIZON_MINS),
        dmn_registry=dmn_registry,
    )
    causal_model = build_plastics_causal_decision_model(cfg, result=result)

    return {
        "architecture": "5-Layer Decision Intelligence + 6-Primitive UEMGraph Compiler",
        "domain": ds.name,
        "layers": {
            "layer_1_business_ontology": {
                "ontology_id": ont_graph.ontology_id,
                "version": ont_graph.version,
                "counts": ont_graph.summary_counts(),
                "entity_types": [et.model_dump() for et in ont_graph.entity_types],
                "invariants": [inv.model_dump() for inv in ont_graph.invariants],
            },
            "layer_2_architecture_validation": arch_report.model_dump(),
            "layer_3_bpmn_process_template": {
                "process_id": bpmn_template.process_id,
                "name": bpmn_template.name,
                "topology_validation": bpmn_validation.model_dump(),
                "nodes": [n.model_dump() for n in bpmn_template.nodes],
                "sequence_flows": [sf.model_dump() for sf in bpmn_template.sequence_flows],
            },
            "layer_4_dmn_decision_tables": {
                "registry_id": dmn_registry.registry_id,
                "namespace": dmn_registry.namespace,
                "table_count": len(dmn_registry.tables),
                "tables": [
                    {
                        "table_id": t.table_id,
                        "name": t.name,
                        "hit_policy": t.hit_policy,
                        "rule_count": len(t.rules),
                        "inputs": [i.model_dump() for i in t.inputs],
                        "outputs": [o.model_dump() for o in t.outputs],
                        "rules": [r.model_dump() for r in t.rules],
                    }
                    for t in dmn_registry.tables
                ],
            },
            "uem_graph_6_primitives": {
                "graph_id": uem_graph.graph_id,
                "horizon_mins": uem_graph.horizon_mins,
                "primitive_counts": uem_graph.primitive_counts(),
                "primitives": [
                    "1. ResourceNode (Primary Unary Presses, Secondary Exclusive Molds, Consumable Resin Pools)",
                    "2. ActivityNode (Schedulable Production Orders with Release Floor, Due Date & Virgin/Regrind Split)",
                    "3. TransitionMatrix (Asymmetric Sequence-Dependent Setup & Barrel Purge AddCircuit Arcs)",
                    "4. CumulativeEnvelope (CUMULATIVE_CAP: Silo Inventory Caps, Peak Tariff Overlaps & Two-Way Shift Operator Envelopes)",
                    "5. SynchronizationGroup (Multi-SKU Export Container Release Barriers & Floating/Static Mold PM Windows)",
                    "6. ObjectiveTermSpec (Weighted Multi-Objective Coefficients in Integer Cents)",
                ],
            },
            "layer_5_causal_decision_meta_model": {
                **causal_model.model_dump(),
                "traced_causal_pathways": [p.model_dump() for p in causal_model.trace_causal_pathways()],
            },
        },
    }
