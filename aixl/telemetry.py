"""OpenTelemetry: report AIXL verdicts as GenAI `gen_ai.evaluation.result` events, so any OTel stack (Langfuse, Grafana, Datadog, a collector...) can show "was the meaning preserved?" next to its traces.
OpenTelemetry records evaluation results but does not compute them: AIXL is the evaluator, this module is the carrier.

Names checked against the official definition (github.com/open-telemetry/semantic-conventions-genai, model/gen-ai/events.yaml and registry.yaml, main branch, 2026-10-30): event `gen_ai.evaluation.result`, stability **development**;
attributes `gen_ai.evaluation.name` (required), `gen_ai.evaluation.score.label` (low-cardinality string, the implementation should document its values: see LABELS), `gen_ai.evaluation.explanation` (recommended), `gen_ai.response.id`
(recommended, when available). `gen_ai.evaluation.score.value` is "if applicable" and is NOT emitted: AIXL verdicts are categories, and a similarity number would read as a proof it is not. These names are in Development and may change.
Privacy by design: the texts, the clauses and the slot values are NEVER sent — only the evaluation name, the verdict label, the names of the violated families and booleans. Everything is best effort: with no OpenTelemetry installed, or any
failure while emitting, the call is a no-op and the verdict is returned unchanged. Optional dependency: `opentelemetry-api` (extra `otel`); the application configures the SDK/exporter."""
from aixl.api.service import compare_verified
from aixl.invariants import relay_check
from aixl.logic import logic_compare

EVENT = "gen_ai.evaluation.result"
NAME_RELAY = "aixl.relay_check"
NAME_COMPARE = "aixl.compare_verified"
NAME_LOGIC = "aixl.logic_compare"
LABELS = {   # evaluation name -> the complete, low-cardinality set of labels this module can emit
    NAME_RELAY: ("ok", "violation", "not_analysed"),
    NAME_COMPARE: ("equivalent", "not_equivalent", "inconclusive", "unverified"),
    NAME_LOGIC: ("equivalent_logic", "different_logic", "abstain"),
}
_counter = None


def available() -> bool:
    try:
        import opentelemetry._logs  # noqa: F401, PLC0415
        return True
    except ImportError:
        return False


def _default_logger():
    from opentelemetry._logs import get_logger  # noqa: PLC0415
    return get_logger("aixl")


def _count(name: str, label: str) -> None:
    global _counter
    try:
        from opentelemetry import metrics  # noqa: PLC0415
        if _counter is None:
            _counter = metrics.get_meter("aixl").create_counter("aixl.evaluations", description="AIXL evaluations by name and label (no content)")
        _counter.add(1, {"gen_ai.evaluation.name": name, "gen_ai.evaluation.score.label": label})
    except Exception:                                                        # noqa: BLE001 — best effort
        pass


def record_evaluation(name: str, label: str, *, explanation: str | None = None, response_id: str | None = None, attributes: dict | None = None, logger=None) -> bool:
    """Emit one `gen_ai.evaluation.result` event. Returns True if it was handed to a logger, False otherwise (never raises). `label` must be one of LABELS[name]: anything else is refused (cardinality)."""
    try:
        if label not in LABELS.get(name, ()):
            return False
        attrs = {"gen_ai.evaluation.name": name, "gen_ai.evaluation.score.label": label}
        if explanation:
            attrs["gen_ai.evaluation.explanation"] = explanation[:500]
        if response_id:
            attrs["gen_ai.response.id"] = str(response_id)[:200]
        for k, v in (attributes or {}).items():
            if not k.startswith("aixl."):
                continue                                                     # only our own namespace; never arbitrary caller keys
            if isinstance(v, (str, bool, int, float)):
                attrs[k] = v
            elif isinstance(v, (list, tuple)) and all(isinstance(x, str) for x in v):
                attrs[k] = list(v)
        (logger or _default_logger()).emit(event_name=EVENT, attributes=attrs)
        _count(name, label)
        return True
    except Exception:                                                        # noqa: BLE001
        return False


def relay_check_evaluated(source: str, relay: str, *, response_id: str | None = None, logger=None, **kwargs) -> dict:
    """`aixl.relay_check` + the evaluation event. `kwargs` go to relay_check (e.g. plural_audience=True). The result is returned unchanged."""
    r = relay_check(source, relay, **kwargs)
    fams = sorted({v["family"] for v in r.get("violations", [])})
    label = "not_analysed" if r.get("reason") else ("ok" if r.get("ok") else "violation")
    expl = {"ok": "no critical slot visibly changed (not a proof of equivalence)", "violation": "changed critical slot families: " + ", ".join(fams), "not_analysed": "the pair could not be analysed"}[label]
    record_evaluation(NAME_RELAY, label, explanation=expl, response_id=response_id, attributes={"aixl.violation.families": fams, "aixl.regime": str(r.get("regime", ""))}, logger=logger)
    return r


def compare_verified_evaluated(a: str, b: str, *, response_id: str | None = None, logger=None) -> dict:
    """`aixl.compare_verified` + the evaluation event (verdict only: no similarity score, no text)."""
    r = compare_verified(a, b)
    label = str(r.get("verdict", "unverified")).lower()
    if label not in LABELS[NAME_COMPARE]:
        label = "unverified"
    record_evaluation(NAME_COMPARE, label, explanation=f"verified={bool(r.get('verified'))}; difference_reliable={r.get('difference_reliable')}", response_id=response_id,
                      attributes={"aixl.verified": bool(r.get("verified")), "aixl.complete": bool(r.get("complete"))}, logger=logger)
    return r


def logic_compare_evaluated(a: str, b: str, *, response_id: str | None = None, logger=None) -> dict:
    """`aixl.logic_compare` + the evaluation event (verdict and the generic abstention reason; no clause text)."""
    r = logic_compare(a, b)
    label = r["verdict"].lower()
    reason = None if label != "abstain" else str(r.get("reason", ""))[:80]
    record_evaluation(NAME_LOGIC, label, explanation=reason, response_id=response_id, logger=logger)
    return r
