"use client";

import React, { useState } from "react";
import { Copy, Edit3, Flame, Plus, Trash2, X } from "lucide-react";
import { COPY } from "@/lib/i18n";
import { useApp } from "@/lib/store";
import type { Mold } from "@/lib/types";
import { ConfirmDeleteModal } from "./ConfirmDeleteModal";

const EMPTY_MOLD: Mold = {
  mold_id: "",
  name: "",
  compatible_machines: [],
  cavities: 4,
  cycle_time_sec: 15,
  is_hot_runner: true,
  base_changeover_mins: 90,
  current_shots: 50000,
  maintenance_interval_shots: 500000,
  pm_duration_hrs: 4,
};

function ShotHealthBar({ current, interval }: { current: number; interval: number }) {
  const pct = Math.min(100, Math.round((current / Math.max(interval, 1)) * 1000) / 10);
  const barCls = pct >= 95 ? "bg-rose-500" : pct >= 80 ? "bg-amber-400" : "bg-emerald-400";
  const textCls = pct >= 95 ? "text-rose-300" : pct >= 80 ? "text-amber-300" : "text-emerald-300";

  return (
    <div className="min-w-[120px] space-y-1">
      <div className="flex items-center justify-between font-mono text-[10px]">
        <span className="text-slate-400">
          {current.toLocaleString()} / {interval.toLocaleString()}
        </span>
        <span className={`font-bold ${textCls}`}>{pct.toFixed(1)}%</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
        <div className={`h-full transition-all ${barCls}`} style={{ width: `${Math.min(100, pct)}%` }} />
      </div>
    </div>
  );
}

export function MoldsEditor() {
  const { lang, dataset, config, upsertMold, deleteMold } = useApp();
  const t = COPY[lang];
  const presses = dataset?.presses ?? [];
  const molds = dataset?.molds ?? [];
  const orders = dataset?.orders ?? [];
  const rushOrders = config.scenarios.rush_orders ?? [];

  const [editing, setEditing] = useState<{ mold: Mold; originalId?: string } | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Mold | null>(null);

  const openNew = () => {
    const idx = molds.length + 1;
    setEditing({
      mold: {
        ...EMPTY_MOLD,
        mold_id: `M-${String(idx).padStart(2, "0")}`,
        name: `New Mold ${idx}`,
        compatible_machines: presses.slice(0, 1).map((p) => p.machine_id),
      },
    });
  };

  const openEdit = (m: Mold) => {
    setEditing({
      mold: { ...m, compatible_machines: [...m.compatible_machines] },
      originalId: m.mold_id,
    });
  };

  const duplicateMold = (m: Mold) => {
    let idx = 2;
    let candidate = `${m.mold_id}-C`;
    while (molds.some((x) => x.mold_id === candidate)) {
      candidate = `${m.mold_id}-C${idx++}`;
    }
    upsertMold({
      ...m,
      mold_id: candidate,
      name: `${m.name} (Copy)`,
      compatible_machines: [...m.compatible_machines],
    });
  };

  const getReferences = (moldId: string): string[] => {
    return [...orders, ...rushOrders]
      .filter((o) => o.mold_id === moldId)
      .map((o) => `Order ${o.order_id} (${o.sku_name})`);
  };

  const toggleMachine = (mid: string) => {
    if (!editing) return;
    const curr = editing.mold.compatible_machines;
    const next = curr.includes(mid) ? curr.filter((x) => x !== mid) : [...curr, mid];
    setEditing({ ...editing, mold: { ...editing.mold, compatible_machines: next } });
  };

  const saveModal = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editing) return;
    const cleanId = editing.mold.mold_id.trim();
    if (!cleanId) return;
    upsertMold(
      {
        ...editing.mold,
        mold_id: cleanId,
        name: editing.mold.name.trim() || cleanId,
      },
      editing.originalId
    );
    setEditing(null);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-slate-400">
          {molds.length} {lang === "ar" ? "قالب مسجل" : "physical molds configured"}
        </p>
        <button
          type="button"
          data-testid="btn-add-mold"
          onClick={openNew}
          className="inline-flex items-center gap-1.5 rounded-xl bg-cyan-500 px-3.5 py-2 text-xs font-bold text-slate-950 transition hover:bg-cyan-400"
        >
          <Plus className="h-3.5 w-3.5" />
          <span>{t.studioAddMold}</span>
        </button>
      </div>

      <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-[#0f1629]">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-slate-800 bg-slate-900/60 text-slate-400">
              <th className="px-3 py-2.5 text-start">Mold ID</th>
              <th className="px-3 py-2.5 text-start">Name</th>
              <th className="px-3 py-2.5 text-start">Compatible Presses</th>
              <th className="px-3 py-2.5 text-end">Cavities</th>
              <th className="px-3 py-2.5 text-end">Cycle (s)</th>
              <th className="px-3 py-2.5 text-center">Runner</th>
              <th className="px-3 py-2.5 text-end">Setup (m)</th>
              <th className="px-3 py-2.5 text-start">Shot-Count Health</th>
              <th className="px-3 py-2.5 text-end">PM (h)</th>
              <th className="px-3 py-2.5 text-end">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/70">
            {molds.map((m) => (
              <tr key={m.mold_id} data-testid={`mold-row-${m.mold_id}`} className="hover:bg-slate-900/40">
                <td className="px-3 py-2.5 font-mono font-bold text-cyan-300">{m.mold_id}</td>
                <td className="px-3 py-2.5 font-medium text-white">{m.name}</td>
                <td className="px-3 py-2.5">
                  <div className="flex flex-wrap gap-1">
                    {m.compatible_machines.length === 0 ? (
                      <span className="text-rose-400">None</span>
                    ) : (
                      m.compatible_machines.map((mid) => (
                        <span key={mid} className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-[10px] text-slate-200">
                          {mid}
                        </span>
                      ))
                    )}
                  </div>
                </td>
                <td dir="ltr" className="px-3 py-2.5 text-end font-mono text-slate-200">
                  {m.cavities}
                </td>
                <td dir="ltr" className="px-3 py-2.5 text-end font-mono text-slate-200">
                  {m.cycle_time_sec}s
                </td>
                <td className="px-3 py-2.5 text-center">
                  {m.is_hot_runner ? (
                    <span className="inline-flex items-center gap-1 rounded bg-cyan-500/15 px-2 py-0.5 text-[10px] font-bold text-cyan-300">
                      <Flame className="h-3 w-3" /> HR
                    </span>
                  ) : (
                    <span className="text-[11px] text-slate-400">CR</span>
                  )}
                </td>
                <td dir="ltr" className="px-3 py-2.5 text-end font-mono text-slate-300">
                  {m.base_changeover_mins}m
                </td>
                <td className="px-3 py-2.5">
                  <ShotHealthBar current={m.current_shots} interval={m.maintenance_interval_shots} />
                </td>
                <td dir="ltr" className="px-3 py-2.5 text-end font-mono text-slate-300">
                  {m.pm_duration_hrs}h
                </td>
                <td className="px-3 py-2.5 text-end">
                  <div className="inline-flex items-center gap-1">
                    <button
                      type="button"
                      data-testid={`edit-mold-${m.mold_id}`}
                      onClick={() => openEdit(m)}
                      className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-cyan-300"
                    >
                      <Edit3 className="h-3.5 w-3.5" />
                    </button>
                    <button
                      type="button"
                      data-testid={`dup-mold-${m.mold_id}`}
                      onClick={() => duplicateMold(m)}
                      className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-indigo-300"
                    >
                      <Copy className="h-3.5 w-3.5" />
                    </button>
                    <button
                      type="button"
                      data-testid={`del-mold-${m.mold_id}`}
                      onClick={() => setDeleteTarget(m)}
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

      {/* Add / Edit Mold Modal */}
      {editing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <form
            onSubmit={saveModal}
            className="max-h-[90vh] w-full max-w-xl overflow-y-auto rounded-2xl border border-slate-700 bg-[#0f1629] p-5 shadow-2xl"
          >
            <div className="mb-4 flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-white">
                {editing.originalId ? `${t.studioEdit}: ${editing.originalId}` : t.studioAddMold}
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
              <label className="space-y-1 text-xs">
                <span className="text-slate-400">Mold ID</span>
                <input
                  required
                  value={editing.mold.mold_id}
                  onChange={(e) => setEditing({ ...editing, mold: { ...editing.mold, mold_id: e.target.value } })}
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-white"
                />
              </label>
              <label className="space-y-1 text-xs">
                <span className="text-slate-400">Name</span>
                <input
                  required
                  value={editing.mold.name}
                  onChange={(e) => setEditing({ ...editing, mold: { ...editing.mold, name: e.target.value } })}
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-white"
                />
              </label>
              <label className="space-y-1 text-xs">
                <span className="text-slate-400">Cavities</span>
                <input
                  type="number"
                  min={1}
                  required
                  value={editing.mold.cavities}
                  onChange={(e) =>
                    setEditing({ ...editing, mold: { ...editing.mold, cavities: Number(e.target.value) } })
                  }
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-white"
                />
              </label>
              <label className="space-y-1 text-xs">
                <span className="text-slate-400">Cycle Time (sec)</span>
                <input
                  type="number"
                  step="0.1"
                  min={0.5}
                  required
                  value={editing.mold.cycle_time_sec}
                  onChange={(e) =>
                    setEditing({ ...editing, mold: { ...editing.mold, cycle_time_sec: Number(e.target.value) } })
                  }
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-white"
                />
              </label>
              <label className="space-y-1 text-xs">
                <span className="text-slate-400">Base Changeover (mins, 15–480)</span>
                <input
                  type="number"
                  min={15}
                  max={480}
                  required
                  value={editing.mold.base_changeover_mins}
                  onChange={(e) =>
                    setEditing({
                      ...editing,
                      mold: { ...editing.mold, base_changeover_mins: Number(e.target.value) },
                    })
                  }
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-white"
                />
              </label>
              <label className="space-y-1 text-xs">
                <span className="text-slate-400">PM Duration (hrs)</span>
                <input
                  type="number"
                  step="0.5"
                  min={0.5}
                  max={72}
                  required
                  value={editing.mold.pm_duration_hrs}
                  onChange={(e) =>
                    setEditing({ ...editing, mold: { ...editing.mold, pm_duration_hrs: Number(e.target.value) } })
                  }
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-white"
                />
              </label>
              <label className="space-y-1 text-xs">
                <span className="text-slate-400">Current Shots</span>
                <input
                  type="number"
                  min={0}
                  required
                  value={editing.mold.current_shots}
                  onChange={(e) =>
                    setEditing({ ...editing, mold: { ...editing.mold, current_shots: Number(e.target.value) } })
                  }
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-white"
                />
              </label>
              <label className="space-y-1 text-xs">
                <span className="text-slate-400">Maintenance Interval Shots</span>
                <input
                  type="number"
                  min={1000}
                  required
                  value={editing.mold.maintenance_interval_shots}
                  onChange={(e) =>
                    setEditing({
                      ...editing,
                      mold: { ...editing.mold, maintenance_interval_shots: Number(e.target.value) },
                    })
                  }
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-white"
                />
              </label>
            </div>

            {/* Live Shot-Count Health Bar */}
            <div className="mt-3 rounded-xl border border-slate-800 bg-slate-950/70 p-3">
              <div className="mb-1.5 text-[11px] font-semibold text-slate-300">
                Live Shot-Count Health (HC6 PM auto-triggers at ≥ 95%)
              </div>
              <ShotHealthBar
                current={editing.mold.current_shots}
                interval={editing.mold.maintenance_interval_shots}
              />
            </div>

            <label className="mt-3 flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-900/70 px-3 py-2 text-xs text-slate-200">
              <input
                type="checkbox"
                checked={editing.mold.is_hot_runner}
                onChange={(e) =>
                  setEditing({ ...editing, mold: { ...editing.mold, is_hot_runner: e.target.checked } })
                }
                className="h-4 w-4 accent-cyan-400"
              />
              <span>Hot-Runner Mold (0.5% runner loss; requires Hot-Runner capable press)</span>
            </label>

            {/* Dynamic Compatible Machines Multi-Select */}
            <div className="mt-3 rounded-xl border border-slate-800 bg-slate-950/60 p-3">
              <div className="mb-2 text-xs font-semibold text-slate-300">
                Compatible Presses (from Sub-Tab A)
              </div>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                {presses.map((p) => {
                  const checked = editing.mold.compatible_machines.includes(p.machine_id);
                  return (
                    <label
                      key={p.machine_id}
                      className={`flex cursor-pointer items-center gap-2 rounded-lg border px-2.5 py-1.5 text-[11px] transition ${
                        checked
                          ? "border-cyan-500/50 bg-cyan-500/15 text-cyan-200"
                          : "border-slate-800 bg-slate-900 text-slate-400"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggleMachine(p.machine_id)}
                        className="h-3.5 w-3.5 accent-cyan-400"
                      />
                      <span className="truncate font-mono">{p.machine_id}</span>
                    </label>
                  );
                })}
              </div>
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
                data-testid="save-mold-btn"
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
        entityLabel={deleteTarget ? `${deleteTarget.mold_id} (${deleteTarget.name})` : ""}
        references={deleteTarget ? getReferences(deleteTarget.mold_id) : []}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={() => {
          if (deleteTarget) deleteMold(deleteTarget.mold_id);
          setDeleteTarget(null);
        }}
      />
    </div>
  );
}
