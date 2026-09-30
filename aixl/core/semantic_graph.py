"""FASE 2 — SemanticGraph: nodes (SemanticObject) + edges (SemanticRelation), and the CANONICAL form.

The graph is the canonical representation. `to_frame()`/`from_frame()` are the bridge to the 0.2 SemanticFrame
that the AIXL codec serializes. Contract of the frame encoding of the 0.3 extensions (see ARCHITECTURE.md):
  quantity        K:QTY=100:RECORDS           modality FORBID  N:NO_X + K:FORBID_X       modality ALLOW  K:ALLOW_X
  aggregate       D:TOTAL_SALES / AVERAGE_ / COUNT_    visibility K:VISIBILITY=PUBLIC     before/after K:BEFORE=... K:AFTER=...
  count condition F:COUNT>100:RECORDS       flags (ambiguity) are kept in `meta["flags"]`, not in meaning.
"""
import re
from aixl.core.semantic_object import SemanticObject
from aixl.core.semantic_relation import SemanticRelation
from aixl.core.ontology import type_of, ENTITIES, DATA
from aixl.legacy02.core.semantic_frame import SemanticFrame
from aixl.legacy02.protocol.atoms import derive_intent, derive_goal

AGG = ("TOTAL", "AVERAGE", "COUNT")
FLAGS = {"AMBIGUOUS_YEAR", "AMBIGUOUS_MODALITY"}


def _num(s: str) -> str:
    """.90 == .9 == 0.9 ; 100 stays 100."""
    s = s.strip()
    m = re.fullmatch(r"(>=|<=|>|<|=)?(\d*\.?\d+)", s)
    if not m:
        return s
    v = m.group(2)
    v = ("0" + v) if v.startswith(".") else v
    v = v.rstrip("0").rstrip(".") if "." in v else v
    return (m.group(1) or "") + v


_DUR_UNIT = {"YEAR": 12, "YEARS": 12, "MONTH": 1, "MONTHS": 1}


def _unit_canon(v: str) -> str:
    """Duration-unit normalization (E-DATE round 2, 2026-09-27, set7 S7-036/S7-077): '1 year' and
    '12 months' are the same duration whether written as the AGE constraint or reused as a COUNT
    condition (an LLM encoder did this on its own, matching the card's existing COUNT>N:UNIT pattern);
    convert any trailing :YEAR(S)/:MONTH(S) suffix to a MONTHS count so both compare equal. DAY is left
    alone (imprecise without a specific reference month)."""
    m = re.match(r"^(.*?)(>=|<=|!=|>|<|=)(\d+(?:\.\d+)?):(YEARS?|MONTHS?)$", v)
    if not m:
        return v
    prefix, op, n, unit = m.groups()
    months = float(n) * _DUR_UNIT[unit.upper()]
    months = int(months) if months == int(months) else months
    return f"{prefix}{op}{months}:MONTHS"


def _cond_canon(c: str) -> str:
    m = re.match(r"^(H|CONF\w*)\s*(>=|<=|!=|>|<|=)\s*(.+)$", c)
    if m:
        return f"H{m.group(2)}{_num(m.group(3))}"
    return _unit_canon(c)


class SemanticGraph:
    def __init__(self, nodes=None, edges=None, meta=None):
        self.nodes: list[SemanticObject] = nodes or []
        self.edges: list[SemanticRelation] = edges or []
        self.meta: dict = meta or {}

    # ---- construction -------------------------------------------------------------------------------
    def add_node(self, type_: str, value: str, attributes=None, confidence=1.0, source="natural_language") -> SemanticObject:
        n = SemanticObject(f"{type_.lower()}_{sum(1 for x in self.nodes if x.type == type_) + 1}", type_, value,
                           attributes or {}, confidence, source)
        self.nodes.append(n)
        return n

    def add_edge(self, source: str, relation: str, target: str, **attrs) -> SemanticRelation:
        e = SemanticRelation(source, relation, target, attrs)
        self.edges.append(e)
        return e

    def by_type(self, type_: str):
        return [n for n in self.nodes if n.type == type_]

    # ---- frame bridge -------------------------------------------------------------------------------
    @classmethod
    def from_frame(cls, frame: SemanticFrame, confidences: dict | None = None, source="natural_language") -> "SemanticGraph":
        g = cls(meta={"raw": frame.raw, "lang": frame.lang, "flags": []})
        conf = confidences or {}
        c = lambda key: conf.get(key, 1.0)
        neg = {n[3:] for n in frame.negations if n.startswith("NO_")}
        forbid = {k[7:] for k in frame.constraints if k.startswith("FORBID_")}
        allow = {k[6:] for k in frame.constraints if k.startswith("ALLOW_")}
        forbidden = neg | forbid
        actions = []
        for i, a in enumerate(frame.actions):
            mod = "FORBID" if a in forbidden else ("ALLOW" if a in allow else "REQUEST")
            actions.append(g.add_node("ACTION", a, {"modality": mod, "order": i}, c(a), source))
        root = next((n for n in actions if n.attributes["modality"] == "REQUEST"), actions[0] if actions else None)
        if frame.intent:
            g.add_node("INTENT", frame.intent, {}, 1.0, source)
        for a1, a2 in zip(actions, actions[1:]):
            g.add_edge(a1.id, "BEFORE", a2.id)

        def hang(node, rel):
            if root is not None:
                g.add_edge(root.id, rel, node.id)

        # ontology decides the node type (spec §9): REPORT/DOCUMENT/MODEL... are ENTITIES even if the 0.2 frame listed them under D
        for d in frame.data:
            agg = next((p for p in AGG if d.startswith(p + "_")), None)
            base = d[len(agg) + 1:] if agg else d
            typ = "ENTITY" if base in ENTITIES else "DATA"
            hang(g.add_node(typ, base, {"aggregate": agg} if agg else {}, c(d), source), "TARGET")
        for e in frame.entities:
            typ = "DATA" if e in DATA else "ENTITY"
            hang(g.add_node(typ, e, {}, c(e), source), "TARGET")
        for t in (frame.time.split(",") if frame.time else []):
            hang(g.add_node("TIME", t, {}, c(t), source), "TIME")
        if frame.location:
            hang(g.add_node("LOCATION", ",".join(frame.location), {}, 1.0, source), "LOCATION")
        for r in frame.references:
            hang(g.add_node("REFERENCE", r, {}, 1.0, source), "REFERENCE")
        for k in frame.constraints:
            if k.startswith(("FORBID_", "ALLOW_")):
                continue
            if k.startswith("QTY="):
                v, _, unit = k[4:].partition(":")
                hang(g.add_node("QUANTITY", v, {"unit": unit}, c(k), source), "QUANTITY")
            else:
                hang(g.add_node("CONSTRAINT", k, {}, c(k), source), "CONSTRAINT")
        for cnd in frame.conditions:
            if cnd in FLAGS:
                g.meta["flags"].append(cnd)
            else:
                hang(g.add_node("CONDITION", cnd, {}, c(cnd), source), "CONDITION")
        if frame.confidence:
            hang(g.add_node("MODIFIER", "CONFIDENCE" + frame.confidence, {}, 1.0, source), "MODIFIER")
        if frame.priority:
            hang(g.add_node("MODIFIER", "PRIORITY=" + frame.priority, {}, 1.0, source), "MODIFIER")
        if frame.goal:
            hang(g.add_node("GOAL", frame.goal, {}, 1.0, source), "RESULT")
        for o in frame.output:
            hang(g.add_node("OUTPUT", o, {}, 1.0, source), "OUTPUT")
        return g

    def to_frame(self) -> SemanticFrame:
        f = SemanticFrame(version="AIXL-0.3", raw=self.meta.get("raw", ""), lang=self.meta.get("lang", ""), source="graph")
        for n in sorted(self.by_type("ACTION"), key=lambda x: x.attributes.get("order", 0)):
            f.actions.append(n.value)
            if n.attributes.get("modality") == "FORBID":
                f.negations.append("NO_" + n.value); f.constraints.append("FORBID_" + n.value)
            elif n.attributes.get("modality") == "ALLOW":
                f.constraints.append("ALLOW_" + n.value)
        for n in self.by_type("DATA"):
            f.data.append((n.attributes["aggregate"] + "_" if n.attributes.get("aggregate") else "") + n.value)
        f.entities = [n.value for n in self.by_type("ENTITY")]
        f.time = ",".join(n.value for n in self.by_type("TIME"))
        f.location = next((n.value.split(",") for n in self.by_type("LOCATION")), [])
        f.references = [n.value for n in self.by_type("REFERENCE")]
        for n in self.by_type("QUANTITY"):
            f.constraints.append("QTY=" + n.value + (":" + n.attributes["unit"] if n.attributes.get("unit") else ""))
        f.constraints += [n.value for n in self.by_type("CONSTRAINT")]
        f.conditions = [n.value for n in self.by_type("CONDITION")] + list(self.meta.get("flags", []))
        for n in self.by_type("MODIFIER"):
            if n.value.startswith("CONFIDENCE"): f.confidence = n.value[len("CONFIDENCE"):]
            elif n.value.startswith("PRIORITY="): f.priority = n.value[len("PRIORITY="):]
        f.goal = next((n.value for n in self.by_type("GOAL")), "")
        f.output = [n.value for n in self.by_type("OUTPUT")]
        f.intent = next((n.value for n in self.by_type("INTENT")), "") or derive_intent(f.actions, [x[3:] for x in f.negations])
        return f

    # ---- canonical form -----------------------------------------------------------------------------
    def canonical(self, config: dict | None = None, today=None) -> dict:
        """Canonical form: comparison is done on THIS, not on the surface words or on the frame.
        Normalizations (all configurable/documented): action groups (data/config.json), EXCLUDE == FORBID INCLUDE,
        generic DATA dropped when a specific datum is present, intent/goal derived from the canonical actions.
        `today` (E-DATE, 2026-09-27): reference date used to resolve TODAY/YESTERDAY/... TIME nodes to a
        literal value AT COMPARISON TIME — applied here, not only in the rule-based translator, so it also
        covers TIME nodes decoded from an LLM-encoded AIXL line (found missing by set 7 / E-DATE round 2:
        the translator-only fix left the LLM route unable to match 'T:TODAY' against a literal date).
        Defaults to the real system date; pass an explicit date for deterministic tests/reproductions."""
        from aixl.core.ontology import load_config, resolve_relative_time_token
        import datetime as _dt
        cfg = config or load_config()
        today = today or _dt.date.today()
        rep = {}
        for grp in cfg.get("action_groups", []):
            for a in grp:
                rep[a] = grp[0]
        acts = sorted(self.by_type("ACTION"), key=lambda x: x.attributes.get("order", 0))
        canon_actions, neg = [], []
        for n in acts:
            act, mod = rep.get(n.value, n.value), n.attributes.get("modality", "REQUEST")
            if act == "EXCLUDE":                                   # "excluye X" == "no incluyas X"
                act, mod = "INCLUDE", {"REQUEST": "FORBID", "FORBID": "REQUEST"}.get(mod, mod)
            canon_actions.append(act)
            if mod in ("FORBID", "ALLOW"):
                neg.append(f"{mod}:{act}")
        data = [(f"{n.attributes['aggregate']}({n.value})" if n.attributes.get("aggregate") else n.value) for n in self.by_type("DATA")]
        if "DATA" in data and len(data) > 1:
            data.remove("DATA")
        entities = tuple(sorted(n.value for n in self.by_type("ENTITY")))
        negated = [x.split(":")[1] for x in neg if x.startswith("FORBID")]
        from aixl.legacy02.protocol.atoms import derive_intent, derive_goal
        cons = []
        for n in self.by_type("CONSTRAINT"):
            v = n.value
            if v.startswith(("LIMIT=", "APPROX=")):
                v = v.split("=")[0] + "=" + _num(v.split("=", 1)[1])
            elif v.startswith("AGE"):
                v = _unit_canon(v)
            cons.append(v)
        return {
            "intent": derive_intent(canon_actions, negated) if canon_actions else "UNKNOWN",
            "actions": tuple(canon_actions),
            "entities": entities,
            "data": tuple(sorted(data)),
            "time": tuple(sorted(resolve_relative_time_token(n.value, today) for n in self.by_type("TIME"))),
            "location": tuple(x for n in self.by_type("LOCATION") for x in n.value.split(",")),
            "constraints": tuple(sorted(cons)),
            "conditions": tuple(sorted(_cond_canon(n.value) for n in self.by_type("CONDITION"))),
            "negation": tuple(sorted(neg)),
            "references": tuple(sorted(n.value for n in self.by_type("REFERENCE"))),
            "quantities": tuple(sorted(f"{n.value}:{n.attributes.get('unit', '')}" for n in self.by_type("QUANTITY"))),
            "goal": derive_goal(canon_actions, list(entities), negated),
            "output": tuple(sorted(n.value for n in self.by_type("OUTPUT"))),
            "modifiers": tuple(sorted(("CONFIDENCE" + _num(n.value[10:])) if n.value.startswith("CONFIDENCE") else n.value for n in self.by_type("MODIFIER"))),
        }

    # ---- JSON ---------------------------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {"nodes": [n.to_dict() for n in self.nodes], "edges": [e.to_dict() for e in self.edges], "meta": self.meta}

    @classmethod
    def from_dict(cls, d: dict) -> "SemanticGraph":
        return cls([SemanticObject.from_dict(n) for n in d["nodes"]], [SemanticRelation.from_dict(e) for e in d["edges"]], dict(d.get("meta", {})))
