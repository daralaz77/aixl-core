"""Deterministic, VETO-ONLY second opinion for translators that are lossy around irreversible actions.

Evidence (distill/irreversible_stress.py, 96 minimal pairs, 2026-10-02):
  * the distilled local model encodes Portuguese "exclua"/"apague" as EXCLUDE/DISABLE (the card lists `exclui` under
    EXCLUDE), so a gate that only looks at the output's `A:` atom caught 22/50 Portuguese delete/send texts (EN 51/51,
    ES 50/50): irreversible actions slipped through the language the vocabulary is weakest in;
  * the model (and even more the rule-based translator, 19.2 % unsafe) sometimes calls two instructions equivalent while
    one of them drops "without confirmation" vs "after confirmation", "only if" vs "even if", before/after, a number or id.

This module never says "equivalent". It can only turn an EQUIVALENT verdict into "needs review" (or flag that an
irreversible action was not recognised in the AIXL), so it cannot create a false equivalence and cannot lower the
measured precision of the translator; the cost is extra escalations, which the caller can count.

usage: assess(text_a, text_b, aixl_a, aixl_b, equivalent) -> {"escalate": bool, "reasons": [...]}
       text_irreversible(text) -> set of irreversible actions the TEXT mentions (EN/ES/PT), independent of the translator.
"""
import re

# verbs that mean permanent removal / outbound communication, per irreversible action in data/config.json
_VERBS = {
    "DELETE": r"\b(delet\w*|remov\w*|eras\w*|purg\w*|wip\w*|destro\w*|drop\w*|elimin\w*|borr\w*|suprim\w*|destru\w*|"
              r"exclu(?:a|am|as|i|ir|ir[ií]a|[ií]d[oa]s?)|exclu[ií]\w*|apag\w*|remov\w*|quit\w*\s+permanente\w*)\b",
    "SEND": r"\b(send\w*|sent|e-?mail\w*|mail\w*|forward\w*|post\w*|publish\w*|env[ií]\w*|mand\w*|reenv\w*|public\w*|"
            r"encaminh\w*|reenvi\w*)\b",
}
_CUES = {
    "NEG": r"\b(not|n't|never|nunca|jam[aá]s|n[aã]o|no)\b",
    "WITHOUT": r"\b(without|sin|sem)\b",
    "ONLY_IF": r"\b(only if|solo si|s[oó]lo si|somente se|apenas se|unless|a menos que|salvo que|exceto se)\b",
    "EVEN_IF": r"\b(even if|even though|aunque|incluso si|mesmo que|mesmo se|ainda que)\b",
    "BEFORE": r"\b(before|prior to|ahead of|antes de|antes del|antes de la|antes d[oa]s?|antes das)\b",
    "MAX": r"\b(no more than|at most|up to|maximum|m[aá]xim[oa]s?|a lo sumo|at the most|at\u00e9)\b",
    "AFTER": r"\b(after|despu[eé]s de|depois de)\b",
    "CONFIRM": r"\b(confirm\w*|approv\w*|aprob\w*|aprov\w*|authori[sz]\w*|autoriz\w*)\b",
    "ALL": r"\b(all|every|todos?|todas?|cada)\b",
}
_THEN = re.compile(r"\b(then|afterwards?|luego|despu[eé]s|depois|e depois|y luego|entonces)\b", re.I)
_BACKUP = re.compile(r"\b(back ?up|copy|copia|c[oó]pia|respald\w*|backup|save|guard\w*|salv\w*)\b", re.I)
_NUM = re.compile(r"#?\d+(?:[.,]\d+)?")
_NUMWORDS = {"ten": 10, "twenty": 20, "thirty": 30, "fifty": 50, "hundred": 100, "diez": 10, "veinte": 20, "treinta": 30,
             "cincuenta": 50, "cien": 100, "ciento": 100, "dez": 10, "vinte": 20, "trinta": 30, "cinquenta": 50, "cem": 100,
             "cento": 100}
_NUMWORD_RX = re.compile(r"\b(" + "|".join(_NUMWORDS) + r")\b", re.I)
# "no more than N" / "at most N" are limits, not negations: drop them before the NEG cue is looked up
_LIMIT_RX = re.compile(_CUES["MAX"], re.I)


def text_irreversible(text, irreversible=("DELETE", "SEND")):
    """Irreversible actions the raw text mentions, in any of EN/ES/PT (deliberately conservative: over-flags)."""
    return {a for a in irreversible if a in _VERBS and re.search(_VERBS[a], text, re.I)}


def aixl_actions(aixl):
    m = re.search(r" A:(\S+)", aixl or "")
    return set(m.group(1).split(",")) if m else set()


def cue_signature(text):
    sig = {name for name, rx in _CUES.items() if re.search(rx, text, re.I)}
    if "MAX" in sig and "NEG" in sig and not re.search(_CUES["NEG"], _LIMIT_RX.sub(" ", re.sub(r"\b(?:no more than|no m[aá]ximo)\b", " ", text, flags=re.I)), re.I):
        sig.discard("NEG")
    sig |= {"N" + n.replace(",", ".").lstrip("#") for n in _NUM.findall(text)}
    sig |= {"N" + str(_NUMWORDS[w.lower()]) for w in _NUMWORD_RX.findall(text)}
    if _THEN.search(text):  # ordering of the irreversible verb vs. a backup/copy step
        v = min((m.start() for rx in _VERBS.values() for m in re.finditer(rx, text, re.I)), default=None)
        b = _BACKUP.search(text)
        if v is not None and b is not None:
            sig.add("ORDER_IRR_FIRST" if v < b.start() else "ORDER_BACKUP_FIRST")
    return frozenset(sig)


def assess(text_a, text_b, aixl_a, aixl_b, equivalent, irreversible=("DELETE", "SEND")):
    reasons = []
    irr = set(irreversible)
    mentioned = text_irreversible(text_a, irreversible) | text_irreversible(text_b, irreversible)
    recognised = (aixl_actions(aixl_a) | aixl_actions(aixl_b)) & irr
    if mentioned and not recognised:
        reasons.append("irreversible_verb_in_text_not_recognised_in_aixl")
    if mentioned or recognised:
        if equivalent:
            sa, sb = cue_signature(text_a), cue_signature(text_b)
            if sa != sb:
                reasons.append("modifier_mismatch_on_irreversible_action:" + ",".join(sorted(sa ^ sb)))
    return {"escalate": bool(reasons), "reasons": reasons}
