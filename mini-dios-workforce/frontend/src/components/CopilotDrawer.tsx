"use client";

import React, { useEffect, useState } from "react";
import {
  AlertCircle,
  Bot,
  CheckCircle2,
  Clock,
  Loader2,
  Scale,
  Search,
  Send,
  Sparkles,
  X,
} from "lucide-react";
import { askCopilotApi } from "@/lib/api";
import { convertCurrency, formatMoney } from "@/lib/format";
import { COPY } from "@/lib/i18n";
import { useApp } from "@/lib/store";
import type { CopilotResult } from "@/lib/types";
import { PinScenarioButton } from "./PinScenarioButton";

interface MessageItem {
  id: string;
  prompt: string;
  response?: CopilotResult;
  error?: string;
  applied?: boolean;
}

export function CopilotDrawer() {
  const {
    lang,
    currency,
    dataset,
    config,
    result,
    applyCopilotScenario,
    setActiveView,
    copilotOpen,
    setCopilotOpen,
    copilotDraftPrompt,
    setCopilotDraftPrompt,
  } = useApp();

  const t = COPY[lang];

  const [input, setInput] = useState("");
  const [isSimulating, setIsSimulating] = useState(false);

  useEffect(() => {
    if (copilotOpen && copilotDraftPrompt) {
      setInput(copilotDraftPrompt);
      setCopilotDraftPrompt(null);
    }
  }, [copilotOpen, copilotDraftPrompt, setCopilotDraftPrompt]);
  const [copilotError, setCopilotError] = useState<string | null>(null);
  const [messages, setMessages] = useState<MessageItem[]>([
    {
      id: "welcome",
      prompt: "System Ready",
      response: {
        reply:
          lang === "ar"
            ? "مساعد عمليات Mini-DIOS للبلاستيك جاهز لمحاكاة أي سيناريو مركّب عبر OR-Tools CP-SAT (أعطال ماكينات، نقص خامات، أوامر تصدير عاجلة، أو تحليل اختناقات). اختر أحد الأمثلة أو اكتب سؤالك."
            : "Mini-DIOS Plastics Operations Copilot is ready. Ask ANY multi-disruption what-if (breakdowns, resin shortages, rush export orders, strategy trade-offs, or mold bottlenecks) — 100% solved by OR-Tools CP-SAT.",
        action: "ready",
        tool_calls_executed: [],
        config,
        timing: { gemini_ms: 0, solver_ms: 0, total_ms: 0 },
        source: "system",
      },
    },
  ]);

  if (!copilotOpen) return null;

  const quickPrompts = [
    { label: t.chipBreakdown, prompt: t.chipBreakdown, testId: "copilot-chip-breakdown" },
    { label: t.chipResin, prompt: t.chipResin, testId: "copilot-chip-resin" },
    { label: t.chipRush, prompt: t.chipRush, testId: "copilot-chip-rush" },
    { label: t.chipCompare, prompt: t.chipCompare, testId: "copilot-chip-compare" },
    { label: t.chipBottleneck, prompt: t.chipBottleneck, testId: "copilot-chip-bottleneck" },
    { label: t.chipWorkforceCallout, prompt: t.chipWorkforceCallout, testId: "copilot-chip-workforce" },
  ];

  const handleSubmit = async (promptText: string) => {
    const trimmed = promptText.trim();
    if (!trimmed || isSimulating) return;

    setIsSimulating(true);
    setCopilotError(null);

    try {
      const res = await askCopilotApi(trimmed, dataset, config, result, lang);
      setMessages((prev) => [
        ...prev,
        { id: `${Date.now()}`, prompt: trimmed, response: res, applied: false },
      ]);
      setInput("");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Simulation request failed.";
      setCopilotError(msg);
      setMessages((prev) => [...prev, { id: `${Date.now()}`, prompt: trimmed, error: msg }]);
    } finally {
      setIsSimulating(false);
    }
  };

  const handleApply = (msgId: string, res: CopilotResult) => {
    applyCopilotScenario(res.config, res.result);
    setMessages((prev) => prev.map((m) => (m.id === msgId ? { ...m, applied: true } : m)));
    if (res.result?.workforce?.callouts_applied && res.result.workforce.callouts_applied.length > 0) {
      setActiveView("workforce");
    } else {
      setActiveView("gantt");
    }
  };

  const fmtCur = (amount: number, res: CopilotResult) => {
    const fromCur = res.result?.currency ?? currency;
    const fx = res.result?.fx_egp_per_sar ?? 13.0;
    return formatMoney(convertCurrency(amount, fromCur, currency, fx), currency);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-end bg-black/65 backdrop-blur-sm md:items-stretch">
      <div
        data-testid="copilot-drawer"
        className="flex h-[92dvh] max-h-[92dvh] w-full flex-col overflow-hidden rounded-t-3xl border-t border-slate-800 bg-[#070b14] shadow-2xl md:h-dvh md:max-h-dvh md:max-w-xl md:rounded-none md:border-s md:border-t-0"
        role="dialog"
        aria-modal="true"
      >
        {/* Header */}
        <div className="flex shrink-0 items-center justify-between border-b border-slate-800 px-4 py-3.5 sm:px-5 sm:py-4">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-tr from-cyan-500 to-indigo-500 text-slate-950 shadow-md shadow-cyan-500/20">
              <Sparkles className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h2 className="truncate text-sm font-bold text-white">{t.copilotTitle}</h2>
                <span className="shrink-0 rounded-full border border-cyan-500/30 bg-cyan-500/10 px-2 py-0.5 text-[10px] font-semibold text-cyan-300">
                  3 Tools • CP-SAT
                </span>
              </div>
              <p className="truncate text-[11px] text-slate-400">{t.copilotSubtitle}</p>
            </div>
          </div>
          <button
            type="button"
            data-testid="btn-close-copilot"
            onClick={() => setCopilotOpen(false)}
            className="inline-flex min-h-[44px] min-w-[44px] shrink-0 items-center justify-center rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-800 hover:text-white md:min-h-0 md:min-w-0"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Starter Chips (Single-row scroll strip on mobile, wrapped on desktop) */}
        <div className="shrink-0 border-b border-slate-800/80 bg-slate-950/60 px-4 py-2.5 sm:px-5 sm:py-3">
          <div className="mb-1.5 text-[11px] font-semibold text-slate-400">{t.copilotQuickPrompts}</div>
          <div className="no-scrollbar flex flex-nowrap gap-1.5 overflow-x-auto snap-x whitespace-nowrap pb-0.5 md:flex-wrap md:overflow-visible md:whitespace-normal">
            {quickPrompts.map((qp, idx) => (
              <button
                key={idx}
                type="button"
                data-testid={qp.testId}
                disabled={isSimulating}
                onClick={() => void handleSubmit(qp.prompt)}
                className="min-h-[36px] shrink-0 snap-start rounded-lg border border-slate-700/80 bg-slate-900/90 px-2.5 py-1 text-[11px] font-medium text-slate-300 transition hover:border-cyan-500/50 hover:bg-slate-800 hover:text-white disabled:opacity-50 md:min-h-0"
              >
                {qp.label}
              </button>
            ))}
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 space-y-4 overflow-y-auto p-4 sm:p-5">
          {copilotError && (
            <div className="flex items-start gap-2.5 rounded-xl border border-rose-500/40 bg-rose-500/15 p-3 text-xs text-rose-200">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-300" />
              <span>{copilotError}</span>
            </div>
          )}

          {messages.map((m) => (
            <div key={m.id} className="space-y-2">
              {m.prompt !== "System Ready" && (
                <div className="flex justify-end">
                  <div className="max-w-[85%] rounded-2xl rounded-te-sm border border-cyan-500/30 bg-cyan-600/20 px-3.5 py-2 text-xs font-medium text-cyan-100">
                    {m.prompt}
                  </div>
                </div>
              )}

              {m.response && (
                <div className="flex items-start gap-2.5">
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-indigo-500/30 bg-indigo-500/20 text-indigo-300">
                    <Bot className="h-4 w-4" />
                  </div>
                  <div className="min-w-0 flex-1 space-y-2.5 rounded-2xl rounded-ts-sm border border-slate-800 bg-[#0f1629] p-3.5 text-xs">
                    <p className="leading-relaxed text-slate-200">
                      {m.response.reply.split(/(\*\*[^*]+\*\*)/g).map((part, pi) =>
                        part.startsWith("**") && part.endsWith("**") ? (
                          <strong key={pi} className="font-bold text-white">
                            {part.slice(2, -2)}
                          </strong>
                        ) : (
                          <React.Fragment key={pi}>{part}</React.Fragment>
                        )
                      )}
                    </p>

                    {/* Bottleneck Insight Card */}
                    {m.response.bottleneck && (
                      <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 space-y-1.5">
                        <div className="flex items-center gap-1.5 font-bold text-amber-200">
                          <Search className="h-3.5 w-3.5" />
                          <span>{m.response.bottleneck.headline}</span>
                        </div>
                        <ul className="list-disc space-y-1 ps-4 text-[11px] text-slate-200">
                          {m.response.bottleneck.facts.map((f, fi) => (
                            <li key={fi}>{f}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Strategy Comparison Table */}
                    {m.response.comparison && (
                      <div className="overflow-hidden rounded-xl border border-slate-700/80 bg-slate-950/70">
                        <div className="flex items-center gap-1.5 border-b border-slate-800 bg-slate-900 px-3 py-2 text-[11px] font-bold text-cyan-300">
                          <Scale className="h-3.5 w-3.5" />
                          <span>
                            {m.response.comparison.strategy_a_name} vs. {m.response.comparison.strategy_b_name}
                          </span>
                        </div>
                        <table className="w-full text-[11px]">
                          <thead>
                            <tr className="border-b border-slate-800 text-slate-400">
                              <th className="px-2.5 py-1.5 text-start">Metric</th>
                              <th className="px-2 py-1.5 text-end">A</th>
                              <th className="px-2 py-1.5 text-end">B</th>
                              <th className="px-2.5 py-1.5 text-end">Delta</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-800/60 font-mono">
                            {m.response.comparison.rows.map((row, ri) => (
                              <tr key={ri}>
                                <td className="px-2.5 py-1.5 font-sans text-slate-300">{row.metric}</td>
                                <td className="px-2 py-1.5 text-end text-slate-200">{row.strategy_a}</td>
                                <td className="px-2 py-1.5 text-end text-cyan-200">{row.strategy_b}</td>
                                <td className="px-2.5 py-1.5 text-end text-amber-300">{row.delta}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}

                    {/* Simulation KPI Preview */}
                    {m.response.result?.scorecard && (
                      <div className="grid grid-cols-2 gap-2 rounded-xl border border-slate-800/80 bg-slate-950/60 p-2.5 text-[11px]">
                        <div>
                          <span className="text-slate-400">Cash Saved vs FIFO:</span>{" "}
                          <span className="font-mono font-bold text-emerald-300">
                            {fmtCur(m.response.result.scorecard.cash_savings, m.response)}
                          </span>
                        </div>
                        <div>
                          <span className="text-slate-400">Purge Scrap:</span>{" "}
                          <span className="font-mono font-bold text-cyan-300">
                            {m.response.result.optimized.kpis.purge_scrap_kg.toFixed(1)} kg
                          </span>
                        </div>
                        <div>
                          <span className="text-slate-400">OTIF / OEE:</span>{" "}
                          <span className="font-mono font-bold text-indigo-300">
                            {m.response.result.optimized.kpis.otif_pct.toFixed(1)}% /{" "}
                            {m.response.result.optimized.kpis.oee_pct.toFixed(1)}%
                          </span>
                        </div>
                        <div>
                          <span className="text-slate-400">Changeover:</span>{" "}
                          <span className="font-mono font-bold text-amber-300">
                            {m.response.result.optimized.kpis.changeover_hours.toFixed(2)}h
                          </span>
                        </div>
                      </div>
                    )}

                    {/* Apply Scenario to Dashboard + Pin for Comparison CTAs */}
                    {m.response.action !== "ready" && m.response.result && (
                      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                        <button
                          type="button"
                          data-testid="btn-apply-copilot-scenario"
                          onClick={() => handleApply(m.id, m.response!)}
                          className={`inline-flex w-full items-center justify-center gap-2 rounded-xl px-3 py-2 text-xs font-bold transition ${
                            m.applied
                              ? "border border-emerald-500/40 bg-emerald-500/15 text-emerald-300"
                              : "bg-cyan-500 text-slate-950 hover:bg-cyan-400"
                          }`}
                        >
                          <CheckCircle2 className="h-4 w-4 shrink-0" />
                          <span className="truncate">{m.applied ? t.copilotAppliedBadge : t.copilotApplyBtn}</span>
                        </button>
                        <PinScenarioButton
                          variant="copilot"
                          testId="btn-pin-copilot-scenario"
                          customConfig={m.response.config}
                          customResult={m.response.result}
                          customDataset={dataset}
                          className="w-full [&>button]:w-full"
                        />
                      </div>
                    )}

                    {/* Timing Bar */}
                    <div className="flex flex-wrap items-center gap-2 border-t border-slate-800/60 pt-1.5 font-mono text-[10px] text-slate-400">
                      <span className="inline-flex items-center gap-1">
                        <Clock className="h-3 w-3 text-amber-400" />
                        Total: {m.response.timing.total_ms}ms
                      </span>
                      <span>•</span>
                      <span>Gemini: {m.response.timing.gemini_ms}ms</span>
                      <span>•</span>
                      <span>CP-SAT: {m.response.timing.solver_ms}ms</span>
                      <span>•</span>
                      <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[9px] uppercase text-slate-300">
                        {m.response.source}
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}

          {isSimulating && (
            <div className="flex items-center gap-3 rounded-2xl border border-cyan-500/30 bg-cyan-500/10 p-4 text-xs text-cyan-200">
              <Loader2 className="h-5 w-5 animate-spin text-cyan-400" />
              <div>
                <div className="font-semibold">{t.copilotSimulating}</div>
                <div className="text-[11px] text-cyan-300/80">
                  Constructing composable parameters & solving deterministic OR-Tools CP-SAT...
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Sticky Bottom Free-Text Input Bar */}
        <div className="sticky bottom-0 shrink-0 border-t border-slate-800 bg-slate-950/95 p-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] sm:p-4 md:pb-4">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void handleSubmit(input);
            }}
            className="flex items-center gap-2"
          >
            <input
              type="text"
              data-testid="copilot-input"
              disabled={isSimulating}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={t.copilotPlaceholder}
              className="min-h-[44px] flex-1 rounded-xl border border-slate-700 bg-slate-900 px-3.5 py-2.5 text-base text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500 disabled:opacity-50 md:min-h-0 md:text-xs"
            />
            <button
              type="submit"
              data-testid="copilot-submit"
              disabled={!input.trim() || isSimulating}
              className="inline-flex min-h-[44px] shrink-0 items-center gap-1.5 rounded-xl bg-cyan-500 px-4 py-2.5 text-xs font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-40 md:min-h-0"
            >
              {isSimulating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              <span>{t.copilotSend}</span>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
