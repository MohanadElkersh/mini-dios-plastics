"use client";

import React from "react";
import {
  Award,
  Boxes,
  Cpu,
  Database,
  Factory,
  GanttChartSquare,
  Globe,
  Loader2,
  LogOut,
  Moon,
  Play,
  RotateCcw,
  ShieldCheck,
  Sliders,
  Sparkles,
  TrendingUp,
  UserCheck,
  Users,
  Wrench,
  Zap,
} from "lucide-react";
import { COPY, STATUS_LABELS } from "@/lib/i18n";
import { useApp } from "@/lib/store";
import type { ViewTab } from "@/lib/types";

export function TopBar() {
  const {
    lang,
    setLang,
    currency,
    setCurrency,
    activeView,
    setActiveView,
    config,
    result,
    loading,
    validation,
    toggleRamadanMode,
    togglePeakTariffMode,
    toggleAutonomousPmMode,
    runSolve,
    setBriefModalOpen,
    setCopilotOpen,
    auth,
    logout,
    resetHostedSandbox,
  } = useApp();

  const t = COPY[lang];
  const activeRiskCount =
    (result?.risk_radar?.critical_count ?? 0) + (result?.risk_radar?.elevated_count ?? 0);

  const tabs: { id: ViewTab; label: string; icon: React.ReactNode }[] = [
    { id: "scope", label: t.tabScope, icon: <Boxes className="h-4 w-4" /> },
    { id: "studio", label: t.tabStudio, icon: <Database className="h-4 w-4" /> },
    { id: "console", label: t.tabConsole, icon: <Sliders className="h-4 w-4" /> },
    { id: "gantt", label: t.tabGantt, icon: <GanttChartSquare className="h-4 w-4" /> },
    { id: "financials", label: t.tabFinancials, icon: <TrendingUp className="h-4 w-4" /> },
    { id: "workforce", label: t.tabWorkforce, icon: <Users className="h-4 w-4" /> },
  ];

  return (
    <header className="sticky top-0 z-30 border-b border-slate-800/90 bg-[#070b14]/95 backdrop-blur">
      <div className="mx-auto max-w-[1440px] px-4 sm:px-6">
        {/* Top Row: Brand + Global Controls */}
        <div className="flex flex-wrap items-center justify-between gap-3 py-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-400 to-blue-600 text-slate-950 shadow-lg shadow-cyan-500/20">
              <Factory className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-bold tracking-tight text-white sm:text-lg">
                  {t.appTitle}
                </h1>
                <span className="hidden items-center gap-1 rounded-full border border-cyan-500/30 bg-cyan-500/10 px-2 py-0.5 text-[11px] font-semibold text-cyan-300 sm:inline-flex">
                  <ShieldCheck className="h-3 w-3" />
                  OR-Tools CP-SAT
                </span>
              </div>
              <p className="text-xs text-slate-400">{t.appSubtitle}</p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* Peak Electricity Tariff Avoidance Toggle */}
            <button
              type="button"
              data-testid="toggle-peak-tariff"
              disabled={loading}
              onClick={() => void togglePeakTariffMode()}
              className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-semibold transition ${
                config.avoid_peak_tariff_hrs
                  ? "border-emerald-400/60 bg-emerald-500/20 text-emerald-200"
                  : "border-slate-700 bg-slate-900 text-slate-300 hover:border-slate-600 hover:text-white"
              }`}
            >
              <Zap className="h-3.5 w-3.5" />
              <span>{t.peakTariff}</span>
              <span
                className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                  config.avoid_peak_tariff_hrs ? "bg-emerald-400 text-slate-950" : "bg-slate-800 text-slate-400"
                }`}
              >
                {config.avoid_peak_tariff_hrs ? t.stateOn : t.stateOff}
              </span>
            </button>

            {/* Ramadan Shift Mode Toggle */}
            <button
              type="button"
              data-testid="toggle-ramadan"
              disabled={loading}
              onClick={() => void toggleRamadanMode()}
              className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-semibold transition ${
                config.ramadan_shift_mode
                  ? "border-amber-400/60 bg-amber-500/20 text-amber-200"
                  : "border-slate-700 bg-slate-900 text-slate-300 hover:border-slate-600 hover:text-white"
              }`}
            >
              <Moon className="h-3.5 w-3.5" />
              <span>{t.ramadanMode}</span>
              <span
                className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                  config.ramadan_shift_mode ? "bg-amber-400 text-slate-950" : "bg-slate-800 text-slate-400"
                }`}
              >
                {config.ramadan_shift_mode ? t.stateOn : t.stateOff}
              </span>
            </button>

            {/* Autonomous Preventive Maintenance Co-Optimization Toggle */}
            <button
              type="button"
              data-testid="toggle-auto-pm"
              disabled={loading}
              onClick={() => void toggleAutonomousPmMode()}
              className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-semibold transition ${
                config.autonomous_pm_window
                  ? "border-purple-400/60 bg-purple-500/20 text-purple-200"
                  : "border-slate-700 bg-slate-900 text-slate-300 hover:border-slate-600 hover:text-white"
              }`}
            >
              <Wrench className="h-3.5 w-3.5" />
              <span>{t.autonomousPm}</span>
              <span
                className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                  config.autonomous_pm_window ? "bg-purple-400 text-slate-950" : "bg-slate-800 text-slate-400"
                }`}
              >
                {config.autonomous_pm_window ? t.stateOn : t.stateOff}
              </span>
            </button>

            {/* Currency Switch: SAR / EGP */}
            <div className="inline-flex rounded-lg border border-slate-700 bg-slate-900 p-0.5 text-xs font-semibold">
              {(["SAR", "EGP"] as const).map((cur) => (
                <button
                  key={cur}
                  type="button"
                  data-testid={`currency-${cur}`}
                  onClick={() => setCurrency(cur)}
                  className={`rounded-md px-2.5 py-1 transition ${
                    currency === cur ? "bg-cyan-500 text-slate-950" : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {cur}
                </button>
              ))}
            </div>

            {/* Language Switch: EN / AR RTL */}
            <button
              type="button"
              data-testid="toggle-lang"
              onClick={() => setLang(lang === "en" ? "ar" : "en")}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-semibold text-slate-200 transition hover:border-cyan-500/50 hover:text-white"
            >
              <Globe className="h-3.5 w-3.5 text-cyan-400" />
              <span>{lang === "en" ? "العربية" : "English"}</span>
            </button>

            {/* Operations Copilot Button */}
            <button
              type="button"
              data-testid="btn-open-copilot"
              onClick={() => setCopilotOpen(true)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-cyan-500/40 bg-cyan-500/10 px-3 py-1.5 text-xs font-semibold text-cyan-200 transition hover:bg-cyan-500/20 hover:text-white"
            >
              <Sparkles className="h-3.5 w-3.5 text-cyan-400" />
              <span>{t.copilotButton}</span>
            </button>

            {/* Primary Solve CTA */}
            <button
              type="button"
              data-testid="btn-run-solve"
              disabled={loading || (validation !== null && !validation.ready)}
              onClick={() => {
                setActiveView("console");
                void runSolve();
              }}
              className="inline-flex items-center gap-2 rounded-lg bg-cyan-500 px-3.5 py-1.5 text-xs font-bold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
              <span>{loading ? t.solving : t.runOptimize}</span>
            </button>

            {/* Hosted Demo Session Controls (visible when AUTH_ENABLED=true) */}
            {auth.auth_enabled && auth.authenticated && (
              <div className="flex items-center gap-1.5 border-s border-slate-800 ps-2">
                {auth.client_label && (
                  <span
                    data-testid="hosted-client-badge"
                    className="hidden items-center gap-1 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1.5 text-[11px] font-semibold text-emerald-200 xl:inline-flex"
                  >
                    <UserCheck className="h-3.5 w-3.5 text-emerald-400" />
                    <span>{auth.client_label}</span>
                  </span>
                )}
                <button
                  type="button"
                  data-testid="btn-reset-sandbox"
                  disabled={loading}
                  onClick={() => {
                    if (window.confirm(t.sandboxResetConfirm)) {
                      void resetHostedSandbox();
                    }
                  }}
                  title={t.sandboxResetBtn}
                  className="inline-flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-[11px] font-semibold text-slate-300 transition hover:border-amber-500/50 hover:text-amber-200 disabled:opacity-50"
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                  <span className="hidden lg:inline">{t.sandboxResetBtn}</span>
                </button>
                <button
                  type="button"
                  data-testid="btn-sign-out"
                  onClick={() => void logout()}
                  title={t.signOutBtn}
                  className="inline-flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-[11px] font-semibold text-slate-300 transition hover:border-rose-500/50 hover:text-rose-200"
                >
                  <LogOut className="h-3.5 w-3.5" />
                  <span className="hidden lg:inline">{t.signOutBtn}</span>
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Second Row: View Navigation Tabs + Status Pill + Export */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-800/70 py-2">
          <nav className="flex flex-wrap items-center gap-1.5" aria-label="Workspace Views">
            {tabs.map((tab) => {
              const active = activeView === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  data-testid={`tab-${tab.id}`}
                  onClick={() => setActiveView(tab.id)}
                  className={`inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                    active
                      ? "bg-slate-800 text-cyan-300 ring-1 ring-cyan-500/40"
                      : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
                  }`}
                >
                  {tab.icon}
                  <span>{tab.label}</span>
                  {tab.id === "scope" && activeRiskCount > 0 && (
                    <span className="rounded-full bg-rose-500/20 px-1.5 py-0.5 font-mono text-[10px] font-bold text-rose-300">
                      {activeRiskCount}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>

          <div className="flex items-center gap-2">
            {result && (
              <div className="hidden items-center gap-2 rounded-lg border border-slate-800 bg-slate-900/80 px-2.5 py-1 text-[11px] text-slate-300 md:inline-flex">
                <Cpu className="h-3.5 w-3.5 text-emerald-400" />
                <span className="font-semibold text-emerald-300">
                  {STATUS_LABELS[lang][result.status] ?? result.status}
                </span>
                <span className="text-slate-500">•</span>
                <span dir="ltr" className="font-mono">
                  {result.solve_time_ms} ms
                </span>
                <span className="text-slate-500">•</span>
                <span dir="ltr" className="font-mono text-slate-400">
                  {result.run_id}
                </span>
              </div>
            )}
            <button
              type="button"
              data-testid="btn-open-brief-modal"
              onClick={() => setBriefModalOpen(true)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-500/40 bg-emerald-500/15 px-3 py-1.5 text-xs font-semibold text-emerald-200 transition hover:bg-emerald-500/25 shadow-sm shadow-emerald-950/40"
            >
              <Award className="h-3.5 w-3.5 text-emerald-400" />
              <span>{t.executiveBriefBtn}</span>
            </button>
          </div>
        </div>
      </div>

      {config.ramadan_shift_mode && (
        <div className="border-t border-amber-500/30 bg-amber-500/10 px-4 py-1.5 text-center text-xs font-medium text-amber-200">
          {t.ramadanBanner}
        </div>
      )}
      {config.autonomous_pm_window && (
        <div className="border-t border-purple-500/30 bg-purple-500/10 px-4 py-1.5 text-center text-xs font-medium text-purple-200">
          {t.autonomousPmBanner}
        </div>
      )}
    </header>
  );
}
