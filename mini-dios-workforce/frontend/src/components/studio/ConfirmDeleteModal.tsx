"use client";

import React from "react";
import { AlertTriangle, Trash2, X } from "lucide-react";
import { COPY } from "@/lib/i18n";
import type { Lang } from "@/lib/types";

interface ConfirmDeleteModalProps {
  lang: Lang;
  open: boolean;
  entityLabel: string;
  references: string[];
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDeleteModal({
  lang,
  open,
  entityLabel,
  references,
  onConfirm,
  onCancel,
}: ConfirmDeleteModalProps) {
  if (!open) return null;
  const t = COPY[lang];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
      <div
        role="dialog"
        aria-modal="true"
        className="w-full max-w-md rounded-2xl border border-rose-500/40 bg-[#0f1629] p-5 shadow-2xl"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-rose-500/20 text-rose-300">
              <AlertTriangle className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white">{t.studioConfirmDeleteTitle}</h3>
              <p className="text-xs text-slate-400">{entityLabel}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onCancel}
            className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="mt-4 space-y-2 text-xs text-slate-300">
          {references.length > 0 ? (
            <>
              <p className="font-medium text-amber-200">{t.studioConfirmDeleteMsg}</p>
              <ul className="max-h-40 space-y-1 overflow-y-auto rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-[11px] text-amber-100">
                {references.map((ref, idx) => (
                  <li key={idx} className="font-mono">
                    • {ref}
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <p className="text-slate-300">
              {lang === "ar"
                ? `هل تريد حذف ${entityLabel} نهائياً؟`
                : `Are you sure you want to delete ${entityLabel}?`}
            </p>
          )}
        </div>

        <div className="mt-5 flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-semibold text-slate-300 hover:text-white"
          >
            {t.studioCancel}
          </button>
          <button
            type="button"
            data-testid="confirm-delete-btn"
            onClick={onConfirm}
            className="inline-flex items-center gap-1.5 rounded-lg bg-rose-500 px-3.5 py-1.5 text-xs font-bold text-white hover:bg-rose-400"
          >
            <Trash2 className="h-3.5 w-3.5" />
            <span>{t.studioConfirmDeleteBtn}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
