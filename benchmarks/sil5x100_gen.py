"""Master prompt §42 benchmark: 5 classes x 100 (EQUIVALENT, NOT_EQUIVALENT, PARTIALLY_EQUIVALENT, AMBIGUOUS,
CONTRADICTORY), ES/EN/PT. Reproducible: `python -m benchmarks.sil5x100_gen` (seed fixed) rewrites the JSONL.

Ground truth is BY CONSTRUCTION (slot-level generation), never taken from the system under test, and the
vocabulary is written from the master prompt's own examples + common words WITHOUT consulting the system's
lexicon (so failures measure real coverage). Label definitions (declared before running):
  EQUIVALENT          same slots, different language / synonym / word order
  NOT_EQUIVALENT      exactly one slot value CHANGED (action, object, target, time, format, quantity); no negation flip
  PARTIALLY_EQUIVALENT B = A plus one extra slot (A's meaning is a strict subset of B's); nothing changed or removed
  AMBIGUOUS           one text whose action cannot be resolved without context (bare pronoun / vague referent)
  CONTRADICTORY       pair that cannot both be obeyed: do/don't, enable/disable, allow/forbid, before/after
v1.1 (2026-10-02): dropped "Forward" as a synonym of "Send" (not a strict synonym -> 8 doubtful EQUIVALENT labels
found after the first run; v1 scored 447/500 = 89.4%). Labels are otherwise unchanged.
Note (§65 overlap): a pure negation flip is labelled CONTRADICTORY here, not NOT_EQUIVALENT."""
import json, os, random, itertools

SEED = 20261002
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "sil5x100")

# action key -> per-language list of imperative verb forms (first = canonical, others = synonyms)
V = {
 "send": {"es": ["Envía", "Manda"], "en": ["Send"], "pt": ["Envie", "Mande"]},
 "analyze": {"es": ["Analiza", "Examina"], "en": ["Analyze", "Examine"], "pt": ["Analise", "Examine"]},
 "translate": {"es": ["Traduce"], "en": ["Translate"], "pt": ["Traduza"]},
 "summarize": {"es": ["Resume"], "en": ["Summarize"], "pt": ["Resuma"]},
 "delete": {"es": ["Elimina", "Borra"], "en": ["Delete", "Remove"], "pt": ["Elimine", "Apague"]},
 "generate": {"es": ["Genera", "Crea"], "en": ["Generate", "Create"], "pt": ["Gere", "Crie"]},
}
VNEG = {"es": "No {v_neg}", "en": "Do not {v_inf}", "pt": "Não {v_neg}"}
# negated imperative forms
NEG = {
 "send": {"es": "No envíes", "en": "Do not send", "pt": "Não envie"},
 "analyze": {"es": "No analices", "en": "Do not analyze", "pt": "Não analise"},
 "translate": {"es": "No traduzcas", "en": "Do not translate", "pt": "Não traduza"},
 "summarize": {"es": "No resumas", "en": "Do not summarize", "pt": "Não resuma"},
 "delete": {"es": "No elimines", "en": "Do not delete", "pt": "Não elimine"},
 "generate": {"es": "No generes", "en": "Do not generate", "pt": "Não gere"},
}
# object key -> lang -> (with article)
O = {
 "report": {"es": "el informe", "en": "the report", "pt": "o relatório"},
 "document": {"es": "el documento", "en": "the document", "pt": "o documento"},
 "dataset": {"es": "el dataset", "en": "the dataset", "pt": "o dataset"},
 "sales": {"es": "las ventas", "en": "the sales", "pt": "as vendas"},
 "invoice": {"es": "la factura", "en": "the invoice", "pt": "a fatura"},
}
TGT = {"es": "a {n}", "en": "to {n}", "pt": "para {n}"}
NAMES = ["Ana", "Carlos", "Marta", "Pedro", "Lucía", "Beto"]
TIME = {"tomorrow": {"es": "mañana", "en": "tomorrow", "pt": "amanhã"},
        "today": {"es": "hoy", "en": "today", "pt": "hoje"},
        "yesterday": {"es": "ayer", "en": "yesterday", "pt": "ontem"}}
FMT = {"PDF": {"es": "en PDF", "en": "as a PDF", "pt": "em PDF"},
       "JSON": {"es": "en JSON", "en": "as JSON", "pt": "em JSON"},
       "CSV": {"es": "en CSV", "en": "as CSV", "pt": "em CSV"}}
LANGS = ["es", "en", "pt"]
SEND_LIKE = {"send"}
TGT_OK = {"send"}          # only 'send' takes a recipient


def render(lang, act, obj, tgt=None, time=None, fmt=None, vi=0, order=0, qty=None):
    verb = V[act][lang][vi % len(V[act][lang])]
    parts = [verb, O[obj][lang]]
    if tgt:
        parts.append(TGT[lang].format(n=tgt))
    if fmt:
        parts.append(FMT[fmt][lang])
    t = TIME[time][lang] if time else None
    if order == 0:
        if t:
            parts.append(t)
        s = " ".join(parts)
    else:                                   # time-first word order
        s = (t.capitalize() + ", " + verb[0].lower() + verb[1:] + " " + " ".join(parts[1:])) if t else " ".join(parts)
    return s.strip() + "."


def slots(rng, act=None):
    act = act or rng.choice(list(V))
    return dict(act=act, obj=rng.choice(list(O)), tgt=rng.choice(NAMES) if act in TGT_OK else None,
                time=rng.choice(list(TIME)), fmt=None)


def mk(label, kind, a, b=None, **meta):
    d = dict(label=label, kind=kind, a=a)
    if b is not None:
        d["b"] = b
    d.update(meta)
    return d


def gen_equivalent(rng):
    out, seen = [], set()
    while len(out) < 100:
        s = slots(rng)
        if rng.random() < 0.5:
            s["fmt"] = rng.choice(list(FMT))
        l1, l2 = rng.sample(LANGS, 2) if rng.random() < 0.8 else (rng.choice(LANGS),) * 2
        a = render(l1, **s, vi=0, order=0)
        b = render(l2, **s, vi=rng.randint(0, 1), order=rng.randint(0, 1))
        if a == b or (a, b) in seen:
            continue
        seen.add((a, b))
        out.append(mk("EQUIVALENT", "paraphrase" if l1 == l2 else "cross-lingual", a, b, langs=[l1, l2]))
    return out


def gen_not_equivalent(rng):
    out, seen = [], set()
    changes = ["action", "object", "target", "time", "format"]
    while len(out) < 100:
        s = slots(rng)
        ch = rng.choice(changes)
        if ch == "target" and s["tgt"] is None:
            s = slots(rng, "send")
        if ch == "format":
            s["fmt"] = rng.choice(list(FMT))
        s2 = dict(s)
        if ch == "action":
            s2["act"] = rng.choice([x for x in V if x != s["act"]])
            s2["tgt"] = rng.choice(NAMES) if s2["act"] in TGT_OK else None
            if s["tgt"] and s2["tgt"]:
                s2["tgt"] = s["tgt"]
        elif ch == "object":
            s2["obj"] = rng.choice([x for x in O if x != s["obj"]])
        elif ch == "target":
            s2["tgt"] = rng.choice([x for x in NAMES if x != s["tgt"]])
        elif ch == "time":
            s2["time"] = rng.choice([x for x in TIME if x != s["time"]])
        else:
            s2["fmt"] = rng.choice([x for x in FMT if x != s["fmt"]])
        l1, l2 = rng.sample(LANGS, 2) if rng.random() < 0.6 else (rng.choice(LANGS),) * 2
        a, b = render(l1, **s), render(l2, **s2)
        if (a, b) in seen:
            continue
        seen.add((a, b))
        out.append(mk("NOT_EQUIVALENT", "slot-changed:" + ch, a, b, langs=[l1, l2]))
    return out


def gen_partial(rng):
    out, seen = [], set()
    while len(out) < 100:
        s = slots(rng)
        extra = rng.choice(["format", "time", "target"])
        if extra == "target":
            s = slots(rng, "send")
        base = dict(s)
        if extra == "format":
            full = dict(s, fmt=rng.choice(list(FMT)))
        elif extra == "time":
            base["time"] = None
            full = dict(s)
        else:
            base["tgt"] = None
            full = dict(s)
        l1, l2 = rng.sample(LANGS, 2) if rng.random() < 0.6 else (rng.choice(LANGS),) * 2
        a, b = render(l1, **base), render(l2, **full)
        if rng.random() < 0.5:
            a, b = b, a                                   # either direction of subset
        if (a, b) in seen:
            continue
        seen.add((a, b))
        out.append(mk("PARTIALLY_EQUIVALENT", "extra-slot:" + extra, a, b, langs=[l1, l2]))
    return out


AMB_T = {   # bare-pronoun / vague-referent commands (no antecedent anywhere in the text)
 "es": ["{V} eso.", "{V}lo.", "{V} aquello.", "{V} todo.", "{V} ambos.", "{V} los otros.", "{V} el archivo viejo.", "{V} esto a él."],
 "en": ["{V} it.", "{V} that.", "{V} those.", "{V} everything.", "{V} both.", "{V} the other ones.", "{V} it to him.", "{V} this."],
 "pt": ["{V} isso.", "{V} aquilo.", "{V} tudo.", "{V} ambos.", "{V} os outros.", "{V} isto para ele.", "{V} aquele."],
}


def gen_ambiguous(rng):
    pool = []
    for act in V:
        for lang in LANGS:
            for t in AMB_T[lang]:
                v = V[act][lang][0]
                if "{V}lo" in t:
                    v = v.rstrip("s") if False else v
                pool.append((lang, act, t.format(V=v)))
    rng.shuffle(pool)
    out, seen = [], set()
    for lang, act, text in pool:
        if text in seen:
            continue
        seen.add(text)
        out.append(mk("AMBIGUOUS", "vague-referent", text, langs=[lang]))
        if len(out) == 100:
            break
    return out


def gen_contradictory(rng):
    out, seen = [], set()
    kinds = ["negation"] * 5 + ["enable"] + ["allow"] + ["time"]
    while len(out) < 100:
        k = rng.choice(kinds)
        l1, l2 = rng.sample(LANGS, 2) if rng.random() < 0.6 else (rng.choice(LANGS),) * 2
        if k == "negation":
            s = slots(rng)
            a = render(l1, **s)
            act = s["act"]
            rest = a.split(" ", 1)[1]
            b = NEG[act][l2] + " " + render(l2, **s).split(" ", 1)[1]
        elif k == "enable":
            obj = rng.choice(["alert", "report", "dashboard"])
            T = {"alert": {"es": "la alerta", "en": "the alert", "pt": "o alerta"},
                 "report": {"es": "el reporte", "en": "the report", "pt": "o relatório"},
                 "dashboard": {"es": "el panel", "en": "the dashboard", "pt": "o painel"}}
            on = {"es": "Activa", "en": "Enable", "pt": "Ative"}
            off = {"es": "Desactiva", "en": "Disable", "pt": "Desative"}
            a, b = f"{on[l1]} {T[obj][l1]}.", f"{off[l2]} {T[obj][l2]}."
        elif k == "allow":
            obj = rng.choice(list(O))
            al = {"es": "Permite eliminar", "en": "Allow deleting", "pt": "Permita eliminar"}
            fb = {"es": "Prohíbe eliminar", "en": "Forbid deleting", "pt": "Proíba eliminar"}
            a, b = f"{al[l1]} {O[obj][l1]}.", f"{fb[l2]} {O[obj][l2]}."
        else:
            s = slots(rng); s["time"] = None
            d = rng.choice(["2026-03-15", "2026-06-01", "2026-12-31"])
            bf = {"es": "antes de", "en": "before", "pt": "antes de"}
            af = {"es": "después de", "en": "after", "pt": "depois de"}
            a = f"{V['analyze'][l1][0]} {O[s['obj']][l1]} {bf[l1]} {d}."
            b = f"{V['analyze'][l2][0]} {O[s['obj']][l2]} {af[l2]} {d}."
        if (a, b) in seen:
            continue
        seen.add((a, b))
        out.append(mk("CONTRADICTORY", "contra:" + k, a, b, langs=[l1, l2]))
    return out


def build():
    rng = random.Random(SEED)
    return {"EQUIVALENT": gen_equivalent(rng), "NOT_EQUIVALENT": gen_not_equivalent(rng),
            "PARTIALLY_EQUIVALENT": gen_partial(rng), "AMBIGUOUS": gen_ambiguous(rng), "CONTRADICTORY": gen_contradictory(rng)}


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    ds = build()
    for lab, rows in ds.items():
        assert len(rows) == 100, (lab, len(rows))
        with open(os.path.join(OUT, lab + ".jsonl"), "w", encoding="utf-8") as fh:
            for i, r in enumerate(rows):
                fh.write(json.dumps({"id": f"{lab[:3]}-{i:03d}", **r}, ensure_ascii=False) + "\n")
    print("wrote", {k: len(v) for k, v in ds.items()})
