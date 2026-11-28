# Mini-DIOS Plastics — Codebase & Code-Update Ledger

> **Track B — Dedicated Engineering Ledger (For Engineers, DevOps & AI Agents)**
> **Scope:** Complete, granular, file-by-file map of what the codebase currently contains (**Section A**) and a chronological, newest-first ledger of every code update ever made (**Section B**).
> **Security Guardrail:** NEVER store `.env` values, API keys, passwords, `AUTH_SECRET_KEY`, `GEMINI_API_KEY`, or private tokens in this file (reference variable names only).
> **Last Synchronized:** 2026-11-28 (`v1.9 / Visual Decision Intelligence Blueprint & Causal Trace Inspector` • **119** active repository files mapped • **13** code updates logged)

---

## Section A — Living Codebase Map (Current State)

### A.1 Clean Repository Directory Tree
*(Excludes `node_modules/`, `.next/`, `__pycache__/`, `.venv/`, `.tools/`, `.pytest_cache/`, `.git/`, `backend/data/*.db`, `package-lock.json`, and `.env`)*

```text
DIOs/
├── .gitignore
├── render.yaml
├── scripts/
│   └── sync_docs_to_drive.py
├── tests/
│   └── test_drive_sync.py
└── mini-dios-workforce/
    ├── .gitignore
    ├── AUDIT_AGENT.md
    ├── AUDIT_REPORT.md
    ├── README.md
    ├── docker-compose.yml
    ├── docker-compose.prod.yml
    ├── start.bat
    ├── stop.bat
    ├── scripts/
    │   └── run_audit.py
    ├── backend/
    │   ├── .env.example
    │   ├── Dockerfile
    │   ├── main.py
    │   ├── pytest.ini
    │   ├── requirements.txt
    │   ├── api/
    │   │   ├── __init__.py
    │   │   └── routes.py
    │   ├── core/
    │   │   ├── __init__.py
    │   │   ├── audit.py
    │   │   ├── auth.py
    │   │   ├── backtest.py
    │   │   ├── copilot.py
    │   │   ├── disruptions.py
    │   │   ├── excel_io.py
    │   │   ├── financials.py
    │   │   ├── kpi.py
    │   │   ├── onboarding.py
    │   │   ├── ontology.py
    │   │   ├── risk_radar.py
    │   │   ├── seed.py
    │   │   ├── solver.py
    │   │   ├── verify.py
    │   │   └── workforce_solver.py
    │   └── tests/
    │       ├── conftest.py
    │       ├── test_api.py
    │       ├── test_auth_and_sandbox.py
    │       ├── test_copilot.py
    │       ├── test_financials.py
    │       ├── test_risk_radar_and_autonomous_pm.py
    │       ├── test_solver.py
    │       ├── test_validator.py
    │       └── test_workforce_solver.py
    └── frontend/
        ├── Dockerfile
        ├── next-env.d.ts
        ├── next.config.ts
        ├── package.json
        ├── postcss.config.mjs
        ├── tsconfig.json
        └── src/
            ├── app/
            │   ├── api/[...path]/route.ts
            │   ├── globals.css
            │   ├── icon.svg
            │   ├── layout.tsx
            │   └── page.tsx
            ├── components/
            │   ├── CopilotDrawer.tsx
            │   ├── DataStudioView.tsx
            │   ├── DecisionLoopStrip.tsx
            │   ├── ExecutiveBriefModal.tsx
            │   ├── FinancialsView.tsx
            │   ├── GuidedOnboardingModal.tsx
            │   ├── HistoricalBacktestModal.tsx
            │   ├── LoginGate.tsx
            │   ├── PinScenarioButton.tsx
            │   ├── ProductionGanttView.tsx
            │   ├── QuickAddModal.tsx
            │   ├── RiskRadarPanel.tsx
            │   ├── ScenarioComparisonMatrix.tsx
            │   ├── ScheduleExportMenu.tsx
            │   ├── ScopeView.tsx
            │   ├── TopBar.tsx
            │   ├── TradeoffConsole.tsx
            │   ├── WorkforceView.tsx
            │   └── studio/
            │       ├── ConfirmDeleteModal.tsx
            │       ├── MoldsEditor.tsx
            │       ├── OrdersEditor.tsx
            │       ├── PhysicsEditor.tsx
            │       ├── PressesEditor.tsx
            │       └── ResinsEditor.tsx
            └── lib/
                ├── api.ts
                ├── format.ts
                ├── i18n.ts
                ├── store.tsx
                └── types.ts
```

---

### A.2 File-by-File Inventory — Backend (`mini-dios-workforce/backend/`, 31 files)

#### Core Application & API (`18` files)
| File Path | Purpose | Key Classes, Functions & Routes | Key Dependencies |
| :--- | :--- | :--- | :--- |
| `backend/main.py` | FastAPI app entrypoint, CORS middleware, and router mounting. | `root()` | `fastapi`, `api/routes.py` |
| `backend/api/__init__.py` | Package marker for API routers. | — | — |
| `backend/api/routes.py` | All REST, auth, sandbox, solver, Copilot, Backtest, Guided Onboarding, Integration Export, workspace, audit, and Excel endpoints under `/api`. | `GET /health`, `GET /auth/me`, `POST /auth/login`, `POST /auth/logout`, `POST /sandbox/reset`, `GET /demo-data`, `GET /template.xlsx`, `POST /validate`, `POST /solve`, `POST /workforce/solve`, `POST /copilot/ask`, `GET /backtest/template`, `POST /backtest/replay`, `POST /onboarding/generate`, `GET /export/schedule.xlsx`, `GET /export/schedule.csv`, `GET /export/erp-payload.json`, `POST /export-dataset.xlsx`, `POST /export-brief.xlsx`, `GET /audit-log`, `GET /audit-log/{run_id}`, `GET/POST/DELETE /workspaces` | `core/auth.py`, `core/solver.py`, `core/workforce_solver.py`, `core/copilot.py`, `core/backtest.py`, `core/onboarding.py`, `core/excel_io.py`, `core/audit.py` |
| `backend/core/__init__.py` | Re-exports core domain schemas and solver helpers. | — | `core/*` |
| `backend/core/ontology.py` | Industrial plastics Pydantic models (including container consolidation & warehouse WIP schemas), physics helpers, and Pre-Solve Plant Anomaly Validator. | `PressMachine`, `Mold`, `ResinStock`, `ProductionOrder`, `FactoryWorker`, `PlantPhysicsConfig`, `WorkforceConfig`, `SolverConfig`, `ScenarioDisruptions`, `ContainerGroupSummary`, `PlantDataset`, `SolveResult`, `validate_plant_data()`, `transition_penalty()`, `order_duration_mins()`, `order_gross_weight_kg()`, `peak_overlap_mins()` | `pydantic` |
| `backend/core/disruptions.py` | Composable scenario engine transforming base `PlantDataset` + `SolverConfig.scenarios` without mutating caller state. | `EffectivePlantState`, `apply_plant_scenarios()` | `core/ontology.py` |
| `backend/core/solver.py` | Deterministic Google OR-Tools CP-SAT parallel-machine scheduler (`HC1–HC6`, `Auto PM`, 6.5h export buffer, `container_sync_enabled` multi-SKU export container coupling) + Naive FIFO baseline comparator. | `DatasetValidationError`, `run_fifo_baseline()`, `solve_plant_schedule()` | `ortools.sat.python.cp_model`, `disruptions.py`, `workforce_solver.py`, `financials.py`, `risk_radar.py`, `kpi.py`, `verify.py` |
| `backend/core/verify.py` | Independent zero-tolerance post-solve verifier for all 6 Press hard constraints (`HC1–HC6`). | `verify_hard_constraints()` | `core/ontology.py` |
| `backend/core/workforce_solver.py` | Press-coupled 5-role Workforce CP-SAT roster optimizer (`WHC1–WHC5`), Ramadan 4×6h clamp, Naive Static Rotation baseline, and callout simulator. | `ShiftDef`, `SlotDemand`, `shift_layout()`, `derive_demand()`, `evaluate_roster()`, `verify_workforce()`, `build_naive_roster()`, `solve_workforce()`, `solve_workforce_with_callouts()` | `ortools.sat.python.cp_model`, `core/ontology.py` |
| `backend/core/kpi.py` | Deterministic KPI evaluator, container consolidation & finished-goods warehouse inventory sweep, Gantt block builder, resin/press summaries, and Baseline vs. CP-SAT ROI scorecard. | `build_schedule_plan()`, `build_scorecard()` | `core/ontology.py` |
| `backend/core/financials.py` | Zero-double-counting weekly P&L reconciliation, monthly/annual projections, unlocked capacity value, and per-order margin table. | `compute_financial_report()` | `core/ontology.py` |
| `backend/core/risk_radar.py` | Deterministic Proactive Delay & Bottleneck Risk Radar (6 categories including `warehouse_congestion` & trapped container alerts with bilingual Copilot mitigation prompts). | `compute_risk_radar()` | `core/ontology.py` |
| `backend/core/copilot.py` | Unlimited Composable Operations Copilot (`google-genai` `gemini-4-hydrogen` + EN/AR deterministic offline parser) returning unified scenario bundles and Commander-Grade `FinancialTradeoffSummary`. | `FinancialTradeoffSummary`, `CopilotResult`, `StrategyComparison`, `BottleneckInsight`, `_compute_financial_tradeoff_summary()`, `execute_simulate_plant_scenario()`, `execute_inspect_bottleneck()`, `execute_compare_two_strategies()`, `run_offline_composable_copilot()`, `run_plastics_copilot()` | `google-genai`, `solver.py`, `workforce_solver.py`, `financials.py`, `risk_radar.py` |
| `backend/core/backtest.py` | 1-Month Historical Backtest / Replay Engine ("The Proof Engine") generating 13-column CSV/XLSX templates, parsing historical logs, and replaying them via CP-SAT. | `HistoricalLogRow`, `BacktestComparisonBlock`, `HistoricalBacktestReport`, `build_backtest_template_csv()`, `build_backtest_template_xlsx()`, `sample_30day_historical_rows()`, `parse_backtest_upload()`, `run_historical_backtest_replay()` | `openpyxl`, `core/ontology.py`, `core/solver.py` |
| `backend/core/onboarding.py` | Guided "Process-First" 5-Step Plant Onboarding Generator building immediately solvable plant workspaces + "Current Specs Only" Readiness Checklist. | `GuidedSetupRequest`, `ReadinessChecklistItem`, `GuidedSetupResponse`, `build_current_specs_checklist()`, `build_guided_plant_workspace()` | `core/ontology.py`, `core/solver.py`, `core/seed.py` |
| `backend/core/ctp.py` | Capable-to-Promise (CTP) Non-Destructive Rush-Order Quoter computing earliest finish hour, marginal cost breakdown, break-even unit price, and bumped-order delays without mutating active state. | `CTPQuoteRequest`, `CTPFinancialImpact`, `CTPBumpedOrder`, `CTPQuoteResult`, `evaluate_ctp_rush_order()` | `core/ontology.py`, `core/solver.py`, `core/seed.py` |
| `backend/core/dispatch.py` | Deterministic bilingual (`EN` / `AR`) WhatsApp Shift Dispatch formatter for full-week or day/shift scope. | `WhatsAppDispatchRequest`, `WhatsAppDispatchResponse`, `format_whatsapp_shift_dispatch()` | `core/ontology.py`, `core/workforce_solver.py` |
| `backend/core/excel_io.py` | 4-tab Excel workbook generator/parser, Executive Brief `.xlsx` exporter, and Integration-Ready Schedule exporters (`schedule.xlsx`, `schedule.csv`, `erp-payload.json`). | `build_template_workbook()`, `parse_workbook_bytes()`, `export_brief_workbook()`, `export_integration_schedule_workbook()`, `export_integration_schedule_csv()`, `export_integration_erp_payload()` | `openpyxl`, `core/ontology.py` |
| `backend/core/audit.py` | Dual-mode persistence layer (`DATABASE_URL` PostgreSQL connection pool `pool_size=3, max_overflow=2, pool_pre_ping=True` + SQLite fallback `data/mini_dios.db`) for `plastics_audit_runs`, `saved_workspaces`, `pinned_scenarios`, `backtest_runs`, and `decision_checkpoints`. | `AuditStore`, `normalize_database_url()` | `sqlite3`, `sqlalchemy` (optional), `core/ontology.py` |
| `backend/core/auth.py` | Signed HMAC cookie sessions, multi-client passcode parsing (`DEMO_ACCESS_CODES`), sandbox namespace isolation, and per-hour Copilot quota shield. | `AuthSession`, `is_auth_enabled()`, `verify_passcode()`, `sign_session_token()`, `verify_session_token()`, `set_session_cookie()`, `clear_session_cookie()` | `hmac`, `hashlib`, `fastapi` |
| `backend/core/seed.py` | Seeded Delta & Riyadh Polymer Packaging Plant (6 presses, 10 molds, 5 resins, 24 orders across 4 export container groups, 28 floor workers). | `default_config()`, `demo_workers()`, `demo_dataset()` | `core/ontology.py` |
| `backend/core/uem.py` | Domain-agnostic 6-Primitive Universal Execution Model (`ResourceNode`, `ActivityNode`, `TransitionMatrix`, `CumulativeEnvelope`, `SynchronizationGroup`, `ObjectiveTermSpec`) & solution schemas. | `UEMGraph`, `ResourceNode`, `ActivityNode`, `TransitionMatrix`, `CumulativeEnvelope`, `SynchronizationGroup`, `ObjectiveTermSpec`, `UEMSolution`, `UEMVerificationCheck` | `pydantic` |
| `backend/core/uem_compiler.py` | Deterministic OR-Tools CP-SAT compiler translating any 6-primitive `UEMGraph` into a `cp_model.CpModel` and solving with warm-start hints. | `compile_and_solve_uem()` | `ortools.sat.python.cp_model`, `core/uem.py` |
| `backend/core/uem_verify.py` | Independent zero-tolerance post-solve verifier for all 6 UEM primitives (`UEM-P1..UEM-P6`). | `verify_uem_solution()` | `core/uem.py` |
| `backend/core/di/__init__.py` | Re-exports all 5 domain-agnostic Decision Intelligence layers. | Layer 1–5 exports | `core/di/*` |
| `backend/core/di/ontology_meta.py` | Layer 1 Formal Business Ontology Meta-Model (`EntityTypeSpec`, `EntityInstance`, `TypedRelationship`, `SemanticInvariantSpec`, `BusinessOntologyGraph`). | `BusinessOntologyGraph` | `pydantic` |
| `backend/core/di/arch_validator.py` | Layer 2 Pre-Solve Business Architecture Validator (`GATE-1-STRUCTURAL`, `GATE-2-CAPABILITY`, `GATE-3-POLICY`). | `validate_business_architecture()`, `ArchitectureValidationReport` | `core/di/ontology_meta.py` |
| `backend/core/di/bpmn_engine.py` | Layer 3 OMG BPMN 2.0 Process Template, topological connectivity validator, and standards-compliant BPMN 2.0 XML exporter. | `BPMNProcessTemplate`, `BPMNFlowNode`, `BPMNSequenceFlow` | `xml.sax.saxutils`, `pydantic` |
| `backend/core/di/dmn_engine.py` | Layer 4 Pure-Python OMG DMN 1.3 Decision Table rule engine (S-FEEL unary tests, hit policies `U/F/P/A/C/C+/C</C>`) and DMN 1.3 XML exporter. | `DMNDecisionTable`, `DMNRegistry`, `eval_feel_unary_test()` | `xml.sax.saxutils`, `pydantic` |
| `backend/core/di/decision_meta.py` | Layer 5 Decision Intelligence Causal Decision Diagram (`DecisionLever -> IntermediateMetric -> DecisionOutcome` pathway tracer). | `CausalDecisionModel`, `DecisionLever`, `IntermediateMetric`, `DecisionOutcome`, `CausalEdge` | `pydantic` |
| `backend/adapters/__init__.py` | Domain adapters package exports. | Plastics adapter exports | `adapters/plastics.py` |
| `backend/adapters/plastics.py` | Mini-DIOS Plastics reference domain adapter compiling `PlantDataset` + `SolverConfig` through Layers 1–4 into `UEMGraph` with two-way bounded labor coupling and Layer 5 Causal Decision Diagram. | `build_plastics_ontology_graph()`, `validate_plastics_architecture()`, `build_plastics_dmn_registry()`, `build_plastics_bpmn_template()`, `compile_plastics_to_uem_graph()`, `solve_plastics_via_uem()`, `build_plastics_causal_decision_model()`, `build_plastics_blueprint()` | `core/di/*`, `core/uem*.py`, `core/ontology.py`, `core/workforce_solver.py` |
| `backend/tests/test_uem_di_parity.py` | Full pytest parity suite comparing Legacy vs. UEM+DI across 5 core modes, CTP, Backtest, Copilot, two-way labor shortage feedback, core domain purity, and a non-plastics Beverage Bottling Plant proof. | 14 parity & universality tests | `pytest`, `adapters/plastics.py`, `core/uem*.py`, `core/di/*` |

#### Backend Tests & Config (`13` files)
| File Path | Purpose | Key Functions / Contents | Key Dependencies |
| :--- | :--- | :--- | :--- |
| `backend/tests/conftest.py` | Shared pytest fixtures for seeded plant dataset and solve results. | `base_plant_dataset()`, `base_solve_result()` | `pytest`, `core/seed.py`, `core/solver.py` |
| `backend/tests/test_api.py` | End-to-end FastAPI TestClient coverage for health, demo, Excel bridge, solve, audit log, and workspaces CRUD. | `test_health_and_demo_data`, `test_solve_audit_log_and_export_brief_xlsx`, `test_workspaces_crud_endpoints` | `fastapi.testclient`, `main.py` |
| `backend/tests/test_auth_and_sandbox.py` | Tests auth gate enforcement, signed cookies, multi-prospect workspace isolation, sandbox reset, and Copilot hourly quota shield. | `test_unauthenticated_blocked_when_auth_enabled`, `test_multi_prospect_workspace_isolation_and_sandbox_reset` | `core/auth.py`, `api/routes.py` |
| `backend/tests/test_copilot.py` | Tests Gemini tool-calling, zero-LLM-math guard, EN/AR offline fallback, and multi-lever Risk Radar mitigations returning unified bundles. | `test_copilot_gemini_composable_simulate_tool_uses_real_cpsat`, multi-lever mitigation tests | `core/copilot.py`, `api/routes.py` |
| `backend/tests/test_financials.py` | Verifies P&L reconciliation (`Revenue - Costs == Net Profit`), zero double-counting, currency conversion, and annualized projections. | Financial reconciliation assertions | `core/financials.py` |
| `backend/tests/test_risk_radar_and_autonomous_pm.py` | Verifies Risk Radar alert generation, resin depletion clock, and Autonomous PM (`Auto PM`) shot-limit constraints. | Risk Radar & Auto PM tests | `core/risk_radar.py`, `core/solver.py` |
| `backend/tests/test_solver.py` | Verifies Press CP-SAT `HC1–HC6` compliance, purge scrap reduction vs. FIFO, breakdowns, resin caps, and Ramadan/Peak modes. | Press CP-SAT regression suite | `core/solver.py`, `core/verify.py` |
| `backend/tests/test_validator.py` | Tests Pre-Solve Anomaly Validator error/warning detection (press compatibility, hot-runner mismatch, resin deficits, impossible deadlines, PM threshold). | Validator unit tests | `core/ontology.py` |
| `backend/tests/test_workforce_solver.py` | Verifies 28-worker seed, `WHC1–WHC5` zero violations, 11h rest gap, Ramadan 4×6h clamp, leave/sick locks, and callout recovery. | 20 workforce CP-SAT tests | `core/workforce_solver.py` |
| `backend/.env.example` | Template listing backend env var names (`GEMINI_API_KEY`, `GEMINI_MODEL`, `OFFLINE_MODE`, auth vars) with no real secrets. | Environment variable template | — |
| `backend/Dockerfile` | Python 3.12 slim container image for FastAPI + OR-Tools CP-SAT backend. | Docker build spec | `requirements.txt` |
| `backend/pytest.ini` | Pytest discovery and path configuration. | `pytest` config | — |
| `backend/requirements.txt` | Pinned Python dependencies (`fastapi`, `uvicorn`, `ortools`, `pydantic`, `openpyxl`, `google-genai`, `python-dotenv`, `pytest`, etc.). | Python package manifest | — |

---

### A.3 File-by-File Inventory — Frontend (`mini-dios-workforce/frontend/`, 41 files)

#### App Router, Proxy & Core Libraries (`10` files)
| File Path | Purpose | Key Exports / Hooks | Key Dependencies |
| :--- | :--- | :--- | :--- |
| `frontend/src/app/layout.tsx` | Root Next.js layout, metadata, mobile viewport config (`viewport-fit=cover`), and `AppProvider` wrapper. | `viewport`, `metadata`, `RootLayout` | `globals.css`, `lib/store.tsx` |
| `frontend/src/app/page.tsx` | Main command center shell routing between `LoginGate`, `TopBar`, `DecisionLoopStrip`, Applied Delta Banner, Tabs 1–6, `QuickAddModal`, `ExecutiveBriefModal`, `HistoricalBacktestModal`, `GuidedOnboardingModal`, and `CopilotDrawer`. | `HomePage` | All top-level views & modals, `lib/store.tsx` |
| `frontend/src/app/api/[...path]/route.ts` | Server-side Next.js API catch-all proxy to `BACKEND_INTERNAL_URL` with explicit header allowlist (prevents Render HTTP 508 loop), self-proxy guard, cookie `Domain=` stripping, and single GET retry on 502/503/504 cold starts. | `dynamic`, `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `OPTIONS` | `next/server` |
| `frontend/src/app/globals.css` | Tailwind CSS base, dark theme tokens, hatched Gantt patterns, Peak/Iftar bands, 24px mobile slider thumbs, safe-area padding, and RTL typography rules. | CSS utility classes | Tailwind CSS |
| `frontend/src/app/icon.svg` | Browser favicon SVG for Mini-DIOS Plastics. | SVG asset | — |
| `frontend/src/lib/store.tsx` | Global React state context: workspaces, dataset CRUD, solver config, `toggleContainerSyncMode`, `backtestModalOpen`, `onboardingModalOpen`, `applyGuidedWorkspace`, atomic Copilot bundle commit, signature-based debounced auto-sync across Tabs 1–6, Pin & Compare A/B/C slots, currency/lang, and auth session. | `AppProvider`, `useApp`, `QuickModalType`, `StudioSubTab`, `DEFAULT_PHYSICS`, `DEFAULT_WORKFORCE` | `lib/api.ts`, `lib/types.ts` |
| `frontend/src/lib/api.ts` | Typed HTTP client (`handleJson` single-read stream parser) for auth, validation, solve, workforce solve, Copilot, Backtest replay/templates, Guided Onboarding, Integration Schedule Exports, workspaces, and audit endpoints. | `API_BASE`, `fetchAuthMe`, `loginWithPasscodeApi`, `runSolveApi`, `runWorkforceSolveApi`, `askCopilotApi`, `runHistoricalBacktestReplayApi`, `generateGuidedSetupApi`, `downloadIntegrationScheduleXlsx` (+18) | `lib/types.ts` |
| `frontend/src/lib/types.ts` | Complete TypeScript domain interfaces mirroring `backend/core/ontology.py`, `copilot.py`, `backtest.py`, `onboarding.py`, and `auth.py`. | `PlantDataset`, `SolverConfig`, `SolveResult`, `WorkforceResult`, `FinancialReport`, `RiskRadarReport`, `CopilotResult`, `FinancialTradeoffSummary`, `HistoricalBacktestReport`, `GuidedSetupRequest`, `PinnedScenario` (+68) | — |
| `frontend/src/lib/i18n.ts` | Complete English (LTR) and Arabic (RTL) dictionary for all UI labels, roles, shifts, colors, constraints, Backtest, Guided Onboarding, Dual-Audience Brief, and Risk Radar copy. | `COPY`, `WORKER_ROLE_LABELS`, `SHIFT_LABELS`, `CONSTRAINT_LABELS`, `WORKFORCE_CONSTRAINT_LABELS`, `COLOR_LABELS`, `DAY_NAMES_I18N` | `lib/types.ts` |
| `frontend/src/lib/format.ts` | Deterministic SAR ↔ EGP currency conversion and number/money formatting helpers. | `convertCurrency`, `formatMoney`, `formatNumber` | `lib/types.ts` |

#### Views, Modals & Studio Editors (`25` files)
| File Path | Purpose | Key Exports | Key Dependencies |
| :--- | :--- | :--- | :--- |
| `frontend/src/components/LoginGate.tsx` | Hosted executive access gate supporting multi-client passcodes (`ALEX-2026`, `KSA-2026`, `DIOS-2026`) and optional instant demo. | `LoginGate` | `lib/store.tsx`, `lib/i18n.ts` |
| `frontend/src/components/TopBar.tsx` | Responsive header (desktop bar + mobile compact bar with slide-over Controls drawer including `Container Sync` + sticky bottom action bar for Run Optimization & Ops Copilot). | `TopBar` | `lib/store.tsx`, `lib/i18n.ts` |
| `frontend/src/components/DecisionLoopStrip.tsx` | 5-stage horizontal snap-scroll strip (`1. Model → 2. Sense → 3. Optimize → 4. Command → 5. Adapt`) with live risk, status, constraint, and savings badges. | `DecisionLoopStrip` | `lib/store.tsx`, `lib/i18n.ts` |
| `frontend/src/components/ScopeView.tsx` | Tab 1 (`Plant Scope & Readiness`): Saved Workspaces, 1-Month Historical Backtest & 5-Step Guided Setup action banner, Current Specs Readiness Checklist, Quick-Add Hub, 6 KPI pills, Risk Radar, inline Resin & Mold PM health, Pre-Solve Diagnostics, Press Fleet. | `ScopeView` | `RiskRadarPanel`, `lib/store.tsx` |
| `frontend/src/components/HistoricalBacktestModal.tsx` | Bilingual 1-Month Historical Backtest / Replay modal ("The Proof Engine") with CSV/XLSX template downloads, file uploader, 1-click sample 30-day replay, and Actual vs. Mini-DIOS ROI Replay Card. | `HistoricalBacktestModal` | `lib/api.ts`, `lib/store.tsx`, `lib/format.ts` |
| `frontend/src/components/GuidedOnboardingModal.tsx` | Bilingual 5-Step Process-First Guided Plant Setup Wizard + "Current Specs Only" 3-Hour Readiness Checklist. | `GuidedOnboardingModal` | `lib/api.ts`, `lib/store.tsx`, `lib/i18n.ts` |
| `frontend/src/components/ScheduleExportMenu.tsx` | Integration-Ready Schedule Export button bar (`Excel .xlsx`, `Flat CSV .csv`, `ERP JSON Odoo / SAP B1`). | `ScheduleExportMenu` | `lib/api.ts`, `lib/store.tsx` |
| `frontend/src/components/RiskRadarPanel.tsx` | Full & compact Risk Radar cards displaying `Plant Risk Score`, financial exposure, Resin Silo Depletion Clock, Warehouse Congestion alerts, and one-click `Mitigate in Copilot` / `Inspect` actions. | `RiskRadarPanel` | `lib/store.tsx`, `lib/format.ts` |
| `frontend/src/components/DataStudioView.tsx` | Tab 2 (`Plant Data & Parameters`): Sticky action bar, validation pill, and 5 Studio sub-tabs. | `DataStudioView` | `studio/*`, `lib/store.tsx` |
| `frontend/src/components/studio/PressesEditor.tsx` | Tab 2A CRUD editor for presses (stacked mobile cards + desktop table). | `PressesEditor` | `ConfirmDeleteModal`, `lib/store.tsx` |
| `frontend/src/components/studio/MoldsEditor.tsx` | Tab 2B CRUD editor for molds, compatibility, cycle times, and shot intervals. | `MoldsEditor` | `ConfirmDeleteModal`, `lib/store.tsx` |
| `frontend/src/components/studio/ResinsEditor.tsx` | Tab 2C CRUD editor for resin inventory, pricing, drying floors, and melt temps. | `ResinsEditor` | `ConfirmDeleteModal`, `lib/store.tsx` |
| `frontend/src/components/studio/OrdersEditor.tsx` | Tab 2D CRUD editor for production orders with search/filter and live run-time/weight estimates. | `OrdersEditor` | `ConfirmDeleteModal`, `lib/store.tsx` |
| `frontend/src/components/studio/PhysicsEditor.tsx` | Tab 2E editor for purge physics, tariffs, peak windows, currency/FX, horizon, overhead, and solver time cap. | `PhysicsEditor` | `lib/store.tsx` |
| `frontend/src/components/studio/ConfirmDeleteModal.tsx` | Referential-safety confirmation modal warning of impacted orders/molds before deleting a press, mold, or resin. | `ConfirmDeleteModal` | `lib/i18n.ts` |
| `frontend/src/components/TradeoffConsole.tsx` | Tab 3 (`Trade-Off & Scenario Composer`): 4 KPI delta cards, 4 executive sliders + presets, Export Container Consolidation & Finished-Goods Warehouse WIP card, composable disruption builder, `PinScenarioButton`, `ScenarioComparisonMatrix`, `6/6` HC verification, and audit history. | `TradeoffConsole` | `PinScenarioButton`, `ScenarioComparisonMatrix`, `lib/store.tsx` |
| `frontend/src/components/PinScenarioButton.tsx` | One-click button/popover to pin the active schedule into Comparison Slot A, B, or C. | `PinScenarioButton` | `lib/store.tsx` |
| `frontend/src/components/ScenarioComparisonMatrix.tsx` | Side-by-side A vs. B vs. C boardroom matrix with exact deltas, `Best` badges, and `Promote to Active Plan`. | `ScenarioComparisonMatrix` | `lib/store.tsx`, `lib/format.ts` |
| `frontend/src/components/ProductionGanttView.tsx` | Tab 4 (`Press Gantt & Color Sequence`): 168h pigment-colored Gantt, `ScheduleExportMenu`, FIFO vs. CP-SAT switch, Peak/Iftar bands, tap-to-inspect mobile support, resin/scrap charts, and sequence audit table. | `ProductionGanttView` | `RiskRadarPanel`, `ScheduleExportMenu`, `recharts`, `lib/store.tsx` |
| `frontend/src/components/FinancialsView.tsx` | Tab 5 (`Revenue & Savings`): 5 financial KPI cards, 1-Month Historical Backtest trigger, Container Consolidation & Working Capital Lockup table, inline assumptions, FIFO vs. CP-SAT P&L reconciliation, per-order profitability, and `ScenarioComparisonMatrix`. | `FinancialsView` | `PinScenarioButton`, `ScenarioComparisonMatrix`, `recharts`, `lib/store.tsx` |
| `frontend/src/components/WorkforceView.tsx` | Tab 6 (`Workforce & Shifts`): 5 workforce KPI cards, `ScheduleExportMenu`, 3 objective sliders, sick-callout chips, Roster Matrix, Demand vs. Scheduled Coverage Chart, Worker Directory CRUD, and `5/5 WHC` verification. | `WorkforceView` | `ScheduleExportMenu`, `recharts`, `lib/store.tsx` |
| `frontend/src/components/CopilotDrawer.tsx` | Slide-over bilingual Operations Copilot drawer (`92dvh` mobile-safe) with Commander-Grade Financial Trade-Off Callout Box, starter chips, Before → After Applied Delta banner, Bottleneck/Comparison cards, `Pin for Comparison`, and `Apply This Scenario to Dashboard`. | `CopilotDrawer` | `lib/api.ts`, `lib/store.tsx` |
| `frontend/src/components/ExecutiveBriefModal.tsx` | Dual-Audience boardroom ROI scorecard modal (`Owner / Chairman View` vs. `Plant / Production Manager View` Decision Shield + `Download / Print Executive PDF` + `ScheduleExportMenu` + `6/6` verified constraints + Resin Purge Audit). | `ExecutiveBriefModal` | `ScheduleExportMenu`, `lib/store.tsx`, `lib/format.ts` |
| `frontend/src/components/DecisionCheckpointsDrawer.tsx` | Slide-over Decision Checkpoints & 1-Click Rollback drawer accessible from Tab 1 displaying storage badge (`postgres` vs. `sqlite_fallback`), checkpoint history, and atomic rollback. | `DecisionCheckpointsDrawer` | `lib/store.tsx`, `lib/format.ts`, `lib/i18n.ts` |
| `frontend/src/components/CTPQuoterModal.tsx` | Capable-to-Promise (CTP) Non-Destructive Rush-Order Quoter modal with 1-click 40k Export sample loader, color-coded verdict, marginal cost & break-even unit price card, bumped orders list, Discard, and Accept & Commit. | `CTPQuoterModal` | `lib/api.ts`, `lib/store.tsx`, `lib/format.ts`, `lib/i18n.ts` |
| `frontend/src/components/WhatsAppDispatchModal.tsx` | 1-Click Bilingual (`EN` / `AR`) WhatsApp Shift Dispatch modal (Full Week or Specific Day/Shift) with Copy to Clipboard and `wa.me` share actions. | `WhatsAppDispatchModal` | `lib/api.ts`, `lib/store.tsx`, `lib/i18n.ts` |
| `frontend/src/components/ExecutivePrintReport.tsx` | Ink-friendly A4 light-background (`#ffffff`) printable executive report & preview modal supporting EN LTR and AR RTL (`IBM Plex Sans Arabic`) for Owner Brief, Manager Decision Shield, and 30-Day Backtest Proof. | `ExecutivePrintReport` | `lib/store.tsx`, `lib/format.ts`, `lib/i18n.ts` |
| `frontend/src/components/QuickAddModal.tsx` | Tab 1 modal for fast inline creation/editing of presses, molds, resins, orders, and plant physics. | `QuickAddModal` | `lib/store.tsx` |
| `frontend/src/components/DIBlueprintModal.tsx` | Full-height 4-tab Visual Decision Intelligence Blueprint & Causal Trace Inspector modal with persistent JSON / BPMN 2.0 XML / DMN 1.3 XML export bar and active engine badge (`uem_di_v1` vs. `legacy_cpsat_v1`). | `DIBlueprintModal` | `CausalDiagramView`, `DMNInspectorView`, `BPMNFlowView`, `ArchOntologyView`, `lib/store.tsx`, `lib/api.ts` |
| `frontend/src/components/CausalDiagramView.tsx` | Sub-Tab 1: Interactive 3-column Causal Decision Diagram (`DecisionLever -> IntermediateMetric -> DecisionOutcome`) with inline SVG Bezier connector curves, pathway highlighting, and Causal Attribution Card. | `CausalDiagramView` | `lib/store.tsx`, `lib/format.ts`, `lib/i18n.ts` |
| `frontend/src/components/DMNInspectorView.tsx` | Sub-Tab 2: Expandable OMG DMN 1.3 Decision Table rule matrix viewer with live `FIRED` (`N×`) hit counts, `Show Fired Rules Only` filter, and 1-click DMN 1.3 XML export. | `DMNInspectorView` | `lib/api.ts`, `lib/store.tsx`, `lib/i18n.ts` |
| `frontend/src/components/BPMNFlowView.tsx` | Sub-Tab 3: 4-swimlane OMG BPMN 2.0 workflow visualizer with RTL-safe directional SVG connectors, node execution detail strip, and 1-click BPMN 2.0 XML export. | `BPMNFlowView` | `lib/api.ts`, `lib/store.tsx`, `lib/i18n.ts` |
| `frontend/src/components/ArchOntologyView.tsx` | Sub-Tab 4: Pre-Solve Architecture Validation banner (`GATE-1-STRUCTURAL`, `GATE-2-CAPABILITY`, `GATE-3-POLICY`), 6-Primitive `UEMGraph` summary KPI grid, and collapsible Layer 1 `BusinessOntologyGraph` inspector. | `ArchOntologyView` | `lib/store.tsx`, `lib/i18n.ts` |

#### Frontend Config & Build (`6` files)
| File Path | Purpose | Key Contents |
| :--- | :--- | :--- |
| `frontend/Dockerfile` | Multi-stage Node.js production container image for Next.js frontend. | Docker build spec |
| `frontend/package.json` | Next.js, React, Tailwind, Recharts, Lucide dependencies and `dev`/`build`/`start` scripts. | npm scripts & deps |
| `frontend/next.config.ts` | Next.js configuration (standalone output for Docker). | `nextConfig` |
| `frontend/tsconfig.json` | TypeScript compiler & `@/*` path alias config. | TS compiler options |
| `frontend/postcss.config.mjs` | PostCSS / Tailwind CSS plugin pipeline. | PostCSS config |
| `frontend/next-env.d.ts` | Next.js TypeScript ambient declarations. | Type references |

---

### A.4 File-by-File Inventory — Scripts, Tests & Root Infra (`13` files)

| File Path | Purpose | Key Functions / Contents | Key Dependencies |
| :--- | :--- | :--- | :--- |
| `scripts/sync_docs_to_drive.py` | Dual-mode Google Drive Two-Track in-place sync engine (`gdrive` CLI + Drive API v3) with SHA-256 skip, `--force`, `--dry-run`, and manifest persistence. | `assemble_complete_reference()`, `sync_docs_to_drive()`, `GoogleApiDriveBackend`, `GdriveCliBackend`, `main()` | `docs/.drive-sync-manifest.json` |
| `tests/test_drive_sync.py` | Mocked unit test suite verifying first-sync folder/doc creation, strict in-place `file_id` update on edit, and SHA-256 skip / `--force`. | `MockDriveBackend`, `TestDriveSyncEngine` (3 tests) | `unittest`, `scripts/sync_docs_to_drive.py` |
| `mini-dios-workforce/scripts/run_audit.py` | Automated QA & optimization audit runner (`--quick` and full modes) executing pytest, financial reconciliation checks, and CP-SAT solve-time benchmarks. | `run_pytest()`, `check_financial_reconciliation()`, `build_benchmark_scenarios()`, `run_benchmarks()` | `backend/core/*`, `pytest` |
| `render.yaml` | Render.com single-click Docker Blueprint deploying `mini-dios-plastics-api` (1GB `/data` disk) + `mini-dios-plastics` frontend. | Render service & env-var schema (no secrets) | `backend/Dockerfile`, `frontend/Dockerfile` |
| `mini-dios-workforce/docker-compose.yml` | Local/on-prem Docker Compose stack with persistent `dios-audit-data` volume and `/api/health` check. | `backend` + `frontend` services | `backend/Dockerfile`, `frontend/Dockerfile` |
| `mini-dios-workforce/docker-compose.prod.yml` | Production Docker Compose configuration with hardened restart/proxy/env settings. | Production compose services | `backend/Dockerfile`, `frontend/Dockerfile` |
| `mini-dios-workforce/start.bat` | One-click Windows local demo launcher (locates `.venv` & Node, starts Uvicorn `:8000` + Next.js `:3000`, opens browser). | Windows batch launcher | `backend/main.py`, `frontend/package.json` |
| `mini-dios-workforce/stop.bat` | Cleanly terminates local listeners on ports `8000` and `3000` and closes terminal windows. | Windows batch stopper | `netstat`, `taskkill` |
| `.gitignore` / `mini-dios-workforce/.gitignore` | Blocks `.env`, `credentials.json`, `token.json`, `*.oauth.json`, `*.db`, `node_modules/`, `.next/`, `.venv/`, and build artifacts. | Git ignore rules | — |
| `mini-dios-workforce/README.md`, `AUDIT_AGENT.md`, `AUDIT_REPORT.md` | Repo quickstart and historical QA audit specifications/reports. | Internal repo notes | — |

---

## Section B — Complete Code Update Ledger (Newest First)

### Update 13 — `2026-11-28` • `Uncommitted / Local` • `v1.9 (Visual Decision Intelligence Blueprint & Causal Trace Inspector + Standalone Upgrade Brief)`
- **Title & Why:** Build the visual 4-tab **Decision Intelligence Blueprint & Causal Trace Inspector** (`DIBlueprintModal.tsx`, `CausalDiagramView.tsx`, `DMNInspectorView.tsx`, `BPMNFlowView.tsx`, `ArchOntologyView.tsx`) backed deterministically by `GET /api/di/blueprint` (`?format=json`, `?format=bpmn_xml`, `?format=dmn_xml`) with zero external heavy graph dependencies, wire non-intrusive entry points + lazy state sync in `store.tsx`, and author the one-time standalone briefing document `docs/UEM_DI_SOLVER_UPGRADE_BRIEF.md`.
- **Files Changed:**
  - *Added (Frontend Visual Inspector Components — 5 files):* `mini-dios-workforce/frontend/src/components/DIBlueprintModal.tsx`, `mini-dios-workforce/frontend/src/components/CausalDiagramView.tsx`, `mini-dios-workforce/frontend/src/components/DMNInspectorView.tsx`, `mini-dios-workforce/frontend/src/components/BPMNFlowView.tsx`, `mini-dios-workforce/frontend/src/components/ArchOntologyView.tsx`
  - *Modified (Frontend Store, Types, API, i18n & Entry Points — 8 files):* `mini-dios-workforce/frontend/src/lib/types.ts`, `mini-dios-workforce/frontend/src/lib/api.ts`, `mini-dios-workforce/frontend/src/lib/i18n.ts`, `mini-dios-workforce/frontend/src/lib/store.tsx`, `mini-dios-workforce/frontend/src/components/DecisionLoopStrip.tsx`, `mini-dios-workforce/frontend/src/components/TradeoffConsole.tsx`, `mini-dios-workforce/frontend/src/components/TopBar.tsx`, `mini-dios-workforce/frontend/src/app/page.tsx`
  - *Modified (Backend Blueprint Route, DMN Hit Counts & Tests — 4 files):* `mini-dios-workforce/backend/adapters/plastics.py`, `mini-dios-workforce/backend/api/routes.py`, `mini-dios-workforce/backend/tests/test_uem_di_parity.py`, `mini-dios-workforce/backend/tests/test_copilot.py`
  - *Added / Modified (Docs — 5 files):* `docs/UEM_DI_SOLVER_UPGRADE_BRIEF.md` (Added — one-time standalone brief), `docs/MASTER_USER_GUIDE_AND_MANUAL.md`, `docs/technical/TECHNICAL_REFERENCE.md`, `docs/CHANGELOG.md`, `docs/technical/CODEBASE_AND_UPDATES_LOG.md`
- **Granular Code Changes:**
  - `backend/adapters/plastics.py` & `backend/api/routes.py`: Added deterministic `_compute_dmn_rule_hit_counts()` tallying exact per-rule firing counts (`rule_hit_counts`, `fired`, `hit_count`) across all 4 DMN 1.3 tables against the active workspace and latest solved run; added `Content-Disposition` attachment headers to `?format=bpmn_xml` and `?format=dmn_xml`.
  - `frontend/src/lib/types.ts`, `api.ts`, `store.tsx`, `i18n.ts`: Added TypeScript interfaces (`DIBlueprintResponse`, `DIDecisionLever`, `DIIntermediateMetric`, `DIDecisionOutcome`, `DICausalEdge`, `DIDMNDecisionTable`, `DIBPMNFlowNode`, `DIArchitectureValidationReport`), `fetchDiBlueprintJsonApi()`, lazy blueprint loading on modal open, automatic staleness invalidation whenever `result` updates, and complete bilingual EN/AR strings.
  - `frontend/src/components/DIBlueprintModal.tsx` & 4 sub-views: Implemented the 4-tab visual inspector with SVG Bezier causal pathway highlighting (`CausalDiagramView.tsx`), live fired-rule matrix & filter (`DMNInspectorView.tsx`), 4-swimlane OMG BPMN 2.0 diagram (`BPMNFlowView.tsx`), and 3-Gate Architecture Validation + 6-Primitive UEM KPI cards (`ArchOntologyView.tsx`).
  - `DecisionLoopStrip.tsx`, `TradeoffConsole.tsx`, `TopBar.tsx`, `page.tsx`: Wired non-intrusive triggers in the Decision Loop strip, Tab 3 solver controls, and the Admin Engine Switcher card.
- **Impact & Dependencies:** Zero new npm or Python dependencies; fast Next.js production build (`276 kB` route bundle); 100% deterministic backend truth.
- **Verification Status:** Verified via `npm.cmd run build` (0 TypeScript/ESLint errors), full backend `pytest` suite (`100%` passing), and responsive EN (LTR) / AR (RTL) audit across desktop and mobile viewports.

---

### Update 12 — `2026-11-27` • `Uncommitted / Local` • `v1.8 (5-Layer Decision Intelligence + 6-Primitive UEMGraph Compiler & Two-Way Workforce Coupling)`
- **Title & Why:** Implement the domain-agnostic 5-Layer Decision Intelligence stack (Business Ontology, Pre-Solve Architecture Validator, OMG BPMN 2.0 Process Templates, OMG DMN 1.3 Decision Tables, and Causal Decision Diagram Meta-Model) compiling cleanly into a 6-primitive Universal Execution Model (`UEMGraph` + `uem_compiler.py` + `uem_verify.py`), alongside a dedicated `backend/adapters/plastics.py` reference adapter with two-way bounded workforce-press coupling gated behind `USE_UEM_ENGINE` (default `"false"`).
- **Files Changed:**
  - *Added (Backend Core UEM & DI — 9 files):* `mini-dios-workforce/backend/core/uem.py`, `mini-dios-workforce/backend/core/uem_compiler.py`, `mini-dios-workforce/backend/core/uem_verify.py`, `mini-dios-workforce/backend/core/di/__init__.py`, `mini-dios-workforce/backend/core/di/ontology_meta.py`, `mini-dios-workforce/backend/core/di/arch_validator.py`, `mini-dios-workforce/backend/core/di/bpmn_engine.py`, `mini-dios-workforce/backend/core/di/dmn_engine.py`, `mini-dios-workforce/backend/core/di/decision_meta.py`
  - *Added (Plastics Domain Adapter & Tests — 3 files):* `mini-dios-workforce/backend/adapters/__init__.py`, `mini-dios-workforce/backend/adapters/plastics.py`, `mini-dios-workforce/backend/tests/test_uem_di_parity.py`
  - *Modified (Backend Solver, Auth & API — 6 files):* `mini-dios-workforce/backend/core/ontology.py`, `mini-dios-workforce/backend/core/solver.py`, `mini-dios-workforce/backend/core/auth.py`, `mini-dios-workforce/backend/core/copilot.py`, `mini-dios-workforce/backend/core/ctp.py`, `mini-dios-workforce/backend/core/backtest.py`, `mini-dios-workforce/backend/api/routes.py`
  - *Modified (Frontend Admin Engine Switcher — 5 files):* `mini-dios-workforce/frontend/src/lib/types.ts`, `mini-dios-workforce/frontend/src/lib/api.ts`, `mini-dios-workforce/frontend/src/lib/i18n.ts`, `mini-dios-workforce/frontend/src/lib/store.tsx`, `mini-dios-workforce/frontend/src/components/TopBar.tsx`
  - *Modified (Two-Track Documentation — 5 files):* `docs/MASTER_USER_GUIDE_AND_MANUAL.md`, `docs/MASTER_PLAYBOOK.md`, `docs/technical/TECHNICAL_REFERENCE.md`, `docs/CHANGELOG.md`, `docs/technical/CODEBASE_AND_UPDATES_LOG.md`
- **Granular Code Changes:**
  - `backend/core/uem.py`, `uem_compiler.py`, `uem_verify.py`: Implemented the 6 domain-agnostic mathematical primitives (`ResourceNode`, `ActivityNode`, `TransitionMatrix`, `CumulativeEnvelope`, `SynchronizationGroup`, `ObjectiveTermSpec`), deterministic OR-Tools CP-SAT compiler (`compile_and_solve_uem`), and independent post-solve verifier (`verify_uem_solution` checking `UEM-P1..UEM-P6`).
  - `backend/core/di/*`: Implemented Layer 1 `BusinessOntologyGraph`, Layer 2 `validate_business_architecture` (Structural, Capability & Policy gates), Layer 3 `BPMNProcessTemplate` (with OMG BPMN 2.0 XML export), Layer 4 `DMNDecisionTable` & `DMNRegistry` (S-FEEL unary tests, hit policies, OMG DMN 1.3 XML export), and Layer 5 `CausalDecisionModel` (`DecisionLever -> IntermediateMetric -> DecisionOutcome` pathway tracer).
  - `backend/adapters/plastics.py`: Mapped all plastics domain rules, 4 DMN 1.3 tables (`DMN_BARREL_PURGE_TRANSITION`, `DMN_MOLD_PM_POLICY`, `DMN_FOOD_GRADE_REGRIND_SAFETY`, `DMN_SHIFT_WORKFORCE_HEADCOUNT`), BPMN 2.0 workflow, two-way bounded workforce-press coupling (soft-overflow `shift_capacity_cap` envelopes + max 1 conditional feedback re-solve capped at `<= 2.0s`), and Causal Decision Diagram into `solve_plastics_via_uem()` and `build_plastics_blueprint()`.
  - `backend/core/solver.py`, `auth.py`, & `backend/api/routes.py`: Added `get_effective_engine(sandbox_id)`, `set_sandbox_engine_override()`, `bind_sandbox_engine_context()`, `require_admin_session()`, `GET/POST /api/admin/engine-mode`, `/api/optimize` alias, `active_engine` metadata across all solver/CTP/Backtest/Copilot responses, `optimization_engine` (`"legacy_cpsat_v1"` vs. `"uem_di_v1"`) on `GET /api/health`, and `GET /api/di/blueprint` (`?format=json|bpmn_xml|dmn_xml`).
  - `frontend/src/components/TopBar.tsx`, `lib/store.tsx`, `lib/api.ts`, `lib/types.ts`, `lib/i18n.ts`: Added the Admin-gated **Optimization Engine (Live Demo Switch)** modal (`Legacy CP-SAT` ↔ `UEM + 5-Layer DI` segmented switch, `Live Override` / `Server Default` badge, `Reset to Server Default` link, inline re-solve spinner, and 1-click **JSON Blueprint / BPMN 2.0 XML / DMN 1.3 XML** artifact download buttons) plus the dynamic TopBar engine indicator pill (`OR-Tools CP-SAT • UEM+DI` vs. `OR-Tools CP-SAT • Legacy`).
- **Impact & Dependencies:** Pure Python + existing `ortools` and `pydantic` only; zero new heavyweight dependencies; 100% backward compatibility with legacy solver and Neon PostgreSQL persistence.

### Update 11 — `2026-11-27` • `Uncommitted / Local` • `v1.7 (Neon Cloud Platform Integration — Postgres, Auth, AI Gateway, Functions & Realtime)`
- **Title & Why:** Provision and wire all 5 Neon Cloud Platform services (`postgres`, `auth`, `ai-gateway`, `functions`, `realtime`) on Neon branch `production` (`br-bold-hat-bh4fc43k`, project `broad-pond-82857343`, org `org-nameless-sun-74042046`) via `neon init` + `neon deploy`, and integrate them end-to-end across both the Python FastAPI backend and the Next.js App Router frontend.
- **Files Changed:**
  - *Added (Root & Neon Config — 3 files):* `neon.ts`, `hello.ts`, `package.json`
  - *Added (Backend — 2 files):* `mini-dios-workforce/backend/core/neon_services.py`, `mini-dios-workforce/backend/tests/test_neon_services.py`
  - *Modified (Backend — 6 files):* `mini-dios-workforce/backend/requirements.txt`, `mini-dios-workforce/backend/main.py`, `mini-dios-workforce/backend/core/audit.py`, `mini-dios-workforce/backend/core/auth.py`, `mini-dios-workforce/backend/core/copilot.py`, `mini-dios-workforce/backend/api/routes.py`
  - *Added (Frontend — 3 files):* `mini-dios-workforce/frontend/src/lib/neon.ts`, `mini-dios-workforce/frontend/src/app/api/neon/frontend-status/route.ts`, `mini-dios-workforce/frontend/src/app/api/neon/realtime/route.ts`
  - *Modified (Frontend — 3 files):* `mini-dios-workforce/frontend/package.json`, `mini-dios-workforce/frontend/next.config.ts`, `mini-dios-workforce/frontend/src/components/DecisionCheckpointsDrawer.tsx`
  - *Modified (Docs — 3 files):* `docs/technical/CODEBASE_AND_UPDATES_LOG.md`, `docs/technical/TECHNICAL_REFERENCE.md`, `docs/CHANGELOG.md`
- **Granular Code Changes:**
  - `neon.ts` & `hello.ts`: Declared Neon branch policy with `preview: { realtime: true }`, `auth: true`, `aiGateway: true`, and `functions: { hello: { name: "Hello World", source: "./hello.ts" } }`.
  - `backend/core/neon_services.py`: Created unified loader (`load_neon_env()`) reading root `.env.local` (11 variables pulled by `neon deploy`: `DATABASE_URL`, `DATABASE_URL_UNPOOLED`, `NEON_BRANCH`, `NEON_BRANCH_ID`, `NEON_AUTH_BASE_URL`, `NEON_AUTH_JWKS_URL`, `NEON_FUNCTION_HOST_SUFFIX`, `NEON_AI_GATEWAY_TOKEN`, `NEON_AI_GATEWAY_BASE_URL`, `NEON_REALTIME_URL`, `NEON_REALTIME_SECRET`), plus `derive_database_name()`, `get_neon_function_url()`, `invoke_neon_function()`, `fetch_neon_auth_jwks()`, `verify_neon_auth_jwt()`, `probe_neon_ai_gateway()`, `call_neon_ai_gateway_narration()`, and `get_neon_realtime_config_status()`.
  - `backend/core/audit.py`: Updated `_try_init_postgres()` to automatically select `postgresql+psycopg2://` when `psycopg2-binary` is installed under SQLAlchemy 2.1, and added `probe_database()` querying live Postgres metadata (`current_database()`, `current_user`, `version()`, `saved_workspaces`, and `decision_checkpoints`).
  - `backend/core/auth.py` & `copilot.py` & `api/routes.py`: Wired Neon Auth JWT Bearer verification against `NEON_AUTH_JWKS_URL` in `get_optional_session()`, optional Neon AI Gateway narration in `run_plastics_copilot()` with automatic fallback to Gemini / deterministic offline CP-SAT when AI Gateway credits are 0, and added `GET /api/neon/status` and `GET /api/neon/function/{slug}`.
  - `frontend/next.config.ts`, `src/lib/neon.ts`, `src/app/api/neon/frontend-status/route.ts`, `src/app/api/neon/realtime/route.ts`, & `DecisionCheckpointsDrawer.tsx`: Loaded root `.env.local` in `next.config.ts` with `cleanDistDir: false` and `serverExternalPackages: ["@neon/env", "@neon/config"]`; wired `@neon/env` (`parseEnv`, `functionBaseUrl`), `@neondatabase/serverless` (`neon()`), `@neon/realtime/server` (`createRealtime`, `rawSql`), and `@neon/realtime/client` (`createRealtimeClient`) live WebSocket subscriptions inside `DecisionCheckpointsDrawer.tsx`.
- **Impact & Dependencies:** Added `sqlalchemy>=2.0.30`, `psycopg2-binary>=2.9.9`, `PyJWT>=2.9.0` to Python backend and `@neon/env`, `@neon/realtime`, `@neondatabase/serverless` to Next.js frontend. Zero raw secrets committed.
- **Verification Status:** Verified via `npm run build` (exit code 0), `pytest` (all backend tests passing), and live end-to-end verification across all 5 Neon services (`postgres`, `auth`, `functions`, `realtime`, `ai-gateway`).

---

### Update 10 — `2026-11-27` • `Uncommitted / Local` • `v1.6 (Release v1.4 — Pilot-Ready Persistence, CTP Rush-Order Quoter & Executive Dispatch)`
- **Title & Why:** Implement `v1.4` across backend, frontend, and Two-Track docs: (1) log the parked Pilot-Pull Constraints Backlog into `docs/ROADMAP_AND_BACKLOG.md`, `docs/MASTER_PLAYBOOK.md`, and `docs/technical/TECHNICAL_REFERENCE.md` without bloating the Day-1 solver; (2) add dual-mode `DATABASE_URL` PostgreSQL (`pool_size=3, max_overflow=2, pool_pre_ping=True`) + SQLite fallback persistence with auto-migrated `saved_workspaces`, `pinned_scenarios`, `backtest_runs`, and `decision_checkpoints` plus 1-click rollback from Tab 1; (3) add a strictly non-destructive Capable-to-Promise (CTP) Rush-Order Quoter (`POST /api/quote/ctp` & `CTPQuoterModal.tsx`); and (4) add 1-click bilingual (`EN` / `AR`) print-optimized Executive PDF reports and WhatsApp Shift Dispatch exports (`POST /api/dispatch/whatsapp` & `WhatsAppDispatchModal.tsx`).
- **Files Changed:**
  - *Added (Backend — 3 files):* `mini-dios-workforce/backend/core/ctp.py`, `mini-dios-workforce/backend/core/dispatch.py`, `mini-dios-workforce/backend/tests/test_v14_persistence_ctp_dispatch.py`
  - *Modified (Backend & Infra — 4 files):* `mini-dios-workforce/backend/core/audit.py`, `mini-dios-workforce/backend/api/routes.py`, `mini-dios-workforce/backend/.env.example`, `render.yaml`
  - *Added (Frontend — 4 files):* `mini-dios-workforce/frontend/src/components/DecisionCheckpointsDrawer.tsx`, `mini-dios-workforce/frontend/src/components/CTPQuoterModal.tsx`, `mini-dios-workforce/frontend/src/components/WhatsAppDispatchModal.tsx`, `mini-dios-workforce/frontend/src/components/ExecutivePrintReport.tsx`
  - *Modified (Frontend — 10 files):* `mini-dios-workforce/frontend/src/lib/types.ts`, `mini-dios-workforce/frontend/src/lib/api.ts`, `mini-dios-workforce/frontend/src/lib/i18n.ts`, `mini-dios-workforce/frontend/src/lib/store.tsx`, `mini-dios-workforce/frontend/src/app/page.tsx`, `mini-dios-workforce/frontend/src/app/globals.css`, `mini-dios-workforce/frontend/src/components/ScopeView.tsx`, `mini-dios-workforce/frontend/src/components/TradeoffConsole.tsx`, `mini-dios-workforce/frontend/src/components/ScheduleExportMenu.tsx`, `mini-dios-workforce/frontend/src/components/ExecutiveBriefModal.tsx`, `mini-dios-workforce/frontend/src/components/HistoricalBacktestModal.tsx`
  - *Added / Modified (Docs & Scripts — 7 files):* `docs/ROADMAP_AND_BACKLOG.md` (Added), `docs/MASTER_USER_GUIDE_AND_MANUAL.md`, `docs/MASTER_PLAYBOOK.md`, `docs/technical/TECHNICAL_REFERENCE.md`, `docs/CHANGELOG.md`, `docs/technical/CODEBASE_AND_UPDATES_LOG.md`, `scripts/sync_docs_to_drive.py`
- **Granular Code Changes:**
  - `backend/core/audit.py`: Added `normalize_database_url()` (`postgres://` → `postgresql://` + remote `sslmode=require`), dual-mode `_DbSessionAdapter` supporting bounded SQLAlchemy PostgreSQL pools (`pool_size=3, max_overflow=2, pool_pre_ping=True`) with automatic SQLite fallback (`data/mini_dios.db`), and auto-migrated tables `saved_workspaces`, `pinned_scenarios`, `backtest_runs`, and `decision_checkpoints` (`save_checkpoint`, `list_checkpoints`, `get_checkpoint`).
  - `backend/core/ctp.py`: Implemented `evaluate_ctp_rush_order()` performing an in-memory deep-copied, bounded (`<= 2.2s`) CP-SAT evaluation returning `CTPQuoteResult` (`verdict`, `assigned_press_id`, `scheduled_start_hr`, `scheduled_end_hr`, `slack_or_delay_hrs`, itemized marginal `financial_impact`, `min_breakeven_unit_price`, `bumped_orders`, `risk_score_before`/`after`, and bilingual summaries).
  - `backend/core/dispatch.py`: Implemented `format_whatsapp_shift_dispatch()` generating deterministic EN and AR WhatsApp shift dispatch briefs and `https://wa.me/?text=...` share links.
  - `backend/api/routes.py`: Added `GET /api/checkpoints`, `POST /api/checkpoints`, `POST /api/checkpoints/{checkpoint_id}/restore`, `POST /api/quote/ctp`, `POST /api/quote/ctp/commit`, and `POST /api/dispatch/whatsapp`.
  - `frontend/src/components/*` & `store.tsx`: Built `DecisionCheckpointsDrawer.tsx` (launched from Tab 1 Workspaces panel), `CTPQuoterModal.tsx` (launched from Tab 1 Quick-Add Hub and Tab 3 Trade-Off Console), `WhatsAppDispatchModal.tsx` (launched from Tab 4, Tab 6, and Executive Brief), and `ExecutivePrintReport.tsx` + `@media print` CSS rules.
- **Impact & Dependencies:** Zero breaking changes to existing solver constraints (`HC1–HC6`, `WHC1–WHC5`), auth gate, proxy allowlist, or Excel exports.
- **Verification Status:** Verified via `pytest` (all existing + new `test_v14_persistence_ctp_dispatch.py` tests passing), `npm.cmd run build` (0 TypeScript/ESLint errors), and live responsive audit across `375×812`, `430×932`, `1280×800`, and `1440×900` in EN (LTR) and AR (RTL).

---

### Update 9 — `2026-11-25` • `Uncommitted / Local` • `v1.5.1`
- **Title & Why:** Relocate desktop hosted session controls (`Admin` / plant badge, `Reset Sandbox`, `Sign Out`) to the top brand row of `TopBar.tsx` so `Sign Out` is never clipped at `1280px–1440px`, and eliminate horizontal overflow / left-shift on Tab 4 (`4. Press Gantt & Color Sequence`) across desktop and mobile viewports in both English (LTR) and Arabic (RTL).
- **Files Changed:**
  - *Modified (Frontend — 7 files):* `mini-dios-workforce/frontend/src/components/TopBar.tsx`, `mini-dios-workforce/frontend/src/components/ProductionGanttView.tsx`, `mini-dios-workforce/frontend/src/components/FinancialsView.tsx`, `mini-dios-workforce/frontend/src/components/RiskRadarPanel.tsx`, `mini-dios-workforce/frontend/src/components/DecisionLoopStrip.tsx`, `mini-dios-workforce/frontend/src/app/page.tsx`, `mini-dios-workforce/frontend/src/app/layout.tsx`, `mini-dios-workforce/frontend/src/app/globals.css`
  - *Modified (Docs — 1 file):* `docs/technical/CODEBASE_AND_UPDATES_LOG.md`
- **Granular Code Changes:**
  - `frontend/src/components/TopBar.tsx`: Split the overcrowded desktop header into a clean 2-row CSS Grid (`lg:grid-cols-[minmax(0,1fr)_auto]`): Row 1 places Brand Identity on inline-start and the session utility cluster (`hosted-client-badge`, `Reset Sandbox`, `Sign Out`) on inline-end (top-right in EN LTR, top-left in AR RTL); Row 2 places the operational toggles (`Peak Tariff Avoid`, `Ramadan Shift`, `Auto PM`, `Container & WIP Sync`), `SAR/EGP`, `العربية/EN`, `Ops Copilot`, and `Run CP-SAT Optimization` inside a `min-w-0 flex-wrap gap-2` row while keeping single shared DOM nodes and unpinned `< lg` mobile header + drawer intact.
  - `frontend/src/app/globals.css`, `layout.tsx`, `page.tsx`: Replaced `max-width: 100vw; overflow-x: hidden;` (which conflicted with desktop vertical scrollbar width and sticky headers) with `width: 100%; max-width: 100%; overflow-x: clip;` and added `min-w-0` on the root flex shell, `<main>`, and active tab container.
  - `frontend/src/components/ProductionGanttView.tsx`, `RiskRadarPanel.tsx`, `DecisionLoopStrip.tsx`: Added `w-full max-w-full min-w-0 overflow-hidden` on Gantt, Risk Radar, and Recharts grid cards, added compact export buttons + `flex-wrap gap-2` in the Gantt card header, and constrained the wide timeline (`w-full min-w-[920px]` / `min-w-[1680px]`) and sequence table inside `w-full max-w-full min-w-0 overflow-x-auto` scroll containers so `mx-auto` centering never shifts left.
- **Impact & Dependencies:** Frontend CSS/layout only (zero backend logic, solver math, API route, or state sync changes).
- **Verification Status:** Verified via `npm.cmd run build` (0 TypeScript/ESLint errors) and headless Playwright E2E across all 6 tabs at `1280×800`, `1366×768`, `1440×900`, and `375×812` in both English (LTR) and Arabic (RTL).

---

### Update 8 — `2026-11-25` • `Uncommitted / Local` • `v1.5 (Commercial & Decision Intelligence Upgrade v1.3)`
- **Title & Why:** Implement the 6-feature Commercial & Decision Intelligence Upgrade: (1) 1-Month Historical Backtest / Replay Engine ("The Proof Engine"), (2) 5-Step Process-First Guided Onboarding Wizard (Zero ERP History Required), (3) Finished-Goods Storage & Multi-SKU Export Container Consolidation Coupling (`Container Sync`), (4) Commander-Grade Financial Trade-Off Callout Box in Operations Copilot, (5) Integration-Ready Schedule Export API (`schedule.xlsx`, `schedule.csv`, `erp-payload.json` for Odoo / SAP B1), and (6) Dual-Audience Executive Brief (`Owner / Chairman View` vs. `Plant / Production Manager View` Decision Shield) + Two-Track Commercial Outreach & Modular Licensing Kit.
- **Files Changed:**
  - *Added (Backend — 2 files):* `mini-dios-workforce/backend/core/backtest.py`, `mini-dios-workforce/backend/core/onboarding.py`
  - *Added (Frontend — 3 files):* `mini-dios-workforce/frontend/src/components/HistoricalBacktestModal.tsx`, `mini-dios-workforce/frontend/src/components/GuidedOnboardingModal.tsx`, `mini-dios-workforce/frontend/src/components/ScheduleExportMenu.tsx`
  - *Modified (Backend — 9 files):* `backend/core/ontology.py`, `backend/core/seed.py`, `backend/core/solver.py`, `backend/core/workforce_solver.py`, `backend/core/kpi.py`, `backend/core/risk_radar.py`, `backend/core/copilot.py`, `backend/core/excel_io.py`, `backend/api/routes.py`, `backend/tests/test_api.py`
  - *Modified (Frontend — 13 files):* `frontend/src/lib/types.ts`, `frontend/src/lib/api.ts`, `frontend/src/lib/i18n.ts`, `frontend/src/lib/store.tsx`, `frontend/src/app/page.tsx`, `frontend/src/components/TopBar.tsx`, `frontend/src/components/ScopeView.tsx`, `frontend/src/components/TradeoffConsole.tsx`, `frontend/src/components/ProductionGanttView.tsx`, `frontend/src/components/FinancialsView.tsx`, `frontend/src/components/WorkforceView.tsx`, `frontend/src/components/CopilotDrawer.tsx`, `frontend/src/components/ExecutiveBriefModal.tsx`
  - *Modified (Docs — 6 files):* `docs/MASTER_USER_GUIDE_AND_MANUAL.md`, `docs/MASTER_PLAYBOOK.md`, `docs/templates-and-drafts/hosted-demo-outreach-pilot-kit-en-ar.md`, `docs/technical/TECHNICAL_REFERENCE.md`, `docs/CHANGELOG.md`, `docs/technical/CODEBASE_AND_UPDATES_LOG.md`
- **Granular Code Changes:**
  - `backend/core/backtest.py` & `api/routes.py`: Built 13-column CSV/XLSX historical press-log template generator (`GET /api/backtest/template`), upload parser, 28-order built-in 30-day sample log, and deterministic CP-SAT replay engine (`POST /api/backtest/replay`) returning `HistoricalBacktestReport` (`actual_vs_optimized`, extra sellable units/tons unlocked, 1-month & annualized cash left on the floor, and payback days).
  - `backend/core/onboarding.py` & `api/routes.py`: Built 5-step process-first plant generator (`POST /api/onboarding/generate`) creating tailored presses (with backup press speed factor), molds, resins, multi-SKU export container orders, 2/3-shift workforce, and a 6-item bilingual `"Current Specs Only" Readiness Checklist`.
  - `backend/core/ontology.py`, `seed.py`, `solver.py`, `kpi.py`, `risk_radar.py`: Added `container_group_id` across 4 seeded export container groups (`CNT-RIYADH-01`, `CNT-JEDDAH-02`, `CNT-AUTO-03`, `CNT-CHEM-04`), `fg_storage_capacity_tons` (`22.0t`), `wip_holding_cost_per_ton_day` (`85.0`), and `container_sync_enabled` (`True`); coupled multi-SKU container completion variables (`cg_ship`, `cg_wait`) into CP-SAT `wc_terms`; computed `ContainerGroupSummary`, `warehouse_utilization_pct`, `peak_warehouse_tons`, `trapped_working_capital`, `wip_holding_days`, and `container_wait_delay_hrs`; added `warehouse_congestion` alerts to Risk Radar.
  - `backend/core/copilot.py`: Added `_compute_financial_tradeoff_summary()` and `FinancialTradeoffSummary` (`headline_en`, `headline_ar`, `cost_paid_amount`, `value_protected_amount`, `net_financial_gain`, `is_positive_net`) on `CopilotResult`.
  - `backend/core/excel_io.py` & `api/routes.py`: Added `export_integration_schedule_workbook` (`GET /api/export/schedule.xlsx`), `export_integration_schedule_csv` (`GET /api/export/schedule.csv`), and `export_integration_erp_payload` (`GET /api/export/erp-payload.json`).
  - `frontend/src/components/*` & `lib/*`: Added `HistoricalBacktestModal`, `GuidedOnboardingModal`, `ScheduleExportMenu`, `Container Sync` toggles in `TopBar` and `TradeoffConsole`, Commander-Grade Financial Trade-Off Callout Box in `CopilotDrawer`, and Dual-Audience switcher (`Owner / Chairman View` vs. `Plant / Production Manager View`) in `ExecutiveBriefModal`.
- **Impact & Dependencies:** Full-stack upgrade across Backend solver/API, Frontend Tabs 1–6 & modals, and Two-Track documentation. Zero new environment variables required.
- **Verification Status:** Verified via `pytest` (including `test_v13_backtest_template_and_replay_engine` and `test_v13_guided_onboarding_container_sync_copilot_tradeoff_and_exports`), `npm.cmd run build`, and Google Drive Two-Track in-place sync.

---

### Update 7 — `2026-11-23` • `Uncommitted / Local` • `v1.4.1`
- **Title & Why:** Register dedicated `CODEBASE_AND_UPDATES_LOG.md` ledger in persistent workspace rules and Drive sync engine so every future code change is automatically mapped and logged without manual reminders.
- **Files Changed:**
  - *Added:* `docs/technical/CODEBASE_AND_UPDATES_LOG.md`
  - *Modified:* `.agents/rules/living-docs-sync.md`, `.agents/agents/docs-commercial-architect.md`, `.agents/skills/sync-master-docs/SKILL.md`, `scripts/sync_docs_to_drive.py`, `tests/test_drive_sync.py`, `docs/.drive-sync-manifest.json`
- **Granular Code Changes:**
  - `scripts/sync_docs_to_drive.py`: Registered `codebase_and_updates_log` entry inside `MASTER_DOCS` routed to `folder: "tech"` (`Technical Specs (For Engineers & IT)`).
  - `tests/test_drive_sync.py`: Added `docs/technical/CODEBASE_AND_UPDATES_LOG.md` fixture and updated expected created/updated document counts from `6` to `7`.
  - `.agents/*`: Embedded mandatory post-code-edit Section A + Section B update gate and strict secret-exclusion guardrail.
- **Impact & Dependencies:** Documentation automation & Google Drive sync pipeline only (zero backend/frontend runtime impact).
- **Verification Status:** `python -m unittest tests/test_drive_sync.py -v` (3/3 passed), `python scripts/sync_docs_to_drive.py --dry-run` (all docs synced), zero-secret scan passed.

---

### Update 6 — `2026-11-23 04:04:45 +0200` • Commit `0d9dba1e` • `v1.4`
- **Title & Why:** Synchronize dashboard state in lockstep across Tabs 1–6 and execute multi-lever Risk Radar mitigations in Operations Copilot so clicking *"Mitigate in Copilot"* → *"Apply This Scenario to Dashboard"* visibly resolves risks and updates every coupled view.
- **Files Changed:**
  - *Modified (Backend):* `mini-dios-workforce/backend/core/copilot.py`, `mini-dios-workforce/backend/core/risk_radar.py`, `mini-dios-workforce/backend/core/solver.py`, `mini-dios-workforce/backend/api/routes.py`, `mini-dios-workforce/backend/tests/test_copilot.py`
  - *Modified (Frontend):* `mini-dios-workforce/frontend/src/lib/store.tsx`, `mini-dios-workforce/frontend/src/lib/types.ts`, `mini-dios-workforce/frontend/src/components/CopilotDrawer.tsx`, `mini-dios-workforce/frontend/src/components/DecisionLoopStrip.tsx`, `mini-dios-workforce/frontend/src/components/WorkforceView.tsx`, `mini-dios-workforce/frontend/src/app/page.tsx`
  - *Modified (Docs):* `docs/MASTER_USER_GUIDE_AND_MANUAL.md`, `docs/MASTER_PLAYBOOK.md`, `docs/technical/TECHNICAL_REFERENCE.md`, `docs/CHANGELOG.md`, `docs/.drive-sync-manifest.json`
- **Granular Code Changes:**
  - `backend/core/copilot.py`: Returned unified self-consistent scenario bundle (`plant_state`, `weights`, `toggles`, `production_result`, `workforce_result`, recomputed `risk_radar`); added dataset-level mitigation levers (`auto_staff_workforce_gaps`, `add_relief_workers`, `workforce_overtime_cap_hrs`, `resin_replenishments`, `complete_mold_pm_ids`, `clear_press_breakdowns`).
  - `backend/core/solver.py`: Added 6.5h (`390m`) export port cut-off safety buffer term in Press CP-SAT when `w_otif >= 50` so WIP earliness penalties don't push exports into tight-slack alerts.
  - `backend/core/risk_radar.py`: Balanced per-category Risk Radar score caps (max `68` pts/category) and upgraded all 9 bilingual mitigation prompts to invoke actionable simulation levers rather than read-only inspection.
  - `frontend/src/lib/store.tsx` & `CopilotDrawer.tsx` & `page.tsx`: Atomically committed full Copilot bundles (`dataset` + `config` + `result`), added Before → After Applied Delta Feedback Banner (including physical capacity ceiling explanations), and added signature-based debounced auto-sync for all non-Copilot edits across Tabs 1–6.
  - `backend/tests/test_copilot.py`: Added end-to-end backend tests verifying multi-lever mitigations and Risk Radar delta updates.
- **Impact & Dependencies:** Both Backend and Frontend (Copilot, Risk Radar, Press CP-SAT, global store auto-sync). No new env vars.
- **Verification Status:** `pytest` backend suite (including `test_copilot.py`), Next.js production build, and live Two-Track Drive sync passed.

---

### Update 5 — `2026-11-23 02:46:07 +0200` • Commit `1a597b98`
- **Title & Why:** Enforce Two-Track Documentation Standard separating plain human-friendly business/user docs from a dedicated `TECHNICAL_REFERENCE.md` and `Technical Specs` Google Drive subfolder.
- **Files Changed:**
  - *Added:* `docs/technical/TECHNICAL_REFERENCE.md`
  - *Modified:* `scripts/sync_docs_to_drive.py`, `tests/test_drive_sync.py`, `docs/MASTER_USER_GUIDE_AND_MANUAL.md`, `docs/MASTER_PLAYBOOK.md`, `docs/templates-and-drafts/hosted-demo-outreach-pilot-kit-en-ar.md`, `docs/CHANGELOG.md`, `docs/.drive-sync-manifest.json`
- **Granular Code Changes:**
  - `scripts/sync_docs_to_drive.py`: Added `TECH_SUBFOLDER_NAME`, routed technical docs to `tech_subfolder_id`, and updated `assemble_complete_reference()` to combine only Track A human-friendly docs.
  - `tests/test_drive_sync.py`: Updated mocked backend assertions for 3 Drive folders and 6 synced docs.
- **Impact & Dependencies:** Scripts, unit tests, and Google Drive layout only.
- **Verification Status:** `python -m unittest tests/test_drive_sync.py -v` (3/3 passed), jargon & secret audit returned `0` hits.

---

### Update 4 — `2026-11-23 02:38:45 +0200` • Commit `19ac16cd`
- **Title & Why:** Persist Two-Track Documentation Standard rules into workspace agent and skill definitions.
- **Files Changed:**
  - *Modified:* `.agents/agents/docs-commercial-architect.md`, `.agents/rules/living-docs-sync.md`, `.agents/skills/create-client-doc/SKILL.md`, `.agents/skills/sync-master-docs/SKILL.md`
- **Granular Code Changes:**
  - Updated YAML frontmatter descriptions and enforced the "Normal Human Test" for Track A and dedicated routing for Track B.
- **Impact & Dependencies:** Workspace agent configuration only.
- **Verification Status:** Validated YAML frontmatter across all 4 files.

---

### Update 3 — `2026-11-23 02:34:09 +0200` • Commit `414c87c5` • `v1.3`
- **Title & Why:** Mobile-first responsive UX overhaul for English (LTR) and Arabic (RTL) so factory owners opening Mini-DIOS Plastics on 375px–430px iOS, Android, and WhatsApp in-app browsers get a zero-overflow experience while preserving desktop layouts.
- **Files Changed:**
  - *Modified (Frontend — 25 files):* `globals.css`, `layout.tsx`, `page.tsx`, `TopBar.tsx`, `DecisionLoopStrip.tsx`, `LoginGate.tsx`, `ScopeView.tsx`, `DataStudioView.tsx`, `TradeoffConsole.tsx`, `ProductionGanttView.tsx`, `FinancialsView.tsx`, `WorkforceView.tsx`, `CopilotDrawer.tsx`, `ExecutiveBriefModal.tsx`, `QuickAddModal.tsx`, `PinScenarioButton.tsx`, `RiskRadarPanel.tsx`, `ScenarioComparisonMatrix.tsx`, `studio/PressesEditor.tsx`, `studio/MoldsEditor.tsx`, `studio/ResinsEditor.tsx`, `studio/OrdersEditor.tsx`, `studio/PhysicsEditor.tsx`, `studio/ConfirmDeleteModal.tsx`, `lib/i18n.ts`
  - *Modified (Docs):* `docs/MASTER_USER_GUIDE_AND_MANUAL.md`, `docs/MASTER_PLAYBOOK.md`, `docs/CHANGELOG.md`, `docs/.drive-sync-manifest.json`
- **Granular Code Changes:**
  - `TopBar.tsx`: Condensed `< lg` mobile header with slide-over Controls drawer (Peak Tariff, Ramadan, Auto PM, Executive Brief, session actions) + safe-area-aware sticky bottom action bar pinning `Run CP-SAT Optimization` and `Ops Copilot`.
  - `globals.css` & `layout.tsx` & `LoginGate.tsx`: Adopted `min-h-dvh` / `max-h-[90dvh]` shells, `>= 16px` mobile form fonts (preventing iOS Safari auto-zoom), `>= 44px` touch targets, `24px` range slider thumbs, and `dir="ltr"` on Login Gate passcode input.
  - `studio/*`: Added stacked mobile cards (`< md`) while preserving sticky-first-column desktop tables; pinned modal footers and `92dvh` Copilot input above mobile keyboard.
  - `ProductionGanttView.tsx`, `ScenarioComparisonMatrix.tsx`, `FinancialsView.tsx`, `WorkforceView.tsx`: Added sticky inline-start columns, mobile swipe hints, tap-to-inspect Gantt block selection, and logical CSS properties with zero Arabic letter-spacing.
- **Impact & Dependencies:** Frontend UI only (backend solver and API untouched).
- **Verification Status:** `npm.cmd run build` passed, mobile LTR/RTL viewport checks passed.

---

### Update 2 — `2026-11-23 01:44:04 +0200` • Commit `a8202fd7`
- **Title & Why:** Fix Render.com proxy `HTTP 508 Loop Detected` errors and `handleJson` double response-stream reads during Render Free cold-start wake-ups.
- **Files Changed:**
  - *Added:* `docs/templates-and-drafts/hosted-demo-outreach-pilot-kit-en-ar.md`
  - *Modified:* `mini-dios-workforce/frontend/src/app/api/[...path]/route.ts`, `mini-dios-workforce/frontend/src/lib/api.ts`, `docs/.drive-sync-manifest.json`
- **Granular Code Changes:**
  - `frontend/src/app/api/[...path]/route.ts`: Replaced bulk incoming header forwarding (which leaked Cloudflare/Render edge headers `cdn-loop`, `cf-*`, `render-proxy-ttl`, `via`, `x-forwarded-*`) with an explicit outbound header allowlist (`cookie`, `content-type`, `accept`, `accept-language`, `authorization`, `x-requested-with`); added self-proxy `502` guard if `BACKEND_INTERNAL_URL` matches frontend host; stripped upstream `Domain=` on `Set-Cookie` headers; added single `GET` retry on `502`/`503`/`504`.
  - `frontend/src/lib/api.ts`: Updated `handleJson` to read `res.text()` strictly once before JSON parsing, suppressing raw edge HTML error pages and surfacing clear wake-up messages.
- **Impact & Dependencies:** Frontend API proxy & HTTP client (hosted Render deployment).
- **Verification Status:** Verified clean Render login/API roundtrip with zero `508` loops or stream-read exceptions.

---

### Update 1 — `2026-11-22 20:00:10 +0200` • Commit `b099fc28` • `v1.2` (Initial Hosted Release Baseline)
- **Title & Why:** Initial full-stack hosted release of **Mini-DIOS Plastics** (`v1.2`) featuring deterministic Press + Workforce CP-SAT optimization, Proactive Risk Radar, Autonomous PM, Pin & Compare A/B/C, Hosted Login Gate with multi-prospect sandbox isolation, Docker/Render deployment blueprints, and Google Drive documentation sync.
- **Files Changed:**
  - *Added (`93` files, `28,931` insertions):* Complete `mini-dios-workforce/backend/` (16 core/API files + 9 pytest modules + Docker/env config), complete `mini-dios-workforce/frontend/` (Next.js App Router, 22 components/editors, 5 core libs, Docker/build config), `render.yaml`, `docker-compose.yml`, `docker-compose.prod.yml`, `start.bat`, `stop.bat`, `mini-dios-workforce/scripts/run_audit.py`, `scripts/sync_docs_to_drive.py`, `tests/test_drive_sync.py`, `.agent/*`, `.agents/*`, and initial `docs/*`.
- **Granular Code Changes:**
  - Built Press CP-SAT (`HC1–HC6`, `AddCircuit` + `AddNoOverlap`, `Auto PM`), coupled 5-role Workforce CP-SAT (`WHC1–WHC5`, Ramadan 4×6h), zero-double-counting P&L engine, Proactive Risk Radar, 3-tool Gemini + EN/AR offline Copilot, signed-cookie Login Gate (`core/auth.py` + `LoginGate.tsx`), Pin & Compare A/B/C (`PinScenarioButton.tsx` + `ScenarioComparisonMatrix.tsx`), and dual-mode Drive sync.
- **Impact & Dependencies:** Full stack (Backend, Frontend, Deployment/Env Vars, QA Suite, Docs Automation).
- **Verification Status:** Full backend `pytest` suite, `run_audit.py` benchmarks, `test_drive_sync.py`, Next.js production build, and live Render + Google Drive sync verified.
