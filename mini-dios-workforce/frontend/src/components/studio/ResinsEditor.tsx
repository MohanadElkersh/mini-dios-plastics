"use client";

import React, { useState } from "react";
import { Edit3, Plus, Trash2, X } from "lucide-react";
import { COPY } from "@/lib/i18n";
import { useApp } from "@/lib/store";
import type { ResinCode, ResinStock } from "@/lib/types";
import { ConfirmDeleteModal } from "./ConfirmDeleteModal";

const ALL_RESIN_CODES: ResinCode[] = ["PP", "HDPE", "LDPE", "PET", "ABS", "PVC"];

export function ResinsEditor() {
  const { lang, dataset, config, upsertResin, deleteResin } = useApp();
  const t = COPY[lang];
  const resins = dataset?.resins ?? [];
  const orders = dataset?.orders ?? [];
  const rushOrders = config.scenarios.rush_orders ?? [];

  const [editing, setEditing] = useState<{ resin: ResinStock; originalCode?: ResinCode } | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<ResinStock | null>(null);

  const usedCodes = new Set(resins.map((r) => r.resin_code));
  const availableNewCodes = ALL_RESIN_CODES.filter((c) => !usedCodes.has(c));

  const openNew = () => {
    const code = availableNewCodes[0] ?? "PVC";
    setEditing({
      resin: {
        resin_code: code,
        virgin_available_kg: 5000,
        virgin_cost_per_kg: 5.5,
        regrind_available_kg: 500,
        regrind_cost_per_kg: 3.0,
        drying_lead_time_hrs: code === "PET" || code === "ABS" ? 6 : 0,
        barrel_temp_c: code === "PET" ? 275 : 210,
      },
    });
  };

  const openEdit = (r: ResinStock) => {
    setEditing({ resin: { ...r }, originalCode: r.resin_code });
  };

  const getReferences = (code: ResinCode): string[] => {
    return [...orders, ...rushOrders]
      .filter((o) => o.resin_code === code)
      .map((o) => `Order ${o.order_id} (${o.sku_name})`);
  };

  const saveModal = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editing) return;
    upsertResin(editing.resin, editing.originalCode);
    setEditing(null);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-slate-400">
          {resins.length} {lang === "ar" ? "خامات مسجلة" : "resin grades configured"}
        </p>
        <button
          type="button"
          data-testid="btn-add-resin"
          onClick={openNew}
          disabled={availableNewCodes.length === 0}
          className="inline-flex items-center gap-1.5 rounded-xl bg-cyan-500 px-3.5 py-2 text-xs font-bold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Plus className="h-3.5 w-3.5" />
          <span>{t.studioAddResin}</span>
        </button>
      </div>

      <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-[#0f1629]">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-slate-800 bg-slate-900/60 text-slate-400">
              <th className="px-3 py-2.5 text-start">Resin</th>
              <th className="px-3 py-2.5 text-end">Virgin Stock (kg)</th>
              <th className="px-3 py-2.5 text-end">Virgin Price (SAR/kg)</th>
              <th className="px-3 py-2.5 text-end">Regrind Stock (kg)</th>
              <th className="px-3 py-2.5 text-end">Regrind Price (SAR/kg)</th>
              <th className="px-3 py-2.5 text-end">Drying Lead (h)</th>
              <th className="px-3 py-2.5 text-end">Barrel Temp (°C)</th>
              <th className="px-3 py-2.5 text-end">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/70">
            {resins.map((r) => (
              <tr key={r.resin_code} data-testid={`resin-row-${r.resin_code}`} className="hover:bg-slate-900/40">
                <td className="px-3 py-2.5 font-mono font-bold text-cyan-300">{r.resin_code}</td>
                <td dir="ltr" className="px-3 py-2.5 text-end font-mono text-white">
                  {r.virgin_available_kg.toLocaleString()} kg
                </td>
                <td dir="ltr" className="px-3 py-2.5 text-end font-mono text-emerald-300">
                  {r.virgin_cost_per_kg.toFixed(2)}
                </td>
                <td dir="ltr" className="px-3 py-2.5 text-end font-mono text-slate-300">
                  {r.regrind_available_kg.toLocaleString()} kg
                </td>
                <td dir="ltr" className="px-3 py-2.5 text-end font-mono text-slate-300">
                  {r.regrind_cost_per_kg.toFixed(2)}
                </td>
                <td dir="ltr" className="px-3 py-2.5 text-end font-mono text-amber-300">
                  {r.drying_lead_time_hrs}h
                </td>
                <td dir="ltr" className="px-3 py-2.5 text-end font-mono text-slate-300">
                  {r.barrel_temp_c}°C
                </td>
                <td className="px-3 py-2.5 text-end">
                  <div className="inline-flex items-center gap-1">
                    <button
                      type="button"
                      data-testid={`edit-resin-${r.resin_code}`}
                      onClick={() => openEdit(r)}
                      className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-cyan-300"
                    >
                      <Edit3 className="h-3.5 w-3.5" />
                    </button>
                    <button
                      type="button"
                      data-testid={`del-resin-${r.resin_code}`}
                      onClick={() => setDeleteTarget(r)}
                      className="rounded-lg p-1.5 text-slate-400 hover:bg-rose-500/20 hover:text-rose-300"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Add / Edit Resin Modal */}
      {editing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <form
            onSubmit={saveModal}
            className="w-full max-w-lg rounded-2xl border border-slate-700 bg-[#0f1629] p-5 shadow-2xl"
          >
            <div className="mb-4 flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-white">
                {editing.originalCode ? `${t.studioEdit}: ${editing.originalCode}` : t.studioAddResin}
              </h3>
              <button
                type="button"
                onClick={() => setEditing(null)}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <label className="space-y-1 text-xs sm:col-span-2">
                <span className="text-slate-400">Resin Code</span>
                <select
                  disabled={Boolean(editing.originalCode)}
                  value={editing.resin.resin_code}
                  onChange={(e) =>
                    setEditing({
                      ...editing,
                      resin: { ...editing.resin, resin_code: e.target.value as ResinCode },
                    })
                  }
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-white disabled:opacity-60"
                >
                  {(editing.originalCode ? ALL_RESIN_CODES : availableNewCodes).map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </label>

              <label className="space-y-1 text-xs">
                <span className="text-slate-400">Virgin Available (kg)</span>
                <input
                  type="number"
                  step="10"
                  min={0}
                  required
                  value={editing.resin.virgin_available_kg}
                  onChange={(e) =>
                    setEditing({
                      ...editing,
                      resin: { ...editing.resin, virgin_available_kg: Number(e.target.value) },
                    })
                  }
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-white"
                />
              </label>
              <label className="space-y-1 text-xs">
                <span className="text-slate-400">Virgin Cost (SAR/kg)</span>
                <input
                  type="number"
                  step="0.05"
                  min={0.1}
                  required
                  data-testid="input-resin-virgin-cost"
                  value={editing.resin.virgin_cost_per_kg}
                  onChange={(e) =>
                    setEditing({
                      ...editing,
                      resin: { ...editing.resin, virgin_cost_per_kg: Number(e.target.value) },
                    })
                  }
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-white"
                />
              </label>

              <label className="space-y-1 text-xs">
                <span className="text-slate-400">Regrind Available (kg)</span>
                <input
                  type="number"
                  step="10"
                  min={0}
                  required
                  value={editing.resin.regrind_available_kg}
                  onChange={(e) =>
                    setEditing({
                      ...editing,
                      resin: { ...editing.resin, regrind_available_kg: Number(e.target.value) },
                    })
                  }
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-white"
                />
              </label>
              <label className="space-y-1 text-xs">
                <span className="text-slate-400">Regrind Cost (SAR/kg)</span>
                <input
                  type="number"
                  step="0.05"
                  min={0}
                  required
                  value={editing.resin.regrind_cost_per_kg}
                  onChange={(e) =>
                    setEditing({
                      ...editing,
                      resin: { ...editing.resin, regrind_cost_per_kg: Number(e.target.value) },
                    })
                  }
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-white"
                />
              </label>

              <label className="space-y-1 text-xs">
                <span className="text-slate-400">Drying Lead Time (hrs, 0–48)</span>
                <input
                  type="number"
                  step="0.5"
                  min={0}
                  max={48}
                  required
                  value={editing.resin.drying_lead_time_hrs}
                  onChange={(e) =>
                    setEditing({
                      ...editing,
                      resin: { ...editing.resin, drying_lead_time_hrs: Number(e.target.value) },
                    })
                  }
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-white"
                />
              </label>
              <label className="space-y-1 text-xs">
                <span className="text-slate-400">Barrel Temp (°C, 120–360)</span>
                <input
                  type="number"
                  min={120}
                  max={360}
                  required
                  value={editing.resin.barrel_temp_c}
                  onChange={(e) =>
                    setEditing({
                      ...editing,
                      resin: { ...editing.resin, barrel_temp_c: Number(e.target.value) },
                    })
                  }
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-white"
                />
              </label>
            </div>

            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setEditing(null)}
                className="rounded-lg border border-slate-700 bg-slate-900 px-3.5 py-2 text-xs font-semibold text-slate-300"
              >
                {t.studioCancel}
              </button>
              <button
                type="submit"
                data-testid="save-resin-btn"
                className="rounded-lg bg-cyan-500 px-4 py-2 text-xs font-bold text-slate-950 hover:bg-cyan-400"
              >
                {t.studioSave}
              </button>
            </div>
          </form>
        </div>
      )}

      <ConfirmDeleteModal
        lang={lang}
        open={deleteTarget !== null}
        entityLabel={deleteTarget ? `Resin ${deleteTarget.resin_code}` : ""}
        references={deleteTarget ? getReferences(deleteTarget.resin_code) : []}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={() => {
          if (deleteTarget) deleteResin(deleteTarget.resin_code);
          setDeleteTarget(null);
        }}
      />
    </div>
  );
}
