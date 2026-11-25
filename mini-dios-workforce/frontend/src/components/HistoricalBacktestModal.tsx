"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  Award,
  CalendarClock,
  CheckCircle2,
  Clock,
  Download,
  FileSpreadsheet,
  Flame,
  History,
  Loader2,
  PackageCheck,
  Play,
  Recycle,
  TrendingUp,
  Upload,
  X,
} from "lucide-react";
import {
  getBacktestTemplateUrl,
  runBacktestSampleApi,
  uploadBacktestFileApi,
} from "@/lib/api";
import { convertCurrency, formatMoney, formatNumber } from "@/lib/format";
import { COPY } from "@/lib/i18n";
import { useApp } from "@/lib/store";

export function HistoricalBacktestModal() {
  const {
    lang,
    currency,
    dataset,
    config,
    backtestModalOpen,
    setBacktestModalOpen,
    backtestReport,
    setBacktestReport,
  } = useApp();

  const t = COPY[lang];
  const isAr = lang === "ar";
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleRunSample = async () => {
    setBusy(true);
    setErr(null);
    try {
      const rep = await runBacktestSampleApi(currency, dataset, config);
      setBacktestReport(rep);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Failed to run 30-day historical replay");
    } finally {
      setBusy(false);
    }
  };

  // Auto-load sample replay the first time the modal opens if no report exists yet
  useEffect(() => {
    if (backtestModalOpen && !backtestReport && !busy) {
      void handleRunSample();
    }
  }, [backtestModalOpen]);

  useEffect(() => {
    if (!backtestModalOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setBacktestModalOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [backtestModalOpen, setBacktestModalOpen]);

  if (!backtestModalOpen) return null;

  const handleFileUpload = async (file: File) => {
    setBusy(true);
    setErr(null);
    try {
      const rep = await uploadBacktestFileApi(file, currency, dataset, config);
      setBacktestReport(rep);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Failed to parse uploaded historical log");
    } finally {
      setBusy(false);
    }
  };

  const fromCur = backtestReport?.currency ?? currency;
  const fx = backtestReport?.fx_egp_per_sar ?? config.fx_egp_per_sar ?? 13.0;
  const fmtMoney = (amt: number) =>
    formatMoney(convertCurrency(amt, fromCur, currency, fx), currency);

  const d = backtestReport?.actual_vs_optimized;
  const act = backtestReport?.actual;
  const opt = backtestReport?.optimized;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center p-0 sm:items-center sm:p-4">
      <div
        className="fixed inset-0 bg-slate-950/85 backdrop-blur-sm"
        onClick={() => setBacktestModalOpen(false)}
      />

      <div
        data-testid="historical-backtest-modal"
        className="relative z-10 flex max-h-[92dvh] w-full max-w-5xl flex-col overflow-hidden rounded-t-3xl border border-slate-700/80 bg-[#0b1120] shadow-2xl sm:rounded-2xl"
        role="dialog"
        aria-modal="true"
      >
        {/* Header */}
        <div className="flex shrink-0 items-center justify-between border-b border-slate-800 bg-slate-950/90 px-4 py-3.5 sm:px-6 sm:py-4">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-emerald-500/40 bg-gradient-to-br from-emerald-500/20 to-cyan-500/20 text-emerald-300">
              <History className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="truncate text-sm font-bold text-white sm:text-lg">
                  {t.backtestTitle}
                </h2>
                <span className="rounded-full border border-emerald-500/40 bg-emerald-500/15 px-2.5 py-0.5 text-[10px] font-bold uppercase text-emerald-300">
                  {t.backtestBadge} • OR-Tools CP-SAT
                </span>
              </div>
              <p className="truncate text-[11px] text-slate-400 sm:text-xs">
                {t.backtestSubtitle}
              </p>
            </div>
          </div>

          <button
            type="button"
            data-testid="btn-close-backtest-modal"
            onClick={() => setBacktestModalOpen(false)}
            className="inline-flex min-h-[44px] min-w-[44px] shrink-0 items-center justify-center rounded-xl text-slate-400 hover:bg-slate-800 hover:text-white md:min-h-0 md:min-w-0 md:p-1.5"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 space-y-5 overflow-y-auto p-4 sm:p-6">
          {/* Action Bar: 1-Click Sample Replay + Download Templates + File Uploader */}
          <div className="grid gap-3 rounded-2xl border border-slate-800 bg-[#0f1629] p-4 lg:grid-cols-12">
            <div className="flex flex-col justify-between gap-2.5 lg:col-span-7">
              <div className="text-xs font-bold text-slate-200">
                {isAr
                  ? "١. تشغيل محاكاة شهر كامل فوراً أو تحميل قالب السجل التاريخي:"
                  : "1. Run Instant 30-Day Demo Replay or Download Log Template:"}
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  data-testid="btn-run-sample-backtest"
                  disabled={busy}
                  onClick={() => void handleRunSample()}
                  className="inline-flex min-h-[44px] items-center gap-2 rounded-xl bg-emerald-500 px-4 py-2 text-xs font-bold text-slate-950 shadow-lg shadow-emerald-500/20 transition hover:bg-emerald-400 disabled:opacity-50 md:min-h-0"
                >
                  {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                  <span>{t.backtestRunSampleBtn}</span>
                </button>

                <a
                  href={getBacktestTemplateUrl("csv")}
                  download="mini_dios_30day_backtest_template.csv"
                  data-testid="btn-download-backtest-csv"
                  className="inline-flex min-h-[44px] items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:border-cyan-500/50 hover:text-white md:min-h-0"
                >
                  <Download className="h-3.5 w-3.5 text-cyan-400" />
                  <span>{t.backtestDownloadCsvBtn}</span>
                </a>

                <a
                  href={getBacktestTemplateUrl("xlsx")}
                  download="mini_dios_30day_backtest_template.xlsx"
                  data-testid="btn-download-backtest-xlsx"
                  className="inline-flex min-h-[44px] items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:border-emerald-500/50 hover:text-white md:min-h-0"
                >
                  <FileSpreadsheet className="h-3.5 w-3.5 text-emerald-400" />
                  <span>{t.backtestDownloadXlsxBtn}</span>
                </a>
              </div>
            </div>

            {/* File Picker / Drag-and-Drop Uploader */}
            <div className="lg:col-span-5">
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv,.xlsx,.xls"
                className="hidden"
                data-testid="input-backtest-file"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) void handleFileUpload(f);
                  e.target.value = "";
                }}
              />
              <button
                type="button"
                data-testid="btn-upload-backtest-file"
                disabled={busy}
                onClick={() => fileInputRef.current?.click()}
                className="flex min-h-[76px] w-full flex-col items-center justify-center gap-1 rounded-xl border border-dashed border-cyan-500/40 bg-cyan-500/5 px-4 py-3 text-center text-xs transition hover:border-cyan-400 hover:bg-cyan-500/10 disabled:opacity-50"
              >
                <div className="flex items-center gap-1.5 font-bold text-cyan-300">
                  <Upload className="h-4 w-4" />
                  <span>{t.backtestUploadLabel}</span>
                </div>
                <span className="text-[11px] text-slate-400">
                  {isAr
                    ? "الأعمدة: order_id, resin, color, qty_units, press_id, actual_changeover_hrs, actual_purge_scrap_kg..."
                    : "Columns: order_id, resin, color, qty_units, press_id, actual_changeover_hrs, actual_purge_scrap_kg..."}
                </span>
              </button>
            </div>
          </div>

          {err && (
            <div className="flex items-center gap-2 rounded-xl border border-rose-500/40 bg-rose-500/15 p-3 text-xs text-rose-200">
              <AlertCircle className="h-4 w-4 shrink-0 text-rose-400" />
              <span>{err}</span>
            </div>
          )}

          {busy && !backtestReport && (
            <div className="flex flex-col items-center justify-center rounded-2xl border border-slate-800 bg-[#0f1629] p-10 text-center">
              <Loader2 className="mb-3 h-7 w-7 animate-spin text-emerald-400" />
              <p className="text-sm font-semibold text-white">
                {isAr
                  ? "جاري إعادة جدولة أوامر الشهر الماضي عبر محرك OR-Tools CP-SAT..."
                  : "Replaying 30-day historical press orders through deterministic OR-Tools CP-SAT..."}
              </p>
            </div>
          )}

          {backtestReport && d && act && opt && (
            <>
              {/* Executive Actual vs. Mini-DIOS ROI Replay Hero Card */}
              <div
                data-testid="backtest-roi-replay-card"
                className="rounded-2xl border border-emerald-500/40 bg-gradient-to-br from-emerald-500/15 via-[#0f1629] to-cyan-500/10 p-5 shadow-xl"
              >
                <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <Award className="h-5 w-5 text-emerald-400" />
                    <h3 className="text-sm font-bold text-white">
                      {isAr
                        ? `بطاقة الإثبات التنفيذية: السجل الفعلي مقابل إعادة تشغيل Mini-DIOS (${backtestReport.period_days} يوماً)`
                        : `Executive Proof Card: Actual Factory Log vs. Mini-DIOS CP-SAT Replay (${backtestReport.period_days} Days)`}
                    </h3>
                  </div>
                  <span className="rounded-lg border border-slate-700 bg-slate-900/90 px-2.5 py-1 font-mono text-[11px] text-slate-300">
                    {backtestReport.source_label} • {backtestReport.orders_analyzed}{" "}
                    {isAr ? "أمر مرجعي" : "log orders"} • {backtestReport.solve_time_ms} ms
                  </span>
                </div>

                {/* 4 Hero ROI Pillars */}
                <div className="grid gap-3.5 sm:grid-cols-2 lg:grid-cols-4">
                  <div className="rounded-xl border border-emerald-500/40 bg-slate-950/80 p-4">
                    <div className="flex items-center justify-between text-[11px] font-semibold text-emerald-300">
                      <span>{t.backtestCashLeftTitle}</span>
                      <TrendingUp className="h-4 w-4 text-emerald-400" />
                    </div>
                    <div
                      dir="ltr"
                      data-testid="backtest-cash-1m"
                      className="mt-1.5 font-mono text-2xl font-extrabold text-emerald-300"
                    >
                      {fmtMoney(d.total_cash_left_on_floor_1month)}
                    </div>
                    <div className="mt-1 text-[11px] text-slate-400">
                      {isAr ? "وفورات مباشرة:" : "Direct cost cut:"}{" "}
                      <span dir="ltr" className="font-mono text-slate-200">
                        {fmtMoney(d.direct_cost_savings_1month)}
                      </span>
                    </div>
                  </div>

                  <div className="rounded-xl border border-cyan-500/40 bg-slate-950/80 p-4">
                    <div className="flex items-center justify-between text-[11px] font-semibold text-cyan-300">
                      <span>{t.backtestAnnualizedTitle}</span>
                      <Flame className="h-4 w-4 text-cyan-400" />
                    </div>
                    <div
                      dir="ltr"
                      data-testid="backtest-cash-annual"
                      className="mt-1.5 font-mono text-2xl font-extrabold text-cyan-300"
                    >
                      {fmtMoney(d.annualized_cash_left_on_floor)}
                    </div>
                    <div className="mt-1 text-[11px] text-slate-400">
                      {isAr ? "تجنب غرامات التصدير:" : "Export penalties saved:"}{" "}
                      <span dir="ltr" className="font-mono text-emerald-300">
                        {fmtMoney(d.export_penalties_avoided)}
                      </span>
                    </div>
                  </div>

                  <div className="rounded-xl border border-amber-500/40 bg-slate-950/80 p-4">
                    <div className="flex items-center justify-between text-[11px] font-semibold text-amber-300">
                      <span>{t.backtestExtraOutputTitle}</span>
                      <PackageCheck className="h-4 w-4 text-amber-400" />
                    </div>
                    <div
                      dir="ltr"
                      data-testid="backtest-extra-tons"
                      className="mt-1.5 font-mono text-2xl font-extrabold text-amber-300"
                    >
                      +{formatNumber(d.extra_sellable_tons_unlocked, 1)} t
                    </div>
                    <div className="mt-1 text-[11px] text-slate-400" dir="ltr">
                      +{d.extra_sellable_units_unlocked.toLocaleString("en-US")} pcs •{" "}
                      {formatNumber(d.changeover_hrs_freed, 1)}h freed
                    </div>
                  </div>

                  <div className="rounded-xl border border-indigo-500/40 bg-slate-950/80 p-4">
                    <div className="flex items-center justify-between text-[11px] font-semibold text-indigo-300">
                      <span>{t.backtestPaybackTitle}</span>
                      <CalendarClock className="h-4 w-4 text-indigo-400" />
                    </div>
                    <div
                      data-testid="backtest-payback-days"
                      className="mt-1.5 font-mono text-2xl font-extrabold text-indigo-300"
                    >
                      {d.estimated_payback_days} {isAr ? "أيام فقط" : "Days"}
                    </div>
                    <div className="mt-1 text-[11px] text-slate-400">
                      {isAr
                        ? "استرداد كامل للاشتراك من وفورات أول أسبوع"
                        : "Full license payback inside Week 1"}
                    </div>
                  </div>
                </div>
              </div>

              {/* Side-by-Side Comparison Table: Actual History vs. Mini-DIOS CP-SAT Replay */}
              <div className="overflow-hidden rounded-2xl border border-slate-800 bg-[#0f1629]">
                <div className="border-b border-slate-800 px-5 py-3.5">
                  <h3 className="text-sm font-bold text-white">
                    {isAr
                      ? "مقارنة تفصيلية (تفاحة بتفاحة): الأداء التاريخي الفعلي مقابل إعادة تشغيل Mini-DIOS"
                      : "Apples-to-Apples Breakdown: Actual Factory History vs. Mini-DIOS CP-SAT Replay"}
                  </h3>
                </div>
                <div className="overflow-x-auto touch-pan-x">
                  <table className="w-full min-w-[600px] text-start text-xs">
                    <thead className="bg-slate-900/80 text-[11px] uppercase text-slate-400">
                      <tr>
                        <th className="px-4 py-3 text-start">
                          {isAr ? "مؤشر الأداء التشغيلي والمالي (30 يوماً)" : "30-Day Operational & Financial Metric"}
                        </th>
                        <th className="px-4 py-3 text-end">
                          {isAr ? "السجل الفعلي للمصنع" : "Actual Historical Log"}
                        </th>
                        <th className="px-4 py-3 text-end">
                          {isAr ? "إعادة تشغيل Mini-DIOS" : "Mini-DIOS CP-SAT Replay"}
                        </th>
                        <th className="px-4 py-3 text-end">
                          {isAr ? "المكسب المحقق / الوفر" : "Unlocked Savings / Delta"}
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/80 font-mono">
                      <tr>
                        <td className="px-4 py-3 font-sans font-semibold text-slate-200">
                          {isAr ? "هالك تنظيف الألوان والخامات (كجم)" : "Purge Resin Scrap (kg)"}
                        </td>
                        <td className="px-4 py-3 text-end text-slate-300" dir="ltr">
                          {formatNumber(act.purge_scrap_kg, 1)} kg
                        </td>
                        <td className="px-4 py-3 text-end font-bold text-cyan-300" dir="ltr">
                          {formatNumber(opt.purge_scrap_kg, 1)} kg
                        </td>
                        <td className="px-4 py-3 text-end font-bold text-emerald-400" dir="ltr">
                          -{formatNumber(d.purge_scrap_saved_kg, 1)} kg (-{d.purge_scrap_cut_pct}%)
                        </td>
                      </tr>
                      <tr>
                        <td className="px-4 py-3 font-sans font-semibold text-slate-200">
                          {isAr ? "تكلفة هالك الخامات المهدر" : "Purge Scrap Material Cost"}
                        </td>
                        <td className="px-4 py-3 text-end text-slate-300" dir="ltr">
                          {fmtMoney(act.purge_scrap_cost)}
                        </td>
                        <td className="px-4 py-3 text-end font-bold text-cyan-300" dir="ltr">
                          {fmtMoney(opt.purge_scrap_cost)}
                        </td>
                        <td className="px-4 py-3 text-end font-bold text-emerald-400" dir="ltr">
                          +{fmtMoney(d.purge_scrap_saved_cost)}
                        </td>
                      </tr>
                      <tr>
                        <td className="px-4 py-3 font-sans font-semibold text-slate-200">
                          {isAr ? "ساعات تبديل القوالب والتنظيف" : "Mold Changeover & Purge Hours"}
                        </td>
                        <td className="px-4 py-3 text-end text-slate-300" dir="ltr">
                          {formatNumber(act.changeover_hrs, 1)} hrs
                        </td>
                        <td className="px-4 py-3 text-end font-bold text-cyan-300" dir="ltr">
                          {formatNumber(opt.changeover_hrs, 1)} hrs
                        </td>
                        <td className="px-4 py-3 text-end font-bold text-emerald-400" dir="ltr">
                          {formatNumber(d.changeover_hrs_freed, 1)} hrs freed (-{d.changeover_cut_pct}%)
                        </td>
                      </tr>
                      <tr>
                        <td className="px-4 py-3 font-sans font-semibold text-slate-200">
                          {isAr ? "ساعات وتكلفة العمل الإضافي للورديات" : "Shift Overtime Hours & Cost"}
                        </td>
                        <td className="px-4 py-3 text-end text-slate-300" dir="ltr">
                          {formatNumber(act.overtime_hrs, 1)}h ({fmtMoney(act.overtime_cost)})
                        </td>
                        <td className="px-4 py-3 text-end font-bold text-cyan-300" dir="ltr">
                          {formatNumber(opt.overtime_hrs, 1)}h ({fmtMoney(opt.overtime_cost)})
                        </td>
                        <td className="px-4 py-3 text-end font-bold text-emerald-400" dir="ltr">
                          +{fmtMoney(d.overtime_cost_saved)} (-{formatNumber(d.overtime_hrs_cut, 1)}h)
                        </td>
                      </tr>
                      <tr>
                        <td className="px-4 py-3 font-sans font-semibold text-slate-200">
                          {isAr ? "ساعات التأخير وغرامات التصدير" : "Late Delivery Hours & Export Penalties"}
                        </td>
                        <td className="px-4 py-3 text-end text-rose-300" dir="ltr">
                          {formatNumber(act.late_hours, 1)}h ({fmtMoney(act.export_penalty_cost)})
                        </td>
                        <td className="px-4 py-3 text-end font-bold text-emerald-300" dir="ltr">
                          {formatNumber(opt.late_hours, 1)}h ({fmtMoney(opt.export_penalty_cost)})
                        </td>
                        <td className="px-4 py-3 text-end font-bold text-emerald-400" dir="ltr">
                          +{fmtMoney(d.export_penalties_avoided)}
                        </td>
                      </tr>
                      <tr className="bg-emerald-500/10">
                        <td className="px-4 py-3 font-sans font-bold text-white">
                          {isAr
                            ? "إجمالي النقد الشهري القابل للاسترداد (وفر مباشر + هامش إنتاج محرر)"
                            : "Total Monthly Cash Left on the Floor (Direct Savings + Unlocked Output Margin)"}
                        </td>
                        <td className="px-4 py-3 text-end text-slate-300" dir="ltr">
                          {fmtMoney(act.total_avoidable_waste_cost)}
                        </td>
                        <td className="px-4 py-3 text-end font-bold text-cyan-300" dir="ltr">
                          {fmtMoney(opt.total_avoidable_waste_cost)}
                        </td>
                        <td className="px-4 py-3 text-end text-sm font-extrabold text-emerald-300" dir="ltr">
                          +{fmtMoney(d.total_cash_left_on_floor_1month)}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Per-Press Unlocked Capacity & Scrap Reduction Breakdown */}
              <div className="rounded-2xl border border-slate-800 bg-[#0f1629] p-4">
                <h4 className="mb-3 text-xs font-bold uppercase tracking-wider text-slate-300">
                  {isAr
                    ? "توزيع الساعات المحررة ووفر الهالك حسب الماكينة (30 يوماً)"
                    : "Press-by-Press Unlocked Hours & Purge Scrap Saved (30-Day Replay)"}
                </h4>
                <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
                  {backtestReport.press_breakdown.map((pb) => (
                    <div
                      key={pb.press_id}
                      className="rounded-xl border border-slate-800 bg-slate-950/75 p-3 text-xs"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono font-bold text-cyan-300">{pb.press_id}</span>
                        <span className="rounded bg-emerald-500/15 px-2 py-0.5 font-mono text-[10px] font-bold text-emerald-300">
                          +{pb.unlocked_hrs.toFixed(1)}h freed
                        </span>
                      </div>
                      <div className="mt-2 flex items-center justify-between text-[11px] text-slate-400">
                        <span>{isAr ? "التبديل:" : "Setups:"}</span>
                        <span dir="ltr" className="font-mono text-slate-200">
                          {pb.actual_changeover_hrs.toFixed(1)}h → {pb.optimized_changeover_hrs.toFixed(1)}h
                        </span>
                      </div>
                      <div className="mt-1 flex items-center justify-between text-[11px] text-slate-400">
                        <span>{isAr ? "هالك التنظيف:" : "Purge Scrap:"}</span>
                        <span dir="ltr" className="font-mono text-emerald-300">
                          {pb.actual_purge_scrap_kg.toFixed(0)}kg → {pb.optimized_purge_scrap_kg.toFixed(0)}kg (-
                          {pb.scrap_saved_kg.toFixed(0)}kg)
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex shrink-0 items-center justify-between border-t border-slate-800 bg-slate-950/90 px-4 py-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] sm:px-6 sm:pb-3">
          <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
            <span>
              {isAr
                ? "حساب حتمي 100% من فيزياء القوالب والمكابس — صفر تقديرات تخمينية"
                : "100% Deterministic CP-SAT Replay — Zero LLM Arithmetic"}
            </span>
          </div>
          <button
            type="button"
            data-testid="btn-close-backtest-footer"
            onClick={() => setBacktestModalOpen(false)}
            className="min-h-[44px] rounded-xl bg-slate-800 px-4 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-700 md:min-h-0"
          >
            {isAr ? "إغلاق" : "Close"}
          </button>
        </div>
      </div>
    </div>
  );
}
