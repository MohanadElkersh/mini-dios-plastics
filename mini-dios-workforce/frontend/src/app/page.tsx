"use client";

import React from "react";
import { AlertCircle, Factory, Loader2, X } from "lucide-react";
import { CopilotDrawer } from "@/components/CopilotDrawer";
import { DataStudioView } from "@/components/DataStudioView";
import { DecisionLoopStrip } from "@/components/DecisionLoopStrip";
import { ExecutiveBriefModal } from "@/components/ExecutiveBriefModal";
import { FinancialsView } from "@/components/FinancialsView";
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
  const { lang, activeView, error, clearError, auth, authChecked } = useApp();
  const t = COPY[lang];

  if (!authChecked) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-[#060a13] text-slate-300">
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
    <div className="flex min-h-screen flex-col">
      <TopBar />
      <DecisionLoopStrip />
      <main className="mx-auto w-full max-w-[1440px] flex-1 px-4 py-6 sm:px-6">
        {error && (
          <div className="mb-5 flex items-center justify-between gap-3 rounded-xl border border-rose-500/40 bg-rose-500/15 px-4 py-3 text-xs text-rose-100">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0 text-rose-300" />
              <span>{error}</span>
            </div>
            <button type="button" onClick={clearError} className="text-rose-200 hover:text-white">
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        {activeView === "scope" && <ScopeView />}
        {activeView === "studio" && <DataStudioView />}
        {activeView === "console" && <TradeoffConsole />}
        {activeView === "gantt" && <ProductionGanttView />}
        {activeView === "financials" && <FinancialsView />}
        {activeView === "workforce" && <WorkforceView />}
        <CopilotDrawer />
        <ExecutiveBriefModal />
        <QuickAddModal />
      </main>
      <footer className="border-t border-slate-800/70 py-3 text-center text-[11px] text-slate-500">
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
