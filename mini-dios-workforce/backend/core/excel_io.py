"""4-Tab Plastic Factory Excel Bridge (`openpyxl`): Template Generator, Upload Parser & Executive Brief Export."""
from __future__ import annotations

import io
import json
from typing import Any, Optional

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from .ontology import (
    COLOR_RANKS,
    Currency,
    DowntimeWindow,
    Issue,
    Mold,
    PlantDataset,
    PressMachine,
    ProductionOrder,
    ResinStock,
    SolveResult,
)
from .seed import demo_dataset

# Styling palette
_HEADER_FILL = PatternFill("solid", fgColor="0F172A")
_SUBHEADER_FILL = PatternFill("solid", fgColor="1E293B")
_ZEBRA_FILL = PatternFill("solid", fgColor="F8FAFC")
_BANNER_FILL = PatternFill("solid", fgColor="0B1120")
_SUBBANNER_FILL = PatternFill("solid", fgColor="E2E8F0")
_HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
_BANNER_FONT = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
_SUBBANNER_FONT = Font(name="Calibri", size=10, italic=True, color="1E293B")
_BOLD_FONT = Font(name="Calibri", size=10, bold=True, color="0F172A")
_BODY_FONT = Font(name="Calibri", size=10, color="0F172A")
_WHITE_BOLD_FONT = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
_GOOD_FONT = Font(name="Calibri", size=10, bold=True, color="166534")
_WARN_FONT = Font(name="Calibri", size=10, bold=True, color="92400E")
_THIN = Side(style="thin", color="CBD5E1")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)

# Plastic color fills for the Executive Gantt Schedule tab
_PLASTIC_COLOR_STYLE: dict[str, tuple[PatternFill, Font]] = {
    "Natural": (PatternFill("solid", fgColor="F1F5F9"), _BOLD_FONT),
    "White": (PatternFill("solid", fgColor="FFFFFF"), _BOLD_FONT),
    "Yellow": (PatternFill("solid", fgColor="FEF08A"), _BOLD_FONT),
    "Blue": (PatternFill("solid", fgColor="BFDBFE"), _BOLD_FONT),
    "Red": (PatternFill("solid", fgColor="FECACA"), _BOLD_FONT),
    "Black": (PatternFill("solid", fgColor="1E293B"), _WHITE_BOLD_FONT),
}

_STATUS_FILLS = {
    "PASS": PatternFill("solid", fgColor="DCFCE7"),
    "FAIL": PatternFill("solid", fgColor="FEE2E2"),
    "GOOD": PatternFill("solid", fgColor="ECFDF5"),
    "WARN": PatternFill("solid", fgColor="FFFBEB"),
    "CHANGEOVER": PatternFill("solid", fgColor="FEF3C7"),
    "BREAKDOWN": PatternFill("solid", fgColor="FFE4E6"),
}

_PRESSES_COLS = [
    "machine_id",
    "name",
    "process_type",
    "tonnage",
    "supports_hot_runner",
    "hourly_energy_kwh",
    "hourly_operating_cost",
    "status",
    "downtime_windows",
]
_MOLDS_COLS = [
    "mold_id",
    "name",
    "compatible_machines",
    "cavities",
    "cycle_time_sec",
    "is_hot_runner",
    "base_changeover_mins",
    "current_shots",
    "maintenance_interval_shots",
    "pm_duration_hrs",
]
_RESIN_COLS = [
    "resin_code",
    "virgin_available_kg",
    "virgin_cost_per_kg",
    "regrind_available_kg",
    "regrind_cost_per_kg",
    "drying_lead_time_hrs",
    "barrel_temp_c",
]
_ORDERS_COLS = [
    "order_id",
    "customer",
    "sku_name",
    "mold_id",
    "resin_code",
    "color",
    "color_rank",
    "quantity_pcs",
    "part_weight_g",
    "max_regrind_pct",
    "due_hr",
    "late_penalty_per_hr",
    "is_export",
]


def _style_header(ws, headers: list[str]) -> None:
    ws.append(headers)
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = _BORDER
    ws.freeze_panes = "A2"
    ws.row_dimensions[1].height = 24


def _autofit(
    ws,
    min_width: int = 12,
    max_width: int = 44,
    skip_rows: Optional[set[int]] = None,
    min_col_widths: Optional[dict[int, int]] = None,
) -> None:
    skip = skip_rows or set()
    mins = min_col_widths or {}
    for col_cells in ws.columns:
        col_idx = col_cells[0].column
        col_letter = get_column_letter(col_idx)
        longest = max(min_width, mins.get(col_idx, 0))
        for cell in col_cells:
            if cell.row in skip or cell.value is None:
                continue
            longest = max(longest, len(str(cell.value)) + 4)
        ws.column_dimensions[col_letter].width = min(max_width, longest)


def _format_downtime_str(windows: list[DowntimeWindow]) -> str:
    return "; ".join(f"{w.start_hr:g}-{w.end_hr:g}:{w.reason}" for w in windows)


def _parse_downtime_str(val: Any) -> list[DowntimeWindow]:
    if val is None or str(val).strip() == "":
        return []
    out: list[DowntimeWindow] = []
    for chunk in str(val).split(";"):
        part = chunk.strip()
        if not part:
            continue
        reason = "Scheduled Maintenance"
        if ":" in part:
            rng, reason = part.split(":", 1)
            reason = reason.strip() or reason
        else:
            rng = part
        if "-" not in rng:
            raise ValueError(f"Invalid downtime window '{part}' (expected 'start-end' or 'start-end:reason')")
        s_str, e_str = rng.split("-", 1)
        out.append(DowntimeWindow(start_hr=float(s_str.strip()), end_hr=float(e_str.strip()), reason=reason))
    return out


def build_template_workbook(sample: bool = True, dataset: Optional[PlantDataset] = None) -> bytes:
    """Generate a clean 4-tab Plastics Excel workbook (`Presses`, `Molds`, `Resin_Inventory`, `Production_Orders`)."""
    wb = Workbook()
    ds = dataset if dataset is not None else (demo_dataset() if sample else None)

    # Tab 1: Presses
    ws_press = wb.active
    ws_press.title = "Presses"
    _style_header(ws_press, _PRESSES_COLS)
    if ds is not None:
        for p in ds.presses:
            ws_press.append(
                [
                    p.machine_id,
                    p.name,
                    p.process_type,
                    p.tonnage,
                    "TRUE" if p.supports_hot_runner else "FALSE",
                    p.hourly_energy_kwh,
                    p.hourly_operating_cost,
                    p.status,
                    _format_downtime_str(p.downtime_windows),
                ]
            )
    dv_proc = DataValidation(type="list", formula1='"Injection,BlowMolding,Extrusion"', allow_blank=False)
    dv_stat = DataValidation(type="list", formula1='"active,down,maintenance"', allow_blank=False)
    dv_bool = DataValidation(type="list", formula1='"TRUE,FALSE"', allow_blank=False)
    ws_press.add_data_validation(dv_proc)
    ws_press.add_data_validation(dv_stat)
    ws_press.add_data_validation(dv_bool)
    dv_proc.add("C2:C200")
    dv_bool.add("E2:E200")
    dv_stat.add("H2:H200")
    _autofit(ws_press)

    # Tab 2: Molds
    ws_molds = wb.create_sheet("Molds")
    _style_header(ws_molds, _MOLDS_COLS)
    if ds is not None:
        for m in ds.molds:
            ws_molds.append(
                [
                    m.mold_id,
                    m.name,
                    ", ".join(m.compatible_machines),
                    m.cavities,
                    m.cycle_time_sec,
                    "TRUE" if m.is_hot_runner else "FALSE",
                    m.base_changeover_mins,
                    m.current_shots,
                    m.maintenance_interval_shots,
                    m.pm_duration_hrs,
                ]
            )
    dv_hr = DataValidation(type="list", formula1='"TRUE,FALSE"', allow_blank=False)
    ws_molds.add_data_validation(dv_hr)
    dv_hr.add("F2:F200")
    _autofit(ws_molds)

    # Tab 3: Resin_Inventory
    ws_resins = wb.create_sheet("Resin_Inventory")
    _style_header(ws_resins, _RESIN_COLS)
    if ds is not None:
        for r in ds.resins:
            ws_resins.append(
                [
                    r.resin_code,
                    r.virgin_available_kg,
                    r.virgin_cost_per_kg,
                    r.regrind_available_kg,
                    r.regrind_cost_per_kg,
                    r.drying_lead_time_hrs,
                    r.barrel_temp_c,
                ]
            )
    dv_res = DataValidation(type="list", formula1='"PP,HDPE,LDPE,PET,ABS,PVC"', allow_blank=False)
    ws_resins.add_data_validation(dv_res)
    dv_res.add("A2:A100")
    _autofit(ws_resins)

    # Tab 4: Production_Orders
    ws_orders = wb.create_sheet("Production_Orders")
    _style_header(ws_orders, _ORDERS_COLS)
    if ds is not None:
        for o in ds.orders:
            ws_orders.append(
                [
                    o.order_id,
                    o.customer,
                    o.sku_name,
                    o.mold_id,
                    o.resin_code,
                    o.color,
                    o.color_rank,
                    o.quantity_pcs,
                    o.part_weight_g,
                    o.max_regrind_pct,
                    o.due_hr,
                    o.late_penalty_per_hr,
                    "TRUE" if o.is_export else "FALSE",
                ]
            )
    dv_ores = DataValidation(type="list", formula1='"PP,HDPE,LDPE,PET,ABS,PVC"', allow_blank=False)
    dv_col = DataValidation(type="list", formula1='"Natural,White,Yellow,Blue,Red,Black"', allow_blank=False)
    dv_exp = DataValidation(type="list", formula1='"TRUE,FALSE"', allow_blank=False)
    ws_orders.add_data_validation(dv_ores)
    ws_orders.add_data_validation(dv_col)
    ws_orders.add_data_validation(dv_exp)
    dv_ores.add("E2:E500")
    dv_col.add("F2:F500")
    dv_exp.add("M2:M500")
    _autofit(ws_orders)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _parse_bool(val: Any) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    return str(val or "").strip().lower() in ("true", "1", "yes", "y")


def _parse_csv(val: Any) -> list[str]:
    if val is None:
        return []
    return [part.strip() for part in str(val).split(",") if part.strip()]


def _sheet_rows(ws) -> tuple[dict[str, int], list[tuple[int, list[Any]]]]:
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return {}, []
    header_map = {str(h).strip().lower(): i for i, h in enumerate(rows[0]) if h is not None}
    data_rows: list[tuple[int, list[Any]]] = []
    for idx, row in enumerate(rows[1:], start=2):
        if all(cell is None or str(cell).strip() == "" for cell in row):
            continue
        data_rows.append((idx, list(row)))
    return header_map, data_rows


def _get(row: list[Any], cols: dict[str, int], name: str, default: Any = None) -> Any:
    idx = cols.get(name.lower())
    if idx is None or idx >= len(row) or row[idx] is None or str(row[idx]).strip() == "":
        return default
    return row[idx]


def parse_workbook_bytes(
    content: bytes, dataset_name: str = "Uploaded Plastic Plant Workbook"
) -> tuple[PlantDataset, list[Issue]]:
    """Parse a 4-tab Plastics Excel workbook into a `PlantDataset`, capturing cell errors cleanly."""
    issues: list[Issue] = []

    def add_err(msg: str, etype: str, eid: str) -> None:
        issues.append(Issue(code="XLSX_PARSE", severity="error", message=msg, entity_type=etype, entity_id=eid))  # type: ignore[arg-type]

    try:
        wb = load_workbook(io.BytesIO(content), data_only=True)
    except Exception as exc:
        add_err(f"Could not open Excel file: {exc}", "dataset", "workbook")
        return PlantDataset(name=dataset_name, presses=[], molds=[], resins=[], orders=[]), issues

    required_tabs = ["Presses", "Molds", "Resin_Inventory", "Production_Orders"]
    sheet_lookup = {name.lower(): wb[name] for name in wb.sheetnames}
    for tab in required_tabs:
        if tab.lower() not in sheet_lookup:
            add_err(f"Missing required worksheet '{tab}'.", "dataset", tab)

    # 1. Presses
    presses: list[PressMachine] = []
    if "presses" in sheet_lookup:
        cols, rows = _sheet_rows(sheet_lookup["presses"])
        for rnum, row in rows:
            mid = str(_get(row, cols, "machine_id", "")).strip()
            if not mid:
                add_err(f"Presses row {rnum}: missing machine_id.", "press", f"Presses!A{rnum}")
                continue
            try:
                presses.append(
                    PressMachine(
                        machine_id=mid,
                        name=str(_get(row, cols, "name", mid)).strip(),
                        process_type=str(_get(row, cols, "process_type", "Injection")).strip(),  # type: ignore[arg-type]
                        tonnage=int(float(_get(row, cols, "tonnage", 250))),
                        supports_hot_runner=_parse_bool(_get(row, cols, "supports_hot_runner", True)),
                        hourly_energy_kwh=float(_get(row, cols, "hourly_energy_kwh", 45.0)),
                        hourly_operating_cost=float(_get(row, cols, "hourly_operating_cost", 180.0)),
                        status=str(_get(row, cols, "status", "active")).strip().lower(),  # type: ignore[arg-type]
                        downtime_windows=_parse_downtime_str(_get(row, cols, "downtime_windows", "")),
                    )
                )
            except Exception as exc:
                add_err(f"Presses row {rnum} ({mid}): {exc}", "press", f"Presses!Row{rnum}")

    # 2. Molds
    molds: list[Mold] = []
    if "molds" in sheet_lookup:
        cols, rows = _sheet_rows(sheet_lookup["molds"])
        for rnum, row in rows:
            mold_id = str(_get(row, cols, "mold_id", "")).strip()
            if not mold_id:
                add_err(f"Molds row {rnum}: missing mold_id.", "mold", f"Molds!A{rnum}")
                continue
            try:
                molds.append(
                    Mold(
                        mold_id=mold_id,
                        name=str(_get(row, cols, "name", mold_id)).strip(),
                        compatible_machines=_parse_csv(_get(row, cols, "compatible_machines", "")),
                        cavities=int(float(_get(row, cols, "cavities", 4))),
                        cycle_time_sec=float(_get(row, cols, "cycle_time_sec", 15.0)),
                        is_hot_runner=_parse_bool(_get(row, cols, "is_hot_runner", False)),
                        base_changeover_mins=int(float(_get(row, cols, "base_changeover_mins", 90))),
                        current_shots=int(float(_get(row, cols, "current_shots", 0))),
                        maintenance_interval_shots=int(float(_get(row, cols, "maintenance_interval_shots", 500_000))),
                        pm_duration_hrs=float(_get(row, cols, "pm_duration_hrs", 4.0)),
                    )
                )
            except Exception as exc:
                add_err(f"Molds row {rnum} ({mold_id}): {exc}", "mold", f"Molds!Row{rnum}")

    # 3. Resin_Inventory
    resins: list[ResinStock] = []
    if "resin_inventory" in sheet_lookup:
        cols, rows = _sheet_rows(sheet_lookup["resin_inventory"])
        for rnum, row in rows:
            code = str(_get(row, cols, "resin_code", "")).strip().upper()
            if not code:
                add_err(f"Resin_Inventory row {rnum}: missing resin_code.", "resin", f"Resin_Inventory!A{rnum}")
                continue
            try:
                resins.append(
                    ResinStock(
                        resin_code=code,  # type: ignore[arg-type]
                        virgin_available_kg=float(_get(row, cols, "virgin_available_kg", 5000.0)),
                        virgin_cost_per_kg=float(_get(row, cols, "virgin_cost_per_kg", 5.5)),
                        regrind_available_kg=float(_get(row, cols, "regrind_available_kg", 500.0)),
                        regrind_cost_per_kg=float(_get(row, cols, "regrind_cost_per_kg", 3.0)),
                        drying_lead_time_hrs=float(_get(row, cols, "drying_lead_time_hrs", 0.0)),
                        barrel_temp_c=int(float(_get(row, cols, "barrel_temp_c", 210))),
                    )
                )
            except Exception as exc:
                add_err(f"Resin_Inventory row {rnum} ({code}): {exc}", "resin", f"Resin_Inventory!Row{rnum}")

    # 4. Production_Orders
    orders: list[ProductionOrder] = []
    if "production_orders" in sheet_lookup:
        cols, rows = _sheet_rows(sheet_lookup["production_orders"])
        for rnum, row in rows:
            oid = str(_get(row, cols, "order_id", "")).strip()
            if not oid:
                add_err(f"Production_Orders row {rnum}: missing order_id.", "order", f"Production_Orders!A{rnum}")
                continue
            try:
                color = str(_get(row, cols, "color", "Natural")).strip().title()
                rank_raw = _get(row, cols, "color_rank")
                rank = int(float(rank_raw)) if rank_raw is not None else COLOR_RANKS.get(color, 1)  # type: ignore[arg-type]
                orders.append(
                    ProductionOrder(
                        order_id=oid,
                        customer=str(_get(row, cols, "customer", "Customer")).strip(),
                        sku_name=str(_get(row, cols, "sku_name", oid)).strip(),
                        mold_id=str(_get(row, cols, "mold_id", "")).strip(),
                        resin_code=str(_get(row, cols, "resin_code", "PP")).strip().upper(),  # type: ignore[arg-type]
                        color=color,  # type: ignore[arg-type]
                        color_rank=rank,
                        quantity_pcs=int(float(_get(row, cols, "quantity_pcs", 10000))),
                        part_weight_g=float(_get(row, cols, "part_weight_g", 10.0)),
                        max_regrind_pct=float(_get(row, cols, "max_regrind_pct", 0.0)),
                        due_hr=float(_get(row, cols, "due_hr", 168.0)),
                        late_penalty_per_hr=float(_get(row, cols, "late_penalty_per_hr", 300.0)),
                        is_export=_parse_bool(_get(row, cols, "is_export", False)),
                    )
                )
            except Exception as exc:
                add_err(f"Production_Orders row {rnum} ({oid}): {exc}", "order", f"Production_Orders!Row{rnum}")

    return PlantDataset(name=dataset_name, presses=presses, molds=molds, resins=resins, orders=orders), issues


def _convert_money(amount: float, from_cur: Currency, to_cur: Currency, fx_egp_per_sar: float) -> float:
    if from_cur == to_cur:
        return round(amount, 2)
    if from_cur == "SAR" and to_cur == "EGP":
        return round(amount * fx_egp_per_sar, 2)
    if from_cur == "EGP" and to_cur == "SAR":
        return round(amount / fx_egp_per_sar, 2)
    return round(amount, 2)


def export_brief_workbook(
    result: SolveResult,
    currency_override: Optional[Currency] = None,
) -> bytes:
    """Export the polished Executive Plastics Optimization Brief (`.xlsx`):
    1. `Purge_Scrap_Savings` — Executive ROI Scorecard (SAR & EGP), Active Scenarios, 6/6 Constraint Audit.
    2. `Executive_Gantt_Schedule` — Color-coded Press-by-Press Production & Changeover Schedule.
    3. `Resin_Consumption` — Per-resin Virgin, Regrind, Purge Scrap & Inventory Utilization.
    4. `Audit_Trail` — Cryptographic SHA-256 hashes, weights, and OR-Tools solver metadata.
    """
    wb = Workbook()
    out_cur: Currency = currency_override or result.currency
    other_cur: Currency = "EGP" if out_cur == "SAR" else "SAR"
    fx = result.fx_egp_per_sar
    conv = lambda val: _convert_money(val, result.currency, out_cur, fx)
    conv_other = lambda val: _convert_money(val, result.currency, other_cur, fx)

    # ---- Tab 1: Purge & Scrap Savings (Executive Scorecard) --------------------------------
    ws_sc = wb.active
    ws_sc.title = "Purge_Scrap_Savings"

    ws_sc.merge_cells("A1:E1")
    ws_sc["A1"] = f"Mini-DIOS Plastics — Executive Optimization Brief ({result.dataset_name})"
    ws_sc["A1"].fill = _BANNER_FILL
    ws_sc["A1"].font = _BANNER_FONT
    ws_sc["A1"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws_sc.row_dimensions[1].height = 30

    ws_sc.merge_cells("A2:E2")
    ws_sc["A2"] = (
        f"Run ID: {result.run_id}  |  Solver: OR-Tools CP-SAT ({result.status})  |  Runtime: {result.solve_time_ms} ms  |  "
        f"Currency: {out_cur} (1 SAR = {fx:.2f} EGP)  |  Peak Avoid: {'ON' if result.audit.config.avoid_peak_tariff_hrs else 'OFF'}  |  "
        f"Ramadan Mode: {'ON' if result.audit.config.ramadan_shift_mode else 'OFF'}"
    )
    ws_sc["A2"].fill = _SUBBANNER_FILL
    ws_sc["A2"].font = _SUBBANNER_FONT
    ws_sc["A2"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws_sc.row_dimensions[2].height = 22
    ws_sc.append([])

    sc = result.scorecard
    ws_sc.append(["Executive KPI", "Naive FIFO Baseline", "CP-SAT Optimized", "Savings / Delta", "ROI Impact"])
    hdr_row = ws_sc.max_row
    ws_sc.row_dimensions[hdr_row].height = 24
    for c_idx in range(1, 6):
        c = ws_sc.cell(row=hdr_row, column=c_idx)
        c.fill = _HEADER_FILL
        c.font = _HEADER_FONT
        c.alignment = Alignment(horizontal="center" if c_idx > 1 else "left", vertical="center")
        c.border = _BORDER

    metric_rows = [
        (f"Total Weekly Factory Cost ({out_cur})", conv(sc.total_cost.baseline), conv(sc.total_cost.optimized), conv(sc.cash_savings), f"{sc.cash_savings_pct:+.1f}% Saved", "#,##0", sc.cash_savings >= 0),
        (f"Total Weekly Cost Equivalent ({other_cur})", conv_other(sc.total_cost.baseline), conv_other(sc.total_cost.optimized), conv_other(sc.cash_savings), f"{sc.cash_savings_pct:+.1f}% Saved", "#,##0", sc.cash_savings >= 0),
        ("Purge Resin Scrap (kg)", sc.purge_scrap_kg.baseline, sc.purge_scrap_kg.optimized, sc.purge_scrap_kg_saved, f"{sc.purge_scrap_kg.delta_pct:+.1f}% Scrap", "#,##0.0", sc.purge_scrap_kg_saved >= 0),
        (f"Purge Scrap Cost Saved ({out_cur})", conv(result.baseline.kpis.purge_scrap_cost), conv(result.optimized.kpis.purge_scrap_cost), conv(sc.purge_scrap_cost_saved), "Resin Saved", "#,##0", sc.purge_scrap_cost_saved >= 0),
        ("Changeover & Purge Time (hrs)", sc.changeover_hours.baseline, sc.changeover_hours.optimized, sc.changeover_hours_saved, f"{sc.changeover_hours.delta_pct:+.1f}% Hrs", "#,##0.00", sc.changeover_hours_saved >= 0),
        (f"Electricity Cost ({out_cur})", conv(sc.energy_cost.baseline), conv(sc.energy_cost.optimized), conv(sc.energy_cost.baseline - sc.energy_cost.optimized), f"{sc.energy_cost.delta_pct:+.1f}%", "#,##0", sc.energy_cost.delta <= 0),
        (f"Late Export Penalties ({out_cur})", conv(sc.late_penalty_cost.baseline), conv(sc.late_penalty_cost.optimized), conv(sc.late_penalty_cost.baseline - sc.late_penalty_cost.optimized), f"{sc.late_penalty_cost.delta_pct:+.1f}%", "#,##0", sc.late_penalty_cost.delta <= 0),
        ("On-Time In-Full — OTIF (%)", sc.otif_pct.baseline / 100.0, sc.otif_pct.optimized / 100.0, sc.otif_pct.delta / 100.0, f"{sc.otif_pct.delta:+.1f} pts", "0.0%", sc.otif_pct.delta >= 0),
        ("Plant OEE (%)", sc.oee_pct.baseline / 100.0, sc.oee_pct.optimized / 100.0, sc.oee_pct.delta / 100.0, f"{sc.oee_pct.delta:+.1f} pts", "0.0%", sc.oee_pct.delta >= 0),
    ]
    for idx, (lbl, bv, ov, dv, roi, nfmt, good) in enumerate(metric_rows):
        ws_sc.append([lbl, bv, ov, dv, roi])
        r = ws_sc.max_row
        ws_sc.row_dimensions[r].height = 20
        for c_idx in range(1, 6):
            cell = ws_sc.cell(row=r, column=c_idx)
            cell.border = _BORDER
            if c_idx == 1:
                cell.font = _BOLD_FONT
                cell.alignment = Alignment(horizontal="left", vertical="center")
                if idx % 2 == 1:
                    cell.fill = _ZEBRA_FILL
            elif c_idx in (2, 3, 4):
                cell.number_format = nfmt
                cell.font = _BOLD_FONT if c_idx == 3 else _BODY_FONT
                cell.alignment = Alignment(horizontal="right", vertical="center")
                if idx % 2 == 1:
                    cell.fill = _ZEBRA_FILL
            else:
                cell.font = _GOOD_FONT if good else _WARN_FONT
                cell.fill = _STATUS_FILLS["GOOD" if good else "WARN"]
                cell.alignment = Alignment(horizontal="center", vertical="center")

    # Hard Constraint 6/6 Audit
    ws_sc.append([])
    ws_sc.append(["Hard Constraint Audit (Zero-Violation Guarantee)", "Violations", "Status", "Verification Notes", ""])
    ch_row = ws_sc.max_row
    for c_idx in range(1, 6):
        c = ws_sc.cell(row=ch_row, column=c_idx)
        c.fill = _SUBHEADER_FILL
        c.font = _HEADER_FONT
        c.border = _BORDER
    for chk in result.audit.constraints_verified:
        ws_sc.append([f"{chk.id}: {chk.name}", chk.violations, "PASS" if chk.passed else "FAIL", "; ".join(chk.details) or "0 violations verified", ""])
        r = ws_sc.max_row
        st = ws_sc.cell(row=r, column=3)
        st.fill = _STATUS_FILLS["PASS" if chk.passed else "FAIL"]
        st.font = _GOOD_FONT if chk.passed else _WARN_FONT
        st.alignment = Alignment(horizontal="center", vertical="center")
        for c_idx in range(1, 6):
            ws_sc.cell(row=r, column=c_idx).border = _BORDER

    _autofit(ws_sc, min_width=16, max_width=52, skip_rows={1, 2}, min_col_widths={1: 38, 2: 20, 3: 20, 4: 20, 5: 22})

    # ---- Tab 2: Color-Coded Executive Gantt Schedule ---------------------------------------
    ws_gantt = wb.create_sheet("Executive_Gantt_Schedule")
    g_headers = [
        "Press",
        "Seq #",
        "Order ID",
        "Customer",
        "SKU",
        "Mold",
        "Resin",
        "Plastic Color",
        "Setup/Purge (min)",
        "Purge Scrap (kg)",
        "Transition",
        "Start (Hr)",
        "End (Hr)",
        "Due (Hr)",
        "Late (Hr)",
        "Export",
        f"Purge Cost ({out_cur})",
    ]
    _style_header(ws_gantt, g_headers)

    for j in result.optimized.jobs:
        ws_gantt.append(
            [
                j.machine_id,
                j.sequence_index if j.scheduled else "-",
                j.order_id,
                j.customer,
                j.sku_name,
                j.mold_id,
                j.resin_code,
                j.color,
                j.setup_mins,
                j.purge_scrap_kg,
                j.transition_type.replace("_", " ").title(),
                round(j.start_min / 60.0, 2) if j.scheduled else "-",
                round(j.end_min / 60.0, 2) if j.scheduled else "-",
                j.due_hr,
                j.tardiness_hrs,
                "YES" if j.is_export else "NO",
                conv(j.purge_cost),
            ]
        )
        r = ws_gantt.max_row
        ws_gantt.row_dimensions[r].height = 20
        for c_idx in range(1, len(g_headers) + 1):
            cell = ws_gantt.cell(row=r, column=c_idx)
            cell.border = _BORDER
            cell.font = _BODY_FONT
        # Visually color-code the Plastic Color cell!
        col_cell = ws_gantt.cell(row=r, column=8)
        fill, fnt = _PLASTIC_COLOR_STYLE.get(j.color, (_ZEBRA_FILL, _BOLD_FONT))
        col_cell.fill = fill
        col_cell.font = fnt
        col_cell.alignment = Alignment(horizontal="center", vertical="center")
        if j.setup_mins > 0:
            ws_gantt.cell(row=r, column=9).fill = _STATUS_FILLS["CHANGEOVER"]

    ws_gantt.auto_filter.ref = f"A1:{get_column_letter(len(g_headers))}{ws_gantt.max_row}"
    _autofit(ws_gantt, min_width=12, max_width=36)

    # ---- Tab 3: Resin Consumption ----------------------------------------------------------
    ws_res = wb.create_sheet("Resin_Consumption")
    r_headers = [
        "Resin",
        "Virgin Cap (kg)",
        "Virgin Used (kg)",
        "Purge Scrap (kg)",
        "Regrind Cap (kg)",
        "Regrind Used (kg)",
        "Remaining Virgin (kg)",
        "Utilization (%)",
        f"Virgin Price ({out_cur}/kg)",
    ]
    _style_header(ws_res, r_headers)
    for ru in result.optimized.resin_usage:
        ws_res.append(
            [
                ru.resin_code,
                ru.virgin_available_kg,
                ru.virgin_used_kg,
                ru.purge_scrap_kg,
                ru.regrind_available_kg,
                ru.regrind_used_kg,
                ru.remaining_virgin_kg,
                ru.utilization_pct / 100.0,
                conv(ru.virgin_cost_per_kg),
            ]
        )
        r = ws_res.max_row
        for c_idx in range(1, len(r_headers) + 1):
            c = ws_res.cell(row=r, column=c_idx)
            c.border = _BORDER
            c.font = _BOLD_FONT if c_idx == 1 else _BODY_FONT
        ws_res.cell(row=r, column=8).number_format = "0.0%"
    _autofit(ws_res, min_width=14, max_width=28)

    # ---- Tab 4: Audit Trail ----------------------------------------------------------------
    ws_aud = wb.create_sheet("Audit_Trail")
    _style_header(ws_aud, ["Audit Field", "Value"])
    for k, v in [
        ("run_id", result.run_id),
        ("created_at", result.created_at),
        ("dataset_name", result.dataset_name),
        ("status", result.status),
        ("solve_time_ms", result.solve_time_ms),
        ("inputs_sha256", result.audit.inputs_sha256),
        ("schedule_sha256", result.audit.schedule_sha256),
        ("ortools_version", result.audit.ortools_version),
        ("weights", json.dumps(result.audit.weights)),
        ("applied_scenarios", json.dumps([a.model_dump() for a in result.applied_scenarios])),
        ("config", result.audit.config.model_dump_json()),
    ]:
        ws_aud.append([k, v])
        ws_aud.cell(row=ws_aud.max_row, column=1).font = _BOLD_FONT
        ws_aud.cell(row=ws_aud.max_row, column=1).border = _BORDER
        ws_aud.cell(row=ws_aud.max_row, column=2).border = _BORDER
    _autofit(ws_aud, min_width=22, max_width=90)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def export_integration_schedule_workbook(
    result: SolveResult,
    currency_override: Optional[Currency] = None,
) -> bytes:
    """Export the 4-sheet Integration-Ready Schedule Workbook (`/api/export/schedule.xlsx`):
    1. `Press Schedule`
    2. `Workforce Shifts`
    3. `KPIs & Savings`
    4. `Risk Radar`
    """
    wb = Workbook()
    out_cur: Currency = currency_override or result.currency
    fx = result.fx_egp_per_sar
    conv = lambda val: _convert_money(val, result.currency, out_cur, fx)

    # Sheet 1: Press Schedule
    ws_press = wb.active
    ws_press.title = "Press Schedule"
    p_headers = [
        "Press ID",
        "Press Name",
        "Seq #",
        "Order ID",
        "Customer",
        "SKU Name",
        "Container Group",
        "Mold ID",
        "Resin",
        "Color",
        "Qty (pcs)",
        "Gross Wt (kg)",
        "Setup Start (Hr)",
        "Run Start (Hr)",
        "Run End (Hr)",
        "Due (Hr)",
        "Setup (min)",
        "Run (min)",
        "Purge Scrap (kg)",
        "Container Wait (Hr)",
        "Tardiness (Hr)",
        "Export",
        "Status",
        f"Total Job Cost ({out_cur})",
    ]
    _style_header(ws_press, p_headers)
    for j in result.optimized.jobs:
        job_cost = conv(j.resin_cost + j.purge_cost + j.energy_cost + j.operating_cost + j.late_penalty_cost)
        ws_press.append(
            [
                j.machine_id,
                j.machine_name,
                j.sequence_index if j.scheduled else 0,
                j.order_id,
                j.customer,
                j.sku_name,
                j.container_group_id or "-",
                j.mold_id,
                j.resin_code,
                j.color,
                j.quantity_pcs,
                j.gross_weight_kg,
                round(j.setup_start_min / 60.0, 2) if j.scheduled else "-",
                round(j.start_min / 60.0, 2) if j.scheduled else "-",
                round(j.end_min / 60.0, 2) if j.scheduled else "-",
                j.due_hr,
                j.setup_mins,
                j.duration_mins,
                j.purge_scrap_kg,
                j.container_wait_hrs,
                j.tardiness_hrs,
                "YES" if j.is_export else "NO",
                "SCHEDULED" if j.scheduled else "UNSCHEDULED",
                job_cost,
            ]
        )
    _autofit(ws_press, min_width=12, max_width=36)

    # Sheet 2: Workforce Shifts
    ws_wf = wb.create_sheet("Workforce Shifts")
    wf_headers = [
        "Worker ID",
        "Name",
        "Role",
        "Sun",
        "Mon",
        "Tue",
        "Wed",
        "Thu",
        "Fri",
        "Sat",
        "Shifts Worked",
        "Regular Hrs",
        "Overtime Hrs",
        "Total Hrs",
        f"Weekly Labor Cost ({out_cur})",
    ]
    _style_header(ws_wf, wf_headers)
    if result.workforce is not None:
        wf_cur = result.workforce.currency
        conv_wf = lambda val: _convert_money(val, wf_cur, out_cur, fx)
        for row in result.workforce.optimized.rosters:
            cells = list(row.cells) + ["OFF"] * max(0, 7 - len(row.cells))
            ws_wf.append(
                [
                    row.worker_id,
                    row.name,
                    row.role,
                    *cells[:7],
                    row.shifts_worked,
                    row.regular_hours,
                    row.overtime_hours,
                    row.weekly_hours,
                    conv_wf(row.labor_cost),
                ]
            )
    _autofit(ws_wf, min_width=11, max_width=30)

    # Sheet 3: KPIs & Savings
    ws_kpi = wb.create_sheet("KPIs & Savings")
    _style_header(ws_kpi, ["KPI / Financial Line Item", "FIFO Baseline", "CP-SAT Optimized", "Delta / Savings", "Unit"])
    bk = result.baseline.kpis
    ok = result.optimized.kpis
    fin = result.financials
    kpi_rows = [
        ("Recognized Revenue", conv(fin.baseline.recognized_revenue), conv(fin.optimized.recognized_revenue), conv(fin.optimized.recognized_revenue - fin.baseline.recognized_revenue), out_cur),
        ("Total Operating Cost", conv(fin.baseline.total_operating_cost), conv(fin.optimized.total_operating_cost), conv(fin.baseline.total_operating_cost - fin.optimized.total_operating_cost), out_cur),
        ("Net Operating Profit", conv(fin.baseline.net_operating_profit), conv(fin.optimized.net_operating_profit), conv(fin.optimized.net_operating_profit - fin.baseline.net_operating_profit), out_cur),
        ("Total Weekly Cash Savings", "-", conv(fin.total_weekly_savings), conv(fin.total_weekly_savings), out_cur),
        ("Annualized Projected Savings", "-", conv(fin.annual_projected_savings), conv(fin.annual_projected_savings), out_cur),
        ("Purge Resin Scrap", bk.purge_scrap_kg, ok.purge_scrap_kg, round(bk.purge_scrap_kg - ok.purge_scrap_kg, 1), "kg"),
        ("Changeover & Purge Time", bk.changeover_hours, ok.changeover_hours, round(bk.changeover_hours - ok.changeover_hours, 2), "hrs"),
        ("Plant OEE", bk.oee_pct, ok.oee_pct, round(ok.oee_pct - bk.oee_pct, 1), "%"),
        ("Export & Order OTIF", bk.otif_pct, ok.otif_pct, round(ok.otif_pct - bk.otif_pct, 1), "%"),
        ("Finished-Goods Warehouse Utilization", bk.warehouse_utilization_pct, ok.warehouse_utilization_pct, round(ok.warehouse_utilization_pct - bk.warehouse_utilization_pct, 1), "%"),
        ("Trapped Container Working Capital", conv(bk.trapped_working_capital), conv(ok.trapped_working_capital), conv(bk.trapped_working_capital - ok.trapped_working_capital), out_cur),
        ("WIP Holding Days", bk.wip_holding_days, ok.wip_holding_days, round(bk.wip_holding_days - ok.wip_holding_days, 2), "ton-days"),
    ]
    for r_item in kpi_rows:
        ws_kpi.append(list(r_item))
    _autofit(ws_kpi, min_width=16, max_width=44)

    # Sheet 4: Risk Radar
    ws_risk = wb.create_sheet("Risk Radar")
    _style_header(
        ws_risk,
        ["Alert ID", "Severity", "Category", "Entity", "Title (EN)", "Metric", f"Financial Exposure ({out_cur})", "Recommended Mitigation"],
    )
    if result.risk_radar is not None:
        for a in result.risk_radar.alerts:
            ws_risk.append(
                [
                    a.alert_id,
                    a.severity.upper(),
                    a.category,
                    f"{a.entity_type}:{a.entity_id}",
                    a.title_en,
                    f"{a.metric_label}: {a.metric_value}",
                    conv(a.financial_exposure),
                    a.suggested_prompt_en,
                ]
            )
    _autofit(ws_risk, min_width=14, max_width=52)

    out_buf = io.BytesIO()
    wb.save(out_buf)
    return out_buf.getvalue()


def export_integration_schedule_csv(
    result: SolveResult,
    currency_override: Optional[Currency] = None,
) -> bytes:
    """Export a clean flat press-run schedule CSV (`/api/export/schedule.csv`)."""
    import csv

    out_cur: Currency = currency_override or result.currency
    fx = result.fx_egp_per_sar
    conv = lambda val: _convert_money(val, result.currency, out_cur, fx)

    headers = [
        "order_id",
        "customer",
        "sku_name",
        "container_group_id",
        "machine_id",
        "sequence_index",
        "mold_id",
        "resin_code",
        "color",
        "quantity_pcs",
        "gross_weight_kg",
        "setup_start_hr",
        "start_hr",
        "end_hr",
        "due_hr",
        "setup_mins",
        "duration_mins",
        "purge_scrap_kg",
        "virgin_kg",
        "regrind_kg",
        "container_wait_hrs",
        "tardiness_hrs",
        "is_export",
        "scheduled",
        "total_job_cost",
        "currency",
    ]
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(headers)

    for j in result.optimized.jobs:
        total_job_cost = conv(j.resin_cost + j.purge_cost + j.energy_cost + j.operating_cost + j.late_penalty_cost)
        writer.writerow(
            [
                j.order_id,
                j.customer,
                j.sku_name,
                j.container_group_id or "",
                j.machine_id,
                j.sequence_index if j.scheduled else 0,
                j.mold_id,
                j.resin_code,
                j.color,
                j.quantity_pcs,
                j.gross_weight_kg,
                round(j.setup_start_min / 60.0, 2) if j.scheduled else 0.0,
                round(j.start_min / 60.0, 2) if j.scheduled else 0.0,
                round(j.end_min / 60.0, 2) if j.scheduled else 0.0,
                j.due_hr,
                j.setup_mins,
                j.duration_mins,
                j.purge_scrap_kg,
                j.virgin_kg,
                j.regrind_kg,
                j.container_wait_hrs,
                j.tardiness_hrs,
                j.is_export,
                j.scheduled,
                total_job_cost,
                out_cur,
            ]
        )
    return buf.getvalue().encode("utf-8")


def export_integration_erp_payload(
    result: SolveResult,
    dataset: Optional[PlantDataset] = None,
    currency_override: Optional[Currency] = None,
) -> dict[str, Any]:
    """Build a versioned integration JSON payload (`/api/export/erp-payload.json`) suitable for Odoo / SAP B1 / custom ERPs."""
    out_cur: Currency = currency_override or result.currency
    fx = result.fx_egp_per_sar
    conv = lambda val: _convert_money(val, result.currency, out_cur, fx)
    ok = result.optimized.kpis
    fin = result.financials

    return {
        "schema_version": "mini-dios-plastics-erp/v1.3",
        "compatible_targets": ["Odoo MRP (mrp.production / mrp.workorder)", "SAP Business One (OWOR)", "Custom Factory MES/ERP"],
        "run_id": result.run_id,
        "generated_at": result.created_at,
        "plant_name": result.dataset_name,
        "currency": out_cur,
        "fx_egp_per_sar": fx,
        "solver_telemetry": {
            "engine": "Google OR-Tools CP-SAT",
            "ortools_version": result.audit.ortools_version,
            "status": result.status,
            "solve_time_ms": result.solve_time_ms,
            "inputs_sha256": result.audit.inputs_sha256,
            "schedule_sha256": result.audit.schedule_sha256,
            "all_hard_constraints_passed": result.audit.all_hard_constraints_passed,
            "container_sync_enabled": result.audit.config.container_sync_enabled,
        },
        "work_orders": [
            {
                "work_order_id": f"WO-{j.order_id}",
                "order_id": j.order_id,
                "customer": j.customer,
                "sku_name": j.sku_name,
                "container_group_id": j.container_group_id,
                "workcenter_id": j.machine_id,
                "workcenter_name": j.machine_name,
                "tooling_mold_id": j.mold_id,
                "tooling_mold_name": j.mold_name,
                "sequence_index": j.sequence_index,
                "scheduled": j.scheduled,
                "material": {
                    "resin_code": j.resin_code,
                    "color": j.color,
                    "color_rank": j.color_rank,
                    "quantity_pcs": j.quantity_pcs,
                    "gross_weight_kg": j.gross_weight_kg,
                    "virgin_resin_kg": j.virgin_kg,
                    "regrind_resin_kg": j.regrind_kg,
                    "purge_scrap_kg": j.purge_scrap_kg,
                },
                "timing": {
                    "setup_start_hr": round(j.setup_start_min / 60.0, 2),
                    "production_start_hr": round(j.start_min / 60.0, 2),
                    "production_end_hr": round(j.end_min / 60.0, 2),
                    "due_hr": j.due_hr,
                    "setup_mins": j.setup_mins,
                    "duration_mins": j.duration_mins,
                    "container_wait_hrs": j.container_wait_hrs,
                    "tardiness_hrs": j.tardiness_hrs,
                    "transition_type": j.transition_type,
                },
                "costs": {
                    "resin_cost": conv(j.resin_cost),
                    "purge_cost": conv(j.purge_cost),
                    "energy_cost": conv(j.energy_cost),
                    "operating_cost": conv(j.operating_cost),
                    "late_penalty_cost": conv(j.late_penalty_cost),
                    "currency": out_cur,
                },
            }
            for j in result.optimized.jobs
        ],
        "mold_maintenance_windows": [
            pm.model_dump(mode="json") for pm in (result.optimized.mold_pm_windows or [])
        ],
        "container_consolidations": [
            {
                **cg.model_dump(mode="json"),
                "total_revenue_value": conv(cg.total_revenue_value),
                "trapped_working_capital": conv(cg.trapped_working_capital),
                "holding_cost": conv(cg.holding_cost),
                "currency": out_cur,
            }
            for cg in (result.optimized.container_groups or [])
        ],
        "workforce_shift_roster": (
            [
                {
                    "worker_id": r.worker_id,
                    "name": r.name,
                    "role": r.role,
                    "daily_shifts_sun_to_sat": r.cells,
                    "regular_hours": r.regular_hours,
                    "overtime_hours": r.overtime_hours,
                    "weekly_hours": r.weekly_hours,
                    "weekly_labor_cost": _convert_money(
                        r.labor_cost, result.workforce.currency, out_cur, fx
                    ),
                }
                for r in result.workforce.optimized.rosters
            ]
            if result.workforce
            else []
        ),
        "kpis_and_financials": {
            "recognized_revenue": conv(fin.optimized.recognized_revenue),
            "net_operating_profit": conv(fin.optimized.net_operating_profit),
            "net_margin_pct": fin.optimized.net_margin_pct,
            "total_weekly_savings": conv(fin.total_weekly_savings),
            "annual_projected_savings": conv(fin.annual_projected_savings),
            "purge_scrap_kg": ok.purge_scrap_kg,
            "changeover_hours": ok.changeover_hours,
            "oee_pct": ok.oee_pct,
            "otif_pct": ok.otif_pct,
            "warehouse_utilization_pct": ok.warehouse_utilization_pct,
            "peak_warehouse_tons": ok.peak_warehouse_tons,
            "trapped_working_capital": conv(ok.trapped_working_capital),
            "wip_holding_days": ok.wip_holding_days,
        },
        "risk_alerts": (
            [
                {
                    "alert_id": a.alert_id,
                    "severity": a.severity,
                    "category": a.category,
                    "entity_type": a.entity_type,
                    "entity_id": a.entity_id,
                    "title_en": a.title_en,
                    "financial_exposure": conv(a.financial_exposure),
                }
                for a in result.risk_radar.alerts
            ]
            if result.risk_radar
            else []
        ),
    }
