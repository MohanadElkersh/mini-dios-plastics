"use client";

import React, { useEffect, useRef, useState } from "react";
import { Check, Pin, X } from "lucide-react";
import { COPY } from "@/lib/i18n";
import { useApp } from "@/lib/store";
import type { PinnedSlotId, PlantDataset, SolveResult, SolverConfig } from "@/lib/types";

interface PinScenarioButtonProps {
  customConfig?: SolverConfig;
  customResult?: SolveResult | null;
  customDataset?: PlantDataset | null;
  customLabel?: string;
  variant?: "default" | "copilot";
  testId?: string;
  className?: string;
}

export function PinScenarioButton({
  customConfig,
  customResult,
  customDataset,
  customLabel,
  variant = "default",
  testId = "btn-pin-scenario",
  className = "",
}: PinScenarioButtonProps) {
  const { lang, result, dataset, pinnedScenarios, pinScenario } = useApp();
  const t = COPY[lang];

  const [justPinned, setJustPinned] = useState(false);
  const [replaceOpen, setReplaceOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const effectiveResult = customResult !== undefined ? customResult : result;
  const effectiveDataset = customDataset !== undefined ? customDataset : dataset;
  const disabled = !effectiveResult || !effectiveDataset;
  const count = pinnedScenarios.length;

  useEffect(() => {
    if (!replaceOpen) return;
    const onDocClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setReplaceOpen(false);
      }
    };
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [replaceOpen]);

  const triggerPin = (replaceSlot?: PinnedSlotId) => {
    const slot = pinScenario({
      label: customLabel,
      replaceSlot,
      config: customConfig,
      result: effectiveResult ?? undefined,
      dataset: effectiveDataset ?? undefined,
    });
    if (slot) {
      setReplaceOpen(false);
      setJustPinned(true);
      setTimeout(() => setJustPinned(false), 1600);
    }
  };

  const handleClick = () => {
    if (disabled) return;
    if (count >= 3) {
      setReplaceOpen((prev) => !prev);
    } else {
      triggerPin();
    }
  };

  const baseLabel =
    variant === "copilot"
      ? `${t.pinForComparisonBtn} (${count}/3)`
      : `${t.pinScenarioBtn} (${count}/3)`;

  return (
    <div ref={containerRef} className={`relative inline-flex ${className}`}>
      <button
        type="button"
        data-testid={testId}
        disabled={disabled}
        onClick={handleClick}
        className={`inline-flex items-center justify-center gap-1.5 rounded-xl border px-3 py-2 text-xs font-semibold transition disabled:cursor-not-allowed disabled:opacity-40 ${
          justPinned
            ? "border-emerald-400/60 bg-emerald-500/20 text-emerald-200"
            : variant === "copilot"
            ? "border-indigo-500/40 bg-indigo-500/15 text-indigo-200 hover:border-indigo-400 hover:bg-indigo-500/25"
            : "border-cyan-500/40 bg-cyan-500/10 text-cyan-200 hover:border-cyan-400 hover:bg-cyan-500/20"
        }`}
      >
        {justPinned ? <Check className="h-3.5 w-3.5" /> : <Pin className="h-3.5 w-3.5" />}
        <span>{justPinned ? t.pinnedConfirmBadge : baseLabel}</span>
      </button>

      {replaceOpen && (
        <div
          data-testid="pin-replace-popover"
          className="absolute end-0 top-full z-40 mt-2 w-64 rounded-xl border border-slate-700 bg-[#0c1324] p-3 shadow-2xl shadow-black/60"
        >
          <div className="mb-2 flex items-start justify-between gap-2">
            <p className="text-[11px] font-medium leading-snug text-slate-300">
              {t.pinReplaceTitle}
            </p>
            <button
              type="button"
              onClick={() => setReplaceOpen(false)}
              className="text-slate-400 hover:text-white"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
          <div className="space-y-1.5">
            {(["A", "B", "C"] as const).map((slot) => {
              const existing = pinnedScenarios.find((p) => p.slot === slot);
              return (
                <button
                  key={slot}
                  type="button"
                  data-testid={`pin-replace-slot-${slot}`}
                  onClick={() => triggerPin(slot)}
                  className="flex w-full items-center justify-between gap-2 rounded-lg border border-slate-800 bg-slate-900/90 px-2.5 py-2 text-start text-xs text-slate-200 transition hover:border-cyan-500/50 hover:bg-cyan-500/10"
                >
                  <span className="inline-flex items-center gap-1.5 truncate">
                    <span className="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded bg-cyan-500/20 font-mono text-[10px] font-bold text-cyan-300">
                      {slot}
                    </span>
                    <span className="truncate font-medium">
                      {existing?.label ?? `${t.pinSlotLabel} ${slot}`}
                    </span>
                  </span>
                  <span className="shrink-0 text-[10px] text-cyan-400">
                    {lang === "ar" ? "استبدال" : "Replace"}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
