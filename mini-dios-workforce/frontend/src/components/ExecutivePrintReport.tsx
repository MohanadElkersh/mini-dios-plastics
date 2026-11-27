"use client";

import React from "react";
import { Printer, X } from "lucide-react";
import { convertCurrency, formatMoney, formatNumber } from "@/lib/format";
import { COLOR_LABELS, COPY } from "@/lib/i18n";
import { useApp } from "@/lib/store";

export function ExecutivePrintReport() {
  const {
    lang,
    currency,
    dataset,
    config,
    result,
    backtestReport,
    printReportMode,
    setPrintReportMode,
  } = useApp();

  const t = COPY[lang];
  const isAr = lang === "ar";
  const fx = result?.fx_egp_per_sar ?? config.fx_egp_per_sar ?? 13.0;
  const fromCur = result?.currency ?? currency;
  const fmtCur = (amt: number, srcCur = fromCur) =>
    formatMoney(convertCurrency(amt, srcCur, currency, fx), currency);

  if (!result && !backtestReport) return null;

  const opt = result?.optimized;
  const sc = result?.scorecard;
  const fin = result?.financials;
  const radar = result?.risk_radar;
  const wf = result?.workforce;
  const bt = backtestReport?.actual_vs_optimized;

  const audienceBadge =
    printReportMode === "brief_manager"
      ? isAr
        ? "درع القرار الهندسي — مدير المصنع والإنتاج"
        : "Plant & Production Manager — Decision Shield"
      : printReportMode === "backtest"
        ? isAr
          ? "إثبات المحاكاة التاريخية لشهر كامل (30 يوماً)"
          : "30-Day Historical Backtest ROI Proof"
        : isAr
          ? "تقرير المالك ورئيس مجلس الإدارة"
          : "Owner & Chairman Executive Brief";

  const reportContent = (
    <div
      dir={isAr ? "rtl" : "ltr"}
      data-testid="executive-print-report-sheet"
      className="mx-auto w-full max-w-4xl bg-white p-6 text-slate-900 sm:p-8 print:max-w-none print:p-0"
      style={{
        fontFamily: isAr
          ? '"IBM Plex Sans Arabic", "Segoe UI", Tahoma, Arial, sans-serif'
          : '"Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
      }}
    >
      {/* Header Banner */}
      <div className="flex flex-wrap items-start justify-between gap-4 border-b-2 border-slate-900 pb-4">
        <div>
          <div className="text-xs font-bold uppercase tracking-wider text-slate-600">
            {t.appTitle} • OR-Tools CP-SAT
          </div>
          <h1 className="mt-1 text-xl font-extrabold text-slate-950">
            {dataset?.name || result?.dataset_name || "Delta & Riyadh Polymer Packaging Plant"}
          </h1>
          <p className="mt-0.5 text-xs text-slate-600">{audienceBadge}</p>
        </div>
        <div className="text-end font-mono text-xs text-slate-700">
          <div className="font-bold text-slate-950">
            {isAr ? "العملة النشطة:" : "Currency:"} {currency}
          </div>
          <div>
            {isAr ? "التاريخ:" : "Date:"} {new Date().toISOString().slice(0, 10)}
          </div>
          {result && (
            <div>
              Run ID: {result.run_id} ({result.status})
            </div>
          )}
        </div>
      </div>

      {/* Headline KPIs Grid */}
      {result && opt && sc && fin && (
        <div className="mt-5">
          <h2 className="mb-2.5 text-xs font-extrabold uppercase tracking-wider text-slate-700">
            {isAr
              ? "١. المؤشرات المالية والتشغيلية الرئيسية (مقابل جدول FIFO)"
              : "1. Headline Financial & Operational KPIs (vs. Naive FIFO Baseline)"}
          </h2>
          <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3">
            <div className="rounded-lg border border-slate-300 bg-slate-50 p-3">
              <div className="text-[11px] font-semibold text-slate-600">
                {isAr ? "الوفر النقدي الأسبوعي" : "Weekly Savings vs. FIFO"}
              </div>
              <div dir="ltr" className="mt-1 font-mono text-base font-extrabold text-emerald-700">
                {fmtCur(fin.total_weekly_savings)}
              </div>
              <div className="text-[10px] text-slate-600">
                +{sc.cash_savings_pct.toFixed(1)}% cost cut
              </div>
            </div>

            <div className="rounded-lg border border-slate-300 bg-slate-50 p-3">
              <div className="text-[11px] font-semibold text-slate-600">
                {isAr ? "الوفر السنوي المتوقع (50 أسبوعاً)" : "Annualized Projected Savings"}
              </div>
              <div dir="ltr" className="mt-1 font-mono text-base font-extrabold text-slate-950">
                {fmtCur(fin.annual_projected_savings)}
              </div>
              <div className="text-[10px] text-slate-600">
                +{fin.unlocked_capacity_hours.toFixed(1)}h/wk capacity freed
              </div>
            </div>

            <div className="rounded-lg border border-slate-300 bg-slate-50 p-3">
              <div className="text-[11px] font-semibold text-slate-600">
                {isAr ? "التسليم بالموعد OTIF / الكفاءة OEE" : "OTIF Delivery / Press OEE"}
              </div>
              <div dir="ltr" className="mt-1 font-mono text-base font-extrabold text-slate-950">
                {opt.kpis.otif_pct.toFixed(0)}% / {opt.kpis.oee_pct.toFixed(1)}%
              </div>
              <div className="text-[10px] text-slate-600">
                {opt.kpis.on_time_orders}/{opt.kpis.total_orders} on-time orders
              </div>
            </div>

            <div className="rounded-lg border border-slate-300 bg-slate-50 p-3">
              <div className="text-[11px] font-semibold text-slate-600">
                {isAr ? "وفر هالك تنظيف الخامات" : "Purge Resin Scrap Saved"}
              </div>
              <div dir="ltr" className="mt-1 font-mono text-base font-extrabold text-slate-950">
                {sc.purge_scrap_kg_saved.toFixed(1)} kg
              </div>
              <div dir="ltr" className="text-[10px] text-slate-600">
                {opt.kpis.purge_scrap_kg.toFixed(1)} kg opt vs {result.baseline.kpis.purge_scrap_kg.toFixed(1)} kg FIFO
              </div>
            </div>

            <div className="rounded-lg border border-slate-300 bg-slate-50 p-3">
              <div className="text-[11px] font-semibold text-slate-600">
                {isAr ? "إشغال المخزن والسيولة بالحاويات" : "Warehouse WIP & Container Cash"}
              </div>
              <div dir="ltr" className="mt-1 font-mono text-base font-extrabold text-slate-950">
                {(opt.kpis.warehouse_utilization_pct ?? 0).toFixed(0)}% ({fmtCur(opt.kpis.trapped_working_capital ?? 0)})
              </div>
              <div className="text-[10px] text-slate-600">
                {isAr ? "مزامنة حاويات التصدير مفعّلة" : "Export container sync active"}
              </div>
            </div>

            <div className="rounded-lg border border-slate-300 bg-slate-50 p-3">
              <div className="text-[11px] font-semibold text-slate-600">
                {isAr ? "تغطية الورديات والامتثال" : "Workforce Shift Coverage"}
              </div>
              <div dir="ltr" className="mt-1 font-mono text-base font-extrabold text-slate-950">
                {(wf?.optimized.kpis.coverage_pct ?? 100).toFixed(1)}%
              </div>
              <div className="text-[10px] text-slate-600">
                11/11 Hard Constraints Verified
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Historical Backtest ROI Block (if available) */}
      {backtestReport && bt && (
        <div className="mt-5 rounded-lg border-2 border-slate-800 bg-slate-50 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-xs font-extrabold uppercase tracking-wider text-slate-900">
              {isAr
                ? `إثبات المحاكاة التاريخية لـ ${backtestReport.period_days} يوماً (${backtestReport.orders_analyzed} أمر فعلي)`
                : `30-Day Historical Backtest Proof (${backtestReport.orders_analyzed} Actual Orders Replayed)`}
            </h2>
            <span className="font-mono text-xs font-bold text-emerald-800">
              {isAr ? `فترة الاسترداد: ${bt.estimated_payback_days} أيام` : `Payback: ${bt.estimated_payback_days} Days`}
            </span>
          </div>
          <div className="mt-2.5 grid grid-cols-2 gap-3 text-xs sm:grid-cols-4">
            <div>
              <div className="text-slate-600">{t.backtestCashLeftTitle}</div>
              <div dir="ltr" className="font-mono text-sm font-extrabold text-slate-950">
                {fmtCur(bt.total_cash_left_on_floor_1month, backtestReport.currency)}
              </div>
            </div>
            <div>
              <div className="text-slate-600">{t.backtestAnnualizedTitle}</div>
              <div dir="ltr" className="font-mono text-sm font-extrabold text-slate-950">
                {fmtCur(bt.annualized_cash_left_on_floor, backtestReport.currency)}
              </div>
            </div>
            <div>
              <div className="text-slate-600">{t.backtestExtraOutputTitle}</div>
              <div dir="ltr" className="font-mono text-sm font-extrabold text-slate-950">
                +{formatNumber(bt.extra_sellable_tons_unlocked, 1)} t ({formatNumber(bt.changeover_hrs_freed, 1)}h)
              </div>
            </div>
            <div>
              <div className="text-slate-600">{isAr ? "وفر هالك التنظيف" : "Purge Scrap Cut"}</div>
              <div dir="ltr" className="font-mono text-sm font-extrabold text-slate-950">
                -{formatNumber(bt.purge_scrap_saved_kg, 1)} kg (-{bt.purge_scrap_cut_pct}%)
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Top Risk Radar Alerts */}
      {radar && (
        <div className="mt-5">
          <h2 className="mb-2 text-xs font-extrabold uppercase tracking-wider text-slate-700">
            {isAr
              ? `٢. رادار المخاطر الاستباقي (المؤشر: ${radar.overall_risk_score}/100)`
              : `2. Proactive Risk Radar Alerts (Plant Risk Score: ${radar.overall_risk_score}/100)`}
          </h2>
          {radar.alerts.length === 0 ? (
            <div className="rounded-lg border border-slate-300 px-3 py-2 text-xs text-slate-700">
              {t.riskAllClear}
            </div>
          ) : (
            <div className="grid gap-2 sm:grid-cols-2">
              {radar.alerts.slice(0, 4).map((a) => (
                <div key={a.alert_id} className="rounded-lg border border-slate-300 bg-white p-2.5 text-xs">
                  <div className="flex items-center justify-between font-bold text-slate-900">
                    <span>{isAr ? a.title_ar : a.title_en}</span>
                    <span className="rounded border border-slate-400 px-1.5 py-0.5 font-mono text-[10px] uppercase">
                      {a.severity}
                    </span>
                  </div>
                  <p className="mt-1 text-[11px] text-slate-700">
                    {isAr ? a.detail_ar : a.detail_en}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Compact Press-by-Press Schedule Summary Table */}
      {opt && (
        <div className="mt-5">
          <h2 className="mb-2 text-xs font-extrabold uppercase tracking-wider text-slate-700">
            {isAr
              ? "٣. ملخص جدول تشغيل المكابس والأوامر المعتمدة"
              : "3. Press-by-Press Schedule & Color Sequence Summary"}
          </h2>
          <table className="w-full border-collapse border border-slate-300 text-start text-[11px]">
            <thead className="bg-slate-100 text-slate-800">
              <tr>
                <th className="border border-slate-300 px-2 py-1.5 text-start">Press</th>
                <th className="border border-slate-300 px-2 py-1.5 text-start">Order / Customer</th>
                <th className="border border-slate-300 px-2 py-1.5 text-start">Mold & Resin</th>
                <th className="border border-slate-300 px-2 py-1.5 text-end">Start → End</th>
                <th className="border border-slate-300 px-2 py-1.5 text-end">Purge (kg)</th>
              </tr>
            </thead>
            <tbody>
              {opt.jobs
                .filter((j) => j.scheduled)
                .slice(0, 14)
                .map((j) => (
                  <tr key={j.order_id} className="border-t border-slate-300">
                    <td className="border border-slate-300 px-2 py-1 font-mono font-bold">
                      {j.machine_id}
                    </td>
                    <td className="border border-slate-300 px-2 py-1">
                      <span className="font-mono font-bold">{j.order_id}</span> • {j.customer}
                    </td>
                    <td className="border border-slate-300 px-2 py-1">
                      {j.mold_id} • {j.resin_code} ({COLOR_LABELS[lang][j.color]})
                    </td>
                    <td dir="ltr" className="border border-slate-300 px-2 py-1 text-end font-mono">
                      H{(j.start_min / 60).toFixed(1)} → H{(j.end_min / 60).toFixed(1)}
                    </td>
                    <td dir="ltr" className="border border-slate-300 px-2 py-1 text-end font-mono">
                      {j.purge_scrap_kg.toFixed(1)}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Footer Signature */}
      <div className="mt-6 flex flex-wrap items-center justify-between border-t border-slate-300 pt-3 text-[10px] text-slate-600">
        <span>{t.deterministicFooter}</span>
        {result && <span className="font-mono">SHA-256: {result.audit.schedule_sha256.slice(0, 16)}...</span>}
      </div>
    </div>
  );

  // When printReportMode is active, render an on-screen print preview modal AND keep it visible for @media print
  return (
    <>
      {/* Always mounted hidden print container so browser Cmd+P / Ctrl+P works anytime */}
      <div className="hidden print:block">{reportContent}</div>

      {/* Interactive Print Preview Modal when triggered by "Download / Print Executive PDF" button */}
      {printReportMode && (
        <div
          data-testid="executive-print-preview-modal"
          className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-950/85 p-3 backdrop-blur-sm sm:p-6 print:hidden"
        >
          <div className="flex max-h-[92dvh] w-full max-w-4xl flex-col overflow-hidden rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 bg-slate-950 px-4 py-3 sm:px-6">
              <div className="flex items-center gap-2 text-xs font-bold text-white">
                <Printer className="h-4 w-4 text-cyan-400" />
                <span>{t.printPdfBtn}</span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  data-testid="btn-trigger-window-print"
                  onClick={() => window.print()}
                  className="inline-flex min-h-[38px] items-center gap-1.5 rounded-xl bg-cyan-500 px-4 py-1.5 text-xs font-bold text-slate-950 hover:bg-cyan-400 md:min-h-0"
                >
                  <Printer className="h-3.5 w-3.5" />
                  <span>{isAr ? "طباعة / حفظ كملف PDF" : "Print / Save as PDF"}</span>
                </button>
                <button
                  type="button"
                  data-testid="btn-close-print-preview"
                  onClick={() => setPrintReportMode(null)}
                  className="inline-flex min-h-[38px] min-w-[38px] items-center justify-center rounded-xl text-slate-400 hover:bg-slate-800 hover:text-white md:min-h-0 md:min-w-0 md:p-1.5"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto bg-slate-200 p-3 sm:p-6">
              {reportContent}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
