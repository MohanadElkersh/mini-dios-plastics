"""Tests for Phase 3 Unlimited Composable Operations Copilot (Gemini 3-tool calling + Offline Fallback)."""
from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.routes import set_audit_store
from core.audit import AuditStore
from core.copilot import DEFAULT_GEMINI_MODEL
from core.ontology import SolverConfig
from main import app


@pytest.fixture()
def client(tmp_path):
    store = AuditStore(tmp_path / "copilot_plastics_audit.db")
    set_audit_store(store)
    return TestClient(app)


def test_copilot_gemini_composable_simulate_tool_uses_real_cpsat(client: TestClient, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")
    monkeypatch.setenv("OFFLINE_MODE", "false")
    monkeypatch.delenv("GEMINI_MODEL", raising=False)

    calls: list[dict] = []

    def fake_generate_content(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return SimpleNamespace(
                function_calls=[
                    SimpleNamespace(
                        name="simulate_plant_scenario",
                        args={
                            "machine_breakdowns": [{"machine_id": "P-500T", "start_hr": 48, "duration_hrs": 18}],
                            "resin_shortages": [{"resin_code": "HDPE", "available_pct_reduction": 30, "virgin_price_spike_pct": 15}],
                            "allow_regrind_override_pct": 30,
                        },
                    )
                ],
                candidates=[SimpleNamespace(content=SimpleNamespace(role="model", parts=[]))],
                text="",
            )
        # Turn 2: confirm real CP-SAT numbers are passed back to Gemini
        return SimpleNamespace(
            function_calls=[],
            text="Simulated P-500T 18h breakdown + 30% HDPE cut via CP-SAT with 6/6 hard constraints satisfied.",
        )

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = fake_generate_content

    with patch("google.genai.Client", return_value=mock_client) as mock_cls:
        resp = client.post(
            "/api/copilot/ask",
            json={
                "prompt": "Press 500T breaks down 18h Tuesday and HDPE supply drops 30% with regrind boost",
                "config": SolverConfig().model_dump(mode="json"),
                "language": "en",
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    # Verify 15000ms HttpOptions timeout was passed to genai.Client
    _, cls_kwargs = mock_cls.call_args
    assert cls_kwargs["api_key"] == "fake-gemini-key"
    assert cls_kwargs["http_options"].timeout == 15000
    # Verify model & low thinking config
    assert calls[0]["model"] == DEFAULT_GEMINI_MODEL
    assert calls[0]["config"].thinking_config.thinking_level.value.lower() == "low"

    assert data["source"] == "gemini"
    assert data["tool_calls_executed"] == ["simulate_plant_scenario"]
    assert data["result"]["audit"]["all_hard_constraints_passed"] is True
    assert len(data["config"]["scenarios"]["machine_breakdowns"]) == 1
    assert data["config"]["scenarios"]["machine_breakdowns"][0]["machine_id"] == "P-500T"
    assert data["config"]["scenarios"]["resin_shortages"][0]["resin_code"] == "HDPE"


def test_copilot_gemini_zero_llm_math_guard_blocks_ungrounded_text(client: TestClient, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")
    monkeypatch.setenv("OFFLINE_MODE", "false")

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = SimpleNamespace(
        function_calls=[],
        text="I guess scrap will be 99999 kg.",
    )

    with patch("google.genai.Client", return_value=mock_client):
        resp = client.post(
            "/api/copilot/ask",
            json={"prompt": "Press 500T breaks down 18h on Tuesday", "language": "en"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "offline_fallback"
    assert "99999" not in data["reply"]
    assert data["result"]["audit"]["all_hard_constraints_passed"] is True


def test_copilot_offline_handles_all_5_starter_scenarios_fast_en_and_ar(client: TestClient, monkeypatch):
    monkeypatch.setenv("OFFLINE_MODE", "true")

    prompts = [
        ("Press 500T breaks down 18h on Tuesday", "simulate_plant_scenario", "en"),
        ("HDPE supply cut 35% + boost regrind", "simulate_plant_scenario", "en"),
        ("Add urgent 40k White Cap export order due Thu", "simulate_plant_scenario", "en"),
        ("Compare Min-Scrap vs. Max-OTIF", "compare_two_strategies", "en"),
        ("Why is Mold M-04 a bottleneck?", "inspect_bottleneck", "en"),
        ("عطل ماكينة P-500T لمدة 18 ساعة يوم الثلاثاء مع نقص HDPE 30%", "simulate_plant_scenario", "ar"),
    ]

    for prompt, expected_action, lang in prompts:
        t0 = time.perf_counter()
        resp = client.post("/api/copilot/ask", json={"prompt": prompt, "language": lang})
        elapsed = time.perf_counter() - t0
        assert resp.status_code == 200
        assert elapsed < 10.0, f"Prompt '{prompt}' took {elapsed:.2f}s (>10s limit)"
        data = resp.json()
        assert data["source"] == "offline_fallback"
        assert data["action"] == expected_action
        assert data["result"] is not None
        if expected_action == "compare_two_strategies":
            assert data["comparison"] is not None
            assert len(data["comparison"]["rows"]) >= 6
        if expected_action == "inspect_bottleneck":
            assert data["bottleneck"] is not None
            assert data["bottleneck"]["target_id"] == "M-04"


def test_copilot_risk_radar_mitigations_return_unified_bundle_and_drop_risks(client: TestClient, monkeypatch):
    monkeypatch.setenv("OFFLINE_MODE", "true")

    # 1. Baseline solve to capture starting Risk Radar & Workforce KPIs
    solve_resp = client.post("/api/solve", json={"config": SolverConfig().model_dump(mode="json")})
    assert solve_resp.status_code == 200
    base_res = solve_resp.json()
    base_risk = base_res["risk_radar"]
    base_wf = base_res["workforce"]["optimized"]["kpis"]

    assert base_risk["overall_risk_score"] >= 90
    assert base_risk["export_at_risk_count"] >= 7
    assert base_wf["understaffed_slots"] >= 24
    assert base_wf["coverage_pct"] < 80.0

    # Find the Understaffed Shift Slots alert and Tight Export Cut-Off Buffer alert prompts
    wf_alert = next(a for a in base_risk["alerts"] if a["alert_id"] == "risk-wf-understaffed")
    exp_alert = next(a for a in base_risk["alerts"] if a["alert_id"].startswith("risk-slack-"))

    # 2. Simulate Workforce Understaffed Shift Slots mitigation via Copilot
    wf_resp = client.post(
        "/api/copilot/ask",
        json={
            "prompt": wf_alert["suggested_prompt_en"],
            "config": SolverConfig().model_dump(mode="json"),
            "current_result": base_res,
            "language": "en",
        },
    )
    assert wf_resp.status_code == 200
    wf_bundle = wf_resp.json()
    assert wf_bundle["action"] == "simulate_plant_scenario"
    assert wf_bundle["plant_state"] is not None
    assert wf_bundle["production_result"] is not None
    assert wf_bundle["workforce_result"] is not None
    assert wf_bundle["risk_radar"] is not None
    assert wf_bundle["weights"] is not None
    assert wf_bundle["toggles"] is not None

    # Relief workers added and understaffed slots eliminated (24 -> 0, 79.5% -> 100.0%)
    assert len(wf_bundle["plant_state"]["workers"]) > 28
    assert wf_bundle["workforce_result"]["optimized"]["kpis"]["understaffed_slots"] == 0
    assert wf_bundle["workforce_result"]["optimized"]["kpis"]["coverage_pct"] == 100.0
    assert wf_bundle["risk_radar"]["overall_risk_score"] < base_risk["overall_risk_score"]

    # 3. Simulate Export Cut-Off Buffer mitigation on top of the applied workforce state
    exp_resp = client.post(
        "/api/copilot/ask",
        json={
            "prompt": exp_alert["suggested_prompt_en"],
            "dataset": wf_bundle["plant_state"],
            "config": wf_bundle["config"],
            "current_result": wf_bundle["production_result"],
            "language": "en",
        },
    )
    assert exp_resp.status_code == 200
    exp_bundle = exp_resp.json()
    assert exp_bundle["action"] == "simulate_plant_scenario"
    assert exp_bundle["risk_radar"]["export_at_risk_count"] == 0
    assert exp_bundle["workforce_result"]["optimized"]["kpis"]["understaffed_slots"] == 0
    assert exp_bundle["risk_radar"]["critical_count"] == 0
    assert exp_bundle["risk_radar"]["elevated_count"] < base_risk["elevated_count"]
    assert exp_bundle["risk_radar"]["overall_risk_score"] <= 35
    assert exp_bundle["risk_radar"]["overall_risk_score"] < wf_bundle["risk_radar"]["overall_risk_score"]

