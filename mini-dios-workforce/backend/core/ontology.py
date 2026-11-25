"""Mini-DIOS Plastics — Domain Ontology, Plant Physics Helpers, Pre-Solve Validator & Result Schemas.

Everything in this module is pure, deterministic industrial plastics data modeling.
No optimization or LLM calls happen here.

Conventions
-----------
* Weekly planning horizon = 168 hours (Sun 00:00 -> Sat 24:00) = 10,080 minutes.
* Extended scheduling tail = 240 hours (14,400 minutes) so late orders remain schedulable
  and accurately penalized rather than causing artificial infeasibility.
* Base monetary values in the seeded plant are denominated in SAR; EGP conversion uses
  `config.fx_egp_per_sar` (default 13.0 EGP / SAR).
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

# --------------------------------------------------------------------------------------------
# Constants & Industrial Physics Parameters
# --------------------------------------------------------------------------------------------
DAYS = 7
HOURS_PER_WEEK = 168
HORIZON_MINS = HOURS_PER_WEEK * 60  # 10,080 mins
EXTENDED_HORIZON_HOURS = 264
EXTENDED_HORIZON_MINS = EXTENDED_HORIZON_HOURS * 60  # 15,840 mins
MAX_HORIZON_HOURS = 336
DAY_NAMES = ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")

# MENA industrial electricity peak window defaults (13:00-17:00 daily, +40% kWh surcharge)
PEAK_TARIFF_START_HR = 13
PEAK_TARIFF_END_HR = 17
PEAK_TARIFF_SURCHARGE_PCT = 0.40

# Ramadan Shift Mode defaults (18:00-20:00 daily Iftar changeover blackout, +15% labor cost at 6h shift)
RAMADAN_BLACKOUT_START_HR = 18
RAMADAN_BLACKOUT_END_HR = 20
RAMADAN_LABOR_MULTIPLIER = 1.15

ProcessType = Literal["Injection", "BlowMolding", "Extrusion"]
MachineStatus = Literal["active", "down", "maintenance"]
ResinCode = Literal["PP", "HDPE", "LDPE", "PET", "ABS", "PVC"]
PlasticColor = Literal["Natural", "White", "Yellow", "Blue", "Red", "Black"]
Currency = Literal["EGP", "SAR"]
Severity = Literal["error", "warning", "info"]

COLOR_RANKS: dict[PlasticColor, int] = {
    "Natural": 1,
    "White": 2,
    "Yellow": 3,
    "Blue": 4,
    "Red": 5,
    "Black": 6,
}

# Polyolefins (PP, HDPE, LDPE) share compatible melt temperature bands (~195-215°C).
# PVC, ABS, and PET require aggressive full-barrel purges when switching across families.
POLYOLEFIN_RESINS: frozenset[str] = frozenset({"PP", "HDPE", "LDPE"})


def is_incompatible_resin_switch(resin_a: str, resin_b: str) -> bool:
    """Return True if switching barrel resin from `resin_a` to `resin_b` requires full purge."""
    if resin_a == resin_b:
        return False
    if resin_a in POLYOLEFIN_RESINS and resin_b in POLYOLEFIN_RESINS:
        return False
    return True


# --------------------------------------------------------------------------------------------
# Core Domain Entities
# --------------------------------------------------------------------------------------------
class DowntimeWindow(BaseModel):
    start_hr: float = Field(ge=0, le=MAX_HORIZON_HOURS)
    end_hr: float = Field(ge=0, le=MAX_HORIZON_HOURS)
    reason: str = "Scheduled Maintenance"


class PressMachine(BaseModel):
    machine_id: str = Field(min_length=1)
    name: str
    process_type: ProcessType = "Injection"
    tonnage: int = Field(gt=0, description="Clamping force in metric tons (e.g., 150-800T)")
    supports_hot_runner: bool = True
    hourly_energy_kwh: float = Field(gt=0)
    hourly_operating_cost: float = Field(gt=0, description="Base operating & labor cost per hour in SAR")
    status: MachineStatus = "active"
    downtime_windows: list[DowntimeWindow] = Field(default_factory=list)


class Mold(BaseModel):
    mold_id: str = Field(min_length=1)
    name: str
    compatible_machines: list[str] = Field(default_factory=list)
    cavities: int = Field(gt=0)
    cycle_time_sec: float = Field(gt=0)
    is_hot_runner: bool = False
    base_changeover_mins: int = Field(ge=15, le=480)
    current_shots: int = Field(ge=0)
    maintenance_interval_shots: int = Field(gt=0)
    pm_duration_hrs: float = Field(gt=0, le=72)

    @property
    def shot_utilization_pct(self) -> float:
        return round((self.current_shots / max(self.maintenance_interval_shots, 1)) * 100.0, 1)


class ResinStock(BaseModel):
    resin_code: ResinCode
    virgin_available_kg: float = Field(ge=0)
    virgin_cost_per_kg: float = Field(gt=0, description="Virgin resin cost per kg in SAR")
    regrind_available_kg: float = Field(ge=0)
    regrind_cost_per_kg: float = Field(ge=0, description="Regrind resin cost per kg in SAR")
    drying_lead_time_hrs: float = Field(ge=0, le=48)
    barrel_temp_c: int = Field(ge=120, le=360)


class ProductionOrder(BaseModel):
    order_id: str = Field(min_length=1)
    customer: str
    sku_name: str
    mold_id: str = Field(min_length=1)
    resin_code: ResinCode
    color: PlasticColor
    color_rank: int = Field(default=0, ge=0, le=6)
    quantity_pcs: int = Field(gt=0)
    part_weight_g: float = Field(gt=0)
    max_regrind_pct: float = Field(default=0.0, ge=0.0, le=50.0)
    due_hr: float = Field(gt=0, le=MAX_HORIZON_HOURS)
    late_penalty_per_hr: float = Field(ge=0, description="Late penalty per hour in SAR")
    is_export: bool = False
    container_group_id: Optional[str] = Field(
        default=None,
        description="Optional export container consolidation group ID (e.g. 'CNT-RIYADH-01')",
    )
    unit_selling_price: float = Field(default=0.0, ge=0.0, description="Selling price per finished piece in SAR")
    discount_pct: float = Field(default=0.0, ge=0.0, le=100.0, description="Optional order discount percentage")

    @model_validator(mode="after")
    def _sync_color_rank(self) -> "ProductionOrder":
        if self.color_rank == 0:
            self.color_rank = COLOR_RANKS[self.color]
        return self


# --------------------------------------------------------------------------------------------
# Dynamic Composable Disruption Scenarios
# --------------------------------------------------------------------------------------------
class MachineBreakdown(BaseModel):
    machine_id: str = Field(min_length=1)
    start_hr: float = Field(ge=0, le=MAX_HORIZON_HOURS)
    duration_hrs: float = Field(gt=0, le=MAX_HORIZON_HOURS)


class ResinShortage(BaseModel):
    resin_code: ResinCode
    available_pct_reduction: float = Field(default=0.0, ge=0.0, le=95.0)
    virgin_price_spike_pct: float = Field(default=0.0, ge=0.0, le=300.0)


class MoldPmLock(BaseModel):
    mold_id: str = Field(min_length=1)
    duration_hrs: float = Field(gt=0, le=72)


class ScenarioDisruptions(BaseModel):
    """Composable plant disruptions — supports ANY combination simultaneously."""

    machine_breakdowns: list[MachineBreakdown] = Field(default_factory=list)
    resin_shortages: list[ResinShortage] = Field(default_factory=list)
    mold_pm_locks: list[MoldPmLock] = Field(default_factory=list)
    rush_orders: list[ProductionOrder] = Field(default_factory=list)
    allow_regrind_override_pct: Optional[float] = Field(default=None, ge=0.0, le=40.0)


class PlantPhysicsConfig(BaseModel):
    """Editable industrial plant physics & simulation solver parameters."""

    horizon_hrs: int = Field(168, ge=24, le=336, description="Planning horizon in hours")
    light_to_dark_purge_mins: int = Field(25, ge=0, le=240)
    light_to_dark_purge_kg: float = Field(4.0, ge=0.0, le=200.0)
    dark_to_light_purge_mins: int = Field(135, ge=0, le=480)
    dark_to_light_purge_kg: float = Field(32.0, ge=0.0, le=300.0)
    incompatible_resin_purge_mins: int = Field(180, ge=0, le=600)
    incompatible_resin_purge_kg: float = Field(48.0, ge=0.0, le=500.0)
    energy_tariff_per_kwh: float = Field(0.32, gt=0.0, le=20.0, description="Electricity tariff per kWh in SAR")
    peak_tariff_multiplier: float = Field(1.4, ge=1.0, le=5.0)
    peak_start_hr: int = Field(13, ge=0, le=23)
    peak_end_hr: int = Field(17, ge=1, le=24)
    holding_cost_per_kg_per_day: float = Field(0.05, ge=0.0, le=50.0)
    ramadan_shift_hours: int = Field(6, ge=4, le=12)
    max_solve_seconds: float = Field(5.0, ge=1.0, le=30.0)
    weekly_fixed_overhead: float = Field(
        18500.0, ge=0.0, le=5_000_000.0, description="Weekly fixed factory rent/admin/indirect labor overhead in SAR"
    )
    scrap_regrind_recovery_pct: float = Field(
        10.0, ge=0.0, le=100.0, description="Percentage credit recovered when purge/flash scrap is granulated"
    )
    annual_operating_weeks: int = Field(50, ge=1, le=52, description="Operating weeks per year for annualized projections")
    fg_storage_capacity_tons: float = Field(
        22.0, gt=0.0, le=5000.0, description="Finished-goods warehouse storage capacity ceiling in metric tons"
    )
    wip_holding_cost_per_ton_day: float = Field(
        85.0, ge=0.0, le=50000.0, description="Warehouse & working-capital holding cost per metric ton per day in SAR"
    )

    @model_validator(mode="after")
    def _validate_peak_window(self) -> "PlantPhysicsConfig":
        if self.peak_end_hr <= self.peak_start_hr:
            raise ValueError("peak_end_hr must be greater than peak_start_hr")
        return self


WorkerRole = Literal["Press_Operator", "Mold_Technician", "QC_Inspector", "Material_Handler", "Shift_Supervisor"]
WORKER_ROLES: tuple[str, ...] = (
    "Press_Operator",
    "Mold_Technician",
    "QC_Inspector",
    "Material_Handler",
    "Shift_Supervisor",
)
PreferredShift = Literal["Morning", "Afternoon", "Night", "Any"]
WorkerStatus = Literal["active", "sick", "on_leave"]

# Ramadan Shift Mode caps (4 x 6h shifts, <= 36h / week)
RAMADAN_MAX_WEEKLY_HOURS = 36
RAMADAN_STANDARD_WEEKLY_HOURS = 30


class FactoryWorker(BaseModel):
    """A factory-floor employee (operator, technician, QC, handler or supervisor)."""

    worker_id: str = Field(min_length=1)
    name: str
    role: WorkerRole = "Press_Operator"
    certified_machine_ids: list[str] | Literal["ALL"] = "ALL"
    hourly_rate: float = Field(gt=0, le=10_000, description="Straight-time hourly rate in SAR")
    overtime_multiplier: float = Field(1.5, ge=1.0, le=4.0)
    max_weekly_hours: float = Field(48.0, gt=0, le=84)
    preferred_shift: PreferredShift = "Any"
    approved_leave_days: list[int] = Field(default_factory=list, description="Day indexes 0..6 (Sun..Sat)")
    status: WorkerStatus = "active"

    @model_validator(mode="after")
    def _clean_leave_days(self) -> "FactoryWorker":
        cleaned = sorted({int(d) for d in self.approved_leave_days if 0 <= int(d) <= 6})
        self.approved_leave_days = cleaned
        if isinstance(self.certified_machine_ids, list) and "ALL" in self.certified_machine_ids:
            self.certified_machine_ids = "ALL"
        return self


class WorkforceConfig(BaseModel):
    """Editable labor-scheduling parameters (embedded in SolverConfig)."""

    shift_length_hrs: Literal[6, 8] = 8
    standard_weekly_hours: int = Field(40, ge=10, le=84, description="Hours above this are paid at overtime rate")
    min_rest_hours: int = Field(11, ge=0, le=16)
    min_consecutive_days_off: int = Field(1, ge=1, le=2)
    presses_per_operator: int = Field(2, ge=1, le=4)
    w_labor_cost: int = Field(50, ge=0, le=100)
    w_coverage: int = Field(35, ge=0, le=100)
    w_fairness: int = Field(15, ge=0, le=100)

    @model_validator(mode="after")
    def _weights_not_all_zero(self) -> "WorkforceConfig":
        if self.w_labor_cost + self.w_coverage + self.w_fairness == 0:
            raise ValueError("At least one workforce objective weight must be > 0")
        return self


class SolverConfig(BaseModel):
    # Executive trade-off weights (0-100)
    w_changeover_scrap: int = Field(35, ge=0, le=100)
    w_otif: int = Field(35, ge=0, le=100)
    w_energy_cost: int = Field(15, ge=0, le=100)
    w_working_capital: int = Field(15, ge=0, le=100)

    # Operational toggles
    currency: Currency = "SAR"
    fx_egp_per_sar: float = Field(13.0, gt=0)
    energy_tariff_per_kwh: float = Field(0.32, gt=0, description="Electricity tariff per kWh in SAR")
    avoid_peak_tariff_hrs: bool = False
    ramadan_shift_mode: bool = False
    autonomous_pm_window: bool = False
    container_sync_enabled: bool = True
    max_solve_seconds: float = Field(5.0, gt=0.1, le=120.0)
    random_seed: int = 42
    num_workers: int = Field(8, ge=1, le=64)

    # Editable plant physics & simulation parameters
    physics: PlantPhysicsConfig = Field(default_factory=PlantPhysicsConfig)

    # Factory-floor workforce scheduling parameters (Tab 6)
    workforce: WorkforceConfig = Field(default_factory=WorkforceConfig)

    # Dynamic composable scenarios
    scenarios: ScenarioDisruptions = Field(default_factory=ScenarioDisruptions)

    @model_validator(mode="after")
    def _check_weights_and_sync_physics(self) -> "SolverConfig":
        if self.w_changeover_scrap + self.w_otif + self.w_energy_cost + self.w_working_capital == 0:
            raise ValueError("At least one executive objective weight must be > 0")

        # Keep top-level energy_tariff_per_kwh / max_solve_seconds and physics synced cleanly
        fields_set = self.model_fields_set
        if "energy_tariff_per_kwh" in fields_set and "physics" not in fields_set:
            self.physics.energy_tariff_per_kwh = self.energy_tariff_per_kwh
        elif "physics" in fields_set and "energy_tariff_per_kwh" not in fields_set:
            self.energy_tariff_per_kwh = self.physics.energy_tariff_per_kwh
        elif "physics" in fields_set and "energy_tariff_per_kwh" in fields_set:
            # Prefer physics if top-level stayed at default while physics was edited
            if abs(self.energy_tariff_per_kwh - 0.32) < 1e-9 and abs(self.physics.energy_tariff_per_kwh - 0.32) > 1e-9:
                self.energy_tariff_per_kwh = self.physics.energy_tariff_per_kwh
            else:
                self.physics.energy_tariff_per_kwh = self.energy_tariff_per_kwh

        if "max_solve_seconds" in fields_set and "physics" not in fields_set:
            self.physics.max_solve_seconds = min(30.0, max(1.0, float(self.max_solve_seconds)))
        elif "physics" in fields_set and "max_solve_seconds" not in fields_set:
            self.max_solve_seconds = self.physics.max_solve_seconds
        elif "physics" in fields_set and "max_solve_seconds" in fields_set:
            if abs(self.max_solve_seconds - 5.0) < 1e-9 and abs(self.physics.max_solve_seconds - 5.0) > 1e-9:
                self.max_solve_seconds = self.physics.max_solve_seconds
            else:
                self.physics.max_solve_seconds = min(30.0, max(1.0, float(self.max_solve_seconds)))

        return self


class PlantDataset(BaseModel):
    name: str = "Delta & Riyadh Polymer Packaging Plant"
    presses: list[PressMachine]
    molds: list[Mold]
    resins: list[ResinStock]
    orders: list[ProductionOrder]
    workers: list[FactoryWorker] = Field(default_factory=list)


# --------------------------------------------------------------------------------------------
# Deterministic Plant Physics Helpers (Shared Across Validator, Solver, Baseline, Verifier)
# --------------------------------------------------------------------------------------------
def order_shots(order: ProductionOrder, mold: Mold) -> int:
    return max(1, int(math.ceil(order.quantity_pcs / mold.cavities)))


def order_duration_mins(order: ProductionOrder, mold: Mold) -> int:
    """Exact production duration in minutes based on cavities and cycle time."""
    shots = order_shots(order, mold)
    raw_mins = (shots * mold.cycle_time_sec) / 60.0
    return max(30, int(math.ceil(raw_mins)))


def order_gross_weight_kg(order: ProductionOrder, mold: Mold) -> float:
    """Gross plastic requirement including runner/sprue allowance (0.5% hot-runner, 3% cold-runner)."""
    net_kg = (order.quantity_pcs * order.part_weight_g) / 1000.0
    runner_factor = 1.005 if mold.is_hot_runner else 1.03
    return round(net_kg * runner_factor, 2)


def effective_order_max_regrind_pct(order: ProductionOrder, override_pct: Optional[float]) -> float:
    """Food/pharma orders (`max_regrind_pct == 0`) NEVER accept regrind overrides.
    Non-food industrial orders (`max_regrind_pct > 0`) may be boosted up to `override_pct` (max 40%)."""
    if order.max_regrind_pct <= 0:
        return 0.0
    if override_pct is None:
        return order.max_regrind_pct
    return min(40.0, max(order.max_regrind_pct, float(override_pct)))


def compatible_active_presses(
    mold: Mold, presses_by_id: dict[str, PressMachine]
) -> list[PressMachine]:
    """Return presses that are active, listed on `mold.compatible_machines`, and support hot-runner if needed."""
    out: list[PressMachine] = []
    for mid in mold.compatible_machines:
        p = presses_by_id.get(mid)
        if p is None or p.status != "active":
            continue
        if mold.is_hot_runner and not p.supports_hot_runner:
            continue
        out.append(p)
    return out


def ramadan_labor_multiplier(physics: Optional[PlantPhysicsConfig] = None) -> float:
    """Labor multiplier during Ramadan shift mode (default 6h shift => 1.15x)."""
    hrs = physics.ramadan_shift_hours if physics is not None else 6
    return round(1.0 + max(0.0, (8.0 - float(hrs)) * 0.075), 4)


def transition_penalty(
    prev_order: ProductionOrder,
    next_order: ProductionOrder,
    prev_mold: Mold,
    next_mold: Mold,
    physics: Optional[PlantPhysicsConfig] = None,
) -> tuple[int, float, str]:
    """Asymmetric sequence-dependent changeover minutes and purge resin scrap (kg) for `prev -> next`.

    Uses `PlantPhysicsConfig` values for light-to-dark, dark-to-light, and incompatible-resin purges.
    Returns: `(setup_mins, purge_scrap_kg, transition_type)`.
    """
    ph = physics or PlantPhysicsConfig()
    same_mold = prev_order.mold_id == next_order.mold_id
    same_resin = prev_order.resin_code == next_order.resin_code
    same_color = prev_order.color == next_order.color
    incompat_resin = is_incompatible_resin_switch(prev_order.resin_code, next_order.resin_code)

    r_prev = prev_order.color_rank or COLOR_RANKS[prev_order.color]
    r_next = next_order.color_rank or COLOR_RANKS[next_order.color]

    # Case 1: Same physical mold stays mounted on the press
    if same_mold:
        if same_resin and same_color:
            return 0, 0.0, "continuous_run"
        if same_resin and r_next > r_prev:
            # Light-to-dark: fast inline pigment transition scaled around configured light_to_dark_purge
            delta = r_next - r_prev
            mins = max(0, int(round(ph.light_to_dark_purge_mins * (0.92 + 0.04 * delta))))
            scrap = round(ph.light_to_dark_purge_kg * (0.85 + 0.075 * delta), 1)
            return mins, scrap, "light_to_dark_purge"
        if same_resin and r_next < r_prev:
            # Dark-to-light: heavy barrel purge & screw cleanout scaled around configured dark_to_light_purge
            delta = r_prev - r_next
            mins = max(0, int(round(ph.dark_to_light_purge_mins * (0.88 + 0.04 * delta))))
            scrap = round(ph.dark_to_light_purge_kg * (0.85 + 0.05 * delta), 1)
            return mins, scrap, "dark_to_light_purge"
        # Different resin inside same mold
        if incompat_resin:
            return int(ph.incompatible_resin_purge_mins), round(ph.incompatible_resin_purge_kg, 1), "incompatible_resin_purge"
        # Compatible polyolefin resin transition (PP <-> HDPE <-> LDPE)
        mins = 75
        scrap = 18.0
        if r_next < r_prev:
            mins += int(round(ph.dark_to_light_purge_mins * 0.33))
            scrap += ph.dark_to_light_purge_kg * 0.375
        elif r_next > r_prev:
            mins += int(round(ph.light_to_dark_purge_mins * 0.6))
            scrap += ph.light_to_dark_purge_kg * 1.25
        return mins, round(scrap, 1), "polyolefin_resin_purge"

    # Case 2: Different mold — full physical mold swap + applicable barrel/color purge
    mins = int(next_mold.base_changeover_mins)
    scrap = 4.0 if next_mold.is_hot_runner else 10.0  # Startup runner / thermal stabilization scrap

    if incompat_resin:
        # Incompatible resin requires full barrel purge overlapping only partially with mold hang
        mins = max(int(ph.incompatible_resin_purge_mins), mins + 75)
        scrap += ph.incompatible_resin_purge_kg
        ttype = "mold_swap_incompatible_resin"
    elif not same_resin:
        mins += 40
        scrap += 18.0
        if r_next < r_prev:
            mins += int(round(ph.dark_to_light_purge_mins * 0.26))
            scrap += ph.dark_to_light_purge_kg * 0.44
        ttype = "mold_swap_resin_change"
    elif r_next < r_prev:
        delta = r_prev - r_next
        mins += int(round(ph.dark_to_light_purge_mins * 0.45)) + 5 * delta
        scrap += ph.dark_to_light_purge_kg * (0.8 + 0.06 * delta)
        ttype = "mold_swap_dark_to_light"
    elif r_next > r_prev:
        mins += int(round(ph.light_to_dark_purge_mins * 0.6))
        scrap += ph.light_to_dark_purge_kg * 1.75
        ttype = "mold_swap_light_to_dark"
    else:
        ttype = "mold_swap_same_material"

    return int(mins), round(scrap, 1), ttype


def peak_overlap_mins(
    start_min: int,
    end_min: int,
    peak_start_hr: int = PEAK_TARIFF_START_HR,
    peak_end_hr: int = PEAK_TARIFF_END_HR,
) -> int:
    """Exact minutes of interval `[start_min, end_min)` overlapping daily peak tariff window."""
    if end_min <= start_min or peak_end_hr <= peak_start_hr:
        return 0
    total = 0
    first_day = start_min // 1440
    last_day = (end_min - 1) // 1440
    for d in range(first_day, last_day + 1):
        p_start = d * 1440 + peak_start_hr * 60
        p_end = d * 1440 + peak_end_hr * 60
        ov = min(end_min, p_end) - max(start_min, p_start)
        if ov > 0:
            total += ov
    return total


def convert_sar_to_currency(amount_sar: float, currency: Currency, fx_egp_per_sar: float) -> float:
    if currency == "EGP":
        return round(amount_sar * fx_egp_per_sar, 2)
    return round(amount_sar, 2)


# --------------------------------------------------------------------------------------------
# Pre-Solve Plant Anomaly Validator
# --------------------------------------------------------------------------------------------
class Issue(BaseModel):
    code: str
    severity: Severity
    message: str
    entity_type: Literal["press", "mold", "resin", "order", "dataset", "config", "worker"]
    entity_id: Optional[str] = None


class ValidationReport(BaseModel):
    ready: bool
    error_count: int
    warning_count: int
    info_count: int
    issues: list[Issue]
    summary: dict


def validate_plant_data(
    dataset: PlantDataset, config: Optional[SolverConfig] = None
) -> ValidationReport:
    """Pre-Solve Plant Anomaly Validator detecting blocking errors and operational warnings.

    Detects:
    - Orders assigned to molds with zero active compatible presses (ERROR).
    - Total required resin weight exceeding available virgin + allowed regrind inventory (WARNING).
    - Molds past 95% of rated shot-count maintenance threshold without a scheduled PM block (WARNING).
    - Impossible deadlines: `due_hr < drying_lead_time_hrs + production_duration_hrs` (WARNING).
    - Structural reference integrity (duplicate IDs, unknown molds/resins, invalid downtime windows).
    """
    cfg = config or SolverConfig()
    issues: list[Issue] = []

    def add(code: str, sev: Severity, msg: str, etype: str, eid: Optional[str] = None) -> None:
        issues.append(Issue(code=code, severity=sev, message=msg, entity_type=etype, entity_id=eid))  # type: ignore[arg-type]

    # ---- Presses ---------------------------------------------------------------------------
    presses_by_id: dict[str, PressMachine] = {}
    for p in dataset.presses:
        if p.machine_id in presses_by_id:
            add("DUPLICATE_PRESS_ID", "error", f"Press '{p.machine_id}' is defined more than once.", "press", p.machine_id)
        presses_by_id[p.machine_id] = p
        for dw in p.downtime_windows:
            if dw.end_hr <= dw.start_hr:
                add(
                    "INVALID_DOWNTIME_WINDOW",
                    "error",
                    f"Press '{p.machine_id}' has invalid downtime window {dw.start_hr}h-{dw.end_hr}h.",
                    "press",
                    p.machine_id,
                )
    if not dataset.presses:
        add("NO_PRESSES", "error", "Plant dataset contains zero presses.", "dataset")

    active_press_count = sum(1 for p in dataset.presses if p.status == "active")
    if dataset.presses and active_press_count == 0:
        add("NO_ACTIVE_PRESSES", "error", "All presses are marked down or under maintenance.", "dataset")

    # ---- Resins (with active scenario shortages applied for readiness view) ----------------
    resins_by_code: dict[str, ResinStock] = {}
    shortage_map = {s.resin_code: s for s in cfg.scenarios.resin_shortages}
    effective_virgin_cap: dict[str, float] = {}
    effective_regrind_cap: dict[str, float] = {}

    for r in dataset.resins:
        if r.resin_code in resins_by_code:
            add("DUPLICATE_RESIN_CODE", "error", f"Resin '{r.resin_code}' is defined more than once.", "resin", r.resin_code)
        resins_by_code[r.resin_code] = r
        sh = shortage_map.get(r.resin_code)
        cut_factor = 1.0 - (sh.available_pct_reduction / 100.0) if sh else 1.0
        effective_virgin_cap[r.resin_code] = round(r.virgin_available_kg * max(0.0, cut_factor), 2)
        effective_regrind_cap[r.resin_code] = round(r.regrind_available_kg, 2)

    if not dataset.resins:
        add("NO_RESINS", "error", "Plant dataset contains zero resin inventory records.", "dataset")

    # ---- Molds -----------------------------------------------------------------------------
    molds_by_id: dict[str, Mold] = {}
    explicit_pm_molds = {lk.mold_id for lk in cfg.scenarios.mold_pm_locks}
    mold_health_summary: list[dict] = []

    for m in dataset.molds:
        if m.mold_id in molds_by_id:
            add("DUPLICATE_MOLD_ID", "error", f"Mold '{m.mold_id}' is defined more than once.", "mold", m.mold_id)
        molds_by_id[m.mold_id] = m

        unknown_presses = [mid for mid in m.compatible_machines if mid not in presses_by_id]
        if unknown_presses:
            add(
                "MOLD_UNKNOWN_PRESS",
                "warning",
                f"Mold '{m.mold_id}' references unknown press ID(s): {', '.join(unknown_presses)}.",
                "mold",
                m.mold_id,
            )

        util_pct = m.shot_utilization_pct
        needs_pm = util_pct >= 95.0
        if needs_pm and m.mold_id not in explicit_pm_molds:
            add(
                "MOLD_PM_THRESHOLD_EXCEEDED",
                "warning",
                f"Mold '{m.mold_id}' ({m.name}) is at {util_pct:.1f}% of rated shot life "
                f"({m.current_shots:,}/{m.maintenance_interval_shots:,} shots) without a manual PM block. "
                f"CP-SAT HC6 will automatically enforce a {m.pm_duration_hrs:.0f}h PM block before further runs.",
                "mold",
                m.mold_id,
            )

        compat = compatible_active_presses(m, presses_by_id)
        mold_health_summary.append(
            {
                "mold_id": m.mold_id,
                "name": m.name,
                "cavities": m.cavities,
                "cycle_time_sec": m.cycle_time_sec,
                "is_hot_runner": m.is_hot_runner,
                "current_shots": m.current_shots,
                "maintenance_interval_shots": m.maintenance_interval_shots,
                "shot_utilization_pct": util_pct,
                "pm_duration_hrs": m.pm_duration_hrs,
                "needs_pm": needs_pm or (m.mold_id in explicit_pm_molds),
                "active_compatible_presses": [p.machine_id for p in compat],
            }
        )

    # ---- Orders (Base + Composable Rush Orders) -------------------------------------------
    all_orders = [*dataset.orders, *cfg.scenarios.rush_orders]
    if not all_orders:
        add("NO_ORDERS", "error", "Plant dataset contains zero production orders.", "dataset")

    seen_orders: set[str] = set()
    resin_demand_total_kg: dict[str, float] = defaultdict(float)
    resin_min_virgin_kg: dict[str, float] = defaultdict(float)
    resin_max_regrind_kg: dict[str, float] = defaultdict(float)
    total_run_hrs = 0.0

    for o in all_orders:
        if o.order_id in seen_orders:
            add("DUPLICATE_ORDER_ID", "error", f"Order '{o.order_id}' appears more than once.", "order", o.order_id)
        seen_orders.add(o.order_id)

        mold = molds_by_id.get(o.mold_id)
        if mold is None:
            add("ORDER_UNKNOWN_MOLD", "error", f"Order '{o.order_id}' references unknown mold '{o.mold_id}'.", "order", o.order_id)
            continue

        compat = compatible_active_presses(mold, presses_by_id)
        if not compat:
            add(
                "ORDER_NO_COMPATIBLE_PRESS",
                "error",
                f"Order '{o.order_id}' ({o.sku_name}) uses mold '{o.mold_id}' which has ZERO active compatible presses "
                f"(check machine status and hot-runner compatibility).",
                "order",
                o.order_id,
            )

        resin = resins_by_code.get(o.resin_code)
        if resin is None:
            add("ORDER_UNKNOWN_RESIN", "error", f"Order '{o.order_id}' references unknown resin '{o.resin_code}'.", "order", o.order_id)
            continue

        dur_hrs = order_duration_mins(o, mold) / 60.0
        total_run_hrs += dur_hrs
        gross_kg = order_gross_weight_kg(o, mold)
        eff_regrind_pct = effective_order_max_regrind_pct(o, cfg.scenarios.allow_regrind_override_pct)
        max_rg = gross_kg * (eff_regrind_pct / 100.0)
        min_vg = gross_kg - max_rg

        resin_demand_total_kg[o.resin_code] += gross_kg
        resin_min_virgin_kg[o.resin_code] += min_vg
        resin_max_regrind_kg[o.resin_code] += max_rg

        # Impossible deadline check (accounting for drying lead time + mandatory PM block if applicable)
        pm_floor_hrs = 0.0
        if mold.shot_utilization_pct >= 95.0:
            pm_floor_hrs = max(pm_floor_hrs, mold.pm_duration_hrs)
        for lk in cfg.scenarios.mold_pm_locks:
            if lk.mold_id == mold.mold_id:
                pm_floor_hrs = max(pm_floor_hrs, lk.duration_hrs)

        earliest_start_hrs = max(resin.drying_lead_time_hrs, pm_floor_hrs)
        if o.due_hr < resin.drying_lead_time_hrs + dur_hrs:
            add(
                "IMPOSSIBLE_DEADLINE",
                "warning",
                f"Order '{o.order_id}' ({o.sku_name}) due at {o.due_hr:.1f}h cannot finish on time: "
                f"requires {resin.drying_lead_time_hrs:.1f}h {o.resin_code} pre-drying + {dur_hrs:.1f}h run "
                f"= {resin.drying_lead_time_hrs + dur_hrs:.1f}h.",
                "order",
                o.order_id,
            )
        elif o.due_hr < earliest_start_hrs + dur_hrs:
            add(
                "PM_DEADLINE_RISK",
                "warning",
                f"Order '{o.order_id}' ({o.sku_name}) due at {o.due_hr:.1f}h is tight against "
                f"mold '{mold.mold_id}' {pm_floor_hrs:.1f}h PM block + {dur_hrs:.1f}h production.",
                "order",
                o.order_id,
            )

    # ---- Resin Stock vs. Demand Checks -----------------------------------------------------
    resin_summary: list[dict] = []
    for code, r in resins_by_code.items():
        v_cap = effective_virgin_cap[code]
        rg_cap = effective_regrind_cap[code]
        req_total = round(resin_demand_total_kg.get(code, 0.0), 1)
        req_min_virgin = round(resin_min_virgin_kg.get(code, 0.0), 1)
        usable_regrind = round(min(rg_cap, resin_max_regrind_kg.get(code, 0.0)), 1)
        usable_total = round(v_cap + usable_regrind, 1)

        if req_total > usable_total + 1e-6 or req_min_virgin > v_cap + 1e-6:
            shortfall = round(max(req_total - usable_total, req_min_virgin - v_cap), 1)
            add(
                "RESIN_INVENTORY_DEFICIT",
                "warning",
                f"Resin '{code}' demand ({req_total:,.1f} kg, min virgin {req_min_virgin:,.1f} kg) exceeds "
                f"available stock ({v_cap:,.1f} kg virgin + {usable_regrind:,.1f} kg usable regrind) by "
                f"{shortfall:,.1f} kg. CP-SAT will prioritize high-penalty/export orders and flag unscheduled jobs.",
                "resin",
                code,
            )

        resin_summary.append(
            {
                "resin_code": code,
                "virgin_available_kg": round(v_cap, 1),
                "regrind_available_kg": round(rg_cap, 1),
                "usable_regrind_kg": usable_regrind,
                "demand_kg": req_total,
                "min_virgin_required_kg": req_min_virgin,
                "drying_lead_time_hrs": r.drying_lead_time_hrs,
                "barrel_temp_c": r.barrel_temp_c,
                "utilization_pct": round((req_total / max(usable_total, 1.0)) * 100.0, 1),
                "deficit_kg": round(max(0.0, req_total - usable_total, req_min_virgin - v_cap), 1),
            }
        )

    horizon_hrs = cfg.physics.horizon_hrs
    for o in all_orders:
        if o.due_hr > horizon_hrs:
            add(
                "ORDER_BEYOND_HORIZON",
                "info",
                f"Order '{o.order_id}' due at {o.due_hr:.0f}h exceeds the configured {horizon_hrs}h planning horizon.",
                "order",
                o.order_id,
            )

    # ---- Floor workforce (Tab 6) -----------------------------------------------------------
    seen_workers: set[str] = set()
    for w in dataset.workers:
        if w.worker_id in seen_workers:
            add("DUPLICATE_WORKER_ID", "error", f"Worker '{w.worker_id}' is defined more than once.", "worker", w.worker_id)
        seen_workers.add(w.worker_id)
        if isinstance(w.certified_machine_ids, list):
            unknown = [mid for mid in w.certified_machine_ids if mid not in presses_by_id]
            if unknown:
                add(
                    "WORKER_UNKNOWN_PRESS",
                    "warning",
                    f"Worker '{w.worker_id}' ({w.name}) is certified on unknown press ID(s): {', '.join(unknown)}.",
                    "worker",
                    w.worker_id,
                )
    if dataset.workers:
        active_by_role: dict[str, int] = defaultdict(int)
        for w in dataset.workers:
            if w.status == "active":
                active_by_role[w.role] += 1
        for role in WORKER_ROLES:
            if active_by_role.get(role, 0) == 0:
                add(
                    "ROLE_NO_ACTIVE_WORKERS",
                    "warning",
                    f"No active {role.replace('_', ' ')} on the roster - that role's shifts will be understaffed.",
                    "worker",
                    role,
                )

    errors = sum(1 for i in issues if i.severity == "error")
    warnings = sum(1 for i in issues if i.severity == "warning")
    infos = sum(1 for i in issues if i.severity == "info")

    summary = {
        "dataset_name": dataset.name,
        "horizon_hrs": horizon_hrs,
        "presses_total": len(dataset.presses),
        "presses_active": active_press_count,
        "molds_total": len(dataset.molds),
        "molds_needing_pm": sum(1 for m in mold_health_summary if m["needs_pm"]),
        "resins_total": len(dataset.resins),
        "orders_total": len(all_orders),
        "export_orders": sum(1 for o in all_orders if o.is_export),
        "total_production_hrs": round(total_run_hrs, 1),
        "available_press_hrs": active_press_count * horizon_hrs,
        "plant_load_pct": round((total_run_hrs / max(active_press_count * horizon_hrs, 1)) * 100.0, 1),
        "resin_balance": resin_summary,
        "mold_health": mold_health_summary,
        "workers_total": len(dataset.workers),
        "workers_active": sum(1 for w in dataset.workers if w.status == "active"),
        "workers_sick": sum(1 for w in dataset.workers if w.status == "sick"),
        "workers_on_leave": sum(1 for w in dataset.workers if w.status == "on_leave"),
    }

    return ValidationReport(
        ready=errors == 0,
        error_count=errors,
        warning_count=warnings,
        info_count=infos,
        issues=sorted(issues, key=lambda i: ({"error": 0, "warning": 1, "info": 2}[i.severity], i.code)),
        summary=summary,
    )


# --------------------------------------------------------------------------------------------
# Result & Scorecard Schemas (Shared by Solver, API, Copilot, Audit & Excel Export)
# --------------------------------------------------------------------------------------------
class ScheduledJob(BaseModel):
    order_id: str
    customer: str
    sku_name: str
    machine_id: str
    machine_name: str
    mold_id: str
    mold_name: str
    resin_code: ResinCode
    color: PlasticColor
    color_rank: int
    quantity_pcs: int
    is_export: bool
    container_group_id: Optional[str] = None
    gross_weight_kg: float = 0.0
    container_wait_hrs: float = 0.0
    scheduled: bool = True
    unscheduled_reason: Optional[str] = None
    sequence_index: int = 0
    setup_start_min: int = 0
    start_min: int = 0
    end_min: int = 0
    duration_mins: int = 0
    setup_mins: int = 0
    purge_scrap_kg: float = 0.0
    transition_type: str = "initial_setup"
    due_hr: float = 168.0
    tardiness_hrs: float = 0.0
    earliness_hrs: float = 0.0
    late_penalty_cost: float = 0.0
    virgin_kg: float = 0.0
    regrind_kg: float = 0.0
    resin_cost: float = 0.0
    purge_cost: float = 0.0
    energy_kwh: float = 0.0
    energy_cost: float = 0.0
    operating_cost: float = 0.0
    peak_overlap_mins: int = 0


class GanttBlock(BaseModel):
    block_id: str
    machine_id: str
    block_type: Literal["production", "changeover", "breakdown", "maintenance", "mold_pm"]
    label: str
    start_min: int
    end_min: int
    order_id: Optional[str] = None
    mold_id: Optional[str] = None
    resin_code: Optional[ResinCode] = None
    color: Optional[PlasticColor] = None
    purge_scrap_kg: float = 0.0
    transition_type: Optional[str] = None
    is_export: bool = False
    tardiness_hrs: float = 0.0


class ResinUsageSummary(BaseModel):
    resin_code: ResinCode
    virgin_available_kg: float
    regrind_available_kg: float
    virgin_used_kg: float
    regrind_used_kg: float
    purge_scrap_kg: float
    total_consumed_kg: float
    remaining_virgin_kg: float
    utilization_pct: float
    virgin_cost_per_kg: float


class PressSummary(BaseModel):
    machine_id: str
    name: str
    process_type: ProcessType
    tonnage: int
    status: MachineStatus
    jobs_count: int
    run_hrs: float
    changeover_hrs: float
    downtime_hrs: float
    oee_pct: float
    purge_scrap_kg: float
    energy_kwh: float
    energy_cost: float


class KpiBlock(BaseModel):
    total_cost: float
    resin_material_cost: float
    purge_scrap_cost: float
    energy_cost: float
    operating_cost: float
    late_penalty_cost: float
    wip_holding_cost: float
    changeover_hours: float
    purge_scrap_kg: float
    total_energy_kwh: float
    peak_energy_hrs: float
    total_run_hours: float
    oee_pct: float
    otif_pct: float
    on_time_orders: int
    late_orders: int
    unscheduled_orders: int
    total_orders: int
    total_tardiness_hrs: float
    virgin_resin_used_kg: float
    regrind_resin_used_kg: float
    weighted_objective: float = 0.0
    wip_holding_days: float = 0.0
    peak_warehouse_tons: float = 0.0
    fg_storage_capacity_tons: float = 22.0
    warehouse_utilization_pct: float = 0.0
    trapped_working_capital: float = 0.0
    container_wait_delay_hrs: float = 0.0


class ContainerGroupSummary(BaseModel):
    container_group_id: str
    order_ids: list[str]
    customers: list[str]
    total_weight_tons: float
    total_revenue_value: float
    first_finish_hr: float
    last_finish_hr: float
    container_due_hr: float
    spread_wait_hrs: float
    wip_ton_days: float
    trapped_working_capital: float
    holding_cost: float
    is_delayed: bool = False


class ScheduledMoldPm(BaseModel):
    mold_id: str
    mold_name: str
    machine_id: str
    start_min: int
    end_min: int
    duration_hrs: float
    mode: Literal["autonomous", "static_t0"] = "static_t0"
    trigger_reason: str = "shot_threshold_95pct"
    deadline_hr: Optional[float] = None


class SchedulePlan(BaseModel):
    jobs: list[ScheduledJob]
    gantt_blocks: list[GanttBlock]
    resin_usage: list[ResinUsageSummary]
    press_summaries: list[PressSummary]
    unscheduled_order_ids: list[str] = Field(default_factory=list)
    mold_pm_windows: list[ScheduledMoldPm] = Field(default_factory=list)
    container_groups: list[ContainerGroupSummary] = Field(default_factory=list)
    kpis: KpiBlock


class MetricCompare(BaseModel):
    baseline: float
    optimized: float
    delta: float
    delta_pct: float


class Scorecard(BaseModel):
    total_cost: MetricCompare
    cash_savings: float
    cash_savings_pct: float
    purge_scrap_kg: MetricCompare
    purge_scrap_kg_saved: float
    purge_scrap_cost_saved: float
    changeover_hours: MetricCompare
    changeover_hours_saved: float
    energy_and_late_savings: float
    energy_cost: MetricCompare
    late_penalty_cost: MetricCompare
    oee_pct: MetricCompare
    otif_pct: MetricCompare
    weighted_objective: MetricCompare


class ConstraintCheck(BaseModel):
    id: str
    name: str
    violations: int
    passed: bool
    details: list[str] = Field(default_factory=list)


class AppliedScenario(BaseModel):
    type: str
    description: str
    affected_ids: list[str] = Field(default_factory=list)


class AuditRecord(BaseModel):
    inputs_sha256: str
    schedule_sha256: str
    weights: dict[str, int]
    config: SolverConfig
    solver_params: dict
    ortools_version: str
    constraints_verified: list[ConstraintCheck]
    baseline_constraints_verified: list[ConstraintCheck]
    all_hard_constraints_passed: bool


class PlanFinancials(BaseModel):
    total_booked_revenue: float
    recognized_revenue: float
    at_risk_or_unscheduled_revenue: float
    direct_resin_cost: float
    purge_scrap_cost: float
    purge_scrap_gross_cost: float
    purge_scrap_recovery_credit: float
    energy_and_press_operating_cost: float
    late_delivery_penalties: float
    wip_holding_cost: float
    direct_labor_and_overtime_cost: float = 0.0
    variable_production_cost: float
    weekly_fixed_overhead: float
    total_operating_cost: float
    gross_profit: float
    gross_margin_pct: float
    net_operating_profit: float
    net_margin_pct: float


class SavingsBreakdown(BaseModel):
    purge_scrap_saved: float
    energy_and_operating_saved: float
    avoided_late_penalties: float
    wip_holding_saved: float
    regrind_blend_savings: float
    labor_and_overtime_saved: float = 0.0


class OrderProfitabilityItem(BaseModel):
    order_id: str
    customer: str
    sku_name: str
    quantity_pcs: int
    unit_selling_price: float
    discount_pct: float
    order_revenue: float
    direct_resin_cost: float
    allocated_energy_cost: float
    allocated_purge_cost: float
    late_penalty: float
    net_order_profit: float
    order_margin_pct: float
    scheduled: bool


class FinancialReport(BaseModel):
    currency: Currency
    annual_operating_weeks: int
    scrap_regrind_recovery_pct: float
    baseline: PlanFinancials
    optimized: PlanFinancials
    unlocked_capacity_hours: float
    unlocked_capacity_revenue_potential: float
    total_weekly_savings: float
    profit_lift_pct: float
    savings_breakdown: SavingsBreakdown
    monthly_projected_savings: float
    annual_projected_savings: float
    order_profitability: list[OrderProfitabilityItem] = Field(default_factory=list)


class WorkerWeek(BaseModel):
    """One worker's 7-day roster row. `cells[d]` is a shift label, `OFF`, `LEAVE` or `SICK`."""

    worker_id: str
    name: str
    role: WorkerRole
    cells: list[str]
    shifts_worked: int = 0
    weekly_hours: float = 0.0
    regular_hours: float = 0.0
    overtime_hours: float = 0.0
    night_shifts: int = 0
    labor_cost: float = 0.0
    preference_matches: int = 0


class ShiftDemandCell(BaseModel):
    """Required vs scheduled headcount for one (day, shift, role) slot."""

    day: int
    shift: str
    role: WorkerRole
    required: int
    scheduled: int
    reasons: list[str] = Field(default_factory=list)
    mold_change: bool = False
    active_presses: int = 0
    uncertified_presses: list[str] = Field(default_factory=list)


class WorkforceKpis(BaseModel):
    regular_labor_cost: float
    overtime_cost: float
    total_labor_cost: float
    regular_hours: float
    overtime_hours: float
    total_hours: float
    coverage_pct: float
    changeover_readiness_pct: float
    preference_match_pct: float
    understaffed_slots: int
    headcount_gap: int
    night_spread: int
    violations: int = 0
    worst_slot: Optional[str] = None
    role_coverage_pct: dict[str, float] = Field(default_factory=dict)


class WorkforcePlan(BaseModel):
    rosters: list[WorkerWeek]
    demand: list[ShiftDemandCell]
    kpis: WorkforceKpis


class WorkforceCallout(BaseModel):
    """A day-specific absence: by role+count, or by explicit worker ids."""

    role: Optional[WorkerRole] = None
    count: int = Field(1, ge=1, le=50)
    day: int = Field(0, ge=0, le=6)
    worker_ids: list[str] = Field(default_factory=list)


class WorkforceResult(BaseModel):
    currency: Currency
    ramadan_mode: bool
    shift_names: list[str]
    shift_hours: int
    shift_windows: dict[str, str]
    status: str
    solve_time_ms: int
    objective: float
    baseline_objective: float
    optimized: WorkforcePlan
    baseline: WorkforcePlan
    constraints_verified: list[ConstraintCheck]
    baseline_constraints_verified: list[ConstraintCheck]
    all_hard_constraints_passed: bool
    labor_cost_saved: float
    overtime_hours_cut: float
    callouts_applied: list[str] = Field(default_factory=list)
    reference_kpis: Optional[WorkforceKpis] = None
    notes: list[str] = Field(default_factory=list)


RiskSeverity = Literal["critical", "elevated", "watch", "healthy"]
RiskCategory = Literal[
    "late_export",
    "resin_stockout",
    "press_bottleneck",
    "mold_shot_limit",
    "workforce_fragility",
    "warehouse_congestion",
]


class RiskAlert(BaseModel):
    alert_id: str
    category: RiskCategory
    severity: Literal["critical", "elevated", "watch"]
    entity_type: Literal["order", "resin", "press", "mold", "shift", "container"]
    entity_id: str
    title_en: str
    title_ar: str
    detail_en: str
    detail_ar: str
    metric_label: str
    metric_value: str
    financial_exposure: float = 0.0
    suggested_prompt_en: str = ""
    suggested_prompt_ar: str = ""


class ResinDepletionClock(BaseModel):
    resin_code: ResinCode
    starting_virgin_kg: float
    consumed_virgin_plus_purge_kg: float
    remaining_virgin_kg: float
    utilization_pct: float
    projected_stockout_hr: Optional[float] = None
    coverage_hrs_remaining: float
    status: RiskSeverity


class RiskRadarReport(BaseModel):
    overall_risk_score: int = Field(0, ge=0, le=100)
    risk_level: RiskSeverity = "healthy"
    critical_count: int = 0
    elevated_count: int = 0
    watch_count: int = 0
    total_financial_exposure: float = 0.0
    export_at_risk_count: int = 0
    tightest_slack_order_id: Optional[str] = None
    tightest_slack_hrs: Optional[float] = None
    resin_clocks: list[ResinDepletionClock] = Field(default_factory=list)
    alerts: list[RiskAlert] = Field(default_factory=list)


class SolveResult(BaseModel):
    run_id: str
    created_at: str
    dataset_name: str
    currency: Currency
    fx_egp_per_sar: float
    status: Literal["OPTIMAL", "FEASIBLE", "INFEASIBLE", "UNKNOWN", "MODEL_INVALID"]
    solve_time_ms: int
    objective: float
    best_bound: float
    gap_pct: float
    validation: ValidationReport
    applied_scenarios: list[AppliedScenario]
    optimized: SchedulePlan
    baseline: SchedulePlan
    scorecard: Scorecard
    financials: FinancialReport
    audit: AuditRecord
    workforce: Optional[WorkforceResult] = None
    risk_radar: Optional[RiskRadarReport] = None
