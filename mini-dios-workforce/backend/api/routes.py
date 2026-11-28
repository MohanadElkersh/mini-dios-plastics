"""REST endpoints for Mini-DIOS Plastics (auth gate, validation, CP-SAT solve, 4-tab Excel bridge, composable Copilot, audit log, isolated sandboxes)."""
from __future__ import annotations

import asyncio
import os
from typing import Optional

import ortools
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from core.audit import AuditStore
from core.auth import (
    AuthSession,
    check_login_rate_limit,
    clear_login_failures,
    clear_session_cookie,
    consume_copilot_live_quota,
    get_client_ip,
    get_optional_session,
    is_admin_label,
    is_auth_enabled,
    is_instant_demo_enabled,
    new_session_id,
    record_login_failure,
    require_admin_session,
    require_auth_session,
    set_session_cookie,
    sign_session_token,
    verify_passcode,
)
from core.copilot import CopilotResult, run_plastics_copilot
from core.ctp import CTPQuoteRequest, CTPQuoteResult, evaluate_ctp_rush_order
from core.dispatch import (
    WhatsAppDispatchRequest,
    WhatsAppDispatchResponse,
    format_whatsapp_shift_dispatch,
)
from core.neon_services import (
    fetch_neon_auth_jwks,
    get_neon_function_url,
    get_neon_realtime_config_status,
    invoke_neon_function,
    probe_neon_ai_gateway,
)
from core.disruptions import apply_plant_scenarios
from core.excel_io import (
    build_template_workbook,
    export_brief_workbook,
    export_integration_erp_payload,
    export_integration_schedule_csv,
    export_integration_schedule_workbook,
    parse_workbook_bytes,
)
from core.backtest import (
    BacktestReplayReport,
    build_backtest_template_csv,
    build_backtest_template_xlsx,
    parse_backtest_upload,
    run_historical_backtest_replay,
)
from core.onboarding import (
    GuidedSetupRequest,
    ReadinessChecklistItem,
    build_guided_plant_workspace,
)
from core.financials import compute_financial_report
from core.ontology import (
    Currency,
    FinancialReport,
    PlantDataset,
    ProductionOrder,
    RiskRadarReport,
    SolveResult,
    SolverConfig,
    ValidationReport,
    WorkforceCallout,
    WorkforceResult,
    validate_plant_data,
)
from core.risk_radar import compute_risk_radar
from core.seed import default_config, demo_dataset
from core.solver import (
    DatasetValidationError,
    EngineMode,
    EngineOverrideInput,
    bind_sandbox_engine_context,
    get_effective_engine,
    get_engine_mode_metadata,
    get_env_default_engine,
    is_uem_engine_enabled,
    set_sandbox_engine_override,
    solve_plant_schedule,
)
from core.workforce_solver import solve_workforce, solve_workforce_with_callouts

router = APIRouter(prefix="/api", tags=["Mini-DIOS Plastics"])

_audit_store: Optional[AuditStore] = None


def get_audit_store() -> AuditStore:
    global _audit_store
    if _audit_store is None:
        _audit_store = AuditStore()
    return _audit_store


def set_audit_store(store: AuditStore) -> None:
    """Allow tests to inject an isolated SQLite audit store."""
    global _audit_store
    _audit_store = store


# --------------------------------------------------------------------------------------------
# Request / Response Models
# --------------------------------------------------------------------------------------------
class AuthLoginRequest(BaseModel):
    passcode: str = ""
    instant_demo: bool = False


class AuthStatusResponse(BaseModel):
    auth_enabled: bool
    authenticated: bool
    client_label: Optional[str] = None
    session_id: Optional[str] = None
    instant_demo_enabled: bool = False
    is_admin: bool = False
    active_engine: EngineMode = "legacy_cpsat_v1"
    env_default_engine: EngineMode = "legacy_cpsat_v1"
    is_engine_override: bool = False


class DemoDataResponse(BaseModel):
    dataset: PlantDataset
    default_config: SolverConfig


class ValidateResponse(BaseModel):
    dataset: PlantDataset
    report: ValidationReport


class SolveRequest(BaseModel):
    dataset: Optional[PlantDataset] = None
    config: SolverConfig = Field(default_factory=SolverConfig)


class ExportBriefRequest(BaseModel):
    run_id: Optional[str] = None
    result: Optional[SolveResult] = None
    dataset: Optional[PlantDataset] = None
    config: Optional[SolverConfig] = None
    currency: Optional[Currency] = None


class CopilotAskRequest(BaseModel):
    prompt: str
    dataset: Optional[PlantDataset] = None
    config: Optional[SolverConfig] = None
    current_result: Optional[SolveResult] = None
    language: str = "en"


class WorkforceSolveRequest(BaseModel):
    dataset: Optional[PlantDataset] = None
    config: SolverConfig = Field(default_factory=SolverConfig)
    result: Optional[SolveResult] = None
    worker_callouts: list[WorkforceCallout] = Field(default_factory=list)


class WorkforceSolveResponse(BaseModel):
    workforce: Optional[WorkforceResult] = None
    financials: FinancialReport
    risk_radar: Optional[RiskRadarReport] = None


class WorkspacePayload(BaseModel):
    workspace_id: str
    name: str
    dataset: PlantDataset
    config: Optional[SolverConfig] = None
    record_checkpoint: bool = False
    result: Optional[SolveResult] = None


class CheckpointCreateRequest(BaseModel):
    trigger_source: str = "manual"
    title_en: str = "Saved Decision Checkpoint"
    title_ar: str = "حفظ نقطة قرار مرجعية"
    dataset: Optional[PlantDataset] = None
    config: Optional[SolverConfig] = None
    result: Optional[SolveResult] = None


class CheckpointRestoreResponse(BaseModel):
    restored: bool = True
    storage_backend: str
    active_engine: EngineMode = "legacy_cpsat_v1"
    checkpoint: dict
    dataset: PlantDataset
    config: SolverConfig
    result: SolveResult
    workforce: Optional[WorkforceResult] = None
    financials: FinancialReport
    risk_radar: Optional[RiskRadarReport] = None
    validation: ValidationReport


class CTPCommitRequest(BaseModel):
    candidate_order: ProductionOrder
    dataset: Optional[PlantDataset] = None
    config: Optional[SolverConfig] = None
    workspace_id: str = "default"


class CTPCommitResponse(BaseModel):
    committed: bool = True
    order_id: str
    active_engine: EngineMode = "legacy_cpsat_v1"
    checkpoint: dict
    dataset: PlantDataset
    config: SolverConfig
    result: SolveResult
    workforce: Optional[WorkforceResult] = None
    financials: FinancialReport
    risk_radar: Optional[RiskRadarReport] = None
    validation: ValidationReport


class AdminEngineModeRequest(BaseModel):
    engine: EngineOverrideInput = Field(
        description="Target optimization engine: 'uem_di_v1', 'legacy_cpsat_v1', or 'default'"
    )
    dataset: Optional[PlantDataset] = None
    config: Optional[SolverConfig] = None
    workspace_id: str = "default"


class AdminEngineSwitchDelta(BaseModel):
    prev_engine: EngineMode
    new_engine: EngineMode
    solve_time_ms: int
    weekly_savings: float
    otif_pct: float


class AdminEngineModeSwitchResponse(BaseModel):
    active_engine: EngineMode
    env_default_engine: EngineMode
    is_override: bool
    engine_override: Optional[EngineMode] = None
    di_standards: list[str]
    switch_delta: AdminEngineSwitchDelta
    dataset: PlantDataset
    config: SolverConfig
    result: SolveResult
    workforce: Optional[WorkforceResult] = None
    financials: FinancialReport
    risk_radar: Optional[RiskRadarReport] = None
    validation: ValidationReport


# --------------------------------------------------------------------------------------------
# Public Health & Auth Endpoints
# --------------------------------------------------------------------------------------------
@router.get("/health")
def health(request: Request) -> dict:
    store = get_audit_store()
    sess = get_optional_session(request)
    sid = sess.session_id if sess else "local"
    eff_eng = get_effective_engine(sid)
    uem_on = eff_eng == "uem_di_v1"
    return {
        "status": "ok",
        "service": "mini-dios-plastics",
        "ortools_version": getattr(ortools, "__version__", "unknown"),
        "optimization_engine": eff_eng,
        "use_uem_engine": uem_on,
        "auth_enabled": is_auth_enabled(),
        "storage_backend": store.storage_backend,
        "neon_branch": os.environ.get("NEON_BRANCH") or None,
        "neon_branch_id": os.environ.get("NEON_BRANCH_ID") or None,
        "neon_function_hello_url": get_neon_function_url("hello"),
    }


@router.get("/di/blueprint")
def get_di_blueprint_endpoint(
    request: Request,
    format: str = Query(
        default="json",
        description="Blueprint export format: 'json', 'bpmn_xml' (OMG BPMN 2.0 XML), or 'dmn_xml' (OMG DMN 1.3 XML)",
    ),
    include_solved_causal: bool = Query(
        default=False,
        description="If true, runs a deterministic solve to populate live baseline vs. optimized causal deltas",
    ),
):
    """Inspect the 5-Layer Decision Intelligence & 6-Primitive UEMGraph Blueprint (JSON, BPMN 2.0 XML, or DMN 1.3 XML)."""
    from adapters.plastics import (
        build_plastics_blueprint,
        build_plastics_bpmn_template,
        build_plastics_dmn_registry,
    )

    fmt = format.strip().lower()
    if fmt == "bpmn_xml":
        xml_str = build_plastics_bpmn_template().to_bpmn_xml()
        return Response(content=xml_str, media_type="application/xml")
    if fmt == "dmn_xml":
        xml_str = build_plastics_dmn_registry().to_dmn_xml()
        return Response(content=xml_str, media_type="application/xml")
    if fmt != "json":
        raise HTTPException(
            status_code=400,
            detail="Unsupported format. Use 'json', 'bpmn_xml', or 'dmn_xml'.",
        )

    sess = get_optional_session(request)
    sid = sess.session_id if sess else "local"
    ds = demo_dataset()
    cfg = default_config()
    with bind_sandbox_engine_context(sid):
        solved_res = solve_plant_schedule(ds, cfg, sandbox_id=sid) if include_solved_causal else None
    bp = build_plastics_blueprint(dataset=ds, config=cfg, result=solved_res)
    bp["optimization_engine"] = get_effective_engine(sid)
    return bp


@router.get("/admin/engine-mode")
def get_admin_engine_mode_endpoint(
    session: AuthSession = Depends(require_admin_session),
) -> dict:
    """Inspect the calling admin sandbox's active optimization engine, override state, and 5-layer DI standards."""
    meta = get_engine_mode_metadata(session.session_id)
    return {
        "active_engine": meta["active_engine"],
        "env_default_engine": meta["env_default_engine"],
        "is_override": meta["is_override"],
        "engine_override": meta["engine_override"],
        "sandbox_id": meta["sandbox_id"],
        "di_standards": meta["di_standards"],
    }


@router.post("/admin/engine-mode", response_model=AdminEngineModeSwitchResponse)
def set_admin_engine_mode_endpoint(
    payload: AdminEngineModeRequest,
    session: AuthSession = Depends(require_admin_session),
):
    """Switch the calling admin sandbox's optimization engine live and return an immediately solved unified bundle."""
    sid = session.session_id
    prev_engine = get_effective_engine(sid)
    set_sandbox_engine_override(sid, payload.engine)
    meta = get_engine_mode_metadata(sid)
    new_engine: EngineMode = meta["active_engine"]

    store = get_audit_store()
    ws = store.get_workspace(payload.workspace_id, session_id=sid, access_code=session.client_label)
    ds = payload.dataset or (
        PlantDataset.model_validate(ws["dataset"]) if ws and ws.get("dataset") else demo_dataset()
    )
    cfg = payload.config or (
        SolverConfig.model_validate(ws["config"]) if ws and ws.get("config") else default_config()
    )

    try:
        with bind_sandbox_engine_context(sid):
            result = solve_plant_schedule(ds, cfg, sandbox_id=sid)
    except DatasetValidationError as exc:
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc), "validation": exc.report.model_dump(mode="json")},
        )

    store.save_run(result, dataset=ds, session_id=sid)

    return AdminEngineModeSwitchResponse(
        active_engine=new_engine,
        env_default_engine=meta["env_default_engine"],
        is_override=meta["is_override"],
        engine_override=meta["engine_override"],
        di_standards=meta["di_standards"],
        switch_delta=AdminEngineSwitchDelta(
            prev_engine=prev_engine,
            new_engine=new_engine,
            solve_time_ms=result.solve_time_ms,
            weekly_savings=result.financials.total_weekly_savings,
            otif_pct=result.optimized.kpis.otif_pct,
        ),
        dataset=ds,
        config=cfg,
        result=result,
        workforce=result.workforce,
        financials=result.financials,
        risk_radar=result.risk_radar,
        validation=result.validation,
    )


@router.get("/neon/status")
def neon_status_endpoint() -> dict:
    """End-to-end diagnostic status of all 5 wired Neon services from the Python FastAPI backend."""
    store = get_audit_store()
    pg_status = store.probe_database()
    auth_status = fetch_neon_auth_jwks()
    fn_status = invoke_neon_function("hello")
    ai_gw_status = probe_neon_ai_gateway()
    rt_status = get_neon_realtime_config_status()
    return {
        "branch": os.environ.get("NEON_BRANCH") or "production",
        "branch_id": os.environ.get("NEON_BRANCH_ID") or None,
        "services": {
            "postgres": pg_status,
            "auth": auth_status,
            "functions": fn_status,
            "ai_gateway": ai_gw_status,
            "realtime": rt_status,
        },
    }


@router.get("/neon/function/{slug}")
def neon_invoke_function_endpoint(slug: str = "hello") -> dict:
    """Invoke a deployed Neon Function by slug (e.g., `hello`) and return its live response."""
    return invoke_neon_function(slug)


@router.get("/auth/me", response_model=AuthStatusResponse)
def auth_me(request: Request) -> AuthStatusResponse:
    auth_on = is_auth_enabled()
    instant_on = is_instant_demo_enabled()
    if not auth_on:
        meta = get_engine_mode_metadata("local")
        return AuthStatusResponse(
            auth_enabled=False,
            authenticated=True,
            client_label="Local Plant",
            session_id="local",
            instant_demo_enabled=instant_on,
            is_admin=True,
            active_engine=meta["active_engine"],
            env_default_engine=meta["env_default_engine"],
            is_engine_override=meta["is_override"],
        )
    sess = get_optional_session(request)
    if sess is None:
        meta = get_engine_mode_metadata("local")
        return AuthStatusResponse(
            auth_enabled=True,
            authenticated=False,
            client_label=None,
            session_id=None,
            instant_demo_enabled=instant_on,
            is_admin=False,
            active_engine=meta["active_engine"],
            env_default_engine=meta["env_default_engine"],
            is_engine_override=meta["is_override"],
        )
    meta = get_engine_mode_metadata(sess.session_id)
    return AuthStatusResponse(
        auth_enabled=True,
        authenticated=True,
        client_label=sess.client_label,
        session_id=sess.session_id,
        instant_demo_enabled=instant_on,
        is_admin=sess.is_admin or is_admin_label(sess.client_label, True),
        active_engine=meta["active_engine"],
        env_default_engine=meta["env_default_engine"],
        is_engine_override=meta["is_override"],
    )


@router.post("/auth/login", response_model=AuthStatusResponse)
def auth_login(payload: AuthLoginRequest, request: Request, response: Response) -> AuthStatusResponse:
    auth_on = is_auth_enabled()
    instant_on = is_instant_demo_enabled()

    if not auth_on:
        meta = get_engine_mode_metadata("local")
        return AuthStatusResponse(
            auth_enabled=False,
            authenticated=True,
            client_label="Local Plant",
            session_id="local",
            instant_demo_enabled=instant_on,
            is_admin=True,
            active_engine=meta["active_engine"],
            env_default_engine=meta["env_default_engine"],
            is_engine_override=meta["is_override"],
        )

    client_ip = get_client_ip(request)
    check_login_rate_limit(client_ip)

    client_label: Optional[str] = None
    if payload.instant_demo:
        if not instant_on:
            raise HTTPException(status_code=403, detail="Instant guided demo is disabled. Please enter your access code.")
        client_label = "Guided Demo"
    else:
        client_label = verify_passcode(payload.passcode)
        if client_label is None:
            record_login_failure(client_ip)
            raise HTTPException(status_code=401, detail="Invalid access code or password.")

    clear_login_failures(client_ip)
    sid = new_session_id()
    token = sign_session_token(sid, client_label)
    set_session_cookie(response, request, token)

    # Pre-seed an isolated default workspace for this session
    get_audit_store().list_workspaces(session_id=sid)
    meta = get_engine_mode_metadata(sid)

    return AuthStatusResponse(
        auth_enabled=True,
        authenticated=True,
        client_label=client_label,
        session_id=sid,
        instant_demo_enabled=instant_on,
        is_admin=is_admin_label(client_label, True),
        active_engine=meta["active_engine"],
        env_default_engine=meta["env_default_engine"],
        is_engine_override=meta["is_override"],
    )


@router.post("/auth/logout")
def auth_logout(response: Response) -> dict:
    clear_session_cookie(response)
    return {"authenticated": False, "logged_out": True}


# --------------------------------------------------------------------------------------------
# Protected Operational Endpoints
# --------------------------------------------------------------------------------------------
@router.post("/sandbox/reset")
def sandbox_reset_endpoint(session: AuthSession = Depends(require_auth_session)) -> dict:
    """Reset ONLY the calling session's workspaces to the fresh demo plant."""
    return get_audit_store().reset_session_sandbox(session_id=session.session_id)


@router.get("/demo-data", response_model=DemoDataResponse)
def get_demo_data(session: AuthSession = Depends(require_auth_session)) -> DemoDataResponse:
    return DemoDataResponse(dataset=demo_dataset(), default_config=default_config())


@router.get("/template.xlsx")
def download_template(
    sample: bool = Query(default=True, description="Pre-fill with 6-press Delta & Riyadh Plastics demo data"),
    session: AuthSession = Depends(require_auth_session),
) -> Response:
    xlsx_bytes = build_template_workbook(sample=sample)
    filename = "mini_dios_plastics_template.xlsx" if sample else "mini_dios_plastics_blank_template.xlsx"
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/validate", response_model=ValidateResponse)
async def validate_endpoint(
    request: Request,
    session: AuthSession = Depends(require_auth_session),
) -> ValidateResponse:
    """Accepts JSON (`{dataset, config?}` or raw `PlantDataset`) OR `multipart/form-data` `.xlsx` upload."""
    content_type = (request.headers.get("content-type") or "").lower()

    if "multipart/form-data" in content_type:
        form = await request.form()
        upload = form.get("file")
        if upload is None or not hasattr(upload, "read"):
            raise HTTPException(status_code=400, detail="Expected multipart field 'file' containing an .xlsx workbook.")
        raw_bytes = await upload.read()
        filename = getattr(upload, "filename", "uploaded_plastics_plant.xlsx") or "uploaded_plastics_plant.xlsx"
        config_raw = form.get("config")
        config = SolverConfig.model_validate_json(str(config_raw)) if config_raw else default_config()
        dataset, parse_issues = parse_workbook_bytes(raw_bytes, dataset_name=filename)
        report = validate_plant_data(dataset, config)
        if parse_issues:
            merged_issues = sorted(
                [*parse_issues, *report.issues],
                key=lambda i: ({"error": 0, "warning": 1, "info": 2}[i.severity], i.code),
            )
            err_n = sum(1 for i in merged_issues if i.severity == "error")
            warn_n = sum(1 for i in merged_issues if i.severity == "warning")
            info_n = sum(1 for i in merged_issues if i.severity == "info")
            report = report.model_copy(
                update={
                    "ready": err_n == 0,
                    "error_count": err_n,
                    "warning_count": warn_n,
                    "info_count": info_n,
                    "issues": merged_issues,
                }
            )
        return ValidateResponse(dataset=dataset, report=report)

    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {exc}") from exc

    if isinstance(body, dict) and "dataset" in body:
        dataset = PlantDataset.model_validate(body["dataset"])
        config = SolverConfig.model_validate(body["config"]) if body.get("config") else default_config()
    else:
        dataset = PlantDataset.model_validate(body)
        config = default_config()

    report = validate_plant_data(dataset, config)
    return ValidateResponse(dataset=dataset, report=report)


@router.post("/solve", response_model=SolveResult)
@router.post("/optimize", response_model=SolveResult)
def solve_endpoint(
    payload: SolveRequest,
    session: AuthSession = Depends(require_auth_session),
):
    dataset = payload.dataset or demo_dataset()
    try:
        with bind_sandbox_engine_context(session.session_id):
            result = solve_plant_schedule(dataset, payload.config, sandbox_id=session.session_id)
    except DatasetValidationError as exc:
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc), "validation": exc.report.model_dump(mode="json")},
        )
    get_audit_store().save_run(result, dataset=dataset, session_id=session.session_id)
    return result


@router.post("/workforce/solve", response_model=WorkforceSolveResponse)
def workforce_solve_endpoint(
    payload: WorkforceSolveRequest,
    session: AuthSession = Depends(require_auth_session),
):
    """Quick labor-only re-solve against the already-solved Press Gantt (no press re-solve)."""
    dataset = payload.dataset or demo_dataset()
    cfg = payload.config
    result = payload.result
    try:
        if result is None:
            with bind_sandbox_engine_context(session.session_id):
                result = solve_plant_schedule(dataset, cfg, sandbox_id=session.session_id)
    except DatasetValidationError as exc:
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc), "validation": exc.report.model_dump(mode="json")},
        )
    if not dataset.workers:
        raise HTTPException(status_code=422, detail="The active plant workspace has no workers defined.")
    plan = result.optimized
    if payload.worker_callouts:
        wf = solve_workforce_with_callouts(dataset, cfg, plan, payload.worker_callouts)
    else:
        wf = solve_workforce(dataset, cfg, plan)
    eff_ds = apply_plant_scenarios(dataset, cfg).dataset
    fin = compute_financial_report(eff_ds, cfg, result.baseline, result.optimized, wf)
    radar = compute_risk_radar(eff_ds, cfg, result.optimized, wf)
    return WorkforceSolveResponse(workforce=wf, financials=fin, risk_radar=radar)


@router.post("/copilot/ask", response_model=CopilotResult)
async def copilot_ask_endpoint(
    payload: CopilotAskRequest,
    session: AuthSession = Depends(require_auth_session),
) -> CopilotResult:
    """Unlimited Composable Operations Copilot executed inside `asyncio.to_thread` with hourly Gemini quota shield."""
    curr_cfg = payload.config or default_config()
    eff_dataset = payload.dataset or demo_dataset()

    # Check hourly live Gemini quota shield before calling Gemini
    api_key_present = bool(os.environ.get("GEMINI_API_KEY", "").strip())
    offline_mode = os.environ.get("OFFLINE_MODE", "false").lower() in ("true", "1", "yes")
    force_offline = False
    quota_limited = False
    if api_key_present and not offline_mode:
        allowed, used, limit = consume_copilot_live_quota(session.session_id)
        if not allowed:
            force_offline = True
            quota_limited = True
            print(
                f"[Copilot] Quota shield active for session={session.session_id} ({used}/{limit}/hr); falling back to deterministic offline CP-SAT.",
                flush=True,
            )

    print(f"[Copilot] Request received: prompt='{payload.prompt}'", flush=True)
    with bind_sandbox_engine_context(session.session_id):
        copilot_res = await asyncio.to_thread(
            run_plastics_copilot,
            payload.prompt,
            eff_dataset,
            curr_cfg,
            payload.current_result,
            payload.language,
            force_offline,
            quota_limited,
        )
    if copilot_res.result is not None:
        saved_ds = copilot_res.dataset or copilot_res.plant_state or eff_dataset
        await asyncio.to_thread(
            get_audit_store().save_run, copilot_res.result, saved_ds, session.session_id
        )
    print(
        f"[Copilot] Completed action='{copilot_res.action}' source='{copilot_res.source}' "
        f"total={copilot_res.timing.total_ms}ms (gemini={copilot_res.timing.gemini_ms}ms, solver={copilot_res.timing.solver_ms}ms)",
        flush=True,
    )
    return copilot_res


@router.post("/export-dataset.xlsx")
def export_dataset_excel(
    dataset: PlantDataset,
    session: AuthSession = Depends(require_auth_session),
) -> Response:
    """Export the live edited `PlantDataset` from the Data & Parameters Studio as a 4-tab `.xlsx`."""
    xlsx_bytes = build_template_workbook(sample=False, dataset=dataset)
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="mini_dios_plastics_plant_data.xlsx"'},
    )


@router.post("/export-brief.xlsx")
def export_brief_endpoint(
    payload: ExportBriefRequest,
    session: AuthSession = Depends(require_auth_session),
) -> Response:
    result = payload.result
    if result is None and payload.run_id:
        result = get_audit_store().get_run(payload.run_id, session_id=session.session_id)
        if result is None and payload.dataset is None:
            raise HTTPException(status_code=404, detail=f"Audit run '{payload.run_id}' not found.")
    if result is None and payload.dataset is not None:
        cfg = payload.config or default_config()
        if payload.currency is not None:
            cfg = cfg.model_copy(update={"currency": payload.currency})
        try:
            result = solve_plant_schedule(payload.dataset, cfg)
        except DatasetValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=400, detail="Provide 'run_id', inline 'result', or 'dataset' + 'config'.")

    if payload.config is not None:
        updated_audit = result.audit.model_copy(update={"config": payload.config})
        result = result.model_copy(update={"audit": updated_audit})

    xlsx_bytes = export_brief_workbook(result, currency_override=payload.currency)
    filename = f"mini_dios_plastics_brief_{result.run_id}.xlsx"
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/audit-log")
def list_audit_log(
    limit: int = Query(default=50, ge=1, le=500),
    session: AuthSession = Depends(require_auth_session),
) -> dict:
    return {"runs": get_audit_store().list_runs(limit=limit, session_id=session.session_id)}


@router.get("/audit-log/{run_id}", response_model=SolveResult)
def get_audit_run(
    run_id: str,
    session: AuthSession = Depends(require_auth_session),
) -> SolveResult:
    res = get_audit_store().get_run(run_id, session_id=session.session_id)
    if res is None:
        raise HTTPException(status_code=404, detail=f"Audit run '{run_id}' not found.")
    return res


@router.get("/workspaces")
def list_workspaces_endpoint(session: AuthSession = Depends(require_auth_session)) -> dict:
    """List all saved plant workspaces for the active session."""
    return {"workspaces": get_audit_store().list_workspaces(session_id=session.session_id)}


@router.post("/workspaces")
def save_workspace_endpoint(
    payload: WorkspacePayload,
    session: AuthSession = Depends(require_auth_session),
) -> dict:
    """Save or update a plant workspace in the active session."""
    store = get_audit_store()
    saved = store.save_workspace(
        workspace_id=payload.workspace_id,
        name=payload.name,
        dataset=payload.dataset,
        config=payload.config,
        session_id=session.session_id,
        access_code=session.client_label,
    )
    if payload.record_checkpoint or payload.workspace_id != "default":
        cfg = payload.config or default_config()
        store.save_checkpoint(
            dataset=payload.dataset,
            config=cfg,
            result=payload.result,
            trigger_source="workspace_save",
            title_en=f"Workspace Saved: {payload.name}",
            title_ar=f"حفظ مساحة العمل: {payload.name}",
            session_id=session.session_id,
            access_code=session.client_label,
        )
    return saved


@router.get("/workspaces/{workspace_id}")
def get_workspace_endpoint(
    workspace_id: str,
    session: AuthSession = Depends(require_auth_session),
) -> dict:
    """Retrieve a plant workspace by ID within the active session."""
    ws = get_audit_store().get_workspace(workspace_id, session_id=session.session_id)
    if ws is None:
        raise HTTPException(status_code=404, detail=f"Workspace '{workspace_id}' not found.")
    return ws


@router.delete("/workspaces/{workspace_id}")
def delete_workspace_endpoint(
    workspace_id: str,
    session: AuthSession = Depends(require_auth_session),
) -> dict:
    """Delete a plant workspace by ID (or reset default if ID is default) within the active session."""
    success = get_audit_store().delete_workspace(workspace_id, session_id=session.session_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Workspace '{workspace_id}' not found.")
    return {"deleted": True, "workspace_id": workspace_id}


# --------------------------------------------------------------------------------------------
# v1.3 Feature 1: 1-Month Historical Backtest / Replay Mode ("The Proof Engine")
# --------------------------------------------------------------------------------------------
@router.get("/backtest/template")
def download_backtest_template(
    format: str = Query(default="csv", description="Template format: 'csv' or 'xlsx'"),
    session: AuthSession = Depends(require_auth_session),
) -> Response:
    fmt = (format or "csv").strip().lower()
    if fmt == "xlsx":
        xlsx_bytes = build_backtest_template_xlsx()
        return Response(
            content=xlsx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="mini_dios_30day_backtest_template.xlsx"'},
        )
    csv_bytes = build_backtest_template_csv()
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="mini_dios_30day_backtest_template.csv"'},
    )


@router.post("/backtest/replay", response_model=BacktestReplayReport)
async def backtest_replay_endpoint(
    request: Request,
    session: AuthSession = Depends(require_auth_session),
) -> BacktestReplayReport:
    """Run deterministic CP-SAT replay on an uploaded CSV/Excel press log or built-in sample_30day_log."""
    content_type = (request.headers.get("content-type") or "").lower()
    rows = None
    source_label = "sample_30day_log"
    dataset = demo_dataset()
    config = default_config()

    if "multipart/form-data" in content_type:
        form = await request.form()
        upload = form.get("file")
        if upload is not None and hasattr(upload, "read"):
            raw_bytes = await upload.read()
            filename = getattr(upload, "filename", "backtest_log.csv") or "backtest_log.csv"
            try:
                rows = parse_backtest_upload(raw_bytes, filename=filename)
            except Exception as exc:
                raise HTTPException(status_code=400, detail=f"Invalid historical backtest file: {exc}") from exc
            source_label = filename
        cur_raw = form.get("currency")
        if cur_raw in ("SAR", "EGP"):
            config = config.model_copy(update={"currency": str(cur_raw)})  # type: ignore[arg-type]
        cfg_raw = form.get("config")
        if cfg_raw:
            config = SolverConfig.model_validate_json(str(cfg_raw))
        ds_raw = form.get("dataset")
        if ds_raw:
            dataset = PlantDataset.model_validate_json(str(ds_raw))
    else:
        try:
            body = await request.json()
        except Exception:
            body = {}
        if isinstance(body, dict):
            if body.get("dataset"):
                dataset = PlantDataset.model_validate(body["dataset"])
            if body.get("config"):
                config = SolverConfig.model_validate(body["config"])
            if body.get("currency") in ("SAR", "EGP"):
                config = config.model_copy(update={"currency": body["currency"]})
            if body.get("csv_text"):
                try:
                    rows = parse_backtest_upload(str(body["csv_text"]).encode("utf-8"), "uploaded_log.csv")
                    source_label = str(body.get("source_label") or "uploaded_log.csv")
                except Exception as exc:
                    raise HTTPException(status_code=400, detail=f"Invalid CSV content: {exc}") from exc
            elif body.get("rows") and isinstance(body["rows"], list):
                rows = body["rows"]
                source_label = str(body.get("source_label") or "custom_rows")
            else:
                source_label = str(body.get("mode") or body.get("source_label") or "sample_30day_log")

    with bind_sandbox_engine_context(session.session_id):
        report = await asyncio.to_thread(
            run_historical_backtest_replay,
            dataset,
            config,
            rows,
            source_label,
        )
    await asyncio.to_thread(
        get_audit_store().save_backtest_run,
        report,
        session.session_id,
        session.client_label,
    )
    return report


# --------------------------------------------------------------------------------------------
# v1.3 Feature 2: Guided "Process-First" 5-Step Onboarding Wizard
# --------------------------------------------------------------------------------------------
class GuidedSetupResponse(BaseModel):
    workspace_id: str
    dataset: PlantDataset
    config: SolverConfig
    result: SolveResult
    readiness_checklist: list[ReadinessChecklistItem]


@router.post("/onboarding/generate", response_model=GuidedSetupResponse)
def onboarding_generate_endpoint(
    payload: GuidedSetupRequest,
    session: AuthSession = Depends(require_auth_session),
) -> GuidedSetupResponse:
    """Build and immediately solve a tailored plant workspace from the 5-step Guided Setup interview."""
    ds, cfg, checklist = build_guided_plant_workspace(payload)
    with bind_sandbox_engine_context(session.session_id):
        result = solve_plant_schedule(ds, cfg, sandbox_id=session.session_id)
    ws_id = f"guided-{result.run_id.lower()}"
    store = get_audit_store()
    store.save_workspace(ws_id, ds.name, ds, cfg, session_id=session.session_id)
    store.save_run(result, dataset=ds, session_id=session.session_id)
    return GuidedSetupResponse(
        workspace_id=ws_id,
        dataset=ds,
        config=cfg,
        result=result,
        readiness_checklist=checklist,
    )


# --------------------------------------------------------------------------------------------
# v1.3 Feature 5: Integration-Ready Export API (Excel, CSV & ERP JSON)
# --------------------------------------------------------------------------------------------
def _resolve_active_session_result(
    session_id: str,
    run_id: Optional[str] = None,
    currency: Optional[Currency] = None,
) -> tuple[SolveResult, Optional[PlantDataset]]:
    store = get_audit_store()
    result: Optional[SolveResult] = None
    if run_id:
        result = store.get_run(run_id, session_id=session_id)
    if result is None:
        runs = store.list_runs(limit=1, session_id=session_id)
        if runs:
            result = store.get_run(runs[0]["run_id"], session_id=session_id)

    ws = store.get_workspace("default", session_id=session_id)
    ds = PlantDataset.model_validate(ws["dataset"]) if ws and ws.get("dataset") else demo_dataset()
    cfg = SolverConfig.model_validate(ws["config"]) if ws and ws.get("config") else default_config()
    if currency in ("SAR", "EGP"):
        cfg = cfg.model_copy(update={"currency": currency})

    if result is None:
        result = solve_plant_schedule(ds, cfg)
        store.save_run(result, dataset=ds, session_id=session_id)
    return result, ds


@router.get("/export/schedule.xlsx")
def export_schedule_xlsx_endpoint(
    run_id: Optional[str] = Query(default=None),
    currency: Optional[Currency] = Query(default=None),
    session: AuthSession = Depends(require_auth_session),
) -> Response:
    result, _ = _resolve_active_session_result(session.session_id, run_id=run_id, currency=currency)
    xlsx_bytes = export_integration_schedule_workbook(result, currency_override=currency)
    filename = f"mini_dios_schedule_{result.run_id}.xlsx"
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/schedule.csv")
def export_schedule_csv_endpoint(
    run_id: Optional[str] = Query(default=None),
    currency: Optional[Currency] = Query(default=None),
    session: AuthSession = Depends(require_auth_session),
) -> Response:
    result, _ = _resolve_active_session_result(session.session_id, run_id=run_id, currency=currency)
    csv_bytes = export_integration_schedule_csv(result, currency_override=currency)
    filename = f"mini_dios_schedule_{result.run_id}.csv"
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/erp-payload.json")
def export_erp_payload_endpoint(
    run_id: Optional[str] = Query(default=None),
    currency: Optional[Currency] = Query(default=None),
    session: AuthSession = Depends(require_auth_session),
) -> Response:
    result, ds = _resolve_active_session_result(session.session_id, run_id=run_id, currency=currency)
    payload = export_integration_erp_payload(result, dataset=ds, currency_override=currency)
    filename = f"mini_dios_erp_payload_{result.run_id}.json"
    import json

    return Response(
        content=json.dumps(payload, indent=2).encode("utf-8"),
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# --------------------------------------------------------------------------------------------
# v1.4 Feature 1: Persistent Decision Checkpoints & 1-Click Rollback
# --------------------------------------------------------------------------------------------
@router.get("/checkpoints")
def list_checkpoints_endpoint(
    limit: int = Query(default=25, ge=1, le=100),
    seed_if_empty: bool = Query(default=False),
    session: AuthSession = Depends(require_auth_session),
) -> dict:
    """Return recent decision checkpoints (newest first, capped at 25) with storage diagnostics badge."""
    store = get_audit_store()
    checkpoints = store.list_checkpoints(session_id=session.session_id, limit=limit)
    if not checkpoints and seed_if_empty:
        ws = store.get_workspace("default", session_id=session.session_id, access_code=session.client_label)
        ds = PlantDataset.model_validate(ws["dataset"]) if ws and ws.get("dataset") else demo_dataset()
        cfg = SolverConfig.model_validate(ws["config"]) if ws and ws.get("config") else default_config()
        runs = store.list_runs(limit=1, session_id=session.session_id)
        latest_res = store.get_run(runs[0]["run_id"], session_id=session.session_id) if runs else None
        store.save_checkpoint(
            dataset=ds,
            config=cfg,
            result=latest_res,
            trigger_source="workspace_save",
            title_en=f"Initial Plant Baseline: {ds.name}",
            title_ar=f"خط الأساس الافتراضي للمصنع: {ds.name}",
            session_id=session.session_id,
            access_code=session.client_label,
        )
        checkpoints = store.list_checkpoints(session_id=session.session_id, limit=limit)
    return {
        "storage_backend": store.storage_backend,
        "pool_config": store.pool_config,
        "checkpoints": checkpoints,
    }


@router.post("/checkpoints")
def create_checkpoint_endpoint(
    payload: CheckpointCreateRequest,
    session: AuthSession = Depends(require_auth_session),
) -> dict:
    """Record an immutable decision checkpoint (Copilot apply, manual save, or workspace milestone)."""
    store = get_audit_store()
    ws = store.get_workspace("default", session_id=session.session_id, access_code=session.client_label)
    ds = payload.dataset or (PlantDataset.model_validate(ws["dataset"]) if ws and ws.get("dataset") else demo_dataset())
    cfg = payload.config or (SolverConfig.model_validate(ws["config"]) if ws and ws.get("config") else default_config())
    created = store.save_checkpoint(
        dataset=ds,
        config=cfg,
        result=payload.result,
        trigger_source=payload.trigger_source,
        title_en=payload.title_en,
        title_ar=payload.title_ar,
        session_id=session.session_id,
        access_code=session.client_label,
    )
    return {
        "storage_backend": store.storage_backend,
        "checkpoint": created,
        "checkpoints": store.list_checkpoints(session_id=session.session_id, limit=25),
    }


@router.post("/checkpoints/{checkpoint_id}/restore", response_model=CheckpointRestoreResponse)
def restore_checkpoint_endpoint(
    checkpoint_id: str,
    session: AuthSession = Depends(require_auth_session),
) -> CheckpointRestoreResponse:
    """Restore exact plant/config state from a checkpoint and return a freshly solved unified scenario bundle."""
    store = get_audit_store()
    cp = store.get_checkpoint(checkpoint_id, session_id=session.session_id)
    if cp is None:
        raise HTTPException(status_code=404, detail=f"Decision checkpoint '{checkpoint_id}' not found.")

    snap = cp.get("state_snapshot") or {}
    try:
        restored_ds = PlantDataset.model_validate(snap["dataset"])
        restored_cfg = SolverConfig.model_validate(snap["config"])
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Corrupted checkpoint state snapshot: {exc}") from exc

    with bind_sandbox_engine_context(session.session_id):
        result = solve_plant_schedule(restored_ds, restored_cfg, sandbox_id=session.session_id)
    store.save_workspace(
        workspace_id="default",
        name=restored_ds.name,
        dataset=restored_ds,
        config=restored_cfg,
        session_id=session.session_id,
        access_code=session.client_label,
    )
    store.save_run(result, dataset=restored_ds, session_id=session.session_id)

    cp_meta = {k: v for k, v in cp.items() if k != "state_snapshot"}
    return CheckpointRestoreResponse(
        restored=True,
        storage_backend=store.storage_backend,
        active_engine=result.active_engine,
        checkpoint=cp_meta,
        dataset=restored_ds,
        config=restored_cfg,
        result=result,
        workforce=result.workforce,
        financials=result.financials,
        risk_radar=result.risk_radar,
        validation=result.validation,
    )


# --------------------------------------------------------------------------------------------
# v1.4 Feature 2: Capable-to-Promise (CTP) Non-Destructive Rush-Order Quoter
# --------------------------------------------------------------------------------------------
@router.post("/quote/ctp", response_model=CTPQuoteResult)
async def quote_ctp_endpoint(
    payload: CTPQuoteRequest,
    session: AuthSession = Depends(require_auth_session),
) -> CTPQuoteResult:
    """Strictly non-destructive Capable-to-Promise (CTP) evaluation. Never mutates active workspace or DB."""
    store = get_audit_store()
    fallback_ds = payload.dataset
    fallback_cfg = payload.config
    if fallback_ds is None or fallback_cfg is None:
        ws = store.get_workspace("default", session_id=session.session_id, access_code=session.client_label)
        if fallback_ds is None:
            fallback_ds = PlantDataset.model_validate(ws["dataset"]) if ws and ws.get("dataset") else demo_dataset()
        if fallback_cfg is None:
            fallback_cfg = SolverConfig.model_validate(ws["config"]) if ws and ws.get("config") else default_config()

    try:
        with bind_sandbox_engine_context(session.session_id):
            return await asyncio.to_thread(
                evaluate_ctp_rush_order,
                payload,
                fallback_ds,
                fallback_cfg,
            )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/quote/ctp/commit", response_model=CTPCommitResponse)
def commit_ctp_order_endpoint(
    payload: CTPCommitRequest,
    session: AuthSession = Depends(require_auth_session),
) -> CTPCommitResponse:
    """Commit an accepted CTP candidate rush order into the live schedule and record a Decision Checkpoint."""
    store = get_audit_store()
    ws = store.get_workspace(payload.workspace_id, session_id=session.session_id, access_code=session.client_label)
    base_ds = payload.dataset or (PlantDataset.model_validate(ws["dataset"]) if ws and ws.get("dataset") else demo_dataset())
    base_cfg = payload.config or (SolverConfig.model_validate(ws["config"]) if ws and ws.get("config") else default_config())

    next_ds = base_ds.model_copy(deep=True)
    existing_ids = {o.order_id for o in next_ds.orders}
    cand = payload.candidate_order.model_copy(deep=True)
    if cand.order_id in existing_ids:
        seq = 1
        while f"CTP-RUSH-{seq:02d}" in existing_ids:
            seq += 1
        cand.order_id = f"CTP-RUSH-{seq:02d}"
    next_ds.orders.append(cand)

    with bind_sandbox_engine_context(session.session_id):
        result = solve_plant_schedule(next_ds, base_cfg, sandbox_id=session.session_id)
    store.save_workspace(
        workspace_id=payload.workspace_id,
        name=next_ds.name,
        dataset=next_ds,
        config=base_cfg,
        session_id=session.session_id,
        access_code=session.client_label,
    )
    store.save_run(result, dataset=next_ds, session_id=session.session_id)
    cp = store.save_checkpoint(
        dataset=next_ds,
        config=base_cfg,
        result=result,
        trigger_source="ctp_commit",
        title_en=f"CTP Rush Order Committed: {cand.order_id} ({cand.customer} • {cand.quantity_pcs:,} pcs)",
        title_ar=f"اعتماد أمر عاجل CTP: {cand.order_id} ({cand.customer} • {cand.quantity_pcs:,} قطعة)",
        session_id=session.session_id,
        access_code=session.client_label,
    )

    return CTPCommitResponse(
        committed=True,
        order_id=cand.order_id,
        active_engine=result.active_engine,
        checkpoint=cp,
        dataset=next_ds,
        config=base_cfg,
        result=result,
        workforce=result.workforce,
        financials=result.financials,
        risk_radar=result.risk_radar,
        validation=result.validation,
    )


# --------------------------------------------------------------------------------------------
# v1.4 Feature 3: 1-Click Bilingual WhatsApp Shift Dispatch Formatter
# --------------------------------------------------------------------------------------------
@router.post("/dispatch/whatsapp", response_model=WhatsAppDispatchResponse)
def whatsapp_dispatch_endpoint(
    payload: WhatsAppDispatchRequest,
    session: AuthSession = Depends(require_auth_session),
) -> WhatsAppDispatchResponse:
    """Format a deterministic EN or AR WhatsApp shift dispatch message for a specific day/shift or full week."""
    res = payload.result
    ds = payload.dataset
    cfg = payload.config
    if res is None:
        res, resolved_ds = _resolve_active_session_result(session.session_id)
        if ds is None:
            ds = resolved_ds
    return format_whatsapp_shift_dispatch(
        result=res,
        dataset=ds,
        config=cfg,
        scope=payload.scope,
        day=payload.day,
        shift=payload.shift,
        language=payload.language,
    )
