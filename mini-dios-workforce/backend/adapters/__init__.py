"""Domain Adapters for the 5-Layer Decision Intelligence + 6-Primitive UEMGraph Engine."""
from .plastics import (
    build_plastics_blueprint,
    build_plastics_bpmn_template,
    build_plastics_causal_decision_model,
    build_plastics_dmn_registry,
    build_plastics_ontology_graph,
    compile_plastics_to_uem_graph,
    solve_plastics_via_uem,
)

__all__ = [
    "build_plastics_blueprint",
    "build_plastics_bpmn_template",
    "build_plastics_causal_decision_model",
    "build_plastics_dmn_registry",
    "build_plastics_ontology_graph",
    "compile_plastics_to_uem_graph",
    "solve_plastics_via_uem",
]
