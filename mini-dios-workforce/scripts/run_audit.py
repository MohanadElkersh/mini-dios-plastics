"""Executable QA & Optimization Audit Harness for Mini-DIOS Plastics.

Runs:
1. Full pytest suite (`backend/tests/`) with per-test timing (unless `--quick` skips pytest).
2. CP-SAT Solver Performance & Optimality Benchmark across 4 stress scenarios:
   - standard
   - ramadan_6h
   - heavy_disruption (press breakdown + resin shortage + rush export order)
   - workforce_callout (sick workers + callouts)
3. Financial Reconciliation Cross-Check:
   - Revenue - Variable Costs == Gross Profit
   - Gross Profit - Fixed Overhead == Net Operating Profit
   - Itemized variable costs == Variable Production Cost (zero double-counting / drift)
   - Labor cost matches Workforce KPIs exactly
   - Annualized savings == total_weekly_savings * annual_operating_weeks
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from core.ontology import (  # noqa: E402
    MachineBreakdown,
    ProductionOrder,
    ResinShortage,
    ScenarioDisruptions,
    SolverConfig,
    WorkforceCallout,
)
from core.seed import default_config, demo_dataset  # noqa: E402
from core.solver import solve_plant_schedule  # noqa: E402


def run_pytest(quick: bool = False) -> bool:
    print("\n" + "=" * 72)
    print("1. BACKEND PYTEST SUITE")
    print("=" * 72)
    cmd = [sys.executable, "-m", "pytest", "-v", "--durations=0"]
    if quick:
        cmd += ["-k", "not copilot_offline_handles_all_5_starter"]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND_DIR)
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=str(BACKEND_DIR), env=env)
    elapsed = time.perf_counter() - t0
    print(f"Pytest completed in {elapsed:.2f}s (exit code={proc.returncode})")
    return proc.returncode == 0


def check_financial_reconciliation(name: str, result) -> list[str]:
    errors: list[str] = []
    fin = result.financials
    wf = result.workforce

    for label, plan_fin, wf_plan in (
        ("baseline", fin.baseline, wf.baseline if wf else None),
        ("optimized", fin.optimized, wf.optimized if wf else None),
    ):
        # 1. Gross profit = Recognized revenue - Variable production cost
        gp_diff = abs((plan_fin.recognized_revenue - plan_fin.variable_production_cost) - plan_fin.gross_profit)
        if gp_diff > 0.05:
            errors.append(f"[{name}:{label}] Gross profit mismatch: diff={gp_diff:.4f}")

        # 2. Net operating profit = Gross profit - Weekly fixed overhead
        np_diff = abs((plan_fin.gross_profit - plan_fin.weekly_fixed_overhead) - plan_fin.net_operating_profit)
        if np_diff > 0.05:
            errors.append(f"[{name}:{label}] Net profit mismatch: diff={np_diff:.4f}")

        # 3. Total operating cost = Variable + Fixed overhead
        toc_diff = abs((plan_fin.variable_production_cost + plan_fin.weekly_fixed_overhead) - plan_fin.total_operating_cost)
        if toc_diff > 0.05:
            errors.append(f"[{name}:{label}] Total operating cost mismatch: diff={toc_diff:.4f}")

        # 4. Itemized variable costs sum == variable_production_cost
        itemized = (
            plan_fin.direct_resin_cost
            + plan_fin.purge_scrap_cost
            + plan_fin.energy_and_press_operating_cost
            + plan_fin.late_delivery_penalties
            + plan_fin.wip_holding_cost
            + plan_fin.direct_labor_and_overtime_cost
        )
        var_diff = abs(itemized - plan_fin.variable_production_cost)
        if var_diff > 0.05:
            errors.append(f"[{name}:{label}] Itemized variable sum mismatch: diff={var_diff:.4f}")

        # 5. Labor cost matches workforce KPIs (no double-counting or drift)
        if wf_plan is not None:
            labor_diff = abs(plan_fin.direct_labor_and_overtime_cost - round(wf_plan.kpis.total_labor_cost, 2))
            if labor_diff > 0.02:
                errors.append(
                    f"[{name}:{label}] Labor cost drift: fin={plan_fin.direct_labor_and_overtime_cost} vs wf={wf_plan.kpis.total_labor_cost}"
                )

    # 6. Weekly savings & annualized savings formula
    expected_weekly = round(
        (fin.baseline.total_operating_cost - fin.optimized.total_operating_cost)
        + (fin.optimized.recognized_revenue - fin.baseline.recognized_revenue),
        2,
    )
    if abs(expected_weekly - fin.total_weekly_savings) > 0.05:
        errors.append(f"[{name}] Weekly savings mismatch: expected={expected_weekly} vs got={fin.total_weekly_savings}")

    expected_annual = round(fin.total_weekly_savings * fin.annual_operating_weeks, 2)
    if abs(expected_annual - fin.annual_projected_savings) > 0.10:
        errors.append(f"[{name}] Annualized savings mismatch: expected={expected_annual} vs got={fin.annual_projected_savings}")

    return errors


def build_benchmark_scenarios():
    base_ds = demo_dataset()

    # 1. Standard
    std_ds = base_ds.model_copy(deep=True)
    std_cfg = default_config()

    # 2. Ramadan 6h
    ram_ds = base_ds.model_copy(deep=True)
    ram_cfg = SolverConfig(ramadan_shift_mode=True)

    # 3. Heavy Disruption (Press breakdown + HDPE shortage + rush export order)
    heavy_ds = base_ds.model_copy(deep=True)
    rush = ProductionOrder(
        order_id="RUSH-EXP-99",
        customer="Almarai Packaging KSA",
        sku_name="Urgent 40k White Cap Export",
        mold_id=heavy_ds.molds[0].mold_id,
        resin_code="HDPE",
        color="White",
        quantity_pcs=40_000,
        part_weight_g=14.5,
        due_hr=96.0,
        unit_selling_price=0.45,
        late_penalty_per_hr=350.0,
        max_regrind_pct=0.0,
        is_export=True,
    )
    heavy_cfg = SolverConfig(
        scenarios=ScenarioDisruptions(
            machine_breakdowns=[MachineBreakdown(machine_id="P-500T", start_hr=48.0, duration_hrs=18.0)],
            resin_shortages=[ResinShortage(resin_code="HDPE", available_pct_reduction=35.0, virgin_price_spike_pct=15.0)],
            rush_orders=[rush],
            allow_regrind_override_pct=25.0,
        )
    )

    # 4. Autonomous PM Co-Optimization
    auto_pm_ds = base_ds.model_copy(deep=True)
    auto_pm_cfg = SolverConfig(autonomous_pm_window=True)

    # 5. Workforce Callout Stress Test (2 sick/leave workers)
    wf_ds = base_ds.model_copy(deep=True)
    if len(wf_ds.workers) >= 2:
        wf_ds.workers[0].status = "sick"
        wf_ds.workers[1].status = "on_leave"
    wf_cfg = SolverConfig()

    return [
        ("standard", std_ds, std_cfg),
        ("ramadan_6h", ram_ds, ram_cfg),
        ("heavy_disruption", heavy_ds, heavy_cfg),
        ("autonomous_pm", auto_pm_ds, auto_pm_cfg),
        ("workforce_callout", wf_ds, wf_cfg),
    ]


def run_benchmarks() -> tuple[bool, list[str]]:
    print("\n" + "=" * 72)
    print("2. CP-SAT PERFORMANCE, OPTIMALITY & P&L RECONCILIATION BENCHMARK")
    print("=" * 72)
    header = (
        f"{'Scenario':<18} | {'Press(ms)':>9} | {'P-Status':<8} | {'Gap%':>6} | "
        f"{'WF(ms)':>7} | {'W-Status':<8} | {'Savings/wk':>11} | {'HC':>4}"
    )
    print(header)
    print("-" * len(header))

    all_ok = True
    all_errors: list[str] = []

    for name, ds, cfg in build_benchmark_scenarios():
        res = solve_plant_schedule(ds, cfg)
        wf = res.workforce
        wf_ms = wf.solve_time_ms if wf else 0
        wf_status = wf.status if wf else "N/A"
        wf_hc = wf.all_hard_constraints_passed if wf else True
        press_hc = res.audit.all_hard_constraints_passed
        hc_ok = press_hc and wf_hc

        print(
            f"{name:<18} | {res.solve_time_ms:>9} | {res.status:<8} | {res.gap_pct:>5.2f}% | "
            f"{wf_ms:>7} | {wf_status:<8} | {res.financials.total_weekly_savings:>11,.2f} | "
            f"{'PASS' if hc_ok else 'FAIL':>4}"
        )

        if not hc_ok:
            all_ok = False
            all_errors.append(f"[{name}] Hard constraint check failed (press={press_hc}, wf={wf_hc})")

        fin_errs = check_financial_reconciliation(name, res)
        if fin_errs:
            all_ok = False
            all_errors.extend(fin_errs)

    print("\n3. FINANCIAL RECONCILIATION SUMMARY")
    print("-" * 40)
    if not all_errors:
        print("PASS: All scenarios reconciled with zero P&L drift or double-counting.")
    else:
        for err in all_errors:
            print(f"FAIL: {err}")

    return all_ok, all_errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Mini-DIOS Plastics Audit Harness")
    parser.add_argument("--quick", action="store_true", help="Skip slow multi-scenario copilot pytest loop")
    parser.add_argument("--skip-pytest", action="store_true", help="Run only CP-SAT benchmarks & P&L reconciliation")
    args = parser.parse_args()

    pytest_ok = True if args.skip_pytest else run_pytest(quick=args.quick)
    bench_ok, _ = run_benchmarks()

    print("\n" + "=" * 72)
    print(f"OVERALL AUDIT HARNESS RESULT: {'PASS' if (pytest_ok and bench_ok) else 'FAIL'}")
    print("=" * 72)
    return 0 if (pytest_ok and bench_ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
