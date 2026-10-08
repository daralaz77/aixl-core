"""Internal guard: decide whether a candidate text kept the meaning of its source (fail-closed).

PASS only when (1) no critical-term / number / negation mismatch under the profile and (2) the AIXL comparator
agrees (EQUIVALENT) when the profile requires it. Everything else is REVIEW (send to a human or the 2-of-2 arbiter,
docs/EVIDENCE.md). PASS is *not* a proof of equivalence: it means "no known loss signal was found".
"""
from __future__ import annotations
import json, os, re, unicodedata
from dataclasses import dataclass, field

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROFILE_DIR = os.path.join(ROOT, "data", "guard")


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", t.lower())
    return "".join(c for c in t if not unicodedata.combining(c))


@dataclass
class GuardResult:
    decision: str                     # PASS | REVIEW
    reasons: list = field(default_factory=list)
    aixl_verdict: str | None = None

    @property
    def passed(self) -> bool:
        return self.decision == "PASS"


_cache: dict = {}


def load_profile(name: str) -> dict:
    if name not in _cache:
        with open(os.path.join(PROFILE_DIR, f"{name}.json"), encoding="utf-8") as fh:
            prof = json.load(fh)
        with open(os.path.join(PROFILE_DIR, "common.json"), encoding="utf-8") as fh:
            common = json.load(fh)
        classes = dict(common["classes"]) if prof.get("use_common_classes", True) else {}
        classes.update(prof.get("classes", {}))
        prof["_classes"] = {k: re.compile(v) for k, v in classes.items()}
        prof["_canon"] = [(re.compile(rx), tpl) for rx, tpl in prof.get("canon", [])]
        _cache[name] = prof
    return _cache[name]


_WORDS = {w: str(i) for i, w in enumerate("cero uno dos tres cuatro cinco seis siete ocho nueve diez once doce trece catorce quince veinte treinta cuarenta sesenta noventa cien".split())}
_WORDS.update({"cero": "0", "diez": "10", "once": "11", "doce": "12", "trece": "13", "catorce": "14", "quince": "15", "veinte": "20",
               "treinta": "30", "cuarenta": "40", "sesenta": "60", "noventa": "90", "cien": "100", "un": "1", "una": "1"})


def _numbers(t: str, minlen: int, ignore=()) -> list:
    out = [m.replace(".", "").replace(",", "") for m in re.findall(r"\d+(?:[.,]\d+)*", t)]
    out += [_WORDS[w] for w in re.findall(r"[a-z]+", t) if w in _WORDS and w not in ("un", "una", "uno")]
    return sorted(n for n in out if len(n) >= minlen and n not in ignore)


def _proper(text: str) -> set:
    words = re.findall(r"[^\W\d_]+", text)
    out = set()
    for m in re.finditer(r"(?<![.!?]\s)(?<!^)\b([A-Z\u00c1\u00c9\u00cd\u00d3\u00da\u00d1][a-zA-Z\u00e1\u00e9\u00ed\u00f3\u00fa\u00f1]+)", text):
        out.add(_norm(m.group(1)))
    return out


def _classes(t: str, prof: dict) -> set:
    return {k for k, rx in prof["_classes"].items() if rx.search(t)}


def _canon(t: str, prof: dict) -> set:
    out = set()
    for rx, tpl in prof["_canon"]:
        for m in rx.finditer(t):
            out.add(m.expand(tpl))
    return out


_STOP = set("""con sin por que una uno unos unas del los las les sus mis pero esa ese eso esto esta este cada muy mas aun asi ser fue son han hay
solicito pido quiero requiero favor mediante cuando donde porque aunque sobre entre desde hasta hacia durante segun tambien ademas
trainer instruccion como cada otro otra otros otras esta este estos estas ellos ellas mismo misma tiene tener haber hacer hace hacen pueda puedan puede
sean sera sido esta estan estaba estaban para pero sino acaba acabas cual cuales quien quienes todo toda todos todas siempre dicha dicho dichos dichas""".split())


def _stems(t: str) -> set:
    return {w[:4] for w in re.findall(r"[a-z]+", t) if len(w) >= 4 and w not in _STOP}


def _covered_by_class(t: str, prof: dict) -> set:
    """stems of source words that sit inside a critical-class match (their equality is checked by the class set instead)"""
    out = set()
    for rx in prof["_classes"].values():
        for m in rx.finditer(t):
            out |= {w[:4] for w in re.findall(r"[a-z]+", m.group(0)) if len(w) >= 4}
    return out


def _consume(t: str, prof: dict) -> str:
    for rx, _ in prof["_canon"]:
        t = rx.sub(" ", t)
    return t


def guard(source: str, candidate: str, profile: str, use_aixl: bool = True) -> GuardResult:
    prof = load_profile(profile)
    from aixl.core.normalizer import sanitize_input
    hidden = []
    for label, txt in (("source", source), ("candidate", candidate)):
        clean, found = sanitize_input(txt)
        if found:
            hidden.append(f"{label}:{','.join(found)}")
        if label == "source": source = clean
        else: candidate = clean
    a, b = _norm(source), _norm(candidate)
    reasons: list = [f"HIDDEN_CHARS {h}" for h in hidden]
    if a.strip() == b.strip() and not hidden:
        return GuardResult("PASS", ["IDENTICAL"], None)
    ca, cb = _canon(a, prof), _canon(b, prof)
    if prof.get("canon_required") and ca != cb:
        reasons.append(f"CANON_MISMATCH only_source={sorted(ca - cb)} only_candidate={sorted(cb - ca)}")
    if prof.get("canon_required") and not ca:
        reasons.append("SOURCE_NOT_RECOGNIZED")
    if prof.get("canon_leftover"):
        left = [w for w in re.findall(r"[a-z]+", _consume(b, prof)) if w not in set(prof["canon_leftover"])]
        if left:
            reasons.append(f"CANDIDATE_EXTRA_CONTENT {sorted(set(left))}")
    if prof.get("check_coverage"):
        miss = sorted(_stems(a) - _stems(b) - _covered_by_class(a, prof) - set(prof.get("coverage_allow", [])))
        if miss:
            reasons.append(f"DROPPED_CONTENT {miss}")
    if prof.get("max_added_stems") is not None:
        extra = sorted(_stems(b) - _stems(a) - set(prof.get("added_allow", [])))
        if len(extra) > prof["max_added_stems"]:
            reasons.append(f"ADDED_CONTENT {extra}")
    for cls in prof.get("strict_added", []):
        rx = prof["_classes"].get(cls)
        if rx and rx.search(b) and not rx.search(a):
            reasons.append(f"ADDED_{cls}")
    if prof.get("check_numbers", True):
        ig = prof.get("ignore_numbers", ())
        na, nb = _numbers(a, prof.get("number_minlen", 1), ig), _numbers(b, prof.get("number_minlen", 1), ig)
        if na != nb:
            reasons.append(f"NUMBERS source={na} candidate={nb}")
    if prof.get("check_proper_nouns"):
        pa, pb = _proper(source), _proper(candidate)
        if pa != pb:
            reasons.append(f"PROPER_NOUNS only_source={sorted(pa - pb)} only_candidate={sorted(pb - pa)}")
    ka, kb = _classes(a, prof), _classes(b, prof)
    if ka != kb:
        reasons.append(f"CRITICAL_TERMS only_source={sorted(ka - kb)} only_candidate={sorted(kb - ka)}")
    if prof.get("order_ids"):
        oa, ob = re.findall(prof["order_ids"], source), re.findall(prof["order_ids"], candidate)
        if oa and oa != ob:
            reasons.append(f"ORDER source={oa} candidate={ob}")
    verdict = None
    mode = prof.get("aixl_mode", "required")
    if use_aixl and mode != "off":
        import aixl
        verdict = aixl.compare(source, candidate).verdict
        if verdict != "EQUIVALENT" and mode == "required":
            reasons.append(f"AIXL_{verdict}")
    return GuardResult("REVIEW" if reasons else "PASS", reasons, verdict)


def guard_actions(instruction: str, actions: list, profile: str = "robot_school_actions") -> GuardResult:
    """Realization check (not equivalence): does at least one recorded action realise each action the instruction asks for?
    `actions` = [{"verb": ..., "description": ...}]. The instruction is Spanish, the actions are usually English (real episodes),
    so each rule maps an instruction-side class to the verbs/words that would realise it in either language."""
    prof = load_profile_actions(profile)
    ins = _norm(instruction)
    ev = _norm(" . ".join(f"{a.get('verb', '')} {a.get('description', '')}" for a in actions))
    reasons = []
    asked = [r for r in prof["_rules"] if r["ask"].search(ins)]
    if not asked:
        reasons.append("INSTRUCTION_NOT_RECOGNIZED")
    for r in asked:
        if not r["done"].search(ev):
            reasons.append(f"NOT_REALIZED {r['name']}")
    if not actions:
        reasons.append("NO_ACTIONS")
    return GuardResult("REVIEW" if reasons else "PASS", reasons)


def load_profile_actions(name: str) -> dict:
    key = "actions:" + name
    if key not in _cache:
        with open(os.path.join(PROFILE_DIR, f"{name}.json"), encoding="utf-8") as fh:
            prof = json.load(fh)
        prof["_rules"] = [{"name": n, "ask": re.compile(a), "done": re.compile(d)} for n, a, d in prof["rules"]]
        _cache[key] = prof
    return _cache[key]
