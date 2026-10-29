"""Hand-off contract: what MUST be present in an instruction before an agent acts on it (the receiving side of a hand-off).

`relay_check` asks "did the relay lose something the SOURCE had?". This asks the other question: "does the instruction we received carry the fields we need at all?" — e.g. a
deadline, a quantity, a named target. Missing fields -> state `input-required` (the receiver should ask the sender, not guess). It reuses the closed-class extractors of
`aixl.invariants`, so it works on open vocabulary, and it makes no claim about meaning: `ok` means "the required kinds of slot are present", never "the instruction is correct".
Required kinds (closed list): DATE (a date, clock time or weekday), NUMBER, NAME (a capitalised name, @handle, #id, e-mail or URL), CONDITION, USE_LIMIT.
Limits: NAME only sees capitalised tokens that are not at the start of a sentence: a lower-case name is NOT seen (without a capital letter `ana` is indistinguishable from `casa`), so
`NAME` must not be used to decide whether a recipient was given in text typed in lower case. Two ways to see it were measured and REJECTED (LIMITATIONS.md E-HANDOFF-NAMES): a given-name list and "the word
after a recipient preposition". If a recipient matters, have the sender declare it as a structured field instead of inferring it. DATE does not understand `soon`/`pronto`."""
from aixl.invariants import extract

KINDS = ("DATE", "NUMBER", "NAME", "CONDITION", "USE_LIMIT")


def present_kinds(text: str) -> frozenset:
    f = extract(text)
    out = set()
    if f.get("DATE") or f.get("WEEKDAY") or f.get("CLOCK") or f.get("DAY_OF_MONTH"):
        out.add("DATE")
    if f.get("NUMBER"):
        out.add("NUMBER")
    if f.get("NAME"):
        out.add("NAME")
    if f.get("CONDITION") or f.get("CONDITION_TEXT"):
        out.add("CONDITION")
    if f.get("USE_LIMIT"):
        out.add("USE_LIMIT")
    return frozenset(out)


def handoff_check(text: str, required) -> dict:
    """`required`: kinds from KINDS. Unknown kinds are an error, not silently ignored (a typo must not read as "satisfied")."""
    req = [str(r).strip().upper() for r in (required or [])]
    unknown = [r for r in req if r not in KINDS]
    if unknown:
        return {"ok": False, "state": "invalid-contract", "unknown_kinds": unknown, "allowed": list(KINDS)}
    try:
        have = present_kinds(text)
    except Exception as e:                                                         # noqa: BLE001 — fail closed: an input we cannot analyse is not "complete"
        return {"ok": False, "state": "input-required", "missing": req, "reason": f"not analysed: {type(e).__name__}"}
    missing = [r for r in req if r not in have]
    return {"ok": not missing, "state": "ready" if not missing else "input-required", "missing": missing, "present": sorted(have),
            "note": "ok:true = the required kinds of slot are present; it says nothing about whether the instruction is right"}
