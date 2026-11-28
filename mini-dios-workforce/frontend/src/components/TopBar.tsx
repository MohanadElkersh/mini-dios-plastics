"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  Award,
  Boxes,
  Cpu,
  Database,
  Download,
  Factory,
  GanttChartSquare,
  Globe,
  Layers,
  Loader2,
  LogOut,
  Moon,
  Play,
  RotateCcw,
  Settings2,
  ShieldCheck,
  Sliders,
  Sparkles,
  TrendingUp,
  UserCheck,
  Users,
  Wrench,
  X,
  Zap,
} from "lucide-react";
import { downloadDiBlueprintArtifact } from "@/lib/api";
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
    toggleContainerSyncMode,
    runSolve,
    setBriefModalOpen,
    setCopilotOpen,
    auth,
    logout,
    resetHostedSandbox,
    activeEngine,
    isEngineOverride,
    diStandards,
    engineSwitching,
    adminPanelOpen,
    setAdminPanelOpen,
    switchOptimizationEngine,
  } = useApp();

  const t = COPY[lang];
  const [mobileControlsOpen, setMobileControlsOpen] = useState(false);
  const [downloadingArtifact, setDownloadingArtifact] = useState<string | null>(null);
  const tabRefs = useRef<Record<string, HTMLButtonElement | null>>({});

  const isAdmin = Boolean(
    auth.is_admin ||
      !auth.auth_enabled ||
      (auth.client_label && auth.client_label.toLowerCase() === "admin")
  );
  const isUemActive = activeEngine === "uem_di_v1";

  const handleDownloadBlueprint = async (fmt: "json" | "bpmn_xml" | "dmn_xml") => {
    if (downloadingArtifact) return;
    setDownloadingArtifact(fmt);
    try {
      await downloadDiBlueprintArtifact(fmt);
    } finally {
      setDownloadingArtifact(null);
    }
  };

  const activeRiskCount =
    (result?.risk_radar?.critical_count ?? 0) + (result?.risk_radar?.elevated_count ?? 0);

  const activeModesCount =
    (config.avoid_peak_tariff_hrs ? 1 : 0) +
    (config.ramadan_shift_mode ? 1 : 0) +
    (config.autonomous_pm_window ? 1 : 0) +
    (config.container_sync_enabled !== false ? 1 : 0);

  const tabs: { id: ViewTab; label: string; icon: React.ReactNode }[] = [
    { id: "scope", label: t.tabScope, icon: <Boxes className="h-4 w-4 shrink-0" /> },
    { id: "studio", label: t.tabStudio, icon: <Database className="h-4 w-4 shrink-0" /> },
    { id: "console", label: t.tabConsole, icon: <Sliders className="h-4 w-4 shrink-0" /> },
    { id: "gantt", label: t.tabGantt, icon: <GanttChartSquare className="h-4 w-4 shrink-0" /> },
    { id: "financials", label: t.tabFinancials, icon: <TrendingUp className="h-4 w-4 shrink-0" /> },
    { id: "workforce", label: t.tabWorkforce, icon: <Users className="h-4 w-4 shrink-0" /> },
  ];

  // Auto-scroll active tab into view on mobile tab switches
  useEffect(() => {
    const el = tabRefs.current[activeView];
    if (el && typeof el.scrollIntoView === "function") {
      try {
        el.scrollIntoView({ behavior: "smooth", inline: "center", block: "nearest" });
      } catch {
        // Fallback for older browsers
      }
    }
  }, [activeView]);

  // Close mobile controls drawer on Escape
  useEffect(() => {
    if (!mobileControlsOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMobileControlsOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [mobileControlsOpen]);

  return (
    <>
      <header className="relative z-30 w-full max-w-full overflow-x-clip border-b border-slate-800/90 bg-[#070b14]/95 backdrop-blur lg:sticky lg:top-0">
        <div className="mx-auto w-full max-w-[1440px] min-w-0 px-3 sm:px-6">
          {/* Row 1 (Mobile: Compact Brand + Quick Controls | Desktop: Brand + Session Utility Cluster in Top Corner) */}
          <div className="flex min-w-0 items-center justify-between gap-2 py-2.5 lg:grid lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center lg:gap-x-4 lg:gap-y-2 lg:py-2.5">
            {/* Brand Identity (Inline-Start) */}
            <div className="flex min-w-0 items-center gap-2.5 sm:gap-3 lg:col-start-1 lg:row-start-1">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-400 to-blue-600 text-slate-950 shadow-lg shadow-cyan-500/20 sm:h-10 sm:w-10">
                <Factory className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h1 className="truncate text-sm font-bold tracking-tight text-white sm:text-lg">
                    {t.appTitle}
                  </h1>
                  <span
                    data-testid="topbar-engine-pill"
                    className={`hidden items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-semibold sm:inline-flex ${
                      isUemActive
                        ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                        : "border-cyan-500/30 bg-cyan-500/10 text-cyan-300"
                    }`}
                  >
                    <ShieldCheck className="h-3 w-3 shrink-0" />
                    <span dir="ltr">{isUemActive ? t.topBarEngineUem : t.topBarEngineLegacy}</span>
                  </span>
                </div>
                <p className="hidden truncate text-xs text-slate-400 md:block">{t.appSubtitle}</p>
              </div>
            </div>

            {/* Desktop Session Utility Cluster in Top Brand Row (Inline-End: Right in EN LTR, Left in AR RTL) */}
            <div className="hidden min-w-0 flex-wrap items-center justify-end gap-2 lg:col-start-2 lg:row-start-1 lg:flex">
              {isAdmin && (
                <button
                  type="button"
                  data-testid="btn-admin-menu"
                  onClick={() => setAdminPanelOpen(true)}
                  className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-[11px] font-semibold transition ${
                    isUemActive
                      ? "border-emerald-500/45 bg-emerald-500/15 text-emerald-200 hover:bg-emerald-500/25"
                      : "border-cyan-500/40 bg-slate-900 text-cyan-200 hover:border-cyan-400/60 hover:text-white"
                  }`}
                >
                  <Layers className="h-3.5 w-3.5 shrink-0 text-cyan-400" />
                  <span>{t.adminBtn}</span>
                  <span
                    dir="ltr"
                    className={`rounded px-1.5 py-0.5 font-mono text-[10px] font-bold ${
                      isUemActive ? "bg-emerald-400 text-slate-950" : "bg-slate-800 text-cyan-300"
                    }`}
                  >
                    {isUemActive ? "UEM+DI" : "Legacy"}
                  </span>
                </button>
              )}
              {auth.auth_enabled && auth.authenticated && (
                <>
                  {auth.client_label && (
                    <span
                      data-testid="hosted-client-badge"
                      className="inline-flex items-center gap-1 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1.5 text-[11px] font-semibold text-emerald-200"
                    >
                      <UserCheck className="h-3.5 w-3.5 shrink-0 text-emerald-400" />
                      <span className="truncate">{auth.client_label}</span>
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
                    className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-[11px] font-semibold text-slate-300 transition hover:border-amber-500/50 hover:text-amber-200 disabled:opacity-50"
                  >
                    <RotateCcw className="h-3.5 w-3.5 shrink-0" />
                    <span>{t.sandboxResetBtn}</span>
                  </button>
                  <button
                    type="button"
                    data-testid="btn-sign-out"
                    onClick={() => void logout()}
                    title={t.signOutBtn}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-[11px] font-semibold text-slate-300 transition hover:border-rose-500/50 hover:text-rose-200"
                  >
                    <LogOut className="h-3.5 w-3.5 shrink-0" />
                    <span>{t.signOutBtn}</span>
                  </button>
                </>
              )}
            </div>

            {/* Row 2 on Desktop (Full-Width Wrapping Operational Controls) / Inline-End Quick Controls on Mobile */}
            <div className="flex shrink-0 items-center gap-1.5 sm:gap-2 lg:col-span-2 lg:row-start-2 lg:w-full lg:min-w-0 lg:shrink lg:flex-wrap lg:items-center lg:justify-between lg:gap-2 lg:border-t lg:border-slate-800/70 lg:pt-2">
              {/* Desktop-only Physics Mode Toggles (lg:flex flex-wrap) */}
              <div className="hidden min-w-0 flex-wrap items-center gap-2 lg:flex">
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
                  <Zap className="h-3.5 w-3.5 shrink-0" />
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
                  <Moon className="h-3.5 w-3.5 shrink-0" />
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
                  <Wrench className="h-3.5 w-3.5 shrink-0" />
                  <span>{t.autonomousPm}</span>
                  <span
                    className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                      config.autonomous_pm_window ? "bg-purple-400 text-slate-950" : "bg-slate-800 text-slate-400"
                    }`}
                  >
                    {config.autonomous_pm_window ? t.stateOn : t.stateOff}
                  </span>
                </button>

                {/* Container & Warehouse WIP Sync Toggle (v1.3 Feature 3) */}
                <button
                  type="button"
                  data-testid="toggle-container-sync"
                  disabled={loading}
                  onClick={() => void toggleContainerSyncMode()}
                  className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-semibold transition ${
                    config.container_sync_enabled !== false
                      ? "border-cyan-400/60 bg-cyan-500/20 text-cyan-200"
                      : "border-slate-700 bg-slate-900 text-slate-300 hover:border-slate-600 hover:text-white"
                  }`}
                >
                  <Boxes className="h-3.5 w-3.5 shrink-0" />
                  <span>{t.containerSync}</span>
                  <span
                    className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                      config.container_sync_enabled !== false
                        ? "bg-cyan-400 text-slate-950"
                        : "bg-slate-800 text-slate-400"
                    }`}
                  >
                    {config.container_sync_enabled !== false ? t.stateOn : t.stateOff}
                  </span>
                </button>
              </div>

              {/* Currency, Language & Action Buttons (Shared single DOM nodes across Mobile & Desktop) */}
              <div className="flex min-w-0 flex-wrap items-center gap-1.5 sm:gap-2 lg:ms-auto">
                {/* Currency Switch: SAR / EGP (Visible on Mobile & Desktop) */}
                <div className="inline-flex min-h-[44px] items-center rounded-lg border border-slate-700 bg-slate-900 p-0.5 text-xs font-semibold lg:min-h-0">
                  {(["SAR", "EGP"] as const).map((cur) => (
                    <button
                      key={cur}
                      type="button"
                      data-testid={`currency-${cur}`}
                      onClick={() => setCurrency(cur)}
                      className={`min-h-[38px] rounded-md px-2.5 py-1 transition lg:min-h-0 ${
                        currency === cur ? "bg-cyan-500 text-slate-950" : "text-slate-400 hover:text-slate-200"
                      }`}
                    >
                      {cur}
                    </button>
                  ))}
                </div>

                {/* Language Switch: EN / AR RTL (Visible on Mobile & Desktop) */}
                <button
                  type="button"
                  data-testid="toggle-lang"
                  onClick={() => setLang(lang === "en" ? "ar" : "en")}
                  className="inline-flex min-h-[44px] items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-xs font-semibold text-slate-200 transition hover:border-cyan-500/50 hover:text-white sm:px-3 lg:min-h-0"
                >
                  <Globe className="h-3.5 w-3.5 shrink-0 text-cyan-400" />
                  <span>{lang === "en" ? "العربية" : "EN"}</span>
                </button>

                {/* Mobile Controls / Settings Drawer Button (< lg) */}
                <button
                  type="button"
                  data-testid="btn-mobile-controls"
                  aria-label={t.mobileControlsBtn}
                  onClick={() => setMobileControlsOpen(true)}
                  className="relative inline-flex min-h-[44px] min-w-[44px] items-center justify-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-xs font-semibold text-slate-200 transition hover:border-cyan-500/50 hover:text-white lg:hidden"
                >
                  <Settings2 className="h-4 w-4 text-cyan-400" />
                  <span className="hidden sm:inline">{t.mobileControlsBtn}</span>
                  {activeModesCount > 0 && (
                    <span className="inline-flex h-4 min-w-[16px] items-center justify-center rounded-full bg-cyan-500 px-1 font-mono text-[10px] font-bold text-slate-950">
                      {activeModesCount}
                    </span>
                  )}
                </button>

                {/* Desktop-only Operations Copilot + Run CP-SAT (lg:flex) */}
                <div className="hidden min-w-0 flex-wrap items-center gap-2 lg:flex">
                  <button
                    type="button"
                    data-testid="btn-open-copilot"
                    onClick={() => setCopilotOpen(true)}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-cyan-500/40 bg-cyan-500/10 px-3 py-1.5 text-xs font-semibold text-cyan-200 transition hover:bg-cyan-500/20 hover:text-white"
                  >
                    <Sparkles className="h-3.5 w-3.5 shrink-0 text-cyan-400" />
                    <span>{t.copilotButton}</span>
                  </button>

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
                    {loading ? <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin" /> : <Play className="h-3.5 w-3.5 shrink-0" />}
                    <span>{loading ? t.solving : t.runOptimize}</span>
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Row 3: Horizontally Scrollable 6-Tab Strip on Mobile, Full Wrapping Row on Desktop */}
          <div className="flex min-w-0 items-center justify-between gap-2 border-t border-slate-800/70 py-1.5 lg:flex-wrap lg:py-2">
            <div className="relative min-w-0 flex-1">
              <nav
                className="no-scrollbar flex flex-nowrap items-center gap-1.5 overflow-x-auto snap-x snap-mandatory whitespace-nowrap pe-4 lg:flex-wrap lg:overflow-visible lg:pe-0"
                aria-label="Workspace Views"
              >
                {tabs.map((tab) => {
                  const active = activeView === tab.id;
                  return (
                    <button
                      key={tab.id}
                      ref={(el) => {
                        tabRefs.current[tab.id] = el;
                      }}
                      type="button"
                      data-testid={`tab-${tab.id}`}
                      onClick={() => setActiveView(tab.id)}
                      className={`inline-flex min-h-[44px] shrink-0 snap-start items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-semibold transition lg:min-h-0 ${
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
              {/* Subtle Edge Fade Indicator on Mobile */}
              <div
                aria-hidden="true"
                className="pointer-events-none absolute inset-y-0 end-0 w-6 bg-gradient-to-s from-[#070b14] to-transparent lg:hidden"
              />
            </div>

            {/* Desktop Status Pill + Executive Brief Button */}
            <div className="hidden shrink-0 items-center gap-2 lg:flex">
              {result && (
                <div className="inline-flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-900/80 px-2.5 py-1 text-[11px] text-slate-300">
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
                className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-500/40 bg-emerald-500/15 px-3 py-1.5 text-xs font-semibold text-emerald-200 shadow-sm shadow-emerald-950/40 transition hover:bg-emerald-500/25"
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

      {/* Mobile Controls Slide-Over Drawer / Bottom Sheet (< lg) */}
      {mobileControlsOpen && (
        <div
          data-testid="mobile-controls-drawer"
          className="fixed inset-0 z-50 flex items-end justify-center bg-black/75 backdrop-blur-sm sm:items-center sm:p-4 lg:hidden"
        >
          <div
            className="fixed inset-0"
            onClick={() => setMobileControlsOpen(false)}
          />
          <div
            role="dialog"
            aria-modal="true"
            className="relative z-10 flex max-h-[88dvh] w-full max-w-md flex-col overflow-hidden rounded-t-3xl border-t border-slate-700/80 bg-[#0b1120] shadow-2xl sm:rounded-2xl sm:border"
          >
            {/* Drawer Header */}
            <div className="flex items-center justify-between border-b border-slate-800 px-5 py-4">
              <div>
                <h2 className="text-sm font-bold text-white">{t.mobileControlsTitle}</h2>
                <p className="mt-0.5 text-[11px] text-slate-400">{t.mobileControlsSubtitle}</p>
              </div>
              <button
                type="button"
                data-testid="btn-close-mobile-controls"
                onClick={() => setMobileControlsOpen(false)}
                className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-xl text-slate-400 hover:bg-slate-800 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Drawer Body */}
            <div className="flex-1 space-y-3 overflow-y-auto p-5 pb-[calc(1.25rem+env(safe-area-inset-bottom))]">
              {/* Solver Telemetry Pill */}
              {result && (
                <div className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-900/90 px-3.5 py-2.5 text-xs text-slate-300">
                  <div className="flex items-center gap-2">
                    <Cpu className="h-4 w-4 text-emerald-400" />
                    <span className="font-bold text-emerald-300">
                      {STATUS_LABELS[lang][result.status] ?? result.status}
                    </span>
                  </div>
                  <div dir="ltr" className="font-mono text-[11px] text-slate-400">
                    {result.solve_time_ms} ms • {result.run_id}
                  </div>
                </div>
              )}

              {/* Physics Toggles */}
              <div className="space-y-2">
                <button
                  type="button"
                  data-testid="mobile-toggle-peak-tariff"
                  disabled={loading}
                  onClick={() => void togglePeakTariffMode()}
                  className={`flex min-h-[48px] w-full items-center justify-between rounded-xl border px-4 py-2.5 text-xs font-semibold transition ${
                    config.avoid_peak_tariff_hrs
                      ? "border-emerald-400/60 bg-emerald-500/20 text-emerald-200"
                      : "border-slate-700 bg-slate-900 text-slate-200"
                  }`}
                >
                  <span className="inline-flex items-center gap-2.5">
                    <Zap className="h-4 w-4 text-emerald-400" />
                    <span>{t.peakTariff}</span>
                  </span>
                  <span
                    className={`rounded-md px-2 py-0.5 text-[11px] font-bold ${
                      config.avoid_peak_tariff_hrs ? "bg-emerald-400 text-slate-950" : "bg-slate-800 text-slate-400"
                    }`}
                  >
                    {config.avoid_peak_tariff_hrs ? t.stateOn : t.stateOff}
                  </span>
                </button>

                <button
                  type="button"
                  data-testid="mobile-toggle-ramadan"
                  disabled={loading}
                  onClick={() => void toggleRamadanMode()}
                  className={`flex min-h-[48px] w-full items-center justify-between rounded-xl border px-4 py-2.5 text-xs font-semibold transition ${
                    config.ramadan_shift_mode
                      ? "border-amber-400/60 bg-amber-500/20 text-amber-200"
                      : "border-slate-700 bg-slate-900 text-slate-200"
                  }`}
                >
                  <span className="inline-flex items-center gap-2.5">
                    <Moon className="h-4 w-4 text-amber-400" />
                    <span>{t.ramadanMode}</span>
                  </span>
                  <span
                    className={`rounded-md px-2 py-0.5 text-[11px] font-bold ${
                      config.ramadan_shift_mode ? "bg-amber-400 text-slate-950" : "bg-slate-800 text-slate-400"
                    }`}
                  >
                    {config.ramadan_shift_mode ? t.stateOn : t.stateOff}
                  </span>
                </button>

                <button
                  type="button"
                  data-testid="mobile-toggle-auto-pm"
                  disabled={loading}
                  onClick={() => void toggleAutonomousPmMode()}
                  className={`flex min-h-[48px] w-full items-center justify-between rounded-xl border px-4 py-2.5 text-xs font-semibold transition ${
                    config.autonomous_pm_window
                      ? "border-purple-400/60 bg-purple-500/20 text-purple-200"
                      : "border-slate-700 bg-slate-900 text-slate-200"
                  }`}
                >
                  <span className="inline-flex items-center gap-2.5">
                    <Wrench className="h-4 w-4 text-purple-400" />
                    <span>{t.autonomousPm}</span>
                  </span>
                  <span
                    className={`rounded-md px-2 py-0.5 text-[11px] font-bold ${
                      config.autonomous_pm_window ? "bg-purple-400 text-slate-950" : "bg-slate-800 text-slate-400"
                    }`}
                  >
                    {config.autonomous_pm_window ? t.stateOn : t.stateOff}
                  </span>
                </button>

                <button
                  type="button"
                  data-testid="mobile-toggle-container-sync"
                  disabled={loading}
                  onClick={() => void toggleContainerSyncMode()}
                  className={`flex min-h-[48px] w-full items-center justify-between rounded-xl border px-4 py-2.5 text-xs font-semibold transition ${
                    config.container_sync_enabled !== false
                      ? "border-cyan-400/60 bg-cyan-500/20 text-cyan-200"
                      : "border-slate-700 bg-slate-900 text-slate-200"
                  }`}
                >
                  <span className="inline-flex items-center gap-2.5">
                    <Boxes className="h-4 w-4 text-cyan-400" />
                    <span>{t.containerSync}</span>
                  </span>
                  <span
                    className={`rounded-md px-2 py-0.5 text-[11px] font-bold ${
                      config.container_sync_enabled !== false
                        ? "bg-cyan-400 text-slate-950"
                        : "bg-slate-800 text-slate-400"
                    }`}
                  >
                    {config.container_sync_enabled !== false ? t.stateOn : t.stateOff}
                  </span>
                </button>
              </div>

              {/* Executive Brief Button */}
              <button
                type="button"
                data-testid="mobile-btn-open-brief-modal"
                onClick={() => {
                  setMobileControlsOpen(false);
                  setBriefModalOpen(true);
                }}
                className="flex min-h-[48px] w-full items-center justify-center gap-2 rounded-xl border border-emerald-500/40 bg-emerald-500/15 px-4 py-2.5 text-xs font-bold text-emerald-200 transition hover:bg-emerald-500/25"
              >
                <Award className="h-4 w-4 text-emerald-400" />
                <span>{t.executiveBriefBtn}</span>
              </button>

              {/* Hosted Demo Session Controls & Mobile Admin Trigger */}
              {isAdmin && (
                <div className="border-t border-slate-800 pt-3">
                  <button
                    type="button"
                    data-testid="mobile-btn-admin-menu"
                    onClick={() => {
                      setMobileControlsOpen(false);
                      setAdminPanelOpen(true);
                    }}
                    className="flex min-h-[44px] w-full items-center justify-between rounded-xl border border-cyan-500/40 bg-cyan-500/10 px-3.5 py-2.5 text-xs font-bold text-cyan-200 transition hover:bg-cyan-500/20"
                  >
                    <span className="inline-flex items-center gap-2">
                      <Layers className="h-4 w-4 text-cyan-400" />
                      <span>{t.adminPanelTitle}</span>
                    </span>
                    <span
                      dir="ltr"
                      className={`rounded-md px-2 py-0.5 font-mono text-[10px] font-bold ${
                        isUemActive ? "bg-emerald-400 text-slate-950" : "bg-slate-800 text-cyan-300"
                      }`}
                    >
                      {isUemActive ? "UEM+DI" : "Legacy"}
                    </span>
                  </button>
                </div>
              )}

              {auth.auth_enabled && auth.authenticated && (
                <div className="space-y-2 border-t border-slate-800 pt-3">
                  {auth.client_label && (
                    <div
                      data-testid="mobile-hosted-client-badge"
                      className="flex items-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3.5 py-2 text-xs font-semibold text-emerald-200"
                    >
                      <UserCheck className="h-4 w-4 text-emerald-400" />
                      <span>{auth.client_label}</span>
                    </div>
                  )}
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      data-testid="mobile-btn-reset-sandbox"
                      disabled={loading}
                      onClick={() => {
                        if (window.confirm(t.sandboxResetConfirm)) {
                          setMobileControlsOpen(false);
                          void resetHostedSandbox();
                        }
                      }}
                      className="inline-flex min-h-[44px] items-center justify-center gap-1.5 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs font-semibold text-slate-200 hover:border-amber-500/50 hover:text-amber-200 disabled:opacity-50"
                    >
                      <RotateCcw className="h-3.5 w-3.5" />
                      <span>{t.sandboxResetBtn}</span>
                    </button>
                    <button
                      type="button"
                      data-testid="mobile-btn-sign-out"
                      onClick={() => {
                        setMobileControlsOpen(false);
                        void logout();
                      }}
                      className="inline-flex min-h-[44px] items-center justify-center gap-1.5 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs font-semibold text-rose-200 hover:border-rose-500/50"
                    >
                      <LogOut className="h-3.5 w-3.5" />
                      <span>{t.signOutBtn}</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Sticky Bottom Action Bar on Mobile (< lg) */}
      <div
        data-testid="mobile-bottom-action-bar"
        className="fixed inset-x-0 bottom-0 z-40 border-t border-slate-800/90 bg-[#070b14]/95 px-3 pt-2 pb-[calc(0.5rem+env(safe-area-inset-bottom))] shadow-2xl backdrop-blur-md lg:hidden"
      >
        <div className="mx-auto flex max-w-md items-center gap-2">
          <button
            type="button"
            data-testid="mobile-btn-run-solve"
            disabled={loading || (validation !== null && !validation.ready)}
            onClick={() => {
              setActiveView("console");
              void runSolve();
            }}
            className="inline-flex min-h-[44px] flex-1 items-center justify-center gap-2 rounded-xl bg-cyan-500 px-4 py-2.5 text-xs font-bold text-slate-950 shadow-lg shadow-cyan-500/20 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            <span className="truncate">{loading ? t.solving : t.runOptimize}</span>
          </button>

          <button
            type="button"
            data-testid="mobile-btn-open-copilot"
            onClick={() => setCopilotOpen(true)}
            className="inline-flex min-h-[44px] shrink-0 items-center justify-center gap-1.5 rounded-xl border border-cyan-500/40 bg-cyan-500/15 px-3.5 py-2.5 text-xs font-bold text-cyan-200 transition hover:bg-cyan-500/25"
          >
            <Sparkles className="h-4 w-4 text-cyan-400" />
            <span>{t.copilotButton}</span>
          </button>
        </div>
      </div>

      {/* Admin Control & Solver Engine Switcher Modal (Strictly Admin-Gated) */}
      {isAdmin && adminPanelOpen && (
        <div
          data-testid="admin-engine-modal"
          className="fixed inset-0 z-50 flex items-end justify-center bg-black/75 backdrop-blur-sm sm:items-center sm:p-4"
        >
          <div
            className="fixed inset-0"
            onClick={() => setAdminPanelOpen(false)}
          />
          <div
            role="dialog"
            aria-modal="true"
            className="relative z-10 flex max-h-[90dvh] w-full max-w-lg flex-col overflow-hidden rounded-t-3xl border-t border-slate-700/80 bg-[#0b1120] shadow-2xl sm:rounded-2xl sm:border"
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-slate-800 px-5 py-4">
              <div className="flex items-center gap-2.5">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-cyan-500/40 bg-cyan-500/15 text-cyan-300">
                  <Layers className="h-4 w-4" />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-white">{t.adminPanelTitle}</h2>
                  <p className="mt-0.5 text-[11px] text-slate-400">{t.adminPanelSubtitle}</p>
                </div>
              </div>
              <button
                type="button"
                data-testid="btn-close-admin-modal"
                onClick={() => setAdminPanelOpen(false)}
                className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-xl text-slate-400 hover:bg-slate-800 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 space-y-4 overflow-y-auto p-5 pb-[calc(1.25rem+env(safe-area-inset-bottom))]">
              {/* Optimization Engine (Live Demo Switch) Card */}
              <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-xs font-bold text-white">{t.adminEngineCardTitle}</span>
                  <span
                    className={`rounded-md border px-2 py-0.5 text-[10px] font-semibold ${
                      isEngineOverride
                        ? "border-amber-500/40 bg-amber-500/15 text-amber-200"
                        : "border-slate-700 bg-slate-800 text-slate-300"
                    }`}
                  >
                    {isEngineOverride ? t.adminEngineLiveOverride : t.adminEngineServerDefault}
                  </span>
                </div>

                {/* Status Pill */}
                <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                  <span
                    data-testid="admin-active-engine-badge"
                    className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-bold ${
                      isUemActive
                        ? "border-emerald-500/45 bg-emerald-500/15 text-emerald-200"
                        : "border-amber-500/45 bg-amber-500/15 text-amber-200"
                    }`}
                  >
                    <Cpu className="h-3.5 w-3.5 shrink-0" />
                    <span>{isUemActive ? t.adminEngineUemBadge : t.adminEngineLegacyBadge}</span>
                  </span>

                  {isEngineOverride && (
                    <button
                      type="button"
                      data-testid="btn-engine-reset-default"
                      disabled={engineSwitching || loading}
                      onClick={() => void switchOptimizationEngine("default")}
                      className="text-[11px] font-semibold text-cyan-300 underline decoration-cyan-500/50 underline-offset-4 transition hover:text-cyan-200 disabled:opacity-50"
                    >
                      {t.adminEngineResetDefault}
                    </button>
                  )}
                </div>

                {/* Bilingual Segmented Toggle Switch */}
                <div className="mt-3.5 grid grid-cols-2 gap-1.5 rounded-xl border border-slate-800 bg-slate-950 p-1">
                  <button
                    type="button"
                    data-testid="btn-engine-legacy"
                    disabled={engineSwitching || loading}
                    onClick={() => void switchOptimizationEngine("legacy_cpsat_v1")}
                    className={`inline-flex min-h-[42px] items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-xs font-bold transition disabled:opacity-50 ${
                      !isUemActive
                        ? "bg-amber-500 text-slate-950 shadow-md shadow-amber-500/20"
                        : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
                    }`}
                  >
                    <span>{t.adminEngineOptLegacy}</span>
                  </button>
                  <button
                    type="button"
                    data-testid="btn-engine-uem"
                    disabled={engineSwitching || loading}
                    onClick={() => void switchOptimizationEngine("uem_di_v1")}
                    className={`inline-flex min-h-[42px] items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-xs font-bold transition disabled:opacity-50 ${
                      isUemActive
                        ? "bg-emerald-400 text-slate-950 shadow-md shadow-emerald-500/20"
                        : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
                    }`}
                  >
                    <span>{t.adminEngineOptUem}</span>
                  </button>
                </div>

                {/* Inline Re-solving Spinner */}
                {engineSwitching && (
                  <div
                    data-testid="admin-engine-resolving-spinner"
                    className="mt-3 flex items-center justify-center gap-2 rounded-xl border border-cyan-500/30 bg-cyan-500/10 px-3 py-2 text-xs font-semibold text-cyan-200"
                  >
                    <Loader2 className="h-4 w-4 animate-spin text-cyan-400" />
                    <span>{t.adminEngineResolving}</span>
                  </div>
                )}

                {/* Active DI Standards Pills */}
                <div className="mt-3 flex flex-wrap items-center gap-1.5">
                  {diStandards.map((std) => (
                    <span
                      key={std}
                      dir="ltr"
                      className="rounded-md border border-slate-800 bg-slate-950/80 px-2 py-0.5 font-mono text-[10px] text-slate-400"
                    >
                      {std}
                    </span>
                  ))}
                </div>
              </div>

              {/* 1-Click 5-Layer DI Standards Export Buttons */}
              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                <div className="mb-2.5 text-xs font-bold text-slate-200">{t.adminDiExportsLabel}</div>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                  <button
                    type="button"
                    data-testid="btn-export-di-json"
                    disabled={downloadingArtifact !== null}
                    onClick={() => void handleDownloadBlueprint("json")}
                    className="inline-flex min-h-[40px] items-center justify-center gap-1.5 rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs font-semibold text-cyan-200 transition hover:border-cyan-500/50 hover:text-white disabled:opacity-50"
                  >
                    {downloadingArtifact === "json" ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Download className="h-3.5 w-3.5 text-cyan-400" />
                    )}
                    <span>{t.adminExportJsonBlueprint}</span>
                  </button>
                  <button
                    type="button"
                    data-testid="btn-export-di-bpmn"
                    disabled={downloadingArtifact !== null}
                    onClick={() => void handleDownloadBlueprint("bpmn_xml")}
                    className="inline-flex min-h-[40px] items-center justify-center gap-1.5 rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs font-semibold text-emerald-200 transition hover:border-emerald-500/50 hover:text-white disabled:opacity-50"
                  >
                    {downloadingArtifact === "bpmn_xml" ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Download className="h-3.5 w-3.5 text-emerald-400" />
                    )}
                    <span dir="ltr">{t.adminExportBpmnXml}</span>
                  </button>
                  <button
                    type="button"
                    data-testid="btn-export-di-dmn"
                    disabled={downloadingArtifact !== null}
                    onClick={() => void handleDownloadBlueprint("dmn_xml")}
                    className="inline-flex min-h-[40px] items-center justify-center gap-1.5 rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs font-semibold text-purple-200 transition hover:border-purple-500/50 hover:text-white disabled:opacity-50"
                  >
                    {downloadingArtifact === "dmn_xml" ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Download className="h-3.5 w-3.5 text-purple-400" />
                    )}
                    <span dir="ltr">{t.adminExportDmnXml}</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
