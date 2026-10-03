"""Semantic fingerprint (master prompt §40): a stable hash of the CANONICAL meaning.

Depends only on `SemanticGraph.canonical()` — not on language, surface word order, style or punctuation.
Conservative by construction: any canonical field that differs (negation, target, quantity, time...) changes
the fingerprint. Relative TIME tokens resolve against `today`, so pass it explicitly for reproducible hashes
across days (default = system date, same as compare)."""
import hashlib
import json


def _jsonable(v):
    if isinstance(v, (tuple, list)):
        return [_jsonable(x) for x in v]
    return v


def fingerprint_graph(graph, config: dict | None = None, today=None, length: int = 16) -> str:
    canon = {k: _jsonable(v) for k, v in graph.canonical(config, today=today).items()}
    blob = json.dumps(canon, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()[:length]
