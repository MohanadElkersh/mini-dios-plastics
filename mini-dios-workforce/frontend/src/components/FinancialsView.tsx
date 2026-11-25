"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowDownRight,
  ArrowUpRight,
  Banknote,
  Boxes,
  Building2,
  CalendarRange,
  CheckCircle2,
  DollarSign,
  History,
  Loader2,
  Play,
  Recycle,
  Search,
  Sparkles,
  TrendingUp,
  Zap,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { convertCurrency, formatMoney, formatNumber } from "@/lib/format";
import { useApp } from "@/lib/store";
import type { Currency } from "@/lib/types";
import { PinScenarioButton } from "./PinScenarioButton";
import { ScenarioComparisonMatrix } from "./ScenarioComparisonMatrix";

function pctChange(base: number, opt: number): string {
  if (Math.abs(base) < 1e-6) return "—";
  const pct = ((opt - base) / Math.abs(base)) * 100;
  return `${pct >= 0 ? "+" : ""}${pct.toFixed(1)}%`;
}

export function FinancialsView() {
  const {
    lang,
    currency,
    dataset,
    config,
    result,
    loading,
    updatePhysics,
    upsertOrder,
    runSolve,
    setBacktestModalOpen,
  } = useApp();

  const isAr = lang === "ar";
  const fx = config.fx_egp_per_sar;
  const ph = config.physics;
  const fin = result?.financials;
  const resCurrency: Currency = result?.currency ?? currency;

  const [orderQuery, setOrderQuery] = useState("");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Local draft state for inline unit selling price inputs so typing feels instant
  const [priceDrafts, setPriceDrafts] = useState<Record<string, string>>({});
  const [overheadDraft, setOverheadDraft] = useState<string>("");

  // Sync overhead draft when currency or config changes externally
  useEffect(() => {
    const displayVal = convertCurrency(ph.weekly_fixed_overhead, "SAR", currency, fx);
    setOverheadDraft(String(Math.round(displayVal)));
  }, [ph.weekly_fixed_overhead, currency, fx]);

  // Clear stale price drafts when dataset or currency refreshes from backend
  useEffect(() => {
    setPriceDrafts({});
  }, [dataset, currency]);

  const scheduleAutoSolve = (nextCfg = config, nextDs = dataset) => {
    if (!nextDs) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      void runSolve(nextCfg, nextDs);
    }, 500);
  };

  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  const ordersById = useMemo(
    () => new Map((dataset?.orders ?? []).map((o) => [o.order_id, o])),
    [dataset?.orders]
  );

  const filteredOrderRows = useMemo(() => {
    const rows = fin?.order_profitability ?? [];
    const q = orderQuery.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter(
      (r) =>
        r.order_id.toLowerCase().includes(q) ||
        r.customer.toLowerCase().includes(q) ||
        r.sku_name.toLowerCase().includes(q)
    );
  }, [fin?.order_profitability, orderQuery]);

  if (!result || !fin) {
    return (
      <div className="flex min-h-[360px] flex-col items-center justify-center rounded-2xl border border-slate-800 bg-[#0f1629] p-8 text-center">
        <Loader2 className="mb-3 h-7 w-7 animate-spin text-cyan-400" />
        <p className="text-sm font-semibold text-white">
          {isAr ? "جاري حساب التقرير المالي..." : "Computing deterministic financial report..."}
        </p>
      </div>
    );
  }

  const base = fin.baseline;
  const opt = fin.optimized;
  const toDisplay = (v: number) => convertCurrency(v, resCurrency, currency, fx);
  const fmtDisp = (v: number) => formatMoney(toDisplay(v), currency);
  const marginLiftPts = Number((opt.net_margin_pct - base.net_margin_pct).toFixed(1));

  // Chart A data: Baseline vs CP-SAT
  const comparisonChartData = [
    {
      name: isAr ? "الإيرادات" : "Revenue",
      [isAr ? "خط الأساس FIFO" : "Naive FIFO"]: Math.round(toDisplay(base.recognized_revenue)),
      [isAr ? "أمثلية CP-SAT" : "CP-SAT Optimized"]: Math.round(toDisplay(opt.recognized_revenue)),
    },
    {
      name: isAr ? "التكلفة الكلية" : "Total Cost",
      [isAr ? "خط الأساس FIFO" : "Naive FIFO"]: Math.round(toDisplay(base.total_operating_cost)),
      [isAr ? "أمثلية CP-SAT" : "CP-SAT Optimized"]: Math.round(toDisplay(opt.total_operating_cost)),
    },
    {
      name: isAr ? "صافي الربح" : "Net Profit",
      [isAr ? "خط الأساس FIFO" : "Naive FIFO"]: Math.round(toDisplay(base.net_operating_profit)),
      [isAr ? "أمثلية CP-SAT" : "CP-SAT Optimized"]: Math.round(toDisplay(opt.net_operating_profit)),
    },
  ];

  // Chart B data: Itemized Savings Breakdown (includes Labor & Overtime Saved)
  const sb = fin.savings_breakdown;
  const laborSaved = sb.labor_and_overtime_saved ?? 0;
  const savingsChartData = [
    {
      name: isAr ? "وفر هالك التنظيف" : "Purge Scrap",
      value: Math.round(toDisplay(sb.purge_scrap_saved)),
      color: "#22d3ee",
    },
    {
      name: isAr ? "وفر العمالة والإضافي" : "Labor & Overtime",
      value: Math.round(toDisplay(laborSaved)),
      color: "#ec4899",
    },
    {
      name: isAr ? "تجنب غرامات التأخير" : "Late Penalties",
      value: Math.round(toDisplay(sb.avoided_late_penalties)),
      color: "#10b981",
    },
    {
      name: isAr ? "الطاقة والتشغيل" : "Energy & Oper.",
      value: Math.round(toDisplay(sb.energy_and_operating_saved)),
      color: "#3b82f6",
    },
    {
      name: isAr ? "خلط الريجريند" : "Regrind Blend",
      value: Math.round(toDisplay(sb.regrind_blend_savings)),
      color: "#a855f7",
    },
    {
      name: isAr ? "تكلفة الاحتفاظ WIP" : "WIP Holding",
      value: Math.round(toDisplay(sb.wip_holding_saved)),
      color: "#f59e0b",
    },
  ];

  const handleOverheadChange = (raw: string) => {
    setOverheadDraft(raw);
    const num = Number(raw);
    if (Number.isNaN(num) || num < 0) return;
    const sarVal = Math.round(convertCurrency(num, currency, "SAR", fx) * 100) / 100;
    const nextCfg = {
      ...config,
      physics: { ...config.physics, weekly_fixed_overhead: sarVal },
    };
    updatePhysics({ weekly_fixed_overhead: sarVal });
    scheduleAutoSolve(nextCfg, dataset);
  };

  const handleRecoveryChange = (raw: string) => {
    const num = Math.max(0, Math.min(100, Number(raw)));
    if (Number.isNaN(num)) return;
    const nextCfg = {
      ...config,
      physics: { ...config.physics, scrap_regrind_recovery_pct: num },
    };
    updatePhysics({ scrap_regrind_recovery_pct: num });
    scheduleAutoSolve(nextCfg, dataset);
  };

  const handleWeeksChange = (raw: string) => {
    const num = Math.max(1, Math.min(52, Math.round(Number(raw))));
    if (Number.isNaN(num)) return;
    const nextCfg = {
      ...config,
      physics: { ...config.physics, annual_operating_weeks: num },
    };
    updatePhysics({ annual_operating_weeks: num });
    scheduleAutoSolve(nextCfg, dataset);
  };

  const handleOrderPriceChange = (orderId: string, raw: string) => {
    setPriceDrafts((prev) => ({ ...prev, [orderId]: raw }));
    const num = Number(raw);
    if (Number.isNaN(num) || num < 0 || !dataset) return;
    const existing = ordersById.get(orderId);
    if (!existing) return;
    const sarPrice = Math.round(convertCurrency(num, currency, "SAR", fx) * 10000) / 10000;
    const updatedOrder = { ...existing, unit_selling_price: sarPrice };
    upsertOrder(updatedOrder);
    const nextDs = {
      ...dataset,
      orders: dataset.orders.map((o) => (o.order_id === orderId ? updatedOrder : o)),
    };
    scheduleAutoSolve(config, nextDs);
  };

  const pnlRows = [
    {
      label: isAr ? "الإيرادات المحققة (المجدولة)" : "Recognized Revenue",
      base: base.recognized_revenue,
      opt: opt.recognized_revenue,
      delta: opt.recognized_revenue - base.recognized_revenue,
      higherIsBetter: true,
      bold: true,
    },
    {
      label: isAr ? "تكلفة الخامات المباشرة (الراتنج)" : "Direct Resin Material Cost",
      base: base.direct_resin_cost,
      opt: opt.direct_resin_cost,
      delta: base.direct_resin_cost - opt.direct_resin_cost,
      higherIsBetter: false,
      bold: false,
    },
    {
      label: isAr ? "تكلفة هالك التنظيف (صافي بعد الاسترداد)" : "Purge Scrap Cost (Net of Recovery)",
      base: base.purge_scrap_cost,
      opt: opt.purge_scrap_cost,
      delta: base.purge_scrap_cost - opt.purge_scrap_cost,
      higherIsBetter: false,
      bold: false,
    },
    {
      label: isAr ? "تكلفة الطاقة وتشغيل المكابس" : "Energy & Press Operating Cost",
      base: base.energy_and_press_operating_cost,
      opt: opt.energy_and_press_operating_cost,
      delta: base.energy_and_press_operating_cost - opt.energy_and_press_operating_cost,
      higherIsBetter: false,
      bold: false,
    },
    {
      label: isAr ? "غرامات تأخير التسليم" : "Late Delivery Penalties",
      base: base.late_delivery_penalties,
      opt: opt.late_delivery_penalties,
      delta: base.late_delivery_penalties - opt.late_delivery_penalties,
      higherIsBetter: false,
      bold: false,
    },
    {
      label: isAr ? "تكلفة الاحتفاظ بالمخزون WIP" : "WIP Holding Cost",
      base: base.wip_holding_cost,
      opt: opt.wip_holding_cost,
      delta: base.wip_holding_cost - opt.wip_holding_cost,
      higherIsBetter: false,
      bold: false,
      testId: "pnl-row-wip",
    },
    {
      label: isAr ? "تكلفة عمالة المصنع والوقت الإضافي" : "Direct Floor Labor & Overtime Cost",
      base: base.direct_labor_and_overtime_cost ?? 0,
      opt: opt.direct_labor_and_overtime_cost ?? 0,
      delta: (base.direct_labor_and_overtime_cost ?? 0) - (opt.direct_labor_and_overtime_cost ?? 0),
      higherIsBetter: false,
      bold: false,
      testId: "pnl-row-labor",
    },
    {
      label: isAr
        ? `إجمالي الربح (${opt.gross_margin_pct.toFixed(1)}% هامش)`
        : `Gross Profit (${opt.gross_margin_pct.toFixed(1)}% margin)`,
      base: base.gross_profit,
      opt: opt.gross_profit,
      delta: opt.gross_profit - base.gross_profit,
      higherIsBetter: true,
      bold: true,
      highlight: true,
    },
    {
      label: isAr ? "المصاريف الإدارية والثابتة الأسبوعية" : "Weekly Fixed Overhead",
      base: base.weekly_fixed_overhead,
      opt: opt.weekly_fixed_overhead,
      delta: base.weekly_fixed_overhead - opt.weekly_fixed_overhead,
      higherIsBetter: false,
      bold: false,
    },
    {
      label: isAr
        ? `صافي الربح التشغيلي (${opt.net_margin_pct.toFixed(1)}% هامش)`
        : `Net Operating Profit (${opt.net_margin_pct.toFixed(1)}% margin)`,
      base: base.net_operating_profit,
      opt: opt.net_operating_profit,
      delta: opt.net_operating_profit - base.net_operating_profit,
      higherIsBetter: true,
      bold: true,
      highlight: true,
    },
  ];

  return (
    <div className="w-full max-w-full min-w-0 space-y-6" data-testid="financials-view">
      {/* Executive Header Bar with One-Click Scenario Pinning */}
      <div className="flex min-w-0 flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-800 bg-[#0f1629] px-5 py-3.5">
        <div>
          <h2 className="text-sm font-bold text-white">
            {isAr ? "تقرير الإيرادات وصافي الربح والوفورات التنفيذي" : "Executive Revenue, Net Profit & Savings P&L"}
          </h2>
          <p className="text-xs text-slate-400">
            {isAr
              ? "تحليل حتمي 100% من محرك OR-Tools CP-SAT مع تحويل فوري بين الريال والجنيه"
              : "100% deterministic OR-Tools CP-SAT P&L with instant SAR / EGP currency reconciliation"}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            data-testid="btn-open-backtest-financials"
            onClick={() => setBacktestModalOpen(true)}
            className="inline-flex min-h-[40px] items-center gap-1.5 rounded-xl border border-emerald-500/40 bg-emerald-500/15 px-3.5 py-2 text-xs font-bold text-emerald-200 transition hover:bg-emerald-500/25 md:min-h-0"
          >
            <History className="h-3.5 w-3.5 text-emerald-400" />
            <span>
              {isAr ? "اختبار تاريخي لشهر كامل (Actual vs. Mini-DIOS)" : "1-Month Historical Backtest (Proof Engine)"}
            </span>
          </button>
          <PinScenarioButton testId="btn-pin-scenario-financials" />
        </div>
      </div>

      {/* v1.3 Feature 3: Working Capital & Multi-SKU Export Container WIP Holding Strip */}
      <div
        data-testid="financials-container-wip-card"
        className="grid gap-3 rounded-2xl border border-cyan-500/30 bg-[#0f1629] p-4 sm:grid-cols-2 lg:grid-cols-4"
      >
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-cyan-500/40 bg-cyan-500/15 text-cyan-300">
            <Boxes className="h-4 w-4" />
          </div>
          <div>
            <div className="text-[11px] text-slate-400">
              {isAr ? "رأس المال المحتجز بالحاويات" : "Trapped Container Working Capital"}
            </div>
            <div dir="ltr" className="font-mono text-sm font-bold text-amber-300">
              {fmtDisp(result.optimized.kpis.trapped_working_capital ?? 0)}
            </div>
          </div>
        </div>

        <div>
          <div className="text-[11px] text-slate-400">
            {isAr ? "ذروة إشغال مخزن المنتج التام" : "FG Warehouse Peak Load"}
          </div>
          <div dir="ltr" className="mt-0.5 font-mono text-sm font-bold text-cyan-300">
            {(result.optimized.kpis.warehouse_utilization_pct ?? 0).toFixed(1)}% (
            {(result.optimized.kpis.peak_warehouse_tons ?? 0).toFixed(1)}t /{" "}
            {(result.optimized.kpis.fg_storage_capacity_tons ?? 22).toFixed(0)}t)
          </div>
        </div>

        <div>
          <div className="text-[11px] text-slate-400">
            {isAr ? "أيام تخزين التجميع (طن-يوم)" : "WIP Holding Volume (Ton-Days)"}
          </div>
          <div dir="ltr" className="mt-0.5 font-mono text-sm font-bold text-indigo-300">
            {(result.optimized.kpis.wip_holding_days ?? 0).toFixed(1)} t-days
          </div>
        </div>

        <div>
          <div className="text-[11px] text-slate-400">
            {isAr ? "تكلفة الاحتفاظ بالمخزون WIP" : "Weekly WIP & Container Holding Cost"}
          </div>
          <div dir="ltr" className="mt-0.5 font-mono text-sm font-bold text-emerald-300">
            {fmtDisp(opt.wip_holding_cost)} (FIFO: {fmtDisp(base.wip_holding_cost)})
          </div>
        </div>
      </div>

      {/* Boardroom Side-by-Side Scenario Comparison Matrix (A vs. B vs. C) */}
      <ScenarioComparisonMatrix />

      {/* 1. Top 5 Executive Financial KPI Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {/* Card 1: Weekly Recognized Revenue */}
        <div
          data-testid="kpi-recognized-revenue"
          className="rounded-2xl border border-slate-800 bg-[#0f1629] p-4 shadow-lg"
        >
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>{isAr ? "الإيرادات المحققة أسبوعياً" : "Weekly Recognized Revenue"}</span>
            <DollarSign className="h-4 w-4 text-cyan-400" />
          </div>
          <div className="mt-2 font-mono text-2xl font-bold text-white">
            {fmtDisp(opt.recognized_revenue)}
          </div>
          <div className="mt-1.5 flex items-center justify-between text-[11px] text-slate-400">
            <span>
              {isAr ? "المحجوز:" : "Booked:"} {fmtDisp(opt.total_booked_revenue)}
            </span>
            {opt.at_risk_or_unscheduled_revenue > 0 ? (
              <span className="font-semibold text-amber-300">
                {isAr ? "معرض للخطر:" : "At-Risk:"}{" "}
                {fmtDisp(opt.at_risk_or_unscheduled_revenue)}
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-emerald-400">
                <CheckCircle2 className="h-3 w-3" />
                {isAr ? "100% مجدول" : "100% Covered"}
              </span>
            )}
          </div>
        </div>

        {/* Card 2: Optimized Net Profit & Margin % */}
        <div
          data-testid="kpi-net-profit"
          className="rounded-2xl border border-slate-800 bg-[#0f1629] p-4 shadow-lg"
        >
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>{isAr ? "صافي الربح والهامش" : "Optimized Net Profit & Margin"}</span>
            <TrendingUp className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="font-mono text-2xl font-bold text-white">
              {fmtDisp(opt.net_operating_profit)}
            </span>
            <span className="rounded-md bg-emerald-500/15 px-1.5 py-0.5 font-mono text-xs font-bold text-emerald-300">
              {opt.net_margin_pct.toFixed(1)}%
            </span>
          </div>
          <div className="mt-1.5 flex items-center gap-1 text-[11px] text-emerald-300">
            <ArrowUpRight className="h-3.5 w-3.5" />
            <span>
              {marginLiftPts >= 0 ? "+" : ""}
              {marginLiftPts.toFixed(1)}% {isAr ? "تحسن هامش عن FIFO" : "margin lift vs FIFO"}
            </span>
          </div>
        </div>

        {/* Card 3: Total Weekly Savings (Hero Card) */}
        <div
          data-testid="kpi-weekly-savings"
          className="rounded-2xl border border-emerald-500/40 bg-gradient-to-br from-emerald-500/15 via-[#0f1629] to-cyan-500/10 p-4 shadow-lg shadow-emerald-500/10"
        >
          <div className="flex items-center justify-between text-xs font-semibold text-emerald-300">
            <span>{isAr ? "إجمالي الوفورات الأسبوعية" : "Total Weekly Savings"}</span>
            <Sparkles className="h-4 w-4 text-emerald-300" />
          </div>
          <div className="mt-2 font-mono text-2xl font-extrabold text-emerald-300">
            {fmtDisp(fin.total_weekly_savings)}
          </div>
          <div className="mt-1.5 text-[11px] text-emerald-200/80">
            {isAr ? "قفزة الربح:" : "Profit Lift:"}{" "}
            <span className="font-mono font-bold">
              {fin.profit_lift_pct >= 0 ? "+" : ""}
              {fin.profit_lift_pct.toFixed(1)}%
            </span>{" "}
            {isAr ? "مقابل FIFO" : "vs Naive FIFO"}
          </div>
        </div>

        {/* Card 4: Annualized Projected Savings */}
        <div
          data-testid="kpi-annual-savings"
          className="rounded-2xl border border-slate-800 bg-[#0f1629] p-4 shadow-lg"
        >
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>{isAr ? "الوفورات السنوية المتوقعة" : "Annualized Projected Savings"}</span>
            <CalendarRange className="h-4 w-4 text-blue-400" />
          </div>
          <div className="mt-2 font-mono text-2xl font-bold text-cyan-300">
            {fmtDisp(fin.annual_projected_savings)}
          </div>
          <div className="mt-1.5 text-[11px] text-slate-400">
            {fin.annual_operating_weeks} {isAr ? "أسبوع تشغيل/سنة" : "operating wks/yr"} •{" "}
            {isAr ? "شهرياً:" : "Mo:"} {fmtDisp(fin.monthly_projected_savings)}
          </div>
        </div>

        {/* Card 5: Unlocked Capacity Value */}
        <div
          data-testid="kpi-unlocked-capacity"
          className="rounded-2xl border border-slate-800 bg-[#0f1629] p-4 shadow-lg"
        >
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>{isAr ? "قيمة الساعات المحررة" : "Unlocked Capacity Value"}</span>
            <Zap className="h-4 w-4 text-amber-400" />
          </div>
          <div className="mt-2 font-mono text-2xl font-bold text-amber-300">
            {fmtDisp(fin.unlocked_capacity_revenue_potential)}
          </div>
          <div className="mt-1.5 text-[11px] text-slate-400">
            {formatNumber(fin.unlocked_capacity_hours, 1)}{" "}
            {isAr ? "ساعة تبديل محررة أسبوعياً" : "changeover hrs freed / wk"}
          </div>
        </div>
      </div>

      {/* 2. Inline Financial Assumptions Strip */}
      <div className="flex flex-col justify-between gap-4 rounded-2xl border border-slate-800 bg-[#0f1629] px-4 py-3.5 sm:flex-row sm:flex-wrap sm:items-center sm:px-5">
        <div className="grid grid-cols-1 gap-3 sm:flex sm:flex-wrap sm:items-center sm:gap-5">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-200">
            <Building2 className="h-4 w-4 text-cyan-400" />
            <span>{isAr ? "الافتراضات المالية:" : "Financial Assumptions:"}</span>
          </div>

          <label className="flex items-center justify-between gap-2 text-xs text-slate-300 sm:justify-start">
            <span>{isAr ? `المصاريف الثابتة (${currency}/أسبوع)` : `Weekly Fixed Overhead (${currency})`}</span>
            <input
              type="number"
              min={0}
              step={500}
              data-testid="fin-input-overhead"
              value={overheadDraft}
              onChange={(e) => handleOverheadChange(e.target.value)}
              dir="ltr"
              className="min-h-[40px] w-28 rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-1 text-end font-mono text-base font-bold text-cyan-300 focus:border-cyan-500 focus:outline-none md:min-h-0 md:text-xs"
            />
          </label>

          <label className="flex items-center justify-between gap-2 text-xs text-slate-300 sm:justify-start">
            <span className="inline-flex items-center gap-1.5">
              <Recycle className="h-3.5 w-3.5 text-emerald-400" />
              <span>{isAr ? "استرداد الهالك (%)" : "Scrap Recovery (%)"}</span>
            </span>
            <input
              type="number"
              min={0}
              max={100}
              step={1}
              data-testid="fin-input-recovery"
              value={ph.scrap_regrind_recovery_pct}
              onChange={(e) => handleRecoveryChange(e.target.value)}
              dir="ltr"
              className="min-h-[40px] w-20 rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-1 text-end font-mono text-base font-bold text-emerald-300 focus:border-emerald-500 focus:outline-none md:min-h-0 md:text-xs"
            />
          </label>

          <label className="flex items-center justify-between gap-2 text-xs text-slate-300 sm:justify-start">
            <span>{isAr ? "أسابيع التشغيل/سنة" : "Operating Weeks / Yr"}</span>
            <input
              type="number"
              min={1}
              max={52}
              step={1}
              data-testid="fin-input-weeks"
              value={ph.annual_operating_weeks}
              onChange={(e) => handleWeeksChange(e.target.value)}
              dir="ltr"
              className="min-h-[40px] w-20 rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-1 text-end font-mono text-base font-bold text-blue-300 focus:border-blue-500 focus:outline-none sm:w-16 md:min-h-0 md:text-xs"
            />
          </label>
        </div>

        <button
          type="button"
          disabled={loading}
          onClick={() => void runSolve()}
          data-testid="fin-sync-solve"
          className="inline-flex min-h-[44px] w-full items-center justify-center gap-2 rounded-xl bg-cyan-500 px-3.5 py-1.5 text-xs font-bold text-slate-950 transition hover:bg-cyan-400 disabled:opacity-50 sm:w-auto md:min-h-0"
        >
          {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
          <span>{isAr ? "مزامنة CP-SAT" : "Run CP-SAT Optimization"}</span>
        </button>
      </div>

      {/* 3. Visual Charts (Recharts, RTL-safe dir="ltr") */}
      <div className="grid w-full max-w-full min-w-0 gap-6 lg:grid-cols-2">
        {/* Chart A: Baseline vs CP-SAT */}
        <div className="min-w-0 overflow-hidden rounded-2xl border border-slate-800 bg-[#0f1629] p-5">
          <div className="mb-4 flex items-center justify-between">
            <div className="min-w-0">
              <h3 className="truncate text-sm font-bold text-white">
                {isAr
                  ? "مقارنة الإيرادات والتكاليف والأرباح (FIFO مقابل CP-SAT)"
                  : "Baseline vs. CP-SAT Cost & Profit Comparison"}
              </h3>
              <p className="text-[11px] text-slate-400">
                {isAr ? `جميع القيم بعملة ${resCurrency}` : `All values in ${resCurrency}`}
              </p>
            </div>
            <Banknote className="h-4 w-4 shrink-0 text-cyan-400" />
          </div>
          <div dir="ltr" className="h-64 w-full min-w-0">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={comparisonChartData} margin={{ top: 10, right: 16, left: 8, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} />
                <YAxis stroke="#94a3b8" fontSize={11} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0b1120",
                    borderColor: "#334155",
                    borderRadius: "10px",
                    color: "#f8fafc",
                    fontSize: "12px",
                  }}
                />
                <Legend wrapperStyle={{ fontSize: "12px" }} />
                <Bar
                  dataKey={isAr ? "خط الأساس FIFO" : "Naive FIFO"}
                  fill="#64748b"
                  radius={[6, 6, 0, 0]}
                />
                <Bar
                  dataKey={isAr ? "أمثلية CP-SAT" : "CP-SAT Optimized"}
                  fill="#22d3ee"
                  radius={[6, 6, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart B: Itemized Savings Breakdown */}
        <div className="min-w-0 overflow-hidden rounded-2xl border border-slate-800 bg-[#0f1629] p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-white">
                {isAr
                  ? "مصادر الوفورات الأسبوعية (أين تتحقق المكاسب؟)"
                  : "Where Your Weekly Savings Come From"}
              </h3>
              <p className="text-[11px] text-slate-400">
                {isAr
                  ? `تفصيل الوفورات المحققة بعملة ${resCurrency}`
                  : `Itemized weekly savings breakdown (${resCurrency})`}
              </p>
            </div>
            <Sparkles className="h-4 w-4 text-emerald-400" />
          </div>
          <div dir="ltr" className="h-64 w-full min-w-0">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={savingsChartData}
                layout="vertical"
                margin={{ top: 5, right: 16, left: 4, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis type="number" stroke="#94a3b8" fontSize={10} />
                <YAxis type="category" dataKey="name" stroke="#cbd5e1" fontSize={10} width={96} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0b1120",
                    borderColor: "#334155",
                    borderRadius: "10px",
                    color: "#f8fafc",
                    fontSize: "12px",
                  }}
                />
                <Bar dataKey="value" radius={[0, 6, 6, 0]}>
                  {savingsChartData.map((entry, idx) => (
                    <Cell key={`cell-${idx}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* 4. Side-by-Side Executive P&L Statement Table */}
      <div className="overflow-hidden rounded-2xl border border-slate-800 bg-[#0f1629]">
        <div className="border-b border-slate-800 px-5 py-3.5">
          <h3 className="text-sm font-bold text-white">
            {isAr
              ? "قائمة الدخل التشغيلية الأسبوعية (P&L) — مقارنة خط الأساس مع CP-SAT"
              : "Side-by-Side Weekly Executive P&L Statement"}
          </h3>
        </div>
        <div className="overflow-x-auto touch-pan-x">
          <table className="w-full min-w-[580px] text-start text-xs">
            <thead className="bg-slate-900/70 text-[11px] uppercase text-slate-400">
              <tr>
                <th className="sticky start-0 z-10 bg-slate-900/95 px-3.5 py-3 text-start sm:px-5">
                  {isAr ? "البند المالي" : "Line Item"}
                </th>
                <th className="px-4 py-3 text-end">{isAr ? "خط الأساس FIFO" : "Naive FIFO Baseline"}</th>
                <th className="px-4 py-3 text-end">{isAr ? "أمثلية CP-SAT" : "CP-SAT Optimized"}</th>
                <th className="px-4 py-3 text-end">{isAr ? "الفرق (الوفر / المكسب)" : "Delta (Savings / Gain)"}</th>
                <th className="px-5 py-3 text-end">{isAr ? "التغير %" : "% Change"}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {pnlRows.map((row) => {
                const isGain = row.delta >= 0;
                return (
                  <tr
                    key={row.label}
                    data-testid={"testId" in row ? row.testId : undefined}
                    className={
                      row.highlight
                        ? "bg-slate-900/60 font-semibold"
                        : "hover:bg-slate-900/40"
                    }
                  >
                    <td
                      className={`sticky start-0 z-10 bg-[#0f1629]/95 px-3.5 py-3 sm:px-5 ${
                        row.bold ? "font-bold text-white" : "text-slate-300"
                      }`}
                    >
                      {row.label}
                    </td>
                    <td className="px-4 py-3 text-end font-mono text-slate-300" dir="ltr">
                      {fmtDisp(row.base)}
                    </td>
                    <td className="px-4 py-3 text-end font-mono font-bold text-white" dir="ltr">
                      {fmtDisp(row.opt)}
                    </td>
                    <td
                      className={`px-4 py-3 text-end font-mono font-bold ${
                        isGain ? "text-emerald-400" : "text-rose-400"
                      }`}
                      dir="ltr"
                    >
                      <span className="inline-flex items-center gap-1">
                        {isGain ? (
                          <ArrowUpRight className="h-3.5 w-3.5" />
                        ) : (
                          <ArrowDownRight className="h-3.5 w-3.5" />
                        )}
                        {row.delta >= 0 ? "+" : ""}
                        {fmtDisp(row.delta)}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-end font-mono text-slate-300" dir="ltr">
                      {pctChange(row.base, row.opt)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* 5. Interactive Order & Customer Profitability Table (Inline Price Editor) */}
      <div className="overflow-hidden rounded-2xl border border-slate-800 bg-[#0f1629]">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 px-5 py-3.5">
          <div>
            <h3 className="text-sm font-bold text-white">
              {isAr
                ? "ربحية أوامر الإنتاج والعملاء (تعديل سعر البيع مباشرة)"
                : "Order & Customer Profitability (Inline Price Editor)"}
            </h3>
            <p className="text-[11px] text-slate-400">
              {isAr
                ? "أي تعديل في سعر بيع القطعة يتزامن فوراً مع تبويب 2 ويعيد حساب الإيرادات والهوامش تلقائياً."
                : "Editing Unit Selling Price syncs immediately with Tab 2 and recalculates revenue, profit, and margins."}
            </p>
          </div>
          <div className="relative w-full sm:w-64">
            <Search className="pointer-events-none absolute start-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={orderQuery}
              onChange={(e) => setOrderQuery(e.target.value)}
              placeholder={isAr ? "بحث بالطلب أو العميل..." : "Filter order or customer..."}
              className="min-h-[44px] w-full rounded-xl border border-slate-700 bg-slate-900 py-1.5 pe-3 ps-8 text-base text-white placeholder:text-slate-500 focus:border-cyan-500 focus:outline-none md:min-h-0 md:text-xs"
            />
          </div>
        </div>

        <div className="overflow-x-auto touch-pan-x">
          <table className="w-full min-w-[720px] text-start text-xs">
            <thead className="bg-slate-900/70 text-[11px] uppercase text-slate-400">
              <tr>
                <th className="sticky start-0 z-10 bg-slate-900/95 px-4 py-3 text-start">{isAr ? "الطلب" : "Order"}</th>
                <th className="px-4 py-3 text-start">{isAr ? "العميل" : "Customer"}</th>
                <th className="px-4 py-3 text-start">{isAr ? "المنتج" : "SKU"}</th>
                <th className="px-3 py-3 text-end">{isAr ? "الكمية" : "Qty (pcs)"}</th>
                <th className="px-3 py-3 text-end">
                  {isAr ? `سعر القطعة (${resCurrency})` : `Unit Price (${resCurrency})`}
                </th>
                <th className="px-3 py-3 text-end">{isAr ? "الإيرادات" : "Revenue"}</th>
                <th className="px-3 py-3 text-end">{isAr ? "التكلفة" : "Prod. Cost"}</th>
                <th className="px-3 py-3 text-end">{isAr ? "غرامة التأخير" : "Late Penalty"}</th>
                <th className="px-3 py-3 text-end">{isAr ? "صافي الربح" : "Net Profit"}</th>
                <th className="px-4 py-3 text-end">{isAr ? "الهامش %" : "Margin %"}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {filteredOrderRows.map((row) => {
                const prodCost =
                  row.direct_resin_cost + row.allocated_energy_cost + row.allocated_purge_cost;
                const draftVal =
                  priceDrafts[row.order_id] ?? String(row.unit_selling_price);
                const badgeClass =
                  row.order_margin_pct >= 18
                    ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/30"
                    : row.order_margin_pct >= 0
                    ? "bg-amber-500/15 text-amber-300 border-amber-500/30"
                    : "bg-rose-500/15 text-rose-300 border-rose-500/30";

                return (
                  <tr key={row.order_id} className="hover:bg-slate-900/40">
                    <td className="sticky start-0 z-10 bg-[#0f1629]/95 px-4 py-2.5 font-mono font-bold text-cyan-300">
                      {row.order_id}
                    </td>
                    <td className="px-4 py-2.5 text-slate-200">{row.customer}</td>
                    <td className="px-4 py-2.5 text-slate-300">{row.sku_name}</td>
                    <td className="px-3 py-2.5 text-end font-mono text-slate-300" dir="ltr">
                      {row.quantity_pcs.toLocaleString("en-US")}
                    </td>
                    <td className="px-3 py-2.5 text-end" dir="ltr">
                      <input
                        type="number"
                        min={0}
                        step={0.005}
                        data-testid={`fin-price-${row.order_id}`}
                        value={draftVal}
                        onChange={(e) => handleOrderPriceChange(row.order_id, e.target.value)}
                        className="w-24 rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-end font-mono text-xs font-bold text-cyan-300 focus:border-cyan-500 focus:outline-none"
                      />
                    </td>
                    <td className="px-3 py-2.5 text-end font-mono text-white" dir="ltr">
                      {formatMoney(row.order_revenue, resCurrency)}
                    </td>
                    <td className="px-3 py-2.5 text-end font-mono text-slate-300" dir="ltr">
                      {formatMoney(prodCost, resCurrency)}
                    </td>
                    <td
                      className={`px-3 py-2.5 text-end font-mono ${
                        row.late_penalty > 0 ? "text-rose-400" : "text-slate-500"
                      }`}
                      dir="ltr"
                    >
                      {formatMoney(row.late_penalty, resCurrency)}
                    </td>
                    <td
                      className={`px-3 py-2.5 text-end font-mono font-bold ${
                        row.net_order_profit >= 0 ? "text-emerald-300" : "text-rose-400"
                      }`}
                      dir="ltr"
                    >
                      {formatMoney(row.net_order_profit, resCurrency)}
                    </td>
                    <td className="px-4 py-2.5 text-end" dir="ltr">
                      <span
                        className={`inline-block rounded-full border px-2 py-0.5 font-mono text-[11px] font-bold ${badgeClass}`}
                      >
                        {row.order_margin_pct.toFixed(1)}%
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
