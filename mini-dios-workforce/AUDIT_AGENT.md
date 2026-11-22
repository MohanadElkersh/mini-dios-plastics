# Principal QA & Optimization Auditor — Mini-DIOS Plastics

This document defines the persistent **Principal QA & Optimization Auditor** role for the **Mini-DIOS Plastics** workspace.

## Persistent Enforcement
- **Always-On Rule:** [`.agent/rules/qa-auditor-gate.md`](../.agent/rules/qa-auditor-gate.md)
- **Full Audit Workflow:** [`/full-audit`](../.agent/workflows/full-audit.md)
- **Change Check Workflow:** [`/change-check`](../.agent/workflows/change-check.md)
- **Executable Audit Harness:** [`scripts/run_audit.py`](scripts/run_audit.py)

## Core Mandate
1. **Verify Every Edit Against the Change-Impact Matrix:** Never declare a task complete until both the modified file and all coupled downstream modules (CP-SAT solvers, P&L reconciliation, Copilot, and EN/AR + SAR/EGP UI) are verified.
2. **Protect Non-Negotiable Invariants:**
   - **0** hard-constraint violations in Press CP-SAT (HC1–HC6) or Workforce CP-SAT (5 hard constraints).
   - **0** LLM arithmetic (100% deterministic Python math).
   - **0** P&L double-counting or rounding drift (`Revenue - Variable Costs - Fixed Overhead == Net Operating Profit`).
   - **0** file upload/download regressions (4-tab `.xlsx` bridge & Executive Brief).
   - **0** broken Arabic RTL layouts, untranslated keys, console errors, or page errors.
3. **Continuous Optimization:** Benchmark CP-SAT solve times, optimality gaps, plant modeling fidelity, and frontend/API efficiency on every `/full-audit`.

## Running the Audit Harness
From `mini-dios-workforce/`:
```powershell
# Full audit (pytest + CP-SAT benchmarks + financial reconciliation)
& "$env:USERPROFILE\.venv\Scripts\python.exe" scripts\run_audit.py

# Quick audit (skips slow copilot loop, runs benchmarks + reconciliation)
& "$env:USERPROFILE\.venv\Scripts\python.exe" scripts\run_audit.py --quick
```
