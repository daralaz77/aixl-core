"""Option E (V1 audit): integrity envelope = NATURAL text + short semantic fingerprint. The receiver re-derives the fingerprint from the text it
actually holds (or from its own paraphrase/interpretation) and compares. Three honest outcomes:
  MATCH       both sides complete and fingerprints equal
  MISMATCH    both complete and fingerprints differ  (meaning drift detected)
  UNVERIFIED  at least one side is outside what the translator fully encodes (completeness fails) -> NO claim either way
Nothing here compresses; it only detects."""
from aixl.core.completeness import check_completeness
from aixl.core.fingerprint import fingerprint_graph
from aixl.gate import strict_complete
from aixl.translators.natural_to_semantic import to_graph


def _fp(text):
    g = to_graph(text)
    complete = bool(check_completeness(text, g).get("complete")) and strict_complete(text, g)
    return fingerprint_graph(g, length=8), complete


def seal(text: str) -> dict:
    fp, complete = _fp(text)
    return {"text": text, "fp": fp if complete else None, "verifiable": complete, "v": "AIXL-ENV-1"}


def verify(envelope: dict, received_text: str) -> str:
    fp, complete = _fp(received_text)
    if not envelope.get("verifiable") or not complete:
        return "UNVERIFIED"
    return "MATCH" if fp == envelope["fp"] else "MISMATCH"
