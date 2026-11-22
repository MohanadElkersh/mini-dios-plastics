"use client";

import React, { useEffect, useState } from "react";
import {
  CalendarClock,
  Check,
  Cpu,
  Droplet,
  Factory,
  Flame,
  Layers,
  Package,
  Plus,
  Sliders,
  X,
  Zap,
} from "lucide-react";
import { COLOR_LABELS, COPY } from "@/lib/i18n";
import { useApp } from "@/lib/store";
import type {
  Mold,
  PlantPhysicsConfig,
  PlasticColor,
  PressMachine,
  ProcessType,
  ProductionOrder,
  ResinCode,
  ResinStock,
} from "@/lib/types";

const ALL_RESINS: ResinCode[] = ["PP", "HDPE", "LDPE", "PET", "ABS", "PVC"];
const ALL_COLORS: { color: PlasticColor; rank: number; hex: string }[] = [
  { color: "Natural", rank: 1, hex: "#f1f5f9" },
  { color: "White", rank: 2, hex: "#ffffff" },
  { color: "Yellow", rank: 3, hex: "#eab308" },
  { color: "Blue", rank: 4, hex: "#3b82f6" },
  { color: "Red", rank: 5, hex: "#ef4444" },
  { color: "Black", rank: 6, hex: "#0f172a" },
];

export function QuickAddModal() {
  const {
    lang,
    currency,
    dataset,
    config,
    activeQuickModal,
    quickModalItem,
    closeQuickModal,
    upsertPress,
    upsertMold,
    upsertResin,
    upsertOrder,
    updatePhysics,
  } = useApp();

  const t = COPY[lang];

  // Forms state
  const [pressForm, setPressForm] = useState<PressMachine>({
    machine_id: "",
    name: "",
    process_type: "Injection",
    tonnage: 250,
    supports_hot_runner: true,
    hourly_energy_kwh: 45,
    hourly_operating_cost: 180,
    status: "active",
    downtime_windows: [],
  });

  const [moldForm, setMoldForm] = useState<Mold>({
    mold_id: "",
    name: "",
    compatible_machines: [],
    cavities: 8,
    cycle_time_sec: 18,
    is_hot_runner: true,
    base_changeover_mins: 45,
    current_shots: 0,
    maintenance_interval_shots: 100000,
    pm_duration_hrs: 6,
  });

  const [resinForm, setResinForm] = useState<ResinStock>({
    resin_code: "PP",
    virgin_available_kg: 5000,
    virgin_cost_per_kg: 5.5,
    regrind_available_kg: 500,
    regrind_cost_per_kg: 3.0,
    drying_lead_time_hrs: 0,
    barrel_temp_c: 210,
  });

  const [orderForm, setOrderForm] = useState<ProductionOrder>({
    order_id: "",
    customer: "",
    sku_name: "",
    mold_id: "",
    resin_code: "PP",
    color: "Natural",
    color_rank: 1,
    quantity_pcs: 25000,
    part_weight_g: 22,
    max_regrind_pct: 20,
    due_hr: 96,
    late_penalty_per_hr: 300,
    is_export: false,
    unit_selling_price: 0.25,
    discount_pct: 0,
  });

  const [physicsForm, setPhysicsForm] = useState<PlantPhysicsConfig>(config.physics);

  useEffect(() => {
    if (!activeQuickModal) return;
    if (activeQuickModal === "press") {
      if (quickModalItem) {
        setPressForm({ ...quickModalItem });
      } else {
        const idx = (dataset?.presses.length ?? 0) + 1;
        setPressForm({
          machine_id: `P-0${idx}`,
          name: `Press P-0${idx} (300T)`,
          process_type: "Injection",
          tonnage: 300,
          supports_hot_runner: true,
          hourly_energy_kwh: 50,
          hourly_operating_cost: 200,
          status: "active",
          downtime_windows: [],
        });
      }
    } else if (activeQuickModal === "mold") {
      if (quickModalItem) {
        setMoldForm({ ...quickModalItem });
      } else {
        const idx = (dataset?.molds.length ?? 0) + 1;
        const padIdx = idx < 10 ? `0${idx}` : `${idx}`;
        const firstPress = dataset?.presses[0]?.machine_id;
        setMoldForm({
          mold_id: `M-${padIdx}`,
          name: `Custom Mold M-${padIdx}`,
          compatible_machines: firstPress ? [firstPress] : [],
          cavities: 8,
          cycle_time_sec: 18,
          is_hot_runner: true,
          base_changeover_mins: 45,
          current_shots: 0,
          maintenance_interval_shots: 100000,
          pm_duration_hrs: 6,
        });
      }
    } else if (activeQuickModal === "resin") {
      if (quickModalItem) {
        setResinForm({ ...quickModalItem });
      } else {
        const usedCodes = new Set(dataset?.resins.map((r) => r.resin_code) ?? []);
        const nextCode = ALL_RESINS.find((c) => !usedCodes.has(c)) ?? "PP";
        setResinForm({
          resin_code: nextCode,
          virgin_available_kg: 5000,
          virgin_cost_per_kg: 5.5,
          regrind_available_kg: 500,
          regrind_cost_per_kg: 3.0,
          drying_lead_time_hrs: nextCode === "PET" || nextCode === "ABS" ? 6 : 0,
          barrel_temp_c: nextCode === "PET" ? 275 : 210,
        });
      }
    } else if (activeQuickModal === "order") {
      if (quickModalItem) {
        setOrderForm({ ...quickModalItem });
      } else {
        const idx = (dataset?.orders.length ?? 0) + 1;
        const firstMold = dataset?.molds[0]?.mold_id ?? "M-01";
        const firstResin = dataset?.resins[0]?.resin_code ?? "PP";
        setOrderForm({
          order_id: `ORD-NEW-${idx}`,
          customer: "Gulf FMCG Packaging",
          sku_name: `Custom Product SKU-${idx}`,
          mold_id: firstMold,
          resin_code: firstResin,
          color: "Natural",
          color_rank: 1,
          quantity_pcs: 30000,
          part_weight_g: 25,
          max_regrind_pct: 15,
          due_hr: 96,
          late_penalty_per_hr: 450,
          is_export: false,
          unit_selling_price: 0.28,
          discount_pct: 0,
        });
      }
    } else if (activeQuickModal === "physics") {
      setPhysicsForm({ ...config.physics });
    }
  }, [activeQuickModal, quickModalItem, dataset, config]);

  if (!activeQuickModal) return null;

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    if (activeQuickModal === "press") {
      upsertPress(pressForm, quickModalItem?.machine_id);
    } else if (activeQuickModal === "mold") {
      upsertMold(moldForm, quickModalItem?.mold_id);
    } else if (activeQuickModal === "resin") {
      upsertResin(resinForm, quickModalItem?.resin_code);
    } else if (activeQuickModal === "order") {
      upsertOrder(orderForm, quickModalItem?.order_id);
    } else if (activeQuickModal === "physics") {
      updatePhysics(physicsForm);
    }
    closeQuickModal();
  };

  const getTitle = () => {
    switch (activeQuickModal) {
      case "press":
        return quickModalItem ? `${t.studioEdit}: ${quickModalItem.machine_id}` : t.studioAddPress;
      case "mold":
        return quickModalItem ? `${t.studioEdit}: ${quickModalItem.mold_id}` : t.studioAddMold;
      case "resin":
        return quickModalItem ? `${t.editResinInline}: ${quickModalItem.resin_code}` : t.studioAddResin;
      case "order":
        return quickModalItem ? `${t.studioEdit}: ${quickModalItem.order_id}` : t.studioAddOrder;
      case "physics":
        return t.editPhysicsBtn;
      default:
        return "";
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6">
      <div className="fixed inset-0 bg-slate-950/85 backdrop-blur-sm" onClick={closeQuickModal} />
      <div
        data-testid="quick-add-modal"
        className="relative z-10 flex max-h-[90vh] w-full max-w-xl flex-col rounded-2xl border border-slate-700/80 bg-slate-900 shadow-2xl overflow-hidden"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 bg-slate-950/80 px-6 py-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-cyan-500/20 text-cyan-400">
              {activeQuickModal === "press" && <Factory className="h-4 w-4" />}
              {activeQuickModal === "mold" && <Layers className="h-4 w-4" />}
              {activeQuickModal === "resin" && <Package className="h-4 w-4" />}
              {activeQuickModal === "order" && <Droplet className="h-4 w-4" />}
              {activeQuickModal === "physics" && <Sliders className="h-4 w-4" />}
            </div>
            <h3 className="text-sm font-bold text-slate-100 sm:text-base">{getTitle()}</h3>
          </div>
          <button
            onClick={closeQuickModal}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-slate-100"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSave} className="flex-1 overflow-y-auto p-6 space-y-4 text-xs">
          {/* PRESS FORM */}
          {activeQuickModal === "press" && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[11px] font-medium text-slate-400">Machine ID</label>
                  <input
                    type="text"
                    required
                    value={pressForm.machine_id}
                    onChange={(e) => setPressForm({ ...pressForm, machine_id: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 font-mono text-cyan-300"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-medium text-slate-400">Name</label>
                  <input
                    type="text"
                    required
                    value={pressForm.name}
                    onChange={(e) => setPressForm({ ...pressForm, name: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-slate-200"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-[11px] font-medium text-slate-400">Process</label>
                  <select
                    value={pressForm.process_type}
                    onChange={(e) => setPressForm({ ...pressForm, process_type: e.target.value as ProcessType })}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 text-slate-200"
                  >
                    <option value="Injection">Injection</option>
                    <option value="BlowMolding">BlowMolding</option>
                    <option value="Extrusion">Extrusion</option>
                  </select>
                </div>
                <div>
                  <label className="text-[11px] font-medium text-slate-400">Tonnage (T)</label>
                  <input
                    type="number"
                    min={50}
                    max={2000}
                    value={pressForm.tonnage}
                    onChange={(e) => setPressForm({ ...pressForm, tonnage: Number(e.target.value) })}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 font-mono text-cyan-300"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-medium text-slate-400">Status</label>
                  <select
                    value={pressForm.status}
                    onChange={(e) => setPressForm({ ...pressForm, status: e.target.value as any })}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 text-slate-200"
                  >
                    <option value="active">Active</option>
                    <option value="down">Down</option>
                    <option value="maintenance">Maintenance</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[11px] font-medium text-slate-400">Hourly Energy (kWh)</label>
                  <input
                    type="number"
                    min={5}
                    max={300}
                    value={pressForm.hourly_energy_kwh}
                    onChange={(e) => setPressForm({ ...pressForm, hourly_energy_kwh: Number(e.target.value) })}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 font-mono text-cyan-300"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-medium text-slate-400">Hourly Op Cost ({currency})</label>
                  <input
                    type="number"
                    min={20}
                    max={2000}
                    value={pressForm.hourly_operating_cost}
                    onChange={(e) => setPressForm({ ...pressForm, hourly_operating_cost: Number(e.target.value) })}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 font-mono text-cyan-300"
                  />
                </div>
              </div>

              <div className="flex items-center gap-2 pt-2">
                <input
                  type="checkbox"
                  id="qa-hot-runner"
                  checked={pressForm.supports_hot_runner}
                  onChange={(e) => setPressForm({ ...pressForm, supports_hot_runner: e.target.checked })}
                  className="rounded border-slate-700 bg-slate-950 text-cyan-500"
                />
                <label htmlFor="qa-hot-runner" className="text-xs text-slate-300">
                  Supports Hot-Runner Manifolds
                </label>
              </div>
            </div>
          )}

          {/* MOLD FORM */}
          {activeQuickModal === "mold" && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[11px] font-medium text-slate-400">Mold ID</label>
                  <input
                    type="text"
                    required
                    value={moldForm.mold_id}
                    onChange={(e) => setMoldForm({ ...moldForm, mold_id: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 font-mono text-cyan-300"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-medium text-slate-400">Name</label>
                  <input
                    type="text"
                    required
                    value={moldForm.name}
                    onChange={(e) => setMoldForm({ ...moldForm, name: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-slate-200"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-[11px] font-medium text-slate-400">Cavities</label>
                  <input
                    type="number"
                    min={1}
                    max={128}
                    value={moldForm.cavities}
                    onChange={(e) => setMoldForm({ ...moldForm, cavities: Number(e.target.value) })}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 font-mono text-cyan-300"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-medium text-slate-400">Cycle Time (s)</label>
                  <input
                    type="number"
                    min={2}
                    max={120}
                    value={moldForm.cycle_time_sec}
                    onChange={(e) => setMoldForm({ ...moldForm, cycle_time_sec: Number(e.target.value) })}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 font-mono text-cyan-300"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-medium text-slate-400">Base Change (m)</label>
                  <input
                    type="number"
                    min={5}
                    max={360}
                    value={moldForm.base_changeover_mins}
                    onChange={(e) => setMoldForm({ ...moldForm, base_changeover_mins: Number(e.target.value) })}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 font-mono text-cyan-300"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-[11px] font-medium text-slate-400">Current Shots</label>
                  <input
                    type="number"
                    min={0}
                    value={moldForm.current_shots}
                    onChange={(e) => setMoldForm({ ...moldForm, current_shots: Number(e.target.value) })}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 font-mono text-cyan-300"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-medium text-slate-400">PM Interval</label>
                  <input
                    type="number"
                    min={1000}
                    value={moldForm.maintenance_interval_shots}
                    onChange={(e) => setMoldForm({ ...moldForm, maintenance_interval_shots: Number(e.target.value) })}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 font-mono text-cyan-300"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-medium text-slate-400">PM Duration (h)</label>
                  <input
                    type="number"
                    min={1}
                    max={48}
                    value={moldForm.pm_duration_hrs}
                    onChange={(e) => setMoldForm({ ...moldForm, pm_duration_hrs: Number(e.target.value) })}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 font-mono text-cyan-300"
                  />
                </div>
              </div>

              {/* Compatible Presses Checkboxes */}
              <div>
                <label className="text-[11px] font-medium text-slate-400">Compatible Presses</label>
                <div className="mt-1.5 flex flex-wrap gap-2">
                  {dataset?.presses.map((p) => {
                    const checked = moldForm.compatible_machines.includes(p.machine_id);
                    return (
                      <button
                        key={p.machine_id}
                        type="button"
                        onClick={() => {
                          const next = checked
                            ? moldForm.compatible_machines.filter((x) => x !== p.machine_id)
                            : [...moldForm.compatible_machines, p.machine_id];
                          setMoldForm({ ...moldForm, compatible_machines: next });
                        }}
                        className={`rounded-lg border px-2.5 py-1 text-xs font-mono font-medium transition ${
                          checked
                            ? "border-cyan-500/50 bg-cyan-500/20 text-cyan-200"
                            : "border-slate-800 bg-slate-950 text-slate-400 hover:border-slate-700"
                        }`}
                      >
                        {p.machine_id}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* RESIN FORM */}
          {activeQuickModal === "resin" && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[11px] font-medium text-slate-400">Resin Code</label>
                  <select
                    value={resinForm.resin_code}
                    disabled={!!quickModalItem}
                    onChange={(e) => setResinForm({ ...resinForm, resin_code: e.target.value as ResinCode })}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 font-bold text-slate-200"
                  >
                    {ALL_RESINS.map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-[11px] font-medium text-slate-400">Barrel Temp (°C)</label>
                  <input
                    type="number"
                    min={150}
                    max={350}
                    value={resinForm.barrel_temp_c}
                    onChange={(e) => setResinForm({ ...resinForm, barrel_temp_c: Number(e.target.value) })}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 font-mono text-cyan-300"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[11px] font-medium text-slate-400">Virgin Stock (kg)</label>
                  <input
                    type="number"
                    min={0}
                    step={50}
                    value={resinForm.virgin_available_kg}
                    onChange={(e) => setResinForm({ ...resinForm, virgin_available_kg: Number(e.target.value) })}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 font-mono text-cyan-300"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-medium text-slate-400">Virgin Cost / kg ({currency})</label>
                  <input
                    type="number"
                    min={0.5}
                    step={0.1}
                    value={resinForm.virgin_cost_per_kg}
                    onChange={(e) => setResinForm({ ...resinForm, virgin_cost_per_kg: Number(e.target.value) })}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 font-mono text-cyan-300"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[11px] font-medium text-slate-400">Regrind Stock (kg)</label>
                  <input
                    type="number"
                    min={0}
                    step={25}
                    value={resinForm.regrind_available_kg}
                    onChange={(e) => setResinForm({ ...resinForm, regrind_available_kg: Number(e.target.value) })}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 font-mono text-cyan-300"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-medium text-slate-400">Regrind Cost / kg ({currency})</label>
                  <input
                    type="number"
                    min={0.1}
                    step={0.1}
                    value={resinForm.regrind_cost_per_kg}
                    onChange={(e) => setResinForm({ ...resinForm, regrind_cost_per_kg: Number(e.target.value) })}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 font-mono text-cyan-300"
                  />
                </div>
              </div>

              <div>
                <label className="text-[11px] font-medium text-slate-400">Pre-Drying Lead Time (hrs)</label>
                <input
                  type="number"
                  min={0}
                  max={24}
                  value={resinForm.drying_lead_time_hrs}
                  onChange={(e) => setResinForm({ ...resinForm, drying_lead_time_hrs: Number(e.target.value) })}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 font-mono text-cyan-300"
                />
              </div>
            </div>
          )}

          {/* ORDER FORM */}
          {activeQuickModal === "order" && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[11px] font-medium text-slate-400">Order ID</label>
                  <input
                    type="text"
                    required
                    value={orderForm.order_id}
                    onChange={(e) => setOrderForm({ ...orderForm, order_id: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 font-mono text-cyan-300"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-medium text-slate-400">Customer</label>
                  <input
                    type="text"
                    required
                    value={orderForm.customer}
                    onChange={(e) => setOrderForm({ ...orderForm, customer: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-slate-200"
                  />
                </div>
              </div>

              <div>
                <label className="text-[11px] font-medium text-slate-400">SKU Name</label>
                <input
                  type="text"
                  required
                  value={orderForm.sku_name}
                  onChange={(e) => setOrderForm({ ...orderForm, sku_name: e.target.value })}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-slate-200"
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-[11px] font-medium text-slate-400">Mold</label>
                  <select
                    value={orderForm.mold_id}
                    onChange={(e) => setOrderForm({ ...orderForm, mold_id: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 text-slate-200 font-mono"
                  >
                    {dataset?.molds.map((m) => (
                      <option key={m.mold_id} value={m.mold_id}>{m.mold_id} ({m.name})</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-[11px] font-medium text-slate-400">Resin</label>
                  <select
                    value={orderForm.resin_code}
                    onChange={(e) => setOrderForm({ ...orderForm, resin_code: e.target.value as ResinCode })}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 text-slate-200 font-bold"
                  >
                    {dataset?.resins.map((r) => (
                      <option key={r.resin_code} value={r.resin_code}>{r.resin_code}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-[11px] font-medium text-slate-400">Color</label>
                  <select
                    value={orderForm.color}
                    onChange={(e) => {
                      const c = e.target.value as PlasticColor;
                      const r = ALL_COLORS.find((x) => x.color === c)?.rank ?? 1;
                      setOrderForm({ ...orderForm, color: c, color_rank: r });
                    }}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 text-slate-200"
                  >
                    {ALL_COLORS.map((c) => (
                      <option key={c.color} value={c.color}>{COLOR_LABELS[lang][c.color]}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-[11px] font-medium text-slate-400">Quantity (pcs)</label>
                  <input
                    type="number"
                    min={100}
                    step={100}
                    value={orderForm.quantity_pcs}
                    onChange={(e) => setOrderForm({ ...orderForm, quantity_pcs: Number(e.target.value) })}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 font-mono text-cyan-300"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-medium text-slate-400">Part Wt (g)</label>
                  <input
                    type="number"
                    min={1}
                    value={orderForm.part_weight_g}
                    onChange={(e) => setOrderForm({ ...orderForm, part_weight_g: Number(e.target.value) })}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 font-mono text-cyan-300"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-medium text-slate-400">Due (hr)</label>
                  <input
                    type="number"
                    min={1}
                    max={config.physics.horizon_hrs}
                    value={orderForm.due_hr}
                    onChange={(e) => setOrderForm({ ...orderForm, due_hr: Number(e.target.value) })}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 font-mono text-cyan-300"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[11px] font-medium text-slate-400">Unit Selling Price (SAR/pc)</label>
                  <input
                    type="number"
                    min={0}
                    step={0.005}
                    value={orderForm.unit_selling_price ?? 0}
                    onChange={(e) => setOrderForm({ ...orderForm, unit_selling_price: Number(e.target.value) })}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 font-mono text-cyan-300"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-medium text-slate-400">Discount %</label>
                  <input
                    type="number"
                    min={0}
                    max={100}
                    step={0.5}
                    value={orderForm.discount_pct ?? 0}
                    onChange={(e) => setOrderForm({ ...orderForm, discount_pct: Number(e.target.value) })}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 font-mono text-white"
                  />
                </div>
              </div>

              <div className="flex items-center gap-2 pt-2">
                <input
                  type="checkbox"
                  id="qa-export"
                  checked={orderForm.is_export}
                  onChange={(e) => setOrderForm({ ...orderForm, is_export: e.target.checked })}
                  className="rounded border-slate-700 bg-slate-950 text-cyan-500"
                />
                <label htmlFor="qa-export" className="text-xs text-slate-300">
                  Priority Export Contract (Strict OTIF)
                </label>
              </div>
            </div>
          )}

          {/* PHYSICS FORM */}
          {activeQuickModal === "physics" && (
            <div className="space-y-4">
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 space-y-3">
                <h4 className="text-xs font-semibold text-slate-200">Purge & Changeover Physics</h4>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-[10px] text-slate-400">Light→Dark Purge (mins)</label>
                    <input
                      type="number"
                      min={5}
                      max={120}
                      value={physicsForm.light_to_dark_purge_mins}
                      onChange={(e) => setPhysicsForm({ ...physicsForm, light_to_dark_purge_mins: Number(e.target.value) })}
                      className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 font-mono text-cyan-300"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-400">Light→Dark Scrap (kg)</label>
                    <input
                      type="number"
                      min={1}
                      max={50}
                      step={0.5}
                      value={physicsForm.light_to_dark_purge_kg}
                      onChange={(e) => setPhysicsForm({ ...physicsForm, light_to_dark_purge_kg: Number(e.target.value) })}
                      className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 font-mono text-cyan-300"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-400">Dark→Light Purge (mins)</label>
                    <input
                      type="number"
                      min={30}
                      max={360}
                      value={physicsForm.dark_to_light_purge_mins}
                      onChange={(e) => setPhysicsForm({ ...physicsForm, dark_to_light_purge_mins: Number(e.target.value) })}
                      className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 font-mono text-cyan-300"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-400">Dark→Light Scrap (kg)</label>
                    <input
                      type="number"
                      min={5}
                      max={150}
                      step={0.5}
                      value={physicsForm.dark_to_light_purge_kg}
                      onChange={(e) => setPhysicsForm({ ...physicsForm, dark_to_light_purge_kg: Number(e.target.value) })}
                      className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 font-mono text-cyan-300"
                    />
                  </div>
                </div>
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 space-y-3">
                <h4 className="text-xs font-semibold text-slate-200">Energy & Horizon Rules</h4>
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="text-[10px] text-slate-400">Tariff ({currency}/kWh)</label>
                    <input
                      type="number"
                      min={0.05}
                      max={2.0}
                      step={0.01}
                      value={physicsForm.energy_tariff_per_kwh}
                      onChange={(e) => setPhysicsForm({ ...physicsForm, energy_tariff_per_kwh: Number(e.target.value) })}
                      className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 font-mono text-cyan-300"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-400">Peak Multiplier (x)</label>
                    <input
                      type="number"
                      min={1.0}
                      max={3.0}
                      step={0.1}
                      value={physicsForm.peak_tariff_multiplier}
                      onChange={(e) => setPhysicsForm({ ...physicsForm, peak_tariff_multiplier: Number(e.target.value) })}
                      className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 font-mono text-cyan-300"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-400">Horizon (hrs)</label>
                    <input
                      type="number"
                      min={24}
                      max={336}
                      step={24}
                      value={physicsForm.horizon_hrs}
                      onChange={(e) => setPhysicsForm({ ...physicsForm, horizon_hrs: Number(e.target.value) })}
                      className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 font-mono text-cyan-300"
                    />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Modal Actions */}
          <div className="flex items-center justify-end gap-2 border-t border-slate-800 pt-4">
            <button
              type="button"
              onClick={closeQuickModal}
              className="rounded-lg bg-slate-800 px-3.5 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-700"
            >
              {t.studioCancel}
            </button>
            <button
              type="submit"
              data-testid="btn-save-quick-modal"
              className="rounded-lg bg-cyan-500 px-4 py-1.5 text-xs font-bold text-slate-950 hover:bg-cyan-400 transition"
            >
              {t.studioSave}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
