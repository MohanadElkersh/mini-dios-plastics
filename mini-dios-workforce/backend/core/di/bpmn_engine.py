"""Layer 3 — OMG BPMN 2.0 Process Templates, Workflow Compiler & XML Serializer (Domain-Agnostic).

Models enterprise operational workflows using OMG BPMN 2.0 constructs:
  - Events: `startEvent`, `endEvent`, `boundaryTimerEvent`
  - Tasks: `serviceTask`, `businessRuleTask` (linked to Layer 4 DMN 1.3 tables), `userTask`
  - Gateways: `exclusiveGateway`, `parallelGateway`, `inclusiveGateway`
  - Sequence Flows: directed transitions with optional condition expressions and UEM primitive mappings
  - Exports standards-compliant OMG BPMN 2.0 XML (`http://www.omg.org/spec/BPMN/20100524/MODEL`).
"""
from __future__ import annotations

from collections import deque
from typing import Any, Literal, Optional
from xml.sax.saxutils import escape as xml_escape
from pydantic import BaseModel, Field

BPMNNodeKind = Literal[
    "startEvent",
    "endEvent",
    "boundaryTimerEvent",
    "serviceTask",
    "businessRuleTask",
    "userTask",
    "exclusiveGateway",
    "parallelGateway",
]

UEMPrimitiveTarget = Literal[
    "ResourceNode",
    "ActivityNode",
    "TransitionMatrix",
    "CumulativeEnvelope",
    "SynchronizationGroup",
    "ObjectiveTermSpec",
    "ValidatorGate",
]


class BPMNFlowNode(BaseModel):
    node_id: str = Field(min_length=1)
    name: str
    kind: BPMNNodeKind
    dmn_table_id: Optional[str] = None
    timer_duration_iso: Optional[str] = None
    attached_to_ref: Optional[str] = None
    compiles_to_primitive: Optional[UEMPrimitiveTarget] = None
    description: str = ""


class BPMNSequenceFlow(BaseModel):
    flow_id: str = Field(min_length=1)
    source_ref: str = Field(min_length=1)
    target_ref: str = Field(min_length=1)
    name: str = ""
    condition_expression: Optional[str] = None


class BPMNTopologyValidation(BaseModel):
    valid: bool
    start_events: int
    end_events: int
    reachable_nodes: int
    total_nodes: int
    dmn_linked_tasks: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)


class BPMNProcessTemplate(BaseModel):
    """Layer 3 OMG BPMN 2.0 Process Template."""

    process_id: str = Field(min_length=1)
    name: str
    is_executable: bool = True
    nodes: list[BPMNFlowNode] = Field(default_factory=list)
    sequence_flows: list[BPMNSequenceFlow] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def validate_topology(self) -> BPMNTopologyValidation:
        """Verify graph connectivity from `startEvent` to `endEvent` and DMN task bindings."""
        node_map = {n.node_id: n for n in self.nodes}
        starts = [n for n in self.nodes if n.kind == "startEvent"]
        ends = [n for n in self.nodes if n.kind == "endEvent"]
        issues: list[str] = []

        if not starts:
            issues.append("BPMN process has no startEvent.")
        if not ends:
            issues.append("BPMN process has no endEvent.")

        adj: dict[str, list[str]] = {n.node_id: [] for n in self.nodes}
        for sf in self.sequence_flows:
            if sf.source_ref not in node_map:
                issues.append(f"SequenceFlow '{sf.flow_id}' references unknown source '{sf.source_ref}'.")
            elif sf.target_ref not in node_map:
                issues.append(f"SequenceFlow '{sf.flow_id}' references unknown target '{sf.target_ref}'.")
            else:
                adj[sf.source_ref].append(sf.target_ref)

        # Boundary timers are attached to a host task
        for n in self.nodes:
            if n.kind == "boundaryTimerEvent" and n.attached_to_ref in adj:
                adj[n.attached_to_ref].append(n.node_id)

        visited: set[str] = set()
        queue = deque(s.node_id for s in starts)
        while queue:
            curr = queue.popleft()
            if curr in visited:
                continue
            visited.add(curr)
            for nxt in adj.get(curr, []):
                if nxt not in visited:
                    queue.append(nxt)

        if len(visited) < len(self.nodes):
            unreachable = sorted(set(node_map.keys()) - visited)
            issues.append(f"Unreachable BPMN nodes from startEvent: {unreachable}")

        dmn_tasks = [
            f"{n.node_id} -> {n.dmn_table_id}"
            for n in self.nodes
            if n.kind == "businessRuleTask" and n.dmn_table_id
        ]

        return BPMNTopologyValidation(
            valid=len(issues) == 0,
            start_events=len(starts),
            end_events=len(ends),
            reachable_nodes=len(visited),
            total_nodes=len(self.nodes),
            dmn_linked_tasks=dmn_tasks,
            issues=issues,
        )

    def to_bpmn_xml(self) -> str:
        """Export the process template as standards-compliant OMG BPMN 2.0 XML."""
        exec_str = "true" if self.is_executable else "false"
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL"',
            '             xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
            f'             id="defs_{xml_escape(self.process_id)}"',
            '             targetNamespace="https://dios.decision-intelligence.io/bpmn/2.0">',
            f'  <process id="{xml_escape(self.process_id)}" name="{xml_escape(self.name)}" isExecutable="{exec_str}">',
        ]

        for n in self.nodes:
            nid = xml_escape(n.node_id)
            nname = xml_escape(n.name)
            if n.kind == "startEvent":
                lines.append(f'    <startEvent id="{nid}" name="{nname}" />')
            elif n.kind == "endEvent":
                lines.append(f'    <endEvent id="{nid}" name="{nname}" />')
            elif n.kind == "boundaryTimerEvent":
                att = xml_escape(n.attached_to_ref or "")
                dur = xml_escape(n.timer_duration_iso or "PT1H")
                lines.append(f'    <boundaryEvent id="{nid}" name="{nname}" attachedToRef="{att}" cancelActivity="false">')
                lines.append("      <timerEventDefinition>")
                lines.append(f"        <timeDuration>{dur}</timeDuration>")
                lines.append("      </timerEventDefinition>")
                lines.append("    </boundaryEvent>")
            elif n.kind == "businessRuleTask":
                dmn_attr = f' implementation="dmn:{xml_escape(n.dmn_table_id)}"' if n.dmn_table_id else ""
                lines.append(f'    <businessRuleTask id="{nid}" name="{nname}"{dmn_attr} />')
            elif n.kind == "serviceTask":
                lines.append(f'    <serviceTask id="{nid}" name="{nname}" />')
            elif n.kind == "userTask":
                lines.append(f'    <userTask id="{nid}" name="{nname}" />')
            elif n.kind == "exclusiveGateway":
                lines.append(f'    <exclusiveGateway id="{nid}" name="{nname}" />')
            elif n.kind == "parallelGateway":
                lines.append(f'    <parallelGateway id="{nid}" name="{nname}" />')

        for sf in self.sequence_flows:
            fid = xml_escape(sf.flow_id)
            src = xml_escape(sf.source_ref)
            tgt = xml_escape(sf.target_ref)
            name_attr = f' name="{xml_escape(sf.name)}"' if sf.name else ""
            if sf.condition_expression:
                lines.append(f'    <sequenceFlow id="{fid}" sourceRef="{src}" targetRef="{tgt}"{name_attr}>')
                lines.append(
                    f'      <conditionExpression xsi:type="tFormalExpression">{xml_escape(sf.condition_expression)}</conditionExpression>'
                )
                lines.append("    </sequenceFlow>")
            else:
                lines.append(f'    <sequenceFlow id="{fid}" sourceRef="{src}" targetRef="{tgt}"{name_attr} />')

        lines.append("  </process>")
        lines.append("</definitions>")
        return "\n".join(lines)
