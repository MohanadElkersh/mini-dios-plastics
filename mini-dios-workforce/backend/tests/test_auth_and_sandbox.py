"""Tests for Hosted Demo Auth Gate, Multi-Prospect Sandbox Isolation, and Copilot Quota Shield."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.routes import set_audit_store
from core.audit import AuditStore
from core.auth import SESSION_COOKIE_NAME, reset_auth_runtime_state
from core.copilot import CopilotResult, CopilotTiming
from core.seed import default_config, demo_dataset
from main import app


@pytest.fixture()
def isolated_env(tmp_path, monkeypatch):
    """Enable AUTH_ENABLED=true with isolated SQLite DB and clean rate-limit/quota state."""
    store = AuditStore(tmp_path / "auth_sandbox_audit.db")
    set_audit_store(store)
    reset_auth_runtime_state()

    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_SECRET_KEY", "test-hmac-secret-key-mini-dios-2026")
    monkeypatch.setenv(
        "DEMO_ACCESS_CODES",
        "Executive Demo:DIOS-2026,Alexandria Plant:ALEX-2026,Riyadh Plant:KSA-2026",
    )
    monkeypatch.setenv("ADMIN_PASSWORD", "SUPER-ADMIN-99")
    monkeypatch.setenv("ALLOW_INSTANT_DEMO", "true")
    monkeypatch.setenv("COPILOT_MAX_LIVE_CALLS_PER_HOUR", "2")
    yield store
    reset_auth_runtime_state()


def test_unauthenticated_blocked_when_auth_enabled(isolated_env):
    client = TestClient(app)

    # Public endpoints remain accessible
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["auth_enabled"] is True

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["auth_enabled"] is True
    assert me.json()["authenticated"] is False

    # Operational endpoints return 401
    solve_res = client.post("/api/solve", json={"config": default_config().model_dump(mode="json")})
    assert solve_res.status_code == 401

    ws_res = client.get("/api/workspaces")
    assert ws_res.status_code == 401

    demo_res = client.get("/api/demo-data")
    assert demo_res.status_code == 401


def test_login_cookie_unlocks_endpoints_and_logout_reglocks(isolated_env):
    client = TestClient(app)

    # Wrong passcode -> 401
    bad = client.post("/api/auth/login", json={"passcode": "WRONG-CODE"})
    assert bad.status_code == 401

    # Valid passcode -> 200 + HttpOnly signed cookie
    ok = client.post("/api/auth/login", json={"passcode": "ALEX-2026"})
    assert ok.status_code == 200
    body = ok.json()
    assert body["authenticated"] is True
    assert body["client_label"] == "Alexandria Plant"
    assert body["session_id"].startswith("sess_")
    assert SESSION_COOKIE_NAME in ok.cookies

    # /api/auth/me reflects authenticated session
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["authenticated"] is True
    assert me.json()["client_label"] == "Alexandria Plant"

    # Protected endpoints now succeed
    ws = client.get("/api/workspaces")
    assert ws.status_code == 200
    assert len(ws.json()["workspaces"]) == 1

    solve = client.post("/api/solve", json={"config": default_config().model_dump(mode="json")})
    assert solve.status_code == 200
    assert solve.json()["audit"]["all_hard_constraints_passed"] is True

    # Logout clears cookie -> re-gated
    out = client.post("/api/auth/logout")
    assert out.status_code == 200
    assert client.get("/api/workspaces").status_code == 401


def test_multi_prospect_workspace_isolation_and_sandbox_reset(isolated_env):
    client_alex = TestClient(app)
    client_riyadh = TestClient(app)

    r1 = client_alex.post("/api/auth/login", json={"passcode": "ALEX-2026"})
    r2 = client_riyadh.post("/api/auth/login", json={"passcode": "KSA-2026"})
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["session_id"] != r2.json()["session_id"]

    # Alexandria modifies its default workspace and saves a custom workspace
    ds_alex = demo_dataset()
    ds_alex.name = "Alexandria Custom Blow-Mold Line"
    ds_alex.presses[0].hourly_operating_cost = 999.0

    save_alex = client_alex.post(
        "/api/workspaces",
        json={
            "workspace_id": "default",
            "name": ds_alex.name,
            "dataset": ds_alex.model_dump(mode="json"),
            "config": default_config().model_dump(mode="json"),
        },
    )
    assert save_alex.status_code == 200

    save_alex_custom = client_alex.post(
        "/api/workspaces",
        json={
            "workspace_id": "alex-exp-1",
            "name": "Alexandria Expansion",
            "dataset": ds_alex.model_dump(mode="json"),
            "config": default_config().model_dump(mode="json"),
        },
    )
    assert save_alex_custom.status_code == 200

    # Riyadh MUST NOT see Alexandria's edits or custom workspace
    riyadh_list = client_riyadh.get("/api/workspaces").json()["workspaces"]
    assert [w["workspace_id"] for w in riyadh_list] == ["default"]

    riyadh_default = client_riyadh.get("/api/workspaces/default").json()
    assert riyadh_default["name"] != "Alexandria Custom Blow-Mold Line"
    assert riyadh_default["dataset"]["presses"][0]["hourly_operating_cost"] != 999.0
    assert client_riyadh.get("/api/workspaces/alex-exp-1").status_code == 404

    # Riyadh edits its own workspace
    ds_riyadh = demo_dataset()
    ds_riyadh.name = "Riyadh Export Plant"
    client_riyadh.post(
        "/api/workspaces",
        json={
            "workspace_id": "default",
            "name": ds_riyadh.name,
            "dataset": ds_riyadh.model_dump(mode="json"),
            "config": default_config().model_dump(mode="json"),
        },
    )

    # Alexandria triggers one-click sandbox reset -> ONLY Alexandria is reset
    reset_res = client_alex.post("/api/sandbox/reset")
    assert reset_res.status_code == 200
    assert reset_res.json()["reset"] is True

    alex_after = client_alex.get("/api/workspaces").json()["workspaces"]
    assert [w["workspace_id"] for w in alex_after] == ["default"]
    assert client_alex.get("/api/workspaces/default").json()["dataset"]["presses"][0]["hourly_operating_cost"] != 999.0

    # Riyadh's edits remain completely untouched
    assert client_riyadh.get("/api/workspaces/default").json()["name"] == "Riyadh Export Plant"


def test_copilot_hourly_quota_shield_falls_back_to_deterministic_offline(isolated_env, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key-for-quota-test")
    monkeypatch.setenv("OFFLINE_MODE", "false")
    monkeypatch.setenv("COPILOT_MAX_LIVE_CALLS_PER_HOUR", "2")

    client = TestClient(app)
    login = client.post("/api/auth/login", json={"passcode": "DIOS-2026"})
    assert login.status_code == 200

    ds = demo_dataset()
    cfg = default_config()

    def _fake_gemini_call(prompt, dataset, current_config, current_result, language):
        return CopilotResult(
            reply="Mock live Gemini response",
            action="run_scenario_simulation",
            tool_calls_executed=["run_scenario_simulation"],
            config=current_config,
            result=None,
            timing=CopilotTiming(gemini_ms=10, solver_ms=0, total_ms=10),
            source="gemini",
        )

    with patch("core.copilot._call_gemini_composable_copilot", side_effect=_fake_gemini_call) as mock_gemini:
        # Calls 1 and 2 hit live Gemini
        for _ in range(2):
            r = client.post(
                "/api/copilot/ask",
                json={
                    "prompt": "What if P-500T breaks down for 12 hours?",
                    "dataset": ds.model_dump(mode="json"),
                    "config": cfg.model_dump(mode="json"),
                    "language": "en",
                },
            )
            assert r.status_code == 200
            assert r.json()["source"] == "gemini"
            assert r.json()["quota_limited"] is False

        assert mock_gemini.call_count == 2

        # Call 3 exceeds hourly cap (2/hr) -> automatically falls back to deterministic offline CP-SAT
        r3 = client.post(
            "/api/copilot/ask",
            json={
                "prompt": "What if P-500T breaks down for 12 hours?",
                "dataset": ds.model_dump(mode="json"),
                "config": cfg.model_dump(mode="json"),
                "language": "en",
            },
        )
        assert r3.status_code == 200
        data3 = r3.json()
        assert data3["source"] == "offline_fallback"
        assert data3["quota_limited"] is True
        assert "quota" in data3["reply"].lower()
        assert data3["result"] is not None
        assert data3["result"]["audit"]["all_hard_constraints_passed"] is True
        # Live Gemini was NOT called a 3rd time
        assert mock_gemini.call_count == 2
