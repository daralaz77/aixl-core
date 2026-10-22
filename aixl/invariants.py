"""Critical-slot INVARIANTS: what must survive a hop, checked WITHOUT understanding the nouns.

Equivalence needs a vocabulary; preservation of the critical slots does not. A relay can paraphrase every noun and still be faithful, but it must not lose a
negation, change a number / date / time / unit, flip a modality (`must`->`may`), turn `and` into `or`, move a weekday, drop a condition or a clause, or swap a
named entity. Those slots are closed-class words, digits and capitalised tokens: they are extracted deterministically in ES/EN/PT, language-independent codes.

`extract(text)` -> {family: frozenset(slot)}.  `check(source, relay)` -> violations (family, only_in_source, only_in_relay).
It makes NO claim of equivalence: no violation means "no critical slot visibly changed", never "same meaning". Families are measured, not assumed:
benchmarks/invariants_eval.py reports per-family recall / false-alarm on labelled pairs of other authors."""
import collections
import re

from aixl.core.limits import check_size
from aixl.translators.auto import to_graph_auto

# constraint prefix -> family. Everything else (entities, data, actions) is vocabulary-dependent and deliberately NOT an invariant.
_FAMILY = {
    "CMP": "COMPARATOR", "COND": "CONDITION", "DISJ": "DISJUNCTION", "DOW": "WEEKDAY", "DOWREL": "WEEKDAY_RELATION", "DAYM": "DAY_OF_MONTH",
    "TIME_AT": "CLOCK", "TIME_BETWEEN": "CLOCK", "BEFORE": "CLOCK", "AFTER": "CLOCK", "MEAS": "UNIT", "PER": "UNIT", "MODAL": "MODALITY", "NEGN": "NEGATION",
    "NEGW": "NEGATION", "ONLY": "ONLY", "FREQ": "FREQUENCY", "CLAUSES": "CLAUSES", "MOD": "MODIFIER", "QTY": "QUANTITY", "AGE>": "AGE", "AGE<": "AGE",
    "SEQ": "SEQUENCE", "FORBID_": "NEGATION", "ALLOW_": "PERMISSION",
}
_NAME = re.compile(r"(?<![\w@#])(?:@[A-Za-z0-9_.]+|#\d+|[\w.+-]+@[\w-]+\.[\w.-]+|https?://\S+)")
_CAP = re.compile(r"(?<=[\s,;:(])([A-ZÁÉÍÓÚÑ][\wáéíóúñ]{2,})")        # capitalised word NOT at the start of a sentence
_WORD = re.compile(r"[a-z\u00e1\u00e9\u00ed\u00f3\u00fa\u00f1\u00e3\u00f5\u00e7]+")
_PRONOUNS = frozenset("he she him her his hers they them their theirs it its el ella ellos ellas le les lo la su sus ele ela eles elas dele dela deles delas seu sua seus suas".split())
_NUM = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)?(?![\w])")


def _family_of(constraint: str):
    for pre, fam in _FAMILY.items():
        if constraint.startswith(pre):
            return fam
    return None


def extract(text: str) -> dict:
    check_size(text)
    g = to_graph_auto(text)
    c = g.canonical()
    out: dict = {}
    for k in c["constraints"]:
        fam = _family_of(k)
        if fam:
            out.setdefault(fam, set()).add(k)
    if c.get("negation"):
        out.setdefault("NEGATION", set()).add("NEG")
    for t in c.get("time", ()):
        out.setdefault("DATE", set()).add(str(t))
    for q in c.get("quantities", ()):
        out.setdefault("QUANTITY", set()).add(str(q))
    text = text.strip()
    caps = {m.group(1).lower() for m in _CAP.finditer(text) if text[:m.start()].rstrip()[-1:] not in ("", ".", "!", "?", "\u00bf", "\u00a1", "*", '"', "\u201c", "\u2018", "'", ">", "-", "\u2022", "#")}
    names = {m.group(0).lower() for m in _NAME.finditer(text)} | caps
    acts = set(c.get("actions") or ())
    if acts:
        out["ACTION"] = acts                                     # the lexicon's verbs: `send` -> `cancel` is a different action
    order = tuple(m.group(0).lower() for m in sorted(list(_NAME.finditer(text)) + [m for m in _CAP.finditer(text) if m.group(1).lower() in caps], key=lambda m: m.start()))
    if len(order) >= 2:
        out["NAME_ORDER"] = {order}                              # who comes first: `Ana ... Luis` vs `Luis ... Ana` (role swap)
    pron = collections.Counter(w for w in _WORD.findall(text.lower()) if w in _PRONOUNS)
    if pron:
        out["PRONOUN"] = {f"{k}:{v}" for k, v in pron.items()}     # `he`/`she`, `él`/`ella`, `his`/`her`: whom a pronoun points to
    if names:
        out["NAME"] = names
    nums = {n.replace(",", ".") for n in _NUM.findall(text)}
    if nums:
        out["NUMBER"] = nums
    return {k: frozenset(v) for k, v in out.items()}


def check(source: str, relay: str, families=None) -> list:
    """Violations between a source text and its relay: [(family, only_in_source, only_in_relay)] for each family whose slot sets differ."""
    a, b = extract(source), extract(relay)
    out = []
    for fam in sorted(set(a) | set(b)):
        if families is not None and fam not in families:
            continue
        sa, sb = a.get(fam, frozenset()), b.get(fam, frozenset())
        if sa != sb:
            out.append((fam, tuple(sorted(sa - sb)), tuple(sorted(sb - sa))))
    return out


# Families that flag a corruption without flagging benign near-verbatim edits (selection rule and numbers: benchmarks/invariants_relay_eval.py, LIMITATIONS.md E-RELAY).
RELAY_FAMILIES = frozenset({"ACTION", "NAME_ORDER", "PRONOUN", "CLAUSES", "COMPARATOR", "CONDITION", "DATE", "DISJUNCTION", "MODALITY", "MODIFIER", "NAME", "NEGATION", "NUMBER", "ONLY", "QUANTITY", "SEQUENCE", "WEEKDAY"})


def relay_check(source: str, relay: str) -> dict:
    """Did a critical slot change between `source` and its `relay`?  Built for NEAR-VERBATIM relays (copy, truncation, a flipped word, an injected
    clause). It is NOT an equivalence test: `ok: true` means "no critical slot visibly changed", never "same meaning" — a rewording that moves a negation
    into a different construction can raise a violation, and an antonym swap (`send` -> `cancel`) or a vocabulary-only change is invisible to it.
    Measured (other authors' seeds, families chosen on the project's own): 94.7 % of meaning-changing corruptions flagged, 0.1 % of benign edits flagged."""
    try:
        v = check(source, relay, RELAY_FAMILIES)
    except Exception as e:                                        # noqa: BLE001 — fail closed: an input we cannot analyse is not "ok"
        return {"ok": False, "violations": [], "reason": f"not analysed: {type(e).__name__}", "regime": "near-verbatim relay"}
    return {"ok": not v, "regime": "near-verbatim relay",
            "violations": [{"family": f, "only_in_source": list(a), "only_in_relay": list(b)} for f, a, b in v],
            "note": "ok:true = no critical slot visibly changed; it is not a proof of equivalence"}
