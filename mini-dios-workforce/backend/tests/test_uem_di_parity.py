"""Comprehensive Parity, Two-Way Labor Coupling, & Non-Plastics Bottling Proof Tests for the 5-Layer DI + 6-Primitive UEM Engine."""
from __future__ import annotations

import copy
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest
from fastapi.testclient import TestClient

from adapters.plastics import (
    build_plastics_blueprint,
    build_plastics_bpmn_template,
    build_plastics_causal_decision_model,
    build_plastics_dmn_registry,
    build_plastics_ontology_graph,
    solve_plastics_via_uem,
    validate_plastics_architecture,
)
from core.backtest import run_historical_backtest_replay
from core.copilot import run_plastics_copilot
from core.ctp import CTPQuoteRequest, evaluate_ctp_rush_order
from core.di import (
    BPMNFlowNode,
    BPMNProcessTemplate,
    BPMNSequenceFlow,
    BusinessOntologyGraph,
    DMNDecisionTable,
    DMNInputColumn,
    DMNOutputColumn,
    DMNRule,
    EntityInstance,
    EntityTypeSpec,
    TypedRelationship,
    validate_business_architecture,
)
from core.seed import default_config, demo_dataset
from core.solver import solve_plant_schedule
from core.uem import (
    ActivityNode,
    CumulativeEnvelope,
    ObjectiveTermSpec,
    ResourceNode,
    SynchronizationGroup,
    TransitionEntry,
    TransitionMatrix,
    UEMGraph,
)
from core.uem_compiler import compile_and_solve_uem
from core.uem_verify import verify_uem_solution
from main import app


# --------------------------------------------------------------------------------------------
# 1. Domain-Agnostic Core Purity Test (Zero Plastics Logic in Core UEM & DI Modules)
# --------------------------------------------------------------------------------------------
def test_zero_plastics_vocabulary_in_core_uem_and_di_modules():
    """Verify that core/uem*.py and core/di/*.py contain zero plastics-specific domain terms."""
    backend_root = Path(__file__).resolve().parent.parent
    core_files = [
        backend_root / "core" / "uem.py",
        backend_root / "core" / "uem_compiler.py",
        backend_root / "core" / "uem_verify.py",
        backend_root / "core" / "di" / "__init__.py",
        backend_root / "core" / "di" / "ontology_meta.py",
        backend_root / "core" / "di" / "arch_validator.py",
        backend_root / "core" / "di" / "bpmn_engine.py",
        backend_root / "core" / "di" / "dmn_engine.py",
        backend_root / "core" / "di" / "decision_meta.py",
    ]
    forbidden_terms = (
        "pressmachine",
        "resin_code",
        "regrind",
        "hot_runner",
        "purge_scrap",
        "cavities",
        "polyolefin",
        "mold_id",
    )
    for fpath in core_files:
        assert fpath.exists(), f"Missing core module: {fpath}"
        content_lower = fpath.read_text(encoding="utf-8").lower()
        for term in forbidden_terms:
            assert term not in content_lower, f"Forbidden plastics term '{term}' found in {fpath.name}"


# --------------------------------------------------------------------------------------------
# 2. 5-Layer DI Stack, BPMN 2.0 XML, DMN 1.3 XML, & /api/di/blueprint Endpoints
# --------------------------------------------------------------------------------------------
def test_five_layer_di_blueprint_and_xml_endpoints(monkeypatch: pytest.MonkeyPatch):
    client = TestClient(app)

    # Default health reports legacy_cpsat_v1
    monkeypatch.setenv("USE_UEM_ENGINE", "false")
    r_health_legacy = client.get("/api/health")
    assert r_health_legacy.status_code == 200
    assert r_health_legacy.json()["optimization_engine"] == "legacy_cpsat_v1"
    assert r_health_legacy.json()["use_uem_engine"] is False

    # Toggled health reports uem_di_v1
    monkeypatch.setenv("USE_UEM_ENGINE", "true")
    r_health_uem = client.get("/api/health")
    assert r_health_uem.status_code == 200
    assert r_health_uem.json()["optimization_engine"] == "uem_di_v1"
    assert r_health_uem.json()["use_uem_engine"] is True

    # JSON Blueprint
    r_bp = client.get("/api/di/blueprint?format=json")
    assert r_bp.status_code == 200
    bp = r_bp.json()
    assert bp["optimization_engine"] == "uem_di_v1"
    layers = bp["layers"]
    assert layers["layer_1_business_ontology"]["counts"]["entity_types"] == 6
    assert layers["layer_2_architecture_validation"]["ready"] is True
    assert layers["layer_3_bpmn_process_template"]["topology_validation"]["valid"] is True
    assert layers["layer_4_dmn_decision_tables"]["table_count"] == 4
    assert "rule_hit_counts" in layers["layer_4_dmn_decision_tables"]
    assert sum(layers["layer_4_dmn_decision_tables"]["rule_hit_counts"].values()) > 0
    for tbl in layers["layer_4_dmn_decision_tables"]["tables"]:
        assert any(r.get("fired") is True for r in tbl["rules"])
    assert layers["uem_graph_6_primitives"]["primitive_counts"]["ActivityNode"] == 24
    assert len(layers["layer_5_causal_decision_meta_model"]["traced_causal_pathways"]) >= 10

    # OMG BPMN 2.0 XML export
    r_bpmn = client.get("/api/di/blueprint?format=bpmn_xml")
    assert r_bpmn.status_code == 200
    assert "application/xml" in r_bpmn.headers["content-type"]
    assert "mini_dios_plastics_workflow.bpmn20.xml" in r_bpmn.headers.get("content-disposition", "")
    bpmn_root = ET.fromstring(r_bpmn.text)
    assert "BPMN/20100524/MODEL" in bpmn_root.tag

    # OMG DMN 1.3 XML export
    r_dmn = client.get("/api/di/blueprint?format=dmn_xml")
    assert r_dmn.status_code == 200
    assert "application/xml" in r_dmn.headers["content-type"]
    assert "mini_dios_plastics_rules.dmn13.xml" in r_dmn.headers.get("content-disposition", "")
    dmn_root = ET.fromstring(r_dmn.text)
    assert "DMN/20191111/MODEL" in dmn_root.tag


# --------------------------------------------------------------------------------------------
# 3. Full Legacy vs. UEM+DI Parity Suite Across Core Modes & Downstream Engines
# --------------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "mode_name,cfg_updates",
    [
        ("default", {}),
        ("peak_tariff", {"avoid_peak_tariff_hrs": True, "w_energy_cost": 55}),
        ("ramadan", {"ramadan_shift_mode": True}),
        ("auto_pm", {"autonomous_pm_window": True}),
        ("container_sync", {"container_sync_enabled": True, "w_working_capital": 60}),
    ],
)
def test_legacy_vs_uem_di_schedule_and_pnl_parity(
    monkeypatch: pytest.MonkeyPatch,
    mode_name: str,
    cfg_updates: dict,
):
    ds = demo_dataset()
    cfg = default_config().model_copy(update=cfg_updates)

    monkeypatch.setenv("USE_UEM_ENGINE", "false")
    legacy_res = solve_plant_schedule(copy.deepcopy(ds), copy.deepcopy(cfg))

    monkeypatch.setenv("USE_UEM_ENGINE", "true")
    uem_res = solve_plant_schedule(copy.deepcopy(ds), copy.deepcopy(cfg))

    # 1. Both engines must pass 100% of HC1-HC6 and WHC1-WHC5
    assert legacy_res.audit.all_hard_constraints_passed is True, f"Legacy failed HC in {mode_name}"
    assert uem_res.audit.all_hard_constraints_passed is True, f"UEM failed HC in {mode_name}"
    assert uem_res.workforce is not None and uem_res.workforce.all_hard_constraints_passed is True

    # 2. UEM audit record must confirm all 6 UEM primitives verified
    uem_prim_checks = uem_res.audit.solver_params.get("uem_primitives_verified", [])
    assert len(uem_prim_checks) == 6
    assert all(c["passed"] for c in uem_prim_checks)

    # 3. Exact scheduled order count, objective parity/improvement, and P&L reconciliation
    assert uem_res.optimized.kpis.unscheduled_orders == legacy_res.optimized.kpis.unscheduled_orders
    assert uem_res.optimized.kpis.total_orders == legacy_res.optimized.kpis.total_orders
    assert uem_res.objective <= legacy_res.objective * 1.05
    assert uem_res.financials.optimized.net_operating_profit >= legacy_res.financials.optimized.net_operating_profit * 0.94
    # Zero P&L rounding drift or double-counting
    for col in (uem_res.financials.baseline, uem_res.financials.optimized):
        assert round(col.recognized_revenue - col.variable_production_cost - col.weekly_fixed_overhead, 2) == pytest.approx(
            col.net_operating_profit, abs=0.05
        )


def test_ctp_backtest_and_copilot_under_uem_engine(monkeypatch: pytest.MonkeyPatch):
    """Verify CTP Quoter, 1-Month Backtest Replay, and Offline Copilot work seamlessly with USE_UEM_ENGINE=true."""
    monkeypatch.setenv("USE_UEM_ENGINE", "true")
    ds = demo_dataset()
    cfg = default_config()

    # CTP Rush-Order Quoter
    ctp_req = CTPQuoteRequest(
        customer="Gulf Dairy Export",
        sku_name="28mm Rush Cap",
        mold_id="M-01",
        qty_units=35_000,
        color="White",
        target_due_hour=96.0,
        is_export=True,
        dataset=ds,
        config=cfg,
    )
    ctp_res = evaluate_ctp_rush_order(ctp_req)
    assert ctp_res.verdict in ("ON_TIME", "LATE")
    assert ctp_res.assigned_press_id is not None

    # 1-Month Historical Backtest Replay
    bt_res = run_historical_backtest_replay(dataset=ds, config=cfg)
    assert bt_res.orders_analyzed > 0
    assert bt_res.actual_vs_optimized.total_cash_left_on_floor_1month > 0

    # Offline Operations Copilot
    cop_res = run_plastics_copilot(
        "Press P-02 breaks down for 12 hours and enable Ramadan shift mode",
        ds,
        cfg,
        None,
        "en",
        True,
    )
    assert cop_res.result is not None
    assert cop_res.result.audit.all_hard_constraints_passed is True
    assert cop_res.result.audit.solver_params.get("engine") == "uem_cpsat_v1"


# --------------------------------------------------------------------------------------------
# 4. Two-Way Bounded Labor Shortage Coupling Test
# --------------------------------------------------------------------------------------------
def test_two_way_bounded_labor_coupling_under_operator_shortage():
    """Verify that when Press_Operators are scarce on specific days/shifts, UEM's two-way labor coupling activates."""
    ds = demo_dataset()
    cfg = default_config()
    cfg.workforce.presses_per_operator = 1  # 1 operator per active press makes operator pool tight

    # Put most Press_Operators on approved leave on Sun (day 0) & Mon (day 1), leaving only 1 operator available
    op_seen = 0
    for w in ds.workers:
        if w.role == "Press_Operator":
            op_seen += 1
            if op_seen > 2:
                w.approved_leave_days = [0, 1]

    res = solve_plastics_via_uem(ds, cfg)
    assert res.audit.all_hard_constraints_passed is True
    labor_meta = res.audit.solver_params["two_way_labor_coupling"]
    assert labor_meta["enabled"] is True
    assert labor_meta["feedback_iterations"] <= 1


# --------------------------------------------------------------------------------------------
# 5. Non-Plastics Domain Universality Proof: Beverage Bottling & Canning Plant
# --------------------------------------------------------------------------------------------
def test_non_plastics_beverage_bottling_plant_on_uem_and_di_core():
    """Prove 100% domain-agnostic universality by compiling & solving a Beverage Bottling Plant on UEM+DI."""
    # Layer 1: Beverage Bottling Business Ontology
    ont = BusinessOntologyGraph(
        ontology_id="ONT-BEVERAGE-BOTTLING-01",
        domain_name="High-Speed Beverage Bottling Plant",
        entity_types=[
            EntityTypeSpec(
                type_id="BottlingLine",
                label="Rotary Filling & Capping Line",
                ontology_role="primary_resource",
                required_attributes=["bottles_per_min"],
            ),
            EntityTypeSpec(
                type_id="StarwheelFormat",
                label="Bottle Neck Starwheel Change-Part Set",
                ontology_role="secondary_resource",
                required_attributes=["bottle_size_ml"],
            ),
            EntityTypeSpec(
                type_id="SyrupTank",
                label="Flavor Syrup Batch Tank",
                ontology_role="consumable_pool",
                required_attributes=["liters_available"],
            ),
            EntityTypeSpec(
                type_id="BottlingOrder",
                label="Retail Beverage Bottling Order",
                ontology_role="demand_activity",
                required_attributes=["cases_qty", "due_min"],
            ),
        ],
        entities=[
            EntityInstance(
                entity_id="LINE-1",
                type_id="BottlingLine",
                label="Krones Rotary Filler 1",
                ontology_role="primary_resource",
                attributes={"bottles_per_min": 600},
            ),
            EntityInstance(
                entity_id="LINE-2",
                type_id="BottlingLine",
                label="Krones Rotary Filler 2",
                ontology_role="primary_resource",
                attributes={"bottles_per_min": 500},
            ),
            EntityInstance(
                entity_id="SW-330ML",
                type_id="StarwheelFormat",
                label="330ml Glass Starwheel Set",
                ontology_role="secondary_resource",
                attributes={"bottle_size_ml": 330},
            ),
            EntityInstance(
                entity_id="SW-1000ML",
                type_id="StarwheelFormat",
                label="1000ml Family Starwheel Set",
                ontology_role="secondary_resource",
                attributes={"bottle_size_ml": 1000},
            ),
            EntityInstance(
                entity_id="SYRUP-COLA",
                type_id="SyrupTank",
                label="Cola Concentrate Tank",
                ontology_role="consumable_pool",
                attributes={"liters_available": 5000},
            ),
            EntityInstance(
                entity_id="BOT-ORD-1",
                type_id="BottlingOrder",
                label="Cola 330ml Retail Batch",
                ontology_role="demand_activity",
                attributes={"cases_qty": 2000, "due_min": 720},
            ),
            EntityInstance(
                entity_id="BOT-ORD-2",
                type_id="BottlingOrder",
                label="Cola 1L Supermarket Batch",
                ontology_role="demand_activity",
                attributes={"cases_qty": 1500, "due_min": 960},
            ),
            EntityInstance(
                entity_id="BOT-ORD-3",
                type_id="BottlingOrder",
                label="Cola 330ml Export Pallet Batch",
                ontology_role="demand_activity",
                attributes={"cases_qty": 1800, "due_min": 960},
            ),
        ],
        relationships=[
            TypedRelationship(
                relationship_id="r1",
                relation_type="REQUIRES_SECONDARY",
                source_id="BOT-ORD-1",
                target_id="SW-330ML",
            ),
            TypedRelationship(
                relationship_id="r2",
                relation_type="REQUIRES_SECONDARY",
                source_id="BOT-ORD-2",
                target_id="SW-1000ML",
            ),
            TypedRelationship(
                relationship_id="r3",
                relation_type="REQUIRES_SECONDARY",
                source_id="BOT-ORD-3",
                target_id="SW-330ML",
            ),
            TypedRelationship(
                relationship_id="r4",
                relation_type="COMPATIBLE_WITH_PRIMARY",
                source_id="SW-330ML",
                target_id="LINE-1",
            ),
            TypedRelationship(
                relationship_id="r5",
                relation_type="COMPATIBLE_WITH_PRIMARY",
                source_id="SW-1000ML",
                target_id="LINE-1",
            ),
            TypedRelationship(
                relationship_id="r6",
                relation_type="COMPATIBLE_WITH_PRIMARY",
                source_id="SW-1000ML",
                target_id="LINE-2",
            ),
        ],
    )

    # Layer 2: Validate Bottling Business Architecture
    arch_rep = validate_business_architecture(ont)
    assert arch_rep.ready is True
    assert arch_rep.error_count == 0

    # Layer 4: DMN CIP (Clean-In-Place) Sanitization Rule Table
    cip_dmn = DMNDecisionTable(
        table_id="DMN_BOTTLING_CIP_WASH",
        name="Bottling Line CIP Sanitization Rules",
        hit_policy="FIRST",
        inputs=[
            DMNInputColumn(input_id="i1", label="Same Starwheel Format", expression="same_format", type_ref="boolean"),
        ],
        outputs=[
            DMNOutputColumn(output_id="o1", label="CIP Setup Minutes", name="cip_mins", type_ref="number"),
            DMNOutputColumn(output_id="o2", label="Syrup Flush Liters (x10)", name="flush_10", type_ref="number"),
        ],
        rules=[
            DMNRule(rule_id="CIP_1", input_entries=["true"], output_entries={"cip_mins": 15, "flush_10": 50}),
            DMNRule(rule_id="CIP_2", input_entries=["false"], output_entries={"cip_mins": 60, "flush_10": 200}),
        ],
    )

    # Layer 3: BPMN 2.0 Bottling Process Template
    bot_bpmn = BPMNProcessTemplate(
        process_id="BPMN_Beverage_Bottling_V1",
        name="Beverage Bottling & CIP Execution Workflow",
        nodes=[
            BPMNFlowNode(node_id="s1", name="Start Bottling Schedule", kind="startEvent"),
            BPMNFlowNode(node_id="t1", name="Evaluate CIP Sanitization Rules", kind="businessRuleTask", dmn_table_id="DMN_BOTTLING_CIP_WASH"),
            BPMNFlowNode(node_id="t2", name="Execute Rotary Filling Lines", kind="serviceTask"),
            BPMNFlowNode(node_id="e1", name="Bottling Complete", kind="endEvent"),
        ],
        sequence_flows=[
            BPMNSequenceFlow(flow_id="bf1", source_ref="s1", target_ref="t1"),
            BPMNSequenceFlow(flow_id="bf2", source_ref="t1", target_ref="t2"),
            BPMNSequenceFlow(flow_id="bf3", source_ref="t2", target_ref="e1"),
        ],
    )
    assert bot_bpmn.validate_topology().valid is True

    # Compile into 6-Primitive UEMGraph
    same_fmt_res = cip_dmn.evaluate({"same_format": True})
    diff_fmt_res = cip_dmn.evaluate({"same_format": False})

    uem_graph = UEMGraph(
        graph_id="UEM-BOTTLING-01",
        domain_name="Beverage Bottling",
        horizon_mins=1440,
        base_horizon_mins=1440,
        max_solve_seconds=2.0,
        resources=[
            ResourceNode(resource_id="LINE-1", name="Filler 1", kind="primary_unary"),
            ResourceNode(resource_id="LINE-2", name="Filler 2", kind="primary_unary"),
            ResourceNode(resource_id="SW-330ML", name="330ml Starwheel", kind="secondary_exclusive"),
            ResourceNode(resource_id="SW-1000ML", name="1000ml Starwheel", kind="secondary_exclusive"),
            ResourceNode(resource_id="SYRUP-COLA", name="Cola Syrup Pool", kind="consumable_pool", capacity=5000.0, lead_time_floor_mins=30),
        ],
        activities=[
            ActivityNode(
                activity_id="BOT-ORD-1",
                name="Cola 330ml Retail",
                duration_mins=180,
                earliest_start_min=30,
                due_min=720,
                compatible_primary_ids=["LINE-1"],
                secondary_resource_id="SW-330ML",
                consumable_pool_id="SYRUP-COLA",
                gross_consumable_units_10=12000,
            ),
            ActivityNode(
                activity_id="BOT-ORD-2",
                name="Cola 1L Supermarket",
                duration_mins=240,
                earliest_start_min=30,
                due_min=960,
                compatible_primary_ids=["LINE-1", "LINE-2"],
                secondary_resource_id="SW-1000ML",
                consumable_pool_id="SYRUP-COLA",
                gross_consumable_units_10=15000,
            ),
            ActivityNode(
                activity_id="BOT-ORD-3",
                name="Cola 330ml Export",
                duration_mins=200,
                earliest_start_min=30,
                due_min=960,
                compatible_primary_ids=["LINE-1"],
                secondary_resource_id="SW-330ML",
                consumable_pool_id="SYRUP-COLA",
                gross_consumable_units_10=11000,
            ),
        ],
        transitions=TransitionMatrix(
            entries=[
                TransitionEntry(
                    from_activity_id="BOT-ORD-1",
                    to_activity_id="BOT-ORD-3",
                    setup_mins=int(same_fmt_res["cip_mins"]),
                    consumable_waste_units_10=int(same_fmt_res["flush_10"]),
                    consumable_pool_id="SYRUP-COLA",
                    transition_Waste_cost_cents=5000,
                ),
                TransitionEntry(
                    from_activity_id="BOT-ORD-3",
                    to_activity_id="BOT-ORD-1",
                    setup_mins=int(same_fmt_res["cip_mins"]),
                    consumable_waste_units_10=int(same_fmt_res["flush_10"]),
                    consumable_pool_id="SYRUP-COLA",
                    transition_Waste_cost_cents=5000,
                ),
                TransitionEntry(
                    from_activity_id="BOT-ORD-1",
                    to_activity_id="BOT-ORD-2",
                    setup_mins=int(diff_fmt_res["cip_mins"]),
                    consumable_waste_units_10=int(diff_fmt_res["flush_10"]),
                    consumable_pool_id="SYRUP-COLA",
                    transition_Waste_cost_cents=25000,
                ),
                TransitionEntry(
                    from_activity_id="BOT-ORD-2",
                    to_activity_id="BOT-ORD-1",
                    setup_mins=int(diff_fmt_res["cip_mins"]),
                    consumable_waste_units_10=int(diff_fmt_res["flush_10"]),
                    consumable_pool_id="SYRUP-COLA",
                    transition_Waste_cost_cents=25000,
                ),
            ]
        ),
        cumulative_envelopes=[
            CumulativeEnvelope(
                envelope_id="env_syrup_cola",
                kind="consumable_cap",
                resource_id="SYRUP-COLA",
                primary_cap_units_10=50000,
                secondary_cap_units_10=0,
            )
        ],
        sync_groups=[
            SynchronizationGroup(
                group_id="PALLET-EXP-01",
                kind="barrier_consolidation",
                activity_ids=["BOT-ORD-2", "BOT-ORD-3"],
                wait_holding_cents_per_min_by_activity={"BOT-ORD-2": 5, "BOT-ORD-3": 5},
            )
        ],
        objective=ObjectiveTermSpec(),
    )

    sol = compile_and_solve_uem(uem_graph)
    assert sol.status in ("OPTIMAL", "FEASIBLE")
    assert len(sol.activities) == 3
    assert all(a.scheduled for a in sol.activities)

    checks = verify_uem_solution(uem_graph, sol)
    assert len(checks) == 6
    assert all(c.passed for c in checks)


# --------------------------------------------------------------------------------------------
# 6. Admin-Only Live Engine Mode Switcher & Per-Sandbox Isolation Tests
# --------------------------------------------------------------------------------------------
def test_admin_engine_mode_auth_gate_sandbox_isolation_and_reset(tmp_path, monkeypatch: pytest.MonkeyPatch):
    """Verify:
    1. Non-admin guest sessions (e.g. ALEX-2026) are rejected with 403 on GET/POST /api/admin/engine-mode.
    2. Admin session (ADMIN_PASSWORD) can switch legacy_cpsat_v1 -> uem_di_v1 -> legacy_cpsat_v1 -> default.
    3. Switching in Admin's sandbox does NOT affect Alexandria guest sandbox's engine mode.
    4. Subsequent /api/optimize (/api/solve) and /api/quote/ctp calls in Admin's sandbox inherit the override.
    """
    from api.routes import set_audit_store
    from core.audit import AuditStore
    from core.auth import reset_auth_runtime_state

    store = AuditStore(tmp_path / "admin_engine_test.db")
    set_audit_store(store)
    reset_auth_runtime_state()

    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_SECRET_KEY", "test-admin-engine-secret-2026")
    monkeypatch.setenv("DEMO_ACCESS_CODES", "Alexandria Plant:ALEX-2026,Riyadh Plant:KSA-2026")
    monkeypatch.setenv("ADMIN_PASSWORD", "SUPER-ADMIN-99")
    monkeypatch.setenv("USE_UEM_ENGINE", "false")

    guest_client = TestClient(app)
    admin_client = TestClient(app)

    # Unauthenticated call -> 401
    assert guest_client.get("/api/admin/engine-mode").status_code == 401
    assert guest_client.post("/api/admin/engine-mode", json={"engine": "uem_di_v1"}).status_code == 401

    # Guest logs in with ALEX-2026 -> is_admin is False, /api/admin/engine-mode rejected with 403
    r_guest_login = guest_client.post("/api/auth/login", json={"passcode": "ALEX-2026"})
    assert r_guest_login.status_code == 200
    assert r_guest_login.json()["is_admin"] is False
    assert guest_client.get("/api/admin/engine-mode").status_code == 403
    assert guest_client.post("/api/admin/engine-mode", json={"engine": "uem_di_v1"}).status_code == 403

    # Admin logs in with ADMIN_PASSWORD -> is_admin is True
    r_admin_login = admin_client.post("/api/auth/login", json={"passcode": "SUPER-ADMIN-99"})
    assert r_admin_login.status_code == 200
    assert r_admin_login.json()["is_admin"] is True
    assert r_admin_login.json()["active_engine"] == "legacy_cpsat_v1"

    # 1. Inspect initial engine mode (server default = legacy_cpsat_v1)
    r_mode_0 = admin_client.get("/api/admin/engine-mode")
    assert r_mode_0.status_code == 200
    m0 = r_mode_0.json()
    assert m0["active_engine"] == "legacy_cpsat_v1"
    assert m0["env_default_engine"] == "legacy_cpsat_v1"
    assert m0["is_override"] is False
    assert m0["di_standards"] == ["BusinessOntology", "ArchValidation", "DMN", "BPMN", "DI_CDD"]

    # 2. Switch Admin sandbox to uem_di_v1 -> immediate re-solve & unified scenario bundle
    r_sw_uem = admin_client.post("/api/admin/engine-mode", json={"engine": "uem_di_v1"})
    assert r_sw_uem.status_code == 200
    b_uem = r_sw_uem.json()
    assert b_uem["active_engine"] == "uem_di_v1"
    assert b_uem["is_override"] is True
    assert b_uem["switch_delta"]["prev_engine"] == "legacy_cpsat_v1"
    assert b_uem["switch_delta"]["new_engine"] == "uem_di_v1"
    assert b_uem["switch_delta"]["solve_time_ms"] > 0
    assert b_uem["result"]["active_engine"] == "uem_di_v1"
    assert b_uem["result"]["audit"]["all_hard_constraints_passed"] is True
    assert b_uem["workforce"]["all_hard_constraints_passed"] is True

    # 3. Verify subsequent /api/optimize and /api/quote/ctp in Admin sandbox use uem_di_v1
    r_opt = admin_client.post("/api/optimize", json={"config": default_config().model_dump(mode="json")})
    assert r_opt.status_code == 200
    assert r_opt.json()["active_engine"] == "uem_di_v1"
    assert r_opt.json()["audit"]["solver_params"]["active_engine"] == "uem_di_v1"

    r_ctp = admin_client.post(
        "/api/quote/ctp",
        json={
            "customer": "Admin Rush Test",
            "sku_name": "28mm Cap",
            "mold_id": "M-01",
            "qty_units": 25000,
            "color": "White",
            "target_due_hour": 96.0,
            "is_export": True,
        },
    )
    assert r_ctp.status_code == 200
    assert r_ctp.json()["active_engine"] == "uem_di_v1"

    # 4. Verify Guest sandbox (ALEX-2026) is still isolated on legacy_cpsat_v1
    r_guest_opt = guest_client.post("/api/optimize", json={"config": default_config().model_dump(mode="json")})
    assert r_guest_opt.status_code == 200
    assert r_guest_opt.json()["active_engine"] == "legacy_cpsat_v1"

    # 5. Switch Admin sandbox back to legacy_cpsat_v1 explicitly
    r_sw_leg = admin_client.post("/api/admin/engine-mode", json={"engine": "legacy_cpsat_v1"})
    assert r_sw_leg.status_code == 200
    assert r_sw_leg.json()["active_engine"] == "legacy_cpsat_v1"
    assert r_sw_leg.json()["is_override"] is True
    assert r_sw_leg.json()["switch_delta"]["prev_engine"] == "uem_di_v1"
    assert r_sw_leg.json()["switch_delta"]["new_engine"] == "legacy_cpsat_v1"
    assert r_sw_leg.json()["result"]["active_engine"] == "legacy_cpsat_v1"

    # 6. Reset Admin sandbox to "default" -> restores USE_UEM_ENGINE env default with is_override=False
    monkeypatch.setenv("USE_UEM_ENGINE", "true")
    r_sw_def = admin_client.post("/api/admin/engine-mode", json={"engine": "default"})
    assert r_sw_def.status_code == 200
    assert r_sw_def.json()["is_override"] is False
    assert r_sw_def.json()["active_engine"] == "uem_di_v1"
    assert r_sw_def.json()["env_default_engine"] == "uem_di_v1"

    reset_auth_runtime_state()

