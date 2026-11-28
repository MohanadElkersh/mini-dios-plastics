# Mini-DIOS — UEM & 5-Layer DI Solver Upgrade Brief (One-Time Reference)

> **What this document is:** A standalone, one-time executive and engineering briefing explaining our upgrade from a single-industry plastics scheduler (`legacy_cpsat_v1`) to a **5-Layer Decision Intelligence (DI) Core + 6-Primitive Universal Execution Meta-Model (`uem_di_v1`)**, including verified benchmark comparisons, visual inspection capabilities, and a practical decision guide on when to use each solver.
> **Who it is for:** Co-founders, enterprise factory owners, holding-group CTOs, and technical reviewers evaluating Mini-DIOS's architecture, governance, and multi-industry scalability.
> **Security Note:** This document contains zero secrets, passwords, API keys, or `.env` values.

---

## 1. What Changed in the Last Update (Complete Summary)

We upgraded Mini-DIOS from a monolithic, plastics-specific optimization script into a **layered, industry-agnostic Decision Intelligence Operating System** backed by Google OR-Tools CP-SAT, OMG process/rule standards, and an interactive visual inspector.

### 1.1 The 5-Layer Decision Intelligence Core (`backend/core/di/*`)
1. **Layer 1 — Formal Business Ontology (`ontology_meta.py`):**
   - Models any industrial operation as a typed semantic graph (`BusinessOntologyGraph`) consisting of formal `EntityTypeSpec` classes (`primary_resource`, `secondary_resource`, `consumable_pool`, `demand_activity`, `workforce_actor`, `sync_container`), concrete `EntityInstance` records, directed `TypedRelationship` links (`M:N`, `N:1`, `1:1`), and declarative `SemanticInvariantSpec` constraints (`INV-HC1` through `INV-HC6`).
2. **Layer 2 — Pre-Solve Business Architecture Validator (`arch_validator.py`):**
   - Evaluates the ontology graph across three formal enterprise gates **before** invoking the mathematical solver:
     - **`GATE-1-STRUCTURAL`:** Entity schema conformance, required attributes, and referential integrity across all relationships.
     - **`GATE-2-CAPABILITY`:** Guarantees every customer order has at least one active, physically compatible primary resource path (e.g., matching clamping tonnage and hot-runner manifold support).
     - **`GATE-3-POLICY`:** Evaluates resource pool bounds, drying lead-time floors, mold shot-life thresholds, and custom domain policy invariants.
3. **Layer 3 — OMG BPMN 2.0 Process Template & Compiler (`bpmn_engine.py`):**
   - Formalizes the end-to-end operational execution loop as an executable **OMG BPMN 2.0** workflow (`BPMNProcessTemplate`) with `startEvent`, `serviceTask`, `businessRuleTask` (bound directly to Layer 4 DMN tables), `boundaryTimerEvent` (e.g., `PT168H` port container cut-off timer), `exclusiveGateway`, `parallelGateway`, and `endEvent`.
   - Includes a graph-reachability topology validator (`validate_topology()`) and exports standards-compliant **OMG BPMN 2.0 XML** (`http://www.omg.org/spec/BPMN/20100524/MODEL`).
4. **Layer 4 — OMG DMN 1.3 Decision Table Rule Engine (`dmn_engine.py`):**
   - Externalizes business policies out of hardcoded Python `if/else` statements into a deterministic, pure-Python **OMG DMN 1.3** decision table engine (`DMNDecisionTable`, `DMNRegistry`) supporting S-FEEL unary tests (wildcards, intervals `[a..b]`, comparisons, disjunction lists) and formal hit policies (`FIRST`, `UNIQUE`, `PRIORITY`, `ANY`, `COLLECT`, `COLLECT_SUM/MIN/MAX`).
   - Exports standards-compliant **OMG DMN 1.3 XML** (`https://www.omg.org/spec/DMN/20191111/MODEL/`) and tracks exact per-rule firing counts (`fired`, `hit_count`) across every solved schedule.
5. **Layer 5 — Causal Decision Diagram (CDD) Meta-Model (`decision_meta.py`):**
   - Formalizes Lorien Pratt / OMG Decision Intelligence **Causal Decision Diagrams** (`CausalDecisionModel`) connecting controllable **`DecisionLever`** inputs (executive trade-off weights and operational mode toggles) → **`IntermediateMetric`** shop-floor drivers (purge scrap kg, changeover hours, tardiness hours, container staging wait, warehouse peak tons, overtime hours) → **`DecisionOutcome`** executive KPIs (Weekly Net Operating Profit, Total Weekly Savings vs. FIFO, OTIF %, Shift Coverage %, Plant Risk Score) via directed `CausalEdge` links with polarity (`+` / `-`) and governing UEM primitive attribution.

### 1.2 The 6-Primitive Universal Execution Meta-Model (`backend/core/uem*.py`)
Zero plastics-specific vocabulary exists inside `core/uem.py`, `core/uem_compiler.py`, or `core/uem_verify.py`. Any industry domain compiles its ontology, BPMN 2.0 workflow, and DMN 1.3 tables into six canonical mathematical primitives:
1. **`ResourceNode`** — Primary unary machines (`primary_unary`), secondary exclusive tooling (`secondary_exclusive`), and dual-tier consumable pools (`consumable_pool`).
2. **`ActivityNode`** — Schedulable production/service activities with release floors, due dates, primary compatibility lists, secondary tool requirements, consumable draw, and tardiness/earliness penalties.
3. **`TransitionMatrix`** — Directed, asymmetric sequence-dependent setup times, consumable transition waste, and setup blackout windows compiled into `AddCircuit` per primary resource.
4. **`CumulativeEnvelope` (`CUMULATIVE_CAP`)** — Silo/inventory consumption caps (`consumable_cap`), time-windowed energy tariff surcharges (`time_window_tariff`), and shift-windowed operator availability caps (`shift_capacity_cap`) with bounded soft-overflow penalties.
5. **`SynchronizationGroup`** — Multi-SKU export container release barriers (`barrier_consolidation`) and static or autonomous floating preventive maintenance windows (`fixed_maintenance` / `floating_maintenance`).
6. **`ObjectiveTermSpec`** — Multi-objective weighted coefficients in exact integer cents.

Every `UEMGraph` is compiled into OR-Tools CP-SAT by `compile_and_solve_uem()` and independently verified post-solve by `verify_uem_solution()` (`UEM-P1` through `UEM-P6`).

### 1.3 Plastics Domain Adapter, Two-Way Bounded Labor Coupling & Live Admin Controls
- **`PlasticsAdapter` (`backend/adapters/plastics.py`):** Maps Mini-DIOS Plastics onto the 5-layer DI stack and 6-primitive `UEMGraph`, registering 4 production DMN 1.3 tables (`DMN_BARREL_PURGE_TRANSITION`, `DMN_MOLD_PM_POLICY`, `DMN_FOOD_GRADE_REGRIND_SAFETY`, `DMN_SHIFT_WORKFORCE_HEADCOUNT`) and a 14-node BPMN 2.0 workflow.
- **Two-Way Bounded Workforce-Press Coupling:** Replaces one-way press-then-workforce scheduling with a two-way feedback loop:
  - *Forward pass:* Injects shift operator availability envelopes into `UEMGraph` when available operators cannot staff all presses simultaneously.
  - *Backward feedback pass (Max 1 conditional re-solve capped at `<= 2.0s`):* If Pass 1 leaves `Press_Operator` shortages on specific shifts while spare capacity exists elsewhere in the week, tightens those shift caps and re-solves once to reduce understaffed slots without dropping orders.
- **Live Sandbox-Isolated Admin Engine Switcher (`USE_UEM_ENGINE` + `/api/admin/engine-mode`):** Allows authorized administrators to toggle live between `legacy_cpsat_v1` and `uem_di_v1` inside their isolated demo sandbox with an immediate re-solve and delta toast.
- **Blueprint API (`GET /api/di/blueprint`) & Visual DI Blueprint Inspector (`DIBlueprintModal.tsx`):** Exposes the live 5-layer blueprint as JSON, BPMN 2.0 XML, and DMN 1.3 XML, and renders an interactive 4-tab visual inspector (Causal Decision Diagram with SVG Bezier pathways, DMN 1.3 Rule Trace with live `FIRED` hit counts, BPMN 2.0 Swimlane Viewer, and Architecture Gates + 6-Primitive UEM Graph summary) in both English (LTR) and Arabic (RTL).

---

## 2. Why We Made This Upgrade

1. **Multi-Industry Reusability Without Rewriting Core CP-SAT Math:**
   - Previously, polymer purge rules, hot-runner checks, and mold shot limits were intertwined directly with OR-Tools CP-SAT variables inside `solver.py`. By separating domain rules (`adapters/plastics.py`) from the 6-primitive compiler (`core/uem_compiler.py`), Mini-DIOS can onboard new verticals—such as **Beverage Bottling & Canning (CIP wash cycles & starwheel change-parts)**, **Pharmaceutical Packaging**, **Food Processing**, or **Metal Stamping**—by writing a lightweight domain adapter without touching the core mathematical compiler.
2. **Auditable Enterprise Governance (OMG DMN 1.3 & BPMN 2.0):**
   - Enterprise IT directors, quality auditors, and plant managers distrust "black-box" optimization code. Externalizing shop-floor rules into industry-standard **OMG DMN 1.3 decision tables** and **OMG BPMN 2.0 process flows** (with 1-click XML export and live visual rule-firing traces) lets plant engineers see and audit the exact policy rule that governed every purge, regrind limit, mold PM block, and shift staffing requirement.
3. **Eliminating Black-Box `INFEASIBLE` Failures via Pre-Solve Architecture Gates:**
   - When a planner uploads a spreadsheet with a broken mold reference, an offline press, or an impossible resin balance, raw CP-SAT solvers simply return `INFEASIBLE`. Layer 2's three-stage **Pre-Solve Business Architecture Validator** (`GATE-1-STRUCTURAL`, `GATE-2-CAPABILITY`, `GATE-3-POLICY`) catches structural and capability dead-ends upfront and explains them in plain English and Arabic before the solver runs.
4. **Closing the One-Way Press-to-Labor Gap:**
   - In real factories, scheduling all 6 presses to run simultaneously on a shift where only 2 certified press operators are available creates an unstaffable floor plan. Two-way bounded labor coupling allows shift operator scarcity to feed back into press scheduling within a strict `<= 2.0s` re-solve budget—safe even on Render Free Tier (`0.1 CPU / 512 MB RAM`).
5. **Executive Causal Explainability (`Levers → Intermediates → Outcomes`):**
   - Factory owners and CFOs don't just want a Gantt chart—they want to understand *why* changing a priority slider or toggling `Container & WIP Sync` saved `24,761 SAR/week`. Layer 5's **Causal Decision Diagram** visually traces every decision lever through intermediate floor metrics straight to Net Operating Profit and Risk Radar scores.

---

## 3. New Solver (`uem_di_v1`) vs. Old Solver (`legacy_cpsat_v1`) — Exact Differences & Verified Benchmarks

### 3.1 Side-by-Side Architectural Comparison

| Dimension | Old Solver (`legacy_cpsat_v1`) | New Solver (`uem_di_v1` — UEM + 5-Layer DI) |
| :--- | :--- | :--- |
| **Architecture & Domain Coupling** | Monolithic plastics-only CP-SAT builder (`backend/core/solver.py`). | 5-Layer DI Core (`core/di/*`) + 6-Primitive `UEMGraph` compiler (`core/uem*.py`) + modular `PlasticsAdapter` (`adapters/plastics.py`). |
| **Pre-Solve Data Validation** | Single-pass domain validator (`validate_plant_data`). | Formal Layer 1 `BusinessOntologyGraph` + Layer 2 3-Gate Architecture Validator (`GATE-1-STRUCTURAL`, `GATE-2-CAPABILITY`, `GATE-3-POLICY`). |
| **Policy & Process Standards** | Rules embedded inside Python helper functions. | Explicit **OMG DMN 1.3** decision tables (4 tables, 17 rules with live hit counts) + **OMG BPMN 2.0** executable workflow + XML exports. |
| **Workforce-Press Coupling** | **One-Way Sequential:** Solves presses first, then rosters workers against fixed press demand. | **Two-Way Bounded Coupling:** Forward `shift_capacity_cap` envelopes + max 1 conditional backward feedback re-solve (`<= 2.0s`) under operator shortages. |
| **Post-Solve Verification** | 6 Plastics Hard Constraints (`HC1–HC6`) + 5 Workforce Constraints (`WHC1–WHC5`). | **17 Independent Mathematical Checks:** 6 UEM Primitive Verifiers (`UEM-P1..P6`) + 6 Plastics (`HC1–HC6`) + 5 Workforce (`WHC1–WHC5`). |
| **Causal Explainability** | Before/After KPI scorecard and P&L table. | Interactive 3-column **Causal Decision Diagram (`Levers → Intermediates → Outcomes`)** with live DMN rule and UEM primitive attribution. |
| **Multi-Industry Reusability** | Plastics (Injection, Blow Molding, Extrusion) only. | **100% Domain-Agnostic Core** (proven on a non-plastics **High-Speed Beverage Bottling & CIP Plant** with zero core code changes). |
| **Render Free-Tier Footprint** | Bounded `<= 5.0s` solve, low RAM. | Same bounded `<= 5.0s` primary solve (+ max `2.0s` only if operator shortage feedback triggers), zero heavy graph/JS dependencies. |

### 3.2 Verified Parity & Performance Benchmarks (`test_uem_di_parity.py`)
All benchmarks below were executed deterministically on the seeded **Delta & Riyadh Polymer Packaging Plant** (6 presses `150T–650T`, 10 molds, 5 resins, 24 weekly orders across 4 export container groups, 28 floor workers) and verified in `backend/tests/test_uem_di_parity.py`:

| Scenario / Mode | Metric | `legacy_cpsat_v1` | `uem_di_v1` (New) | Verified Outcome & Parity Notes |
| :--- | :--- | :---: | :---: | :--- |
| **1. Default Balanced Plant** | Solve Time / Hard Constraints<br>Scheduled Orders / OTIF %<br>Purge Scrap (kg)<br>Weekly Savings vs. FIFO<br>Weekly Net Operating Profit | `2,246 ms` (`6/6 HC`)<br>`24/24` (`100.0%`)<br>`207.4 kg`<br>`23,819.24 SAR`<br>`49,502.90 SAR` | **`1,880 ms`** (`6/6 HC` + `6/6 UEM`)<br>`24/24` (`100.0%`)<br>`207.4 kg`<br>**`23,819.24 SAR`**<br>**`49,502.90 SAR`** | **Exact 100% schedule, scrap & P&L parity** with **~16% faster solve time** under `uem_di_v1`. |
| **2. Peak Tariff Avoid** (`13:00–17:00`, `w_energy=55`) | Solve Time / Hard Constraints<br>Scheduled Orders<br>Purge Scrap (kg)<br>Weekly Savings vs. FIFO<br>Weekly Net Operating Profit | `5,081 ms` (`6/6 HC`)<br>`24/24`<br>`396.5 kg`<br>`19,812.76 SAR`<br>`44,391.43 SAR` | `5,073 ms` (`6/6 HC` + `6/6 UEM`)<br>`24/24`<br>**`280.1 kg` (`-116.4 kg`)**<br>**`24,182.79 SAR` (`+4,370 SAR`)**<br>**`48,361.46 SAR` (`+3,970 SAR`)** | `uem_di_v1`'s `CumulativeEnvelope` peak-tariff formulation cuts **`116.4 kg` more purge scrap** and unlocks **`+4,370 SAR/wk` higher savings**. |
| **3. Ramadan 6h Shift Mode** (`4×6h`, `18:00–20:00` Iftar Blackout) | Solve Time / Hard Constraints<br>Scheduled Orders / OTIF %<br>Purge Scrap (kg)<br>Weekly Savings vs. FIFO<br>Weekly Net Operating Profit | `3,486 ms` (`6/6 HC`)<br>`24/24` (`100.0%`)<br>`207.4 kg`<br>`19,210.90 SAR`<br>`37,728.55 SAR` | `3,519 ms` (`6/6 HC` + `6/6 UEM`)<br>`24/24` (`100.0%`)<br>`207.4 kg`<br>**`19,210.90 SAR`**<br>**`37,728.55 SAR`** | **Exact 100% schedule, Iftar blackout & P&L parity** across all 24 orders and 28 workers (`4×6h` / `36h` cap). |
| **4. Autonomous Floating Mold PM** (`Auto PM = ON`) | Solve Time / Hard Constraints<br>Scheduled Orders / OTIF %<br>Purge Scrap (kg)<br>Weekly Savings vs. FIFO | `1,760–2,600 ms` (`6/6 HC`)<br>`24/24` (`100.0%`)<br>`207.4 kg`<br>`23,819.24 SAR` | `1,800–2,614 ms` (`6/6 HC` + `6/6 UEM`)<br>`24/24` (`100.0%`)<br>`207.4 kg`<br>**`23,819.24 SAR`** | **Exact 100% parity** via `SynchronizationGroup(kind="floating_maintenance")` governed by `DMN_MOLD_PM_POLICY`. |
| **5. Multi-SKU Export Container Sync** (`w_capital=60`) | Solve Time / Hard Constraints<br>Scheduled Orders<br>Weekly Savings vs. FIFO | `5,042 ms` (`6/6 HC`)<br>`24/24`<br>`24,208.47 SAR` | `5,043 ms` (`6/6 HC` + `6/6 UEM`)<br>`24/24`<br>**`24,761.75 SAR` (`+553 SAR`)** | `uem_di_v1`'s `barrier_consolidation` synchronization group achieves **`+553.28 SAR/wk` higher total weekly savings**. |
| **6. Downstream Engines** (CTP Quoter, 30-Day Backtest, Offline Copilot) | Capable-to-Promise 35k Rush Cap<br>30-Day Historical Backtest Replay<br>Offline Copilot Breakdown + Ramadan | `ON_TIME / LATE` (`6/6 HC`)<br>28 orders replayed (`>0` ROI)<br>`6/6 HC` & `5/5 WHC` passed | `ON_TIME / LATE` (`6/6 HC` + `6/6 UEM`)<br>28 orders replayed (`>0` ROI)<br>`6/6 HC`, `5/5 WHC` & `6/6 UEM` passed | **100% seamless compatibility** across CTP Rush-Order Quoter, 1-Month Backtest, and Operations Copilot. |
| **7. Non-Plastics Universality Proof: Beverage Bottling Plant** | 2 Rotary Fillers, 2 Starwheel Formats, Cola Syrup Pool (`5,000 L`), CIP Wash DMN Table, Export Pallet Sync | *Not Supported (Plastics-only schema)* | **Solved to `OPTIMAL` in `< 200 ms`** (`3/3` orders scheduled, `6/6` UEM primitives verified) | Proves **100% domain-agnostic universality** of the 5-Layer DI + 6-Primitive UEM core outside plastics. |

---

## 4. Decision Guide — When to Use Each Solver

Both engines remain compiled, tested, and instantaneously switchable via the **`USE_UEM_ENGINE`** environment variable or the live **Admin Control & Architecture Console** (`TopBar → Admin`).

### 4.1 Use `uem_di_v1` (Recommended Default for Production, Pilots & Enterprise Demos) When:
- **Running live production or pilot factories:** You want full 17-check post-solve mathematical verification (`6/6` UEM Primitives + `6/6` Plastics Hard Constraints + `5/5` Workforce Hard Constraints) and Pre-Solve Architecture Gates (`GATE-1` through `GATE-3`) guarding every run.
- **Evaluating complex multi-constraint trade-offs:** Especially **Peak Electricity Tariff Avoidance** (where `uem_di_v1` cuts `116.4 kg` more purge scrap and saves `+4,370 SAR/week` more than the legacy formulation), **Multi-SKU Export Container Consolidation Sync** (`+553 SAR/week` extra savings), or **tight shift operator availability** where two-way bounded labor coupling prevents unstaffable press peaks.
- **Pitching enterprise holding groups, CTOs, or quality/audit teams:** You can click **`Inspect DI Blueprint`** (or **`Causal Trace & Policy Rules (DMN/BPMN)`** on Tab 3) to visually walk through the interactive **Causal Decision Diagram**, live **DMN 1.3 fired rules**, **BPMN 2.0 swimlanes**, and download standards-compliant XML artifacts on the spot.
- **Onboarding new custom factory constraints or new manufacturing verticals:** New floor rules map cleanly to DMN 1.3 tables or `CumulativeEnvelope` / `SynchronizationGroup` primitives without invasive core solver rewrites.

### 4.2 Use `legacy_cpsat_v1` (Safety Fallback & Live A/B Benchmark Mode) When:
- **Instant zero-downtime rollback on Render:** If an unexpected edge-case dataset or Render Free-Tier CPU spike ever occurs during a live session, an admin can switch back to `legacy_cpsat_v1` in one click (or set `USE_UEM_ENGINE=false`) with zero downtime and zero data loss.
- **Running a live side-by-side A/B proof during sales demos:** An administrator can solve the plant under `legacy_cpsat_v1`, pin the scenario into **Comparison Slot A**, switch live to `uem_di_v1` in the Admin modal, and pin it into **Comparison Slot B**—visually proving the extra weekly cash savings and full causal traceability of the 5-Layer Decision Intelligence upgrade.
- **Regression isolation during engineering diagnostics:** Quickly determines whether any future behavior change originates in the DI/UEM translation adapter (`adapters/plastics.py`) versus the underlying OR-Tools CP-SAT solver environment.
