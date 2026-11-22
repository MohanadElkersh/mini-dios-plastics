"use client";

import React, { useState } from "react";
import { Copy, Edit3, Flame, Plus, Power, Trash2, X } from "lucide-react";
import { COPY } from "@/lib/i18n";
import { useApp } from "@/lib/store";
import type { DowntimeWindow, MachineStatus, PressMachine, ProcessType } from "@/lib/types";
import { ConfirmDeleteModal } from "./ConfirmDeleteModal";

const EMPTY_PRESS: PressMachine = {
  machine_id: "",
  name: "",
  process_type: "Injection",
  tonnage: 250,
  supports_hot_runner: true,
  hourly_energy_kwh: 45,
  hourly_operating_cost: 180,
  status: "active",
  downtime_windows: [],
};

export function PressesEditor() {
  const { lang, dataset, config, upsertPress, deletePress } = useApp();
  const t = COPY[lang];
  const presses = dataset?.presses ?? [];
  const molds = dataset?.molds ?? [];
  const maxHr = config.physics.horizon_hrs;

  const [editing, setEditing] = useState<{ press: PressMachine; originalId?: string } | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<PressMachine | null>(null);

  const openNew = () => {
    const idx = presses.length + 1;
    setEditing({
      press: {
        ...EMPTY_PRESS,
        machine_id: `P-NEW${idx}`,
        name: `New Press ${idx}`,
      },
    });
  };

  const openEdit = (p: PressMachine) => {
    setEditing({
      press: { ...p, downtime_windows: p.downtime_windows.map((d) => ({ ...d })) },
      originalId: p.machine_id,
    });
  };

  const duplicatePress = (p: PressMachine) => {
    let suffix = 2;
    let candidate = `${p.machine_id}-COPY`;
    while (presses.some((x) => x.machine_id === candidate)) {
      candidate = `${p.machine_id}-COPY${suffix++}`;
    }
    upsertPress({
      ...p,
      machine_id: candidate,
      name: `${p.name} (Copy)`,
      downtime_windows: p.downtime_windows.map((d) => ({ ...d })),
    });
  };

  const toggleStatus = (p: PressMachine) => {
    const nextStatus: MachineStatus = p.status === "active" ? "down" : "active";
    upsertPress({ ...p, status: nextStatus }, p.machine_id);
  };

  const getReferences = (machineId: string): string[] => {
    const affectedMolds = molds.filter((m) => m.compatible_machines.includes(machineId));
    return affectedMolds.map(
      (m) => `Mold ${m.mold_id} (${m.name}) — ${m.compatible_machines.length} compatible press(es)`
    );
  };

  const saveModal = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editing) return;
    const cleanId = editing.press.machine_id.trim();
    if (!cleanId) return;
    upsertPress(
      {
        ...editing.press,
        machine_id: cleanId,
        name: editing.press.name.trim() || cleanId,
        downtime_windows: editing.press.downtime_windows.filter((d) => d.end_hr > d.start_hr),
      },
      editing.originalId
    );
    setEditing(null);
  };

  const addDowntimeRow = () => {
    if (!editing) return;
    const dw: DowntimeWindow = { start_hr: 24, end_hr: 28, reason: "Scheduled Maintenance" };
    setEditing({
      ...editing,
      press: { ...editing.press, downtime_windows: [...editing.press.downtime_windows, dw] },
    });
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-slate-400">
          {presses.length} {lang === "ar" ? "ماكينة مسجلة" : "presses configured"}
        </p>
        <button
          type="button"
          data-testid="btn-add-press"
          onClick={openNew}
          className="inline-flex items-center gap-1.5 rounded-xl bg-cyan-500 px-3.5 py-2 text-xs font-bold text-slate-950 transition hover:bg-cyan-400"
        >
          <Plus className="h-3.5 w-3.5" />
          <span>{t.studioAddPress}</span>
        </button>
      </div>

      <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-[#0f1629]">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-slate-800 bg-slate-900/60 text-slate-400">
              <th className="px-3 py-2.5 text-start">ID</th>
              <th className="px-3 py-2.5 text-start">Name</th>
              <th className="px-3 py-2.5 text-start">Process</th>
              <th className="px-3 py-2.5 text-end">Tonnage</th>
              <th className="px-3 py-2.5 text-center">Hot Runner</th>
              <th className="px-3 py-2.5 text-end">kWh/h</th>
              <th className="px-3 py-2.5 text-end">Op Cost/h</th>
              <th className="px-3 py-2.5 text-center">Status</th>
              <th className="px-3 py-2.5 text-start">Downtime Windows</th>
              <th className="px-3 py-2.5 text-end">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/70">
            {presses.map((p) => (
              <tr key={p.machine_id} data-testid={`press-row-${p.machine_id}`} className="hover:bg-slate-900/40">
                <td className="px-3 py-2.5 font-mono font-bold text-cyan-300">{p.machine_id}</td>
                <td className="px-3 py-2.5 font-medium text-white">{p.name}</td>
                <td className="px-3 py-2.5 text-slate-300">{p.process_type}</td>
                <td dir="ltr" className="px-3 py-2.5 text-end font-mono text-slate-200">
                  {p.tonnage}T
                </td>
                <td className="px-3 py-2.5 text-center">
                  {p.supports_hot_runner ? (
                    <span className="inline-flex items-center gap-1 rounded bg-cyan-500/15 px-2 py-0.5 text-[10px] font-bold text-cyan-300">
                      <Flame className="h-3 w-3" /> HR
                    </span>
                  ) : (
                    <span className="text-[11px] text-slate-500">Cold</span>
                  )}
                </td>
                <td dir="ltr" className="px-3 py-2.5 text-end font-mono text-slate-300">
                  {p.hourly_energy_kwh}
                </td>
                <td dir="ltr" className="px-3 py-2.5 text-end font-mono text-slate-300">
                  {p.hourly_operating_cost}
                </td>
                <td className="px-3 py-2.5 text-center">
                  <button
                    type="button"
                    data-testid={`toggle-press-status-${p.machine_id}`}
                    onClick={() => toggleStatus(p)}
                    className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[10px] font-bold transition ${
                      p.status === "active"
                        ? "bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/30"
                        : "bg-rose-500/20 text-rose-300 hover:bg-rose-500/30"
                    }`}
                  >
                    <Power className="h-2.5 w-2.5" />
                    <span>{p.status}</span>
                  </button>
                </td>
                <td className="px-3 py-2.5 text-[11px] text-slate-400">
                  {p.downtime_windows.length === 0
                    ? "—"
                    : p.downtime_windows.map((d, i) => (
                        <span key={i} className="me-1.5 inline-block rounded bg-slate-800 px-1.5 py-0.5 font-mono">
                          H{d.start_hr}–{d.end_hr}
                        </span>
                      ))}
                </td>
                <td className="px-3 py-2.5 text-end">
                  <div className="inline-flex items-center gap-1">
                    <button
                      type="button"
                      data-testid={`edit-press-${p.machine_id}`}
                      onClick={() => openEdit(p)}
                      title={t.studioEdit}
                      className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-cyan-300"
                    >
                      <Edit3 className="h-3.5 w-3.5" />
                    </button>
                    <button
                      type="button"
                      data-testid={`dup-press-${p.machine_id}`}
                      onClick={() => duplicatePress(p)}
                      title={t.studioDuplicate}
                      className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-indigo-300"
                    >
                      <Copy className="h-3.5 w-3.5" />
                    </button>
                    <button
                      type="button"
                      data-testid={`del-press-${p.machine_id}`}
                      onClick={() => setDeleteTarget(p)}
                      title={t.studioDelete}
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

      {/* Add / Edit Press Modal */}
      {editing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <form
            onSubmit={saveModal}
            className="max-h-[90vh] w-full max-w-xl overflow-y-auto rounded-2xl border border-slate-700 bg-[#0f1629] p-5 shadow-2xl"
          >
            <div className="mb-4 flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-white">
                {editing.originalId ? `${t.studioEdit}: ${editing.originalId}` : t.studioAddPress}
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
                <span className="text-slate-400">Machine ID</span>
                <input
                  required
                  value={editing.press.machine_id}
                  onChange={(e) =>
                    setEditing({ ...editing, press: { ...editing.press, machine_id: e.target.value } })
                  }
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-white"
                />
              </label>
              <label className="space-y-1 text-xs">
                <span className="text-slate-400">Name</span>
                <input
                  required
                  value={editing.press.name}
                  onChange={(e) => setEditing({ ...editing, press: { ...editing.press, name: e.target.value } })}
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-white"
                />
              </label>
              <label className="space-y-1 text-xs">
                <span className="text-slate-400">Process Type</span>
                <select
                  value={editing.press.process_type}
                  onChange={(e) =>
                    setEditing({
                      ...editing,
                      press: { ...editing.press, process_type: e.target.value as ProcessType },
                    })
                  }
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-white"
                >
                  <option value="Injection">Injection</option>
                  <option value="BlowMolding">BlowMolding</option>
                  <option value="Extrusion">Extrusion</option>
                </select>
              </label>
              <label className="space-y-1 text-xs">
                <span className="text-slate-400">Tonnage (Metric Tons)</span>
                <input
                  type="number"
                  min={20}
                  max={5000}
                  required
                  value={editing.press.tonnage}
                  onChange={(e) =>
                    setEditing({ ...editing, press: { ...editing.press, tonnage: Number(e.target.value) } })
                  }
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-white"
                />
              </label>
              <label className="space-y-1 text-xs">
                <span className="text-slate-400">Hourly Energy (kWh)</span>
                <input
                  type="number"
                  step="0.5"
                  min={1}
                  required
                  value={editing.press.hourly_energy_kwh}
                  onChange={(e) =>
                    setEditing({
                      ...editing,
                      press: { ...editing.press, hourly_energy_kwh: Number(e.target.value) },
                    })
                  }
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-white"
                />
              </label>
              <label className="space-y-1 text-xs">
                <span className="text-slate-400">Operating Cost (SAR/hr)</span>
                <input
                  type="number"
                  step="1"
                  min={1}
                  required
                  value={editing.press.hourly_operating_cost}
                  onChange={(e) =>
                    setEditing({
                      ...editing,
                      press: { ...editing.press, hourly_operating_cost: Number(e.target.value) },
                    })
                  }
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-white"
                />
              </label>
              <label className="space-y-1 text-xs">
                <span className="text-slate-400">Status</span>
                <select
                  value={editing.press.status}
                  onChange={(e) =>
                    setEditing({ ...editing, press: { ...editing.press, status: e.target.value as MachineStatus } })
                  }
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-white"
                >
                  <option value="active">active</option>
                  <option value="down">down</option>
                  <option value="maintenance">maintenance</option>
                </select>
              </label>
              <label className="flex items-center gap-2 self-end rounded-lg border border-slate-800 bg-slate-900/70 px-3 py-2.5 text-xs text-slate-200">
                <input
                  type="checkbox"
                  checked={editing.press.supports_hot_runner}
                  onChange={(e) =>
                    setEditing({
                      ...editing,
                      press: { ...editing.press, supports_hot_runner: e.target.checked },
                    })
                  }
                  className="h-4 w-4 accent-cyan-400"
                />
                <span>Supports Hot-Runner Molds</span>
              </label>
            </div>

            {/* Downtime Windows Mini-List Editor */}
            <div className="mt-4 rounded-xl border border-slate-800 bg-slate-950/60 p-3">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-300">Downtime Windows (Hours)</span>
                <button
                  type="button"
                  onClick={addDowntimeRow}
                  className="inline-flex items-center gap-1 rounded-md border border-cyan-500/40 bg-cyan-500/10 px-2 py-1 text-[11px] font-semibold text-cyan-300 hover:bg-cyan-500/20"
                >
                  <Plus className="h-3 w-3" /> Add Window
                </button>
              </div>
              {editing.press.downtime_windows.length === 0 ? (
                <p className="text-[11px] text-slate-500">No scheduled downtime windows.</p>
              ) : (
                <div className="space-y-2">
                  {editing.press.downtime_windows.map((dw, idx) => (
                    <div key={idx} className="grid grid-cols-[80px_80px_1fr_auto] items-center gap-2">
                      <input
                        type="number"
                        min={0}
                        max={maxHr}
                        step="0.5"
                        value={dw.start_hr}
                        onChange={(e) => {
                          const next = [...editing.press.downtime_windows];
                          next[idx] = { ...dw, start_hr: Number(e.target.value) };
                          setEditing({ ...editing, press: { ...editing.press, downtime_windows: next } });
                        }}
                        placeholder="Start"
                        className="rounded border border-slate-700 bg-slate-900 px-2 py-1 font-mono text-xs text-white"
                      />
                      <input
                        type="number"
                        min={0}
                        max={336}
                        step="0.5"
                        value={dw.end_hr}
                        onChange={(e) => {
                          const next = [...editing.press.downtime_windows];
                          next[idx] = { ...dw, end_hr: Number(e.target.value) };
                          setEditing({ ...editing, press: { ...editing.press, downtime_windows: next } });
                        }}
                        placeholder="End"
                        className="rounded border border-slate-700 bg-slate-900 px-2 py-1 font-mono text-xs text-white"
                      />
                      <input
                        type="text"
                        value={dw.reason}
                        onChange={(e) => {
                          const next = [...editing.press.downtime_windows];
                          next[idx] = { ...dw, reason: e.target.value };
                          setEditing({ ...editing, press: { ...editing.press, downtime_windows: next } });
                        }}
                        placeholder="Reason"
                        className="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-white"
                      />
                      <button
                        type="button"
                        onClick={() => {
                          const next = editing.press.downtime_windows.filter((_, i) => i !== idx);
                          setEditing({ ...editing, press: { ...editing.press, downtime_windows: next } });
                        }}
                        className="rounded p-1 text-slate-400 hover:bg-rose-500/20 hover:text-rose-300"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
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
                data-testid="save-press-btn"
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
        entityLabel={deleteTarget ? `${deleteTarget.machine_id} (${deleteTarget.name})` : ""}
        references={deleteTarget ? getReferences(deleteTarget.machine_id) : []}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={() => {
          if (deleteTarget) deletePress(deleteTarget.machine_id);
          setDeleteTarget(null);
        }}
      />
    </div>
  );
}
