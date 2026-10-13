"""Adversarial arena: attackers mutate seeds, oracles (ground truth BY CONSTRUCTION) judge, failures are minimized,
stored, and fed back as new seeds; attacker weights adapt to what actually breaks the code.

  python -m lab.arena.arena run --rounds 30 --seed 1     # attack, learn, persist state
  python -m lab.arena.arena replay                       # re-run stored failures: which are fixed / still open

Oracles never use the system under test to define "correct":
  META-*   a meaning-changing mutation must NOT be judged EQUIVALENT / must not pass the gate as lossless (unsafe = defect)
  WIRE-*   malformed AIXL must raise AixlError only (any other exception / hang = defect), never decode silently lossy
  COSM-*   cosmetic edits (case/space/final punctuation) must keep the semantic fingerprint
Limits: seeds are own-author; the oracles cover only the mutations listed; a clean arena is NOT proof of correctness."""
from __future__ import annotations

import argparse
import json
import random
import re
import signal
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
STATE, CORPUS = HERE / "state.json", HERE / "failures.jsonl"

SEEDS = [
 "Resume el informe en cinco puntos.", "Analiza las ventas de Q1 2026.", "Compara el dataset #77 con el dataset #81.",
 "Traduce el documento al inglés.", "Envía el informe a Ana.", "Elimina los registros duplicados.",
 "Borra el archivo temporal.", "Genera un reporte en JSON con los 10 clientes principales.",
 "Summarize the report in five bullet points.", "Delete the old backups.", "Send the invoice to Acme.",
 "Translate the text into English.", "Compare the two documents and list the differences.",
 "Analyze the sales for March 2026.", "Create a summary of 3 paragraphs.", "Export the data to CSV.",
 "Resuma o relatório em cinco pontos.", "Envie o relatório para Maria.", "Exclua os arquivos antigos.",
 "Analiza los videos de esta semana.", "Actualiza el precio de los 20 productos.", "Enable the notifications for all users.",
]
# Seeds that really TAKE the AIXL path of the gate (found by scanning the characterization corpus: only these 4 do). Without them the gate's AIXL
# branch -- the one oracles META-GATE-* guard -- was never executed by any attack (0 of the 22 seeds above reach it).
GATE_SEEDS = ["Analiza las ventas del primer trimestre de 2026.", "Analise as vendas do primeiro trimestre de 2026.", "Genera un PDF.", "Traduce el documento."]
SEEDS += GATE_SEEDS
# Seeds with a conjunction: the AND->OR attacker below needs one (found 2026-10-13: 'a Ana y a Luis' -> 'a Ana o a Luis' was MATCH in the envelope)
CONJ_SEEDS = ["Envía el informe a Ana y a Luis.", "Delete the old backups and the logs.", "Borra los archivos y las carpetas.", "Send the report to Ana and notify Luis."]
SEEDS += CONJ_SEEDS
# Seeds for the 2026-10-13 families: sequence, condition, quantifier/comparator, modality, and negation inside a conjunct.
LOGIC_SEEDS = ["Envía el informe y luego borra los registros antiguos.", "Send the report and then delete the old logs.",
               "Borra los respaldos si la auditoría pasó.", "Delete the backups if the audit passed.", "Archive the tickets when the client approves.",
               "Exporta al menos 10 registros.", "Export at most 5 records.", "Process more than 100 orders.", "Delete all the temporary files.",
               "You must delete the old backups.", "Debes borrar los respaldos antiguos.", "You may send the report to Ana.", "Puedes enviar el informe a Ana.",
               "Send the report to Ana and delete the old logs.", "Envía el informe y borra los registros antiguos."]
SEEDS += LOGIC_SEEDS

# ---- attackers: (name, kind, fn(text, rng)->text|None) ; kind META = meaning-changing, COSM = cosmetic ----------------
NEG_PRE = ["Never ", "Do not ", "Nunca ", "No quiero que "]
SWAP_NAMES = [("Ana", "Luis"), ("Maria", "Joao"), ("Acme", "Globex"), ("Q1", "Q2"), ("March", "April"), ("JSON", "CSV"), ("CSV", "JSON")]
ANTONYM = [("Elimina", "Crea"), ("Borra", "Guarda"), ("Delete", "Create"), ("Exclua", "Crie"), ("Enable", "Disable"),
           ("Envía", "Cancela"), ("Send", "Cancel"), ("Resume", "Amplía"), ("Summarize", "Expand")]
EXTRA = [" solo si el cliente lo aprueba", " only if the manager approves", " antes del viernes", " sin usar datos personales",
         " and notify the whole team", " y avisa a todo el equipo"]


def lc(t): return t[:1].lower() + t[1:]


def a_neg_prefix(t, r): return r.choice(NEG_PRE) + lc(t)
def a_neg_suffix(t, r): return t.rstrip(".") + r.choice([", pero no lo hagas.", ", but do not do it.", " (no hacerlo)."])
def a_num(t, r):
    m = list(re.finditer(r"\d+", t))
    if not m: return None
    x = r.choice(m); n = int(x.group()); return t[:x.start()] + str(n + r.choice([1, 9, 90])) + t[x.end():]
def a_name(t, r):
    c = [(a, b) for a, b in SWAP_NAMES if re.search(rf"\b{a}\b", t)]
    if not c: return None
    a, b = r.choice(c); return re.sub(rf"\b{a}\b", b, t, count=1)
def a_antonym(t, r):
    c = [(a, b) for a, b in ANTONYM if t.startswith(a)]
    if not c: return None
    a, b = r.choice(c); return b + t[len(a):]
def a_add_constraint(t, r): return t.rstrip(".") + r.choice(EXTRA) + "."
def a_drop_tail(t, r):
    m = re.search(r"\s(y|and|e|pero|but|con|with|en|in|a|to|para|for)\s", t)
    return t[:m.start()] + "." if m else None
LEX = [("todos", "algunos"), ("todas", "algunas"), ("all", "some"), ("antes", "después"), ("before", "after"), ("más de", "menos de"),
       ("more than", "less than"), ("con ", "sin "), ("with ", "without "), ("ayer", "mañana"), ("yesterday", "tomorrow"),
       ("lunes", "martes"), ("Monday", "Tuesday"), ("al menos", "como máximo"), ("at least", "at most"), ("kg", "g"),
       ("principales", "últimos"), ("top", "bottom"), ("first", "last"), ("primer", "último"), ("old", "new"), ("antiguos", "nuevos"),
       ("viejos", "nuevos"), ("duplicados", "únicos"), ("temporal", "permanente"), ("two", "three"), ("dos", "tres"), ("10", "1.0")]
def a_lex(t, r):
    c = [(a, b) for a, b in LEX if a in t]
    if not c: return None
    a, b = r.choice(c); return t.replace(a, b, 1)
def a_quantifier_add(t, r):
    return t.rstrip(".") + r.choice([", excepto los de 2025.", ", except the ones from 2025.", ", pero solo los de Colombia.", ", only for admins."])
CONJ = [(" y ", " o "), (" and ", " or "), (" e ", " ou "), (" o ", " y "), (" or ", " and ")]
_PT = ("ção", "relatório", " não ", " do ", " da ", " dos ", " das ", " pontos", "arquivos antigos")
def a_conj_swap(t, r):
    pt = any(m in t for m in _PT)                                # PT `o` is an article, not 'or': swapping it makes nonsense, not a meaning flip
    c = [(a, b) for a, b in CONJ if a in t and not (pt and a == " o ")]
    if not c: return None
    a, b = r.choice(c); return t.replace(a, b, 1)
QFLIP = [("al menos", "como máximo"), ("como máximo", "al menos"), ("at least", "at most"), ("at most", "at least"), ("más de", "menos de"),
         ("menos de", "más de"), ("more than", "fewer than"), ("less than", "more than"), ("all the", "none of the"), ("todos los", "ninguno de los"),
         ("todas las", "ninguna de las"), ("exactly", "about"), ("exactamente", "aproximadamente")]
def a_quant_flip(t, r):
    c = [(a, b) for a, b in QFLIP if a in t]
    if not c: return None
    a, b = r.choice(c); return t.replace(a, b, 1)
CFLIP = [(" if ", " unless "), (" si ", " a menos que "), (" when ", " unless "), (" cuando ", " excepto cuando "), (" unless ", " if "), (" only if ", " even if ")]
def a_cond_flip(t, r):
    c = [(a, b) for a, b in CFLIP if a in t]
    if not c: return None
    a, b = r.choice(c); return t.replace(a, b, 1)
def a_cond_drop(t, r):
    m = re.search(r"\s(if|si|when|cuando|unless)\s", t)
    return t[:m.start()] + "." if m else None
MFLIP = [("must", "may"), ("may", "must"), ("debes", "puedes"), ("puedes", "debes"), ("debe ", "puede "), ("should", "may"), ("deberías", "puedes")]
def a_modal_flip(t, r):
    c = [(a, b) for a, b in MFLIP if re.search(rf"\b{a.strip()}\b", t)]
    if not c: return None
    a, b = r.choice(c); return re.sub(rf"\b{a.strip()}\b", b.strip(), t, count=1)
def a_neg_scope(t, r):
    """Negate the SECOND conjunct only: 'Send A and delete B' -> 'Send A and do not delete B'."""
    for conj, neg in ((" and ", " and do not "), (" y ", " y no "), (" e ", " e não ")):
        if conj in t: return t.replace(conj, neg, 1)
    return None
def a_order_swap(t, r):
    """Reverse a sequence: 'X and then Y' -> 'Y and then X' (a conjunction without 'then' is commutative, a sequence is not)."""
    for sep in (" and then ", " y luego "):
        if sep in t:
            x, y = t.rstrip(".").split(sep, 1)
            return y[:1].upper() + y[1:] + sep + x[:1].lower() + x[1:] + "."
    return None
def a_compose(t, r):
    fns = [a_num, a_name, a_antonym, a_lex, a_add_constraint, a_neg_prefix]
    out = t
    for f in r.sample(fns, 2):
        o = f(out, r)
        if o: out = o
    return out if out != t else None
WORDNUM = {"1": "uno", "2": "dos", "3": "tres", "5": "cinco", "10": "diez", "20": "veinte"}
def a_nbsp(t, r): return t.replace(" ", "\u00a0")
def a_quotes(t, r): return r.choice(['"', "'", "“"]) + t + r.choice(['"', "'", "”"])
def a_please(t, r): return r.choice(["Por favor, ", "Please, ", "Por favor "]) + lc(t)
def a_tab_nl(t, r): return t.replace(" ", "\t", 1) + "\n"
def a_wordnum(t, r):
    for d, w in WORDNUM.items():
        if re.search(rf"\b{d}\b", t): return re.sub(rf"\b{d}\b", w, t, count=1)
    return None
def a_case(t, r): return t.upper() if r.random() < .5 else t.lower()
def a_space(t, r): return "  " + t.replace(" ", "   ") + " "
def a_punct(t, r): return t.rstrip(".") + r.choice(["", ".", "..", " ."])

NL_ATTACKERS = [("neg_prefix", "META", a_neg_prefix), ("neg_suffix", "META", a_neg_suffix), ("num_change", "META", a_num),
                ("name_swap", "META", a_name), ("antonym", "META", a_antonym), ("add_constraint", "META", a_add_constraint),
                ("drop_tail", "META", a_drop_tail), ("lex_swap", "META", a_lex), ("quantifier_add", "META", a_quantifier_add), ("conj_swap", "META", a_conj_swap), ("quant_flip", "META", a_quant_flip), ("cond_flip", "META", a_cond_flip), ("cond_drop", "META", a_cond_drop),
                ("modal_flip", "META", a_modal_flip), ("neg_scope", "META", a_neg_scope), ("order_swap", "META", a_order_swap), ("compose", "META", a_compose), ("case", "COSM", a_case), ("nbsp", "COSM", a_nbsp), ("quotes", "COSM", a_quotes), ("please", "COSM", a_please), ("tab_nl", "COSM", a_tab_nl), ("wordnum", "COSM", a_wordnum), ("space", "COSM", a_space), ("punct", "COSM", a_punct)]

WIRE_BASE = ["V:AIXL-0.3 I:REQUEST_ANALYSIS A:ANALYZE D:SALES T:Q1-2026",
             "V:AIXL-0.3 I:REQUEST_EXECUTION A:DELETE,SEND E:REPORT Y:@ANA N:NO_DELETE K:FORBID_DELETE,BIND=DELETE>REPORT",
             "V:AIXL-0.3 I:REQUEST_COMPARISON A:COMPARE E:DATASET#77,DATASET#81",
             "V:AIXL-0.3 I:REQUEST_TRANSLATION A:TRANSLATE E:DOCUMENT L:EN"]
HOMO = {"A": "А", "E": "Е", "O": "О", "S": "Ѕ", "T": "Т"}


def w_del(l, r):
    p = l.split(); 
    if len(p) < 2: return None
    p.pop(r.randrange(len(p))); return " ".join(p)
def w_dup(l, r):
    p = l.split(); i = r.randrange(len(p)); p.insert(i, p[i]); return " ".join(p)
def w_shuffle(l, r):
    p = l.split(); r.shuffle(p); return " ".join(p)
def w_homoglyph(l, r):
    i = [k for k, ch in enumerate(l) if ch in HOMO and k > 12]
    if not i: return None
    k = r.choice(i); return l[:k] + HOMO[l[k]] + l[k + 1:]
def w_empty_value(l, r):
    return re.sub(r"\b([ADENKTYL]):\S+", r"\1:", l, count=1)
def w_zero_width(l, r):
    k = r.randrange(len(l)); return l[:k] + "​" + l[k:]
def w_newline(l, r): return l.replace(" ", "\n", 1)
def w_long(l, r): return l + " " + ",".join(["X"] * r.choice([2000, 20000]))
def w_quote(l, r): return l + ' K:"unclosed'
def w_neg_orphan(l, r): return l + r.choice([" N:NO_PUBLISH", " K:FORBID_MERGE", " N:NO_ARCHIVE K:FORBID_ARCHIVE"])
def w_dup_field(l, r): return l + " A:DELETE"
def w_lower(l, r): return l.lower()
def w_version(l, r): return l.replace("AIXL-0.3", r.choice(["AIXL-0.30", "AIXL-1.0", "AIXL-0.3.1", "AIXL-"]))

WIRE_ATTACKERS = [("w_del", w_del), ("w_dup", w_dup), ("w_shuffle", w_shuffle), ("w_homoglyph", w_homoglyph),
                  ("w_empty_value", w_empty_value), ("w_zero_width", w_zero_width), ("w_newline", w_newline),
                  ("w_long", w_long), ("w_quote", w_quote), ("w_neg_orphan", w_neg_orphan), ("w_dup_field", w_dup_field),
                  ("w_lower", w_lower), ("w_version", w_version)]


# ---- oracles -----------------------------------------------------------------------------------------------------
class _Timeout(Exception): ...
def _alarm(sec):
    signal.signal(signal.SIGALRM, lambda *a: (_ for _ in ()).throw(_Timeout()))
    signal.alarm(sec)


def judge_meta(orig: str, mut: str) -> str | None:
    """Return a defect code or None. Mutation changed meaning, so EQUIVALENT / MATCH / a lossless gate are the unsafe answers.
    Layers attacked: the experimental comparator (aixl.semantic), the integrity envelope and the token gate (the layers that SHIP).
    The core comparator (aixl.compare) is deliberately NOT a defect source here: its closed-lexicon limits are known and are measured by `scope`."""
    from aixl.envelope import seal, verify
    from aixl.gate import translate_gated
    from aixl.semantic.compare import compare_texts
    try:
        v = compare_texts(orig, mut)
    except Exception as e:
        return f"META-CRASH:{type(e).__name__}"
    if v.verdict == "EQUIVALENT":
        return "META-FALSE-EQUIVALENT"
    try:
        from aixl.api.service import compare_verified
        if compare_verified(orig, mut)["equivalent"]:               # the surface MCP/A2A clients actually receive
            return "META-VERIFIED-COMPARE-FALSE-EQUIVALENT"
    except Exception as e:
        return f"META-VERIFIED-CRASH:{type(e).__name__}"
    try:
        if verify(seal(orig), mut) == "MATCH":                     # envelope says the received text means what was sealed
            return "META-ENVELOPE-FALSE-MATCH"
    except Exception as e:
        return f"META-ENVELOPE-CRASH:{type(e).__name__}"
    try:
        g = translate_gated(mut)
        if g["mode"] == "AIXL":
            # AIXL claims a lossless compact form of `mut`: numbers and negation cues must still be in it.
            nums = re.findall(r"\d+", mut)
            if any(n not in g["output"] for n in nums): return "META-GATE-DROPPED-NUMBER"
            if re.search(r"\b(no|not|never|nunca|n[aã]o|sin|without)\b", mut, re.I) and not re.search(r"\b[NK]:", g["output"]):
                return "META-GATE-DROPPED-NEGATION"
            go = translate_gated(orig)
            if go["mode"] == "AIXL" and go["output"] == g["output"]:   # two different meanings compressed to the SAME AIXL
                return "META-GATE-COLLAPSE"
    except Exception as e:
        return f"META-GATE-CRASH:{type(e).__name__}"
    return None


def judge_cosm(orig: str, mut: str) -> str | None:
    from aixl.core.fingerprint import fingerprint_graph as fp
    from aixl.gate import translate_gated
    from aixl.translators.natural_to_semantic import to_graph
    try:
        if fp(to_graph(orig)) == fp(to_graph(mut)): return None
        # translator-level miss is CONTAINED if the gate refuses the mutant (NATURAL); only an uncontained one ships a lossy AIXL
        return "COSM-UNCONTAINED-LOSS" if translate_gated(mut)["mode"] == "AIXL" else None
    except Exception as e:
        return f"COSM-CRASH:{type(e).__name__}"


def judge_wire(orig: str, mut: str) -> str | None:
    from aixl.serialization.aixl_codec import AixlError, decode
    try:
        _alarm(3)
        try:
            decode(mut)
        finally:
            signal.alarm(0)
    except AixlError:
        return None
    except _Timeout:
        return "WIRE-HANG"
    except Exception as e:
        return f"WIRE-CRASH:{type(e).__name__}"
    # decoded OK: if the mutation inserted a prohibition, it must be visible in the decoded frame (no silent drop)
    m = re.search(r"\b([NK]):((?:NO|FORBID)_[A-Z_]+)", mut)
    if m and m.group(0) not in orig:
        try:
            f = decode(mut).to_frame()
            if m.group(2) not in list(f.negations) + list(f.constraints): return "WIRE-SILENT-DROP"
        except AixlError:
            return None
    return None


def judge(kind: str, orig: str, mut: str) -> str | None:
    return {"META": judge_meta, "COSM": judge_cosm, "WIRE": judge_wire}[kind](orig, mut)


# ---- minimizer (word-level ddmin, keeps the SAME defect code) ----------------------------------------------------
def minimize(kind, fn, base, aseed, code):
    """Shrink `base`; every candidate is re-attacked with the same operator+seed. Returns (min_base, min_mutant)."""
    toks = base.split(); n = 2
    def attempt(t):
        try: m = fn(t, random.Random(aseed))
        except Exception: return None
        return m if m and m != t and judge(kind, t, m) == code else None
    while len(toks) >= 2:
        chunk = max(1, len(toks) // n); done = False
        for i in range(0, len(toks), chunk):
            cand = toks[:i] + toks[i + chunk:]
            if cand and attempt(" ".join(cand)):
                toks, n, done = cand, max(n - 1, 2), True; break
        if not done:
            if chunk == 1: break
            n = min(len(toks), n * 2)
    b = " ".join(toks)
    return b, fn(b, random.Random(aseed))


# ---- learning loop ------------------------------------------------------------------------------------------------
def load_state():
    if STATE.exists(): return json.loads(STATE.read_text())
    return {"weights": {n: 1.0 for n, *_ in NL_ATTACKERS} | {n: 1.0 for n, _ in WIRE_ATTACKERS}, "rounds": 0, "hits": {}}


def load_corpus():
    return [json.loads(l) for l in CORPUS.read_text().splitlines() if l.strip()] if CORPUS.exists() else []


def sig(kind, code, text): return f"{kind}|{code}|{re.sub(r'[^a-z:_@#]', '', text.lower())[:60]}"


def run(rounds: int, seed: int, per_round: int = 60):
    rng = random.Random(seed); st = load_state(); corpus = load_corpus()
    seen = {c["sig"] for c in corpus}
    # evolution: previously failing minimized inputs become seeds for further mutation (attacks compound)
    nl_seeds = SEEDS + [c["minimized"] for c in corpus if c["kind"] in ("META", "COSM")][:40]
    wire_seeds = WIRE_BASE + [c["minimized"] for c in corpus if c["kind"] == "WIRE"][:20]
    new = []
    for _ in range(rounds):
        names = list(st["weights"]); ws = [st["weights"][n] for n in names]
        for _ in range(per_round):
            op = rng.choices(names, ws)[0]
            if op.startswith("w_"):
                fn = dict(WIRE_ATTACKERS)[op]; base = rng.choice(wire_seeds); kind = "WIRE"
            else:
                _, kind, fn = next(a for a in NL_ATTACKERS if a[0] == op); base = rng.choice(nl_seeds)
            aseed = rng.randrange(1 << 30)
            try: mut = fn(base, random.Random(aseed))
            except Exception: mut = None
            if not mut or mut == base: continue
            code = judge(kind, base, mut)
            if code is None:
                st["weights"][op] = max(0.2, st["weights"][op] * 0.995); continue
            mbase, mmut = minimize(kind, fn, base, aseed, code)
            s = sig(kind, code, mbase + "=>" + mmut)
            st["hits"][op] = st["hits"].get(op, 0) + 1
            if s in seen:
                st["weights"][op] = max(0.2, st["weights"][op] * 0.9); continue
            st["weights"][op] = min(8.0, st["weights"][op] * 1.5)
            seen.add(s)
            rec = dict(sig=s, kind=kind, code=code, op=op, original=mbase, mutated=mmut, minimized=mbase, ts=time.time())
            new.append(rec)
            with CORPUS.open("a") as f: f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        st["rounds"] += 1
    STATE.write_text(json.dumps(st, indent=1))
    return new


# every defect code the CURRENT oracles can emit; a stored record with any other code was written by an older oracle
EMITTED = {"META-FALSE-EQUIVALENT", "META-VERIFIED-COMPARE-FALSE-EQUIVALENT", "META-ENVELOPE-FALSE-MATCH", "META-GATE-DROPPED-NUMBER", "META-GATE-DROPPED-NEGATION",
           "META-GATE-COLLAPSE", "COSM-UNCONTAINED-LOSS", "WIRE-HANG", "WIRE-SILENT-DROP"}


def _status(c) -> str:
    code = judge(c["kind"], c["original"], c["mutated"])
    if code == c["code"]:
        return "STILL_FAILS"
    if c["code"] in EMITTED or c["code"].split(":")[0] in {"META-CRASH", "META-VERIFIED-CRASH", "META-ENVELOPE-CRASH", "META-GATE-CRASH", "COSM-CRASH", "WIRE-CRASH"}:
        return "FIXED" if code is None else f"CHANGED->{code}"
    # stored code is not one the oracle emits any more (older oracle): do NOT claim it was fixed
    if c["kind"] == "COSM":
        from aixl.core.fingerprint import fingerprint_graph as fp
        from aixl.translators.natural_to_semantic import to_graph
        if fp(to_graph(c["original"])) == fp(to_graph(c["mutated"])):
            return "FIXED"
        return "CONTAINED" if code is None else f"CHANGED->{code}"       # translator still differs; gate falls back to NATURAL
    return "RECLASSIFIED" if code is None else f"CHANGED->{code}"


def replay():
    return [(c["sig"], c["code"], _status(c)) for c in load_corpus()]


def selftest() -> list:
    """An arena that cannot catch a planted bug proves nothing. Plant 3 bugs, require each to be flagged."""
    import importlib

    import aixl.gate as G
    import aixl.serialization.aixl_codec as K
    importlib.import_module("aixl.semantic.compare")
    cmp_mod = sys.modules["aixl.semantic.compare"]
    res = []
    class V: verdict, diffs, unresolved = "EQUIVALENT", [], []
    o = cmp_mod.compare_texts; cmp_mod.compare_texts = lambda a, b: V()
    try: res.append(("comparator says EQUIVALENT to everything", judge_meta("Borra el archivo.", "Nunca borres el archivo.") == "META-FALSE-EQUIVALENT"))
    finally: cmp_mod.compare_texts = o
    oc = K._check; K._check = lambda f, s: None
    try: res.append(("decoder silently drops orphan prohibition", judge_wire("", "V:AIXL-0.3 I:REQUEST_ANALYSIS A:ANALYZE D:SALES N:NO_PUBLISH") == "WIRE-SILENT-DROP"))
    finally: K._check = oc
    og = G.translate_gated
    G.translate_gated = lambda t: {"mode": "AIXL", "output": "A:ANALYZE D:SALES"}
    try: res.append(("gate ships AIXL that dropped the number", judge_meta("Analiza 5 ventas.", "Analiza 6 ventas.") == "META-GATE-DROPPED-NUMBER"))
    finally: G.translate_gated = og
    import aixl.api.service as SV
    ocv = SV.compare_verified; SV.compare_verified = lambda a, b, c=None: {"equivalent": True}
    try: res.append(("published compare says EQUIVALENT to a meaning change", judge_meta("Borra el archivo.", "Nunca borres el archivo.") == "META-VERIFIED-COMPARE-FALSE-EQUIVALENT"))
    finally: SV.compare_verified = ocv
    import aixl.envelope as EV
    ov = EV.verify; EV.verify = lambda env, t: "MATCH"
    try: res.append(("envelope MATCHes a meaning change", judge_meta("Borra el archivo.", "Nunca borres el archivo.") == "META-ENVELOPE-FALSE-MATCH"))
    finally: EV.verify = ov
    G.translate_gated = lambda t: {"mode": "AIXL", "output": "A:DELETE E:FILE"}
    try: res.append(("gate compresses two different meanings to the same AIXL", judge_meta("Borra el archivo.", "Crea el archivo.") == "META-GATE-COLLAPSE"))
    finally: G.translate_gated = og
    return res


def other_author_seeds() -> list[tuple[str, str]]:
    """(author, text) written by Opus/Sonnet/Haiku sub-agents that never saw the arena or the lexicons (data/arena/other_author_seeds.jsonl)."""
    import os
    f = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "arena", "other_author_seeds.jsonl")
    return [(r["author"], r["text"]) for r in map(json.loads, open(f, encoding="utf-8")) if r.get("text")]


def scope(seed: int = 7, reps: int = 5, seeds=None) -> dict:
    """Fixed-seed sweep of every META attacker against EVERY layer, one verdict per layer. Writes nothing.
    `core_compare_equivalent` is a KNOWN LIMIT of the closed lexicons (the core comparator is not what protects a message in production: the envelope and
    the gate abstain instead). The other counters are defects when non-zero."""
    import collections

    import aixl
    from aixl.envelope import seal, verify
    from aixl.gate import translate_gated
    from aixl.semantic.compare import compare_texts
    rng, c, known = random.Random(seed), collections.Counter(), []
    for name, kind, fn in NL_ATTACKERS:
        if kind != "META":
            continue
        for base in (seeds or SEEDS):
            for _ in range(reps):
                try: m = fn(base, random.Random(rng.randrange(1 << 30)))
                except Exception: m = None
                if not m or m == base:
                    continue
                c["mutants"] += 1
                if compare_texts(base, m).verdict == "EQUIVALENT": c["semantic_equivalent"] += 1
                if aixl.compare(base, m).equivalent:
                    c["core_compare_equivalent"] += 1; known.append((name, base, m))
                from aixl.api.service import compare_verified
                cv = compare_verified(base, m)
                if cv["equivalent"]:
                    c["verified_compare_equivalent"] += 1
                c["decided"] += bool(cv.get("complete"))             # both texts completely accounted for: the layers made a real decision
                c["family_n:" + name] += 1
                c["family_decided:" + name] += bool(cv.get("complete"))
                v = verify(seal(base), m); c["envelope_" + v] += 1
                g = translate_gated(m); c["gate_" + g["mode"]] += 1
                if g["mode"] == "AIXL":
                    go = translate_gated(base)
                    if go["mode"] == "AIXL" and go["output"] == g["output"]: c["gate_collapse"] += 1
    return {"counts": dict(c), "known_limits": known}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["run", "replay", "selftest", "scope"]); ap.add_argument("--other", action="store_true", help="scope over the other-author seeds only")
    ap.add_argument("--rounds", type=int, default=20); ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    if a.cmd == "run":
        new = run(a.rounds, a.seed)
        print(f"new distinct defects: {len(new)}")
        for r in new: print(f"  [{r['code']}] via {r['op']}: {r['original']!r} -> {r['mutated']!r}")
        st = load_state(); print("weights:", {k: round(v, 2) for k, v in sorted(st['weights'].items(), key=lambda x: -x[1])[:6]})
    elif a.cmd == "scope":
        r = scope(seeds=[t for _a, t in other_author_seeds()] if a.other else None); k = r["counts"]
        print(f"mutants (meaning-changing, fixed seed): {k.get('mutants', 0)}")
        print(f"  semantic comparator EQUIVALENT      : {k.get('semantic_equivalent', 0)}   (defect if > 0)")
        print(f"  published compare (verified) EQUIV  : {k.get('verified_compare_equivalent', 0)}   (defect if > 0)")
        print(f"  integrity envelope MATCH            : {k.get('envelope_MATCH', 0)}   (defect if > 0; MISMATCH {k.get('envelope_MISMATCH', 0)}, UNVERIFIED {k.get('envelope_UNVERIFIED', 0)})")
        print(f"  gate AIXL (lossy or collapsed)      : {k.get('gate_AIXL', 0)} AIXL / {k.get('gate_NATURAL', 0)} NATURAL, collapse {k.get('gate_collapse', 0)}")
        print(f"  core comparator EQUIVALENT (known)  : {k.get('core_compare_equivalent', 0)}   (documented limit, not a defect)")
        n = k.get("mutants", 0); d = k.get("decided", 0)
        print(f"  DECIDED (both texts complete)       : {d} of {n} ({100*d/max(n,1):.0f}%)  -> a zero above is only meaningful over these; the rest the layers ABSTAINED on")
        never = sorted(f.split(":", 1)[1] for f in k if f.startswith("family_n:") and k.get("family_decided:" + f.split(":", 1)[1], 0) == 0)
        print(f"  families with 0 decided (verification vacuous there): {never or 'none'}")
        for n, b0, m in r["known_limits"][:30]: print(f"      [{n}] {b0!r} -> {m!r}")
        sys.exit(1 if k.get("semantic_equivalent") or k.get("verified_compare_equivalent") or k.get("envelope_MATCH") or k.get("gate_collapse") else 0)
    elif a.cmd == "selftest":
        r = selftest()
        for n, ok in r: print("CAUGHT" if ok else "MISSED", "-", n)
        sys.exit(0 if all(ok for _, ok in r) else 1)
    else:
        for s, c, status in replay(): print(status, c, s)
