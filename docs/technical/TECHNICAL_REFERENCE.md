# Mini-DIOS Plastics — Technical Reference & Engineering Architecture

> **Track B — Dedicated Technical Documentation (For Engineers, DevOps, IT & AI Agents)**
> **Repository:** `mini-dios-workforce/` • **Last Synchronized:** 2026-11-23 (`v1.2`)
> **Security Note:** This document lists environment variable *names* and architectural specs only. It NEVER stores real API keys, passwords, OAuth tokens, or `.env` values.

---

## Table of Contents
1. [System Architecture & Tech Stack](#1-system-architecture--tech-stack)
2. [Repository & Module Map](#2-repository--module-map)
3. [Press Scheduling CP-SAT Formulation (`HC1–HC6`)](#3-press-scheduling-cp-sat-formulation-hc1hc6)
4. [Workforce CP-SAT Formulation (`WHC1–WHC5`)](#4-workforce-cp-sat-formulation-whc1whc5)
5. [Deterministic Financial & Risk Radar Formulas](#5-deterministic-financial--risk-radar-formulas)
6. [Operations Copilot 3-Tool Architecture (Live Gemini & Air-Gapped Offline)](#6-operations-copilot-3-tool-architecture-live-gemini--air-gapped-offline)
7. [REST & Excel Integration API Endpoints](#7-rest--excel-integration-api-endpoints)
8. [Authentication, Proxy Routing, CORS & Storage](#8-authentication-proxy-routing-cors--storage)
9. [Environment Variables, Local Launch, Docker & Render Deployment](#9-environment-variables-local-launch-docker--render-deployment)
10. [QA, Testing, Audit & Drive Sync Commands](#10-qa-testing-audit--drive-sync-commands)

---

## 1. System Architecture & Tech Stack

| Layer | Technology | Responsibility |
| :--- | :--- | :--- |
| **Frontend UI** | Next.js (App Router), React, TypeScript, Tailwind CSS, Recharts, Lucide Icons | 6-tab Executive Command Center, Bilingual EN (LTR) / AR (RTL), SAR / EGP live currency conversion, `LoginGate`, `Pin & Compare A/B/C`, `CopilotDrawer`, `ExecutiveBriefModal`. |
| **Backend API** | Python 3.12, FastAPI, Pydantic v2, Uvicorn | Validation, scenario composition, CP-SAT orchestration, Excel `.xlsx` import/export bridge, Copilot tool router, SQLite persistence. |
| **Optimization Engine** | Google OR-Tools CP-SAT (`cp_model`) | 100% deterministic integer/constraint programming (`AddCircuit` + `AddNoOverlap`) for parallel-machine press scheduling and role-decomposed floor workforce rostering. |
| **Copilot Orchestrator** | `google-genai` SDK (`gemini-4-hydrogen`, `thinking_level="low"`, 15s `HttpOptions` timeout) + Deterministic Offline Parser | Zero-LLM-Arithmetic architecture: LLM only constructs structured tool arguments and narrates exact Python-computed results; fails over seamlessly to local EN/AR parser when offline. |
| **Persistence** | SQLite (`audit.db`, configurable via `DIOS_AUDIT_DB`) | Persists saved plant workspaces, cryptographic SHA-256 audit logs (`PL-XXXXXXXX`), and isolated guest demo sessions. |

---

## 2. Repository & Module Map

```text
DIOs/
├── render.yaml                          # Render.com single-click Docker Blueprint (API + Frontend)
├── scripts/
│   └── sync_docs_to_drive.py            # Dual-mode Google Drive in-place sync engine (gdrive CLI + Drive API v3)
├── tests/
│   └── test_drive_sync.py               # Mocked unit tests for Drive sync manifest & in-place updates
├── docs/
│   ├── MASTER_USER_GUIDE_AND_MANUAL.md  # Track A: Human-friendly user manual
│   ├── MASTER_PLAYBOOK.md               # Track A: Human-friendly commercial playbook
│   ├── templates-and-drafts/            # Track A: Human-friendly client outreach & proposals
│   ├── technical/TECHNICAL_REFERENCE.md # Track B: This file
│   ├── CHANGELOG.md                     # Track B: Dated engineering & documentation log
│   └── .drive-sync-manifest.json        # Canonical Google Drive folder/file IDs & SHA-256 hashes
└── mini-dios-workforce/
    ├── start.bat / stop.bat             # Windows local dev launcher & port 8000/3000 cleaner
    ├── docker-compose.yml               # On-prem Docker stack (backend + frontend + persistent volume)
    ├── backend/
    │   ├── main.py                      # FastAPI app entrypoint & CORS/auth middleware
    │   ├── api/routes.py                # REST & Excel API endpoints (/api/*)
    │   ├── core/
    │   │   ├── ontology.py              # Pydantic models, physics helpers, Pre-Solve Validator
    │   │   ├── disruptions.py           # Composable scenario engine (breakdowns, shocks, rush orders, PM)
    │   │   ├── solver.py                # Press CP-SAT solver + Naive FIFO Baseline comparator
    │   │   ├── verify.py                # Independent HC1–HC6 post-solve verifier
    │   │   ├── workforce_solver.py      # Coupled 5-role Workforce CP-SAT + Naive Static Rotation + WHC1–WHC5
    │   │   ├── kpi.py                   # Schedule KPIs, Gantt block builder, ROI scorecard
    │   │   ├── financials.py            # Zero-double-counting P&L reconciliation & per-order profitability
    │   │   ├── risk_radar.py            # Deterministic Proactive Delay & Bottleneck Risk Radar
    │   │   ├── copilot.py               # 3-tool Gemini + EN/AR deterministic offline parser
    │   │   ├── excel_io.py              # 4-tab Excel workbook parser & executive brief exporter
    │   │   ├── audit.py                 # SQLite AuditStore (runs & workspaces)
    │   │   └── seed.py                  # Seeded 6-press Delta & Riyadh demo dataset (24 orders, 28 workers)
    │   └── tests/                       # Pytest suite (solver, workforce, financials, validator, copilot, api, risk_radar)
    └── frontend/src/
        ├── lib/                         # api.ts, format.ts, i18n.ts, store.tsx, types.ts
        └── components/                  # LoginGate, TopBar, DecisionLoopStrip, ScopeView, DataStudioView,
                                         # TradeoffConsole, ProductionGanttView, FinancialsView, WorkforceView,
                                         # RiskRadarPanel, ExecutiveBriefModal, CopilotDrawer, studio/*
```

---

## 3. Press Scheduling CP-SAT Formulation (`HC1–HC6`)

Implemented in `backend/core/solver.py` and independently verified post-solve in `backend/core/verify.py`.

### Horizon & Physics Constants (`backend/core/ontology.py`)
- Default weekly horizon: `168h` (`10,080` min; configurable `24–336h`). Extended tail: `264h` (`15,840` min) so late orders remain schedulable and accurately penalized.
- `order_shots(order, mold) = max(1, ceil(quantity_pcs / cavities))`
- `order_duration_mins(order, mold) = max(30, ceil((shots * cycle_time_sec) / 60))`
- `order_gross_weight_kg(order, mold) = round(((qty * part_weight_g) / 1000) * (1.005 if hot_runner else 1.03), 2)`
- Color pigment ranks: `Natural=1, White=2, Yellow=3, Blue=4, Red=5, Black=6`.
- Compatible polyolefin family: `POLYOLEFIN_RESINS = {"PP", "HDPE", "LDPE"}`. Switching across families (`PET`, `ABS`, `PVC`) triggers incompatible-resin full-barrel purge (default `180 min / 48 kg`).
- Default purge physics (`PlantPhysicsConfig`): Light→Dark `25m / 4.0kg`; Dark→Light `135m / 32.0kg`; Incompatible resin `180m / 48.0kg`; Electricity tariff `0.32 SAR/kWh`; Peak window `13:00–17:00` (`1.4x`); Ramadan shift `6h` (`18:00–20:00` Iftar changeover blackout, `1.15x` labor multiplier); `fx_egp_per_sar = 13.0`.

### Hard Constraints (`HC1–HC6`)
- **`HC1` — Mold–Press Compatibility & Hot-Runner Fit:** Scheduled order runs on exactly one `active` press in `mold.compatible_machines`, with `press.supports_hot_runner == True` when `mold.is_hot_runner == True`.
- **`HC2` — No Press Overlap & Breakdown/Downtime Exclusion:** `AddNoOverlap` per press across all busy intervals `[start - setup, end)` and all downtime/breakdown windows. When `ramadan_shift_mode=True`, setup intervals also `AddNoOverlap` daily `18:00–20:00` blackouts.
- **`HC3` — Physical Mold Exclusivity Across Presses:** `AddNoOverlap` per physical mold across all presses.
- **`HC4` — Asymmetric Changeover & Color/Resin Purge Sequencing:** `AddCircuit` per press enforces exact sequence-dependent `setup_mins` and `purge_scrap_kg` via `transition_penalty()`.
- **`HC5` — Resin Pre-Drying Floor, Food-Grade Regrind Safety & Inventory Cap:** `start_min >= resin.drying_lead_time_hrs * 60`; orders with `max_regrind_pct == 0` strictly receive `0 kg` regrind even under `allow_regrind_override_pct`; weekly `virgin_used + purge_scrap <= virgin_available_kg` and `regrind_used <= regrind_available_kg` (modeled at `0.1 kg` integer precision).
- **`HC6` — Mold Preventive Maintenance (PM) Block:** Triggered when `shot_utilization_pct >= 95%`, manual `MoldPmLock`, or projected mid-week shots `> maintenance_interval_shots` under `autonomous_pm_window=True`. In `Auto PM` mode, CP-SAT floats the PM block up to `75%` of horizon while enforcing `shots_before_pm <= maintenance_interval_shots - current_shots`.

### Weighted Multi-Objective (SAR Cents)
```text
Minimize:
  (3 * w_changeover_scrap + 1) * (Purge_Resin_Cost + Changeover_Downtime_Cost_at_250_SAR_hr)
+ (3 * w_otif             + 1) * (Tardiness_Penalty * (1.5 if is_export else 1.0) + Unscheduled_Penalty)
+ (2 * w_energy_cost      + 1) * (Press_Energy_Cost + Peak_Tariff_Surcharge + Press_Operating_Cost)
+ (2 * w_working_capital  + 1) * (Virgin_&_Regrind_Material_Spend + Early_WIP_Holding_Cost)
+ pm_tiebreak_expr
```
Warm-started from `run_fifo_baseline()`. Audit hashes: SHA-256 over canonical JSON of inputs (`inputs_sha256`) and scheduled job tuples (`schedule_sha256`).

---

## 4. Workforce CP-SAT Formulation (`WHC1–WHC5`)

Implemented in `backend/core/workforce_solver.py` (exact role-by-role decomposition across `Press_Operator`, `Mold_Technician`, `QC_Inspector`, `Material_Handler`, `Shift_Supervisor`) and independently verified via `verify_workforce()`.

- **Shift Layouts:**
  - Standard (8h): `Morning 06–14`, `Afternoon 14–22`, `Night 22–06(+1)`.
  - Ramadan (`ramadan_shift_mode=True` or `shift_length_hrs=6`): `Night 00–06`, `Morning 06–12`, `Afternoon 12–18`, `Evening 18–24`; weekly caps clamped to `36h max / 30h standard`.
- **Coupled Demand Derivation (`derive_demand`):**
  - `Press_Operator`: `ceil(active_presses / presses_per_operator)` (default `2`) + press certification check.
  - `Shift_Supervisor`: `1` per active operating shift.
  - `QC_Inspector` & `Material_Handler`: `1` per active shift, `+1` when `active_presses >= 4` or hygroscopic resin (`PET`/`ABS`) is running.
  - `Mold_Technician`: `1` for `1–2` changeovers/PMs in slot; `2` for `>= 3` (`2x` gap criticality).
- **Hard Constraints (`WHC1–WHC5`):**
  - `WHC1`: Role & press certification match.
  - `WHC2`: Weekly hour cap & Ramadan 6h/36h clamp.
  - `WHC3`: Mandatory inter-shift rest gap (`>= min_rest_hours`, default `11h`).
  - `WHC4`: Zero scheduling on `sick`, `on_leave`, `approved_leave_days`, or Copilot callout days + `>= min_consecutive_days_off` (default `1`) consecutive days off per 7-day cycle.
  - `WHC5`: Max 1 shift per worker per calendar day.
- **Objective (SAR Cents):** `Minimize(w_labor_cost * (Regular_Pay + OT_Premium) + w_coverage * (Headcount_Gaps + Cert_Gaps) + w_fairness * (Pref_Mismatches + Night_Shift_Spread))`.

---

## 5. Deterministic Financial & Risk Radar Formulas

### Financial Reconciliation (`backend/core/financials.py`)
- `Recognized Revenue = sum(qty_pcs * unit_selling_price * (1 - discount_pct / 100))` for scheduled orders.
- `Net Purge Scrap Cost = Gross Purge Scrap Cost * (1 - scrap_regrind_recovery_pct / 100)`.
- `Variable Production Cost = Direct Resin + Net Purge Scrap + (Energy + Press Operating) + Late Penalties + WIP Holding + Direct Floor Labor & Overtime`.
- `Gross Profit = Recognized Revenue - Variable Production Cost`.
- `Net Operating Profit = Gross Profit - Weekly Fixed Overhead`.
- `Total Weekly Savings = (Baseline Total Operating Cost - Optimized Total Operating Cost) + (Optimized Recognized Revenue - Baseline Recognized Revenue)`.
- `Monthly Projected Savings = Total Weekly Savings * 4.33`; `Annual Projected Savings = Total Weekly Savings * annual_operating_weeks` (default `50`).
- `Unlocked Capacity Revenue Potential = max(0, Baseline_Changeover_Hrs - Opt_Changeover_Hrs) * (Recognized_Revenue / Opt_Run_Hours)`.

### Proactive Risk Radar (`backend/core/risk_radar.py`)
Evaluates 5 deterministic risk categories and computes `overall_risk_score = min(100, critical * 25 + elevated * 10 + watch * 3)`:
1. Unscheduled / late / tight-slack (`< 6h` export, `< 4h` domestic) orders with exact currency exposure.
2. Minute-by-minute resin silo depletion clock (`projected_stockout_hr` at `>= 98%` draw, remaining coverage hours).
3. High-utilization press choke points (`>= 82%` elevated, `>= 92%` critical).
4. Post-week mold shot-limit trajectory (`>= 90%` watch, `>= 95%` elevated, `>= 100%` critical).
5. Workforce understaffed slots and zero-buffer high-load shift fragility.

---

## 6. Operations Copilot 3-Tool Architecture (Live Gemini & Air-Gapped Offline)

Implemented in `backend/core/copilot.py`, executed inside `asyncio.to_thread()` in `routes.py`:
1. **`simulate_plant_scenario`**: Merges breakdowns, resin shocks, regrind overrides, mold PM locks, rush orders, operational toggles, weights, and `worker_callouts`; runs CP-SAT (`<= 2.5s` interactive cap; labor-only fast path when only workforce args change).
2. **`inspect_bottleneck`**: Deterministic audit of any press, mold, order, resin, or plant-wide choke point.
3. **`compare_two_strategies`**: Runs CP-SAT twice under two competing executive weight profiles and returns a structured comparison table.
- **Failover:** If `GEMINI_API_KEY` is blank, `OFFLINE_MODE=true`, or Gemini times out (>15s), routes transparently to `run_offline_composable_copilot()` (bilingual EN/AR parser executing the exact same 3 CP-SAT tools).

---

## 7. REST & Excel Integration API Endpoints

Defined in `backend/api/routes.py` under prefix `/api`:
- `GET /api/health` — Service status & OR-Tools version.
- `GET /api/demo-data` — Seeded `PlantDataset` + default `SolverConfig`.
- `POST /api/validate` — Accepts JSON (`{dataset, config?}`) or `multipart/form-data` 4-tab `.xlsx` workbook (`Presses`, `Molds`, `Resin_Inventory`, `Production_Orders`).
- `POST /api/solve` — Full Press + Workforce CP-SAT + Financials + Risk Radar + SQLite audit save.
- `POST /api/workforce/solve` — Fast labor-only re-solve against an existing Press Gantt (+ recomputed P&L & Risk Radar).
- `POST /api/copilot/ask` — Executes Copilot 3-tool pipeline.
- `GET/POST /api/workspaces`, `GET/DELETE /api/workspaces/{workspace_id}` — Saved plant workspace CRUD.
- `GET /api/audit-log`, `GET /api/audit-log/{run_id}` — Cryptographic audit trail retrieval.
- `GET /api/template.xlsx`, `POST /api/export-dataset.xlsx`, `POST /api/export-brief.xlsx` — Programmatic Excel bridge.

---

## 8. Authentication, Proxy Routing, CORS & Storage

- **Hosted Access Gate (`LoginGate.tsx` + backend auth):** Enabled via `AUTH_ENABLED=true`. Signed session cookies use `AUTH_SECRET_KEY`. Multi-client passcodes are configured via `DEMO_ACCESS_CODES` (e.g., `Executive Demo:DIOS-2026,Alexandria Plant:ALEX-2026,Riyadh Plant:KSA-2026`).
- **Frontend → Backend Proxy:** In hosted Render deployment, `NEXT_PUBLIC_API_BASE=""` so Next.js proxies `/api/*` internally to `BACKEND_INTERNAL_URL` (`fromService: mini-dios-plastics-api`), avoiding cross-origin cookie issues.
- **CORS:** Controlled via `ALLOWED_ORIGINS` / `CORS_ORIGINS` (e.g., `https://mini-dios-plastics.onrender.com` in production; `http://localhost:3000,http://127.0.0.1:3000` in local Docker).
- **Storage:** Persistent SQLite at `/data/audit.db` (`dios-sqlite-data` 1GB Render disk or `dios-audit-data` Docker volume).

---

## 9. Environment Variables, Local Launch, Docker & Render Deployment

### Environment Variable Names (Never Store Real Values in Docs)
- **Backend (`backend/.env` / Render API service):** `PORT`, `DIOS_AUDIT_DB`, `AUTH_ENABLED`, `AUTH_SECRET_KEY`, `DEMO_ACCESS_CODES`, `ADMIN_PASSWORD`, `ALLOW_INSTANT_DEMO`, `COPILOT_MAX_LIVE_CALLS_PER_HOUR`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `OFFLINE_MODE`, `ALLOWED_ORIGINS`, `CORS_ORIGINS`.
- **Frontend (Render Web service):** `PORT`, `NEXT_PUBLIC_API_BASE`, `NEXT_PUBLIC_ALLOW_INSTANT_DEMO`, `BACKEND_INTERNAL_URL`.

### Local Windows Launch
- Start: `mini-dios-workforce\start.bat` (Uvicorn on `:8000` + Next.js dev on `:3000`).
- Stop: `mini-dios-workforce\stop.bat` (terminates listeners on ports `8000` and `3000`).

### On-Premises Docker (`mini-dios-workforce/docker-compose.yml`)
```bash
cd mini-dios-workforce
docker compose up -d --build
# Shut down (preserves dios-audit-data volume):
docker compose down
```

### Render.com Blueprint (`render.yaml`)
Single-click Blueprint deploys `mini-dios-plastics-api` (Docker, `/api/health`, 1GB persistent disk at `/data`) and `mini-dios-plastics` (Docker frontend proxying to `BACKEND_INTERNAL_URL`).

---

## 10. QA, Testing, Audit & Drive Sync Commands

- **Backend unit & API tests:** `pytest` inside `mini-dios-workforce/backend/`
- **Quick ripple audit / full audit:** `python scripts/run_audit.py --quick` / `python scripts/run_audit.py`
- **Frontend production build:** `npm.cmd run build` (or `.tools\node\npm.cmd run build`) inside `mini-dios-workforce/frontend/`
- **Drive sync unit tests:** `python -m unittest tests/test_drive_sync.py -v`
- **Drive sync dry-run / live API sync:** `python scripts/sync_docs_to_drive.py --dry-run` / `python scripts/sync_docs_to_drive.py`
- **Antigravity `gdrive` CLI in-place update:** `gdrive mutate update <FILE_ID> <local.md> --mime-type "application/vnd.google-apps.document"`
