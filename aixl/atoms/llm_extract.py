"""LLM extraction wrapper with abstention (AIXL 0.4, ADR-019/020).

The core calls NO model: the caller supplies `call(prompt: str) -> str` functions. This module only
  * builds a self-contained prompt (schema + guide + registry + the texts),
  * parses and validates responses (format, endpoint types, TIME grammar, unknown keys), canonicalizes x: lemmas,
  * runs k independent calls and ABSTAINS unless they agree: the same stance as the 2-of-2 arbiter (ADR-018).
Policies: "exact" = identical graphs (fingerprint without the loss marker), "core" = the safety-critical dimensions agree
(modality/negation, quantity, time, scope, constraints) even if auxiliary links differ. Anything else -> ABSTAIN with the candidates
attached for a human or a third call; a wrong graph is never returned as accepted unless every call agreed on it."""
import json
import os
import re
from dataclasses import dataclass, field
from typing import Callable

from aixl.atoms import registry as R
from aixl.atoms import fidelity
from aixl.atoms.schema import AtomGraph

_DOC = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "docs", "ATOM_MODEL.md")
CORE_KEYS = ("polarity", "quantitative", "temporal", "scope", "constraint")


def prompt_id(learned: bool = True) -> str:
    import hashlib
    return hashlib.sha256((open(_DOC, encoding="utf-8").read() + registry_digest(learned)).encode()).hexdigest()[:12]


def registry_digest(learned: bool = True) -> str:
    """compact registry listing for the prompt (ids + English forms), so the model uses real concept ids."""
    by = {}
    for c in R.CONCEPTS:
        if c.get("learned") and not learned: continue
        by.setdefault(c["type"], []).append(f"{c['id']}({'/'.join(c['lex'].get('en', [])[:2])})" if c["lex"].get("en") else c["id"])
    out = [f"registry {R.REGISTRY_VERSION}"]
    for k, v in by.items(): out.append(f"{k}: " + ", ".join(v))
    out.append("RELATIONS (source -> target): " + "; ".join(f"{k}: {'/'.join(sorted(s))}->{'/'.join(sorted(d))}" for k, (s, d) in R.RELATION_SIG.items()))
    out.append("UNITS: " + ", ".join(sorted(R.UNITS)))
    return "\n".join(out)


def build_prompt(items: list, learned: bool = True) -> str:
    """items: [{"id":..., "text":...}, ...] -> one self-contained prompt. The answer must be JSON Lines, one object per id."""
    guide = open(_DOC, encoding="utf-8").read()
    body = "\n".join(json.dumps(dict(id=i["id"], text=i["text"]), ensure_ascii=False) for i in items)
    return (
        "You convert work instructions (Spanish, English or Portuguese) into AIXL 0.4 semantic atom graphs.\n"
        "Follow the annotation guide below (LATER sections win over earlier ones). Use only registry concept ids, or `x:<english_lemma>` "
        "when the registry has none. Represent only what the text says; put fragments the guide says are inexpressible in `unrepresented`.\n"
        "OUTPUT: JSON Lines only, no commentary, no code fences, exactly one line per input id:\n"
        '{"id": "...", "atoms": [...], "relations": [["src","REL","dst"], ...], "unrepresented": [...]}\n'
        "Atom objects: id, type, concept, value, modality, polarity, scope, status as in the guide. Every relation must respect the endpoint types.\n\n"
        "=== REGISTRY ===\n" + registry_digest(learned) + "\n\n=== ANNOTATION GUIDE ===\n" + guide + "\n\n=== INSTRUCTIONS TO CONVERT ===\n" + body + "\n"
    )


_FENCE = re.compile(r"^```\w*\s*$")


def _canon_lemmas(g: AtomGraph) -> None:
    for a in g.atoms:
        if a.concept and a.concept.startswith("x:"):
            a.concept = "x:" + re.sub(r"[^a-z0-9_]+", "_", a.concept[2:].strip().lower()).strip("_")


@dataclass
class Parsed:
    graphs: dict = field(default_factory=dict)       # id -> AtomGraph (valid only)
    errors: dict = field(default_factory=dict)       # id -> [reasons] (invalid / missing)


def parse_response(text: str, expected_ids: list, texts: dict | None = None) -> Parsed:
    """tolerant JSONL parser + validator. Missing ids and invalid graphs are reported, never repaired by guessing."""
    out = Parsed()
    for line in text.splitlines():
        line = line.strip()
        if not line or _FENCE.match(line): continue
        try:
            d = json.loads(line)
            gid = d["id"]
        except (ValueError, KeyError, TypeError):
            continue
        if gid not in expected_ids or gid in out.graphs: continue
        try:
            g = AtomGraph.from_dict(dict(atoms=d["atoms"], relations=d["relations"], unrepresented=d.get("unrepresented", []), text=(texts or {}).get(gid, "")))
        except (KeyError, TypeError, ValueError) as e:
            out.errors[gid] = [f"MALFORMED:{e}"]; continue
        _canon_lemmas(g)
        errs = g.validate()
        if errs: out.errors[gid] = errs
        else: out.graphs[gid] = g
    for gid in expected_ids:
        if gid not in out.graphs and gid not in out.errors: out.errors[gid] = ["MISSING"]
    return out


def core_equal(a: AtomGraph, b: AtomGraph) -> bool:
    da, db = fidelity._dim_items(a), fidelity._dim_items(b)
    return all(da[k] == db[k] for k in CORE_KEYS)


@dataclass
class Result:
    status: str                      # ACCEPT | ABSTAIN
    graph: AtomGraph | None = None
    reasons: list = field(default_factory=list)
    candidates: list = field(default_factory=list)
    agreement: str = ""              # 'exact' | 'core' | ''


_NORM = None


def normalize_graph(g: AtomGraph) -> AtomGraph:
    """graph normal form (ADR-021): collapses representational alternatives before the calls are compared."""
    global _NORM
    if _NORM is None:
        from aixl.atoms.normalize import Normalizer
        _NORM = Normalizer()
    return _NORM(g)


def decide(graphs: list, policy: str = "exact", errors: list | None = None, normalize: bool = False) -> Result:
    """combine the (already parsed) graphs of k independent calls. k < 2 can never be accepted."""
    errors = errors or []
    if normalize: graphs = [normalize_graph(g) if g is not None else None for g in graphs]
    if len(graphs) + len(errors) < 2: return Result("ABSTAIN", None, ["TOO_FEW_CALLS"], list(graphs))
    if errors or any(g is None for g in graphs): return Result("ABSTAIN", None, ["INVALID_CALL"] + [str(e) for e in errors], [g for g in graphs if g is not None])
    first = graphs[0]
    fps = {g.fingerprint(include_unrepresented=False) for g in graphs}
    if len(fps) == 1:
        return Result("ACCEPT", first, agreement="exact")
    if policy == "core" and all(core_equal(first, g) for g in graphs[1:]):
        return Result("ACCEPT", first, ["AUXILIARY_LINKS_DIFFER"], list(graphs), agreement="core")
    return Result("ABSTAIN", None, ["CALLS_DISAGREE"], list(graphs))


def extract_llm(text: str, calls: list, policy: str = "exact", gid: str = "t", normalize: bool = False) -> Result:
    """k independent callables -> one Result. Each callable gets the prompt and returns the model's raw text."""
    prompt = build_prompt([dict(id=gid, text=text)])
    graphs, errs = [], []
    for c in calls:
        p = parse_response(c(prompt), [gid], {gid: text})
        if gid in p.graphs: graphs.append(p.graphs[gid])
        else: errs.append(p.errors.get(gid, ["MISSING"]))
    return decide(graphs, policy, errs, normalize)
