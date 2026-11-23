# Mini-DIOS Plastics — Codebase & Code-Update Ledger

> **Track B — Dedicated Engineering Ledger (For Engineers, DevOps & AI Agents)**
> **Scope:** Complete, granular, file-by-file map of what the codebase currently contains (**Section A**) and a chronological, newest-first ledger of every code update ever made (**Section B**).
> **Security Guardrail:** NEVER store `.env` values, API keys, passwords, `AUTH_SECRET_KEY`, `GEMINI_API_KEY`, or private tokens in this file (reference variable names only).
> **Last Synchronized:** 2026-11-23 (`v1.4` • **80** active repository files mapped • **7** code updates logged)

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
    │   │   ├── copilot.py
    │   │   ├── disruptions.py
    │   │   ├── excel_io.py
    │   │   ├── financials.py
    │   │   ├── kpi.py
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
            │   ├── LoginGate.tsx
            │   ├── PinScenarioButton.tsx
            │   ├── ProductionGanttView.tsx
            │   ├── QuickAddModal.tsx
            │   ├── RiskRadarPanel.tsx
            │   ├── ScenarioComparisonMatrix.tsx
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

### A.2 File-by-File Inventory — Backend (`mini-dios-workforce/backend/`, 29 files)

#### Core Application & API (`16` files)
| File Path | Purpose | Key Classes, Functions & Routes | Key Dependencies |
| :--- | :--- | :--- | :--- |
| `backend/main.py` | FastAPI app entrypoint, CORS middleware, and router mounting. | `root()` | `fastapi`, `api/routes.py` |
| `backend/api/__init__.py` | Package marker for API routers. | — | — |
| `backend/api/routes.py` | All REST, auth, sandbox, solver, Copilot, workspace, audit, and Excel endpoints under `/api`. | `GET /health`, `GET /auth/me`, `POST /auth/login`, `POST /auth/logout`, `POST /sandbox/reset`, `GET /demo-data`, `GET /template.xlsx`, `POST /validate`, `POST /solve`, `POST /workforce/solve`, `POST /copilot/ask`, `POST /export-dataset.xlsx`, `POST /export-brief.xlsx`, `GET /audit-log`, `GET /audit-log/{run_id}`, `GET/POST/DELETE /workspaces` | `core/auth.py`, `core/solver.py`, `core/workforce_solver.py`, `core/copilot.py`, `core/excel_io.py`, `core/audit.py` |
| `backend/core/__init__.py` | Re-exports core domain schemas and solver helpers. | — | `core/*` |
| `backend/core/ontology.py` | Industrial plastics Pydantic models, physics helpers, and Pre-Solve Plant Anomaly Validator. | `PressMachine`, `Mold`, `ResinStock`, `ProductionOrder`, `FactoryWorker`, `PlantPhysicsConfig`, `WorkforceConfig`, `SolverConfig`, `ScenarioDisruptions`, `PlantDataset`, `SolveResult`, `validate_plant_data()`, `transition_penalty()`, `order_duration_mins()`, `order_gross_weight_kg()`, `peak_overlap_mins()` | `pydantic` |
| `backend/core/disruptions.py` | Composable scenario engine transforming base `PlantDataset` + `SolverConfig.scenarios` without mutating caller state. | `EffectivePlantState`, `apply_plant_scenarios()` | `core/ontology.py` |
| `backend/core/solver.py` | Deterministic Google OR-Tools CP-SAT parallel-machine scheduler (`HC1–HC6`, `Auto PM`, 6.5h export buffer) + Naive FIFO baseline comparator. | `DatasetValidationError`, `run_fifo_baseline()`, `solve_plant_schedule()` | `ortools.sat.python.cp_model`, `disruptions.py`, `workforce_solver.py`, `financials.py`, `risk_radar.py`, `kpi.py`, `verify.py` |
| `backend/core/verify.py` | Independent zero-tolerance post-solve verifier for all 6 Press hard constraints (`HC1–HC6`). | `verify_hard_constraints()` | `core/ontology.py` |
| `backend/core/workforce_solver.py` | Press-coupled 5-role Workforce CP-SAT roster optimizer (`WHC1–WHC5`), Ramadan 4×6h clamp, Naive Static Rotation baseline, and callout simulator. | `ShiftDef`, `SlotDemand`, `shift_layout()`, `derive_demand()`, `evaluate_roster()`, `verify_workforce()`, `build_naive_roster()`, `solve_workforce()`, `solve_workforce_with_callouts()` | `ortools.sat.python.cp_model`, `core/ontology.py` |
| `backend/core/kpi.py` | Deterministic KPI evaluator, Gantt block builder, resin/press summaries, and Baseline vs. CP-SAT ROI scorecard. | `build_schedule_plan()`, `build_scorecard()` | `core/ontology.py` |
| `backend/core/financials.py` | Zero-double-counting weekly P&L reconciliation, monthly/annual projections, unlocked capacity value, and per-order margin table. | `compute_financial_report()` | `core/ontology.py` |
| `backend/core/risk_radar.py` | Deterministic Proactive Delay & Bottleneck Risk Radar (balanced per-category score caps, resin silo depletion clock, mold/press/shift alerts, 9 bilingual mitigation prompts). | `compute_risk_radar()` | `core/ontology.py` |
| `backend/core/copilot.py` | Unlimited Composable Operations Copilot (`google-genai` `gemini-4-hydrogen` + EN/AR deterministic offline parser) returning unified scenario bundles with multi-lever dataset mitigations. | `CopilotResult`, `StrategyComparison`, `BottleneckInsight`, `execute_simulate_plant_scenario()`, `execute_inspect_bottleneck()`, `execute_compare_two_strategies()`, `run_offline_composable_copilot()`, `run_plastics_copilot()` | `google-genai`, `solver.py`, `workforce_solver.py`, `financials.py`, `risk_radar.py` |
| `backend/core/excel_io.py` | 4-tab Excel workbook generator (`Presses`, `Molds`, `Resin_Inventory`, `Production_Orders`), parser, and Executive Brief `.xlsx` exporter. | `build_template_workbook()`, `parse_workbook_bytes()`, `export_brief_workbook()` | `openpyxl`, `core/ontology.py` |
| `backend/core/audit.py` | SQLite persistence layer for SHA-256 audit runs and multi-tenant/sandboxed plant workspaces. | `AuditStore` | `sqlite3`, `core/ontology.py` |
| `backend/core/auth.py` | Signed HMAC cookie sessions, multi-client passcode parsing (`DEMO_ACCESS_CODES`), sandbox namespace isolation, and per-hour Copilot quota shield. | `AuthSession`, `is_auth_enabled()`, `verify_passcode()`, `sign_session_token()`, `verify_session_token()`, `set_session_cookie()`, `clear_session_cookie()` | `hmac`, `hashlib`, `fastapi` |
| `backend/core/seed.py` | Seeded Delta & Riyadh Polymer Packaging Plant (6 presses, 10 molds, 5 resins, 24 orders, 28 floor workers). | `default_config()`, `demo_workers()`, `demo_dataset()` | `core/ontology.py` |

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

### A.3 File-by-File Inventory — Frontend (`mini-dios-workforce/frontend/`, 38 files)

#### App Router, Proxy & Core Libraries (`10` files)
| File Path | Purpose | Key Exports / Hooks | Key Dependencies |
| :--- | :--- | :--- | :--- |
| `frontend/src/app/layout.tsx` | Root Next.js layout, metadata, mobile viewport config (`viewport-fit=cover`), and `AppProvider` wrapper. | `viewport`, `metadata`, `RootLayout` | `globals.css`, `lib/store.tsx` |
| `frontend/src/app/page.tsx` | Main command center shell routing between `LoginGate`, `TopBar`, `DecisionLoopStrip`, Applied Delta Banner, Tabs 1–6, `QuickAddModal`, `ExecutiveBriefModal`, and `CopilotDrawer`. | `HomePage` | All top-level views & modals, `lib/store.tsx` |
| `frontend/src/app/api/[...path]/route.ts` | Server-side Next.js API catch-all proxy to `BACKEND_INTERNAL_URL` with explicit header allowlist (prevents Render HTTP 508 loop), self-proxy guard, cookie `Domain=` stripping, and single GET retry on 502/503/504 cold starts. | `dynamic`, `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `OPTIONS` | `next/server` |
| `frontend/src/app/globals.css` | Tailwind CSS base, dark theme tokens, hatched Gantt patterns, Peak/Iftar bands, 24px mobile slider thumbs, safe-area padding, and RTL typography rules. | CSS utility classes | Tailwind CSS |
| `frontend/src/app/icon.svg` | Browser favicon SVG for Mini-DIOS Plastics. | SVG asset | — |
| `frontend/src/lib/store.tsx` | Global React state context: workspaces, dataset CRUD, solver config, atomic Copilot bundle commit, signature-based debounced auto-sync across Tabs 1–6, Pin & Compare A/B/C slots, currency/lang, and auth session. | `AppProvider`, `useApp`, `QuickModalType`, `StudioSubTab`, `DEFAULT_PHYSICS`, `DEFAULT_WORKFORCE` | `lib/api.ts`, `lib/types.ts` |
| `frontend/src/lib/api.ts` | Typed HTTP client (`handleJson` single-read stream parser) for auth, validation, solve, workforce solve, Copilot, workspaces, and audit endpoints. | `API_BASE`, `fetchAuthMe`, `loginWithPasscodeApi`, `runSolveApi`, `runWorkforceSolveApi`, `askCopilotApi`, `listWorkspacesApi`, `saveWorkspaceApi` (+13) | `lib/types.ts` |
| `frontend/src/lib/types.ts` | Complete TypeScript domain interfaces mirroring `backend/core/ontology.py`, `copilot.py`, and `auth.py`. | `PlantDataset`, `SolverConfig`, `SolveResult`, `WorkforceResult`, `FinancialReport`, `RiskRadarReport`, `CopilotResult`, `PinnedScenario` (+60) | — |
| `frontend/src/lib/i18n.ts` | Complete English (LTR) and Arabic (RTL) dictionary for all UI labels, roles, shifts, colors, constraints, and Risk Radar copy. | `COPY`, `WORKER_ROLE_LABELS`, `SHIFT_LABELS`, `CONSTRAINT_LABELS`, `WORKFORCE_CONSTRAINT_LABELS`, `COLOR_LABELS`, `DAY_NAMES_I18N` | `lib/types.ts` |
| `frontend/src/lib/format.ts` | Deterministic SAR ↔ EGP currency conversion and number/money formatting helpers. | `convertCurrency`, `formatMoney`, `formatNumber` | `lib/types.ts` |

#### Views, Modals & Studio Editors (`22` files)
| File Path | Purpose | Key Exports | Key Dependencies |
| :--- | :--- | :--- | :--- |
| `frontend/src/components/LoginGate.tsx` | Hosted executive access gate supporting multi-client passcodes (`ALEX-2026`, `KSA-2026`, `DIOS-2026`) and optional instant demo. | `LoginGate` | `lib/store.tsx`, `lib/i18n.ts` |
| `frontend/src/components/TopBar.tsx` | Responsive header (desktop bar + mobile compact bar with slide-over Controls drawer + sticky bottom action bar for Run Optimization & Ops Copilot). | `TopBar` | `lib/store.tsx`, `lib/i18n.ts` |
| `frontend/src/components/DecisionLoopStrip.tsx` | 5-stage horizontal snap-scroll strip (`1. Model → 2. Sense → 3. Optimize → 4. Command → 5. Adapt`) with live risk, status, constraint, and savings badges. | `DecisionLoopStrip` | `lib/store.tsx`, `lib/i18n.ts` |
| `frontend/src/components/ScopeView.tsx` | Tab 1 (`Plant Scope & Readiness`): Saved Workspaces, Quick-Add Hub, 6 clickable KPI pills, Risk Radar, inline Resin & Mold PM health, Pre-Solve Diagnostics, Press Fleet. | `ScopeView` | `RiskRadarPanel`, `lib/store.tsx` |
| `frontend/src/components/RiskRadarPanel.tsx` | Full & compact Risk Radar cards displaying `Plant Risk Score`, financial exposure, Resin Silo Depletion Clock, and one-click `Mitigate in Copilot` / `Inspect` actions. | `RiskRadarPanel` | `lib/store.tsx`, `lib/format.ts` |
| `frontend/src/components/DataStudioView.tsx` | Tab 2 (`Plant Data & Parameters`): Sticky action bar, validation pill, and 5 Studio sub-tabs. | `DataStudioView` | `studio/*`, `lib/store.tsx` |
| `frontend/src/components/studio/PressesEditor.tsx` | Tab 2A CRUD editor for presses (stacked mobile cards + desktop table). | `PressesEditor` | `ConfirmDeleteModal`, `lib/store.tsx` |
| `frontend/src/components/studio/MoldsEditor.tsx` | Tab 2B CRUD editor for molds, compatibility, cycle times, and shot intervals. | `MoldsEditor` | `ConfirmDeleteModal`, `lib/store.tsx` |
| `frontend/src/components/studio/ResinsEditor.tsx` | Tab 2C CRUD editor for resin inventory, pricing, drying floors, and melt temps. | `ResinsEditor` | `ConfirmDeleteModal`, `lib/store.tsx` |
| `frontend/src/components/studio/OrdersEditor.tsx` | Tab 2D CRUD editor for production orders with search/filter and live run-time/weight estimates. | `OrdersEditor` | `ConfirmDeleteModal`, `lib/store.tsx` |
| `frontend/src/components/studio/PhysicsEditor.tsx` | Tab 2E editor for purge physics, tariffs, peak windows, currency/FX, horizon, overhead, and solver time cap. | `PhysicsEditor` | `lib/store.tsx` |
| `frontend/src/components/studio/ConfirmDeleteModal.tsx` | Referential-safety confirmation modal warning of impacted orders/molds before deleting a press, mold, or resin. | `ConfirmDeleteModal` | `lib/i18n.ts` |
| `frontend/src/components/TradeoffConsole.tsx` | Tab 3 (`Trade-Off & Scenario Composer`): 4 KPI delta cards, 4 executive sliders + presets, composable disruption builder, `PinScenarioButton`, `ScenarioComparisonMatrix`, `6/6` HC verification, and audit history. | `TradeoffConsole` | `PinScenarioButton`, `ScenarioComparisonMatrix`, `lib/store.tsx` |
| `frontend/src/components/PinScenarioButton.tsx` | One-click button/popover to pin the active schedule into Comparison Slot A, B, or C. | `PinScenarioButton` | `lib/store.tsx` |
| `frontend/src/components/ScenarioComparisonMatrix.tsx` | Side-by-side A vs. B vs. C boardroom matrix with exact deltas, `Best` badges, and `Promote to Active Plan`. | `ScenarioComparisonMatrix` | `lib/store.tsx`, `lib/format.ts` |
| `frontend/src/components/ProductionGanttView.tsx` | Tab 4 (`Press Gantt & Color Sequence`): 168h pigment-colored Gantt, FIFO vs. CP-SAT switch, Peak/Iftar bands, tap-to-inspect mobile support, resin/scrap charts, and sequence audit table. | `ProductionGanttView` | `RiskRadarPanel`, `recharts`, `lib/store.tsx` |
| `frontend/src/components/FinancialsView.tsx` | Tab 5 (`Revenue & Savings`): 5 financial KPI cards, inline assumptions, FIFO vs. CP-SAT P&L reconciliation, per-order profitability with inline `Unit Selling Price` editing, and `ScenarioComparisonMatrix`. | `FinancialsView` | `PinScenarioButton`, `ScenarioComparisonMatrix`, `recharts`, `lib/store.tsx` |
| `frontend/src/components/WorkforceView.tsx` | Tab 6 (`Workforce & Shifts`): 5 workforce KPI cards, 3 objective sliders, sick-callout chips, Roster Matrix, Demand vs. Scheduled Coverage Chart, Worker Directory CRUD, and `5/5 WHC` verification. | `WorkforceView` | `recharts`, `lib/store.tsx` |
| `frontend/src/components/CopilotDrawer.tsx` | Slide-over bilingual Operations Copilot drawer (`92dvh` mobile-safe) with starter chips, Before → After Applied Delta banner, Bottleneck/Comparison cards, `Pin for Comparison`, and `Apply This Scenario to Dashboard`. | `CopilotDrawer` | `lib/api.ts`, `lib/store.tsx` |
| `frontend/src/components/ExecutiveBriefModal.tsx` | In-dashboard boardroom ROI scorecard modal (`6/6` verified constraints + Resin Purge Audit, zero file transfers). | `ExecutiveBriefModal` | `lib/store.tsx`, `lib/format.ts` |
| `frontend/src/components/QuickAddModal.tsx` | Tab 1 modal for fast inline creation/editing of presses, molds, resins, orders, and plant physics. | `QuickAddModal` | `lib/store.tsx` |

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
