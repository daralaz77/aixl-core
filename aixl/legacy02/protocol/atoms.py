"""Protocol layer: atoms and controlled vocabularies of AIXL 0.2 (spec §5-§18)."""

# atom letter -> (frame field, is_list)
ATOMS = {
    "V": ("version", False),
    "I": ("intent", False),
    "A": ("actions", True),
    "E": ("entities", True),
    "D": ("data", True),
    "T": ("time", False),
    "L": ("location", True),      # hierarchical: VALLEDUPAR,CESAR,CO
    "K": ("constraints", True),
    "F": ("conditions", True),
    "P": ("priority", False),
    "H": ("confidence", False),
    "Y": ("references", True),
    "N": ("negations", True),
    "G": ("goal", False),
    "O": ("output", True),
}
LETTER_OF = {field: k for k, (field, _) in ATOMS.items()}

# canonical order used by the encoder
ORDER = ["V", "I", "A", "D", "E", "T", "L", "H", "Y", "N", "K", "F", "P", "G", "O"]

INTENTS = {
    "REQUEST_ANALYSIS", "REQUEST_COMPARISON", "REQUEST_SEARCH", "REQUEST_SUMMARY",
    "REQUEST_GENERATION", "REQUEST_TRANSLATION", "REQUEST_VALIDATION",
    "REQUEST_EXECUTION", "REQUEST_RETRIEVAL", "REQUEST_TRANSFORMATION",
    # protocol-level (spec §33)
    "CAPABILITY_QUERY", "CAPABILITY_RESPONSE",
}

ACTIONS = {
    "ANALYZE", "COMPARE", "FIND", "SEARCH", "SUMMARIZE", "GENERATE", "CREATE",
    "CALCULATE", "CHECK", "VALIDATE", "TRANSLATE", "GET", "RETRIEVE", "DELETE",
    "EXECUTE", "TRANSFORM", "CLASSIFY", "EXTRACT", "PREDICT",
    "UPDATE", "ENABLE", "DISABLE", "SEND", "INCLUDE", "EXCLUDE",
}

ACTION_TO_INTENT = {
    "ANALYZE": "REQUEST_ANALYSIS", "FIND": "REQUEST_ANALYSIS",
    "COMPARE": "REQUEST_COMPARISON",
    "SEARCH": "REQUEST_SEARCH",
    "SUMMARIZE": "REQUEST_SUMMARY",
    "GENERATE": "REQUEST_GENERATION", "CREATE": "REQUEST_GENERATION",
    "TRANSLATE": "REQUEST_TRANSLATION",
    "CHECK": "REQUEST_VALIDATION", "VALIDATE": "REQUEST_VALIDATION",
    "DELETE": "REQUEST_EXECUTION", "EXECUTE": "REQUEST_EXECUTION",
    "CALCULATE": "REQUEST_EXECUTION",
    "GET": "REQUEST_RETRIEVAL", "RETRIEVE": "REQUEST_RETRIEVAL",
    "TRANSFORM": "REQUEST_TRANSFORMATION", "CLASSIFY": "REQUEST_ANALYSIS",
    # 0.3 extension actions (ASSUMPTION, see ARCHITECTURE.md)
    "UPDATE": "REQUEST_EXECUTION", "ENABLE": "REQUEST_EXECUTION", "DISABLE": "REQUEST_EXECUTION",
    "SEND": "REQUEST_EXECUTION", "UNSPECIFIED": "REQUEST_EXECUTION", "INCLUDE": "REQUEST_TRANSFORMATION", "EXCLUDE": "REQUEST_TRANSFORMATION",
    "EXTRACT": "REQUEST_RETRIEVAL", "PREDICT": "REQUEST_ANALYSIS",
}

GOALS = {
    "ANOMALY_DETECTION", "COMPARISON", "SUMMARY", "TRANSLATION", "VALIDATION",
    "DATA_RETRIEVAL", "CONTENT_GENERATION",
}
OUTPUTS = {"JSON", "CSV", "TABLE", "TEXT", "REPORT", "AIXL", "MARKDOWN"}
RELATIVE_TIMES = {"TODAY", "YESTERDAY", "TOMORROW", "THIS_WEEK", "THIS_MONTH", "THIS_YEAR"}


def derive_goal(actions, entities, negated=()):
    """Mechanical G rule (card v0.2.1). Negated actions never count. Precedence:
    COMPARE -> COMPARISON; ANOMALY in E and (ANALYZE|FIND) -> ANOMALY_DETECTION; SUMMARIZE -> SUMMARY;
    TRANSLATE -> TRANSLATION; first action GENERATE|CREATE -> CONTENT_GENERATION;
    first action GET|RETRIEVE|SEARCH -> DATA_RETRIEVAL; otherwise no G."""
    live = [a for a in actions if a not in set(negated)]
    if "COMPARE" in live: return "COMPARISON"
    if "ANOMALY" in entities and {"ANALYZE", "FIND"} & set(live): return "ANOMALY_DETECTION"
    if "SUMMARIZE" in live: return "SUMMARY"
    if "TRANSLATE" in live: return "TRANSLATION"
    if live and live[0] in ("GENERATE", "CREATE"): return "CONTENT_GENERATION"
    if live and live[0] in ("GET", "RETRIEVE", "SEARCH"): return "DATA_RETRIEVAL"
    return ""


def derive_intent(actions, negated=()):
    """Card v0.2.3: cross out negated actions, look up the FIRST action left; if all are
    crossed out use the first action; no action -> UNKNOWN.
    E-INTEROP fix (2026-09-29): a value outside the known action vocabulary (e.g. an encoder writing
    the noun `A:ANALYSIS` instead of the verb `A:ANALYZE`) used to crash the whole comparison with an
    uncaught KeyError. A protocol must degrade gracefully on a value it doesn't recognize, not crash —
    that IS the interoperability requirement. Now falls back to UNKNOWN, same as no action at all."""
    neg = set(negated)
    live = [a for a in actions if a not in neg]
    main = live[0] if live else (actions[0] if actions else None)
    return ACTION_TO_INTENT.get(main, "UNKNOWN") if main else "UNKNOWN"
