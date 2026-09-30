"""FASE 3 — Controlled ontology (extensible) + configuration loading."""
import json
import os
from datetime import date, timedelta

REL_DAY = {"TODAY": 0, "YESTERDAY": -1, "TOMORROW": 1}
REL_MONTH = {"THIS_MONTH": 0, "LAST_MONTH": -1, "NEXT_MONTH": 1}
REL_YEAR = {"THIS_YEAR": 0, "LAST_YEAR": -1, "NEXT_YEAR": 1}


def resolve_relative_time_token(v: str, today: date) -> str:
    """0.3 extension (E-DATE, 2026-09-27): resolve a single day/month/year-granularity relative time
    token against a reference date. Used at BOTH layers — the rule-based translator (on `frame.time`,
    so BEFORE=/AFTER=/range-to-period see a concrete date) and `SemanticGraph.canonical()` (on TIME
    nodes regardless of origin, so an LLM-encoded `T:TODAY` also compares equal to a literal date —
    the translator-only fix left this gap on the LLM route, found by set 7 / E-DATE round 2). Verified
    against the corpus first: blind3 A3-024, set6 S6-009/S6-061 are three independent blind-authored
    pairs across different rounds that all label relative-vs-absolute same-day/month EQUIVALENT.
    Week-granularity words (THIS_WEEK/LAST_WEEK/NEXT_WEEK) are deliberately left unresolved: AIXL has
    no week-range literal to resolve them to without inventing one."""
    if v in REL_DAY:
        return (today + timedelta(days=REL_DAY[v])).isoformat()
    if v in REL_MONTH:
        y, mo = today.year, today.month + REL_MONTH[v]
        while mo < 1: mo += 12; y -= 1
        while mo > 12: mo -= 12; y += 1
        return f"{y:04d}-{mo:02d}"
    if v in REL_YEAR:
        return str(today.year + REL_YEAR[v])
    return v


def resolve_relative_time_str(time_str: str, today: date) -> str:
    if not time_str:
        return time_str
    return ",".join(resolve_relative_time_token(v, today) for v in time_str.split(","))

ACTIONS = ["ANALYZE", "COMPARE", "FIND", "CREATE", "DELETE", "CHECK", "TRANSLATE", "GENERATE", "CALCULATE", "SEARCH",
           "RETRIEVE", "EXECUTE", "UPDATE",
           # legacy 0.2 actions kept for compatibility
           "SUMMARIZE", "VALIDATE", "GET", "TRANSFORM", "CLASSIFY", "EXTRACT", "PREDICT",
           # ASSUMPTION: needed by the contradiction pairs of the master prompt (ENABLE/DISABLE, INCLUDE/EXCLUDE) and SEND
           "ENABLE", "DISABLE", "SEND", "INCLUDE", "EXCLUDE"]
ENTITIES = ["PERSON", "COMPANY", "PRODUCT", "REPORT", "DOCUMENT", "RESULT", "ANOMALY", "EVENT", "LOCATION", "MODEL"]
DATA = ["SALES", "CUSTOMERS", "USERS", "DATA", "DATASET", "IMAGE", "AUDIO", "VIDEO"]
TIME_KINDS = ["DATE", "YEAR", "QUARTER", "MONTH", "WEEK", "PERIOD"]
MODIFIERS = ["CONFIDENCE", "PRIORITY", "LIMIT", "FORMAT", "LANGUAGE"]
OUTPUT_FORMATS = ["JSON", "CSV", "TABLE", "TEXT", "REPORT", "AIXL", "MARKDOWN", "PDF", "XLSX", "HTML", "XML", "DOCX"]

# explicit oppositions (same object): (a, b)
ANTONYM_ACTIONS = [("ENABLE", "DISABLE"), ("INCLUDE", "EXCLUDE")]
DIMENSIONS = ["intent", "actions", "entities", "data", "time", "location", "constraints", "conditions", "negation",
              "references", "quantities", "goal", "output", "modifiers"]


def type_of(value: str) -> str:
    v = value.upper()
    if v in ACTIONS: return "ACTION"
    if v in ENTITIES: return "ENTITY"
    if v in DATA: return "DATA"
    return "UNKNOWN"


_CFG = None


def load_config(path: str | None = None) -> dict:
    """Load weights/severities. Pass a path to override; default file: data/config.json."""
    global _CFG
    if path is None and _CFG is not None:
        return _CFG
    p = path or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "config.json")
    with open(p, encoding="utf-8") as fh:
        cfg = json.load(fh)
    if path is None:
        _CFG = cfg
    return cfg


def rank(level: str) -> int:
    return ["NONE", "MINOR", "MODERATE", "MAJOR", "CRITICAL"].index(level)
