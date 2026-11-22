---
trigger: always_on
description: Principal QA & Optimization Auditor gate for Mini-DIOS Plastics — enforces Change-Impact Matrix verification and non-negotiable quality gates after every edit.
---

# Principal QA & Optimization Auditor — Always-On Gate

You are operating in the **Mini-DIOS Plastics** repository (`mini-dios-workforce/`).
After **ANY** code edit, feature addition, or refactor in this repo, you **MUST NOT** declare a task "done" until you run a targeted + ripple-effect regression check covering both the modified files AND every coupled module defined in the Change-Impact Matrix below.

## 1. Change-Impact Matrix (Test Everything Related to the Change)

| Modified Area | Mandatory Coupled Checks |
| :--- | :--- |
| `backend/core/ontology.py` | Test `validator`, `solver`, `workforce_solver`, `financials`, `copilot`, all API routes (`test_api.py`), and E2E across Tabs 1–6. |
| `backend/core/solver.py` | Test Press Gantt (Tab 4), Purge/Scrap math, Mold PM & exclusivity, Workforce demand coupling (Tab 6), Revenue & Savings P&L (Tab 5), Ops Copilot, and CP-SAT solve-time benchmark (`scripts/run_audit.py`). |
| `backend/core/workforce_solver.py` | Test Tab 6 roster/coverage, Ramadan 6h toggle, rest-gap compliance, Tab 5 P&L labor cost line (verify zero double-counting), and Ops Copilot callout scenarios. |
| `backend/core/financials.py` | Test Tab 5 KPI cards, P&L reconciliation (`Revenue - All Itemized Costs == Net Operating Profit`), inline unit-price edits, annualized savings formula, Executive Brief modal, and Ops Copilot financial narration. |
| `backend/core/copilot.py` | Test live Gemini tool-calling (with 15s `HttpOptions` timeout & `thinking_level="low"`), zero-LLM-math guard, offline EN/AR fallback parity, and "Apply This Scenario to Dashboard" state sync. |
| Any `frontend/src/**` component or `store.tsx` | Run `npm.cmd run build` (using `.tools\node\npm.cmd` if needed), live headless browser E2E on affected + coupled tabs, verify both **English (LTR)** and **Arabic (RTL)**, verify **SAR / EGP** switching, and assert `0 console errors` and `0 page errors`. |

## 2. Non-Negotiable Quality Gates

1. **Zero Hard-Constraint Violations:** Both Press CP-SAT (HC1–HC6) and Workforce CP-SAT (5 hard constraints) must pass 100% of independent verification checks (`verify.py` / `verify_workforce`).
2. **Zero LLM Arithmetic:** 100% deterministic Python math. Never let an LLM compute costs, margins, hours, or schedules.
3. **Zero File Upload/Download UI Regressions:** 4-tab Excel bridge (`Presses`, `Molds`, `Resin_Inventory`, `Production_Orders`) and executive brief exports must remain intact.
4. **Zero Broken Arabic RTL or Raw Keys:** All UI text in `i18n.ts` must have complete EN + AR parity with clean RTL layout and zero untranslated keys.
5. **Zero P&L Double-Counting or Rounding Drift:** `Revenue - Variable Costs - Fixed Overhead == Net Operating Profit` across both Baseline and Optimized plans.

## 3. Execution Commands

- Quick ripple check after any edit: run `/change-check` (or `python scripts/run_audit.py --quick`).
- Full system audit: run `/full-audit` (or `python scripts/run_audit.py`).
- Python environment: `%USERPROFILE%\.venv\Scripts\python.exe` (or `.venv\Scripts\python.exe` if present in repo).
- Node/npm: `mini-dios-workforce\.tools\node\npm.cmd` (or `npm.cmd` on PATH).
