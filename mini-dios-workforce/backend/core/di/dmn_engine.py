"""Layer 4 — OMG DMN 1.3 Decision Table Rule Engine & XML Serializer (Domain-Agnostic).

Pure-Python deterministic implementation of OMG DMN 1.3 Decision Tables:
  - Hit Policies supported: `UNIQUE` (`U`), `FIRST` (`F`), `PRIORITY` (`P`),
    `ANY` (`A`), `COLLECT` (`C`), `COLLECT_SUM` (`C+`), `COLLECT_MIN` (`C<`), `COLLECT_MAX` (`C>`).
  - Unary Tests (S-FEEL subset): wildcard `-` or `""`, exact literals (`"str"`, numbers, booleans),
    comparisons (`< x`, `<= x`, `> x`, `>= x`, `!= x`, `== x`), intervals (`[a..b]`, `(a..b]`, `[a..b)`),
    and comma-separated disjunction lists (`"A", "B", "C"`).
  - Exports standards-compliant OMG DMN 1.3 XML (`https://www.omg.org/spec/DMN/20191111/MODEL/`).
"""
from __future__ import annotations

from typing import Any, Literal
from xml.sax.saxutils import escape as xml_escape
from pydantic import BaseModel, Field

HitPolicy = Literal[
    "UNIQUE",
    "FIRST",
    "PRIORITY",
    "ANY",
    "COLLECT",
    "COLLECT_SUM",
    "COLLECT_MIN",
    "COLLECT_MAX",
]


class DMNInputColumn(BaseModel):
    input_id: str
    label: str
    expression: str
    type_ref: str = "string"


class DMNOutputColumn(BaseModel):
    output_id: str
    label: str
    name: str
    type_ref: str = "string"


class DMNRule(BaseModel):
    rule_id: str
    description: str = ""
    priority: int = 1
    input_entries: list[str] = Field(default_factory=list)
    output_entries: dict[str, Any] = Field(default_factory=dict)


def _parse_scalar(token: str) -> Any:
    t = token.strip()
    if (t.startswith('"') and t.endswith('"')) or (t.startswith("'") and t.endswith("'")):
        return t[1:-1]
    low = t.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    try:
        if "." in t:
            return float(t)
        return int(t)
    except ValueError:
        return t


def eval_feel_unary_test(expr: str, value: Any) -> bool:
    """Deterministically evaluate an S-FEEL unary test expression against `value`."""
    raw = expr.strip()
    if raw in ("", "-", "*", "ANY"):
        return True

    # Range interval: [a..b], (a..b], [a..b), (a..b)
    if ".." in raw and raw[0] in "[(" and raw[-1] in "])":
        inc_low = raw[0] == "["
        inc_high = raw[-1] == "]"
        inner = raw[1:-1]
        low_s, high_s = inner.split("..", 1)
        low_v = float(_parse_scalar(low_s))
        high_v = float(_parse_scalar(high_s))
        val_f = float(value)
        ok_low = (val_f >= low_v) if inc_low else (val_f > low_v)
        ok_high = (val_f <= high_v) if inc_high else (val_f < high_v)
        return ok_low and ok_high

    # Comparison operators
    for op in ("<=", ">=", "!=", "==", "<", ">"):
        if raw.startswith(op):
            rhs = _parse_scalar(raw[len(op) :])
            if op == "==":
                return value == rhs
            if op == "!=":
                return value != rhs
            val_f = float(value)
            rhs_f = float(rhs)
            if op == "<=":
                return val_f <= rhs_f
            if op == ">=":
                return val_f >= rhs_f
            if op == "<":
                return val_f < rhs_f
            if op == ">":
                return val_f > rhs_f

    # Comma-separated disjunction list (e.g. '"PP", "HDPE", "LDPE"')
    if "," in raw:
        parts = [_parse_scalar(p) for p in raw.split(",")]
        return value in parts

    target = _parse_scalar(raw)
    if isinstance(value, bool) or isinstance(target, bool):
        return bool(value) is bool(target) if isinstance(value, bool) and isinstance(target, bool) else value == target
    if isinstance(value, (int, float)) and isinstance(target, (int, float)):
        return float(value) == float(target)
    return str(value) == str(target)


class DMNDecisionTable(BaseModel):
    """OMG DMN 1.3 Decision Table."""

    table_id: str = Field(min_length=1)
    name: str
    hit_policy: HitPolicy = "FIRST"
    inputs: list[DMNInputColumn] = Field(default_factory=list)
    outputs: list[DMNOutputColumn] = Field(default_factory=list)
    rules: list[DMNRule] = Field(default_factory=list)
    description: str = ""

    def evaluate(self, context: dict[str, Any]) -> Any:
        """Evaluate the decision table against `context` according to `self.hit_policy`."""
        matched_rules: list[DMNRule] = []
        for rule in self.rules:
            all_match = True
            for col_idx, inp_col in enumerate(self.inputs):
                test_expr = rule.input_entries[col_idx] if col_idx < len(rule.input_entries) else "-"
                ctx_val = context.get(inp_col.expression)
                if not eval_feel_unary_test(test_expr, ctx_val):
                    all_match = False
                    break
            if all_match:
                matched_rules.append(rule)
                if self.hit_policy == "FIRST":
                    return dict(rule.output_entries)

        if not matched_rules:
            return {} if self.hit_policy not in ("COLLECT", "COLLECT_SUM", "COLLECT_MIN", "COLLECT_MAX") else []

        if self.hit_policy in ("UNIQUE", "ANY", "FIRST"):
            return dict(matched_rules[0].output_entries)

        if self.hit_policy == "PRIORITY":
            best = sorted(matched_rules, key=lambda r: r.priority)[0]
            return dict(best.output_entries)

        if self.hit_policy == "COLLECT":
            return [dict(r.output_entries) for r in matched_rules]

        if self.hit_policy == "COLLECT_SUM":
            agg: dict[str, float] = {}
            for out_col in self.outputs:
                key = out_col.name
                agg[key] = sum(float(r.output_entries.get(key, 0.0)) for r in matched_rules)
            return agg

        if self.hit_policy == "COLLECT_MIN":
            agg_min: dict[str, float] = {}
            for out_col in self.outputs:
                key = out_col.name
                agg_min[key] = min(float(r.output_entries.get(key, 0.0)) for r in matched_rules)
            return agg_min

        if self.hit_policy == "COLLECT_MAX":
            agg_max: dict[str, float] = {}
            for out_col in self.outputs:
                key = out_col.name
                agg_max[key] = max(float(r.output_entries.get(key, 0.0)) for r in matched_rules)
            return agg_max

        return dict(matched_rules[0].output_entries)


class DMNRegistry(BaseModel):
    """Collection of OMG DMN 1.3 Decision Tables for an enterprise domain."""

    registry_id: str = "DMN-REG-01"
    namespace: str = "https://dios.decision-intelligence.io/dmn/1.3"
    tables: list[DMNDecisionTable] = Field(default_factory=list)

    def get_table(self, table_id: str) -> DMNDecisionTable:
        for t in self.tables:
            if t.table_id == table_id:
                return t
        raise KeyError(f"DMNDecisionTable '{table_id}' not found in registry.")

    def evaluate(self, table_id: str, context: dict[str, Any]) -> Any:
        return self.get_table(table_id).evaluate(context)

    def to_dmn_xml(self) -> str:
        """Export all decision tables as standards-compliant OMG DMN 1.3 XML."""
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<definitions xmlns="https://www.omg.org/spec/DMN/20191111/MODEL/"',
            '             xmlns:dmndi="https://www.omg.org/spec/DMN/20191111/DMNDI/"',
            f'             id="{xml_escape(self.registry_id)}"',
            '             name="DIOS Decision Intelligence DMN 1.3 Registry"',
            f'             namespace="{xml_escape(self.namespace)}">',
        ]
        for tbl in self.tables:
            hp_attr = tbl.hit_policy.replace("_SUM", "").replace("_MIN", "").replace("_MAX", "")
            agg_attr = ""
            if tbl.hit_policy == "COLLECT_SUM":
                agg_attr = ' aggregation="SUM"'
            elif tbl.hit_policy == "COLLECT_MIN":
                agg_attr = ' aggregation="MIN"'
            elif tbl.hit_policy == "COLLECT_MAX":
                agg_attr = ' aggregation="MAX"'
            lines.append(f'  <decision id="dec_{xml_escape(tbl.table_id)}" name="{xml_escape(tbl.name)}">')
            lines.append(
                f'    <decisionTable id="dt_{xml_escape(tbl.table_id)}" hitPolicy="{hp_attr}"{agg_attr}>'
            )
            for inp in tbl.inputs:
                lines.append(f'      <input id="{xml_escape(inp.input_id)}" label="{xml_escape(inp.label)}">')
                lines.append(
                    f'        <inputExpression id="ie_{xml_escape(inp.input_id)}" typeRef="{xml_escape(inp.type_ref)}">'
                )
                lines.append(f"          <text>{xml_escape(inp.expression)}</text>")
                lines.append("        </inputExpression>")
                lines.append("      </input>")
            for out in tbl.outputs:
                lines.append(
                    f'      <output id="{xml_escape(out.output_id)}" label="{xml_escape(out.label)}" '
                    f'name="{xml_escape(out.name)}" typeRef="{xml_escape(out.type_ref)}" />'
                )
            for rule in tbl.rules:
                lines.append(f'      <rule id="{xml_escape(rule.rule_id)}">')
                if rule.description:
                    lines.append(f"        <description>{xml_escape(rule.description)}</description>")
                for idx, entry in enumerate(rule.input_entries):
                    lines.append(f'        <inputEntry id="{xml_escape(rule.rule_id)}_in_{idx}">')
                    lines.append(f"          <text>{xml_escape(entry)}</text>")
                    lines.append("        </inputEntry>")
                for out_idx, out_col in enumerate(tbl.outputs):
                    val = rule.output_entries.get(out_col.name, "")
                    val_str = f'"{val}"' if isinstance(val, str) else str(val).lower() if isinstance(val, bool) else str(val)
                    lines.append(f'        <outputEntry id="{xml_escape(rule.rule_id)}_out_{out_idx}">')
                    lines.append(f"          <text>{xml_escape(val_str)}</text>")
                    lines.append("        </outputEntry>")
                lines.append("      </rule>")
            lines.append("    </decisionTable>")
            lines.append("  </decision>")
        lines.append("</definitions>")
        return "\n".join(lines)
