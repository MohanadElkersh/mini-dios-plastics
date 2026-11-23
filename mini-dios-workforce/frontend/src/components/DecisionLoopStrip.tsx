"use client";

import React from "react";
import {
  Activity,
  ChevronRight,
  Cpu,
  Database,
  Radar,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { convertCurrency, formatMoney } from "@/lib/format";
import { COPY } from "@/lib/i18n";
import { useApp } from "@/lib/store";

export function DecisionLoopStrip() {
  const { lang, currency, validation, result, loading, workforceLoading, setActiveView, setCopilotOpen } = useApp();
  const t = COPY[lang];
  const isAr = lang === "ar";

  const summary = validation?.summary;
  const radar = result?.risk_radar;
  const pressHcOk = result?.audit.constraints_verified.filter((c) => c.passed).length ?? 0;
  const pressHcTot = result?.audit.constraints_verified.length ?? 6;
  const wfHcOk = result?.workforce?.constraints_verified.filter((c) => c.passed).length ?? 0;
  const wfHcTot = result?.workforce?.constraints_verified.length ?? 0;
  const totalHcOk = pressHcOk + wfHcOk;
  const totalHcTot = pressHcTot + wfHcTot;

  const weeklySavingsDisplay = result
    ? formatMoney(
        convertCurrency(
          result.financials?.total_weekly_savings ?? result.scorecard.cash_savings,
          result.currency,
          currency,
          result.fx_egp_per_sar
        ),
        currency
      )
    : null;

  const riskTone =
    radar?.risk_level === "critical"
      ? "text-rose-300 border-rose-500/35 bg-rose-500/10"
      : radar?.risk_level === "elevated"
        ? "text-amber-200 border-amber-500/35 bg-amber-500/10"
        : "text-emerald-300 border-emerald-500/30 bg-emerald-500/10";

  const stages = [
    {
      id: "model",
      label: t.loopModel,
      icon: <Database className="h-3.5 w-3.5 text-cyan-400" />,
      metric: summary
        ? `${summary.presses_active}/${summary.presses_total}P • ${summary.orders_total}O${
            summary.workers_total ? ` • ${summary.workers_active}/${summary.workers_total}W` : ""
          }`
        : "—",
      tone: validation?.ready
        ? "text-cyan-200 border-cyan-500/25 bg-cyan-500/8"
        : "text-rose-200 border-rose-500/35 bg-rose-500/10",
      onClick: () => setActiveView("studio"),
    },
    {
      id: "sense",
      label: t.loopSense,
      icon: <Radar className="h-3.5 w-3.5 text-amber-400" />,
      metric: radar
        ? `${isAr ? "خطر" : "Risk"} ${radar.overall_risk_score}/100`
        : isAr
          ? "جاهز"
          : "Ready",
      tone: radar ? riskTone : "text-slate-300 border-slate-700/70 bg-slate-900/70",
      onClick: () => setActiveView("scope"),
    },
    {
      id: "optimize",
      label: t.loopOptimize,
      icon: <Cpu className="h-3.5 w-3.5 text-cyan-300" />,
      metric:
        loading || workforceLoading
          ? isAr
            ? "جاري الحل..."
            : "Solving..."
          : result
            ? `${result.status} • ${result.solve_time_ms}ms`
            : "CP-SAT",
      tone: result
        ? "text-cyan-200 border-cyan-500/30 bg-cyan-500/10"
        : "text-slate-300 border-slate-700/70 bg-slate-900/70",
      onClick: () => setActiveView("console"),
    },
    {
      id: "command",
      label: t.loopCommand,
      icon: <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />,
      metric: result ? `${totalHcOk}/${totalHcTot} HC` : "0/6 HC",
      tone:
        result && totalHcOk === totalHcTot
          ? "text-emerald-300 border-emerald-500/35 bg-emerald-500/10"
          : "text-slate-300 border-slate-700/70 bg-slate-900/70",
      onClick: () => setActiveView("gantt"),
    },
    {
      id: "adapt",
      label: t.loopAdapt,
      icon: <Sparkles className="h-3.5 w-3.5 text-emerald-300" />,
      metric: weeklySavingsDisplay ? `+${weeklySavingsDisplay}/wk` : isAr ? "محاكاة" : "What-If",
      tone: "text-emerald-200 border-emerald-500/30 bg-emerald-500/10 hover:bg-emerald-500/20",
      onClick: () => setCopilotOpen(true),
    },
  ];

  return (
    <div
      data-testid="decision-loop-strip"
      className="border-b border-slate-800/70 bg-[#080d19]/90 backdrop-blur-sm"
    >
      <div className="mx-auto flex max-w-[1440px] items-center justify-between gap-2 px-3 py-1.5 sm:px-6 sm:py-2 lg:flex-wrap">
        <div className="hidden items-center gap-1.5 text-[10px] font-bold uppercase tracking-[0.14em] text-slate-400 xl:flex">
          <Activity className="h-3.5 w-3.5 text-cyan-400" />
          <span>{isAr ? "حلقة ذكاء القرار الحتمي" : "DECISION INTELLIGENCE LOOP"}</span>
        </div>

        <div className="no-scrollbar flex flex-1 flex-nowrap items-center gap-1.5 overflow-x-auto snap-x whitespace-nowrap lg:flex-wrap lg:justify-between xl:justify-end">
          {stages.map((st, idx) => (
            <React.Fragment key={st.id}>
              <button
                type="button"
                data-testid={`loop-stage-${st.id}`}
                onClick={st.onClick}
                className={`inline-flex min-h-[36px] shrink-0 snap-start items-center gap-1.5 rounded-lg border px-2.5 py-1 text-[11px] transition hover:brightness-110 lg:min-h-0 lg:gap-2 ${st.tone}`}
              >
                {st.icon}
                <span className="font-semibold">{st.label}</span>
                <span dir="ltr" className="font-mono text-[10px] font-bold opacity-90">
                  {st.metric}
                </span>
              </button>
              {idx < stages.length - 1 && (
                <ChevronRight
                  className={`hidden h-3.5 w-3.5 shrink-0 text-slate-600 lg:block ${isAr ? "rotate-180" : ""}`}
                />
              )}
            </React.Fragment>
          ))}
        </div>
      </div>
    </div>
  );
}
