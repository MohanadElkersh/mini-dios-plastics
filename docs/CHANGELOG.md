# Mini-DIOS Plastics — Master Documentation Changelog

All updates to the canonical Master Living Documents (`docs/MASTER_USER_GUIDE_AND_MANUAL.md`, `docs/MASTER_PLAYBOOK.md`, and `docs/ROADMAP_AND_BACKLOG.md`) are logged chronologically below.

---

## v1.9 (Visual Decision Intelligence Blueprint & Causal Trace Inspector + Standalone Solver Upgrade Brief) — 2026-11-28

### Application & Documentation Changes
- **4-Tab Visual Decision Intelligence Blueprint & Causal Trace Inspector (`frontend/src/components/DIBlueprintModal.tsx`, `CausalDiagramView.tsx`, `DMNInspectorView.tsx`, `BPMNFlowView.tsx`, `ArchOntologyView.tsx`):**
  - Built a lightweight, zero-external-graph-dependency (React + inline SVG Bezier curves + CSS Grid) 4-tab visual inspector backed 100% by `GET /api/di/blueprint` (`?format=json`, `?format=bpmn_xml`, `?format=dmn_xml`):
    1. **Sub-Tab 1 (`CausalDiagramView.tsx`):** Interactive 3-column Causal Decision Diagram (`1. Decision Levers & Externals → 2. Intermediate Operational Drivers → 3. Executive Business Outcomes`) with SVG Bezier pathways, live `SAR ↔ EGP` currency formatting, interactive pathway highlighting, and a Causal Attribution Card with 1-click jumps to governing DMN tables and UEM primitives.
    2. **Sub-Tab 2 (`DMNInspectorView.tsx`):** Expandable OMG DMN 1.3 decision table matrices (`DMN_BARREL_PURGE_TRANSITION`, `DMN_MOLD_PM_POLICY`, `DMN_FOOD_GRADE_REGRIND_SAFETY`, `DMN_SHIFT_WORKFORCE_HEADCOUNT`) with Hit Policy badges, deterministic live `FIRED` (`N×`) rule-hit highlighting computed in `backend/adapters/plastics.py` (`_compute_dmn_rule_hit_counts`), a `Show Fired Rules Only` filter, and 1-click DMN 1.3 XML download.
    3. **Sub-Tab 3 (`BPMNFlowView.tsx`):** 4-swimlane OMG BPMN 2.0 workflow visualizer with RTL-safe SVG directional arrows, node execution detail strip (mapped UEM primitive, DMN table binding, timer duration, sequence flow conditions), and 1-click BPMN 2.0 XML download.
    4. **Sub-Tab 4 (`ArchOntologyView.tsx`):** Pre-Solve Architecture Validation banner (`VALID` / `VALID_WITH_WARNINGS` / `BLOCKED`) across `GATE-1-STRUCTURAL`, `GATE-2-CAPABILITY`, and `GATE-3-POLICY`, 6-Primitive `UEMGraph` KPI summary cards, and collapsible Layer 1 `BusinessOntologyGraph` (`EntityTypes` & `SemanticInvariants`).
- **Non-Intrusive Entry Points & Lazy State Sync (`store.tsx`, `DecisionLoopStrip.tsx`, `TradeoffConsole.tsx`, `TopBar.tsx`, `page.tsx`):**
  - Exposed the inspector from `DecisionLoopStrip.tsx` (`Inspect DI Blueprint`), Tab 3 `TradeoffConsole.tsx` (`Causal Trace & Policy Rules (DMN/BPMN)`), and the Admin Engine Switcher card in `TopBar.tsx` (`Open Visual DI Blueprint Inspector`) with lazy loading on modal open and automatic staleness refresh whenever a solve completes.
- **One-Time Standalone Upgrade Brief (`docs/UEM_DI_SOLVER_UPGRADE_BRIEF.md`):**
  - Authored and uploaded the standalone Google Doc **`Mini-DIOS — UEM & 5-Layer DI Solver Upgrade Brief (One-Time Reference)`** covering what changed, why we upgraded, side-by-side `uem_di_v1` vs. `legacy_cpsat_v1` architecture and verified parity benchmarks, and the decision guide on when to use each solver.

---

## v1.8 (5-Layer Decision Intelligence + 6-Primitive UEMGraph Compiler & Two-Way Workforce Coupling) — 2026-11-27

### Application & Architecture Changes
- **Domain-Agnostic 6-Primitive Universal Execution Model (`backend/core/uem.py`, `backend/core/uem_compiler.py`, `backend/core/uem_verify.py`):**
  - Built the 6-primitive `UEMGraph` (`ResourceNode`, `ActivityNode`, `TransitionMatrix`, `CumulativeEnvelope`, `SynchronizationGroup`, `ObjectiveTermSpec`), deterministic OR-Tools CP-SAT compiler (`compile_and_solve_uem`), and independent zero-tolerance post-solve verifier (`verify_uem_solution` checking `UEM-P1..UEM-P6`) with zero plastics-specific vocabulary in core modules.
- **5-Layer Decision Intelligence Stack (`backend/core/di/*`):**
  - **Layer 1 (`ontology_meta.py`):** Formal `BusinessOntologyGraph` (`EntityTypeSpec`, `EntityInstance`, `TypedRelationship`, `SemanticInvariantSpec`).
  - **Layer 2 (`arch_validator.py`):** Pre-solve Business Architecture Validator across 3 formal gates (`GATE-1-STRUCTURAL`, `GATE-2-CAPABILITY`, `GATE-3-POLICY`).
  - **Layer 3 (`bpmn_engine.py`):** OMG BPMN 2.0 workflow engine (`BPMNProcessTemplate`, events, tasks, exclusive/parallel gateways, boundary timer events, topology validator, and standards-compliant OMG BPMN 2.0 XML export).
  - **Layer 4 (`dmn_engine.py`):** Pure-Python OMG DMN 1.3 Decision Table engine (`DMNDecisionTable`, `DMNRegistry`, S-FEEL unary tests, hit policies `UNIQUE`, `FIRST`, `PRIORITY`, `ANY`, `COLLECT`, `COLLECT_SUM/MIN/MAX`, and standards-compliant OMG DMN 1.3 XML export).
  - **Layer 5 (`decision_meta.py`):** Causal Decision Diagram meta-model (`CausalDecisionModel` tracing `DecisionLever -> IntermediateMetric -> DecisionOutcome` pathways).
- **Plastics Domain Adapter & Two-Way Bounded Labor Coupling (`backend/adapters/plastics.py`, `backend/core/solver.py`, `backend/api/routes.py`):**
  - Implemented `backend/adapters/plastics.py` mapping Mini-DIOS Plastics onto the 5-layer DI stack and 6-primitive `UEMGraph`, including two-way bounded workforce-press coupling (soft-overflow `shift_capacity_cap` `CumulativeEnvelope` + max 1 conditional feedback re-solve capped at `<= 2.0s` when `Press_Operator` shortages are detected).
  - Gated behind `USE_UEM_ENGINE` (default `"false"` so legacy `solver.py` remains untouched by default), added sandbox-scoped live Admin Engine Switching (`GET/POST /api/admin/engine-mode`, `get_effective_engine(sandbox_id)`, and the bilingual Admin Engine Switcher modal + TopBar engine indicator pill in `TopBar.tsx` / `store.tsx`), added `optimization_engine` (`"legacy_cpsat_v1"` vs. `"uem_di_v1"`) to `GET /api/health`, and exposed `GET /api/di/blueprint` (`?format=json`, `?format=bpmn_xml`, `?format=dmn_xml`).
  - Verified full parity across all 5 core plastics modes, CTP Quoter, 1-Month Backtest, Offline Copilot, two-way labor shortage feedback, Admin engine switching & sandbox isolation, and a non-plastics Beverage Bottling Plant proof in `backend/tests/test_uem_di_parity.py`.

---

## v1.7 (Neon Cloud Platform Integration — Postgres, Auth, AI Gateway, Functions & Realtime) — 2026-11-27

### Application & Infrastructure Changes
- **Neon Cloud Platform Provisioning (`neon.ts`, `hello.ts`, `.env.local`):**
  - Initialized and deployed Neon branch `production` (`br-bold-hat-bh4fc43k`) on project `broad-pond-82857343` (`org-nameless-sun-74042046`) with all 5 Neon services enabled: **Postgres**, **Neon Auth**, **AI Gateway**, **Functions** (`hello`), and **Realtime**.
- **Full-Stack Neon Wiring (`backend/core/neon_services.py`, `backend/core/audit.py`, `backend/core/auth.py`, `backend/core/copilot.py`, `backend/api/routes.py`, `frontend/src/lib/neon.ts`, `frontend/src/app/api/neon/*`, `DecisionCheckpointsDrawer.tsx`):**
  - **Neon Postgres (`DATABASE_URL`, `DATABASE_URL_UNPOOLED`):** Connected Python `AuditStore` via SQLAlchemy + `psycopg2-binary` (`storage_backend="postgres"`) and Next.js server routes via `@neondatabase/serverless` (`neon()`).
  - **Neon Auth (`NEON_AUTH_BASE_URL`, `NEON_AUTH_JWKS_URL`):** Wired JWKS key discovery and JWT Bearer token verification (`PyJWT` + `PyJWKClient`) into `backend/core/auth.py` alongside `DEMO_ACCESS_CODES`.
  - **Neon Functions (`NEON_BRANCH_ID`, `NEON_FUNCTION_HOST_SUFFIX`):** Wired `@neon/env`'s `functionBaseUrl("hello")` in Next.js and `invoke_neon_function("hello")` in FastAPI (`GET /api/neon/function/hello`).
  - **Neon Realtime (`NEON_REALTIME_URL`, `NEON_REALTIME_SECRET`):** Wired `@neon/realtime/server` (`createRealtime` + `rawSql`, deriving `db` from `DATABASE_URL`) in `GET /api/neon/realtime` and `@neon/realtime/client` (`createRealtimeClient`) live WebSocket subscriptions in `DecisionCheckpointsDrawer.tsx`.
  - **Neon AI Gateway (`NEON_AI_GATEWAY_BASE_URL`, `NEON_AI_GATEWAY_TOKEN`):** Wired authenticated gateway probing (`/v1/models`) and optional Turn-2 Copilot narration (`/openai/v1/chat/completions`) with automatic fallback to Gemini / deterministic offline CP-SAT when account AI Gateway credits are 0.

---

## v1.6 (Release v1.4 — Pilot-Ready Persistence, CTP Rush-Order Quoter & Executive Dispatch) — 2026-11-27

### Application & Documentation Changes
- **Task 1 — Parked Pilot-Pull Constraints Backlog (`docs/ROADMAP_AND_BACKLOG.md`, `docs/MASTER_PLAYBOOK.md`, `docs/technical/TECHNICAL_REFERENCE.md`):**
  - Created `docs/ROADMAP_AND_BACKLOG.md` and added Section 7 to `docs/MASTER_PLAYBOOK.md` documenting our three-tier Pilot-Pull Constraints Backlog in plain business language: Tier 1 (Shared Auxiliary Equipment, Capped/Blocked Cavities, Multi-Stage Dependencies, Order Splitting & Duplicate Molds, Mid-Week Inbound Supply & Packaging Stockouts, Secondary Downstream Bottlenecks), Tier 2 (Plant kVA Transformer Ceilings, Insert-Only Swaps, Thermal Barrel Soak Windows, QC Quarantine Holds, Extrusion Physics), and Tier 3 (Explicit Pilot Scope Traps: IoT sensor polling, 3D WMS rack bin-packing, TMS fleet GPS routing).
  - Added Section 12 (`Deferred CP-SAT Constraint Extensions — Design Notes`) to `docs/technical/TECHNICAL_REFERENCE.md` mapping every Tier 1 and Tier 2 item to its future OR-Tools CP-SAT formulation (`AddCumulative`, cavity scaling, interval precedence, step-function inventory curves), marked clearly as `STATUS: PARKED / NOT YET IMPLEMENTED`.
- **Task 2 — Persistent Database & Decision Checkpoint History (`backend/core/audit.py`, `backend/api/routes.py`, `render.yaml`, `frontend/src/components/DecisionCheckpointsDrawer.tsx`, `ScopeView.tsx`, `store.tsx`):**
  - Upgraded `AuditStore` in `backend/core/audit.py` to support external PostgreSQL via `DATABASE_URL` (`postgres://` → `postgresql://` normalization, remote `sslmode=require`, and Render Free-tier bounded pooling `pool_size=3, max_overflow=2, pool_pre_ping=True`) with automatic fallback to local SQLite (`data/mini_dios.db` / `DIOS_AUDIT_DB`).
  - Added auto-migrated tables scoped by `sandbox_id` and `access_code`: `saved_workspaces`, `pinned_scenarios`, `backtest_runs`, and `decision_checkpoints`.
  - Added `GET /api/checkpoints`, `POST /api/checkpoints`, and `POST /api/checkpoints/{checkpoint_id}/restore`, wired to `DecisionCheckpointsDrawer.tsx` accessible from Tab 1 (`Saved Plant Workspaces`).
- **Task 3 — Capable-to-Promise (CTP) Non-Destructive Rush-Order Quoter (`backend/core/ctp.py`, `backend/api/routes.py`, `frontend/src/components/CTPQuoterModal.tsx`, `ScopeView.tsx`, `TradeoffConsole.tsx`):**
  - Added `POST /api/quote/ctp` (`evaluate_ctp_rush_order`) performing a strictly non-destructive, deep-copied CP-SAT evaluation returning `CTPQuoteResult` (`verdict`, `assigned_press_id`, `scheduled_start_hr`, `scheduled_end_hr`, `slack_or_delay_hrs`, itemized marginal `financial_impact`, `min_breakeven_unit_price`, `bumped_orders` with export cut-off breach flags, `risk_score_before`/`after`, and bilingual Commander-Grade summaries), plus `POST /api/quote/ctp/commit`.
  - Built `CTPQuoterModal.tsx` accessible from Tab 1 and Tab 3 with a 1-click **"Load Sample Rush Order (40k Export)"** demo trigger, **Discard Quote**, and **Accept & Add to Live Schedule**.
- **Task 4 — 1-Click Bilingual Executive PDF & WhatsApp Shift Dispatch (`backend/core/dispatch.py`, `backend/api/routes.py`, `frontend/src/components/WhatsAppDispatchModal.tsx`, `ExecutivePrintReport.tsx`, `ScheduleExportMenu.tsx`, `ExecutiveBriefModal.tsx`, `HistoricalBacktestModal.tsx`, `globals.css`):**
  - Added `POST /api/dispatch/whatsapp` (`format_whatsapp_shift_dispatch`) and `WhatsAppDispatchModal.tsx` (accessible from Tab 4, Tab 6, and Executive Brief) generating deterministic EN and AR shift dispatch messages with **Copy for WhatsApp** and **Share via WhatsApp (`wa.me`)**.
  - Added `ExecutivePrintReport.tsx` and `@media print` rules in `globals.css` (zero Render RAM overhead) triggered from `ExecutiveBriefModal.tsx` and `HistoricalBacktestModal.tsx`.

---

## v1.5 (Commercial & Decision Intelligence Upgrade v1.3) — 2026-11-25 — 1-Month Historical Backtest Replay, 5-Step Guided Onboarding, Container & Warehouse WIP Sync, Commander-Grade Copilot Trade-Offs, ERP Export API & Dual-Audience Executive Brief

### Application Changes
- **Feature 1 — 1-Month Historical Backtest / Replay Engine (`backend/core/backtest.py`, `backend/api/routes.py`, `frontend/src/components/HistoricalBacktestModal.tsx`, `ScopeView.tsx`, `FinancialsView.tsx`):**
  - Added `GET /api/backtest/template?format=csv|xlsx` returning a 13-column historical press-log template (`order_id`, `customer`, `sku_name`, `resin`, `color`, `qty_units`, `press_id`, `actual_changeover_hrs`, `actual_purge_scrap_kg`, `actual_overtime_hrs`, `actual_late_hours`, `export_penalty_cost`, `unit_margin`).
  - Added `POST /api/backtest/replay` accepting either an uploaded CSV/Excel file or a 1-click `"sample_30day_log"` trigger, running deterministic OR-Tools CP-SAT across the historical orders and returning `actual_vs_optimized` metrics (purge scrap saved, changeover hours freed, overtime cut, export penalties avoided, extra sellable units & tons unlocked, 1-month & annualized cash left on the floor, and payback period in days).
  - Built `HistoricalBacktestModal.tsx` accessible from Tab 1 (`ScopeView.tsx`) and Tab 5 (`FinancialsView.tsx`).
- **Feature 2 — Guided "Process-First" 5-Step Onboarding Wizard (`backend/core/onboarding.py`, `backend/api/routes.py`, `frontend/src/components/GuidedOnboardingModal.tsx`, `ScopeView.tsx`):**
  - Added `POST /api/onboarding/generate` and `GuidedOnboardingModal.tsx` interviewing the user in 5 bilingual (`EN` / `AR`) steps: (1) Process & Operating Model (`Injection`/`BlowMolding`/`Extrusion`/`Hybrid`, `MTO`/`MTS`/`Hybrid`, `EGP`/`SAR`), (2) Presses & Backup Logic, (3) Color/Resin Purge & Batch Rules, (4) Workforce & Tariff Rules, and (5) Export & Warehouse Rules.
  - Generates an immediately solved workspace in the user's sandbox alongside a 6-item **"Current Specs Only" Readiness Checklist** reassuring factories that zero historical ERP data is needed.
- **Feature 3 — Finished-Goods Storage & Export-Container Consolidation Coupling (`backend/core/ontology.py`, `seed.py`, `solver.py`, `kpi.py`, `risk_radar.py`, `TopBar.tsx`, `TradeoffConsole.tsx`, `FinancialsView.tsx`):**
  - Extended `ProductionOrder` with `container_group_id` (seeded with 4 multi-SKU export container groups: `CNT-RIYADH-01`, `CNT-JEDDAH-02`, `CNT-AUTO-03`, `CNT-CHEM-04`), `PlantPhysicsConfig` with `fg_storage_capacity_tons` (`22.0t`) and `wip_holding_cost_per_ton_day` (`85.0`), and `SolverConfig` with `container_sync_enabled` (`True` by default).
  - Coupled multi-SKU container completion variables (`cg_ship`, `cg_wait`) into CP-SAT `wc_terms` in `solver.py`, added post-solve container consolidation and finished-goods warehouse utilization sweeps (`ContainerGroupSummary`, `warehouse_utilization_pct`, `peak_warehouse_tons`, `trapped_working_capital`, `wip_holding_days`, `container_wait_delay_hrs`) in `kpi.py`, and added `warehouse_congestion` alerts with bilingual Copilot mitigation prompts in `risk_radar.py`.
  - Added the `Container Sync` toggle to `TopBar.tsx` (desktop & mobile drawer) and Tab 3 (`TradeoffConsole.tsx`), plus Container Consolidation & Warehouse WIP panels in Tab 3 and Tab 5 (`FinancialsView.tsx`).
- **Feature 4 — "Commander-Grade" Financial Trade-Off Explanations in Ops Copilot (`backend/core/copilot.py`, `frontend/src/components/CopilotDrawer.tsx`):**
  - Added deterministic `_compute_financial_tradeoff_summary()` computing exact cost paid vs. value protected and net financial gain (`FinancialTradeoffSummary`) in both live Gemini and offline CP-SAT simulations, rendered in a highlighted **Commander-Grade Financial Trade-Off Callout Box** at the top of every Copilot simulation card.
- **Feature 5 — Integration-Ready Export API (`backend/core/excel_io.py`, `backend/api/routes.py`, `frontend/src/components/ScheduleExportMenu.tsx`, `ExecutiveBriefModal.tsx`, `ProductionGanttView.tsx`, `WorkforceView.tsx`):**
  - Added `GET /api/export/schedule.xlsx` (4 sheets: `Press Schedule`, `Workforce Shifts`, `KPIs & Savings`, `Risk Radar`), `GET /api/export/schedule.csv`, and `GET /api/export/erp-payload.json` (versioned `mini-dios-plastics-erp/v1.3` payload for Odoo / SAP Business One / custom ERPs), wired to `ScheduleExportMenu.tsx` on Tab 4, Tab 6, and `ExecutiveBriefModal.tsx`.
- **Feature 6 — Dual-Audience Executive Brief & Updated Two-Track Docs / Outreach Kit (`frontend/src/components/ExecutiveBriefModal.tsx`, `docs/*`):**
  - Added a 2-tab audience switcher inside `ExecutiveBriefModal.tsx`: **Owner / Chairman View** (Institutional Memory, Ending Department Friction, Working Capital & Annualized Cash Unlocked) vs. **Plant / Production Manager View** (**The Manager's Decision Shield** providing instant mathematical proof for overtime, relief staffing, mold maintenance, and rush-order trade-offs).

### Master Documents Updated
- Updated `docs/MASTER_USER_GUIDE_AND_MANUAL.md`, `docs/MASTER_PLAYBOOK.md`, and `docs/templates-and-drafts/hosted-demo-outreach-pilot-kit-en-ar.md` (Track A — 100% plain human language).
- Updated `docs/technical/TECHNICAL_REFERENCE.md`, `docs/CHANGELOG.md`, and `docs/technical/CODEBASE_AND_UPDATES_LOG.md` (Track B — Separate Technical Track), and synced all documents in-place to Google Drive.

---

## v1.4 — 2026-11-23 — Lockstep Dashboard State Synchronization, Unified Copilot Scenario Bundle & Actionable Risk Radar Mitigations

### Application Changes
- **Unified Copilot Scenario Bundle & Actionable Multi-Lever Mitigations (`backend/core/copilot.py`, `backend/core/risk_radar.py`, `backend/core/solver.py`, `backend/api/routes.py`):**
  - Expanded `CopilotResult` and `_build_copilot_result` so every Operations Copilot simulation returns a self-consistent bundle (`plant_state`, `dataset`, `config`, `weights`, `toggles`, `production_result`, `result`, `workforce_result`, and freshly recomputed `risk_radar`).
  - Added dataset-level operational mitigation levers to `simulate_plant_scenario`: `auto_staff_workforce_gaps` (automatically adds the minimum required relief workers per bottleneck role to eliminate understaffed shift slots), `add_relief_workers`, `workforce_overtime_cap_hrs`, `resin_replenishments`, `complete_mold_pm_ids`, and `clear_press_breakdowns`.
  - Added routing guard (`has_simulation_intent`) in `run_offline_composable_copilot` so Risk Radar mitigation prompts always route to `simulate_plant_scenario` instead of being intercepted by `inspect_bottleneck`.
  - Added export port cut-off safety buffer protection (`6.5h` / `390m`) in `_solve_cpsat_model` (`solver.py`) when `w_otif >= 50` so prioritizing export OTIF pulls export completions ahead of the `< 6.0h` risk zone (`export_at_risk_count: 7 → 0`).
  - Upgraded all 9 `suggested_prompt_en` and `suggested_prompt_ar` templates in `risk_radar.py` to invoke physical + weight mitigations, and updated `pm_done_molds` to union `plan.mold_pm_windows`, `config.scenarios.mold_pm_locks`, and `plan.gantt_blocks` (`block_type == "mold_pm"`).
- **Atomic Lockstep Frontend Store & Applied Delta Feedback Banner (`frontend/src/lib/types.ts`, `store.tsx`, `CopilotDrawer.tsx`, `DecisionLoopStrip.tsx`, `WorkforceView.tsx`, `app/page.tsx`):**
  - Upgraded `applyCopilotScenario(nextCfg, nextRes, nextDataset, prompt)` in `store.tsx` to atomically commit `dataset`, `config`, `result`, and `validation`, compute `AppliedScenarioDelta` (with physical ceiling explanations when a hard physical constraint is hit), and persist to the active workspace.
  - Added signature-based debounced auto-sync (`computeProductionSignature` / `computeFullSignature`) in `store.tsx` so any edit outside Copilot (Studio CRUD, Physics, Trade-Off sliders/disruptions, TopBar toggles, or Workforce roster/weights/rules) automatically re-solves in lockstep.
  - Added the **Before → After Applied Delta Feedback Banner** inside `CopilotDrawer.tsx` and at the top of `page.tsx`, plus worker headcount telemetry (`W`) on the `1. Model` badge in `DecisionLoopStrip.tsx`.

### Master Documents Updated
- Updated `docs/MASTER_USER_GUIDE_AND_MANUAL.md`: Section 3 (Proactive Risk Radar actionable mitigations and automatic lockstep dashboard sync) and Section 4 (Operations Copilot unified apply & Before → After Applied Summary Banner).
- Updated `docs/MASTER_PLAYBOOK.md`: Section 3 (Minute 6–8 live Risk Radar mitigation & Before → After Applied Summary Banner demo flow).
- Updated `docs/technical/TECHNICAL_REFERENCE.md`: Sections 3, 5, and 6 (`v1.4` export safety buffer formulation, unified `CopilotResult` bundle, and signature-based lockstep store architecture).

---

## v1.3 — 2026-11-23 — Mobile-First Responsive UX Overhaul (375px–430px iOS/Android/WhatsApp in EN LTR & AR RTL)

### Application Changes
- **Global Mobile Ergonomics & Safe Areas (`frontend/src/app/globals.css`, `layout.tsx`, `page.tsx`, `lib/i18n.ts`):**
  - Switched full-height shells, drawers, and modals from `vh`/`min-h-screen` to `dvh`/`min-h-dvh` with `viewportFit: "cover"` and safe-area bottom inset padding (`env(safe-area-inset-bottom)`).
  - Enforced `16px` (`text-base`) minimum font size on all `<input>`, `<select>`, and `<textarea>` controls on mobile viewports (`< 768px`) to prevent iOS Safari forced auto-zoom, enlarged `.dios-slider` range thumbs to `24px × 24px` with vertical touch padding on mobile, enforced `≥ 44px` touch targets on primary controls, and enforced `letter-spacing: normal` across Arabic (`html[dir="rtl"]`) so connected glyphs never break.
- **Compact Mobile Header, Controls Drawer & Sticky Bottom Action Bar (`frontend/src/components/TopBar.tsx`, `DecisionLoopStrip.tsx`, `LoginGate.tsx`):**
  - Preserved the full desktop (`lg:`) top bar while condensing mobile (`< lg`) into a compact top row (`Brand`, `SAR/EGP`, `العربية/EN`, and `Controls` / `الإعدادات` slide-over drawer button) plus a **Sticky Bottom Action Bar (`lg:hidden`)** pinning **`Run CP-SAT Optimization`** and **`Ops Copilot`** for one-thumb mobile access.
  - Added the **Mobile Controls Drawer** containing `Peak Tariff Avoid`, `Ramadan Shift`, `Auto PM`, `Executive Brief`, solver status telemetry, and Hosted Sandbox (`Reset Sandbox`, `Sign Out`) controls.
  - Converted the 6 main workspace tabs and the 5-stage `Decision Intelligence Loop` into single-row horizontal snap-scroll strips on mobile with active-tab auto-scrolling, and updated `LoginGate.tsx` with `dir="ltr"` on passcode inputs so codes like `ALEX-2026` type cleanly in Arabic RTL.
- **Responsive Studio Cards, Keyboard-Safe Modals, Touch Gantt & Copilot Drawer (`ScopeView.tsx`, `DataStudioView.tsx`, `QuickAddModal.tsx`, `ExecutiveBriefModal.tsx`, `studio/ConfirmDeleteModal.tsx`, `PressesEditor.tsx`, `MoldsEditor.tsx`, `ResinsEditor.tsx`, `OrdersEditor.tsx`, `PhysicsEditor.tsx`, `TradeoffConsole.tsx`, `PinScenarioButton.tsx`, `ScenarioComparisonMatrix.tsx`, `RiskRadarPanel.tsx`, `ProductionGanttView.tsx`, `FinancialsView.tsx`, `WorkforceView.tsx`, `CopilotDrawer.tsx`):**
  - Added stacked mobile cards (`md:hidden`) for Presses, Molds, Resins, and Production Orders in Tab 2 while preserving desktop tables (`hidden md:block`) with sticky first columns.
  - Upgraded all modals and the `Ops Copilot` drawer (`92dvh` on mobile) with scrollable inner bodies and sticky footers/chat input bars pinned above the mobile keyboard.
  - Added sticky inline-start columns (`sticky start-0`) and mobile swipe hints (`Swipe timeline →` / `اسحب الجدول ←`, `Swipe table →` / `اسحب للمقارنة ←`) to `ProductionGanttView.tsx`, `ScenarioComparisonMatrix.tsx`, `FinancialsView.tsx`, and `WorkforceView.tsx`, plus **Tap-to-Inspect** block selection on the Press Gantt and 100% CSS logical directional properties (`ms-*`, `me-*`, `ps-*`, `pe-*`, `start-*`, `end-*`, `text-start`, `text-end`).

### Master Documents Updated
- Updated `docs/MASTER_USER_GUIDE_AND_MANUAL.md`: Section 2.4 & 2.4b (Mobile Controls Drawer, Sticky Bottom Action Bar, and Mobile-First Bilingual Ergonomics) and Section 3 (Tab 4 Sticky Press Column & Tap-to-Inspect Gantt).
- Updated `docs/MASTER_PLAYBOOK.md`: Section 4.1 (Mobile-ready WhatsApp sandbox demo positioning).

---

## v1.2 — 2026-11-22 — Boardroom Pin & Compare (A/B/C) + Shareable Hosted Demo & Login Gate

### Application Changes
- **Boardroom Side-by-Side Scenario Comparison (`frontend/src/lib/types.ts`, `store.tsx`, `i18n.ts`, `PinScenarioButton.tsx`, `ScenarioComparisonMatrix.tsx`, `TradeoffConsole.tsx`, `FinancialsView.tsx`, `CopilotDrawer.tsx`):**
  - Added immutable `pinnedScenarios` (max 3 slots: `A`, `B`, `C`) persisted per session in `localStorage`, capturing the exact deterministic Python `SolveResult`, `SolverConfig`, and `PlantDataset` (zero JS metric fabrication).
  - Added one-click `Pin Scenario (X/3)` controls on Tab 3, Tab 5, and `Pin for Comparison` inside the Operations Copilot drawer (with clean slot-replacement popover when 3/3 full).
  - Added collapsible `Scenario Comparison Matrix (A vs. B vs. C)` visible on Tab 3 and Tab 5 comparing Weekly Net Profit & Margin, Weekly & Annualized Savings vs. FIFO, OTIF & Late Orders, Purge Scrap & Changeover Hours, Direct Labor & Overtime, Risk Radar Exposure, and Active Disruptions/Toggles — with emerald `Best` badges, `+ / -` deltas vs. `Slot A`, live `SAR <-> EGP` and `EN (LTR) <-> AR (RTL)` reactivity, inline Rename, and `Promote to Active Plan`.
- **Shareable Hosted Demo Architecture & Branded Login Gate (`backend/core/auth.py`, `core/audit.py`, `core/copilot.py`, `api/routes.py`, `main.py`, `.env.example`, `frontend/next.config.ts`, `lib/api.ts`, `components/LoginGate.tsx`, `TopBar.tsx`, `app/page.tsx`):**
  - Added HMAC-SHA256 `HttpOnly` `SameSite=Lax` signed session cookie authentication (`AUTH_ENABLED`, `AUTH_SECRET_KEY`, `DEMO_ACCESS_CODES`, `ADMIN_PASSWORD`, `ALLOW_INSTANT_DEMO`) with per-IP login brute-force rate limiting and `/api/auth/login`, `/api/auth/logout`, `/api/auth/me` endpoints.
  - Added SQLite per-session isolation (`session_id` on `plastics_workspaces` and `plastics_audit_runs` with automatic migration) plus `POST /api/sandbox/reset` and TopBar `Reset Sandbox` / `Sign Out` / client badge controls.
  - Added per-session hourly Gemini quota shield (`COPILOT_MAX_LIVE_CALLS_PER_HOUR`, default `15`) that automatically falls back to the deterministic offline OR-Tools CP-SAT engine with a bilingual notice.
  - Added Next.js `/api/*` proxy rewrites (`BACKEND_INTERNAL_URL`), explicit `ALLOWED_ORIGINS` CORS credentials support, production `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.prod.yml`, and root `render.yaml` blueprint.
  - Added `backend/tests/test_auth_and_sandbox.py` verifying 401 gating, cookie login/logout, multi-prospect workspace isolation, sandbox reset, and Copilot quota shield fallback.

### Master Documents Updated
- Updated `docs/MASTER_USER_GUIDE_AND_MANUAL.md`: Section 2.2b (Hosted Demo Docker/Render & Multi-Prospect Isolation), Section 2.3 (Auth Gate & Copilot Quota Shield env vars), Section 2.4 (Hosted TopBar session controls), and Section 3 (Tab 3 & Tab 5 Boardroom Pin & Compare A/B/C Matrix).
- Updated `docs/MASTER_PLAYBOOK.md`: Section 3 (Hosted demo access codes and Pin & Compare boardroom close).

---

## v1.1 — 2026-11-22 — Quick Wins Bundle (CP-SAT Speed & Optimality, Startup Dedup, Executive Brief Localization)

### Application Changes
- **`mini-dios-workforce/backend/core/solver.py`**: Expanded feasible FIFO `AddHint` warm-starts to cover `scheduled`, press assignments, chronological `AddCircuit` arcs, and exact 0.1 kg virgin/regrind splits; set `relative_gap_limit = 0.001` for faster `OPTIMAL` convergence without degrading weekly savings.
- **`mini-dios-workforce/backend/core/workforce_solver.py`**: Added lexicographic symmetry breaking across strictly identical workers (same role, certifications, pay/OT/cap, shift preference, and unavailable days) with symmetry-aligned warm-start hints, plus deterministic parallel search (`num_workers = 4`, `interleave_search = True`), lifting Workforce CP-SAT from `FEASIBLE` to `OPTIMAL` across standard, disruption, Auto PM, and callout scenarios and increasing weekly savings by `+192` to `+576 SAR/wk`.
- **`mini-dios-workforce/frontend/src/lib/store.tsx`**: Eliminated redundant `validatePlantJson()` call immediately prior to `solvePlantScheduleApi()` in `loadDemo(true)` and deduplicated startup `loadWorkspaces()`.
- **`mini-dios-workforce/frontend/src/components/ExecutiveBriefModal.tsx` & `frontend/src/lib/i18n.ts`**: Added `Escape` key dismissal and localized all 10 remaining resin audit table headers and solver telemetry labels in English and Arabic (RTL).

### Master Documents Updated
- Updated `docs/MASTER_USER_GUIDE_AND_MANUAL.md`: Section 3 (Tab 5 Executive Brief Modal localization & `Escape` shortcut) and Section 5.3 (Press & Workforce CP-SAT warm-start, symmetry breaking, and deterministic parallel search details).

---

## v1.2 — 2026-11-23 — Two-Track Documentation Standard & Technical Reference Separation

### Documentation Architecture Upgrade
- Enforced permanent **Two-Track Documentation Standard** across `.agents/rules/living-docs-sync.md`, `.agents/agents/docs-commercial-architect.md`, `.agents/skills/sync-master-docs/SKILL.md`, and `.agents/skills/create-client-doc/SKILL.md`.
- Created dedicated Track B Technical Reference at `docs/technical/TECHNICAL_REFERENCE.md` consolidating all system architecture, `render.yaml` / Docker deployment specs, environment variable names (zero secrets), REST/Excel API routes, CP-SAT (`HC1–HC6`, `WHC1–WHC5`) formulations, financial/Risk Radar math, and QA/test commands.
- Audited and rewrote all Track A human-friendly documents (`docs/MASTER_USER_GUIDE_AND_MANUAL.md`, `docs/MASTER_PLAYBOOK.md`, and `docs/templates-and-drafts/hosted-demo-outreach-pilot-kit-en-ar.md`) to pass the Normal Human Test with zero raw technicalities, code blocks, or developer jargon.
- Updated `scripts/sync_docs_to_drive.py` and Google Drive layout to route Technical Reference & Living Changelog into a dedicated `Technical Specs (For Engineers & IT)` Drive subfolder while keeping the root Drive folder 100% executive-friendly.

---

## v1.0 — 2026-11-22 — Full Mini-DIOS Plastics Baseline

### Verified Live Application Modules Documented
- **Backend (`mini-dios-workforce/backend/`):**
  - `core/ontology.py`: Domain ontology (`PressMachine`, `Mold`, `ResinStock`, `ProductionOrder`, `FactoryWorker`, `PlantPhysicsConfig`, `WorkforceConfig`, `SolverConfig`, `ScenarioDisruptions`), deterministic physics helpers (`order_shots`, `order_duration_mins`, `order_gross_weight_kg`, `transition_penalty`, `peak_overlap_mins`, `ramadan_labor_multiplier`), and Pre-Solve Plant Anomaly Validator (`validate_plant_data`).
  - `core/solver.py` & `core/verify.py`: Deterministic Google OR-Tools CP-SAT parallel-machine scheduling engine (`AddCircuit` + `AddNoOverlap`), Naive FIFO Baseline comparator, Autonomous Preventive Maintenance (`Auto PM`) co-optimization, cryptographic SHA-256 audit hashes, and independent `HC1–HC6` hard-constraint verification.
  - `core/workforce_solver.py`: Press-coupled 5-role Workforce CP-SAT roster optimizer (`Press_Operator`, `Mold_Technician`, `QC_Inspector`, `Material_Handler`, `Shift_Supervisor`), Naive Static Rotation baseline, Ramadan `4×6h` / `36h` cap mode, sick-callout simulation, and independent `WHC1–WHC5` verification.
  - `core/financials.py` & `core/kpi.py`: Zero-LLM-math side-by-side weekly P&L reconciliation (zero double-counting), savings breakdown, monthly/annualized projections, unlocked capacity revenue potential, and per-order profitability.
  - `core/risk_radar.py`: Deterministic Proactive Delay & Bottleneck Risk Radar (late/tight-slack exports, minute-by-minute resin silo depletion clock, press choke points, post-week mold shot-limit trajectory, and zero-buffer shift fragility).
  - `core/copilot.py`: Unlimited Composable Operations Copilot (`gemini-4-hydrogen` with 15s `HttpOptions` timeout & `thinking_level="low"` + deterministic EN/AR offline fallback parser) executing 3 CP-SAT tools (`simulate_plant_scenario`, `inspect_bottleneck`, `compare_two_strategies`).
  - `core/seed.py` & `api/routes.py`: Seeded 6-press Delta & Riyadh Polymer Packaging Plant (6 presses, 10 molds, 5 resins, 24 orders, 28 floor workers), SQLite workspaces & audit log, and FastAPI REST + optional Excel API endpoints.
- **Frontend (`mini-dios-workforce/frontend/src/`):**
  - `TopBar.tsx` & `DecisionLoopStrip.tsx`: Global toggles (`Peak Tariff Avoid`, `Ramadan Shift`, `Auto PM`, `SAR`/`EGP`, `English`/`العربية` RTL), `Ops Copilot`, `Run CP-SAT Optimization`, `Executive Brief` modal trigger, and 5-stage Decision Intelligence Loop Strip.
  - All 6 tabs: Tab 1 (`ScopeView.tsx` + `RiskRadarPanel.tsx`), Tab 2 (`DataStudioView.tsx` + 5 studio editors), Tab 3 (`TradeoffConsole.tsx`), Tab 4 (`ProductionGanttView.tsx`), Tab 5 (`FinancialsView.tsx`), Tab 6 (`WorkforceView.tsx`), plus `ExecutiveBriefModal.tsx` and `CopilotDrawer.tsx`.
- **Operations & Deployment (`mini-dios-workforce/`):**
  - Windows `start.bat` / `stop.bat`, on-prem `docker-compose.yml`, and `backend/.env.example`.

### Master Documents Created
- Created `docs/MASTER_USER_GUIDE_AND_MANUAL.md` (Sections 1–6: Executive Overview, Quick Start & Docker, Tab-by-Tab Guide, Operations Copilot, Mathematical & Technical Appendix, Troubleshooting & FAQ).
- Created `docs/MASTER_PLAYBOOK.md` (Sections 1–6: Egypt/KSA Positioning, ICP & Discovery, 10-Min Live Demo Script, EN/AR Outreach & Email Library, EGP/SAR Enterprise Proposal Template, Objection Handling Playbook).
- Registered workspace agent (`.agents/agents/docs-commercial-architect.md`), always-on sync rule (`.agents/rules/living-docs-sync.md`), and reusable skills (`.agents/skills/sync-master-docs/SKILL.md`, `.agents/skills/create-client-doc/SKILL.md`).
