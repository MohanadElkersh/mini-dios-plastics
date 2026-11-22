---
description: Run the complete end-to-end backend, CP-SAT solver benchmark, frontend build, and live E2E browser sweep across all 6 tabs + Ops Copilot + Executive Brief, and generate AUDIT_REPORT.md.
---

# `/full-audit` — Full System Audit Workflow

Execute all steps below sequentially and report results in `AUDIT_REPORT.md`:

1. **Run Backend & Benchmark Harness (`scripts/run_audit.py`):**
   - Execute from `mini-dios-workforce/`:
     `& "$env:USERPROFILE\.venv\Scripts\python.exe" scripts\run_audit.py`
   - Verifies:
     - Full `pytest` suite (`backend/tests/`) with per-test timings.
     - CP-SAT Solver Performance & Optimality Benchmark (Standard, Ramadan 6h, Heavy Disruption, Workforce Callout Stress Tests) logging solve time (ms), status (`OPTIMAL` vs `FEASIBLE`), optimality gap, and savings deltas.
     - Financial Reconciliation Cross-Check (`Revenue - All Itemized Costs == Net Operating Profit`, zero double-counting, zero rounding drift).

2. **Frontend Production Build:**
   - Execute from `mini-dios-workforce/frontend/`:
     `..\.tools\node\npm.cmd run build` (or `npm.cmd run build`).
   - Confirm zero TypeScript or Next.js build errors.

3. **Live Headless Browser E2E Sweep:**
   - Start backend (`uvicorn main:app --host 127.0.0.1 --port 8000`) and frontend (`npm.cmd run start` or `dev` on port 3000).
   - Verify all 6 tabs:
     - Tab 1 (Scope & Plant Data) + Data Studio inline edits
     - Tab 2 (Resins, Molds & Physics)
     - Tab 3 (Scenario Composer)
     - Tab 4 (Press Gantt)
     - Tab 5 (Revenue & Savings P&L) + Executive Brief modal
     - Tab 6 (Workforce & Shifts) + worker CRUD / callout
   - Verify Ops Copilot drawer (offline/live + "Apply This Scenario to Dashboard").
   - Verify **English (LTR)** and **Arabic (RTL)** switching, **SAR / EGP** currency switching, and assert **0 console errors** and **0 page errors**.

4. **Deep Code & CP-SAT Efficiency Inspection:**
   - Inspect `solver.py`, `workforce_solver.py`, `financials.py`, `copilot.py`, and `frontend/src/lib/store.tsx`.
   - Identify bugs, edge-case gaps, CP-SAT speedup opportunities, plant modeling gaps, and UX/perf improvements.

5. **Generate `AUDIT_REPORT.md`:**
   - Output the 4-section report:
     1. System Health Scorecard (PASS/FAIL table)
     2. Bugs, Broken Links & Edge Cases Found (ranked Critical/High/Medium/Low with file:line)
     3. Model Productivity & Efficiency Recommendations (ranked Impact vs. Effort with before/after expectations)
     4. Next-Step Menu (awaiting user approval before modifying product logic)
