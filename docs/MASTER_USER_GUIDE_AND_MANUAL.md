# Mini-DIOS Plastics — Master User Guide & Operations Manual

> **Canonical Single Source of Truth** | **Edition:** Egypt & KSA Industrial Plastics (Injection, Blow Molding & Extrusion)
> **Engine:** 100% Deterministic Google OR-Tools CP-SAT • **Zero LLM Arithmetic** • **Zero-File-Transfer Executive UI**
> **Last Synchronized with Codebase:** 2026-11-22 (`v1.0`)

---

## Table of Contents

1. [Section 1 — Executive Overview (The "Why")](#section-1--executive-overview-the-why)
2. [Section 2 — Quick Start & Launching Locally (Windows & On-Prem Docker)](#section-2--quick-start--launching-locally-windows--on-prem-docker)
3. [Section 3 — Complete Tab-by-Tab User Guide (Exact UI Labels & Workflows)](#section-3--complete-tab-by-tab-user-guide-exact-ui-labels--workflows)
   - [Global Navigation: TopBar & Decision Intelligence Loop Strip](#global-navigation-topbar--decision-intelligence-loop-strip)
   - [Tab 1: `1. Plant Scope & Readiness`](#tab-1-1-plant-scope--readiness)
   - [Tab 2: `2. Plant Data & Parameters`](#tab-2-2-plant-data--parameters)
   - [Tab 3: `3. Trade-Off & Scenario Composer`](#tab-3-3-trade-off--scenario-composer)
   - [Tab 4: `4. Press Gantt & Color Sequence`](#tab-4-4-press-gantt--color-sequence)
   - [Tab 5: `5. Revenue & Savings`](#tab-5-5-revenue--savings)
   - [Tab 6: `6. Workforce & Shifts`](#tab-6-6-workforce--shifts)
4. [Section 4 — Using the Operations Copilot (EN & AR)](#section-4--using-the-operations-copilot-en--ar)
5. [Section 5 — Mathematical & Technical Architecture Appendix](#section-5--mathematical--technical-architecture-appendix)
6. [Section 6 — Troubleshooting & Operator FAQ](#section-6--troubleshooting--operator-faq)

---

## Section 1 — Executive Overview (The "Why")

### 1.1 What Is Mini-DIOS Plastics?
**Mini-DIOS Plastics** (Decision Intelligence Operating System) is a deterministic production scheduling, floor-workforce rostering, financial P&L reconciliation, and proactive risk-monitoring platform built specifically for **plastics manufacturing plants** (Injection Molding, Blow Molding, and Extrusion) operating across **Egypt** and **Saudi Arabia (KSA)**.

Out of the box, the platform ships with a realistic seeded demo factory — **Delta & Riyadh Polymer Packaging Plant** — featuring **6 presses** (150T–650T Injection + 1 Blow Molding line `P-BM01`), **10 physical molds** (`M-01` to `M-10`), **5 resin grades** (`PP`, `HDPE`, `PET`, `ABS`, `LDPE`), **24 weekly production orders** across a **168-hour** (Sun–Sat) planning horizon, and **28 floor workers** across 5 industrial roles.

### 1.2 The 6 Core Profit Bleeds in Plastic Manufacturing
Traditional spreadsheet scheduling (First-In-First-Out / due-date sorting) silently destroys factory EBITDA through six compounding physical realities:

1. **Asymmetric Color & Resin Purge Scrap:** Switching from a dark pigment (e.g., `Black` or `Red`) back to a light pigment (`Natural` or `White`) requires heavy barrel purging and screw cleanout (default **135 min / 32 kg** of virgin resin wasted) versus fast inline light-to-dark transitions (default **25 min / 4 kg**). Switching between incompatible resin families (e.g., `PP`/`HDPE`/`LDPE` polyolefins ↔ `PET`/`ABS`/`PVC`) triggers a full-barrel purge (default **180 min / 48 kg**).
2. **Excessive Physical Mold Changeovers:** Swapping heavy multi-cavity hot-runner or cold-runner molds consumes **80–155 minutes** of press downtime plus **4–10 kg** of startup runner/thermal stabilization scrap—and keeps barrel heaters burning at **55%** of full molding kWh while producing zero sellable parts.
3. **Press–Mold Tonnage & Hot-Runner Mismatches:** Scheduling a hot-runner mold onto a cold-runner-only press, or double-booking a single physical mold across two parallel presses simultaneously, causes floor chaos and last-minute rescheduling.
4. **Unplanned Mold Breakdowns & Shot-Count Overshoots:** Running a mold past its rated maintenance shot interval (e.g., `M-04` at **96.4%** of its 500,000-shot limit) risks catastrophic cavity damage and multi-day unscheduled stoppages.
5. **Hygroscopic Resin Pre-Drying Delays:** `PET` and `ABS` require mandatory dehumidifying drying lead times (default **6 hours**) before injection can start; ignoring drying floors causes splay defects, rejected lots, and missed export cut-offs.
6. **Peak Electricity Tariffs & Uncoupled Shift Overtime:** Running high-tonnage presses (`500T`–`650T`) blindly through MENA industrial peak electricity windows (`13:00–17:00`, **+40%** kWh surcharge) and running a static 6-day workforce rotation that ignores actual press load and mold-changeover peaks inflates utility bills and overtime payroll.

### 1.3 Why Deterministic Operations Research (OR-Tools CP-SAT) Beats Spreadsheets and LLMs

| Capability | Manual Excel / FIFO | Generic LLM / Chatbot | **Mini-DIOS Plastics (OR-Tools CP-SAT)** |
| :--- | :--- | :--- | :--- |
| **Mathematical Optimality** | Greedy due-date order; misses light-to-dark & mold batching | Probabilistic text prediction; cannot solve combinatorial scheduling | **Exact Constraint Programming (`AddCircuit` + `AddNoOverlap`)** solving in < 5 seconds |
| **Arithmetic & P&L Accuracy** | Prone to broken formulas and double-counting | Hallucinates numbers, hours, and totals | **Zero LLM Arithmetic:** 100% deterministic Python math verified to the cent |
| **Hard-Constraint Safety** | Violated under rush orders or breakdowns | Cannot guarantee feasibility | **11 Hard Constraints** (6 Press `HC1–HC6` + 5 Workforce `WHC1–WHC5`) independently verified post-solve |
| **Historical Data Required** | N/A | Requires massive training / RAG pipelines | **Zero historical ML training data required** — runs Day 1 from current presses, molds, resins & orders |
| **Auditability & Repeatability** | No audit trail | Non-deterministic | **Cryptographic SHA-256 hashes** of inputs & schedules persisted in local SQLite (`audit.db`) |

---

## Section 2 — Quick Start & Launching Locally (Windows & On-Prem Docker)

### 2.1 One-Click Windows Launch (Development / Executive Demo)
All application files reside inside `mini-dios-workforce/`.

1. **Start both servers:** Double-click `mini-dios-workforce\start.bat` (or run it from Command Prompt / PowerShell).
   - Automatically locates Python (`\.venv\Scripts\python.exe`, `backend\.venv\Scripts\python.exe`, or `%USERPROFILE%\.venv\Scripts\python.exe`) and Node.js (`\.tools\node\npm.cmd` or system PATH).
   - Starts **FastAPI + OR-Tools CP-SAT Backend** on `http://localhost:8000` (Swagger API docs at `http://localhost:8000/docs`).
   - Starts **Next.js Executive Command Center** on `http://localhost:3000`.
   - Automatically opens `http://localhost:3000` in your default browser after 4 seconds.
2. **Stop both servers cleanly:** Double-click `mini-dios-workforce\stop.bat`.
   - Terminates all processes listening on ports `8000` and `3000` and closes the Mini-DIOS terminal windows.

### 2.2 On-Premises Docker Deployment (Factory LAN / Air-Gapped Server)
For factory on-prem servers (Egypt on-prem or KSA SDAIA/PDPL private cloud):

```bash
cd mini-dios-workforce
docker compose up -d --build
```

- **Backend container (`mini-dios-backend`):** Exposes port `8000`, mounts persistent SQLite audit & workspace storage volume `dios-audit-data:/data` (`DIOS_AUDIT_DB=/data/audit.db`), and runs a `/api/health` healthcheck every 15s.
- **Frontend container (`mini-dios-frontend`):** Exposes port `3000` and waits for `backend` to report `service_healthy`.
- To shut down: `docker compose down` (preserves `dios-audit-data` volume).

### 2.2b Shareable Hosted Executive Demo & Login Gate (`docker-compose.prod.yml` & `render.yaml`)
To host a shareable public HTTPS demo for multiple factory owners in Egypt and Saudi Arabia:
- **Docker Production Stack:** Run `docker compose -f docker-compose.prod.yml up --build -d` (sets `AUTH_ENABLED=true`, persistent SQLite volume `dios-prod-audit-data:/data`, healthchecks, and Next.js `/api/*` proxy via `BACKEND_INTERNAL_URL=http://backend:8000`).
- **Single-Click Render Blueprint:** Deploy directly from the root `render.yaml`, which provisions the FastAPI backend (with 1 GB persistent disk at `/data`) and the Next.js standalone frontend wired via `BACKEND_INTERNAL_URL`.
- **Same-Origin Cookie Security:** Next.js proxies `/api/:path*` to `BACKEND_INTERNAL_URL`, allowing `HttpOnly`, `SameSite=Lax` HMAC-SHA256 signed cookies (`dios_session`) to work cleanly behind HTTPS without cross-site cookie issues.
- **Multi-Prospect Sandbox Isolation:** Every authenticated session receives an isolated `session_id` in SQLite (`plastics_workspaces` and `plastics_audit_runs`), so concurrent prospects never overwrite each other's machines, prices, or orders. Click **`Reset Sandbox`** (`إعادة ضبط البيئة`) in the TopBar (`POST /api/sandbox/reset`) to restore only your session's plant.

### 2.3 Configuring `backend/.env` (Live Gemini Copilot, Auth Gate & Quota Shield)
Edit `mini-dios-workforce/backend/.env` (template in `backend/.env.example`):

```env
GEMINI_API_KEY=
GEMINI_MODEL=gemini-4-hydrogen
OFFLINE_MODE=false

AUTH_ENABLED=false
AUTH_SECRET_KEY=change-me-to-a-long-random-32-byte-secret
DEMO_ACCESS_CODES=Executive Demo:DIOS-2026,Alexandria Plant:ALEX-2026,Riyadh Plant:KSA-2026
ADMIN_PASSWORD=
ALLOW_INSTANT_DEMO=false
COPILOT_MAX_LIVE_CALLS_PER_HOUR=15
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

- **Live Gemini Tool-Calling Mode:** Set `GEMINI_API_KEY=<your_key>` and `OFFLINE_MODE=false`. Gemini (`gemini-4-hydrogen` with `thinking_level="low"` and a strict 15-second `HttpOptions` timeout) translates natural-language EN/AR requests into structured arguments for the 3 deterministic CP-SAT tools and narrates the exact Python-computed outputs.
- **Per-Session Copilot Quota Shield:** `COPILOT_MAX_LIVE_CALLS_PER_HOUR` (default `15`) caps live Gemini calls per session per rolling hour. If a hosted guest exceeds the cap, `/api/copilot/ask` automatically falls back to the deterministic offline OR-Tools CP-SAT engine with a bilingual notice instead of returning an error or draining API credits.
- **Hosted Login Gate (`AUTH_ENABLED=true`):** Protects all operational `/api/*` endpoints behind `POST /api/auth/login`, `POST /api/auth/logout`, and `GET /api/auth/me` (with per-IP brute-force rate limiting; `/api/health` and `/api/auth/*` remain public). Set `NEXT_PUBLIC_ALLOW_INSTANT_DEMO=true` and `ALLOW_INSTANT_DEMO=true` to show the optional **"Enter Guided Demo"** button on the branded login screen. Keep `AUTH_ENABLED=false` for frictionless local `start.bat` usage.
- **100% Offline / Air-Gapped On-Prem Mode:** Leave `GEMINI_API_KEY` blank **or** set `OFFLINE_MODE=true`. Zero external API calls leave the factory network. The Operations Copilot automatically routes every English and Arabic prompt through the built-in **Deterministic Offline Composable Parser**, executing the exact same 3 OR-Tools CP-SAT tools locally.

### 2.4 Global TopBar Toggles (Live Across All 6 Tabs)
Located in the sticky top header (`TopBar`):

| Control | EN Label / AR Label | Exact Behavior |
| :--- | :--- | :--- |
| **Peak Tariff Avoid** | `Peak Tariff Avoid` / `تجنب ذروة الكهرباء` (`ON`/`OFF`) | Activates daily peak electricity surcharge (default `13:00–17:00`, `1.4x` = **+40%** kWh) in CP-SAT and shades peak bands on the Press Gantt. |
| **Ramadan Shift Mode** | `Ramadan Shift` / `وردية رمضان` (`ON`/`OFF`) | Enforces daily `18:00–20:00` Iftar changeover blackout on all presses, switches Tab 6 workforce to **4 × 6h shifts** (`Night 00–06`, `Morning 06–12`, `Afternoon 12–18`, `Evening 18–24`), clamps weekly caps to **36h max / 30h standard**, and applies the Ramadan shift labor multiplier (default **1.15x** at 6h shifts). |
| **Autonomous PM** | `Auto PM` / `صيانة ذاتية` (`ON`/`OFF`) | Switches mold preventive maintenance from a static `t=0` week-start lock to **Autonomous CP-SAT Co-Optimization**, allowing CP-SAT to float each mold's PM block into the lowest-cost non-overlapping window before its rated shot limit (up to 75% of horizon). |
| **Currency Switch** | `SAR` / `EGP` | Converts every KPI, P&L row, order price, and worker wage live using `fx_egp_per_sar` (default **13.0 EGP / SAR**). Base values are stored deterministically in SAR. |
| **Language & Layout** | `العربية` / `English` | Switches the entire interface between **English (LTR)** and **Arabic (RTL)** with complete bilingual terminology. The Gantt time axis intentionally stays `Sun → Sat` left-to-right for visual clarity. |
| **Operations Copilot** | `Ops Copilot` / `مساعد العمليات` | Opens the slide-over natural-language what-if simulator drawer. |
| **Run Optimization** | `Run CP-SAT Optimization` / `تشغيل تحسين CP-SAT` | Validates the active plant dataset, solves Press CP-SAT + coupled Workforce CP-SAT + P&L + Risk Radar, saves an audit record, and navigates to Tab 3. |
| **Executive Brief** | `Executive Brief` / `التقرير التنفيذي` | Opens the in-dashboard **Executive ROI Scorecard & Audit Brief** modal (zero file downloads required). |
| **Hosted Session Controls** | `<Client Label>`, `Reset Sandbox` / `إعادة ضبط البيئة`, `Sign Out` / `تسجيل الخروج` | Displayed automatically when `AUTH_ENABLED=true`: shows the signed-in prospect label, resets only the current session's sandbox, or signs out back to the branded Login Gate. |

---

## Section 3 — Complete Tab-by-Tab User Guide (Exact UI Labels & Workflows)

### Global Navigation: TopBar & Decision Intelligence Loop Strip
Directly below the `TopBar` sits the interactive **Decision Intelligence Loop Strip** (`1. Model` → `2. Sense` → `3. Optimize` → `4. Command` → `5. Adapt`):
- **`1. Model`** → Jumps to Tab 2 (`Plant Data & Parameters`) showing active presses and total orders.
- **`2. Sense`** → Jumps to Tab 1 (`Plant Scope & Readiness`) showing the live `Risk XX/100` score.
- **`3. Optimize`** → Jumps to Tab 3 (`Trade-Off & Scenario Composer`) showing solver status (`OPTIMAL`/`FEASIBLE`) and solve time in ms.
- **`4. Command`** → Jumps to Tab 4 (`Press Gantt & Color Sequence`) showing combined hard-constraint compliance (`11/11 HC` = 6 Press + 5 Workforce).
- **`5. Adapt`** → Opens the `Ops Copilot` drawer showing weekly savings (`+<amount>/wk`).

---

### Tab 1: `1. Plant Scope & Readiness` (`1. جاهزية المصنع والخامات`)
Tab 1 is your **Zero-File-Transfer Command Center** for managing plant workspaces, inspecting live readiness, and catching anomalies before solving.

1. **Saved Plant Workspaces (`مساحات عمل المصانع المحفوظة`):**
   - Switch between saved factories using the `Active Workspace` dropdown (persisted in SQLite via `/api/workspaces`).
   - **`Save As New Plant`**: Clones the current edited plant and physics configuration under a new workspace name.
   - **`+ New Blank Plant`**: Starts a clean factory workspace so you can enter a prospect's live presses, molds, resins, and orders during a meeting.
   - **`Reset Demo`**: Restores the seeded 6-press Delta & Riyadh demo plant.
   - **`Delete Plant`**: Deletes custom workspaces (the default workspace is protected and resets to demo instead).
2. **Instant Quick-Add & Physics Hub (`مركز الإضافة السريعة وفيزياء المصنع`):**
   - One-click modal buttons for **`Add Press`**, **`Add Mold`**, **`Add Resin`**, **`Add Order`**, and **`Edit Plant Physics`** without leaving Tab 1.
3. **Clickable 6-Card KPI Summary Strip:**
   - `Active Presses` → jumps to Tab 2A (`Presses`)
   - `Physical Molds` (highlights amber if any mold requires PM) → jumps to Tab 2B (`Molds`)
   - `Resin Grades` → jumps to Tab 2C (`Resin Inventory & Pricing`)
   - `Weekly Orders` (shows export count) → jumps to Tab 2D (`Production Orders`)
   - `Plant Load` (`%` and total production hours) → jumps to Tab 2E (`Plant Physics & Solver`)
   - `Floor Workforce` (`Active | Sick`) → jumps to Tab 6 (`Workforce & Shifts`)
4. **Proactive Delay & Bottleneck Risk Radar (`رادار المخاطر الاستباقي للتأخير والاختناقات`):**
   - Displays the deterministic **Plant Risk Score (`0–100`)**, **Financial Exposure**, **Exports at Risk**, **Tightest Buffer**, and **Resin Silo Depletion Clock** (showing projected stockout hour and remaining hours of coverage per resin).
   - Each risk card includes one-click **`Mitigate in Copilot`** (pre-fills an actionable remediation prompt in `Ops Copilot`) and **`Inspect`** (jumps straight to the affected Gantt or Workforce tab).
5. **Resin Inventory vs. Weekly Demand (`مخزون الخامات مقابل الطلب الأسبوعي`):**
   - Progress bars compare weekly demand against `Virgin + Usable Regrind (kg)` and flag drying requirements (e.g., `Dry 6h • 275°C` for `PET`).
   - Click the inline edit icon on any resin row to adjust stock or pricing immediately.
6. **Mold Shot-Count Maintenance Health (`صحة القوالب وعداد الضربات للصيانة الوقائية`):**
   - Tracks `current_shots / maintenance_interval_shots` against the **HC6 PM Threshold ≥ 95%** (e.g., `M-04` at `96.4% • PM REQUIRED`).
   - Click **`PM`** (`Log PM / Reset Shots`) to log completed preventive maintenance and reset the mold's shot counter to `0` instantly, or click the edit icon to update mold specs.
7. **Pre-Solve Plant Anomaly Diagnostics (`فحص الشذوذ المسبق قبل التشغيل`):**
   - Displays `READY FOR CP-SAT` (green) or `BLOCKING ERRORS` (red) with exact error/warning codes (`ORDER_NO_COMPATIBLE_PRESS`, `MOLD_PM_THRESHOLD_EXCEEDED`, `RESIN_INVENTORY_DEFICIT`, `IMPOSSIBLE_DEADLINE`, `PM_DEADLINE_RISK`, etc.).
   - Click **`Run CP-SAT Optimization →`** to launch the solver.
8. **Plant Press Fleet:** Clickable cards for every press showing tonnage, process type, hot-runner support, and `kWh/h`; click any card to edit it inline.

---

### Tab 2: `2. Plant Data & Parameters` (`2. بيانات ومعاملات المصنع`)
The **Plant Data & Parameters Studio** is a live CRUD editor with a sticky action bar showing active `Modified Items` count, live `Ready / Warnings / Errors` validation pill, `Reset to Default Demo`, and **`Validate & Run CP-SAT Optimization →`** (which validates, solves, and opens Tab 4 Gantt). Every edit automatically re-runs validation and powers CP-SAT, Financials, Workforce, and Copilot.

#### Sub-Tab `A. Presses` (`أ. الماكينات`)
| Field | Meaning & Optimization Impact |
| :--- | :--- |
| `machine_id`, `name` | Unique press identifier (e.g., `P-500T`) and display name. |
| `process_type` | `Injection`, `BlowMolding`, or `Extrusion`. |
| `tonnage` | Clamping force in metric tons (e.g., `150T–650T`). |
| `supports_hot_runner` | Boolean (`HC1`): hot-runner molds can ONLY run on presses with `supports_hot_runner = true`. |
| `hourly_energy_kwh` | Full-load power draw (`kWh/h`). Drives energy cost and peak-tariff avoidance. Changeovers draw **55%** of this rate for barrel heating. |
| `hourly_operating_cost` | Base press operating cost per hour (`SAR/h`), scaled by the Ramadan labor multiplier when Ramadan Mode is active. |
| `status` | `active`, `down`, or `maintenance`. Non-active presses are excluded by `HC1`. |
| `downtime_windows` | Scheduled maintenance windows (`start_hr`, `end_hr`, `reason`) blocked by `HC2`. |

#### Sub-Tab `B. Molds` (`ب. القوالب`)
| Field | Meaning & Optimization Impact |
| :--- | :--- |
| `mold_id`, `name` | Unique physical mold ID (e.g., `M-04`). `HC3` guarantees a mold never runs on two presses at once. |
| `compatible_machines` | List of press IDs physically capable of mounting this mold (`HC1`). |
| `cavities` & `cycle_time_sec` | Determines exact production duration: `shots = ceil(quantity_pcs / cavities)` and `duration_mins = max(30, ceil(shots * cycle_time_sec / 60))`. |
| `is_hot_runner` | Requires a hot-runner press (`HC1`). Also sets runner scrap factor (**0.5%** hot-runner vs. **3.0%** cold-runner) and mold-swap startup scrap (**4 kg** vs. **10 kg**). |
| `base_changeover_mins` | Physical mold hanging & stabilization time (`15–480 min`) used in `HC4` transitions. |
| `current_shots` & `maintenance_interval_shots` | If `current_shots / maintenance_interval_shots ≥ 95%` (or projected weekly shots exceed 100% under `Auto PM`), `HC6` enforces a mandatory `pm_duration_hrs` block. |
| `pm_duration_hrs` | Hours required for mold preventive maintenance (`HC6`). |

#### Sub-Tab `C. Resin Inventory & Pricing` (`ج. مخزون وأسعار الخامات`)
| Field | Meaning & Optimization Impact |
| :--- | :--- |
| `resin_code` | `PP`, `HDPE`, `LDPE` (compatible polyolefin family) or `PET`, `ABS`, `PVC` (incompatible across families). |
| `virgin_available_kg` & `virgin_cost_per_kg` | Hard weekly virgin silo cap (`HC5`) covering both production draw and purge scrap; sets virgin material and purge scrap cost. |
| `regrind_available_kg` & `regrind_cost_per_kg` | Hard weekly regrind cap (`HC5`) usable only on orders with `max_regrind_pct > 0`. |
| `drying_lead_time_hrs` | Mandatory pre-drying start floor (`HC5`) — e.g., `6h` for hygroscopic `PET` and `ABS` (also triggers extra QC/Material Handler demand in Tab 6). |
| `barrel_temp_c` | Processing melt temperature (`120–360°C`). |

#### Sub-Tab `D. Production Orders` (`د. أوامر التشغيل`)
Includes search bar (`Search orders, customer, SKU, mold...`) and `All Resins` / `All Colors` filters, plus live calculated `Est. Run Time` and `Est. Resin Needed`.
| Field | Meaning & Optimization Impact |
| :--- | :--- |
| `order_id`, `customer`, `sku_name` | Order identification and customer metadata. |
| `mold_id`, `resin_code`, `color` | Links order to physical mold, resin stock, and pigment rank (`Natural=1`, `White=2`, `Yellow=3`, `Blue=4`, `Red=5`, `Black=6`) for `HC4` light-to-dark sequencing. |
| `quantity_pcs`, `part_weight_g` | Computes net weight and gross plastic weight (including runner factor). |
| `max_regrind_pct` | `0%` for food/pharma orders (**strictly protected by `HC5`**, even when global regrind override is active); up to `50%` for industrial orders. |
| `due_hr`, `late_penalty_per_hr`, `is_export` | Deadline hour in the weekly horizon. Tardiness incurs `late_penalty_per_hr × (1.5 if is_export else 1.0)`. |
| `unit_selling_price`, `discount_pct` | Drives Recognized Revenue, Gross/Net Profit, and per-order margin in Tab 5. |

#### Sub-Tab `E. Plant Physics & Solver` (`هـ. فيزياء المصنع والمحرك`)
Organized into 3 cards:
1. **Purge & Changeover Physics:** `Light → Dark Purge (mins / kg)` (default `25m / 4.0kg`), `Dark → Light Purge (mins / kg)` (default `135m / 32.0kg`), `Incompatible Resin Purge (mins / kg)` (default `180m / 48.0kg`).
2. **Energy & Financial Rules:** `Electricity Tariff (SAR/kWh)` (default `0.32`), `Peak Tariff Multiplier` (default `1.4x`), `Peak Start Hr` / `Peak End Hr` (default `13`–`17`), `WIP Holding Cost (SAR/kg/day)` (default `0.05`), `Display Currency` (`SAR`/`EGP`), and `FX (EGP / SAR)` (default `13.0`).
3. **Calendar & Solver Engine:** `Planning Horizon (hours)` (default `168h`, range `24–336h`), `Ramadan Shift Hours` (default `6h`), `CP-SAT Max Solve Time (sec)` (default `5.0s`, range `1–30s`), `Weekly Fixed Overhead (SAR)` (default `18,500`), `Scrap Regrind Recovery (%)` (default `10%`), and `Annual Operating Weeks` (default `50 wks/yr`).

---

### Tab 3: `3. Trade-Off & Scenario Composer` (`3. لوحة الموازنة والسيناريوهات`)
1. **Top 4 Executive KPI Delta Cards (CP-SAT vs. Naive FIFO Baseline):**
   - `Total Cash Saved vs. FIFO` (with `%` reduction and Baseline → Optimized totals)
   - `Purge Resin Scrap Cut` (kg saved and `%` cut)
   - `Changeover Hours Saved` (hours freed for extra production)
   - `OTIF % / Solve Time` (with `OPTIMAL`/`FEASIBLE` badge, Plant `OEE %`, and truncated SHA-256 audit hash)
2. **Executive Trade-Off Weights (4 Sliders, `0–100`):**
   - `Purge & Changeover` (default `35`), `Export OTIF` (default `35`), `Energy Cost` (default `15`), `Working Capital` (default `15`). Releasing any slider immediately re-solves CP-SAT.
   - **4 One-Click Strategy Presets:** `Balanced Plant` (`35/35/15/15`), `Min Purge Scrap` (`65/15/10/10`), `Zero Late Exports` (`15/70/10/5`), `Min Electricity` (`20/20/50/10`).
3. **Custom Composable Scenario Composer:**
   Combine **unlimited** simultaneous disruptions across 4 sub-tabs, then click **`Run CP-SAT Optimization`**:
   - **`Press Breakdown`**: Pick press, `Start Hour (0–160)`, and `Duration (hrs)` → injects hard downtime window (`HC2`).
   - **`Resin Shock`**: Pick resin grade, `Stock Cut (%)`, `Price Spike (%)`, plus the **`Non-Food Regrind Override Cap`** slider (`0–40%`, strictly protecting `0%` food/pharma orders).
   - **`Rush Order`**: Inject an urgent order (`Mold`, `Resin`, `Plastic Color`, `Qty (pcs)`, `Part Wt (g)`, `Due Hr (12–168)`, `Export Priority` checkbox).
   - **`Mold PM Lock`**: Force a manual `PM Lock Duration (hrs)` on any mold (`HC6`).
   - Active disruptions appear as removable colored chips; click `Reset All` to clear.
4. **Boardroom Side-by-Side Scenario Comparison (`Pin Scenario (X/3)` & `Scenario Comparison Matrix (A vs. B vs. C)`):**
   - Lock up to **3 immutable solved scenarios** (`Slot A`, `Slot B`, `Slot C`) from **Tab 3**, **Tab 5**, or directly inside the **Operations Copilot** (`Pin for Comparison`) without overwriting previous runs or re-solving. When all 3 slots are full, pick which slot (`A`, `B`, or `C`) to replace.
   - Compares **Weekly Net Operating Profit & Margin %**, **Weekly Savings vs. FIFO & Annualized**, **Export & Order OTIF % (Late Orders)**, **Purge Scrap (kg) & Changeover Hours**, **Direct Floor Labor & Overtime**, **Proactive Risk Radar Exposure**, and **Active Disruptions & Mode Toggles** strictly from deterministic Python payloads.
   - Automatically highlights the mathematically best value per row with an emerald **`Best`** (`الأفضل`) badge, shows `+ / -` deltas relative to **`Slot A`** (Anchor), reacts instantaneously to **`SAR <-> EGP`** and **`EN <-> AR`**, and supports inline **Rename**, **`Promote to Active Plan`** (restoring Gantt, P&L, Risk Radar, and Workforce across all 6 tabs), **Remove**, and **Clear All**.
5. **Bottom Verification & Audit Strip:**
   - **`6/6 Hard Constraint Mathematical Verification`**: Shows `0v` (zero violations) across `HC1–HC6`.
   - **`Deterministic Audit Trail`**: Click any historical `PL-XXXXXXXX` run to inspect its exact saved results.

---

### Tab 4: `4. Press Gantt & Color Sequence` (`4. مخطط جانت وتسلسل الألوان`)
1. **Compact Risk Radar Strip:** Highlights top critical/elevated risks with one-click `Mitigate in Copilot` chips.
2. **Interactive Press-by-Press Production Gantt (`168h Sun–Sat`):**
   - **Mode Switch:** Toggle **`CP-SAT Optimized`** vs. **`Naive FIFO Baseline`** (each button displays total purge scrap kg) to visually prove why FIFO suffers dark-to-light purges while CP-SAT sequences light → dark (`Natural → White → Yellow → Blue → Red → Black`).
   - **Zoom Toggle:** Switch between **`Fit Horizon`** and **`Detailed Zoom`** (`1680px` wide timeline).
   - **Visual Legend & Overlays:**
     - Production blocks are colored by actual plastic pigment (`Natural` through `Black`).
     - Hatched **amber** = `Changeover / Purge`, hatched **rose** = `Breakdown / Maint`, hatched **purple** = `Mold PM Block` (showing either `Autonomous CP-SAT Window` or `Static t=0 Lock`).
     - When enabled, translucent vertical bands shade `Peak Tariff (13–17h)` and `Iftar Blackout (18–20h)`.
   - Hover over any block to inspect exact start/end hours, mold, resin, setup time, and purge scrap kg.
3. **Resin Consumption & Purge Scrap Charts:** Side-by-side bar charts comparing Virgin/Regrind consumption and `FIFO vs. CP-SAT Purge Scrap by Resin (kg)`.
4. **Press Execution Sequence & Transition Audit Table:** Complete chronological job sequence per press with transition type (`continuous_run`, `light_to_dark_purge`, `mold_swap_same_material`, etc.), setup minutes, purge kg, and tardiness.

---

### Tab 5: `5. Revenue & Savings` (`5. الإيرادات والوفورات`)
1. **Top 5 Executive Financial KPI Cards:**
   - `Weekly Recognized Revenue` (vs. Booked & At-Risk/Unscheduled revenue)
   - `Optimized Net Profit & Margin` (with percentage-point margin lift vs. FIFO)
   - `Total Weekly Savings` (Hero card showing weekly cash + revenue protection lift and `%` profit lift vs. Naive FIFO)
   - `Annualized Projected Savings` (`Total Weekly Savings × Annual Operating Weeks`, plus monthly projection at `× 4.33`)
   - `Unlocked Capacity Value` (freed changeover hours × average hourly revenue rate)
2. **Inline Financial Assumptions Strip:** Edit `Weekly Fixed Overhead`, `Scrap Regrind Recovery (%)`, and `Annual Operating Weeks` inline — auto-recomputes after 500ms without leaving Tab 5.
3. **Charts & Full Side-by-Side Weekly P&L Reconciliation Table (`Naive FIFO` vs. `CP-SAT Optimized`):**
   - Reconciles every line item deterministically with **zero double-counting**:
     - `Recognized Revenue`
     - `Direct Resin Material Cost`
     - `Purge Scrap Cost (Net of Recovery)`
     - `Energy & Press Operating Cost`
     - `Late Delivery Penalties`
     - `WIP Holding Cost`
     - `Direct Floor Labor & Overtime Cost` (synced live from Tab 6 Workforce CP-SAT)
     - `= Gross Profit` (`Gross Margin %`)
     - `- Weekly Fixed Overhead`
     - `= Net Operating Profit` (`Net Margin %`)
4. **Per-Order Profitability Table with Inline `Unit Selling Price` Editing:**
   - Search by order ID, customer, or SKU. Edit any order's `Unit Selling Price` directly in the table (in `SAR` or `EGP`) to immediately re-run P&L and margin calculations.
5. **In-Dashboard `Executive Brief` Modal (`TopBar` button):**
   - Summarizes `Total Net Cash Saved`, `Purge Scrap Cut`, `Changeover Hours Saved`, `Late Penalties Avoided`, `Energy Cost Saved`, `OEE % / OTIF %`, `6/6 Hard Constraint Verification`, and the full `Resin Consumption & Purge Scrap Audit` table for boardroom presentation with zero file exports.
   - Fully localized in **English (LTR)** and **Arabic (RTL)** (including all resin audit table columns and solver telemetry labels) and dismissible via the `Escape` key or close buttons.

---

### Tab 6: `6. Workforce & Shifts` (`6. القوى العاملة والورديات`)
Tab 6 couples a dedicated **Workforce CP-SAT Roster Optimizer** directly to the solved Tab 4 Press Gantt.

1. **How Staffing Demand Couples Automatically to Tab 4:**
   - For every `(day, shift)` slot across the 7-day week (`Sun–Sat`), `derive_demand()` reads overlapping blocks from the solved Press Gantt:
     - **`Press_Operator`**: `ceil(active_presses / presses_per_operator)` (default `2` presses per operator), plus machine-certification matching (`WHC1`).
     - **`Shift_Supervisor`**: `1` per active operating shift.
     - **`QC_Inspector`** & **`Material_Handler`**: `1` per active shift, plus `+1` during high load (`≥ 4` active presses) or when hygroscopic resin (`PET` / `ABS`) is running.
     - **`Mold_Technician`**: `1` when `1–2` mold changeovers/PM blocks occur in the shift; `2` when `≥ 3` occur (`2x` criticality penalty in CP-SAT).
2. **Top 5 Workforce KPI Cards:**
   - `Active Staff & Utilization`, `Weekly Labor & OT Saved` (vs. Naive Static 6-Day Rotation), `Overtime Hours Reduced`, `Shift & Changeover Coverage` (including `Mold %` readiness), and `Compliance & Fairness` (`100% Rest-Rule Compliant` + preference match `%`).
3. **Interactive Workforce Controls & Quick Disruption Strip:**
   - Tune 3 workforce objective weights (`Labor & Overtime Cost` default `50`, `Shift Coverage` default `35`, `Fairness` default `15`), `Presses/Operator`, `Min Rest Hours` (default `11h`), and `Min Consecutive Days Off` (default `1`).
   - Click one-tap sick-callout chips for key Mold Technicians, Supervisors, or Operators, then click **`Re-Optimize Shifts`** (runs fast labor-only `/api/workforce/solve` and live-updates Tab 5 P&L).
4. **Roster Matrix, Coverage Chart & Worker Directory:**
   - **Roster Matrix:** Filter by role and toggle `CP-SAT Optimized` vs. `Static Rotation` baseline; view `Morning`, `Afternoon`, `Evening` (Ramadan), `Night`, `OFF`, `LEAVE`, and `SICK` cells plus weekly regular/OT hours and cost per worker.
   - **Demand vs. Scheduled Coverage Chart:** Group by `Shift Slot` or `Day` and filter by role; immediately flags understaffed bottlenecks.
   - **Worker Directory:** Full CRUD (Add, Edit, Duplicate, Delete, toggle `Sick`, toggle approved `Leave` days `Sun–Sat`, edit machine certifications and hourly rates).
   - **5/5 Workforce Hard Constraint Verification (`WHC1–WHC5`):** Confirms zero violations across certification, labor-law/Ramadan hour caps, 11h rest gap, leave/sick/days-off lock, and max 1 shift/day.

---

## Section 4 — Using the Operations Copilot (EN & AR)

Click **`Ops Copilot`** (`مساعد العمليات`) in the `TopBar` (or click **`Mitigate in Copilot`** on any Risk Radar alert).

### 4.1 Zero-LLM-Math 3-Tool Architecture
The Copilot NEVER computes schedules, costs, or hours in text. Whether running live with **Gemini (`gemini-4-hydrogen`)** or in **100% Offline Mode**, it executes 3 deterministic Python/CP-SAT tools:
1. **`simulate_plant_scenario`**: Merges arbitrary combinations of press breakdowns, resin shortages/price spikes, regrind overrides, mold PM locks, rush export orders, operational toggles (`Peak Tariff`, `Ramadan Mode`, `Auto PM`), executive weights, and **worker sick callouts** (`worker_callouts`), then runs OR-Tools CP-SAT and returns exact KPIs and P&L deltas.
2. **`inspect_bottleneck`**: Audits any specific press (e.g., `P-500T`), mold (`M-04`), order (`ORD-09`), resin (`HDPE`), or the entire plant (`PLANT`) with deterministic facts and actionable recommendations.
3. **`compare_two_strategies`**: Runs CP-SAT twice under two competing executive weight profiles (e.g., `Min-Scrap` vs. `Max-OTIF`) and returns a side-by-side metric table with a cost/OTIF recommendation.

### 4.2 Starter Prompts & Applying Live to the Dashboard
Built-in one-click chips (available in both English and Arabic):
- *"Press 500T breaks down 18h on Tuesday"* / *"عطل ماكينة 500T لمدة 18 ساعة يوم الثلاثاء"*
- *"HDPE supply cut 35% + boost regrind"* / *"نقص HDPE بنسبة 35% مع رفع المعاد تدويره"*
- *"Add urgent 40k White Cap export order due Thu"* / *"أضف أمر تصدير عاجل 40k غطاء أبيض للخميس"*
- *"Compare Min-Scrap vs. Max-OTIF"* / *"قارن بين أقل هالك وأعلى التزام تسليم"*
- *"Why is Mold M-04 a bottleneck?"* / *"لماذا يمثل القالب M-04 نقطة اختناق؟"*
- *"What if 2 Mold Techs and 3 Press Operators call out on Tuesday?"* / *"ماذا يحدث للتغطية والربح لو تغيب 2 فنيين و3 مشغلين يوم الثلاثاء؟"*

After any simulation completes, click **`Apply This Scenario to Dashboard`** (`تطبيق هذا السيناريو على لوحة التحكم`) to push the simulated configuration and CP-SAT solution live across all 6 tabs (automatically navigating to Tab 6 for workforce callouts or Tab 4 Gantt for press/order scenarios).

---

## Section 5 — Mathematical & Technical Architecture Appendix

### 5.1 Press Scheduling CP-SAT Hard Constraints (`HC1–HC6`)
Independently verified post-solve by `backend/core/verify.py`:
- **`HC1` — Mold–Press Compatibility & Hot-Runner Fit:** Every scheduled order runs on exactly one `active` press listed in `mold.compatible_machines`, with `press.supports_hot_runner == True` whenever `mold.is_hot_runner == True`.
- **`HC2` — No Press Overlap & Breakdown/Downtime Exclusion:** `AddNoOverlap` per press across all busy intervals `[start - setup, end)` and all scheduled downtime/breakdown windows. When Ramadan Mode is ON, setup/purge intervals also `AddNoOverlap` daily `18:00–20:00` Iftar blackouts.
- **`HC3` — Physical Mold Exclusivity Across Presses:** `AddNoOverlap` per physical mold across all presses so one mold never runs in two places simultaneously.
- **`HC4` — Asymmetric Changeover & Color/Resin Purge Sequencing:** `AddCircuit` per press enforces exact sequence-dependent `setup_mins` and `purge_scrap_kg` via `transition_penalty()` (continuous run `0m/0kg` < light-to-dark < dark-to-light < polyolefin switch < incompatible resin switch / mold swap).
- **`HC5` — Resin Pre-Drying Floor, Food-Grade Regrind Safety & Inventory Cap:** Every job starts at or after `resin.drying_lead_time_hrs × 60`; food/pharma orders (`max_regrind_pct == 0`) strictly receive `0 kg` regrind; weekly `virgin_used + purge_scrap <= virgin_available_kg` and `regrind_used <= regrind_available_kg`.
- **`HC6` — Mold Preventive Maintenance (PM) Shot-Count Block:** Any mold at `≥ 95%` shot life (or manually locked, or projected `> 100%` mid-week under `Auto PM`) receives a non-overlapping `pm_duration_hrs` block. In `Auto PM` mode, CP-SAT also enforces `shots_before_pm <= maintenance_interval_shots - current_shots`.

### 5.2 Press CP-SAT Weighted Multi-Objective (SAR Cents)
```text
Minimize:
  (3 * w_changeover_scrap + 1) * (Purge_Resin_Cost + Changeover_Downtime_Cost_at_250_SAR_hr)
+ (3 * w_otif             + 1) * (Tardiness_Penalty * Export_Mult + Unscheduled_Order_Penalty)
+ (2 * w_energy_cost      + 1) * (Press_Energy_Cost + Peak_Tariff_Surcharge + Press_Operating_Cost)
+ (2 * w_working_capital  + 1) * (Virgin_&_Regrind_Material_Spend + Early_WIP_Holding_Cost)
+ pm_tiebreak_expr
```
*Export multiplier = `1.5x` on late penalties for `is_export = True` orders.*

### 5.3 Workforce CP-SAT Hard Constraints (`WHC1–WHC5`) & Objective
Solved role-by-role in `backend/core/workforce_solver.py` and independently verified by `verify_workforce()`:
- **`WHC1`**: Role match and press-operator machine certification match on active presses.
- **`WHC2`**: Weekly hour cap (`≤ worker.max_weekly_hours`, clamped to `≤ 36h` and `6h` shifts in Ramadan Mode).
- **`WHC3`**: Mandatory inter-shift rest gap (`≥ min_rest_hours`, default `11h`) across consecutive days.
- **`WHC4`**: Zero scheduling on `sick`, `on_leave`, `approved_leave_days`, or Copilot callout days, plus at least `min_consecutive_days_off` (default `1`) consecutive off days per 7-day cycle.
- **`WHC5`**: Maximum one shift per worker per calendar day.
- **Objective:** `Minimize(w_labor_cost * (Regular_Pay + OT_Premium) + w_coverage * (Headcount_Gaps + Cert_Gaps) + w_fairness * (Pref_Mismatches + Night_Shift_Spread))`.
- **Solver Acceleration & Determinism:** Both solvers use feasible baseline `AddHint` warm-starts (`solver.py` hints scheduled flags, press assignments, chronological `AddCircuit` arcs, and 0.1 kg virgin/regrind splits with `relative_gap_limit = 0.001`; `workforce_solver.py` uses lexicographic symmetry breaking across strictly identical workers, symmetry-aligned hints, and deterministic parallel search `num_workers = 4`, `interleave_search = True`).

### 5.4 Financial Reconciliation Formulas (Zero Double-Counting)
Computed deterministically in `backend/core/financials.py`:
- `Recognized Revenue = sum(qty_pcs * unit_selling_price * (1 - discount_pct / 100))` for all scheduled orders.
- `Net Purge Scrap Cost = Gross Purge Scrap Cost * (1 - scrap_regrind_recovery_pct / 100)`.
- `Variable Production Cost = Direct Resin + Net Purge Scrap + (Energy + Press Operating) + Late Penalties + WIP Holding + Direct Floor Labor & Overtime`.
- `Gross Profit = Recognized Revenue - Variable Production Cost`.
- `Net Operating Profit = Gross Profit - Weekly Fixed Overhead`.
- `Total Weekly Savings = (Baseline Total Operating Cost - Optimized Total Operating Cost) + (Optimized Recognized Revenue - Baseline Recognized Revenue)`.
- `Annual Projected Savings = Total Weekly Savings * annual_operating_weeks` (default `50`).

### 5.5 Optional REST & Excel Integration Endpoints
While the interactive UI is 100% Zero-File-Transfer, IT/ERP teams can integrate programmatically via FastAPI (`/api/*`):
- `GET /api/health`, `GET /api/demo-data`, `POST /api/validate` (JSON or multipart `.xlsx`), `POST /api/solve`, `POST /api/workforce/solve`, `POST /api/copilot/ask`
- `GET /api/workspaces`, `POST /api/workspaces`, `GET /api/workspaces/{id}`, `DELETE /api/workspaces/{id}`
- `GET /api/audit-log`, `GET /api/audit-log/{run_id}`
- `GET /api/template.xlsx`, `POST /api/export-dataset.xlsx`, `POST /api/export-brief.xlsx`

### 5.6 Security, Data Residency & Offline Guarantees
- **Egypt On-Premises Privacy:** Run via Docker or local Windows install with `OFFLINE_MODE=true`; all plant data, customer pricing, and audit logs remain strictly on local SQLite (`audit.db`) with zero outbound internet traffic.
- **KSA SDAIA / PDPL Alignment:** Full in-kingdom / on-prem deployment capability, zero external model training on factory data, and cryptographic SHA-256 audit trails for every schedule run.

---

## Section 6 — Troubleshooting & Operator FAQ

| Symptom / Question | Root Cause & Exact Resolution |
| :--- | :--- |
| **`Run CP-SAT Optimization` button is disabled** | Tab 1 / Tab 2 Pre-Solve Validator found ≥ 1 blocking `ERROR` (e.g., `ORDER_NO_COMPATIBLE_PRESS`, `DUPLICATE_PRESS_ID`, `INVALID_DOWNTIME_WINDOW`). Open Tab 1 Diagnostics or Tab 2 red banner to fix the flagged entity. |
| **An order shows `UNSCHEDULED (Resin Cap)`** | `HC5` detected that total virgin + purge resin demand exceeds `virgin_available_kg` for that resin grade. Increase virgin stock in Tab 1/2C, or enable **Non-Food Regrind Override Cap** in Tab 3 (up to 40% for non-food orders) to free virgin resin for food/export jobs. |
| **Mold `M-04` starts with a 6h purple PM block** | `M-04` is seeded at `482,000 / 500,000` shots (`96.4% ≥ 95%`), triggering `HC6`. Either toggle **`Auto PM`** ON in the `TopBar` so CP-SAT floats the PM window optimally, or click **`PM`** (`Log PM / Reset Shots`) in Tab 1 once maintenance is completed. |
| **Port `8000` or `3000` already in use on Windows** | Run `mini-dios-workforce\stop.bat` to cleanly terminate stale listeners on ports `8000` and `3000`, then re-run `start.bat`. |
| **Copilot says `offline_fallback` instead of `gemini`** | Either `GEMINI_API_KEY` is blank in `backend/.env`, `OFFLINE_MODE=true`, or Gemini exceeded the 15-second timeout. This is intentional failover behavior: the offline parser still executes the exact same deterministic OR-Tools CP-SAT tools with zero hallucinated math. |
| **Why do currency values change when toggling `SAR` / `EGP`?** | All underlying rates are stored in SAR and converted live at `fx_egp_per_sar` (editable in Tab 2E, default `13.0 EGP/SAR`). |
| **Can an operator accidentally assign regrind to a food/pharma order?** | No. `HC5` and `effective_order_max_regrind_pct()` strictly enforce `0%` regrind on any order with `max_regrind_pct == 0`, even if a global regrind override is active. |
