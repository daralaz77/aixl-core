"""Option E (V1 audit): integrity envelope = NATURAL text + short semantic fingerprint. The receiver re-derives the fingerprint from the text it
actually holds (or from its own paraphrase/interpretation) and compares. Three honest outcomes:
  MATCH       both sides complete and fingerprints equal
  MISMATCH    both complete and fingerprints differ  (meaning drift detected)
  UNVERIFIED  at least one side is outside what the translator fully encodes (completeness fails) -> NO claim either way
Nothing here compresses; it only detects."""
from aixl.core.completeness import is_complete
from aixl.core.connectives import or_count
from aixl.core.fingerprint import fingerprint_graph
from aixl.translators.natural_to_semantic import to_graph


def _fp(text):
    from aixl.core.limits import InputTooLarge
    try:
        g = to_graph(text)
    except InputTooLarge:
        return None, False                                  # too large to analyse: no claim either way
    complete = is_complete(text, g)
    return fingerprint_graph(g, length=8), complete


ENV_VERSION = "AIXL-ENV-2"
SUPPORTED_VERSIONS = frozenset({"AIXL-ENV-1", "AIXL-ENV-2"})
# ENV-2 (2026-10-13) = ENV-1 + the connective witness `or` (count of or/o/ou/u tokens). ENV-1 envelopes are still accepted: the witness is recomputed from
# their `text`. Unknown versions and malformed envelopes get UNVERIFIED (no claim), never an exception. The envelope is NOT signed: it states what the
# sender sealed; authenticating the sender is the transport's job (A2A token, ADR-018).


def seal(text: str) -> dict:
    fp, complete = _fp(text)
    return {"text": text, "fp": fp if complete else None, "verifiable": complete, "v": ENV_VERSION, "or": or_count(text)}


def _sealed_or(envelope: dict):
    if isinstance(envelope.get("or"), int) and not isinstance(envelope.get("or"), bool):
        return envelope["or"]
    t = envelope.get("text")
    return or_count(t) if isinstance(t, str) else None            # ENV-1 envelopes: derive it from the sealed text


def verify(envelope: dict, received_text: str) -> str:
    if not isinstance(envelope, dict) or envelope.get("v") not in SUPPORTED_VERSIONS or not isinstance(received_text, str):
        return "UNVERIFIED"
    fp, complete = _fp(received_text)
    if not envelope.get("verifiable") or not complete or not envelope.get("fp"):
        return "UNVERIFIED"
    sealed_or = _sealed_or(envelope)
    if sealed_or is None:
        return "UNVERIFIED"                                       # cannot establish the connective witness: no claim
    if sealed_or != or_count(received_text):                      # AND<->OR flips are invisible to the fingerprint (y/o are function words)
        return "MISMATCH"
    return "MATCH" if fp == envelope["fp"] else "MISMATCH"
