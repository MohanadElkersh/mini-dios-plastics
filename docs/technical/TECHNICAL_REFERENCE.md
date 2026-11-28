# Mini-DIOS Plastics — Technical Reference & Engineering Architecture

> **Track B — Dedicated Technical Documentation (For Engineers, DevOps, IT & AI Agents)**
> **Repository:** `mini-dios-workforce/` • **Last Synchronized:** 2026-11-28 (`v1.9 — Visual Decision Intelligence Blueprint & Causal Trace Inspector`)
> **Security Note:** This document lists environment variable *names* and architectural specs only. It NEVER stores real API keys, passwords, OAuth tokens, or `.env` values.

---

## Table of Contents
1. [System Architecture & Tech Stack](#1-system-architecture--tech-stack)
2. [Repository & Module Map](#2-repository--module-map)
3. [Press Scheduling CP-SAT Formulation (`HC1–HC6` + Container Consolidation Sync)](#3-press-scheduling-cp-sat-formulation-hc1hc6--container-consolidation-sync)
4. [Workforce CP-SAT Formulation (`WHC1–WHC5`)](#4-workforce-cp-sat-formulation-whc1whc5)
5. [Deterministic Financial, Container WIP & Risk Radar Formulas](#5-deterministic-financial-container-wip--risk-radar-formulas)
6. [Operations Copilot 3-Tool Architecture, Commander-Grade Trade-Offs & Lockstep State Sync](#6-operations-copilot-3-tool-architecture-commander-grade-trade-offs--lockstep-state-sync)
7. [1-Month Historical Backtest Engine, 5-Step Guided Onboarding, CTP Quoter & WhatsApp Dispatch](#7-1-month-historical-backtest-engine-5-step-guided-onboarding-ctp-quoter--whatsapp-dispatch)
8. [REST & Excel Integration API Endpoints](#8-rest--excel-integration-api-endpoints)
9. [Authentication, Proxy Routing, CORS & Dual-Mode Database Persistence](#9-authentication-proxy-routing-cors--dual-mode-database-persistence)
10. [Environment Variables, Local Launch, Docker & Render Deployment](#10-environment-variables-local-launch-docker--render-deployment)
11. [QA, Testing, Audit & Drive Sync Commands](#11-qa-testing-audit--drive-sync-commands)
12. [Deferred CP-SAT Constraint Extensions (Design Notes — Parked / Not Yet Implemented)](#12-deferred-cp-sat-constraint-extensions-design-notes--parked--not-yet-implemented)
13. [5-Layer Decision Intelligence + 6-Primitive UEMGraph Compiler Architecture (`USE_UEM_ENGINE`)](#13-5-layer-decision-intelligence--6-primitive-uemgraph-compiler-architecture-use_uem_engine)

---

## 1. System Architecture & Tech Stack

| Layer | Technology | Responsibility |
| :--- | :--- | :--- |
| **Frontend UI** | Next.js (App Router), React, TypeScript, Tailwind CSS, Recharts, Lucide Icons | 6-tab Executive Command Center, Bilingual EN (LTR) / AR (RTL), SAR / EGP live currency conversion, `LoginGate`, `HistoricalBacktestModal`, `GuidedOnboardingModal`, `ScheduleExportMenu`, `Pin & Compare A/B/C`, `CopilotDrawer`, Dual-Audience `ExecutiveBriefModal`. |
| **Backend API** | Python 3.12, FastAPI, Pydantic v2, Uvicorn | Validation, scenario composition, CP-SAT orchestration, 1-month historical backtest replay engine, 5-step process-first guided onboarding generator, Excel/CSV/ERP JSON integration bridge, Copilot tool router, SQLite persistence. |
| **Optimization Engine** | Google OR-Tools CP-SAT (`cp_model`) | 100% deterministic integer/constraint programming (`AddCircuit` + `AddNoOverlap`) for parallel-machine press scheduling, multi-SKU export container consolidation coupling, and role-decomposed floor workforce rostering. |
| **Copilot Orchestrator** | `google-genai` SDK (`gemini-4-hydrogen`, `thinking_level="low"`, 15s `HttpOptions` timeout) + Deterministic Offline Parser | Zero-LLM-Arithmetic architecture: LLM only constructs structured tool arguments and narrates exact Python-computed results (including `FinancialTradeoffSummary`); fails over seamlessly to local EN/AR parser when offline. |
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
│   ├── technical/
│   │   ├── TECHNICAL_REFERENCE.md       # Track B: This file
│   │   └── CODEBASE_AND_UPDATES_LOG.md  # Track B: File-by-file codebase map & update ledger
│   ├── CHANGELOG.md                     # Track B: Dated engineering & documentation log
│   └── .drive-sync-manifest.json        # Canonical Google Drive folder/file IDs & SHA-256 hashes
└── mini-dios-workforce/
    ├── start.bat / stop.bat             # Windows local dev launcher & port 8000/3000 cleaner
    ├── docker-compose.yml               # On-prem Docker stack (backend + frontend + persistent volume)
    ├── backend/
    │   ├── main.py                      # FastAPI app entrypoint & CORS/auth middleware
    │   ├── api/routes.py                # REST, Backtest, Onboarding & Excel/CSV/ERP Export API endpoints (/api/*)
    │   ├── core/
    │   │   ├── ontology.py              # Pydantic models, container/warehouse physics, Pre-Solve Validator
    │   │   ├── disruptions.py           # Composable scenario engine (breakdowns, shocks, rush orders, PM)
    │   │   ├── solver.py                # Press CP-SAT solver + Container Sync + Naive FIFO Baseline comparator
    │   │   ├── verify.py                # Independent HC1–HC6 post-solve verifier
    │   │   ├── workforce_solver.py      # Coupled 5-role Workforce CP-SAT + Naive Static Rotation + WHC1–WHC5
    │   │   ├── kpi.py                   # Schedule KPIs, Container WIP & Warehouse sweep, Gantt builder, scorecard
    │   │   ├── financials.py            # Zero-double-counting P&L reconciliation & per-order profitability
    │   │   ├── risk_radar.py            # Deterministic Proactive Risk Radar (including warehouse_congestion)
    │   │   ├── copilot.py               # 3-tool Gemini + EN/AR offline parser + FinancialTradeoffSummary
    │   │   ├── backtest.py              # 1-Month Historical Backtest / Replay Engine (CSV/XLSX + sample 30-day log)
    │   │   ├── onboarding.py            # 5-Step Process-First Guided Onboarding Generator + Readiness Checklist
    │   │   ├── excel_io.py              # 4-tab Excel parser, Executive Brief, & Integration Schedule (XLSX/CSV/JSON)
    │   │   ├── audit.py                 # SQLite AuditStore (runs & workspaces)
    │   │   └── seed.py                  # Seeded 6-press Delta & Riyadh demo dataset (24 orders, 4 container groups, 28 workers)
    │   └── tests/                       # Pytest suite (solver, workforce, financials, validator, copilot, api, risk_radar, auth)
    └── frontend/src/
        ├── lib/                         # api.ts, format.ts, i18n.ts, store.tsx, types.ts
        └── components/                  # LoginGate, TopBar, DecisionLoopStrip, ScopeView, DataStudioView,
                                         # TradeoffConsole, ProductionGanttView, FinancialsView, WorkforceView,
                                         # RiskRadarPanel, ExecutiveBriefModal, CopilotDrawer,
                                         # HistoricalBacktestModal, GuidedOnboardingModal, ScheduleExportMenu, studio/*
```

---

## 3. Press Scheduling CP-SAT Formulation (`HC1–HC6` + Container Consolidation Sync)

Implemented in `backend/core/solver.py` and independently verified post-solve in `backend/core/verify.py`.

### Horizon & Physics Constants (`backend/core/ontology.py`)
- Default weekly horizon: `168h` (`10,080` min; configurable `24–336h`). Extended tail: `264h` (`15,840` min) so late orders remain schedulable and accurately penalized.
- `order_shots(order, mold) = max(1, ceil(quantity_pcs / cavities))`
- `order_duration_mins(order, mold) = max(30, ceil((shots * cycle_time_sec) / 60))`
- `order_gross_weight_kg(order, mold) = round(((qty * part_weight_g) / 1000) * (1.005 if hot_runner else 1.03), 2)`
- Color pigment ranks: `Natural=1, White=2, Yellow=3, Blue=4, Red=5, Black=6`.
- Compatible polyolefin family: `POLYOLEFIN_RESINS = {"PP", "HDPE", "LDPE"}`. Switching across families (`PET`, `ABS`, `PVC`) triggers incompatible-resin full-barrel purge (default `180 min / 48 kg`).
- Default purge & warehouse physics (`PlantPhysicsConfig`): Light→Dark `25m / 4.0kg`; Dark→Light `135m / 32.0kg`; Incompatible resin `180m / 48.0kg`; Electricity tariff `0.32 SAR/kWh`; Peak window `13:00–17:00` (`1.4x`); Ramadan shift `6h` (`18:00–20:00` Iftar changeover blackout, `1.15x` labor multiplier); `fg_storage_capacity_tons = 22.0`; `wip_holding_cost_per_ton_day = 85.0`; `fx_egp_per_sar = 13.0`.

### Hard Constraints (`HC1–HC6`)
- **`HC1` — Mold–Press Compatibility & Hot-Runner Fit:** Scheduled order runs on exactly one `active` press in `mold.compatible_machines`, with `press.supports_hot_runner == True` when `mold.is_hot_runner == True`.
- **`HC2` — No Press Overlap & Breakdown/Downtime Exclusion:** `AddNoOverlap` per press across all busy intervals `[start - setup, end)` and all downtime/breakdown windows. When `ramadan_shift_mode=True`, setup intervals also `AddNoOverlap` daily `18:00–20:00` blackouts.
- **`HC3` — Physical Mold Exclusivity Across Presses:** `AddNoOverlap` per physical mold across all presses.
- **`HC4` — Asymmetric Changeover & Color/Resin Purge Sequencing:** `AddCircuit` per press enforces exact sequence-dependent `setup_mins` and `purge_scrap_kg` via `transition_penalty()`.
- **`HC5` — Resin Pre-Drying Floor, Food-Grade Regrind Safety & Inventory Cap:** `start_min >= resin.drying_lead_time_hrs * 60`; orders with `max_regrind_pct == 0` strictly receive `0 kg` regrind even under `allow_regrind_override_pct`; weekly `virgin_used + purge_scrap <= virgin_available_kg` and `regrind_used <= regrind_available_kg` (modeled at `0.1 kg` integer precision).
- **`HC6` — Mold Preventive Maintenance (PM) Block:** Triggered when `shot_utilization_pct >= 95%`, manual `MoldPmLock`, or projected mid-week shots `> maintenance_interval_shots` under `autonomous_pm_window=True`. In `Auto PM` mode, CP-SAT floats the PM block up to `75%` of horizon while enforcing `shots_before_pm <= maintenance_interval_shots - current_shots`.

### Multi-SKU Export Container Consolidation Coupling (`container_sync_enabled`)
- Orders may carry an optional `container_group_id` (e.g., `CNT-RIYADH-01`, `CNT-JEDDAH-02`, `CNT-AUTO-03`, `CNT-CHEM-04`).
- When `config.container_sync_enabled == True`, `_solve_cpsat_model` creates a group shipment completion variable `cg_ship >= end_vars[i]` for every member order `i` in a multi-SKU container group, and a container waiting-time variable `cg_wait_i >= cg_ship - end_vars[i]` (gated by `scheduled_vars[i]`), penalizing early single-SKU batch completion that sits in the finished-goods warehouse waiting for companion SKUs.

### Weighted Multi-Objective (SAR Cents)
```text
Minimize:
  (3 * w_changeover_scrap + 1) * (Purge_Resin_Cost + Changeover_Downtime_Cost_at_250_SAR_hr)
+ (3 * w_otif             + 1) * (Tardiness_Penalty * (1.5 if is_export else 1.0) + Unscheduled_Penalty + Export_Safety_Buffer_Shortfall)
+ (2 * w_energy_cost      + 1) * (Press_Energy_Cost + Peak_Tariff_Surcharge + Press_Operating_Cost)
+ (2 * w_working_capital  + 1) * (Virgin_&_Regrind_Material_Spend + Early_WIP_Holding_Cost + Container_Wait_Holding_Cost)
+ pm_tiebreak_expr
```

---

## 4. Workforce CP-SAT Formulation (`WHC1–WHC5`)

Implemented in `backend/core/workforce_solver.py` across `Press_Operator`, `Mold_Technician`, `QC_Inspector`, `Material_Handler`, `Shift_Supervisor` and independently verified via `verify_workforce()`.
- **Hard Constraints (`WHC1–WHC5`):**
  - `WHC1`: Role & press certification match.
  - `WHC2`: Weekly hour cap & Ramadan 6h/36h clamp.
  - `WHC3`: Mandatory inter-shift rest gap (`>= min_rest_hours`, default `11h`).
  - `WHC4`: Zero scheduling on `sick`, `on_leave`, `approved_leave_days`, or Copilot callout days + `>= min_consecutive_days_off` (default `1`) consecutive days off per 7-day cycle.
  - `WHC5`: Max 1 shift per worker per calendar day.

---

## 5. Deterministic Financial, Container WIP & Risk Radar Formulas

### Financial Reconciliation (`backend/core/financials.py`)
- `Recognized Revenue = sum(qty_pcs * unit_selling_price * (1 - discount_pct / 100))` for scheduled orders.
- `Variable Production Cost = Direct Resin + Net Purge Scrap + (Energy + Press Operating) + Late Penalties + WIP Holding + Direct Floor Labor & Overtime`.
- `Gross Profit = Recognized Revenue - Variable Production Cost`.
- `Net Operating Profit = Gross Profit - Weekly Fixed Overhead`.
- `Total Weekly Savings = (Baseline Total Operating Cost - Optimized Total Operating Cost) + (Optimized Recognized Revenue - Baseline Recognized Revenue)`.

### Container Consolidation & Finished-Goods Warehouse Sweep (`backend/core/kpi.py`)
- For each `container_group_id`, `ship_ready_hr = max(end_hr of scheduled member jobs)`.
- Each member job `j` incurs `container_wait_hrs = max(0, ship_ready_hr - j.end_hr)`.
- `wip_holding_days` accumulates `gross_tons * hold_days` across both early completion before due time and container wait intervals.
- `peak_warehouse_tons` sweeps finished-goods inventory events `[job_end_min, release_min)` across the 7-day horizon; `warehouse_utilization_pct = round((peak_warehouse_tons / fg_storage_capacity_tons) * 100, 1)`.
- `trapped_working_capital` sums time-weighted revenue value (`order_revenue * (wait_hrs / 24.0)`) locked in incomplete multi-SKU export containers.

### Proactive Risk Radar (`backend/core/risk_radar.py`)
Evaluates 6 deterministic risk categories from the **active** `PlantDataset` + `SolveResult` + `WorkforceSolveResult`:
1. `export_delay` — Unscheduled / late / tight-slack (`< 6h` export, `< 4h` domestic) orders.
2. `resin_shortage` — Minute-by-minute resin silo depletion clock (`projected_stockout_hr` at `>= 98%` draw).
3. `press_overload` — High-utilization press choke points (`>= 82%` elevated, `>= 92%` critical).
4. `mold_pm_hazard` — Post-week mold shot-limit trajectory (`>= 90%` watch, `>= 95%` elevated, `>= 100%` critical).
5. `shift_fragility` — Workforce understaffed slots and zero-buffer high-load shift fragility.
6. `warehouse_congestion` — Finished-goods warehouse utilization approaching/exceeding `fg_storage_capacity_tons` (`>= 85%` elevated, `> 100%` critical) or multi-SKU export containers with `max_sku_wait_hrs >= 14.0` trapping working capital.

---

## 6. Operations Copilot 3-Tool Architecture, Commander-Grade Trade-Offs & Lockstep State Sync

Implemented in `backend/core/copilot.py` and rendered in `frontend/src/components/CopilotDrawer.tsx`:
- **Commander-Grade Financial Trade-Off Summary (`FinancialTradeoffSummary`):**
  - `_compute_financial_tradeoff_summary(baseline_result, simulated_result, scenario_summary_en, scenario_summary_ar)` deterministically compares the pre-simulation active schedule against the simulated CP-SAT schedule across 5 cost buckets (`Direct Resin`, `Net Purge Scrap`, `Power & Press Ops`, `Late & Export Penalties`, `WIP & Container Holding`, `Shift Labor & Overtime`) plus revenue delta.
  - Produces `cost_paid_label_en/ar`, `cost_paid_amount`, `value_protected_label_en/ar`, `value_protected_amount`, `net_financial_gain`, `currency`, `is_positive_net`, and bilingual executive callout strings `headline_en` / `headline_ar` (rendered at the top of every Copilot simulation card above `Apply This Scenario to Dashboard` and `Pin for Comparison`).
- **Lockstep State Sync (`frontend/src/lib/store.tsx`):** Every toggle (`Peak Tariff Avoid`, `Ramadan Shift`, `Auto PM`, `Container Sync`), Guided Onboarding workspace generation, or Copilot scenario apply updates `dataset`, `config`, `result`, `workforce`, `financials`, and `risk_radar` atomically.

---

## 7. 1-Month Historical Backtest Engine, 5-Step Guided Onboarding, CTP Quoter & WhatsApp Dispatch

### 7.1 1-Month Historical Backtest / Replay Engine (`backend/core/backtest.py`)
- **Template Generator (`build_backtest_template_csv`, `build_backtest_template_xlsx`):** Emits a 13-column historical log template (`order_id`, `customer`, `sku_name`, `resin`, `color`, `qty_units`, `press_id`, `actual_changeover_hrs`, `actual_purge_scrap_kg`, `actual_overtime_hrs`, `actual_late_hours`, `export_penalty_cost`, `unit_margin`) pre-populated with realistic sample rows.
- **Deterministic Replay (`run_historical_backtest_replay`):** Groups up to 4 weekly batches from the uploaded CSV/XLSX (or 28-order `"sample_30day_log"`), runs OR-Tools CP-SAT with light-to-dark sequencing and container sync against the active plant's physics, persists the summary to `backtest_runs`, and computes `BacktestReplayReport`.

### 7.2 Guided "Process-First" 5-Step Onboarding Wizard (`backend/core/onboarding.py`)
- `build_guided_plant_workspace(req: GuidedSetupRequest)` constructs a tailored `PlantDataset` (presses across selected tonnage tiers with backup press compatibility, molds, resin inventory, multi-SKU export container orders, 2-shift or 3-shift workforce roster, and `PlantPhysicsConfig`), runs `validate_plant_data()` and `solve_plant_schedule()` (capped at `<= 2.2s` for Render Free Tier safety), and returns `GuidedSetupResponse` including a 6-item bilingual **"Current Specs Only" Readiness Checklist** (`ReadinessChecklistItem`) confirming zero historical ERP data is required.

### 7.3 Integration-Ready Export Engine (`backend/core/excel_io.py`)
- `export_integration_schedule_workbook()`: 4-sheet `.xlsx` workbook (`Press Schedule`, `Workforce Shifts`, `KPIs & Savings`, `Risk Radar`).
- `export_integration_schedule_csv()`: Flat UTF-8 `.csv` press schedule with container group and wait hours.
- `export_integration_erp_payload()`: Versioned `mini-dios-plastics-erp/v1.3` JSON payload (`work_orders`, `mold_maintenance_windows`, `container_consolidations`, `workforce_shift_roster`, `kpis_and_financials`, `risk_alerts`) ready for Odoo MRP (`mrp.production` / `mrp.workorder`) and SAP Business One (`OWOR`).

### 7.4 Capable-to-Promise (CTP) Non-Destructive Rush-Order Quoter (`backend/core/ctp.py`)
- **`evaluate_ctp_rush_order(req: CTPQuoteRequest)`:**
  - Deep-copies `dataset` and `config` in memory (`copy.deepcopy`) so the active sandbox workspace and database are **never mutated** during quoting.
  - Bounds `max_solve_seconds <= 2.2s` to respect Render Free-Tier memory/CPU limits (`0.1 CPU / 512 MB RAM`).
  - Inserts the prospective rush order (inheriting tonnage/press compatibility and cycle times from `mold_id`), solves the coupled Press + Workforce + Financial + Risk Radar pipeline, and diffs against the baseline solve.
  - Returns `CTPQuoteResult` containing:
    - `verdict`: `"ON_TIME"` | `"LATE"` | `"INFEASIBLE"`
    - `assigned_press_id`, `scheduled_start_hr`, `scheduled_end_hr`, `target_due_hour`, `slack_or_delay_hrs`
    - `financial_impact`: `gross_revenue`, `direct_resin_cost`, `extra_purge_scrap_kg`, `extra_purge_cost`, `extra_changeover_hrs`, `extra_changeover_cost`, `extra_electricity_cost`, `extra_overtime_labor_cost`, `extra_wip_holding_cost`, `extra_late_penalty_cost`, `total_marginal_cost`, `net_profit_contribution`, `margin_pct`, and `min_breakeven_unit_price` (`total_marginal_cost / qty_units`).
    - `bumped_orders`: Pre-existing confirmed orders delayed by `>= 0.3h` or pushed past deadline (`breaches_cutoff`, `is_export`).
    - `risk_score_before`, `risk_score_after`, `tradeoff_summary_en`, `tradeoff_summary_ar`, and `candidate_order`.

### 7.5 1-Click Bilingual WhatsApp Shift Dispatch & Print-Optimized Executive PDF (`backend/core/dispatch.py`, `WhatsAppDispatchModal.tsx`, `ExecutivePrintReport.tsx`)
- **`format_whatsapp_shift_dispatch()` (`backend/core/dispatch.py`):** Deterministically formats a WhatsApp dispatch brief (`*bold*` headers, clean bullets, press-by-press run sequence, setup/purge alerts, assigned shift crew by role, open gap warnings, and URL-encoded `https://wa.me/?text=...` link) for either `scope="full_week"` or `scope="day_shift"` (`day: 0..6`, `shift: Morning | Afternoon | Evening | Night | ALL`) in `en` or `ar`.
- **`ExecutivePrintReport.tsx` + `@media print` (`globals.css`):** Zero-server-RAM light-background (`#ffffff` / `#0f172a`) printable A4 report supporting `Owner / Chairman View`, `Plant / Production Manager Decision Shield`, and `30-Day Historical Backtest Proof` in both English (`dir="ltr"`) and Arabic (`dir="rtl"`, `IBM Plex Sans Arabic`).

---

## 8. REST & Excel Integration API Endpoints

Defined in `backend/api/routes.py` under prefix `/api`:
- `GET /api/health` — Service status, OR-Tools version, `auth_enabled`, and `storage_backend` (`postgres` vs. `sqlite_fallback`).
- `GET /api/demo-data` — Seeded `PlantDataset` (with 4 export container groups) + default `SolverConfig` (`container_sync_enabled=True`).
- `POST /api/validate` — Accepts JSON (`{dataset, config?}`) or `multipart/form-data` 4-tab `.xlsx` workbook.
- `POST /api/solve` — Full Press + Workforce CP-SAT + Financials + Risk Radar + persistence audit save.
- `POST /api/workforce/solve` — Fast labor-only re-solve against an existing Press Gantt.
- `POST /api/copilot/ask` — Executes Copilot 3-tool pipeline + `financial_tradeoff_summary`.
- `GET /api/checkpoints` — Lists recent decision checkpoints (newest first, capped at 25 per sandbox) with `storage_backend` and `pool_config` diagnostics.
- `POST /api/checkpoints` — Records an immutable decision checkpoint (`copilot`, `ctp_commit`, `workspace_save`, `manual`).
- `POST /api/checkpoints/{checkpoint_id}/restore` — Restores exact plant/config state from a checkpoint, re-solves the coupled production + workforce + Risk Radar bundle, and updates the active workspace.
- `POST /api/quote/ctp` — Non-destructive Capable-to-Promise rush-order evaluation returning `CTPQuoteResult`.
- `POST /api/quote/ctp/commit` — Commits an accepted CTP rush order to the active workspace, re-solves, and saves a `ctp_commit` Decision Checkpoint.
- `POST /api/dispatch/whatsapp` — Formats a deterministic EN/AR WhatsApp shift dispatch payload and `wa.me` share URL.
- `GET /api/backtest/template?format=csv|xlsx` — Downloads 13-column historical backtest template.
- `POST /api/backtest/replay` — Runs 1-Month Historical Backtest Replay from uploaded CSV/XLSX or `mode="sample_30day_log"` and persists to `backtest_runs`.
- `POST /api/onboarding/generate` — Generates and solves a 5-step guided plant workspace + Readiness Checklist.
- `GET /api/export/schedule.xlsx`, `GET /api/export/schedule.csv`, `GET /api/export/erp-payload.json` — Sandbox-scoped live schedule exports (auto-solves active workspace if needed).
- `GET/POST /api/workspaces`, `GET/DELETE /api/workspaces/{workspace_id}` — Saved plant workspace CRUD (`saved_workspaces`).
- `GET /api/audit-log`, `GET /api/audit-log/{run_id}` — Cryptographic audit trail retrieval.
- `GET /api/template.xlsx`, `POST /api/export-dataset.xlsx`, `POST /api/export-brief.xlsx` — Programmatic Excel bridge.

---

## 9. Authentication, Proxy Routing, CORS & Dual-Mode Database Persistence

- **Hosted Access Gate (`LoginGate.tsx` + backend auth):** Enabled via `AUTH_ENABLED=true`. Signed session cookies use `AUTH_SECRET_KEY`. Multi-client passcodes configured via `DEMO_ACCESS_CODES` (`Executive Demo:DIOS-2026,Alexandria Plant:ALEX-2026,Riyadh Plant:KSA-2026`).
- **Frontend → Backend Proxy (`frontend/src/app/api/[...path]/route.ts`):** Proxies `/api/*` internally to `BACKEND_INTERNAL_URL` with an explicit header allowlist and self-proxy loop guard.
- **Dual-Mode Database Persistence (`backend/core/audit.py`):**
  - Reads `DATABASE_URL` from environment variables.
  - When `DATABASE_URL` is set (PostgreSQL on Neon, Supabase, or Render Postgres), normalizes `postgres://` → `postgresql://`, appends `sslmode=require` on remote cloud hosts, and configures a bounded connection pool safe for Render Free tier (`pool_size=3`, `max_overflow=2`, `pool_pre_ping=True`).
  - When `DATABASE_URL` is unset (or connection fails), falls back cleanly to local SQLite (`data/mini_dios.db` or `DIOS_AUDIT_DB`) so the application never crashes on startup.
  - Auto-migrates 5 tables scoped by `sandbox_id` (`session_id`) and `access_code` (`client_label`): `plastics_audit_runs`, `saved_workspaces` (plus legacy `plastics_workspaces` mirror), `pinned_scenarios`, `backtest_runs`, and `decision_checkpoints`.

---

## 10. Environment Variables, Local Launch, Docker & Render Deployment

### Environment Variable Names (Never Store Real Values in Docs)
- **Backend (`backend/.env` / Root `.env.local` / Render API service):** `PORT`, `DATABASE_URL`, `DATABASE_URL_UNPOOLED`, `NEON_BRANCH`, `NEON_BRANCH_ID`, `NEON_AUTH_BASE_URL`, `NEON_AUTH_JWKS_URL`, `NEON_FUNCTION_HOST_SUFFIX`, `NEON_AI_GATEWAY_TOKEN`, `NEON_AI_GATEWAY_BASE_URL`, `NEON_REALTIME_URL`, `NEON_REALTIME_SECRET`, `COPILOT_USE_NEON_AI_GATEWAY`, `DIOS_AUDIT_DB`, `AUTH_ENABLED`, `AUTH_SECRET_KEY`, `DEMO_ACCESS_CODES`, `ADMIN_PASSWORD`, `ALLOW_INSTANT_DEMO`, `COPILOT_MAX_LIVE_CALLS_PER_HOUR`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `OFFLINE_MODE`, `ALLOWED_ORIGINS`, `CORS_ORIGINS`.
- **Frontend (Root `.env.local` / Render Web service):** `PORT`, `NEXT_PUBLIC_API_BASE`, `NEXT_PUBLIC_ALLOW_INSTANT_DEMO`, `BACKEND_INTERNAL_URL`, plus the 11 Neon variables loaded automatically from root `.env.local` via `next.config.ts` (`DATABASE_URL`, `DATABASE_URL_UNPOOLED`, `NEON_BRANCH`, `NEON_BRANCH_ID`, `NEON_AUTH_BASE_URL`, `NEON_AUTH_JWKS_URL`, `NEON_FUNCTION_HOST_SUFFIX`, `NEON_AI_GATEWAY_TOKEN`, `NEON_AI_GATEWAY_BASE_URL`, `NEON_REALTIME_URL`, `NEON_REALTIME_SECRET`).
- **Neon Diagnostic & Live Query Endpoints:**
  - `GET /api/neon/status` (FastAPI Backend): Verifies all 5 Neon services (`postgres`, `auth`, `functions`, `ai_gateway`, `realtime`) from Python.
  - `GET /api/neon/function/{slug}` (FastAPI Backend): Invokes deployed Neon Function `slug` (e.g., `hello`).
  - `GET /api/neon/frontend-status` (Next.js App Router): Verifies all 5 Neon services using `@neondatabase/serverless`, `@neon/env` (`parseEnv`, `functionBaseUrl`), and `@neon/realtime/server` (`createRealtime`, `rawSql`).
  - `GET /api/neon/realtime` (Next.js App Router): Seals a parameterized `SealedLiveQuery` against `decision_checkpoints` for `@neon/realtime/client` WebSocket subscriptions.

---

## 11. QA, Testing, Audit & Drive Sync Commands

- **Backend unit & API tests:** `pytest` inside `mini-dios-workforce/backend/`
- **Quick ripple audit / full audit:** `python scripts/run_audit.py --quick` / `python scripts/run_audit.py`
- **Frontend production build:** `npm.cmd run build` (with `mini-dios-workforce\.tools\node` on `PATH`) inside `mini-dios-workforce/frontend/`
- **Drive sync unit tests:** `python -m unittest tests/test_drive_sync.py -v`
- **Drive sync dry-run / live API sync:** `python scripts/sync_docs_to_drive.py --dry-run` / `python scripts/sync_docs_to_drive.py`
- **Antigravity `gdrive` CLI in-place update:** `gdrive mutate update <FILE_ID> <local.md> --mime-type "application/vnd.google-apps.document"`

---

## 12. Deferred CP-SAT Constraint Extensions (Design Notes — Parked / Not Yet Implemented)

> **STATUS: PARKED / NOT YET IMPLEMENTED (`Pilot-Pull Only`)**
> The following mathematical formulations map every item in `docs/ROADMAP_AND_BACKLOG.md` (Tier 1 and Tier 2) to its target OR-Tools CP-SAT modeling pattern. These constraints are intentionally excluded from the core solver until requested by a pilot factory.

### 12.1 Tier 1 — High-Likelihood Pilot Extensions (`STATUS: PARKED / NOT YET IMPLEMENTED`)

| Backlog Item | Target CP-SAT Modeling Pattern |
| :--- | :--- |
| **1. Shared Auxiliary Equipment (Overhead Cranes, Chiller Tonnage, Dryers/Robots)** | • **Overhead Cranes:** Create setup interval variables `setup_iv[i, m] = NewOptionalIntervalVar(busy_start[i], setup_vars[i], start_vars[i], pres_vars[i, m])` for heavy molds (`tonnage >= 500T`) and enforce `model.AddCumulative(heavy_setup_ivs, [1]*N, max_simultaneous_cranes)`.<br>• **Summer Chiller Tonnage:** For each active run interval `run_iv[i]`, assign cooling demand `chiller_tons[i] = ceil((gross_kg_per_hr[i] * specific_heat_kj) / 12660)` and enforce `model.AddCumulative(run_ivs, chiller_tons, plant_chiller_capacity_tons)`.<br>• **Shared Portable Dryers / Robots:** `model.AddCumulative(auxiliary_ivs, [1]*K, available_aux_units)`. |
| **2. Capped / Blocked Mold Cavities** | • Add `active_cavities: int = Field(le=nominal_cavities, gt=0)` to `Mold`.<br>• Scale shot count deterministically in `order_shots()`: `shots = ceil(quantity_pcs / mold.active_cavities)`, automatically lengthening `order_duration_mins(order, mold)` while keeping part weight per cavity invariant. |
| **3. Multi-Stage Dependencies (Preform → Blow Molding & Cap + Bottle Matching)** | • **Stage Precedence:** For paired upstream preform order `i` and downstream blow-molding order `j`, enforce `model.Add(start_vars[j] >= end_vars[i] + cooling_lag_mins).OnlyEnforceIf([scheduled[i], scheduled[j]])` or lot-split transfer batching.<br>• **Matched Component Sets:** Couple cap order `c` and bottle order `b` via shared packing completion variable `pack_ready >= end_vars[c]` and `pack_ready >= end_vars[b]`, penalizing spread `|end_vars[c] - end_vars[b]|`. |
| **4. Order Splitting & Duplicate Parallel Molds** | • Replace single-mold ID with `mold_group_id` owning `K` physical tool instances (`K >= 1`), using `model.AddCumulative(mold_group_ivs, [1]*N, K)` instead of `AddNoOverlap`, or pre-split large export orders into `m` sub-lots with minimum batch duration floor `min_batch_run_hrs`. |
| **5. Mid-Week Inbound Supply & Packaging Stockouts** | • Replace static scalar `virgin_available_kg` with a step-function cumulative inventory curve at discrete event epochs `t in {0, arrival_1, ..., H}`: `sum_{i: start_i <= t} (virgin_10[i] + purge_10[i]) <= initial_stock_10 + sum_{a: t_a <= t} inbound_10[a]`, plus parallel cumulative caps for `masterbatch_kg`, `cartons_pcs`, `iml_labels_pcs`, and `pallets_cnt`. |
| **6. Secondary / Downstream Bottlenecks (Printing, IML, Ultrasonic Welding)** | • Model each downstream finishing work-center `w` (e.g., Dry-Offset Printer, Pad Printer, Ultrasonic Welder) as a secondary stage with interval `fin_iv[i]` (`fin_start[i] >= end_vars[i]`), enforcing `model.AddNoOverlap(fin_ivs[w])` and evaluating `tardiness_vars[i] >= fin_end[i] - due_min[i]`. |

### 12.2 Tier 2 — Sub-Sector & Heavy-Plant Phase 2 Extensions (`STATUS: PARKED / NOT YET IMPLEMENTED`)

| Backlog Item | Target CP-SAT Modeling Pattern |
| :--- | :--- |
| **1. Hard Plant kVA Transformer Peak-Demand Ceiling** | • Assign each press run interval `piv[i, m]` active kVA draw `kva_run[m]` and each barrel heat-up/changeover interval `siv[i, m]` surge kVA draw `kva_startup[m]`, enforcing `model.AddCumulative(all_press_ivs, kva_demands, transformer_max_kva)`. |
| **2. Insert-Only Swaps vs. Full Mold Changes** | • Add `mold_frame_id` and `insert_id` to `Mold`. In `transition_penalty(prev, next)`: if `prev.mold_frame_id == next.mold_frame_id` and `prev.insert_id != next.insert_id`, use `insert_swap_mins` (`25–35m`) instead of full `base_changeover_mins` (`95–155m`) inside `AddCircuit`. |
| **3. Thermal Barrel Heat-Up / Cool-Down Soak Windows** | • In `transition_penalty(prev, next)`: compute `delta_temp_c = resin_prev.barrel_temp_c - resin_next.barrel_temp_c`. When `|delta_temp_c| >= 50°C` (e.g. PET `280°C` → PP `205°C`), add deterministic thermal soak duration `soak_mins = int(round(|delta_temp_c| * 0.9))` to the `AddCircuit` arc transition time. |
| **4. QC Quarantine & First-Article Lab Hold Buffers** | • Add `qc_hold_hrs: float` to `ProductionOrder` (default `0.0`, `12.0–24.0h` for food/pharma/auto). Shift effective shipping readiness to `ship_ready_min[i] = end_vars[i] + int(round(qc_hold_hrs * 60))` and evaluate tardiness/container sync against `ship_ready_min[i]`. |
| **5. Extrusion-Specific Physics (Die Campaigns, Screen-Pack Swaps, 1D Slitting)** | • Group continuous pipe/film runs into monotonically widening/thickening die campaigns via `AddCircuit` arc costs; insert periodic mandatory screen-pack swap intervals every `max_extrusion_tons_between_screens` via cumulative tonnage counters; solve 1D jumbo-roll width slitting via column-generation cutting-stock pre-pass. |

---

## 13. 5-Layer Decision Intelligence + 6-Primitive UEMGraph Compiler Architecture (`USE_UEM_ENGINE`)

Implemented across `backend/core/uem.py`, `backend/core/uem_compiler.py`, `backend/core/uem_verify.py`, `backend/core/di/*`, and `backend/adapters/plastics.py`:

```text
1. Business Ontology (Formal entities, typed relationships & semantic invariants)  [backend/core/di/ontology_meta.py]
         │
         ▼
2. Business Architecture Validation (Pre-solve structural, capability & policy gate) [backend/core/di/arch_validator.py]
         │
         ▼
3. BPMN 2.0 Process Templates + 4. DMN 1.3 Decision Tables
   [backend/core/di/bpmn_engine.py]    [backend/core/di/dmn_engine.py]
         │
         └──────────────► Compiles cleanly into UEMGraph (6 Primitives)            [backend/core/uem.py]
                                      │
                                      ▼
                          CP-SAT Compiler + uem_verify.py                          [backend/core/uem_compiler.py + uem_verify.py]
                                      │
                                      ▼
5. Decision Intelligence Meta-Model (Causal Decision Diagram: Levers → Intermediates → Outcomes) [backend/core/di/decision_meta.py]
```

### 13.1 The 6 Canonical Primitives of `UEMGraph` (`backend/core/uem.py`)
Zero plastics-specific logic exists in `backend/core/uem*.py` or `backend/core/di/*`. Any domain adapter compiles its ontology, BPMN 2.0 workflow, and DMN 1.3 rule tables into:
1. **`ResourceNode`** — Primary unary execution resources (`primary_unary`), secondary shared tools/resources (`secondary_exclusive`), and dual-tier consumable pools (`consumable_pool`).
2. **`ActivityNode`** — Schedulable operations with `duration_mins`, `earliest_start_min`, `due_min`, `compatible_primary_ids`, `secondary_resource_id`, `consumable_pool_id`, `gross_consumable_units_10`, `max_secondary_consumable_units_10`, `usage_cycles`, and penalty rates.
3. **`TransitionMatrix`** — Directed sequence-dependent transition entries (`setup_mins`, `consumable_waste_units_10`, `transition_Waste_cost_cents`) compiled into `AddCircuit` per unary primary resource, plus `setup_blackout_windows`.
4. **`CumulativeEnvelope` (`CUMULATIVE_CAP`)** — Global consumable inventory caps (`consumable_cap`), time-windowed tariff surcharge overlap envelopes (`time_window_tariff`), and shift-windowed operator availability caps (`shift_capacity_cap`) with bounded soft-overflow penalties.
5. **`SynchronizationGroup`** — Multi-activity barrier consolidation groups (`barrier_consolidation`, modeling `cg_ship >= end_vars[i]` and `cg_wait_i >= cg_ship - end_vars[i]`) and static/autonomous floating maintenance blocks (`fixed_maintenance` / `floating_maintenance` with cumulative cycle budgets before maintenance).
6. **`ObjectiveTermSpec`** — Integer-scaled multi-objective weight multipliers and resource assignment / consumable cost tables.

### 13.2 Two-Way Bounded Workforce-Press Coupling (`backend/adapters/plastics.py`)
- **Forward Pass:** Injects shift-windowed operator availability envelopes (`CumulativeEnvelope(kind="shift_capacity_cap")`) into `UEMGraph` when active operator capacity on a day/shift (`available_operators * presses_per_operator`) is less than the active press fleet.
- **Backward Feedback Pass (Max 1 Iteration Capped at `<= 2.0s`):** If Pass 1's coupled `solve_workforce()` reports `Press_Operator` shortages (`c.required > c.scheduled`) on specific `(day, shift)` slots, `solve_plastics_via_uem()` tightens the `shift_capacity_cap` on those slots to `scheduled_operators * presses_per_operator` and runs at most 1 bounded feedback re-solve (`max_solve_seconds <= 2.0s`), adopting the updated schedule if it reduces `headcount_gap` or `understaffed_slots` without dropping orders.

### 13.3 Runtime Feature Flag, Sandbox-Scoped Admin Engine Switcher & Blueprint Endpoints
- **`USE_UEM_ENGINE` & `get_effective_engine(sandbox_id)` (`backend/core/solver.py`):**
  - `USE_UEM_ENGINE` defaults to `"false"` (`"legacy_cpsat_v1"`).
  - `get_effective_engine(sandbox_id)` resolves the calling sandbox's runtime override (`"uem_di_v1"` or `"legacy_cpsat_v1"`) if set via the Admin panel, falling back to `USE_UEM_ENGINE`.
  - Every optimization entry point (`/api/solve`, `/api/optimize`, `/api/quote/ctp`, `/api/quote/ctp/commit`, `/api/backtest/replay`, `/api/copilot/ask`, `/api/checkpoints/{id}/restore`, and `/api/onboarding/generate`) binds `bind_sandbox_engine_context(session.session_id)` and stamps `active_engine` in its response payload.
- **`GET /api/admin/engine-mode` & `POST /api/admin/engine-mode` (`backend/api/routes.py`):**
  - Restricted strictly to Admin sessions via `Depends(require_admin_session)` (`HTTP 403` for non-admin guest passcodes).
  - `GET /api/admin/engine-mode` returns `active_engine`, `env_default_engine`, `is_override`, `engine_override`, and `di_standards` (`["BusinessOntology", "ArchValidation", "DMN", "BPMN", "DI_CDD"]`).
  - `POST /api/admin/engine-mode` accepts `{"engine": "uem_di_v1" | "legacy_cpsat_v1" | "default"}`, updates only the calling sandbox's override, immediately re-solves the active plant, and returns the updated engine status, `switch_delta` (`prev_engine`, `new_engine`, `solve_time_ms`, `weekly_savings`, `otif_pct`), and the complete unified scenario bundle.
- **`GET /api/health`:** Reports `"optimization_engine": "uem_di_v1" | "legacy_cpsat_v1"` and `"use_uem_engine": bool`.
- **`GET /api/di/blueprint`:**
  - `?format=json` (default): Full 5-layer DI + 6-primitive `UEMGraph` blueprint JSON (including `traced_causal_pathways`, active workspace state, and deterministic per-rule DMN firing counts `rule_hit_counts`, `fired`, `hit_count`).
  - `?format=bpmn_xml`: Standards-compliant OMG BPMN 2.0 XML (`http://www.omg.org/spec/BPMN/20100524/MODEL`) with `Content-Disposition: attachment`.
  - `?format=dmn_xml`: Standards-compliant OMG DMN 1.3 XML (`https://www.omg.org/spec/DMN/20191111/MODEL/`) with `Content-Disposition: attachment`.

### 13.4 Visual Decision Intelligence Blueprint & Causal Trace Inspector (`frontend/src/components/DIBlueprintModal.tsx`)
- **Non-Intrusive Entry Points & Lazy State Sync (`frontend/src/lib/store.tsx`):**
  - Accessible without adding a 7th navigation tab from three entry points: (1) `Inspect DI Blueprint` button at the end of `DecisionLoopStrip.tsx`, (2) `Causal Trace & Policy Rules (DMN/BPMN)` button in `TradeoffConsole.tsx` (Tab 3), and (3) `Open Visual DI Blueprint Inspector` inside the Admin Engine Switcher card in `TopBar.tsx`.
  - Fetches `GET /api/di/blueprint?format=json` lazily only when opened; automatically marks `diBlueprintStale = true` (and refreshes immediately if open) whenever `result` updates after a solve, mode toggle, engine switch, Copilot scenario apply, CTP commit, or checkpoint restore.
- **Zero-Heavy-Dependency 4-Tab Visual Inspector (Pure React + Inline SVG / CSS Grid):**
  1. **Sub-Tab 1 — Visual Causal Decision Diagram (`CausalDiagramView.tsx`):** Interactive 3-column directional flow graph (`DecisionLever → IntermediateMetric → DecisionOutcome`, stacking cleanly on `375px–430px` mobile) with smooth SVG Bezier connector curves, live `SAR ↔ EGP` conversion, interactive pathway highlighting, and a **Causal Attribution Card** linking directly to governing DMN tables and UEM primitives.
  2. **Sub-Tab 2 — DMN 1.3 Decision Tables & Rule Trace (`DMNInspectorView.tsx`):** Expandable S-FEEL rule matrices for `DMN_BARREL_PURGE_TRANSITION`, `DMN_MOLD_PM_POLICY`, `DMN_FOOD_GRADE_REGRIND_SAFETY`, and `DMN_SHIFT_WORKFORCE_HEADCOUNT` with OMG Hit Policy badges, live `FIRED` (`N×`) badges, a `Show Fired Rules Only` filter, and 1-click DMN 1.3 XML export.
  3. **Sub-Tab 3 — BPMN 2.0 Process Flow Viewer (`BPMNFlowView.tsx`):** 4-swimlane OMG BPMN 2.0 diagram (`START_EVENT`, `TIMER_EVENT`, `EXCLUSIVE_GATEWAY`, `PARALLEL_GATEWAY`, `BUSINESS_RULE_TASK`, `TASK`, `END_EVENT`) with RTL-aware directional SVG arrows, interactive node execution specs strip, and 1-click BPMN 2.0 XML export.
  4. **Sub-Tab 4 — Architecture Validation, Ontology & UEM Graph (`ArchOntologyView.tsx`):** Pre-Solve Architecture Validation banner (`VALID` / `VALID_WITH_WARNINGS` / `BLOCKED`) across `GATE-1-STRUCTURAL`, `GATE-2-CAPABILITY`, and `GATE-3-POLICY`, 6-Primitive `UEMGraph` summary KPI cards, and collapsible Layer 1 `BusinessOntologyGraph` (`EntityTypes`, `TypedRelationships`, `SemanticInvariants`).
