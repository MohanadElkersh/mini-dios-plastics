"use client";

import React from "react";
import { AlertCircle, CheckCircle2, Factory, Loader2, X } from "lucide-react";
import { CopilotDrawer } from "@/components/CopilotDrawer";
import { DataStudioView } from "@/components/DataStudioView";
import { DecisionLoopStrip } from "@/components/DecisionLoopStrip";
import { ExecutiveBriefModal } from "@/components/ExecutiveBriefModal";
import { FinancialsView } from "@/components/FinancialsView";
import { GuidedOnboardingModal } from "@/components/GuidedOnboardingModal";
import { HistoricalBacktestModal } from "@/components/HistoricalBacktestModal";
import { LoginGate } from "@/components/LoginGate";
import { ProductionGanttView } from "@/components/ProductionGanttView";
import { QuickAddModal } from "@/components/QuickAddModal";
import { ScopeView } from "@/components/ScopeView";
import { TopBar } from "@/components/TopBar";
import { TradeoffConsole } from "@/components/TradeoffConsole";
import { WorkforceView } from "@/components/WorkforceView";
import { COPY } from "@/lib/i18n";
import { AppProvider, useApp } from "@/lib/store";

function DashboardShell() {
  const {
    lang,
    activeView,
    setActiveView,
    error,
    clearError,
    appliedDelta,
    clearAppliedDelta,
    auth,
    authChecked,
  } = useApp();
  const t = COPY[lang];
  const isAr = lang === "ar";

  if (!authChecked) {
    return (
      <div className="flex min-h-dvh flex-col items-center justify-center bg-[#060a13] px-4 text-slate-300">
        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-400 to-blue-600 text-slate-950 shadow-lg shadow-cyan-500/20">
          <Factory className="h-6 w-6" />
        </div>
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-400">
          <Loader2 className="h-4 w-4 animate-spin text-cyan-400" />
          <span>{lang === "ar" ? "جاري تهيئة مركز القيادة..." : "Initializing Mini-DIOS Command Center..."}</span>
        </div>
      </div>
    );
  }

  if (auth.auth_enabled && !auth.authenticated) {
    return <LoginGate />;
  }

  return (
    <div className="flex min-h-dvh w-full max-w-full min-w-0 flex-col overflow-x-clip">
      <TopBar />
      <DecisionLoopStrip />
      <main className="mx-auto w-full max-w-[1440px] min-w-0 flex-1 px-3.5 py-4 sm:px-6 sm:py-6">
        {error && (
          <div className="mb-5 flex items-center justify-between gap-3 rounded-xl border border-rose-500/40 bg-rose-500/15 px-4 py-3 text-xs text-rose-100">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0 text-rose-300" />
              <span>{error}</span>
            </div>
            <button
              type="button"
              onClick={clearError}
              className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg text-rose-200 hover:text-white md:min-h-0 md:min-w-0"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        {appliedDelta && (
          <div
            data-testid="dashboard-applied-delta-banner"
            className="mb-5 rounded-2xl border border-emerald-500/35 bg-gradient-to-r from-emerald-500/15 via-cyan-500/10 to-slate-900/90 px-4 py-3 text-xs text-emerald-100 shadow-lg shadow-emerald-950/20"
          >
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-2 font-mono text-[11px] font-bold">
                <span className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-400/40 bg-emerald-500/20 px-2.5 py-1 font-sans text-xs font-bold text-emerald-200">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-300" />
                  <span>{isAr ? "تم التطبيق على اللوحة" : "Applied to Dashboard"}</span>
                </span>
                <span dir="ltr" className="rounded-lg border border-slate-700/80 bg-slate-950/70 px-2.5 py-1 text-slate-200">
                  Risk Score: <span className="text-slate-400">{appliedDelta.beforeRiskScore}</span> →{" "}
                  <span className="text-emerald-300">{appliedDelta.afterRiskScore}</span>
                </span>
                <span dir="ltr" className="rounded-lg border border-slate-700/80 bg-slate-950/70 px-2.5 py-1 text-slate-200">
                  Exports at Risk: <span className="text-slate-400">{appliedDelta.beforeExportsAtRisk}</span> →{" "}
                  <span className="text-cyan-300">{appliedDelta.afterExportsAtRisk}</span>
                </span>
                <span dir="ltr" className="rounded-lg border border-slate-700/80 bg-slate-950/70 px-2.5 py-1 text-slate-200">
                  Coverage: <span className="text-slate-400">{appliedDelta.beforeCoveragePct.toFixed(1)}%</span> →{" "}
                  <span className="text-teal-300">{appliedDelta.afterCoveragePct.toFixed(1)}%</span>
                </span>
                <span dir="ltr" className="rounded-lg border border-slate-700/80 bg-slate-950/70 px-2.5 py-1 text-slate-200">
                  Understaffed Slots: <span className="text-slate-400">{appliedDelta.beforeUnderstaffedSlots}</span> →{" "}
                  <span className="text-amber-300">{appliedDelta.afterUnderstaffedSlots}</span>
                </span>
                {appliedDelta.workersAdded > 0 && (
                  <span className="rounded-lg border border-cyan-500/40 bg-cyan-500/15 px-2.5 py-1 text-cyan-200">
                    +{appliedDelta.workersAdded} {isAr ? "كوادر إسناد" : "Relief Staff"} ({appliedDelta.beforeWorkersCount} →{" "}
                    {appliedDelta.afterWorkersCount})
                  </span>
                )}
              </div>

              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => setActiveView("scope")}
                  className={`rounded-lg border px-2.5 py-1 text-[11px] font-semibold transition ${
                    activeView === "scope"
                      ? "border-cyan-500/40 bg-cyan-500/20 text-cyan-200"
                      : "border-slate-700/80 bg-slate-900/80 text-slate-300 hover:border-cyan-500/40 hover:text-white"
                  }`}
                >
                  {isAr ? "رادار المخاطر" : "Risk Radar"}
                </button>
                <button
                  type="button"
                  onClick={() => setActiveView("gantt")}
                  className={`rounded-lg border px-2.5 py-1 text-[11px] font-semibold transition ${
                    activeView === "gantt"
                      ? "border-cyan-500/40 bg-cyan-500/20 text-cyan-200"
                      : "border-slate-700/80 bg-slate-900/80 text-slate-300 hover:border-cyan-500/40 hover:text-white"
                  }`}
                >
                  {isAr ? "جانت المكابس" : "Press Gantt"}
                </button>
                <button
                  type="button"
                  onClick={() => setActiveView("workforce")}
                  className={`rounded-lg border px-2.5 py-1 text-[11px] font-semibold transition ${
                    activeView === "workforce"
                      ? "border-cyan-500/40 bg-cyan-500/20 text-cyan-200"
                      : "border-slate-700/80 bg-slate-900/80 text-slate-300 hover:border-cyan-500/40 hover:text-white"
                  }`}
                >
                  {isAr ? "العمالة والورديات" : "Workforce"}
                </button>
                <button
                  type="button"
                  data-testid="btn-dismiss-applied-delta"
                  onClick={clearAppliedDelta}
                  className="inline-flex h-7 w-7 items-center justify-center rounded-lg text-slate-400 transition hover:bg-slate-800 hover:text-white"
                  aria-label="Dismiss applied delta banner"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>

            {(isAr ? appliedDelta.ceilingNoteAr : appliedDelta.ceilingNoteEn) && (
              <div className="mt-2 rounded-xl border border-amber-500/35 bg-amber-500/15 px-3 py-1.5 text-[11px] text-amber-200">
                {isAr ? appliedDelta.ceilingNoteAr : appliedDelta.ceilingNoteEn}
              </div>
            )}
          </div>
        )}

        <div className="w-full max-w-full min-w-0">
          {activeView === "scope" && <ScopeView />}
          {activeView === "studio" && <DataStudioView />}
          {activeView === "console" && <TradeoffConsole />}
          {activeView === "gantt" && <ProductionGanttView />}
          {activeView === "financials" && <FinancialsView />}
          {activeView === "workforce" && <WorkforceView />}
        </div>
        <CopilotDrawer />
        <ExecutiveBriefModal />
        <HistoricalBacktestModal />
        <GuidedOnboardingModal />
        <QuickAddModal />
      </main>
      <footer className="border-t border-slate-800/70 px-4 pt-3 pb-24 text-center text-[11px] text-slate-500 lg:pb-3">
        {t.deterministicFooter}
      </footer>
    </div>
  );
}

export default function HomePage() {
  return (
    <AppProvider>
      <DashboardShell />
    </AppProvider>
  );
}
