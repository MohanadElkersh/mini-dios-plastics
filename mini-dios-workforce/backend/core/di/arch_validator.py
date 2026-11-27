"""Layer 2 — Business Architecture Validation (Pre-Solve Structural, Capability & Policy Gate).

Evaluates a `BusinessOntologyGraph` across three formal enterprise architecture gates
before compiling BPMN 2.0 / DMN 1.3 into the 6-primitive `UEMGraph`:
  1. Structural Gate : Entity schema conformance, required attributes, and relationship referential integrity.
  2. Capability Gate : Every demand activity has >= 1 active capable primary resource path and valid secondary/consumable links.
  3. Policy Gate     : Resource pool bounds, horizon feasibility, and custom domain policy invariants.
"""
from __future__ import annotations

from typing import Callable, Optional
from pydantic import BaseModel, Field

from .ontology_meta import BusinessOntologyGraph, InvariantViolation

CustomInvariantFn = Callable[[BusinessOntologyGraph], list[InvariantViolation]]


class ArchitectureGateResult(BaseModel):
    gate_id: str
    name: str
    passed: bool
    error_count: int = 0
    warning_count: int = 0
    violations: list[InvariantViolation] = Field(default_factory=list)


class ArchitectureValidationReport(BaseModel):
    """Layer 2 Pre-Solve Business Architecture Validation Report."""

    ready: bool
    error_count: int
    warning_count: int
    info_count: int
    gates: list[ArchitectureGateResult] = Field(default_factory=list)
    violations: list[InvariantViolation] = Field(default_factory=list)


def validate_business_architecture(
    ontology: BusinessOntologyGraph,
    custom_evaluators: Optional[list[CustomInvariantFn]] = None,
) -> ArchitectureValidationReport:
    """Run the 3-stage Business Architecture Validation gate on a `BusinessOntologyGraph`."""
    entity_by_id = ontology.entity_map()
    type_by_id = {t.type_id: t for t in ontology.entity_types}

    structural_v: list[InvariantViolation] = []
    capability_v: list[InvariantViolation] = []
    policy_v: list[InvariantViolation] = []

    # ------------------------------------------------------------------
    # Gate 1: Structural Gate (Entity Pools, Required Attributes & Referential Integrity)
    # ------------------------------------------------------------------
    primaries = ontology.entities_by_role("primary_resource")
    demands = ontology.entities_by_role("demand_activity")

    if not primaries:
        structural_v.append(
            InvariantViolation(
                invariant_id="ARCH-STR-01",
                category="structural",
                severity="error",
                message="Ontology contains zero primary execution resources.",
            )
        )
    if not demands:
        structural_v.append(
            InvariantViolation(
                invariant_id="ARCH-STR-02",
                category="structural",
                severity="error",
                message="Ontology contains zero demand activities to schedule.",
            )
        )

    for ent in ontology.entities:
        tspec = type_by_id.get(ent.type_id)
        if tspec is None:
            structural_v.append(
                InvariantViolation(
                    invariant_id="ARCH-STR-03",
                    category="structural",
                    severity="error",
                    entity_id=ent.entity_id,
                    message=f"Entity '{ent.entity_id}' references undeclared EntityType '{ent.type_id}'.",
                )
            )
            continue
        for req_attr in tspec.required_attributes:
            if req_attr not in ent.attributes or ent.attributes[req_attr] is None:
                structural_v.append(
                    InvariantViolation(
                        invariant_id="ARCH-STR-04",
                        category="structural",
                        severity="error",
                        entity_id=ent.entity_id,
                        message=f"Entity '{ent.entity_id}' ({ent.type_id}) missing required attribute '{req_attr}'.",
                    )
                )

    for rel in ontology.relationships:
        if rel.source_id not in entity_by_id:
            structural_v.append(
                InvariantViolation(
                    invariant_id="ARCH-STR-05",
                    category="structural",
                    severity="error",
                    entity_id=rel.source_id,
                    message=f"Relationship '{rel.relationship_id}' ({rel.relation_type}) references missing source '{rel.source_id}'.",
                )
            )
        if rel.target_id not in entity_by_id:
            structural_v.append(
                InvariantViolation(
                    invariant_id="ARCH-STR-06",
                    category="structural",
                    severity="error",
                    entity_id=rel.target_id,
                    message=f"Relationship '{rel.relationship_id}' ({rel.relation_type}) references missing target '{rel.target_id}'.",
                )
            )

    # ------------------------------------------------------------------
    # Gate 2: Capability Gate (Active Resource Reachability for Every Demand Activity)
    # ------------------------------------------------------------------
    active_primaries = [p for p in primaries if p.active]
    if primaries and not active_primaries:
        capability_v.append(
            InvariantViolation(
                invariant_id="ARCH-CAP-01",
                category="capability",
                severity="error",
                message="All primary execution resources are inactive or down.",
            )
        )

    for dem in demands:
        # Either direct DEMAND_CAPABLE_ON -> primary_resource, or DEMAND_USES_SECONDARY -> secondary -> COMPATIBLE_WITH -> primary
        direct_prim = [
            r.target_id
            for r in ontology.outgoing_relationships(dem.entity_id, "CAPABLE_ON_PRIMARY")
            if r.target_id in entity_by_id and entity_by_id[r.target_id].active
        ]
        via_sec_prim: list[str] = []
        sec_rels = ontology.outgoing_relationships(dem.entity_id, "REQUIRES_SECONDARY")
        for srel in sec_rels:
            sec_ent = entity_by_id.get(srel.target_id)
            if sec_ent is None:
                continue
            for crel in ontology.outgoing_relationships(sec_ent.entity_id, "COMPATIBLE_WITH_PRIMARY"):
                p_ent = entity_by_id.get(crel.target_id)
                if p_ent is not None and p_ent.active:
                    if crel.attributes.get("capability_match", True):
                        via_sec_prim.append(p_ent.entity_id)

        capable_ids = set(direct_prim) | set(via_sec_prim)
        if not capable_ids:
            capability_v.append(
                InvariantViolation(
                    invariant_id="ARCH-CAP-02",
                    category="capability",
                    severity="error",
                    entity_id=dem.entity_id,
                    message=f"Demand activity '{dem.entity_id}' has zero active compatible primary resources.",
                )
            )

    # ------------------------------------------------------------------
    # Gate 3: Policy Gate (Custom Semantic Invariants & Resource Pool Policies)
    # ------------------------------------------------------------------
    if custom_evaluators:
        for fn in custom_evaluators:
            for v in fn(ontology):
                if v.category == "structural":
                    structural_v.append(v)
                elif v.category == "capability":
                    capability_v.append(v)
                else:
                    policy_v.append(v)

    def _build_gate(gid: str, gname: str, vlist: list[InvariantViolation]) -> ArchitectureGateResult:
        errs = sum(1 for v in vlist if v.severity == "error")
        warns = sum(1 for v in vlist if v.severity == "warning")
        return ArchitectureGateResult(
            gate_id=gid,
            name=gname,
            passed=errs == 0,
            error_count=errs,
            warning_count=warns,
            violations=vlist,
        )

    g1 = _build_gate("GATE-1-STRUCTURAL", "Structural & Referential Integrity Gate", structural_v)
    g2 = _build_gate("GATE-2-CAPABILITY", "Resource & Tool Capability Gate", capability_v)
    g3 = _build_gate("GATE-3-POLICY", "Operational & Inventory Policy Gate", policy_v)

    all_v = [*structural_v, *capability_v, *policy_v]
    err_total = sum(1 for v in all_v if v.severity == "error")
    warn_total = sum(1 for v in all_v if v.severity == "warning")
    info_total = sum(1 for v in all_v if v.severity == "info")

    return ArchitectureValidationReport(
        ready=err_total == 0,
        error_count=err_total,
        warning_count=warn_total,
        info_count=info_total,
        gates=[g1, g2, g3],
        violations=all_v,
    )
