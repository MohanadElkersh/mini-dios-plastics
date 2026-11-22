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
