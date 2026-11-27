"""Layer 5 — Decision Intelligence Meta-Model (Causal Decision Diagram: Levers → Intermediates → Outcomes).

Formalizes Lorien Pratt / OMG Decision Intelligence Causal Decision Diagrams (CDDs):
  - `DecisionLever`      : Controllable executive or operational inputs (weights, policy toggles, capacities).
  - `IntermediateMetric` : First- and second-order operational dynamics driven by levers and physics.
  - `DecisionOutcome`    : Executive P&L, service-level, and risk outcomes optimized by the system.
  - `CausalEdge`         : Directed causal link (`Lever -> Intermediate`, `Intermediate -> Intermediate`,
                           or `Intermediate -> Outcome`) with polarity (`+` / `-`) and mechanism description.
"""
from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field

CausalPolarity = Literal["+", "-", "non_monotonic"]
OutcomeDirection = Literal["maximize", "minimize"]


class DecisionLever(BaseModel):
    lever_id: str = Field(min_length=1)
    name: str
    category: Literal["objective_weight", "operational_toggle", "capacity_envelope", "scenario_stress"]
    current_value: Any
    default_value: Any = None
    min_value: Any = None
    max_value: Any = None
    unit: str = ""
    description: str = ""


class IntermediateMetric(BaseModel):
    metric_id: str = Field(min_length=1)
    name: str
    baseline_value: float
    optimized_value: float
    delta_value: float
    unit: str = ""
    formula_summary: str = ""


class DecisionOutcome(BaseModel):
    outcome_id: str = Field(min_length=1)
    name: str
    category: Literal["financial", "service_level", "operational_risk", "sustainability"]
    direction: OutcomeDirection = "maximize"
    baseline_value: float
    optimized_value: float
    delta_value: float
    improvement_pct: float = 0.0
    unit: str = ""


class CausalEdge(BaseModel):
    edge_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    polarity: CausalPolarity = "+"
    mechanism: str
    governed_by_primitive: str = ""


class CausalPathway(BaseModel):
    lever_id: str
    intermediate_id: str
    outcome_id: str
    net_polarity: str
    explanation: str


class CausalDecisionModel(BaseModel):
    """Layer 5 Decision Intelligence Causal Decision Diagram (CDD)."""

    model_id: str = "DI-CDD-01"
    domain_name: str = "enterprise"
    levers: list[DecisionLever] = Field(default_factory=list)
    intermediates: list[IntermediateMetric] = Field(default_factory=list)
    outcomes: list[DecisionOutcome] = Field(default_factory=list)
    causal_edges: list[CausalEdge] = Field(default_factory=list)

    def trace_causal_pathways(self) -> list[CausalPathway]:
        """Deterministically trace all `Lever -> Intermediate -> Outcome` causal chains."""
        lever_ids = {l.lever_id for l in self.levers}
        inter_ids = {m.metric_id for m in self.intermediates}
        outcome_ids = {o.outcome_id for o in self.outcomes}

        l_to_i = [e for e in self.causal_edges if e.source_id in lever_ids and e.target_id in inter_ids]
        i_to_o = [e for e in self.causal_edges if e.source_id in inter_ids and e.target_id in outcome_ids]

        pathways: list[CausalPathway] = []
        for e1 in l_to_i:
            for e2 in i_to_o:
                if e1.target_id != e2.source_id:
                    continue
                if e1.polarity in ("+", "-") and e2.polarity in ("+", "-"):
                    net_pol = "+" if e1.polarity == e2.polarity else "-"
                else:
                    net_pol = "contextual"
                pathways.append(
                    CausalPathway(
                        lever_id=e1.source_id,
                        intermediate_id=e1.target_id,
                        outcome_id=e2.target_id,
                        net_polarity=net_pol,
                        explanation=f"{e1.source_id} ({e1.polarity}) -> {e1.target_id} ({e2.polarity}) -> {e2.target_id}: {e1.mechanism}; {e2.mechanism}",
                    )
                )
        return pathways
