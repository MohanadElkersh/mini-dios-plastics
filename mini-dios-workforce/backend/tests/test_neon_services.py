"""Tests for Neon Cloud Platform integrations (`core/neon_services.py` and `/api/neon/*`)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from core.audit import AuditStore
from core.neon_services import (
    derive_database_name,
    get_neon_function_url,
    get_neon_realtime_config_status,
)
from main import app

client = TestClient(app)


def test_derive_database_name() -> None:
    assert (
        derive_database_name("postgresql://neondb_owner:secret@ep-demo.aws.neon.tech/neondb?sslmode=require")
        == "neondb"
    )
    assert derive_database_name("postgresql://user:pw@localhost:5432/custom_db") == "custom_db"
    assert derive_database_name("") in ("neondb", derive_database_name())


def test_get_neon_function_url(monkeypatch) -> None:
    monkeypatch.setenv("NEON_BRANCH_ID", "br-bold-hat-bh4fc43k")
    monkeypatch.setenv("NEON_FUNCTION_HOST_SUFFIX", ".compute.c-10.eu-central-1.aws.neon.tech")
    assert (
        get_neon_function_url("hello")
        == "https://br-bold-hat-bh4fc43k-hello.compute.c-10.eu-central-1.aws.neon.tech"
    )


def test_realtime_config_status(monkeypatch) -> None:
    monkeypatch.setenv("NEON_REALTIME_URL", "wss://realtime.aws.neon.tech")
    monkeypatch.setenv("NEON_REALTIME_SECRET", "rt_secret_test")
    status = get_neon_realtime_config_status()
    assert status["configured"] is True
    assert status["ok"] is True
    assert status["realtime_url"] == "wss://realtime.aws.neon.tech"
    assert status["secret_configured"] is True


def test_audit_store_probe_database(tmp_path) -> None:
    store = AuditStore(db_path=tmp_path / "probe_test.db")
    probe = store.probe_database()
    assert probe["ok"] is True
    assert probe["storage_backend"] == "sqlite_fallback"
    assert probe["saved_workspaces_count"] >= 1


def test_health_includes_neon_metadata() -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "storage_backend" in body
    assert "neon_function_hello_url" in body
