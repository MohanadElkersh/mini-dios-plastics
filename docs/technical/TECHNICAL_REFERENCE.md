# Mini-DIOS Plastics — Technical Reference & Engineering Architecture

> **Track B — Dedicated Technical Documentation (For Engineers, DevOps, IT & AI Agents)**
> **Repository:** `mini-dios-workforce/` • **Last Synchronized:** 2026-11-25 (`v1.5 / Commercial & Decision Intelligence Upgrade v1.3`)
> **Security Note:** This document lists environment variable *names* and architectural specs only. It NEVER stores real API keys, passwords, OAuth tokens, or `.env` values.

---

## Table of Contents
1. [System Architecture & Tech Stack](#1-system-architecture--tech-stack)
2. [Repository & Module Map](#2-repository--module-map)
3. [Press Scheduling CP-SAT Formulation (`HC1–HC6` + Container Consolidation Sync)](#3-press-scheduling-cp-sat-formulation-hc1hc6--container-consolidation-sync)
4. [Workforce CP-SAT Formulation (`WHC1–WHC5`)](#4-workforce-cp-sat-formulation-whc1whc5)
5. [Deterministic Financial, Container WIP & Risk Radar Formulas](#5-deterministic-financial-container-wip--risk-radar-formulas)
6. [Operations Copilot 3-Tool Architecture, Commander-Grade Trade-Offs & Lockstep State Sync](#6-operations-copilot-3-tool-architecture-commander-grade-trade-offs--lockstep-state-sync)
7. [1-Month Historical Backtest Engine, 5-Step Guided Onboarding & Integration Export APIs](#7-1-month-historical-backtest-engine-5-step-guided-onboarding--integration-export-apis)
8. [REST & Excel Integration API Endpoints](#8-rest--excel-integration-api-endpoints)
9. [Authentication, Proxy Routing, CORS & Storage](#9-authentication-proxy-routing-cors--storage)
10. [Environment Variables, Local Launch, Docker & Render Deployment](#10-environment-variables-local-launch-docker--render-deployment)
11. [QA, Testing, Audit & Drive Sync Commands](#11-qa-testing-audit--drive-sync-commands)

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

## 7. 1-Month Historical Backtest Engine, 5-Step Guided Onboarding & Integration Export APIs

### 7.1 1-Month Historical Backtest / Replay Engine (`backend/core/backtest.py`)
- **Template Generator (`build_backtest_template_csv`, `build_backtest_template_xlsx`):** Emits a 13-column historical log template (`order_id`, `customer`, `sku_name`, `resin`, `color`, `qty_units`, `press_id`, `actual_changeover_hrs`, `actual_purge_scrap_kg`, `actual_overtime_hrs`, `actual_late_hours`, `export_penalty_cost`, `unit_margin`) pre-populated with realistic sample rows.
- **Deterministic Replay (`run_historical_backtest_replay`):** Groups up to 4 weekly batches from the uploaded CSV/XLSX (or 28-order `"sample_30day_log"`), runs OR-Tools CP-SAT with light-to-dark sequencing and container sync against the active plant's physics, and computes `HistoricalBacktestReport`:
  - `actual_vs_optimized`: `actual_purge_scrap_kg` vs. `optimized_purge_scrap_kg`, `actual_changeover_hrs` vs. `optimized_changeover_hrs`, `actual_overtime_hrs` vs. `optimized_overtime_hrs`, `actual_export_penalty_cost` vs. `optimized_export_penalty_cost`.
  - Capacity & ROI metrics: `extra_production_hrs_unlocked`, `extra_sellable_units_unlocked`, `extra_sellable_tons_unlocked`, `total_cash_left_on_floor_1m`, `annualized_cash_left_on_floor` (`× 12`), and `estimated_payback_days` against the annual license reference (`60,000 SAR` / `780,000 EGP`).

### 7.2 Guided "Process-First" 5-Step Onboarding Wizard (`backend/core/onboarding.py`)
- `build_guided_plant_workspace(req: GuidedSetupRequest)` constructs a tailored `PlantDataset` (presses across selected tonnage tiers with backup press compatibility, molds, resin inventory, multi-SKU export container orders, 2-shift or 3-shift workforce roster, and `PlantPhysicsConfig`), runs `validate_plant_data()` and `solve_plant_schedule()` (capped at `<= 2.2s` for Render Free Tier safety), and returns `GuidedSetupResponse` including a 6-item bilingual **"Current Specs Only" Readiness Checklist** (`ReadinessChecklistItem`) confirming zero historical ERP data is required.

### 7.3 Integration-Ready Export Engine (`backend/core/excel_io.py`)
- `export_integration_schedule_workbook()`: 4-sheet `.xlsx` workbook (`Press Schedule`, `Workforce Shifts`, `KPIs & Savings`, `Risk Radar`).
- `export_integration_schedule_csv()`: Flat UTF-8 `.csv` press schedule with container group and wait hours.
- `export_integration_erp_payload()`: Versioned `mini-dios-plastics-erp/v1.3` JSON payload (`work_orders`, `mold_maintenance_windows`, `container_consolidations`, `workforce_shift_roster`, `kpis_and_financials`, `risk_alerts`) ready for Odoo MRP (`mrp.production` / `mrp.workorder`) and SAP Business One (`OWOR`).

---

## 8. REST & Excel Integration API Endpoints

Defined in `backend/api/routes.py` under prefix `/api`:
- `GET /api/health` — Service status & OR-Tools version.
- `GET /api/demo-data` — Seeded `PlantDataset` (with 4 export container groups) + default `SolverConfig` (`container_sync_enabled=True`).
- `POST /api/validate` — Accepts JSON (`{dataset, config?}`) or `multipart/form-data` 4-tab `.xlsx` workbook.
- `POST /api/solve` — Full Press + Workforce CP-SAT + Financials + Risk Radar + SQLite audit save.
- `POST /api/workforce/solve` — Fast labor-only re-solve against an existing Press Gantt.
- `POST /api/copilot/ask` — Executes Copilot 3-tool pipeline + `financial_tradeoff_summary`.
- `GET /api/backtest/template?format=csv|xlsx` — Downloads 13-column historical backtest template.
- `POST /api/backtest/replay` — Runs 1-Month Historical Backtest Replay from uploaded CSV/XLSX or `mode="sample_30day_log"`.
- `POST /api/onboarding/generate` — Generates and solves a 5-step guided plant workspace + Readiness Checklist.
- `GET /api/export/schedule.xlsx`, `GET /api/export/schedule.csv`, `GET /api/export/erp-payload.json` — Sandbox-scoped live schedule exports (auto-solves active workspace if needed).
- `GET/POST /api/workspaces`, `GET/DELETE /api/workspaces/{workspace_id}` — Saved plant workspace CRUD.
- `GET /api/audit-log`, `GET /api/audit-log/{run_id}` — Cryptographic audit trail retrieval.
- `GET /api/template.xlsx`, `POST /api/export-dataset.xlsx`, `POST /api/export-brief.xlsx` — Programmatic Excel bridge.

---

## 9. Authentication, Proxy Routing, CORS & Storage

- **Hosted Access Gate (`LoginGate.tsx` + backend auth):** Enabled via `AUTH_ENABLED=true`. Signed session cookies use `AUTH_SECRET_KEY`. Multi-client passcodes configured via `DEMO_ACCESS_CODES` (`Executive Demo:DIOS-2026,Alexandria Plant:ALEX-2026,Riyadh Plant:KSA-2026`).
- **Frontend → Backend Proxy (`frontend/src/app/api/[...path]/route.ts`):** Proxies `/api/*` internally to `BACKEND_INTERNAL_URL` with an explicit header allowlist and self-proxy loop guard.
- **Storage:** Persistent SQLite at `/data/audit.db` (`dios-sqlite-data` 1GB Render disk or `dios-audit-data` Docker volume).

---

## 10. Environment Variables, Local Launch, Docker & Render Deployment

### Environment Variable Names (Never Store Real Values in Docs)
- **Backend (`backend/.env` / Render API service):** `PORT`, `DIOS_AUDIT_DB`, `AUTH_ENABLED`, `AUTH_SECRET_KEY`, `DEMO_ACCESS_CODES`, `ADMIN_PASSWORD`, `ALLOW_INSTANT_DEMO`, `COPILOT_MAX_LIVE_CALLS_PER_HOUR`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `OFFLINE_MODE`, `ALLOWED_ORIGINS`, `CORS_ORIGINS`.
- **Frontend (Render Web service):** `PORT`, `NEXT_PUBLIC_API_BASE`, `NEXT_PUBLIC_ALLOW_INSTANT_DEMO`, `BACKEND_INTERNAL_URL`.

---

## 11. QA, Testing, Audit & Drive Sync Commands

- **Backend unit & API tests:** `pytest` inside `mini-dios-workforce/backend/`
- **Quick ripple audit / full audit:** `python scripts/run_audit.py --quick` / `python scripts/run_audit.py`
- **Frontend production build:** `npm.cmd run build` (with `mini-dios-workforce\.tools\node` on `PATH`) inside `mini-dios-workforce/frontend/`
- **Drive sync unit tests:** `python -m unittest tests/test_drive_sync.py -v`
- **Drive sync dry-run / live API sync:** `python scripts/sync_docs_to_drive.py --dry-run` / `python scripts/sync_docs_to_drive.py`
- **Antigravity `gdrive` CLI in-place update:** `gdrive mutate update <FILE_ID> <local.md> --mime-type "application/vnd.google-apps.document"`
