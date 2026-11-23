# Mini-DIOS Plastics — Master Documentation Changelog

All updates to the canonical Master Living Documents (`docs/MASTER_USER_GUIDE_AND_MANUAL.md` and `docs/MASTER_PLAYBOOK.md`) are logged chronologically below.

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
