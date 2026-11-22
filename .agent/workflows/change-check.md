---
description: Inspect recent modifications, map impacted modules via the Change-Impact Matrix, run targeted pytest + frontend build + E2E checks, and report PASS/FAIL.
---

# `/change-check` — Targeted & Ripple-Effect Regression Check

Execute after any code edit, feature addition, or refactor:

1. **Identify Modified Files:**
   - Check `git diff --name-only` (or recently modified files in `mini-dios-workforce/` if git is unavailable).

2. **Map Impacted Modules (Change-Impact Matrix):**
   - `ontology.py` -> `test_validator.py`, `test_solver.py`, `test_workforce_solver.py`, `test_financials.py`, `test_copilot.py`, `test_api.py`, E2E Tabs 1–6.
   - `solver.py` -> `test_solver.py`, `test_workforce_solver.py`, `test_financials.py`, `test_copilot.py`, `run_audit.py --quick`, E2E Tabs 4–6 + Copilot.
   - `workforce_solver.py` -> `test_workforce_solver.py`, `test_financials.py`, `test_copilot.py`, E2E Tabs 5–6 + Copilot.
   - `financials.py` -> `test_financials.py`, `test_copilot.py`, `run_audit.py --quick`, E2E Tab 5 + Executive Brief + Copilot.
   - `copilot.py` -> `test_copilot.py`, E2E Copilot Drawer + "Apply This Scenario to Dashboard".
   - `frontend/src/**` -> `npm.cmd run build`, headless browser E2E on affected + coupled tabs in EN (LTR) + AR (RTL) + SAR/EGP, asserting 0 console errors and 0 page errors.

3. **Run Verification:**
   - Run targeted `pytest` tests + `scripts/run_audit.py --quick`.
   - If frontend touched, run `npm.cmd run build` and headless browser E2E on affected tabs.

4. **Report PASS/FAIL:**
   - Summarize exact files checked, tests run, timings, and any side effects or regressions detected.
