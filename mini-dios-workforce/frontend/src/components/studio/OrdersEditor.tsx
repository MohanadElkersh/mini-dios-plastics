"use client";

import React, { useMemo, useState } from "react";
import { Copy, Edit3, Globe, Plus, Search, Trash2, X } from "lucide-react";
import { COLOR_LABELS, COPY } from "@/lib/i18n";
import { useApp } from "@/lib/store";
import type { Mold, PlasticColor, ProductionOrder, ResinCode } from "@/lib/types";
import { ConfirmDeleteModal } from "./ConfirmDeleteModal";

const COLOR_SWATCHES: Record<PlasticColor, { rank: number; hex: string; badge: string }> = {
  Natural: { rank: 1, hex: "#e2e8f0", badge: "bg-slate-200 text-slate-900 border-slate-300" },
  White: { rank: 2, hex: "#ffffff", badge: "bg-white text-slate-950 border-slate-300" },
  Yellow: { rank: 3, hex: "#facc15", badge: "bg-yellow-400 text-slate-950 border-yellow-300" },
  Blue: { rank: 4, hex: "#3b82f6", badge: "bg-blue-500 text-white border-blue-400" },
  Red: { rank: 5, hex: "#ef4444", badge: "bg-red-500 text-white border-red-400" },
  Black: { rank: 6, hex: "#18181b", badge: "bg-zinc-900 text-zinc-100 border-zinc-600" },
};

const PLASTIC_COLORS: PlasticColor[] = ["Natural", "White", "Yellow", "Blue", "Red", "Black"];

function estimateOrderPhysics(order: ProductionOrder, mold?: Mold) {
  const cavities = mold?.cavities ?? 4;
  const cycleSec = mold?.cycle_time_sec ?? 15;
  const isHotRunner = mold?.is_hot_runner ?? false;
  const shots = Math.max(1, Math.ceil(order.quantity_pcs / Math.max(1, cavities)));
  const rawMins = (shots * cycleSec) / 60;
  const estMins = Math.max(30, Math.ceil(rawMins));
  const netKg = (order.quantity_pcs * order.part_weight_g) / 1000;
  const runnerFactor = isHotRunner ? 1.005 : 1.03;
  return {
    estRunHrs: Math.round((estMins / 60) * 10) / 10,
    estResinKg: Math.round(netKg * runnerFactor * 10) / 10,
  };
}

export function OrdersEditor() {
  const { lang, dataset, config, upsertOrder, deleteOrder } = useApp();
  const t = COPY[lang];
  const orders = dataset?.orders ?? [];
  const molds = dataset?.molds ?? [];
  const resins = dataset?.resins ?? [];
  const maxHr = config.physics.horizon_hrs;

  const [query, setQuery] = useState("");
  const [filterResin, setFilterResin] = useState<string>("ALL");
  const [filterColor, setFilterColor] = useState<string>("ALL");
  const [editing, setEditing] = useState<{ order: ProductionOrder; originalId?: string } | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<ProductionOrder | null>(null);

  const moldsById = useMemo(() => new Map(molds.map((m) => [m.mold_id, m])), [molds]);

  const filteredOrders = useMemo(() => {
    const q = query.trim().toLowerCase();
    return orders.filter((o) => {
      if (filterResin !== "ALL" && o.resin_code !== filterResin) return false;
      if (filterColor !== "ALL" && o.color !== filterColor) return false;
      if (!q) return true;
      return (
        o.order_id.toLowerCase().includes(q) ||
        o.customer.toLowerCase().includes(q) ||
        o.sku_name.toLowerCase().includes(q) ||
        o.mold_id.toLowerCase().includes(q)
      );
    });
  }, [orders, query, filterResin, filterColor]);

  const openNew = () => {
    const nextNum = orders.length + 1;
    const defaultMold = molds[0]?.mold_id ?? "M-01";
    const defaultResin = resins[0]?.resin_code ?? "HDPE";
    setEditing({
      order: {
        order_id: `ORD-${String(nextNum).padStart(2, "0")}`,
        customer: "New Customer",
        sku_name: "Custom Molded Part",
        mold_id: defaultMold,
        resin_code: defaultResin,
        color: "White",
        color_rank: COLOR_SWATCHES.White.rank,
        quantity_pcs: 40000,
        part_weight_g: 12,
        max_regrind_pct: 0,
        due_hr: Math.min(96, maxHr),
        late_penalty_per_hr: 400,
        is_export: true,
        unit_selling_price: 0.25,
        discount_pct: 0,
      },
    });
  };

  const openEdit = (o: ProductionOrder) => {
    setEditing({ order: { ...o }, originalId: o.order_id });
  };

  const duplicateOrder = (o: ProductionOrder) => {
    let idx = 2;
    let candidate = `${o.order_id}-C`;
    while (orders.some((x) => x.order_id === candidate)) {
      candidate = `${o.order_id}-C${idx++}`;
    }
    upsertOrder({ ...o, order_id: candidate, sku_name: `${o.sku_name} (Copy)` });
  };

  const saveModal = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editing) return;
    const cleanId = editing.order.order_id.trim();
    if (!cleanId) return;
    upsertOrder(
      {
        ...editing.order,
        order_id: cleanId,
        color_rank: COLOR_SWATCHES[editing.order.color].rank,
      },
      editing.originalId
    );
    setEditing(null);
  };

  const modalEst = editing ? estimateOrderPhysics(editing.order, moldsById.get(editing.order.mold_id)) : null;

  return (
    <div className="space-y-4">
      {/* Search + Filters + Add Order */}
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:flex-wrap sm:items-center">
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative w-full sm:w-60">
            <Search className="pointer-events-none absolute start-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              data-testid="search-orders-input"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t.studioSearchOrders}
              className="min-h-[44px] w-full rounded-xl border border-slate-700 bg-slate-900 py-1.5 pe-3 ps-8 text-base text-white placeholder:text-slate-500 md:min-h-0 md:text-xs"
            />
          </div>
          <select
            value={filterResin}
            onChange={(e) => setFilterResin(e.target.value)}
            className="min-h-[44px] flex-1 rounded-xl border border-slate-700 bg-slate-900 px-3 py-1.5 text-base text-slate-200 sm:flex-initial md:min-h-0 md:text-xs"
          >
            <option value="ALL">{t.studioAllResins}</option>
            {resins.map((r) => (
              <option key={r.resin_code} value={r.resin_code}>
                {r.resin_code}
              </option>
            ))}
          </select>
          <select
            value={filterColor}
            onChange={(e) => setFilterColor(e.target.value)}
            className="min-h-[44px] flex-1 rounded-xl border border-slate-700 bg-slate-900 px-3 py-1.5 text-base text-slate-200 sm:flex-initial md:min-h-0 md:text-xs"
          >
            <option value="ALL">{t.studioAllColors}</option>
            {PLASTIC_COLORS.map((c) => (
              <option key={c} value={c}>
                {COLOR_LABELS[lang][c]}
              </option>
            ))}
          </select>
        </div>

        <button
          type="button"
          data-testid="btn-add-order"
          onClick={openNew}
          className="inline-flex min-h-[44px] w-full items-center justify-center gap-1.5 rounded-xl bg-cyan-500 px-3.5 py-2 text-xs font-bold text-slate-950 transition hover:bg-cyan-400 sm:w-auto md:min-h-0"
        >
          <Plus className="h-3.5 w-3.5" />
          <span>{t.studioAddOrder}</span>
        </button>
      </div>

      {/* Stacked Mobile Cards (< md) */}
      <div className="grid grid-cols-1 gap-3 md:hidden">
        {filteredOrders.map((o) => {
          const est = estimateOrderPhysics(o, moldsById.get(o.mold_id));
          const sw = COLOR_SWATCHES[o.color];
          return (
            <div
              key={o.order_id}
              data-testid={`order-card-${o.order_id}`}
              className="rounded-2xl border border-slate-800 bg-[#0f1629] p-4 text-xs shadow-lg"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-sm font-bold text-cyan-300">{o.order_id}</span>
                    <span
                      className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[10px] font-bold ${sw.badge}`}
                    >
                      {o.color_rank}. {COLOR_LABELS[lang][o.color]}
                    </span>
                    {o.is_export && (
                      <span className="inline-flex items-center gap-1 rounded bg-indigo-500/20 px-2 py-0.5 text-[10px] font-bold text-indigo-200">
                        <Globe className="h-3 w-3" /> Export
                      </span>
                    )}
                  </div>
                  <div className="mt-1 truncate font-semibold text-white">{o.sku_name}</div>
                  <div className="truncate text-[11px] text-slate-400">{o.customer}</div>
                </div>
                <div className="shrink-0 text-end font-mono">
                  <div className="text-xs font-bold text-amber-300">H{o.due_hr}</div>
                  <div className="text-[10px] text-slate-400">{o.mold_id} • {o.resin_code}</div>
                </div>
              </div>

              <div className="mt-3 grid grid-cols-3 gap-2 rounded-xl border border-slate-800/80 bg-slate-950/60 p-2.5 text-[11px]">
                <div>
                  <div className="text-slate-400">Qty</div>
                  <div dir="ltr" className="font-mono font-bold text-white">
                    {o.quantity_pcs.toLocaleString()}
                  </div>
                </div>
                <div>
                  <div className="text-slate-400">Est. Run</div>
                  <div dir="ltr" className="font-mono font-bold text-cyan-300">
                    {est.estRunHrs.toFixed(1)}h
                  </div>
                </div>
                <div>
                  <div className="text-slate-400">Est. Resin</div>
                  <div dir="ltr" className="font-mono font-bold text-emerald-300">
                    {est.estResinKg.toLocaleString()} kg
                  </div>
                </div>
              </div>

              <div className="mt-3 flex items-center justify-end gap-2 border-t border-slate-800/80 pt-3">
                <button
                  type="button"
                  onClick={() => openEdit(o)}
                  className="inline-flex min-h-[40px] flex-1 items-center justify-center gap-1.5 rounded-xl border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-semibold text-cyan-300"
                >
                  <Edit3 className="h-3.5 w-3.5" />
                  <span>{t.studioEdit}</span>
                </button>
                <button
                  type="button"
                  onClick={() => duplicateOrder(o)}
                  className="inline-flex min-h-[40px] items-center justify-center gap-1 rounded-xl border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-slate-300"
                >
                  <Copy className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  onClick={() => setDeleteTarget(o)}
                  className="inline-flex min-h-[40px] items-center justify-center gap-1 rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-1.5 text-xs text-rose-300"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Desktop Orders Table (md:block) */}
      <div className="hidden overflow-x-auto rounded-2xl border border-slate-800 bg-[#0f1629] md:block">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-slate-800 bg-slate-900/60 text-slate-400">
              <th className="sticky start-0 z-10 bg-slate-900/95 px-3 py-2.5 text-start">Order</th>
              <th className="px-3 py-2.5 text-start">Mold / Resin</th>
              <th className="px-3 py-2.5 text-start">Color</th>
              <th className="px-3 py-2.5 text-end">Qty (pcs)</th>
              <th className="px-3 py-2.5 text-end">Est. Run</th>
              <th className="px-3 py-2.5 text-end">Est. Resin</th>
              <th className="px-3 py-2.5 text-end">Due (h)</th>
              <th className="px-3 py-2.5 text-end">Penalty/h</th>
              <th className="px-3 py-2.5 text-center">Export</th>
              <th className="px-3 py-2.5 text-end">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/70">
            {filteredOrders.map((o) => {
              const est = estimateOrderPhysics(o, moldsById.get(o.mold_id));
              const sw = COLOR_SWATCHES[o.color];
              return (
                <tr key={o.order_id} data-testid={`order-row-${o.order_id}`} className="hover:bg-slate-900/40">
                  <td className="sticky start-0 z-10 bg-[#0f1629]/95 px-3 py-2.5">
                    <div className="font-mono font-bold text-cyan-300">{o.order_id}</div>
                    <div className="text-[11px] font-medium text-white">{o.sku_name}</div>
                    <div className="text-[10px] text-slate-400">{o.customer}</div>
                  </td>
                  <td className="px-3 py-2.5 font-mono text-slate-200">
                    <div>{o.mold_id}</div>
                    <div className="text-[10px] text-slate-400">
                      {o.resin_code} • Max RG {o.max_regrind_pct}%
                    </div>
                  </td>
                  <td className="px-3 py-2.5">
                    <span
                      className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-[10px] font-bold ${sw.badge}`}
                    >
                      {o.color_rank}. {COLOR_LABELS[lang][o.color]}
                    </span>
                  </td>
                  <td dir="ltr" className="px-3 py-2.5 text-end font-mono text-slate-200">
                    {o.quantity_pcs.toLocaleString()}
                  </td>
                  <td dir="ltr" className="px-3 py-2.5 text-end font-mono text-cyan-300">
                    {est.estRunHrs.toFixed(1)}h
                  </td>
                  <td dir="ltr" className="px-3 py-2.5 text-end font-mono text-emerald-300">
                    {est.estResinKg.toLocaleString()} kg
                  </td>
                  <td dir="ltr" className="px-3 py-2.5 text-end font-mono text-amber-300">
                    H{o.due_hr}
                  </td>
                  <td dir="ltr" className="px-3 py-2.5 text-end font-mono text-slate-300">
                    {o.late_penalty_per_hr}
                  </td>
                  <td className="px-3 py-2.5 text-center">
                    {o.is_export ? (
                      <span className="inline-flex items-center gap-1 rounded bg-indigo-500/20 px-2 py-0.5 text-[10px] font-bold text-indigo-200">
                        <Globe className="h-3 w-3" /> Export
                      </span>
                    ) : (
                      <span className="text-[11px] text-slate-500">Local</span>
                    )}
                  </td>
                  <td className="px-3 py-2.5 text-end">
                    <div className="inline-flex items-center gap-1">
                      <button
                        type="button"
                        data-testid={`edit-order-${o.order_id}`}
                        onClick={() => openEdit(o)}
                        className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-cyan-300"
                      >
                        <Edit3 className="h-3.5 w-3.5" />
                      </button>
                      <button
                        type="button"
                        data-testid={`dup-order-${o.order_id}`}
                        onClick={() => duplicateOrder(o)}
                        className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-indigo-300"
                      >
                        <Copy className="h-3.5 w-3.5" />
                      </button>
                      <button
                        type="button"
                        data-testid={`del-order-${o.order_id}`}
                        onClick={() => setDeleteTarget(o)}
                        className="rounded-lg p-1.5 text-slate-400 hover:bg-rose-500/20 hover:text-rose-300"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Add / Edit Order Modal */}
      {editing && modalEst && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/75 p-0 backdrop-blur-sm sm:items-center sm:p-4">
          <form
            onSubmit={saveModal}
            className="flex max-h-[90dvh] w-full max-w-xl flex-col overflow-hidden rounded-t-3xl border border-slate-700 bg-[#0f1629] shadow-2xl sm:rounded-2xl"
          >
            <div className="flex shrink-0 items-center justify-between border-b border-slate-800 bg-slate-950/80 px-5 py-3.5">
              <h3 className="text-sm font-bold text-white">
                {editing.originalId ? `${t.studioEdit}: ${editing.originalId}` : t.studioAddOrder}
              </h3>
              <button
                type="button"
                onClick={() => setEditing(null)}
                className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white md:min-h-0 md:min-w-0"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-5">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <label className="space-y-1 text-xs">
                <span className="text-slate-400">Order ID</span>
                <input
                  required
                  data-testid="input-order-id"
                  value={editing.order.order_id}
                  onChange={(e) => setEditing({ ...editing, order: { ...editing.order, order_id: e.target.value } })}
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-white"
                />
              </label>
              <label className="space-y-1 text-xs">
                <span className="text-slate-400">Customer</span>
                <input
                  required
                  data-testid="input-order-customer"
                  value={editing.order.customer}
                  onChange={(e) => setEditing({ ...editing, order: { ...editing.order, customer: e.target.value } })}
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-white"
                />
              </label>
              <label className="space-y-1 text-xs sm:col-span-2">
                <span className="text-slate-400">SKU Name</span>
                <input
                  required
                  data-testid="input-order-sku"
                  value={editing.order.sku_name}
                  onChange={(e) => setEditing({ ...editing, order: { ...editing.order, sku_name: e.target.value } })}
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-white"
                />
              </label>
              <label className="space-y-1 text-xs">
                <span className="text-slate-400">Mold (from Sub-Tab B)</span>
                <select
                  data-testid="select-order-mold"
                  value={editing.order.mold_id}
                  onChange={(e) => setEditing({ ...editing, order: { ...editing.order, mold_id: e.target.value } })}
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-white"
                >
                  {molds.map((m) => (
                    <option key={m.mold_id} value={m.mold_id}>
                      {m.mold_id} — {m.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="space-y-1 text-xs">
                <span className="text-slate-400">Resin (from Sub-Tab C)</span>
                <select
                  data-testid="select-order-resin"
                  value={editing.order.resin_code}
                  onChange={(e) =>
                    setEditing({
                      ...editing,
                      order: { ...editing.order, resin_code: e.target.value as ResinCode },
                    })
                  }
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-white"
                >
                  {resins.map((r) => (
                    <option key={r.resin_code} value={r.resin_code}>
                      {r.resin_code} ({r.virgin_available_kg.toLocaleString()} kg)
                    </option>
                  ))}
                </select>
              </label>

              {/* Visual Color Swatch Selector */}
              <div className="space-y-1.5 text-xs sm:col-span-2">
                <span className="text-slate-400">
                  Pigment Color (auto-sets rank {COLOR_SWATCHES[editing.order.color].rank})
                </span>
                <div className="grid grid-cols-3 gap-2 sm:grid-cols-6">
                  {PLASTIC_COLORS.map((col) => {
                    const active = editing.order.color === col;
                    return (
                      <button
                        key={col}
                        type="button"
                        data-testid={`swatch-color-${col}`}
                        onClick={() =>
                          setEditing({
                            ...editing,
                            order: {
                              ...editing.order,
                              color: col,
                              color_rank: COLOR_SWATCHES[col].rank,
                            },
                          })
                        }
                        className={`flex items-center gap-1.5 rounded-lg border px-2 py-1.5 text-[11px] font-semibold transition ${
                          active
                            ? "border-cyan-400 bg-cyan-500/20 text-white ring-1 ring-cyan-400"
                            : "border-slate-800 bg-slate-900 text-slate-300 hover:border-slate-600"
                        }`}
                      >
                        <span
                          className="h-3 w-3 shrink-0 rounded-sm border border-slate-500"
                          style={{ backgroundColor: COLOR_SWATCHES[col].hex }}
                        />
                        <span className="truncate">{COLOR_LABELS[lang][col]}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              <label className="space-y-1 text-xs">
                <span className="text-slate-400">Quantity (pcs)</span>
                <input
                  type="number"
                  min={1}
                  required
                  data-testid="input-order-qty"
                  value={editing.order.quantity_pcs}
                  onChange={(e) =>
                    setEditing({ ...editing, order: { ...editing.order, quantity_pcs: Number(e.target.value) } })
                  }
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-white"
                />
              </label>
              <label className="space-y-1 text-xs">
                <span className="text-slate-400">Part Weight (g)</span>
                <input
                  type="number"
                  step="0.1"
                  min={0.1}
                  required
                  data-testid="input-order-weight"
                  value={editing.order.part_weight_g}
                  onChange={(e) =>
                    setEditing({ ...editing, order: { ...editing.order, part_weight_g: Number(e.target.value) } })
                  }
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-white"
                />
              </label>
              <label className="space-y-1 text-xs">
                <span className="text-slate-400">Max Regrind % (0 = Food/Pharma)</span>
                <input
                  type="number"
                  step="1"
                  min={0}
                  max={50}
                  required
                  value={editing.order.max_regrind_pct}
                  onChange={(e) =>
                    setEditing({
                      ...editing,
                      order: { ...editing.order, max_regrind_pct: Number(e.target.value) },
                    })
                  }
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-white"
                />
              </label>
              <label className="space-y-1 text-xs">
                <span className="text-slate-400">Due Hour (1–336)</span>
                <input
                  type="number"
                  step="1"
                  min={1}
                  max={336}
                  required
                  data-testid="input-order-due"
                  value={editing.order.due_hr}
                  onChange={(e) =>
                    setEditing({ ...editing, order: { ...editing.order, due_hr: Number(e.target.value) } })
                  }
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-white"
                />
              </label>
              <label className="space-y-1 text-xs">
                <span className="text-slate-400">Late Penalty (SAR/hr)</span>
                <input
                  type="number"
                  step="10"
                  min={0}
                  required
                  value={editing.order.late_penalty_per_hr}
                  onChange={(e) =>
                    setEditing({
                      ...editing,
                      order: { ...editing.order, late_penalty_per_hr: Number(e.target.value) },
                    })
                  }
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-white"
                />
              </label>
              <label className="space-y-1 text-xs">
                <span className="text-slate-400">Unit Selling Price (SAR/pc)</span>
                <input
                  type="number"
                  step="0.005"
                  min={0}
                  data-testid="input-order-unit-price"
                  value={editing.order.unit_selling_price ?? 0}
                  onChange={(e) =>
                    setEditing({
                      ...editing,
                      order: { ...editing.order, unit_selling_price: Number(e.target.value) },
                    })
                  }
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-cyan-300"
                />
              </label>
              <label className="space-y-1 text-xs">
                <span className="text-slate-400">Discount %</span>
                <input
                  type="number"
                  step="0.5"
                  min={0}
                  max={100}
                  data-testid="input-order-discount"
                  value={editing.order.discount_pct ?? 0}
                  onChange={(e) =>
                    setEditing({
                      ...editing,
                      order: { ...editing.order, discount_pct: Number(e.target.value) },
                    })
                  }
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-white"
                />
              </label>
              <label className="flex items-center gap-2 self-end rounded-lg border border-slate-800 bg-slate-900/70 px-3 py-2.5 text-xs text-slate-200">
                <input
                  type="checkbox"
                  checked={editing.order.is_export}
                  onChange={(e) =>
                    setEditing({ ...editing, order: { ...editing.order, is_export: e.target.checked } })
                  }
                  className="h-4 w-4 accent-cyan-400"
                />
                <span>Priority Export Order (1.5x SLA Weight)</span>
              </label>
            </div>

            {/* Live Computed Order Physics & Revenue Banner */}
            <div className="mt-4 grid grid-cols-1 gap-3 rounded-xl border border-cyan-500/30 bg-cyan-500/10 p-3 text-xs sm:grid-cols-3">
              <div>
                <div className="text-[11px] text-cyan-200/80">{t.studioEstRunHrs}</div>
                <div dir="ltr" data-testid="modal-est-run-hrs" className="font-mono text-base font-bold text-cyan-300">
                  {modalEst.estRunHrs.toFixed(1)} hrs
                </div>
              </div>
              <div>
                <div className="text-[11px] text-emerald-200/80">{t.studioEstResinKg}</div>
                <div dir="ltr" data-testid="modal-est-resin-kg" className="font-mono text-base font-bold text-emerald-300">
                  {modalEst.estResinKg.toLocaleString()} kg
                </div>
              </div>
              <div>
                <div className="text-[11px] text-amber-200/80">
                  {lang === "ar" ? "إيراد الطلب (SAR)" : "Order Revenue (SAR)"}
                </div>
                <div dir="ltr" data-testid="modal-est-revenue" className="font-mono text-base font-bold text-amber-300">
                  {Math.round(
                    editing.order.quantity_pcs *
                      (editing.order.unit_selling_price ?? 0) *
                      (1 - (editing.order.discount_pct ?? 0) / 100)
                  ).toLocaleString()}{" "}
                  SAR
                </div>
              </div>
            </div>
            </div>

            <div className="flex shrink-0 justify-end gap-2 border-t border-slate-800 bg-slate-950/90 px-5 py-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] sm:pb-3">
              <button
                type="button"
                onClick={() => setEditing(null)}
                className="min-h-[44px] rounded-lg border border-slate-700 bg-slate-900 px-3.5 py-2 text-xs font-semibold text-slate-300 md:min-h-0"
              >
                {t.studioCancel}
              </button>
              <button
                type="submit"
                data-testid="save-order-btn"
                className="min-h-[44px] rounded-lg bg-cyan-500 px-4 py-2 text-xs font-bold text-slate-950 hover:bg-cyan-400 md:min-h-0"
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
        entityLabel={deleteTarget ? `Order ${deleteTarget.order_id} (${deleteTarget.sku_name})` : ""}
        references={[]}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={() => {
          if (deleteTarget) deleteOrder(deleteTarget.order_id);
          setDeleteTarget(null);
        }}
      />
    </div>
  );
}
