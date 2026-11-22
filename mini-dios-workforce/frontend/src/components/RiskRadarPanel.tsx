"use client";

import React from "react";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Clock,
  Droplet,
  Radar,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { convertCurrency, formatMoney } from "@/lib/format";
import { COPY } from "@/lib/i18n";
import { useApp } from "@/lib/store";
import type { RiskAlert, RiskSeverity } from "@/lib/types";

interface RiskRadarPanelProps {
  compact?: boolean;
}

const SEVERITY_BADGE: Record<RiskSeverity, string> = {
  critical: "border-rose-500/45 bg-rose-500/15 text-rose-200",
  elevated: "border-amber-500/45 bg-amber-500/15 text-amber-200",
  watch: "border-cyan-500/40 bg-cyan-500/10 text-cyan-200",
  healthy: "border-emerald-500/40 bg-emerald-500/15 text-emerald-200",
};

const SEVERITY_LABEL_EN: Record<RiskSeverity, string> = {
  critical: "CRITICAL",
  elevated: "ELEVATED",
  watch: "WATCH",
  healthy: "HEALTHY",
};

const SEVERITY_LABEL_AR: Record<RiskSeverity, string> = {
  critical: "حرج",
  elevated: "مرتفع",
  watch: "مراقبة",
  healthy: "آمن",
};

export function RiskRadarPanel({ compact = false }: RiskRadarPanelProps) {
  const { lang, currency, result, setActiveView, openCopilotWithPrompt } = useApp();
  const t = COPY[lang];
  const isAr = lang === "ar";
  const radar = result?.risk_radar;

  if (!result || !radar) return null;

  const fx = result.fx_egp_per_sar ?? 13.0;
  const fmtExposure = (amt: number) =>
    formatMoney(convertCurrency(amt, result.currency, currency, fx), currency);

  const localizeCurrencyText = (text: string): string => {
    if (!text || currency === result.currency) return text;
    return text.replace(
      /([\d,]+(?:\.\d+)?)\s*(SAR|EGP)\b/g,
      (_match, rawNum: string, srcCur: string) => {
        const parsed = Number.parseFloat(rawNum.replace(/,/g, ""));
        if (Number.isNaN(parsed)) return _match;
        const converted = convertCurrency(parsed, srcCur as "SAR" | "EGP", currency, fx);
        return `${Math.round(converted).toLocaleString("en-US")} ${currency}`;
      }
    );
  };

  const handleInspect = (alert: RiskAlert) => {
    if (alert.entity_type === "shift") {
      setActiveView("workforce");
    } else if (alert.entity_type === "resin" || alert.entity_type === "mold") {
      setActiveView("gantt");
    } else {
      setActiveView("gantt");
    }
  };

  if (compact) {
    const topAlerts = radar.alerts.slice(0, 3);
    return (
      <div
        data-testid="risk-radar-compact"
        className="dios-card rounded-2xl p-4"
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-amber-500/35 bg-amber-500/10 text-amber-300">
              <Radar className="h-4 w-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-100">
                  {t.riskRadarTitle}
                </h3>
                <span className={`rounded-full border px-2 py-0.5 font-mono text-[10px] font-bold ${SEVERITY_BADGE[radar.risk_level]}`}>
                  {radar.overall_risk_score}/100 • {isAr ? SEVERITY_LABEL_AR[radar.risk_level] : SEVERITY_LABEL_EN[radar.risk_level]}
                </span>
              </div>
              <p className="text-[11px] text-slate-400">
                {radar.alerts.length === 0
                  ? t.riskAllClear
                  : isAr
                    ? `${radar.critical_count} حرج • ${radar.elevated_count} مرتفع • تعرض مالي ${fmtExposure(radar.total_financial_exposure)}`
                    : `${radar.critical_count} Critical • ${radar.elevated_count} Elevated • Exposure ${fmtExposure(radar.total_financial_exposure)}`}
              </p>
            </div>
          </div>

          {topAlerts.length > 0 && (
            <div className="flex flex-wrap items-center gap-2">
              {topAlerts.map((a) => (
                <button
                  key={a.alert_id}
                  type="button"
                  onClick={() => openCopilotWithPrompt(isAr ? a.suggested_prompt_ar : a.suggested_prompt_en)}
                  className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-[11px] font-semibold transition hover:brightness-110 ${SEVERITY_BADGE[a.severity]}`}
                >
                  <AlertTriangle className="h-3 w-3 shrink-0" />
                  <span className="max-w-[220px] truncate">{isAr ? a.title_ar : a.title_en}</span>
                  <Sparkles className="h-3 w-3 shrink-0 opacity-80" />
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <section
      data-testid="risk-radar-panel"
      className="dios-card rounded-2xl p-5"
    >
      {/* Header */}
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-amber-500/40 bg-gradient-to-br from-amber-500/20 to-rose-500/15 text-amber-300">
            <Radar className="h-5 w-5" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-sm font-bold text-white">{t.riskRadarTitle}</h2>
              <span
                data-testid="risk-radar-level-badge"
                className={`rounded-full border px-2.5 py-0.5 font-mono text-[10px] font-bold ${SEVERITY_BADGE[radar.risk_level]}`}
              >
                {isAr ? SEVERITY_LABEL_AR[radar.risk_level] : SEVERITY_LABEL_EN[radar.risk_level]} ({radar.overall_risk_score}/100)
              </span>
            </div>
            <p className="mt-0.5 text-xs text-slate-400">{t.riskRadarSubtitle}</p>
          </div>
        </div>

        {/* 4 Executive Risk Telemetry Pills */}
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <div className="rounded-xl border border-slate-800 bg-slate-950/80 px-3 py-2">
            <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
              {t.riskScoreLabel}
            </div>
            <div dir="ltr" className="mt-0.5 font-mono text-base font-bold text-white">
              {radar.overall_risk_score}
              <span className="text-xs font-normal text-slate-500">/100</span>
            </div>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-950/80 px-3 py-2">
            <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
              {t.riskExposureLabel}
            </div>
            <div
              dir="ltr"
              className={`mt-0.5 font-mono text-base font-bold ${
                radar.total_financial_exposure > 0 ? "text-rose-300" : "text-emerald-300"
              }`}
            >
              {fmtExposure(radar.total_financial_exposure)}
            </div>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-950/80 px-3 py-2">
            <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
              {t.riskExportsAtRisk}
            </div>
            <div
              dir="ltr"
              className={`mt-0.5 font-mono text-base font-bold ${
                radar.export_at_risk_count > 0 ? "text-amber-300" : "text-emerald-300"
              }`}
            >
              {radar.export_at_risk_count}
            </div>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-950/80 px-3 py-2">
            <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
              {t.riskTightestSlack}
            </div>
            <div dir="ltr" className="mt-0.5 font-mono text-sm font-bold text-cyan-300">
              {radar.tightest_slack_order_id
                ? `${radar.tightest_slack_order_id} (${radar.tightest_slack_hrs?.toFixed(1)}h)`
                : "—"}
            </div>
          </div>
        </div>
      </div>

      {/* Resin Silo Depletion Clocks */}
      {radar.resin_clocks.length > 0 && (
        <div className="mb-4 rounded-xl border border-slate-800/80 bg-slate-950/70 p-3.5">
          <div className="mb-2.5 flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-slate-300">
            <Droplet className="h-3.5 w-3.5 text-cyan-400" />
            <span>{t.resinClockTitle}</span>
          </div>
          <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-5">
            {radar.resin_clocks.map((rc) => {
              const barCls =
                rc.status === "critical"
                  ? "bg-rose-500"
                  : rc.status === "elevated"
                    ? "bg-amber-400"
                    : rc.status === "watch"
                      ? "bg-cyan-400"
                      : "bg-emerald-400";
              return (
                <div
                  key={rc.resin_code}
                  className="rounded-lg border border-slate-800/90 bg-slate-900/70 p-2.5"
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-mono font-bold text-white">{rc.resin_code}</span>
                    <span dir="ltr" className="font-mono text-[11px] font-semibold text-slate-300">
                      {rc.utilization_pct.toFixed(0)}%
                    </span>
                  </div>
                  <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
                    <div
                      className={`h-full rounded-full transition-all ${barCls}`}
                      style={{ width: `${Math.min(100, rc.utilization_pct)}%` }}
                    />
                  </div>
                  <div className="mt-1.5 flex items-center justify-between text-[10px] text-slate-400">
                    <span dir="ltr" className="font-mono">
                      {rc.remaining_virgin_kg.toLocaleString()} kg {isAr ? "متبقي" : "left"}
                    </span>
                    <span
                      dir="ltr"
                      className={`inline-flex items-center gap-0.5 font-mono font-semibold ${
                        rc.projected_stockout_hr !== null && rc.projected_stockout_hr !== undefined
                          ? "text-rose-300"
                          : "text-emerald-300"
                      }`}
                    >
                      <Clock className="h-2.5 w-2.5" />
                      {rc.projected_stockout_hr !== null && rc.projected_stockout_hr !== undefined
                        ? `H${rc.projected_stockout_hr.toFixed(0)}`
                        : rc.coverage_hrs_remaining >= 999
                          ? "Safe"
                          : `+${rc.coverage_hrs_remaining.toFixed(0)}h`}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Prioritized Risk Alerts */}
      {radar.alerts.length === 0 ? (
        <div className="flex items-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-xs font-medium text-emerald-200">
          <CheckCircle2 className="h-4 w-4 text-emerald-400" />
          <span>{t.riskAllClear}</span>
        </div>
      ) : (
        <div className="space-y-2">
          {radar.alerts.slice(0, 6).map((alert) => (
            <div
              key={alert.alert_id}
              data-testid={`risk-alert-${alert.alert_id}`}
              className="flex flex-col justify-between gap-2.5 rounded-xl border border-slate-800/90 bg-slate-950/75 p-3 sm:flex-row sm:items-center"
            >
              <div className="flex items-start gap-2.5">
                <ShieldAlert
                  className={`mt-0.5 h-4 w-4 shrink-0 ${
                    alert.severity === "critical"
                      ? "text-rose-400"
                      : alert.severity === "elevated"
                        ? "text-amber-400"
                        : "text-cyan-400"
                  }`}
                />
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={`rounded border px-1.5 py-0.5 font-mono text-[9px] font-bold uppercase ${SEVERITY_BADGE[alert.severity]}`}
                    >
                      {isAr ? SEVERITY_LABEL_AR[alert.severity] : SEVERITY_LABEL_EN[alert.severity]}
                    </span>
                    <span className="text-xs font-bold text-slate-100">
                      {localizeCurrencyText(isAr ? alert.title_ar : alert.title_en)}
                    </span>
                    <span dir="ltr" className="rounded bg-slate-800/90 px-1.5 py-0.5 font-mono text-[10px] text-cyan-300">
                      {localizeCurrencyText(alert.metric_value)}
                    </span>
                  </div>
                  <p className="mt-0.5 text-[11px] leading-relaxed text-slate-400">
                    {localizeCurrencyText(isAr ? alert.detail_ar : alert.detail_en)}
                  </p>
                </div>
              </div>

              <div className="flex shrink-0 items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => handleInspect(alert)}
                  className="inline-flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-[11px] font-semibold text-slate-200 transition hover:border-slate-500 hover:text-white"
                >
                  <span>{t.inspectOnSchedule}</span>
                  <ArrowRight className={`h-3 w-3 ${isAr ? "rotate-180" : ""}`} />
                </button>
                <button
                  type="button"
                  data-testid={`btn-mitigate-${alert.alert_id}`}
                  onClick={() =>
                    openCopilotWithPrompt(isAr ? alert.suggested_prompt_ar : alert.suggested_prompt_en)
                  }
                  className="inline-flex items-center gap-1 rounded-lg border border-cyan-500/40 bg-cyan-500/12 px-2.5 py-1.5 text-[11px] font-semibold text-cyan-200 transition hover:bg-cyan-500/25 hover:text-white"
                >
                  <Sparkles className="h-3 w-3 text-cyan-400" />
                  <span>{t.mitigateInCopilot}</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
