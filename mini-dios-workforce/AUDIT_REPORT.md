# Mini-DIOS Plastics — Baseline Audit Report #1

**Auditor:** Principal QA & Optimization Auditor  
**Scope:** Full backend (`pytest`, CP-SAT Press & Workforce solvers, Financial P&L reconciliation), Frontend (`next build`), and Live Headless Browser E2E (Tabs 1–6, Ops Copilot, Executive Brief, EN/LTR & AR/RTL, SAR & EGP).

---

## 1. System Health Scorecard

| Check / Component | Scope | Result | Measured Metrics / Notes |
| :--- | :--- | :---: | :--- |
| **Backend `pytest` Suite** | `backend/tests/` (44 tests) | **PASS** | `44/44 passed` in `204.15s` |
| **CP-SAT: `standard`** | Press + Workforce + P&L | **PASS** | Press: `3,509 ms` (`OPTIMAL`, `0.00%` gap) · WF: `1,138 ms` (`FEASIBLE`) · Savings: `24,461.34/wk` · HC: `PASS` |
| **CP-SAT: `ramadan_6h`** | 6h 4-shift + Iftar blackout | **PASS** | Press: `5,048 ms` (`FEASIBLE`, `0.58%` gap) · WF: `2,273 ms` (`FEASIBLE`) · Savings: `19,921.92/wk` · HC: `PASS` |
| **CP-SAT: `heavy_disruption`** | `P-500T` 18h down + 35% HDPE cut + Rush Export | **PASS** | Press: `4,097 ms` (`OPTIMAL`, `0.00%` gap) · WF: `1,564 ms` (`FEASIBLE`) · Savings: `27,147.35/wk` · HC: `PASS` |
| **CP-SAT: `workforce_callout`** | 2 sick/leave workers + day callouts | **PASS** | Press: `2,943 ms` (`OPTIMAL`, `0.00%` gap) · WF: `1,285 ms` (`FEASIBLE`) · Savings: `22,709.34/wk` · HC: `PASS` |
| **Financial Reconciliation** | P&L identity & labor non-duplication | **PASS** | `0` drift across all 4 scenarios (`Revenue - Variable - Fixed == Net Profit`) |
| **Frontend Production Build** | `next build` (Next.js 15.5.29) | **PASS** | Compiled in `7.5s`, `0` TypeScript/build errors |
| **Live E2E: Tabs 1–6 (EN/LTR, SAR)** | `scope`, `studio`, `console`, `gantt`, `financials`, `workforce` | **PASS** | All 6 tabs rendered cleanly, `0` console errors, `0` page errors |
| **Live E2E: Currency & Ramadan** | `SAR <-> EGP` + Ramadan 6h -> Tab 6 | **PASS** | EGP rendered on Financials; 6h 4-shift layout active on Tab 6 |
| **Live E2E: Ops Copilot & Brief** | Copilot query + Executive Brief modal | **PASS** | Copilot responded; Brief modal opened (`0` HTTP >=400) |
| **Live E2E: Arabic (RTL) Sweep** | `dir="rtl"` across all 6 tabs | **PASS** | `dir=rtl` verified; all 6 tabs rendered with `0` console/page errors |

---

## 2. Bugs, Broken Links & Edge Cases Found

### Medium Severity
1. **Executive Brief Modal traps keyboard `Escape` & has untranslated English labels in Arabic mode**
   - **Location:** [ExecutiveBriefModal.tsx](file:///c:/Users/Sigma%20Alex/OneDrive/Desktop/DIOs/mini-dios-workforce/frontend/src/components/ExecutiveBriefModal.tsx#L37-L70), [#L199-L205](file:///c:/Users/Sigma%20Alex/OneDrive/Desktop/DIOs/mini-dios-workforce/frontend/src/components/ExecutiveBriefModal.tsx#L199-L205), [#L240-L255](file:///c:/Users/Sigma%20Alex/OneDrive/Desktop/DIOs/mini-dios-workforce/frontend/src/components/ExecutiveBriefModal.tsx#L240-L255)
   - **Detail:** Pressing `Escape` does not close the modal (only the close buttons work). Additionally, `"Scrap Saved (kg)"`, `"Run ID:"`, `"Solve Time:"`, `"Ramadan Shift:"`, and `"Peak Tariff Avoid:"` are hardcoded in English instead of using `i18n.ts`.
2. **Redundant API calls on initial load & demo bootstrap**
   - **Location:** [store.tsx](file:///c:/Users/Sigma%20Alex/OneDrive/Desktop/DIOs/mini-dios-workforce/frontend/src/lib/store.tsx#L349-L358), [#L392-L425](file:///c:/Users/Sigma%20Alex/OneDrive/Desktop/DIOs/mini-dios-workforce/frontend/src/lib/store.tsx#L392-L425)
   - **Detail:** `loadDemo()` and `bootstrap()` call `validatePlantJson()` immediately before `solvePlantScheduleApi()`, even though `/api/solve` already runs `validate_plant_data()` and returns `validation`. `loadWorkspaces()` is also invoked twice on initial demo load (`#L358` and `#L394`).
3. **Flat 3% cold-runner scrap factor underestimates small-part multi-cavity molds**
   - **Location:** [ontology.py](file:///c:/Users/Sigma%20Alex/OneDrive/Desktop/DIOs/mini-dios-workforce/backend/core/ontology.py#L345-L349)
   - **Detail:** `order_gross_weight_kg()` uses `runner_factor = 1.005 if mold.is_hot_runner else 1.03` regardless of `mold.cavities` or `order.part_weight_g`. Small caps/closures on cold-runner molds typically incur 10–25% runner/sprue scrap.

### Low Severity
4. **Press CP-SAT hits 5.0s cap in `ramadan_6h` (`0.58%` gap) & Workforce CP-SAT returns `FEASIBLE` in all 4 scenarios**
   - **Location:** [solver.py](file:///c:/Users/Sigma%20Alex/OneDrive/Desktop/DIOs/mini-dios-workforce/backend/core/solver.py#L426-L431), [#L600-L605](file:///c:/Users/Sigma%20Alex/OneDrive/Desktop/DIOs/mini-dios-workforce/backend/core/solver.py#L600-L605); [workforce_solver.py](file:///c:/Users/Sigma%20Alex/OneDrive/Desktop/DIOs/mini-dios-workforce/backend/core/workforce_solver.py#L711-L716)
   - **Detail:** Press CP-SAT has no `relative_gap_limit` and uses variable-size (including 0-duration) `OptionalIntervalVar`s in `AddNoOverlap` for Ramadan setup blackouts. Workforce CP-SAT runs `num_workers = 1` with `max_deterministic_time <= 0.25s` and no symmetry breaking between identical workers.

---

## 3. Model Productivity & Efficiency Recommendations

| Priority | Target | Recommendation | Impact / Effort | Expected Before -> After |
| :---: | :--- | :--- | :---: | :--- |
| **1** | `solver.py` | Set `relative_gap_limit = 0.005` (0.5%) and expand `AddHint` warm-starts to `scheduled[i]`, `AddCircuit` arcs, and `virgin_10`/`regrind_10` from FIFO/color-grouped heuristic | **High Impact / Low Effort** | Press CP-SAT: `3,509–5,048 ms` -> **<800 ms**; closes `ramadan_6h` gap |
| **2** | `workforce_solver.py` | Add lexicographic symmetry breaking between identical workers (same role, certs, preference) + increase `num_workers = 4` | **High Impact / Low Effort** | Workforce CP-SAT: `1,138–2,273 ms (FEASIBLE)` -> **<200 ms (`OPTIMAL`)** |
| **3** | `solver.py` | Prune time-infeasible `AddCircuit` arcs (`start_lb[i] + dur[i] > horizon_mins - dur[j]`) and guard Ramadan setup blackout intervals with `setup_vars[i] > 0` booleans | **High Impact / Medium Effort** | Eliminates Ramadan search-tree blowup; scales cleanly to **100+ orders** |
| **4** | `store.tsx` | Remove redundant `validatePlantJson()` before `solvePlantScheduleApi()` and deduplicate `loadWorkspaces()` on startup | **Medium Impact / Low Effort** | **-2 HTTP round-trips** on startup (~150–300 ms faster load) |
| **5** | `ExecutiveBriefModal.tsx` + `i18n.ts` | Add `Escape` key close handler and localize the 5 hardcoded English strings | **Medium Impact / Low Effort** | 100% keyboard accessibility & 100% Arabic RTL parity |
| **6** | `ontology.py` | Add optional `runner_scrap_pct` on `Mold` (defaulting to `0.5%` hot / `3–15%` cold) + optional dryer/chiller capacity warning | **Medium Impact / Medium Effort** | Higher material & cost accuracy for Egypt/KSA molding plants |

---

## 4. Next-Step Menu

No product logic has been modified yet. Which fixes or optimization recommendations would you like approved and implemented first?
1. **Quick Wins Bundle (Items #1, #2, #4, #5):** CP-SAT 4–6x speedup (`<800 ms` Press, `<200 ms OPTIMAL` Workforce), startup API dedup, and Executive Brief `Escape` + Arabic localization.
2. **Deep Scalability Upgrade (Item #3):** `AddCircuit` arc pruning + Ramadan interval reformulation for 100+ orders.
3. **Plant Physics Upgrade (Item #6):** Mold `runner_scrap_pct` + dryer/chiller capacity modeling.

*(Once you approve any item, `/change-check` will run automatically after every fix.)*
