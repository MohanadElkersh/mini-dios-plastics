"""Universal Execution Model (UEM) — Domain-Agnostic 6-Primitive Graph Representation.

This module defines the 6 canonical mathematical primitives into which any business ontology,
BPMN 2.0 workflow template, and DMN 1.3 decision table compile before OR-Tools CP-SAT execution:

1. `ResourceNode`         — Primary unary execution resources, secondary shared tools/resources,
                            and consumable material pools.
2. `ActivityNode`         — Schedulable operations/jobs with duration, release floor, due time,
                            resource compatibility, and dual primary/secondary consumable split bounds.
3. `TransitionMatrix`     — Asymmetric sequence-dependent setup times, transition consumable draw,
                            transition cost, and setup blackout windows on unary resources.
4. `CumulativeEnvelope`   — Global consumable pool caps, time-windowed tariff overlap envelopes,
                            and shift capacity envelopes (`CUMULATIVE_CAP`) with optional soft overflow.
5. `SynchronizationGroup` — Multi-activity synchronization barriers (e.g., shipment consolidation)
                            and floating preventive maintenance blocks with cumulative usage budgets.
6. `ObjectiveTermSpec`    — Weighted multi-objective cost and penalty coefficients in integer basis units.

Zero domain-specific vocabulary or logic is permitted in this module.
"""
from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field

ResourceKind = Literal["primary_unary", "secondary_exclusive", "consumable_pool", "workforce_pool"]
EnvelopeKind = Literal["consumable_cap", "time_window_tariff", "shift_capacity_cap"]
SyncKind = Literal["barrier_consolidation", "floating_maintenance", "fixed_maintenance"]


class TimeWindow(BaseModel):
    """A closed-open time interval `[start_min, end_min)` on the integer minute timeline."""

    start_min: int = Field(ge=0)
    end_min: int = Field(ge=0)
    label: str = ""


# --------------------------------------------------------------------------------------------
# Primitive 1: ResourceNode
# --------------------------------------------------------------------------------------------
class ResourceNode(BaseModel):
    """Primitive 1: An execution asset, shared tool, or consumable pool."""

    resource_id: str = Field(min_length=1)
    name: str
    kind: ResourceKind = "primary_unary"
    active: bool = True
    capacity: float = Field(default=1.0, ge=0.0)
    secondary_capacity: float = Field(default=0.0, ge=0.0)
    hourly_power_rate: float = Field(default=0.0, ge=0.0)
    hourly_operating_cost: float = Field(default=0.0, ge=0.0)
    unit_primary_cost: float = Field(default=0.0, ge=0.0)
    unit_secondary_cost: float = Field(default=0.0, ge=0.0)
    lead_time_floor_mins: int = Field(default=0, ge=0)
    blocked_windows: list[TimeWindow] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)


# --------------------------------------------------------------------------------------------
# Primitive 2: ActivityNode
# --------------------------------------------------------------------------------------------
class ActivityNode(BaseModel):
    """Primitive 2: A schedulable operation/task requiring primary, secondary, and consumable resources."""

    activity_id: str = Field(min_length=1)
    name: str
    duration_mins: int = Field(gt=0)
    earliest_start_min: int = Field(default=0, ge=0)
    due_min: int = Field(gt=0)
    earliness_ref_min: int = Field(default=0, ge=0)
    compatible_primary_ids: list[str] = Field(default_factory=list)
    secondary_resource_id: Optional[str] = None
    consumable_pool_id: Optional[str] = None
    gross_consumable_units_10: int = Field(default=0, ge=0, description="Total consumable demand in 0.1 base units")
    max_secondary_consumable_units_10: int = Field(
        default=0, ge=0, description="Max recycled/secondary consumable allowed in 0.1 base units"
    )
    usage_cycles: int = Field(default=0, ge=0, description="Discrete cycles/strokes accumulated on secondary resource")
    optional: bool = False
    tardiness_penalty_cents_per_min: int = Field(default=1, ge=0)
    earliness_holding_cents_per_min: int = Field(default=0, ge=0)
    safety_buffer_mins: int = Field(default=0, ge=0)
    safety_buffer_penalty_cents_per_min: int = Field(default=0, ge=0)
    unscheduled_penalty_cents: int = Field(default=0, ge=0)
    sync_group_id: Optional[str] = None
    attributes: dict[str, Any] = Field(default_factory=dict)


# --------------------------------------------------------------------------------------------
# Primitive 3: TransitionMatrix
# --------------------------------------------------------------------------------------------
class TransitionEntry(BaseModel):
    """Directed transition cost & setup between two activities on a primary unary resource."""

    from_activity_id: str
    to_activity_id: str
    setup_mins: int = Field(default=0, ge=0)
    consumable_waste_units_10: int = Field(default=0, ge=0, description="Transition waste in 0.1 base units")
    consumable_pool_id: Optional[str] = None
    transition_Waste_cost_cents: int = Field(default=0, ge=0)
    reason: str = "standard"


class TransitionMatrix(BaseModel):
    """Primitive 3: Asymmetric sequence-dependent setup matrix and setup blackout rules."""

    entries: list[TransitionEntry] = Field(default_factory=list)
    max_possible_setup_mins: int = Field(default=480, ge=0)
    setup_downtime_cost_cents_per_min: int = Field(default=417, ge=0)
    setup_blackout_windows: list[TimeWindow] = Field(default_factory=list)


# --------------------------------------------------------------------------------------------
# Primitive 4: CumulativeEnvelope (CUMULATIVE_CAP)
# --------------------------------------------------------------------------------------------
class CumulativeEnvelope(BaseModel):
    """Primitive 4: Cumulative capacity envelope (`CUMULATIVE_CAP`).

    Covers:
      - `consumable_cap`: Global primary/secondary consumable inventory caps across the horizon.
      - `time_window_tariff`: Time-windowed peak energy/utility surcharge overlap envelope.
      - `shift_capacity_cap`: Shift-windowed concurrent active-resource cap derived from workforce availability,
        supporting bounded soft-overflow penalty (`soft_overflow_cost_cents_per_unit`).
    """

    envelope_id: str = Field(min_length=1)
    kind: EnvelopeKind
    resource_id: Optional[str] = None
    window: Optional[TimeWindow] = None
    primary_cap_units_10: int = Field(default=0, ge=0)
    secondary_cap_units_10: int = Field(default=0, ge=0)
    max_concurrent_activities: int = Field(default=0, ge=0)
    surcharge_cents_per_min: int = Field(default=0, ge=0)
    activity_surcharge_cents_per_min: dict[str, int] = Field(default_factory=dict)
    soft_overflow_allowed: bool = True
    soft_overflow_cost_cents_per_unit: int = Field(default=0, ge=0)
    attributes: dict[str, Any] = Field(default_factory=dict)


# --------------------------------------------------------------------------------------------
# Primitive 5: SynchronizationGroup
# --------------------------------------------------------------------------------------------
class SynchronizationGroup(BaseModel):
    """Primitive 5: Multi-activity synchronization barrier or co-scheduled maintenance block."""

    group_id: str = Field(min_length=1)
    kind: SyncKind
    activity_ids: list[str] = Field(default_factory=list)
    resource_id: Optional[str] = None
    maintenance_duration_mins: int = Field(default=0, ge=0)
    maintenance_deadline_min: int = Field(default=0, ge=0)
    max_cycles_before_maintenance: Optional[int] = None
    force_start_at_zero: bool = False
    wait_holding_cents_per_min_by_activity: dict[str, int] = Field(default_factory=dict)
    trigger_reason: str = "scheduled"
    attributes: dict[str, Any] = Field(default_factory=dict)


# --------------------------------------------------------------------------------------------
# Primitive 6: ObjectiveTermSpec
# --------------------------------------------------------------------------------------------
class ObjectiveTermSpec(BaseModel):
    """Primitive 6: Multi-objective weight multipliers and resource assignment cost table."""

    transition_weight_multiplier: int = Field(default=106, ge=1)
    timeliness_weight_multiplier: int = Field(default=106, ge=1)
    operating_energy_weight_multiplier: int = Field(default=31, ge=1)
    working_capital_weight_multiplier: int = Field(default=31, ge=1)
    labor_envelope_weight_multiplier: int = Field(default=1, ge=1)
    assignment_operating_cost_cents: dict[str, int] = Field(
        default_factory=dict,
        description="Keyed by 'activity_id::resource_id' -> operating + base energy cost in cents",
    )
    primary_consumable_cost_cents_per_unit_10: dict[str, int] = Field(default_factory=dict)
    secondary_consumable_cost_cents_per_unit_10: dict[str, int] = Field(default_factory=dict)


# --------------------------------------------------------------------------------------------
# Warm-Start Hints & Top-Level UEMGraph Container
# --------------------------------------------------------------------------------------------
class UEMActivityHint(BaseModel):
    """Feasible warm-start hint for a single activity (e.g., from a deterministic FIFO baseline)."""

    activity_id: str
    scheduled: bool = True
    primary_resource_id: Optional[str] = None
    start_min: int = 0
    primary_consumable_units_10: int = 0
    secondary_consumable_units_10: int = 0


class UEMGraph(BaseModel):
    """Complete 6-Primitive Universal Execution Model (UEM) Graph."""

    graph_id: str = "UEM-GRAPH-01"
    domain_name: str = "general"
    horizon_mins: int = Field(gt=0)
    base_horizon_mins: int = Field(gt=0)
    max_solve_seconds: float = Field(default=5.0, gt=0.1, le=120.0)
    num_workers: int = Field(default=8, ge=1, le=64)
    random_seed: int = 42

    # The 6 Canonical Primitives
    resources: list[ResourceNode] = Field(default_factory=list)
    activities: list[ActivityNode] = Field(default_factory=list)
    transitions: TransitionMatrix = Field(default_factory=TransitionMatrix)
    cumulative_envelopes: list[CumulativeEnvelope] = Field(default_factory=list)
    sync_groups: list[SynchronizationGroup] = Field(default_factory=list)
    objective: ObjectiveTermSpec = Field(default_factory=ObjectiveTermSpec)

    # Optional warm-start hints
    hints: list[UEMActivityHint] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def primitive_counts(self) -> dict[str, int]:
        return {
            "ResourceNode": len(self.resources),
            "ActivityNode": len(self.activities),
            "TransitionMatrix_entries": len(self.transitions.entries),
            "CumulativeEnvelope": len(self.cumulative_envelopes),
            "SynchronizationGroup": len(self.sync_groups),
            "ObjectiveTermSpec_terms": (
                len(self.objective.assignment_operating_cost_cents)
                + len(self.objective.primary_consumable_cost_cents_per_unit_10)
            ),
        }


# --------------------------------------------------------------------------------------------
# UEM Solved Output & Independent Verification Contracts
# --------------------------------------------------------------------------------------------
class UEMScheduledActivity(BaseModel):
    activity_id: str
    scheduled: bool
    primary_resource_id: Optional[str] = None
    secondary_resource_id: Optional[str] = None
    setup_start_min: int = 0
    start_min: int = 0
    end_min: int = 0
    setup_mins: int = 0
    primary_consumable_units_10: int = 0
    secondary_consumable_units_10: int = 0
    transition_waste_units_10: int = 0
    unscheduled_reason: Optional[str] = None


class UEMScheduledMaintenance(BaseModel):
    group_id: str
    resource_id: str
    start_min: int
    end_min: int
    duration_mins: int
    mode: Literal["static", "autonomous"] = "static"
    trigger_reason: str = "scheduled"
    deadline_min: Optional[int] = None


class UEMSolution(BaseModel):
    status: Literal["OPTIMAL", "FEASIBLE", "INFEASIBLE", "MODEL_INVALID", "UNKNOWN"]
    solve_time_ms: int
    objective_value: float
    best_bound: float
    gap_pct: float
    activities: list[UEMScheduledActivity] = Field(default_factory=list)
    maintenance_windows: list[UEMScheduledMaintenance] = Field(default_factory=list)
    envelope_overflows: dict[str, int] = Field(default_factory=dict)
    solver_params: dict[str, Any] = Field(default_factory=dict)


class UEMVerificationCheck(BaseModel):
    primitive_id: str
    name: str
    passed: bool
    violations: int = 0
    details: list[str] = Field(default_factory=list)
