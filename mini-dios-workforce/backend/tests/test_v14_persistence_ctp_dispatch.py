"""v1.4 Regression & Unit Tests:
1. Persistent Database & Decision Checkpoints (`saved_workspaces`, `decision_checkpoints`, `pinned_scenarios`, `backtest_runs`, `DATABASE_URL` normalization & SQLite fallback).
2. Capable-to-Promise (CTP) Non-Destructive Rush-Order Quoter (`POST /api/quote/ctp` & `POST /api/quote/ctp/commit`).
3. 1-Click Bilingual WhatsApp Shift Dispatch Formatter (`POST /api/dispatch/whatsapp` in EN and AR).
"""
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from api.routes import set_audit_store
from core.audit import AuditStore, normalize_database_url
from core.seed import default_config, demo_dataset
from main import app


def test_database_url_normalization_and_sqlite_fallback(tmp_path: Path) -> None:
    # 1. postgres:// -> postgresql:// with sslmode=require for remote hosts
    norm_remote = normalize_database_url("postgres://user:pass@ep-cool-neon.aws.neon.tech:5432/diosdb")
    assert norm_remote is not None
    assert norm_remote.startswith("postgresql://user:pass@ep-cool-neon.aws.neon.tech:5432/diosdb")
    assert "sslmode=require" in norm_remote

    # 2. Localhost postgres URL keeps clean URL without forcing remote SSL
    norm_local = normalize_database_url("postgres://user:pass@localhost:5432/diosdb")
    assert norm_local == "postgresql://user:pass@localhost:5432/diosdb"

    # 3. AuditStore falls back cleanly to SQLite when DATABASE_URL is unset
    store = AuditStore(db_path=tmp_path / "mini_dios_test.db")
    assert store.storage_backend == "sqlite_fallback"
    assert store.pool_config["pool_size"] == 3
    assert store.pool_config["max_overflow"] == 2
    assert store.pool_config["pool_pre_ping"] is True


def test_saved_workspaces_and_decision_checkpoints_roundtrip(tmp_path: Path) -> None:
    store = AuditStore(db_path=tmp_path / "checkpoints_roundtrip.db")
    set_audit_store(store)
    client = TestClient(app)

    # Create a custom workspace with modified plant name and currency
    ds = demo_dataset()
    ds_custom = ds.model_copy(update={"name": "Alexandria Pilot Plant v1.4"})
    # Remove 2 orders in custom workspace so we can verify checkpoint restore brings back exact state
    ds_custom.orders = ds_custom.orders[:-2]
    cfg_custom = default_config().model_copy(update={"currency": "EGP", "w_changeover_scrap": 70, "w_otif": 15})

    save_ws_resp = client.post(
        "/api/workspaces",
        json={
            "workspace_id": "ws-alex-pilot",
            "name": ds_custom.name,
            "dataset": ds_custom.model_dump(mode="json"),
            "config": cfg_custom.model_dump(mode="json"),
            "record_checkpoint": True,
        },
    )
    assert save_ws_resp.status_code == 200
    ws_data = save_ws_resp.json()
    assert ws_data["workspace_id"] == "ws-alex-pilot"
    assert ws_data["currency"] == "EGP"

    # Verify decision checkpoint was automatically recorded
    cp_list_resp = client.get("/api/checkpoints")
    assert cp_list_resp.status_code == 200
    cp_payload = cp_list_resp.json()
    assert cp_payload["storage_backend"] == "sqlite_fallback"
    assert len(cp_payload["checkpoints"]) >= 1
    first_cp = cp_payload["checkpoints"][0]
    assert first_cp["trigger_source"] == "workspace_save"
    assert "Alexandria Pilot Plant v1.4" in first_cp["title_en"]
    assert first_cp["orders_count"] == len(ds.orders) - 2

    # Also create an explicit Copilot checkpoint via POST /api/checkpoints
    manual_cp_resp = client.post(
        "/api/checkpoints",
        json={
            "trigger_source": "copilot",
            "title_en": "Copilot Applied: Min Purge Scrap Strategy",
            "title_ar": "تطبيق المساعد: استراتيجية أقل هالك تنظيف",
            "dataset": ds_custom.model_dump(mode="json"),
            "config": cfg_custom.model_dump(mode="json"),
        },
    )
    assert manual_cp_resp.status_code == 200
    cp_id = manual_cp_resp.json()["checkpoint"]["id"]

    # Now restore the checkpoint and confirm atomic recalculation & state recovery
    restore_resp = client.post(f"/api/checkpoints/{cp_id}/restore")
    assert restore_resp.status_code == 200
    restored = restore_resp.json()
    assert restored["restored"] is True
    assert restored["dataset"]["name"] == "Alexandria Pilot Plant v1.4"
    assert len(restored["dataset"]["orders"]) == len(ds.orders) - 2
    assert restored["config"]["w_changeover_scrap"] == 70
    assert restored["result"]["status"] in ("OPTIMAL", "FEASIBLE")
    assert restored["workforce"] is not None
    assert restored["risk_radar"] is not None


def test_ctp_rush_order_quoter_is_strictly_non_destructive(tmp_path: Path) -> None:
    store = AuditStore(db_path=tmp_path / "ctp_non_destructive.db")
    set_audit_store(store)
    client = TestClient(app)

    # Snapshot active default workspace before quoting
    ws_before = client.get("/api/workspaces/default").json()
    orders_before = ws_before["dataset"]["orders"]
    runs_before = client.get("/api/audit-log").json()["runs"]

    # Quote a 40,000-unit rush export order on Mold M-01
    quote_resp = client.post(
        "/api/quote/ctp",
        json={
            "customer": "Al-Marai Urgent Gulf Export",
            "sku_name": "28mm White Dairy Cap Rush",
            "mold_id": "M-01",
            "qty_units": 40000,
            "resin": "HDPE",
            "color": "White",
            "target_due_hour": 108.0,
            "unit_price": 0.08,
            "is_export": True,
            "max_regrind_pct": 0.0,
            "allow_peak_or_overtime": True,
            "currency": "SAR",
        },
    )
    assert quote_resp.status_code == 200
    q = quote_resp.json()

    assert q["verdict"] in ("ON_TIME", "LATE")
    assert q["assigned_press_id"] in ("P-150T", "P-250T")
    assert q["scheduled_start_hr"] is not None
    assert q["scheduled_end_hr"] is not None
    assert q["scheduled_end_hr"] > q["scheduled_start_hr"]

    fin = q["financial_impact"]
    assert fin["currency"] == "SAR"
    assert fin["gross_revenue"] == 3200.0
    assert fin["direct_resin_cost"] > 0
    assert fin["total_marginal_cost"] >= fin["direct_resin_cost"]
    assert fin["min_breakeven_unit_price"] > 0
    assert abs(fin["net_profit_contribution"] - (fin["gross_revenue"] - fin["total_marginal_cost"])) < 0.05
    assert isinstance(q["bumped_orders"], list)
    assert q["tradeoff_summary_en"]
    assert q["tradeoff_summary_ar"]
    assert q["candidate_order"]["order_id"].startswith("CTP-RUSH-")

    # Verify live workspace and audit runs were NOT mutated by quoting
    ws_after = client.get("/api/workspaces/default").json()
    runs_after = client.get("/api/audit-log").json()["runs"]
    assert len(ws_after["dataset"]["orders"]) == len(orders_before)
    assert len(runs_after) == len(runs_before)

    # Now test committing the quoted rush order via POST /api/quote/ctp/commit
    commit_resp = client.post(
        "/api/quote/ctp/commit",
        json={
            "candidate_order": q["candidate_order"],
        },
    )
    assert commit_resp.status_code == 200
    committed = commit_resp.json()
    assert committed["committed"] is True
    assert len(committed["dataset"]["orders"]) == len(orders_before) + 1
    assert committed["checkpoint"]["trigger_source"] == "ctp_commit"


def test_whatsapp_shift_dispatch_en_and_ar(tmp_path: Path) -> None:
    store = AuditStore(db_path=tmp_path / "whatsapp_dispatch.db")
    set_audit_store(store)
    client = TestClient(app)

    # 1. English Day/Shift Dispatch (Sunday Morning)
    en_resp = client.post(
        "/api/dispatch/whatsapp",
        json={
            "scope": "day_shift",
            "day": 0,
            "shift": "Morning",
            "language": "en",
        },
    )
    assert en_resp.status_code == 200
    en_data = en_resp.json()
    assert "MINI-DIOS SHIFT DISPATCH" in en_data["message_text"]
    assert "PRESS RUN SEQUENCE" in en_data["message_text"]
    assert "ASSIGNED SHIFT CREW BY ROLE" in en_data["message_text"]
    assert en_data["whatsapp_url"].startswith("https://wa.me/?text=")
    assert en_data["jobs_included"] >= 1
    assert en_data["crew_assigned_count"] >= 1

    # 2. Arabic Full-Week Dispatch
    ar_resp = client.post(
        "/api/dispatch/whatsapp",
        json={
            "scope": "full_week",
            "day": 0,
            "shift": "ALL",
            "language": "ar",
        },
    )
    assert ar_resp.status_code == 200
    ar_data = ar_resp.json()
    assert "أمر تشغيل وتوزيع وردية" in ar_data["message_text"]
    assert "طاقم الوردية المكلف حسب الدور الوظيفي" in ar_data["message_text"]
    assert ar_data["whatsapp_url"].startswith("https://wa.me/?text=")
    assert ar_data["jobs_included"] >= 10
