"use client";

import React, { useEffect, useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  Calculator,
  CheckCircle2,
  Clock,
  DollarSign,
  Factory,
  Loader2,
  PackagePlus,
  Sparkles,
  X,
  XCircle,
  Zap,
} from "lucide-react";
import { quoteCtpRushOrderApi } from "@/lib/api";
import { convertCurrency, formatMoney } from "@/lib/format";
import { COLOR_LABELS, COPY } from "@/lib/i18n";
import { useApp } from "@/lib/store";
import type { CTPQuoteResult, PlasticColor, ResinCode } from "@/lib/types";

const PLASTIC_COLORS: PlasticColor[] = ["Natural", "White", "Yellow", "Blue", "Red", "Black"];
const RESIN_CODES: ResinCode[] = ["PP", "HDPE", "LDPE", "PET", "ABS", "PVC"];

export function CTPQuoterModal() {
  const {
    lang,
    currency,
    dataset,
    config,
    result,
    ctpModalOpen,
    setCtpModalOpen,
    commitCtpOrderToSchedule,
  } = useApp();

  const t = COPY[lang];
  const isAr = lang === "ar";
  const fx = config.fx_egp_per_sar ?? 13.0;

  const [customer, setCustomer] = useState("Al-Marai / Gulf Retail Export");
  const [skuName, setSkuName] = useState("28mm Tamper-Evident Dairy Cap (Rush)");
  const [moldId, setMoldId] = useState("M-01");
  const [resin, setResin] = useState<ResinCode>("HDPE");
  const [color, setColor] = useState<PlasticColor>("White");
  const [qtyUnits, setQtyUnits] = useState(40000);
  const [targetDueHour, setTargetDueHour] = useState(108);
  const [unitPriceDisplay, setUnitPriceDisplay] = useState("0.08");
  const [isExport, setIsExport] = useState(true);
  const [maxRegrindPct, setMaxRegrindPct] = useState(0);
  const [allowPeakOrOvertime, setAllowPeakOrOvertime] = useState(true);

  const [quoting, setQuoting] = useState(false);
  const [committing, setCommitting] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [quote, setQuote] = useState<CTPQuoteResult | null>(null);

  // Sync default unit price when currency changes
  useEffect(() => {
    const defaultSarPrice = 0.08;
    const priceInCur = currency === "EGP" ? +(defaultSarPrice * fx).toFixed(2) : defaultSarPrice;
    setUnitPriceDisplay(String(priceInCur));
  }, [currency, fx]);

  const runQuote = async (overrideParams?: {
    customer?: string;
    sku_name?: string;
    mold_id?: string;
    resin?: ResinCode;
    color?: PlasticColor;
    qty_units?: number;
    target_due_hour?: number;
    unit_price?: number;
    is_export?: boolean;
  }) => {
    setQuoting(true);
    setErr(null);
    try {
      const parsedPrice = Number(unitPriceDisplay);
      const q = await quoteCtpRushOrderApi({
        customer: overrideParams?.customer ?? customer,
        sku_name: overrideParams?.sku_name ?? skuName,
        mold_id: overrideParams?.mold_id ?? moldId,
        resin: overrideParams?.resin ?? resin,
        color: overrideParams?.color ?? color,
        qty_units: overrideParams?.qty_units ?? qtyUnits,
        target_due_hour: overrideParams?.target_due_hour ?? targetDueHour,
        unit_price:
          overrideParams?.unit_price ?? (Number.isFinite(parsedPrice) && parsedPrice > 0 ? parsedPrice : undefined),
        is_export: overrideParams?.is_export ?? isExport,
        max_regrind_pct: (overrideParams?.is_export ?? isExport) ? 0 : maxRegrindPct,
        allow_peak_or_overtime: allowPeakOrOvertime,
        currency,
        dataset,
        config,
        current_result: result,
      });
      setQuote(q);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "CTP Rush-Order quote evaluation failed");
    } finally {
      setQuoting(false);
    }
  };

  const handleLoadSampleRushOrder = () => {
    const samplePrice = currency === "EGP" ? +(0.08 * fx).toFixed(2) : 0.08;
    const firstMold = dataset?.molds?.[0]?.mold_id || "M-01";
    setCustomer("Al-Marai / Gulf Retail Export");
    setSkuName("28mm Tamper-Evident Dairy Cap (40k Rush)");
    setMoldId(firstMold);
    setResin("HDPE");
    setColor("White");
    setQtyUnits(40000);
    setTargetDueHour(108);
    setUnitPriceDisplay(String(samplePrice));
    setIsExport(true);
    setMaxRegrindPct(0);
    setAllowPeakOrOvertime(true);
    void runQuote({
      customer: "Al-Marai / Gulf Retail Export",
      sku_name: "28mm Tamper-Evident Dairy Cap (40k Rush)",
      mold_id: firstMold,
      resin: "HDPE",
      color: "White",
      qty_units: 40000,
      target_due_hour: 108,
      unit_price: samplePrice,
      is_export: true,
    });
  };

  useEffect(() => {
    if (!ctpModalOpen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setCtpModalOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [ctpModalOpen, setCtpModalOpen]);

  if (!ctpModalOpen) return null;

  const fmtCur = (amt: number, fromCur = quote?.financial_impact.currency ?? currency) =>
    formatMoney(convertCurrency(amt, fromCur, currency, fx), currency);

  const fmtUnitPrice = (amt: number, fromCur = quote?.financial_impact.currency ?? currency) => {
    const conv = convertCurrency(amt, fromCur, currency, fx);
    return `${currency} ${conv.toFixed(3)}`;
  };

  const handleCommit = async () => {
    if (!quote) return;
    setCommitting(true);
    setErr(null);
    try {
      await commitCtpOrderToSchedule(quote.candidate_order);
      setCtpModalOpen(false);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Failed to commit rush order to live schedule");
    } finally {
      setCommitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center p-0 sm:items-center sm:p-4">
      <div
        className="fixed inset-0 bg-slate-950/85 backdrop-blur-sm"
        onClick={() => setCtpModalOpen(false)}
      />

      <div
        data-testid="ctp-quoter-modal"
        className="relative z-10 flex max-h-[92dvh] w-full max-w-4xl flex-col overflow-hidden rounded-t-3xl border border-slate-700/80 bg-[#0b1120] shadow-2xl sm:rounded-2xl"
        role="dialog"
        aria-modal="true"
      >
        {/* Header */}
        <div className="flex shrink-0 items-center justify-between border-b border-slate-800 bg-slate-950/90 px-4 py-3.5 sm:px-6 sm:py-4">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-amber-500/40 bg-gradient-to-br from-amber-500/20 to-cyan-500/20 text-amber-300">
              <Calculator className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="truncate text-sm font-bold text-white sm:text-lg">
                  {t.ctpTitle}
                </h2>
                <span className="rounded-full border border-emerald-500/40 bg-emerald-500/15 px-2.5 py-0.5 text-[10px] font-bold uppercase text-emerald-300">
                  {isAr ? "محاكاة غير مدمرة للجدول" : "Non-Destructive Sandbox"}
                </span>
              </div>
              <p className="truncate text-[11px] text-slate-400 sm:text-xs">
                {t.ctpSubtitle}
              </p>
            </div>
          </div>

          <button
            type="button"
            data-testid="btn-close-ctp-modal"
            onClick={() => setCtpModalOpen(false)}
            className="inline-flex min-h-[44px] min-w-[44px] shrink-0 items-center justify-center rounded-xl text-slate-400 hover:bg-slate-800 hover:text-white md:min-h-0 md:min-w-0 md:p-1.5"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 space-y-5 overflow-y-auto p-4 sm:p-6">
          {/* Rush Order Input Form */}
          <div className="rounded-2xl border border-slate-800 bg-[#0f1629] p-4">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2 text-xs font-bold text-slate-200">
                <PackagePlus className="h-4 w-4 text-cyan-400" />
                <span>
                  {isAr ? "مواصفات الأمر العاجل المطلوب تسعيره:" : "Prospective Rush Order Parameters:"}
                </span>
              </div>

              <button
                type="button"
                data-testid="btn-ctp-load-sample"
                disabled={quoting}
                onClick={handleLoadSampleRushOrder}
                className="inline-flex min-h-[38px] items-center gap-1.5 rounded-xl border border-amber-500/40 bg-amber-500/15 px-3 py-1.5 text-xs font-bold text-amber-200 transition hover:bg-amber-500/25 disabled:opacity-50 md:min-h-0"
              >
                <Sparkles className="h-3.5 w-3.5 text-amber-400" />
                <span>{t.ctpLoadSampleBtn}</span>
              </button>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <label className="mb-1 block text-[11px] text-slate-400">
                  {isAr ? "اسم العميل" : "Customer"}
                </label>
                <input
                  type="text"
                  data-testid="input-ctp-customer"
                  value={customer}
                  onChange={(e) => setCustomer(e.target.value)}
                  className="min-h-[44px] w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-base text-white focus:border-cyan-500 focus:outline-none md:min-h-0 md:text-xs"
                />
              </div>

              <div>
                <label className="mb-1 block text-[11px] text-slate-400">
                  {isAr ? "الصنف / المنتج" : "SKU Name"}
                </label>
                <input
                  type="text"
                  data-testid="input-ctp-sku"
                  value={skuName}
                  onChange={(e) => setSkuName(e.target.value)}
                  className="min-h-[44px] w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-base text-white focus:border-cyan-500 focus:outline-none md:min-h-0 md:text-xs"
                />
              </div>

              <div>
                <label className="mb-1 block text-[11px] text-slate-400">
                  {isAr ? "القالب (يرث التوافق وزمن الدورة)" : "Plant Mold (Inherits Cycle & Tonnage)"}
                </label>
                <select
                  data-testid="select-ctp-mold"
                  value={moldId}
                  onChange={(e) => setMoldId(e.target.value)}
                  className="min-h-[44px] w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-base text-white focus:border-cyan-500 focus:outline-none md:min-h-0 md:text-xs"
                >
                  {(dataset?.molds ?? []).map((m) => (
                    <option key={m.mold_id} value={m.mold_id}>
                      {m.mold_id} — {m.name} ({m.cavities} cav)
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-1 block text-[11px] text-slate-400">
                  {isAr ? "الكمية المطلوبة (قطعة)" : "Quantity (pcs)"}
                </label>
                <input
                  type="number"
                  min={500}
                  step={5000}
                  data-testid="input-ctp-qty"
                  value={qtyUnits}
                  onChange={(e) => setQtyUnits(Math.max(500, Number(e.target.value)))}
                  className="min-h-[44px] w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-base text-white focus:border-cyan-500 focus:outline-none md:min-h-0 md:text-xs"
                />
              </div>

              <div>
                <label className="mb-1 block text-[11px] text-slate-400">
                  {isAr ? "درجة الخامة" : "Resin Grade"}
                </label>
                <select
                  data-testid="select-ctp-resin"
                  value={resin}
                  onChange={(e) => setResin(e.target.value as ResinCode)}
                  className="min-h-[44px] w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-base text-white focus:border-cyan-500 focus:outline-none md:min-h-0 md:text-xs"
                >
                  {RESIN_CODES.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-1 block text-[11px] text-slate-400">
                  {isAr ? "لون البلاستيك" : "Plastic Color"}
                </label>
                <select
                  data-testid="select-ctp-color"
                  value={color}
                  onChange={(e) => setColor(e.target.value as PlasticColor)}
                  className="min-h-[44px] w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-base text-white focus:border-cyan-500 focus:outline-none md:min-h-0 md:text-xs"
                >
                  {PLASTIC_COLORS.map((c) => (
                    <option key={c} value={c}>
                      {COLOR_LABELS[lang][c]}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-1 block text-[11px] text-slate-400">
                  {isAr ? "ساعة التسليم المطلوبة (H12–H168)" : "Target Due Hour (H12–H168)"}
                </label>
                <input
                  type="number"
                  min={12}
                  max={240}
                  data-testid="input-ctp-due-hr"
                  value={targetDueHour}
                  onChange={(e) => setTargetDueHour(Math.max(12, Number(e.target.value)))}
                  className="min-h-[44px] w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-base text-white focus:border-cyan-500 focus:outline-none md:min-h-0 md:text-xs"
                />
              </div>

              <div>
                <label className="mb-1 block text-[11px] text-slate-400">
                  {isAr ? `سعر بيع القطعة المقترح (${currency})` : `Proposed Unit Price (${currency}/pc)`}
                </label>
                <input
                  type="number"
                  step="0.005"
                  min={0.001}
                  data-testid="input-ctp-unit-price"
                  value={unitPriceDisplay}
                  onChange={(e) => setUnitPriceDisplay(e.target.value)}
                  className="min-h-[44px] w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-base text-white focus:border-cyan-500 focus:outline-none md:min-h-0 md:text-xs"
                />
              </div>
            </div>

            <div className="mt-3 flex flex-wrap items-center justify-between gap-3 border-t border-slate-800/80 pt-3">
              <div className="flex flex-wrap items-center gap-4 text-xs text-slate-300">
                <label className="inline-flex cursor-pointer items-center gap-2">
                  <input
                    type="checkbox"
                    checked={isExport}
                    onChange={(e) => setIsExport(e.target.checked)}
                    className="accent-cyan-400"
                  />
                  <span>{isAr ? "أولوية تصدير (0% ريجريند)" : "Export Priority (0% Regrind)"}</span>
                </label>

                <label className="inline-flex cursor-pointer items-center gap-2">
                  <input
                    type="checkbox"
                    checked={allowPeakOrOvertime}
                    onChange={(e) => setAllowPeakOrOvertime(e.target.checked)}
                    className="accent-cyan-400"
                  />
                  <span>
                    {isAr ? "السماح بالعمل خلال الذروة / وقت إضافي" : "Allow Peak Tariff / Overtime if Needed"}
                  </span>
                </label>
              </div>

              <button
                type="button"
                data-testid="btn-ctp-run-quote"
                disabled={quoting}
                onClick={() => void runQuote()}
                className="inline-flex min-h-[44px] items-center gap-2 rounded-xl bg-cyan-500 px-5 py-2 text-xs font-bold text-slate-950 shadow-lg shadow-cyan-500/20 transition hover:bg-cyan-400 disabled:opacity-50 md:min-h-0"
              >
                {quoting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Zap className="h-4 w-4" />}
                <span>{quoting ? t.ctpQuoting : t.ctpRunQuoteBtn}</span>
              </button>
            </div>
          </div>

          {err && (
            <div className="flex items-center gap-2 rounded-xl border border-rose-500/40 bg-rose-500/15 p-3 text-xs text-rose-200">
              <AlertTriangle className="h-4 w-4 shrink-0 text-rose-400" />
              <span>{err}</span>
            </div>
          )}

          {/* Deterministic CTP Quote Result Display */}
          {quote && (
            <div data-testid="ctp-quote-result-card" className="space-y-4">
              {/* 1. Color-Coded Verdict Banner */}
              <div
                data-testid="ctp-verdict-banner"
                className={`rounded-2xl border p-4 ${
                  quote.verdict === "ON_TIME"
                    ? "border-emerald-500/45 bg-gradient-to-r from-emerald-500/15 via-slate-900 to-cyan-500/10"
                    : quote.verdict === "LATE"
                      ? "border-amber-500/45 bg-gradient-to-r from-amber-500/15 via-slate-900 to-rose-500/10"
                      : "border-rose-500/50 bg-gradient-to-r from-rose-500/20 via-slate-900 to-slate-950"
                }`}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    {quote.verdict === "ON_TIME" ? (
                      <CheckCircle2 className="h-6 w-6 text-emerald-400" />
                    ) : quote.verdict === "LATE" ? (
                      <AlertTriangle className="h-6 w-6 text-amber-400" />
                    ) : (
                      <XCircle className="h-6 w-6 text-rose-400" />
                    )}
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span
                          data-testid="ctp-verdict-badge"
                          className={`rounded-lg px-2.5 py-0.5 font-mono text-xs font-extrabold ${
                            quote.verdict === "ON_TIME"
                              ? "bg-emerald-400 text-slate-950"
                              : quote.verdict === "LATE"
                                ? "bg-amber-400 text-slate-950"
                                : "bg-rose-500 text-white"
                          }`}
                        >
                          {quote.verdict === "ON_TIME"
                            ? t.ctpVerdictOnTime
                            : quote.verdict === "LATE"
                              ? t.ctpVerdictLate
                              : t.ctpVerdictInfeasible}
                        </span>
                        {quote.assigned_press_id && (
                          <span className="inline-flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-950/80 px-2.5 py-0.5 font-mono text-xs font-bold text-cyan-300">
                            <Factory className="h-3.5 w-3.5" />
                            <span>
                              {quote.assigned_press_id} ({quote.assigned_press_name})
                            </span>
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {quote.scheduled_end_hr !== null && quote.scheduled_end_hr !== undefined && (
                    <div className="flex flex-wrap items-center gap-2 font-mono text-xs">
                      <span
                        dir="ltr"
                        className="rounded-lg border border-slate-700 bg-slate-950/80 px-2.5 py-1 text-slate-200"
                      >
                        Run: H{quote.scheduled_start_hr?.toFixed(1)} → H{quote.scheduled_end_hr.toFixed(1)} (
                        {quote.est_run_hrs.toFixed(1)}h)
                      </span>
                      <span
                        dir="ltr"
                        className={`rounded-lg border px-2.5 py-1 font-bold ${
                          quote.slack_or_delay_hrs >= 0
                            ? "border-emerald-500/40 bg-emerald-500/15 text-emerald-300"
                            : "border-rose-500/40 bg-rose-500/15 text-rose-300"
                        }`}
                      >
                        {quote.slack_or_delay_hrs >= 0
                          ? `+${quote.slack_or_delay_hrs.toFixed(1)}h early vs H${quote.target_due_hour.toFixed(0)}`
                          : `${quote.slack_or_delay_hrs.toFixed(1)}h late vs H${quote.target_due_hour.toFixed(0)}`}
                      </span>
                    </div>
                  )}
                </div>

                {/* Commander-Grade Trade-Off Summary */}
                <p className="mt-3 rounded-xl border border-slate-800/90 bg-slate-950/75 px-3.5 py-2.5 text-xs leading-relaxed text-slate-200">
                  {isAr ? quote.tradeoff_summary_ar : quote.tradeoff_summary_en}
                </p>
              </div>

              {/* 2. Marginal Cost & Break-Even Unit Price Card + Bumped Orders Grid */}
              <div className="grid gap-4 lg:grid-cols-12">
                {/* Marginal Cost & Break-Even Price Card */}
                <div className="rounded-2xl border border-slate-800 bg-[#0f1629] p-4 lg:col-span-7">
                  <div className="mb-3 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <DollarSign className="h-4 w-4 text-emerald-400" />
                      <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                        {t.ctpMarginalCostTitle}
                      </h3>
                    </div>
                    <span className="font-mono text-[11px] text-slate-400">
                      {quote.gross_weight_kg.toFixed(1)} kg {quote.resin_code}
                    </span>
                  </div>

                  {/* Break-Even Hero Callout */}
                  <div className="mb-3 grid grid-cols-2 gap-2.5 sm:grid-cols-3">
                    <div className="rounded-xl border border-cyan-500/35 bg-cyan-500/10 p-3">
                      <div className="text-[10px] font-semibold text-cyan-200">
                        {t.ctpBreakevenPriceLabel}
                      </div>
                      <div
                        dir="ltr"
                        data-testid="ctp-breakeven-price"
                        className="mt-1 font-mono text-base font-extrabold text-cyan-300"
                      >
                        {fmtUnitPrice(quote.financial_impact.min_breakeven_unit_price)}/pc
                      </div>
                      <div dir="ltr" className="text-[10px] font-mono text-slate-400">
                        Offered: {fmtUnitPrice(quote.financial_impact.offered_unit_price)}/pc
                      </div>
                    </div>

                    <div className="rounded-xl border border-amber-500/35 bg-amber-500/10 p-3">
                      <div className="text-[10px] font-semibold text-amber-200">
                        {isAr ? "إجمالي التكلفة الحدية" : "Total Marginal Cost"}
                      </div>
                      <div
                        dir="ltr"
                        data-testid="ctp-total-marginal-cost"
                        className="mt-1 font-mono text-base font-extrabold text-amber-300"
                      >
                        {fmtCur(quote.financial_impact.total_marginal_cost)}
                      </div>
                      <div dir="ltr" className="text-[10px] font-mono text-slate-400">
                        Rev: {fmtCur(quote.financial_impact.gross_revenue)}
                      </div>
                    </div>

                    <div
                      className={`col-span-2 rounded-xl border p-3 sm:col-span-1 ${
                        quote.financial_impact.net_profit_contribution >= 0
                          ? "border-emerald-500/40 bg-emerald-500/10"
                          : "border-rose-500/40 bg-rose-500/10"
                      }`}
                    >
                      <div className="text-[10px] font-semibold text-slate-200">
                        {isAr ? "صافي المساهمة الربحية" : "Net Profit Contribution"}
                      </div>
                      <div
                        dir="ltr"
                        data-testid="ctp-net-profit"
                        className={`mt-1 font-mono text-base font-extrabold ${
                          quote.financial_impact.net_profit_contribution >= 0
                            ? "text-emerald-300"
                            : "text-rose-300"
                        }`}
                      >
                        {fmtCur(quote.financial_impact.net_profit_contribution)}
                      </div>
                      <div dir="ltr" className="text-[10px] font-mono text-slate-400">
                        Margin: {quote.financial_impact.margin_pct.toFixed(1)}%
                      </div>
                    </div>
                  </div>

                  {/* Itemized Marginal Cost Lines */}
                  <div className="space-y-1.5 rounded-xl border border-slate-800/80 bg-slate-950/60 p-3 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-300">
                        {isAr ? "١. تكلفة الخامة المباشرة للأمر" : "1. Direct Resin Material Cost"}
                      </span>
                      <span dir="ltr" className="font-mono font-semibold text-slate-200">
                        {fmtCur(quote.financial_impact.direct_resin_cost)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-slate-300">
                        {isAr
                          ? `٢. هالك تنظيف الألوان الإضافي (+${quote.financial_impact.extra_purge_scrap_kg.toFixed(1)} كجم)`
                          : `2. Extra Color/Resin Purge Scrap (+${quote.financial_impact.extra_purge_scrap_kg.toFixed(1)} kg)`}
                      </span>
                      <span dir="ltr" className="font-mono font-semibold text-amber-300">
                        {fmtCur(quote.financial_impact.extra_purge_cost)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-slate-300">
                        {isAr
                          ? `٣. تكلفة تبديل القالب الإضافية (+${quote.financial_impact.extra_changeover_hrs.toFixed(1)} س)`
                          : `3. Extra Mold Changeover Cost (+${quote.financial_impact.extra_changeover_hrs.toFixed(1)} hrs)`}
                      </span>
                      <span dir="ltr" className="font-mono font-semibold text-slate-200">
                        {fmtCur(quote.financial_impact.extra_changeover_cost)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-slate-300">
                        {isAr ? "٤. الكهرباء وتشغيل المكبس الإضافي" : "4. Extra Electricity & Press Operating"}
                      </span>
                      <span dir="ltr" className="font-mono font-semibold text-slate-200">
                        {fmtCur(quote.financial_impact.extra_electricity_cost)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-slate-300">
                        {isAr ? "٥. عمالة الورديات والوقت الإضافي" : "5. Extra Shift Overtime & Floor Labor"}
                      </span>
                      <span dir="ltr" className="font-mono font-semibold text-slate-200">
                        {fmtCur(quote.financial_impact.extra_overtime_labor_cost)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-slate-300">
                        {isAr ? "٦. تكلفة تخزين WIP وتأخير الأوامر" : "6. Extra WIP Holding & Late Penalty Impact"}
                      </span>
                      <span dir="ltr" className="font-mono font-semibold text-slate-200">
                        {fmtCur(
                          quote.financial_impact.extra_wip_holding_cost +
                            quote.financial_impact.extra_late_penalty_cost
                        )}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Bumped / Impacted Confirmed Orders List */}
                <div className="flex flex-col justify-between rounded-2xl border border-slate-800 bg-[#0f1629] p-4 lg:col-span-5">
                  <div>
                    <div className="mb-3 flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Clock className="h-4 w-4 text-amber-400" />
                        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                          {t.ctpBumpedOrdersTitle}
                        </h3>
                      </div>
                      <span className="rounded-full border border-slate-700 bg-slate-900 px-2 py-0.5 font-mono text-[10px] font-bold text-slate-300">
                        {quote.bumped_orders.length} {isAr ? "متأثر" : "impacted"}
                      </span>
                    </div>

                    {quote.bumped_orders.length === 0 ? (
                      <div className="flex items-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3.5 text-xs text-emerald-200">
                        <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
                        <span>{t.ctpNoBumpedOrders}</span>
                      </div>
                    ) : (
                      <div className="max-h-[210px] space-y-2 overflow-y-auto pe-1">
                        {quote.bumped_orders.map((bo) => (
                          <div
                            key={bo.order_id}
                            data-testid={`ctp-bumped-order-${bo.order_id}`}
                            className={`rounded-xl border p-2.5 text-xs ${
                              bo.breaches_cutoff
                                ? "border-rose-500/50 bg-rose-500/10 text-rose-100"
                                : "border-slate-800 bg-slate-950/75 text-slate-200"
                            }`}
                          >
                            <div className="flex flex-wrap items-center justify-between gap-1">
                              <div className="flex items-center gap-1.5">
                                <span className="font-mono font-bold text-white">{bo.order_id}</span>
                                {bo.is_export && (
                                  <span className="rounded bg-cyan-500/20 px-1.5 py-0.5 text-[10px] font-bold text-cyan-300">
                                    EXPORT
                                  </span>
                                )}
                                {bo.breaches_cutoff && (
                                  <span className="rounded bg-rose-500 px-1.5 py-0.5 text-[10px] font-bold text-white">
                                    {isAr ? "يتجاوز الموعد!" : "BREACHES CUT-OFF"}
                                  </span>
                                )}
                              </div>
                              <span dir="ltr" className="font-mono text-[11px] font-bold text-amber-300">
                                +{bo.delay_hrs.toFixed(1)}h delay
                              </span>
                            </div>
                            <div className="mt-1 truncate text-[11px] text-slate-400">
                              {bo.customer} — {bo.sku_name}
                            </div>
                            <div dir="ltr" className="mt-1 font-mono text-[11px] text-slate-300">
                              End: H{bo.old_end_hr.toFixed(1)} → H{bo.new_end_hr.toFixed(1)} (Due H
                              {bo.due_hr.toFixed(0)})
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Plant Risk Score Delta */}
                  <div className="mt-3 flex items-center justify-between rounded-xl border border-slate-800 bg-slate-950/80 px-3 py-2 text-xs">
                    <span className="text-slate-400">
                      {isAr ? "مؤشر مخاطر المصنع (قبل ← بعد):" : "Plant Risk Score (Before → After):"}
                    </span>
                    <span dir="ltr" className="font-mono font-bold text-slate-200">
                      {quote.risk_score_before} <ArrowRight className="inline h-3 w-3" />{" "}
                      <span
                        className={
                          quote.risk_score_after > quote.risk_score_before
                            ? "text-amber-300"
                            : "text-emerald-300"
                        }
                      >
                        {quote.risk_score_after}
                      </span>
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Sticky Footer: Discard Quote vs. Accept & Add to Live Schedule */}
        <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-t border-slate-800 bg-slate-950/90 px-4 py-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] sm:px-6 sm:pb-3">
          <button
            type="button"
            data-testid="btn-ctp-discard"
            onClick={() => setCtpModalOpen(false)}
            className="min-h-[44px] rounded-xl border border-slate-700 bg-slate-900 px-4 py-2 text-xs font-semibold text-slate-200 transition hover:bg-slate-800 md:min-h-0"
          >
            {t.ctpDiscardBtn}
          </button>

          {quote && quote.verdict !== "INFEASIBLE" && (
            <button
              type="button"
              data-testid="btn-ctp-commit"
              disabled={committing}
              onClick={() => void handleCommit()}
              className="inline-flex min-h-[44px] items-center gap-2 rounded-xl bg-emerald-500 px-5 py-2 text-xs font-bold text-slate-950 shadow-lg shadow-emerald-500/20 transition hover:bg-emerald-400 disabled:opacity-50 md:min-h-0"
            >
              {committing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <CheckCircle2 className="h-4 w-4" />
              )}
              <span>{committing ? t.ctpCommitting : t.ctpAcceptCommitBtn}</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
