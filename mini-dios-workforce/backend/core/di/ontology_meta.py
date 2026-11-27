"""Layer 1 — Formal Business Ontology Meta-Model (Domain-Agnostic).

Defines formal EntityTypes, EntityInstances, TypedRelationships, and SemanticInvariants
that represent an enterprise domain before Business Architecture Validation (Layer 2)
and BPMN 2.0 / DMN 1.3 compilation into a 6-primitive `UEMGraph`.
"""
from __future__ import annotations

from typing import Any, Callable, Literal, Optional
from pydantic import BaseModel, Field

OntologyRole = Literal[
    "primary_resource",
    "secondary_resource",
    "consumable_pool",
    "demand_activity",
    "workforce_actor",
    "sync_container",
    "policy_parameter",
]

Cardinality = Literal["1:1", "1:N", "N:1", "M:N"]
InvariantSeverity = Literal["error", "warning", "info"]


class EntityTypeSpec(BaseModel):
    """Formal schema definition for an ontology entity class."""

    type_id: str = Field(min_length=1)
    label: str
    ontology_role: OntologyRole
    required_attributes: list[str] = Field(default_factory=list)
    description: str = ""


class EntityInstance(BaseModel):
    """Concrete domain entity instance participating in the ontology graph."""

    entity_id: str = Field(min_length=1)
    type_id: str = Field(min_length=1)
    label: str
    ontology_role: OntologyRole
    active: bool = True
    attributes: dict[str, Any] = Field(default_factory=dict)


class TypedRelationship(BaseModel):
    """Directed, typed semantic relationship between two entity instances."""

    relationship_id: str = Field(min_length=1)
    relation_type: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    cardinality: Cardinality = "M:N"
    attributes: dict[str, Any] = Field(default_factory=dict)


class SemanticInvariantSpec(BaseModel):
    """Declarative metadata for a formal semantic invariant."""

    invariant_id: str = Field(min_length=1)
    name: str
    category: Literal["structural", "capability", "policy"] = "structural"
    severity: InvariantSeverity = "error"
    expression_summary: str
    description: str = ""


class InvariantViolation(BaseModel):
    """A single violation or diagnostic emitted by a semantic invariant."""

    invariant_id: str
    category: Literal["structural", "capability", "policy"]
    severity: InvariantSeverity
    entity_id: Optional[str] = None
    message: str


class BusinessOntologyGraph(BaseModel):
    """Layer 1 Formal Business Ontology Graph (Domain-Agnostic)."""

    ontology_id: str = "ONT-01"
    domain_name: str = "enterprise"
    version: str = "1.0.0"
    entity_types: list[EntityTypeSpec] = Field(default_factory=list)
    entities: list[EntityInstance] = Field(default_factory=list)
    relationships: list[TypedRelationship] = Field(default_factory=list)
    invariants: list[SemanticInvariantSpec] = Field(default_factory=list)

    def entities_by_role(self, role: OntologyRole) -> list[EntityInstance]:
        return [e for e in self.entities if e.ontology_role == role]

    def entities_by_type(self, type_id: str) -> list[EntityInstance]:
        return [e for e in self.entities if e.type_id == type_id]

    def entity_map(self) -> dict[str, EntityInstance]:
        return {e.entity_id: e for e in self.entities}

    def outgoing_relationships(self, source_id: str, relation_type: Optional[str] = None) -> list[TypedRelationship]:
        return [
            r
            for r in self.relationships
            if r.source_id == source_id and (relation_type is None or r.relation_type == relation_type)
        ]

    def incoming_relationships(self, target_id: str, relation_type: Optional[str] = None) -> list[TypedRelationship]:
        return [
            r
            for r in self.relationships
            if r.target_id == target_id and (relation_type is None or r.relation_type == relation_type)
        ]

    def summary_counts(self) -> dict[str, int]:
        return {
            "entity_types": len(self.entity_types),
            "entities": len(self.entities),
            "relationships": len(self.relationships),
            "invariants": len(self.invariants),
        }
