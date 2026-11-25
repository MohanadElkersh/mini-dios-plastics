"""End-to-end FastAPI REST & 4-Tab Excel Bridge tests for Mini-DIOS Plastics."""
from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook

from api.routes import set_audit_store
from core.audit import AuditStore
from main import app


@pytest.fixture()
def client(tmp_path):
    store = AuditStore(tmp_path / "api_plastics_audit.db")
    set_audit_store(store)
    return TestClient(app)


def test_health_and_demo_data(client: TestClient):
    h = client.get("/api/health")
    assert h.status_code == 200
    assert h.json()["service"] == "mini-dios-plastics"

    d = client.get("/api/demo-data")
    assert d.status_code == 200
    body = d.json()
    assert len(body["dataset"]["presses"]) == 6
    assert len(body["dataset"]["molds"]) == 10
    assert len(body["dataset"]["resins"]) == 5
    assert len(body["dataset"]["orders"]) == 24
    assert body["default_config"]["physics"]["horizon_hrs"] == 168
    assert body["default_config"]["physics"]["dark_to_light_purge_kg"] == 32.0
    assert body["default_config"]["physics"]["peak_tariff_multiplier"] == 1.4


def test_4_tab_excel_template_download_and_validate_roundtrip(client: TestClient):
    dl = client.get("/api/template.xlsx?sample=true")
    assert dl.status_code == 200
    wb = load_workbook(io.BytesIO(dl.content))
    assert wb.sheetnames == ["Presses", "Molds", "Resin_Inventory", "Production_Orders"]

    up = client.post(
        "/api/validate",
        files={
            "file": (
                "factory_backtest.xlsx",
                dl.content,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert up.status_code == 200
    body = up.json()
    assert body["report"]["ready"] is True
    assert len(body["dataset"]["presses"]) == 6
    assert len(body["dataset"]["orders"]) == 24


def test_solve_audit_log_and_export_brief_xlsx(client: TestClient):
    s = client.post("/api/solve", json={"config": {"currency": "EGP"}})
    assert s.status_code == 200
    res = s.json()
    run_id = res["run_id"]
    assert res["currency"] == "EGP"
    assert res["audit"]["all_hard_constraints_passed"] is True
    assert res["scorecard"]["purge_scrap_kg_saved"] > 0

    log = client.get("/api/audit-log")
    assert log.status_code == 200
    assert any(r["run_id"] == run_id for r in log.json()["runs"])

    run_get = client.get(f"/api/audit-log/{run_id}")
    assert run_get.status_code == 200
    assert run_get.json()["run_id"] == run_id

    exp = client.post("/api/export-brief.xlsx", json={"run_id": run_id, "currency": "SAR"})
    assert exp.status_code == 200
    wb = load_workbook(io.BytesIO(exp.content))
    assert wb.sheetnames == [
        "Purge_Scrap_Savings",
        "Executive_Gantt_Schedule",
        "Resin_Consumption",
        "Audit_Trail",
    ]
    assert wb["Executive_Gantt_Schedule"].max_row >= 25


def test_export_dataset_xlsx_and_live_physics_copilot_and_brief(client: TestClient, monkeypatch):
    monkeypatch.setenv("OFFLINE_MODE", "true")
    demo = client.get("/api/demo-data").json()
    ds = demo["dataset"]
    cfg = demo["default_config"]

    # Edit resin cost, dark_to_light_purge_kg, and add a new order
    ds["resins"][0]["virgin_cost_per_kg"] = 9.5
    ds["orders"].append(
        {
            "order_id": "ORD-STUDIO-99",
            "customer": "Live Studio Customer",
            "sku_name": "Studio Test Cap",
            "mold_id": "M-01",
            "resin_code": "HDPE",
            "color": "Yellow",
            "color_rank": 3,
            "quantity_pcs": 25000,
            "part_weight_g": 2.8,
            "max_regrind_pct": 0.0,
            "due_hr": 120.0,
            "late_penalty_per_hr": 400.0,
            "is_export": True,
        }
    )
    cfg["physics"]["dark_to_light_purge_kg"] = 64.0
    cfg["physics"]["energy_tariff_per_kwh"] = 0.55

    # 1. Export live edited dataset to 4-tab Excel & roundtrip validate
    exp_ds = client.post("/api/export-dataset.xlsx", json=ds)
    assert exp_ds.status_code == 200
    wb_ds = load_workbook(io.BytesIO(exp_ds.content))
    assert wb_ds.sheetnames == ["Presses", "Molds", "Resin_Inventory", "Production_Orders"]
    order_ids = [wb_ds["Production_Orders"].cell(row=r, column=1).value for r in range(2, wb_ds["Production_Orders"].max_row + 1)]
    assert "ORD-STUDIO-99" in order_ids

    # 2. Copilot uses live edited dataset + PlantPhysicsConfig
    cop = client.post(
        "/api/copilot/ask",
        json={"prompt": "Why is Mold M-04 a bottleneck?", "dataset": ds, "config": cfg, "language": "en"},
    )
    assert cop.status_code == 200
    cop_data = cop.json()
    assert cop_data["result"]["optimized"]["kpis"]["total_orders"] == 25
    assert cop_data["result"]["audit"]["config"]["physics"]["dark_to_light_purge_kg"] == 64.0

    # 3. Export brief directly from live dataset + config
    exp_br = client.post("/api/export-brief.xlsx", json={"dataset": ds, "config": cfg, "currency": "SAR"})
    assert exp_br.status_code == 200
    wb_br = load_workbook(io.BytesIO(exp_br.content))
    audit_rows = {
        wb_br["Audit_Trail"].cell(row=r, column=1).value: wb_br["Audit_Trail"].cell(row=r, column=2).value
        for r in range(2, wb_br["Audit_Trail"].max_row + 1)
    }
    assert '"dark_to_light_purge_kg":64.0' in audit_rows["config"].replace(" ", "")


def test_workspaces_crud_endpoints(client: TestClient):
    # 1. Initial list has seeded default workspace
    res = client.get("/api/workspaces")
    assert res.status_code == 200
    workspaces = res.json()["workspaces"]
    assert len(workspaces) >= 1
    assert any(w["workspace_id"] == "default" for w in workspaces)

    # 2. Get default workspace
    d_res = client.get("/api/workspaces/default")
    assert d_res.status_code == 200
    d_data = d_res.json()
    assert d_data["workspace_id"] == "default"
    assert len(d_data["dataset"]["presses"]) == 6

    # 3. Create a custom workspace
    custom_ds = d_data["dataset"]
    custom_ds["name"] = "Alexandria Custom Plant"
    custom_ds["presses"].pop()  # 5 presses
    c_res = client.post(
        "/api/workspaces",
        json={
            "workspace_id": "ws-alexandria",
            "name": "Alexandria Custom Plant",
            "dataset": custom_ds,
            "config": d_data["config"],
        },
    )
    assert c_res.status_code == 200
    assert c_res.json()["workspace_id"] == "ws-alexandria"

    # 4. List now contains both
    res2 = client.get("/api/workspaces")
    assert res2.status_code == 200
    ids = [w["workspace_id"] for w in res2.json()["workspaces"]]
    assert "ws-alexandria" in ids
    assert "default" in ids

    # 5. Delete custom workspace
    del_res = client.delete("/api/workspaces/ws-alexandria")
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] is True

    # 6. Verify 404 on deleted
    not_found = client.get("/api/workspaces/ws-alexandria")
    assert not_found.status_code == 404


def test_v13_backtest_template_and_replay_engine(client: TestClient):
    # 1. Download CSV & XLSX backtest templates
    tpl_csv = client.get("/api/backtest/template")
    assert tpl_csv.status_code == 200
    csv_text = tpl_csv.content.decode("utf-8")
    assert "actual_changeover_hrs" in csv_text
    assert "actual_purge_scrap_kg" in csv_text
    assert "export_penalty_cost" in csv_text

    tpl_xlsx = client.get("/api/backtest/template?format=xlsx")
    assert tpl_xlsx.status_code == 200
    wb = load_workbook(io.BytesIO(tpl_xlsx.content))
    assert "Historical_Press_Log" in wb.sheetnames

    # 2. Run built-in 1-month sample replay in EGP
    rep_sample = client.post(
        "/api/backtest/replay",
        json={"mode": "sample_30day_log", "currency": "EGP"},
    )
    assert rep_sample.status_code == 200
    data = rep_sample.json()
    assert data["currency"] == "EGP"
    assert data["period_days"] == 30
    assert data["orders_analyzed"] == 24
    delta = data["actual_vs_optimized"]
    assert delta["purge_scrap_saved_kg"] > 0
    assert delta["changeover_hrs_freed"] > 0
    assert delta["extra_sellable_units_unlocked"] > 0
    assert delta["extra_sellable_tons_unlocked"] > 0
    assert delta["total_cash_left_on_floor_1month"] > 0
    assert delta["annualized_cash_left_on_floor"] > delta["total_cash_left_on_floor_1month"]
    assert 1 <= delta["estimated_payback_days"] <= 30
    assert len(data["press_breakdown"]) >= 5

    # 3. Upload the downloaded CSV back to /api/backtest/replay
    rep_upload = client.post(
        "/api/backtest/replay",
        files={"file": ("factory_30day_log.csv", tpl_csv.content, "text/csv")},
        data={"currency": "SAR"},
    )
    assert rep_upload.status_code == 200
    up_data = rep_upload.json()
    assert up_data["currency"] == "SAR"
    assert up_data["actual_vs_optimized"]["total_cash_left_on_floor_1month"] > 0


def test_v13_guided_onboarding_container_sync_copilot_tradeoff_and_exports(client: TestClient, monkeypatch):
    monkeypatch.setenv("OFFLINE_MODE", "true")

    # 1. Guided 5-Step Onboarding Wizard endpoint
    onb = client.post(
        "/api/onboarding/generate",
        json={
            "plant_name": "10th of Ramadan Blow & Injection Plant",
            "primary_process": "Hybrid",
            "operating_model": "Hybrid",
            "currency": "EGP",
            "press_count": 6,
            "tonnage_tier": "mixed",
            "backup_press_enabled": True,
            "backup_speed_factor": 0.95,
            "standard_pm_duration_hrs": 5.0,
            "light_to_dark_priority": "strict",
            "min_batch_run_hrs": 8,
            "max_regrind_allowance_pct": 25.0,
            "shift_pattern": "3x8h",
            "avoid_peak_tariff_hrs": True,
            "max_weekly_hours_cap": 48.0,
            "container_sync_enabled": True,
            "fg_storage_capacity_tons": 18.0,
        },
    )
    assert onb.status_code == 200
    onb_data = onb.json()
    assert onb_data["dataset"]["name"] == "10th of Ramadan Blow & Injection Plant"
    assert len(onb_data["readiness_checklist"]) == 4
    assert all(item["erp_history_needed"] is False for item in onb_data["readiness_checklist"])
    assert onb_data["result"]["audit"]["all_hard_constraints_passed"] is True

    # 2. Container & WIP Sync KPIs and Risk Radar Warehouse Congestion alert
    opt_plan = onb_data["result"]["optimized"]
    assert len(opt_plan["container_groups"]) >= 3
    assert opt_plan["kpis"]["warehouse_utilization_pct"] > 0
    assert opt_plan["kpis"]["trapped_working_capital"] >= 0
    radar_alerts = onb_data["result"]["risk_radar"]["alerts"]
    assert any(a["category"] == "warehouse_congestion" for a in radar_alerts)

    # 3. Commander-Grade Financial Trade-Off Summary in Ops Copilot
    cop = client.post(
        "/api/copilot/ask",
        json={
            "prompt": "Enable Container & WIP Sync and set working capital weight to 60 and OTIF weight to 45 to synchronize multi-SKU export container CNT-JEDDAH-02",
            "dataset": onb_data["dataset"],
            "config": onb_data["config"],
            "current_result": onb_data["result"],
            "language": "en",
        },
    )
    assert cop.status_code == 200
    cop_body = cop.json()
    ft = cop_body["financial_tradeoff_summary"]
    assert ft is not None
    assert ft["value_protected_amount"] >= 0
    assert "Net Gain:" in ft["headline_en"]
    assert "صافي المكسب:" in ft["headline_ar"]

    # 4. Integration-Ready Export Endpoints (Excel, CSV & ERP JSON)
    run_id = onb_data["result"]["run_id"]
    exp_xlsx = client.get(f"/api/export/schedule.xlsx?run_id={run_id}&currency=EGP")
    assert exp_xlsx.status_code == 200
    wb_sched = load_workbook(io.BytesIO(exp_xlsx.content))
    assert wb_sched.sheetnames == ["Press Schedule", "Workforce Shifts", "KPIs & Savings", "Risk Radar"]

    exp_csv = client.get(f"/api/export/schedule.csv?run_id={run_id}&currency=EGP")
    assert exp_csv.status_code == 200
    csv_lines = exp_csv.content.decode("utf-8").strip().splitlines()
    assert len(csv_lines) >= 25
    assert "container_group_id" in csv_lines[0]

    exp_erp = client.get(f"/api/export/erp-payload.json?run_id={run_id}&currency=EGP")
    assert exp_erp.status_code == 200
    erp_json = exp_erp.json()
    assert erp_json["schema_version"] == "mini-dios-plastics-erp/v1.3"
    assert len(erp_json["work_orders"]) == 24
    assert len(erp_json["container_consolidations"]) >= 3
    assert len(erp_json["workforce_shift_roster"]) >= 20
