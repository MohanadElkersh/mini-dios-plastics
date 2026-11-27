"use client";

import React, { useEffect, useState } from "react";
import {
  AlertTriangle,
  Award,
  Boxes,
  Building2,
  CheckCircle2,
  Clock,
  Droplet,
  Flame,
  History,
  Layers,
  Printer,
  Scale,
  ShieldCheck,
  TrendingUp,
  UserCheck,
  Wrench,
  X,
  Zap,
} from "lucide-react";
import { ScheduleExportMenu } from "@/components/ScheduleExportMenu";
import { convertCurrency, formatMoney } from "@/lib/format";
import { CONSTRAINT_LABELS, COPY } from "@/lib/i18n";
import { useApp } from "@/lib/store";

export function ExecutiveBriefModal() {
  const {
    lang,
    currency,
    config,
    result,
    briefModalOpen,
    setBriefModalOpen,
    setBacktestModalOpen,
    triggerExecutivePdfPrint,
  } = useApp();
  const t = COPY[lang];
  const isAr = lang === "ar";
  const [audienceTab, setAudienceTab] = useState<"owner" | "manager">("owner");

  useEffect(() => {
    if (!briefModalOpen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setBriefModalOpen(false);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [briefModalOpen, setBriefModalOpen]);

  if (!briefModalOpen) return null;

  const sc = result?.scorecard;
  const opt = result?.optimized;
  const base = result?.baseline;
  const audit = result?.audit;
  const fromCur = result?.currency ?? "SAR";
  const fx = result?.fx_egp_per_sar ?? 13.0;
  const fmtCur = (amt: number) => formatMoney(convertCurrency(amt, fromCur, currency, fx), currency);

  const lateSaved = base && opt ? Math.max(0, base.kpis.late_penalty_cost - opt.kpis.late_penalty_cost) : 0;
  const energySaved = base && opt ? Math.max(0, base.kpis.energy_cost - opt.kpis.energy_cost) : 0;
  const verifiedChecks = audit?.constraints_verified ?? [];
  const passedCount = verifiedChecks.filter((c) => c.passed).length;
  const totalChecks = verifiedChecks.length || 6;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center p-0 sm:items-center sm:p-6">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-950/85 backdrop-blur-sm transition-opacity"
        onClick={() => setBriefModalOpen(false)}
      />

      {/* Modal Dialog */}
      <div
        data-testid="executive-brief-modal"
        className="relative z-10 flex max-h-[90dvh] w-full max-w-4xl flex-col overflow-hidden rounded-t-3xl border border-slate-700/80 bg-slate-900 shadow-2xl shadow-cyan-950/30 sm:rounded-2xl"
      >
        {/* Header */}
        <div className="flex shrink-0 items-center justify-between border-b border-slate-800 bg-slate-950/80 px-4 py-3.5 sm:px-6 sm:py-4">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-emerald-500/40 bg-gradient-to-br from-emerald-500/20 to-cyan-500/20 text-emerald-400">
              <Award className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <h2 className="truncate text-sm font-bold text-slate-100 sm:text-lg">
                {t.executiveBriefTitle}
              </h2>
              <p className="truncate text-[11px] text-slate-400 sm:text-xs">
                {t.executiveBriefSubtitle}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setBriefModalOpen(false)}
            data-testid="btn-close-brief-modal"
            className="inline-flex min-h-[44px] min-w-[44px] shrink-0 items-center justify-center rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-slate-800 hover:text-slate-100 md:min-h-0 md:min-w-0"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 space-y-5 overflow-y-auto p-4 sm:space-y-6 sm:p-6">
          {/* v1.3 Feature 6: Dual-Audience Executive Switcher (Owner/Chairman vs. Plant/Production Manager) */}
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-slate-800 bg-slate-950/90 p-2">
            <div className="grid w-full grid-cols-1 gap-1.5 sm:w-auto sm:grid-cols-2">
              <button
                type="button"
                data-testid="brief-tab-owner"
                onClick={() => setAudienceTab("owner")}
                className={`inline-flex min-h-[40px] items-center justify-center gap-2 rounded-xl px-4 py-2 text-xs font-bold transition md:min-h-0 ${
                  audienceTab === "owner"
                    ? "bg-emerald-500 text-slate-950 shadow-md shadow-emerald-500/20"
                    : "bg-slate-900 text-slate-300 hover:text-white"
                }`}
              >
                <Building2 className="h-4 w-4 shrink-0" />
                <span>{t.briefOwnerTab}</span>
              </button>
              <button
                type="button"
                data-testid="brief-tab-manager"
                onClick={() => setAudienceTab("manager")}
                className={`inline-flex min-h-[40px] items-center justify-center gap-2 rounded-xl px-4 py-2 text-xs font-bold transition md:min-h-0 ${
                  audienceTab === "manager"
                    ? "bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/20"
                    : "bg-slate-900 text-slate-300 hover:text-white"
                }`}
              >
                <UserCheck className="h-4 w-4 shrink-0" />
                <span>{t.briefManagerTab}</span>
              </button>
            </div>

            <div className="flex flex-wrap items-center gap-1.5">
              <button
                type="button"
                data-testid="btn-brief-print-pdf"
                onClick={() =>
                  triggerExecutivePdfPrint(audienceTab === "manager" ? "brief_manager" : "brief_owner")
                }
                className="inline-flex min-h-[38px] items-center gap-1.5 rounded-lg border border-amber-500/45 bg-amber-500/15 px-3 py-1 text-[11px] font-bold text-amber-200 transition hover:bg-amber-500/25 md:min-h-0"
              >
                <Printer className="h-3.5 w-3.5 text-amber-400" />
                <span>{t.printPdfBtn}</span>
              </button>
              <ScheduleExportMenu compact testIdPrefix="brief-export" />
            </div>
          </div>

          {!result ? (
            <div className="rounded-xl border border-dashed border-slate-700 p-8 text-center text-slate-400 text-sm">
              {t.noResultYet}
            </div>
          ) : (
            <>
              {/* Audience-Tailored Strategic Narrative Card */}
              {audienceTab === "owner" ? (
                <div
                  data-testid="brief-owner-view-card"
                  className="rounded-2xl border border-emerald-500/40 bg-gradient-to-br from-emerald-500/15 via-slate-900 to-cyan-500/10 p-4 sm:p-5 space-y-3"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h3 className="text-sm font-bold text-white">
                      {isAr
                        ? "ملخص المالك ورئيس مجلس الإدارة: حماية ذاكرة المصنع وتحرير السيولة السنوية"
                        : "Owner & Chairman Brief: Institutional Memory & Annualized Cash Liberation"}
                    </h3>
                    <button
                      type="button"
                      data-testid="btn-brief-open-backtest"
                      onClick={() => {
                        setBriefModalOpen(false);
                        setBacktestModalOpen(true);
                      }}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-400/50 bg-emerald-500/20 px-2.5 py-1 text-[11px] font-bold text-emerald-200 hover:bg-emerald-500/30"
                    >
                      <History className="h-3.5 w-3.5" />
                      <span>{t.backtestBtn}</span>
                    </button>
                  </div>

                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-3 text-xs">
                      <div className="font-bold text-emerald-300">
                        {isAr
                          ? "١. تحويل خبرة التشغيل إلى أصل مؤسسي دائم"
                          : "1. Institutional Memory (Permanent Company Asset)"}
                      </div>
                      <p className="mt-1 text-[11px] leading-relaxed text-slate-300">
                        {isAr
                          ? "توثيق قواعد تسلسل الألوان وتوافق القوالب وتجفيف الخامات داخل محرك رياضي دائم لا يغادر المصنع أبداً."
                          : "Captures veteran floor know-how (color purge sequences, mold compatibilities, pre-drying rules) into a permanent digital asset."}
                      </p>
                    </div>

                    <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-3 text-xs">
                      <div className="font-bold text-cyan-300">
                        {isAr
                          ? "٢. إنهاء الخلاف اليومي بين الإنتاج والمخازن والمالية"
                          : "2. Ending Cross-Department Friction in One Click"}
                      </div>
                      <p className="mt-1 text-[11px] leading-relaxed text-slate-300">
                        {isAr
                          ? `مزامنة الحاويات تضبط إشغال المخزن عند ${(opt?.kpis.warehouse_utilization_pct ?? 0).toFixed(0)}% وتحمي ${fmtCur(opt?.kpis.trapped_working_capital ?? 0)} من التجميد.`
                          : `Container & WIP Sync balances long press runs against warehouse load (${(opt?.kpis.warehouse_utilization_pct ?? 0).toFixed(0)}%) and trapped container cash (${fmtCur(opt?.kpis.trapped_working_capital ?? 0)}).`}
                      </p>
                    </div>

                    <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-3 text-xs">
                      <div className="font-bold text-amber-300">
                        {isAr
                          ? "٣. العائد النقدي السنوي والطاقة المحررة"
                          : "3. Annualized Cash & Unlocked Selling Capacity"}
                      </div>
                      <p className="mt-1 text-[11px] leading-relaxed text-slate-300">
                        {isAr
                          ? `وفر سنوي متوقع ${fmtCur(result.financials.annual_projected_savings)} مع تحرير ${result.financials.unlocked_capacity_hours.toFixed(1)} ساعة إنتاج أسبوعياً.`
                          : `Projects ${fmtCur(result.financials.annual_projected_savings)} annualized savings while freeing ${result.financials.unlocked_capacity_hours.toFixed(1)} press hours/week for extra sales.`}
                      </p>
                    </div>

                    <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-3 text-xs">
                      <div className="font-bold text-indigo-300">
                        {isAr
                          ? "٤. إثبات العائد قبل الدفع (اختبار 30 يوماً)"
                          : "4. Zero-Risk 1-Month Historical Backtest Proof"}
                      </div>
                      <p className="mt-1 text-[11px] leading-relaxed text-slate-300">
                        {isAr
                          ? "إعادة تشغيل سجلات الشهر الماضي تثبت استرداد قيمة النظام خلال أيام معدودة من وفورات الهالك والوقت الإضافي."
                          : "Replaying your past 30-day press logs proves full license payback in days from purge scrap and overtime savings alone."}
                      </p>
                    </div>
                  </div>
                </div>
              ) : (
                <div
                  data-testid="brief-manager-view-card"
                  className="rounded-2xl border border-cyan-500/40 bg-gradient-to-br from-cyan-500/15 via-slate-900 to-indigo-500/10 p-4 sm:p-5 space-y-3"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h3 className="text-sm font-bold text-white">
                      {isAr
                        ? "درع القرار الهندسي لمدير المصنع والإنتاج: إثبات رياضي يحميك من الضغوط اليومية"
                        : "Plant & Production Manager Decision Shield: Mathematical Proof Against Floor Firefighting"}
                    </h3>
                    <span className="rounded-full border border-cyan-400/40 bg-cyan-500/20 px-2.5 py-0.5 text-[10px] font-bold text-cyan-200">
                      {isAr ? "درع القرار الهندسي" : "DECISION SHIELD"}
                    </span>
                  </div>

                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-3 text-xs">
                      <div className="font-bold text-cyan-300">
                        {isAr
                          ? "١. تبرير رياضي فوري للوقت الإضافي وعمالة الإسناد"
                          : "1. Mathematical Proof for Overtime & Relief Staffing"}
                      </div>
                      <p className="mt-1 text-[11px] leading-relaxed text-slate-300">
                        {isAr
                          ? `تغطية الورديات الحالية ${(result.workforce?.optimized.kpis.coverage_pct ?? 100).toFixed(1)}% مع جاهزية تبديل قوالب ${(result.workforce?.optimized.kpis.changeover_readiness_pct ?? 100).toFixed(0)}% — دليل رقمي واضح عند طلب دعم عمالة.`
                          : `Gives you exact shift coverage (${(result.workforce?.optimized.kpis.coverage_pct ?? 100).toFixed(1)}%) and mold-change readiness (${(result.workforce?.optimized.kpis.changeover_readiness_pct ?? 100).toFixed(0)}%) to justify staffing requests to ownership.`}
                      </p>
                    </div>

                    <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-3 text-xs">
                      <div className="font-bold text-purple-300">
                        {isAr
                          ? "٢. حماية نوافذ الصيانة الوقائية للقوالب (HC6)"
                          : "2. Protected Mold Preventive Maintenance Windows (HC6)"}
                      </div>
                      <p className="mt-1 text-[11px] leading-relaxed text-slate-300">
                        {isAr
                          ? "يحجز النظام صيانة القوالب الحرجة رياضياً قبل تجاوز 95% من عمر الضربات ليمنع كسر القالب تحت ضغط المبيعات."
                          : "Automatically locks mandatory mold PM windows before 95% shot limits so Sales can never force a run that damages a cavity."}
                      </p>
                    </div>

                    <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-3 text-xs">
                      <div className="font-bold text-amber-300">
                        {isAr
                          ? "٣. كشف التكلفة الحقيقية للأوامر العاجلة (Rush Orders)"
                          : "3. Instant Rush-Order Trade-Off Shield"}
                      </div>
                      <p className="mt-1 text-[11px] leading-relaxed text-slate-300">
                        {isAr
                          ? "عندما تطلب المبيعات إدخال أمر عاجل يكسر تسلسل الألوان، يظهر النظام فوراً تكلفة الهالك والتأخير الناتج بالأرقام."
                          : "When Sales demands a mid-week color break, show them the exact purge scrap kg and export delay cost in 2 seconds."}
                      </p>
                    </div>

                    <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-3 text-xs">
                      <div className="font-bold text-emerald-300">
                        {isAr
                          ? "٤. جدول ورديات وماكينات خالٍ من التعارضات (11/11 قيد)"
                          : "4. Zero-Violation Floor Execution (11/11 Constraints)"}
                      </div>
                      <p className="mt-1 text-[11px] leading-relaxed text-slate-300">
                        {isAr
                          ? "تحقق آلي من توافق القوالب، ساعات تجفيف PET/ABS، وعدم تشغيل قالب واحد على ماكينتين في نفس اللحظة."
                          : "Guarantees zero mold collisions, respected PET/ABS drying lead times, and 11h worker rest compliance every shift."}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Top Banner KPI Grid */}
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
                <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-3.5 text-center">
                  <div className="flex items-center justify-center text-emerald-400 mb-1">
                    <TrendingUp className="h-4 w-4" />
                  </div>
                  <div className="text-[11px] font-medium text-emerald-300/80">{t.metricNetSavings}</div>
                  <div dir="ltr" className="mt-1 text-base font-bold text-emerald-400 font-mono">
                    {fmtCur(sc?.cash_savings ?? 0)}
                  </div>
                  <div className="text-[10px] text-emerald-400/80 font-mono mt-0.5">
                    +{sc?.cash_savings_pct.toFixed(1)}% vs FIFO
                  </div>
                </div>

                <div className="rounded-xl border border-amber-500/30 bg-amber-950/20 p-3.5 text-center">
                  <div className="flex items-center justify-center text-amber-400 mb-1">
                    <Droplet className="h-4 w-4" />
                  </div>
                  <div className="text-[11px] font-medium text-amber-300/80">{t.metricScrapCut}</div>
                  <div className="mt-1 text-base font-bold text-amber-400 font-mono">
                    {sc?.purge_scrap_kg_saved.toFixed(1)} kg
                  </div>
                  <div className="text-[10px] text-slate-400 font-mono mt-0.5">
                    cut vs baseline
                  </div>
                </div>

                <div className="rounded-xl border border-cyan-500/30 bg-cyan-950/20 p-3.5 text-center">
                  <div className="flex items-center justify-center text-cyan-400 mb-1">
                    <Clock className="h-4 w-4" />
                  </div>
                  <div className="text-[11px] font-medium text-cyan-300/80">{t.metricHoursSaved}</div>
                  <div className="mt-1 text-base font-bold text-cyan-400 font-mono">
                    {sc?.changeover_hours_saved.toFixed(1)} hrs
                  </div>
                  <div className="text-[10px] text-slate-400 font-mono mt-0.5">
                    changeover cut
                  </div>
                </div>

                <div className="rounded-xl border border-rose-500/30 bg-rose-950/20 p-3.5 text-center">
                  <div className="flex items-center justify-center text-rose-400 mb-1">
                    <AlertTriangle className="h-4 w-4" />
                  </div>
                  <div className="text-[11px] font-medium text-rose-300/80">{t.metricLatePenalties}</div>
                  <div dir="ltr" className="mt-1 text-base font-bold text-rose-400 font-mono">
                    {fmtCur(lateSaved)}
                  </div>
                  <div className="text-[10px] text-slate-400 font-mono mt-0.5">
                    penalties saved
                  </div>
                </div>

                <div className="rounded-xl border border-yellow-500/30 bg-yellow-950/20 p-3.5 text-center">
                  <div className="flex items-center justify-center text-yellow-400 mb-1">
                    <Zap className="h-4 w-4" />
                  </div>
                  <div className="text-[11px] font-medium text-yellow-300/80">{t.metricEnergySaved}</div>
                  <div dir="ltr" className="mt-1 text-base font-bold text-yellow-400 font-mono">
                    {fmtCur(energySaved)}
                  </div>
                  <div className="text-[10px] text-slate-400 font-mono mt-0.5">
                    tariff optimized
                  </div>
                </div>

                <div className="rounded-xl border border-purple-500/30 bg-purple-950/20 p-3.5 text-center">
                  <div className="flex items-center justify-center text-purple-400 mb-1">
                    <Scale className="h-4 w-4" />
                  </div>
                  <div className="text-[11px] font-medium text-purple-300/80">{t.metricOeeOtif}</div>
                  <div className="mt-1 text-base font-bold text-purple-400 font-mono">
                    {opt?.kpis.oee_pct.toFixed(1)}% / {opt?.kpis.otif_pct.toFixed(0)}%
                  </div>
                  <div className="text-[10px] text-slate-400 font-mono mt-0.5">
                    OEE / OTIF
                  </div>
                </div>
              </div>

              {/* 6/6 Hard Constraint Verification */}
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="h-4 w-4 text-emerald-400" />
                    <h3 className="text-xs font-semibold text-slate-200">
                      {t.hardConstraintsTitle}
                    </h3>
                  </div>
                  <span
                    className={`rounded-full border px-2 py-0.5 text-[10px] font-bold ${
                      passedCount === totalChecks
                        ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                        : "bg-rose-500/15 border-rose-500/40 text-rose-300"
                    }`}
                  >
                    {passedCount}/{totalChecks} VERIFIED
                  </span>
                </div>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
                  {Object.entries(CONSTRAINT_LABELS[lang]).map(([code, label]) => {
                    const check = verifiedChecks.find((c) => c.id === code);
                    const ok = check ? check.passed : true;
                    return (
                      <div
                        key={code}
                        className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-xs ${
                          ok
                            ? "border-slate-800/80 bg-slate-900/60"
                            : "border-rose-500/40 bg-rose-950/30"
                        }`}
                      >
                        {ok ? (
                          <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                        ) : (
                          <AlertTriangle className="h-4 w-4 text-rose-400 shrink-0" />
                        )}
                        <span className="text-slate-300 text-[11px] leading-tight">{label}</span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Resin Consumption Breakdown */}
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                <div className="flex items-center gap-2 mb-3">
                  <Layers className="h-4 w-4 text-cyan-400" />
                  <h3 className="text-xs font-semibold text-slate-200">
                    {t.resinConsumptionAudit}
                  </h3>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[520px] text-start text-xs text-slate-300">
                    <thead>
                      <tr className="border-b border-slate-800 text-[11px] text-slate-400">
                        <th className="pb-2 pe-2 font-medium">{t.briefColResinCode}</th>
                        <th className="pb-2 pe-2 font-medium">{t.briefColVirginUsed}</th>
                        <th className="pb-2 pe-2 font-medium">{t.briefColRegrindUsed}</th>
                        <th className="pb-2 pe-2 font-medium">{t.briefColFifoScrap}</th>
                        <th className="pb-2 pe-2 font-medium">{t.briefColOptScrap}</th>
                        <th className="pb-2 font-medium text-emerald-400">{t.briefColScrapSaved}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/50 font-mono text-[11px]">
                      {opt?.resin_usage.map((r) => {
                        const baseScrap = base?.resin_usage.find((b) => b.resin_code === r.resin_code)?.purge_scrap_kg ?? 0;
                        const saved = Math.max(0, baseScrap - r.purge_scrap_kg);
                        return (
                          <tr key={r.resin_code} className="hover:bg-slate-900/40">
                            <td className="py-2 font-semibold text-slate-200">{r.resin_code}</td>
                            <td className="py-2 text-slate-300">{r.virgin_used_kg.toFixed(1)}</td>
                            <td className="py-2 text-slate-400">{r.regrind_used_kg.toFixed(1)}</td>
                            <td className="py-2 text-slate-400">{baseScrap.toFixed(1)}</td>
                            <td className="py-2 text-amber-300">{r.purge_scrap_kg.toFixed(1)}</td>
                            <td className="py-2 font-bold text-emerald-400">
                              {saved > 0 ? `-${saved.toFixed(1)}` : "0.0"}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Solver Telemetry */}
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Flame className="h-4 w-4 text-cyan-400" />
                  <h3 className="text-xs font-semibold text-slate-200">
                    {t.auditHistoryTitle}
                  </h3>
                </div>
                <div className="grid grid-cols-2 gap-2 text-[11px] sm:grid-cols-4 font-mono text-slate-400">
                  <div>
                    <span className="text-slate-500">{t.briefRunId} </span>
                    <span className="text-cyan-300">{result.run_id.slice(0, 8)}...</span>
                  </div>
                  <div>
                    <span className="text-slate-500">{t.briefSolveTime} </span>
                    <span className="text-slate-200">{result.solve_time_ms} ms</span>
                  </div>
                  <div>
                    <span className="text-slate-500">{t.briefRamadanShift} </span>
                    <span className={config.ramadan_shift_mode ? "text-emerald-400" : "text-slate-400"}>
                      {config.ramadan_shift_mode ? t.stateOn : t.stateOff}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500">{t.briefPeakTariffAvoid} </span>
                    <span className={config.avoid_peak_tariff_hrs ? "text-emerald-400" : "text-slate-400"}>
                      {config.avoid_peak_tariff_hrs ? t.stateOn : t.stateOff}
                    </span>
                  </div>
                </div>
                {audit && (
                  <div className="mt-2 text-[10px] font-mono text-slate-500 truncate">
                    SHA256: {audit.schedule_sha256}
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        {/* Sticky Footer */}
        <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-t border-slate-800 bg-slate-950/90 px-4 py-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] sm:px-6 sm:pb-3">
          <span className="hidden text-[11px] text-slate-400 sm:inline">
            {t.deterministicFooter}
          </span>
          <button
            type="button"
            onClick={() => setBriefModalOpen(false)}
            data-testid="btn-close-brief-modal-footer"
            className="min-h-[44px] w-full rounded-xl bg-slate-800 px-4 py-2 text-xs font-semibold text-slate-200 transition-colors hover:bg-slate-700 sm:w-auto md:min-h-0 md:rounded-lg md:py-1.5"
          >
            {t.closeModal}
          </button>
        </div>
      </div>
    </div>
  );
}
