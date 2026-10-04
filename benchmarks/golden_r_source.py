"""AIXL 0.3-R golden dataset — SOURCE OF TRUTH (hand-authored). Run `python -m benchmarks.golden_r_source` to (re)emit
data/golden_r/texts.jsonl, pairs.jsonl and MANIFEST.json (sha256).

Design (master prompt §29-30):
  * texts.jsonl : one record per distinct text -> id, language, source_text, canonical_meaning, expected_semantic_graph,
                  ambiguities, forbidden_inferences
  * pairs.jsonl : one record per comparison -> expected_equivalence (EQUIVALENT | NOT_EQUIVALENT | UNDECIDABLE),
                  expected_diff, category, notes
  * UNDECIDABLE = the two texts cannot be proven equal or different from the text alone; the only SAFE system answer
    is INCONCLUSIVE/UNREPRESENTABLE. Answering EQUIVALENT there counts as a false-equivalent.
Labels are AUTHOR-ASSIGNED (review_status = "author-assigned"); contested ones are listed in data/golden_r/REVIEW.md.
This set is DEVELOPMENT data: the author (Claude) wrote it while knowing the system, so it is NOT an independent
benchmark. Independent evidence needs a separately-authored frozen blind set (see README in data/golden_r/).
"""
import hashlib
import json
import os

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "golden_r")

# canonical_meaning slot vocabulary (see data/golden_r/README.md). Value "UNSPECIFIED" = the text does not say.
SLOTS = {"action", "polarity", "object", "actor", "target", "recipient", "qty", "time", "cond", "exception",
         "sequence", "ref", "scope", "unspecified", "modality", "format", "language", "audience", "length", "source"}
DIFF_TYPES = {"LOSS", "DISTORTION", "ADDITION", "SUBSTITUTION", "CONTRADICTION"}
SEVERITY = {"MINOR", "MODERATE", "MAJOR", "CRITICAL"}
EQ = {"EQUIVALENT", "NOT_EQUIVALENT", "UNDECIDABLE"}
CATS = {"A_negation": "A", "B_quantity": "B", "C_time": "C", "D_condition": "D", "E_scope_exception": "E",
        "F_reference": "F", "H_composition": "H", "I_ambiguity": "I", "J_injection": "J", "K_paraphrase_multilingual": "K"}

TEXTS = {}   # source_text -> dict
PAIRS = []


def M(**kw):
    bad = set(kw) - SLOTS
    assert not bad, bad
    return kw


def d(path, typ, a, b, sev):
    assert typ in DIFF_TYPES and sev in SEVERITY
    return dict(semantic_path=path, original=a, new=b, difference_type=typ, severity=sev)


def T(text, lang, meaning, amb=None, forbid=None):
    rec = dict(source_text=text, language=lang, canonical_meaning=meaning, ambiguities=amb or [], forbidden_inferences=forbid or [])
    if text in TEXTS:
        assert TEXTS[text]["canonical_meaning"] == meaning, f"inconsistent meaning for {text!r}"
        rec["ambiguities"] = TEXTS[text]["ambiguities"] or rec["ambiguities"]
        rec["forbidden_inferences"] = sorted(set(TEXTS[text]["forbidden_inferences"]) | set(rec["forbidden_inferences"]))
    TEXTS[text] = rec
    return text


def P(cat, a, b, eq, diff=None, notes=""):
    assert cat in CATS and eq in EQ
    assert a in TEXTS and b in TEXTS
    assert (eq != "NOT_EQUIVALENT") or diff, "NOT_EQUIVALENT needs expected_diff"
    assert (eq == "NOT_EQUIVALENT") or not diff, "only NOT_EQUIVALENT carries expected_diff"
    PAIRS.append(dict(category=cat, text_a=a, text_b=b, expected_equivalence=eq, expected_diff=diff or [], notes=notes))


FINF_REPORT = ["audience", "length", "format", "language", "recipient"]


# ----------------------------------------------------------------------------------------------------------- A negation
a1 = T("Usa fuentes oficiales.", "es", M(action="use", polarity="oblige", object="official_sources"))
a2 = T("No uses fuentes oficiales.", "es", M(action="use", polarity="forbid", object="official_sources"))
P("A_negation", a1, a2, "NOT_EQUIVALENT", [d("polarity", "DISTORTION", "oblige", "forbid", "CRITICAL")])

b1 = T("No uses fuentes secundarias.", "es", M(action="use", polarity="forbid", object="secondary_sources"))
b2 = T("Nunca uses fuentes secundarias.", "es", M(action="use", polarity="forbid", object="secondary_sources"))
P("A_negation", b1, b2, "EQUIVALENT", notes="'nunca' in an imperative adds no new constraint")
b3 = T("Evita las fuentes secundarias.", "es", M(action="use", polarity="UNSPECIFIED", object="secondary_sources"),
       amb=["'evitar' can be a hard prohibition or a discouragement"])
P("A_negation", b1, b3, "UNDECIDABLE", notes="prohibition vs discouragement; found as a silent-failure class in blind tests")

c1 = T("No es cierto que no debas enviar el informe.", "es", M(action="send", polarity="oblige", object="report"))
c2 = T("Debes enviar el informe.", "es", M(action="send", polarity="oblige", object="report"))
P("A_negation", c1, c2, "EQUIVALENT", notes="double negation")

e1 = T("No envíes ni el informe ni la factura.", "es", M(action="send", polarity="forbid", object=["report", "invoice"]))
e2 = T("No envíes el informe, pero sí la factura.", "es",
       M(action="send", polarity="forbid", object="report", exception=dict(polarity="oblige", object="invoice")))
P("A_negation", e1, e2, "NOT_EQUIVALENT", [d("object[invoice].polarity", "DISTORTION", "forbid", "oblige", "CRITICAL")])

f1 = T("No borres todos los archivos.", "es", M(action="delete", polarity="forbid", object="files", qty=dict(mode="all")),
       amb=["'not all' (some may be deleted) vs 'none'"])
f2 = T("No borres ningún archivo.", "es", M(action="delete", polarity="forbid", object="files", qty=dict(mode="none")))
P("A_negation", f1, f2, "UNDECIDABLE", notes="partial vs total negation; Spanish 'no ... todos' is genuinely ambiguous")

g1 = T("Don't send the report to anyone.", "en", M(action="send", polarity="forbid", object="report", recipient=dict(mode="any")))
g2 = T("Send the report to no one.", "en", M(action="send", polarity="forbid", object="report", recipient=dict(mode="any")))
P("A_negation", g1, g2, "EQUIVALENT")

# ----------------------------------------------------------------------------------------------------------- B quantity
q = lambda mode, v=None, u="files": dict(mode=mode, value=v, unit=u)
t1 = T("Selecciona exactamente 10 archivos.", "es", M(action="select", object="files", qty=q("exact", 10)))
t2 = T("Selecciona máximo 10 archivos.", "es", M(action="select", object="files", qty=q("at_most", 10)))
t3 = T("Selecciona mínimo 10 archivos.", "es", M(action="select", object="files", qty=q("at_least", 10)))
t4 = T("Selecciona aproximadamente 10 archivos.", "es", M(action="select", object="files", qty=q("approx", 10)))
P("B_quantity", t1, t2, "NOT_EQUIVALENT", [d("qty.mode", "DISTORTION", "exact", "at_most", "MAJOR")])
P("B_quantity", t2, t3, "NOT_EQUIVALENT", [d("qty.mode", "DISTORTION", "at_most", "at_least", "CRITICAL")])
P("B_quantity", t1, t4, "NOT_EQUIVALENT", [d("qty.mode", "DISTORTION", "exact", "approx", "MAJOR")])

r1 = T("Selecciona entre 10 y 20 archivos.", "es", M(action="select", object="files", qty=dict(mode="range", min=10, max=20, unit="files")))
r2 = T("Selecciona al menos 10 y como mucho 20 archivos.", "es", M(action="select", object="files", qty=dict(mode="range", min=10, max=20, unit="files")))
P("B_quantity", r1, r2, "EQUIVALENT")

m1 = T("Selecciona más de 10 archivos.", "es", M(action="select", object="files", qty=q("greater_than", 10)))
m2 = T("Selecciona al menos 10 archivos.", "es", M(action="select", object="files", qty=q("at_least", 10)))
P("B_quantity", m1, m2, "NOT_EQUIVALENT", [d("qty.mode", "DISTORTION", "greater_than", "at_least", "MODERATE")])

s1 = T("Resume el informe en 200 palabras.", "es", M(action="summarize", object="report", length=dict(mode="exact", value=200, unit="words")),
       forbid=["audience", "format", "language"])
s2 = T("Resume el informe en 200 caracteres.", "es", M(action="summarize", object="report", length=dict(mode="exact", value=200, unit="characters")))
s3 = T("Resume el informe en doscientas palabras.", "es", M(action="summarize", object="report", length=dict(mode="exact", value=200, unit="words")))
P("B_quantity", s1, s2, "NOT_EQUIVALENT", [d("length.unit", "SUBSTITUTION", "words", "characters", "MAJOR")])
P("B_quantity", s1, s3, "EQUIVALENT", notes="digits vs number words")

n1 = T("Elimina todos los duplicados.", "es", M(action="delete", object="duplicates", qty=dict(mode="all")))
n2 = T("Elimina algunos duplicados.", "es", M(action="delete", object="duplicates", qty=dict(mode="some")))
P("B_quantity", n1, n2, "NOT_EQUIVALENT", [d("qty.mode", "DISTORTION", "all", "some", "CRITICAL")])

# ----------------------------------------------------------------------------------------------------------- C time
v1 = T("Envía el informe antes del viernes.", "es", M(action="send", object="report", time=dict(rel="before", value="friday")))
v2 = T("Envía el informe el viernes.", "es", M(action="send", object="report", time=dict(rel="at", value="friday")))
v3 = T("Envía el informe después del viernes.", "es", M(action="send", object="report", time=dict(rel="after", value="friday")))
v4 = T("Envía el informe antes de que llegue el viernes.", "es", M(action="send", object="report", time=dict(rel="before", value="friday")))
v5 = T("Envía el informe hasta el viernes.", "es", M(action="send", object="report", time=dict(rel="until_inclusive", value="friday")))
P("C_time", v1, v2, "NOT_EQUIVALENT", [d("time.rel", "DISTORTION", "before", "at", "MAJOR")])
P("C_time", v3, v1, "NOT_EQUIVALENT", [d("time.rel", "DISTORTION", "after", "before", "CRITICAL")])
P("C_time", v1, v4, "EQUIVALENT")
P("C_time", v1, v5, "NOT_EQUIVALENT", [d("time.rel", "DISTORTION", "before", "until_inclusive", "MODERATE")],
  notes="'antes de' excludes Friday, 'hasta' includes it")

w1 = T("Envía el informe cada lunes.", "es", M(action="send", object="report", time=dict(rel="recurring", value="monday")))
w2 = T("Envía el informe el lunes.", "es", M(action="send", object="report", time=dict(rel="at", value="monday")))
P("C_time", w1, w2, "NOT_EQUIVALENT", [d("time.rel", "DISTORTION", "recurring", "at", "MAJOR")])

x1 = T("Entrega en 3 días.", "es", M(action="deliver", time=dict(rel="within", value=3, unit="days")),
       amb=["calendar days vs business days not stated"])
x2 = T("Entrega en 3 días hábiles.", "es", M(action="deliver", time=dict(rel="within", value=3, unit="business_days")))
P("C_time", x1, x2, "NOT_EQUIVALENT", [d("time.unit", "SUBSTITUTION", "days", "business_days", "MODERATE")])

# ----------------------------------------------------------------------------------------------------------- D condition
cond_empty = dict(subject="file", pred="is_empty", value=True)
k1 = T("Si el archivo está vacío, solicita otro.", "es", M(action="request_another_file", cond=cond_empty))
k2 = T("Solicita otro archivo.", "es", M(action="request_another_file", cond="UNSPECIFIED"))
k3 = T("Si el archivo no está vacío, solicita otro.", "es", M(action="request_another_file", cond=dict(subject="file", pred="is_empty", value=False)))
k4 = T("Solicita otro archivo si el archivo está vacío.", "es", M(action="request_another_file", cond=cond_empty))
P("D_condition", k1, k2, "NOT_EQUIVALENT", [d("cond", "LOSS", cond_empty, "UNSPECIFIED", "CRITICAL")])
P("D_condition", k1, k3, "NOT_EQUIVALENT", [d("cond.value", "DISTORTION", True, False, "CRITICAL")])
P("D_condition", k1, k4, "EQUIVALENT", notes="clause order only")

l1 = T("Si hay errores, avisa al equipo.", "es", M(action="notify", target="team", cond=dict(subject="errors", pred="exist", value=True)))
l2 = T("Avisa al equipo y revisa si hay errores.", "es", M(action=["notify", "check_errors"], target="team", cond="UNSPECIFIED"))
P("D_condition", l1, l2, "NOT_EQUIVALENT", [d("cond", "LOSS", "errors_exist", "UNSPECIFIED", "CRITICAL")])

o1 = T("Si llueve y hace frío, quédate en casa.", "es", M(action="stay_home", cond=dict(op="and", terms=["rain", "cold"])))
o2 = T("Si llueve o hace frío, quédate en casa.", "es", M(action="stay_home", cond=dict(op="or", terms=["rain", "cold"])))
P("D_condition", o1, o2, "NOT_EQUIVALENT", [d("cond.op", "DISTORTION", "and", "or", "MAJOR")])

u1 = T("Envía el informe a menos que esté incompleto.", "es", M(action="send", object="report", cond=dict(subject="report", pred="is_complete", value=True)))
u2 = T("Si el informe está completo, envíalo.", "es", M(action="send", object="report", cond=dict(subject="report", pred="is_complete", value=True)))
P("D_condition", u1, u2, "EQUIVALENT", notes="'unless' == 'if not'; both leave the incomplete case unspecified, which is the same gap")

# ----------------------------------------------------------------------------------------------------------- E scope / exception
docs = dict(mode="all")
ex_conf = dict(attr="classification", value="confidential")
x_a = T("Resume todos los documentos excepto los confidenciales.", "es", M(action="summarize", object="documents", qty=docs, exception=ex_conf))
x_b = T("Resume todos los documentos.", "es", M(action="summarize", object="documents", qty=docs, exception="NONE"))
x_c = T("Resume todos los documentos menos los confidenciales.", "es", M(action="summarize", object="documents", qty=docs, exception=ex_conf))
x_d = T("Resume solo los documentos no confidenciales.", "es", M(action="summarize", object="documents", qty=docs, exception=ex_conf))
P("E_scope_exception", x_a, x_b, "NOT_EQUIVALENT", [d("exception", "LOSS", ex_conf, "NONE", "CRITICAL")])
P("E_scope_exception", x_a, x_c, "EQUIVALENT")
P("E_scope_exception", x_a, x_d, "EQUIVALENT", notes="same resulting set")

y1 = T("Envía solo a Ana el informe.", "es", M(action="send", object="report", recipient=dict(only=["ana"])))
y2 = T("Envía el informe a Ana y a Luis.", "es", M(action="send", object="report", recipient=dict(only=None, list=["ana", "luis"])))
P("E_scope_exception", y1, y2, "NOT_EQUIVALENT", [d("recipient", "ADDITION", ["ana"], ["ana", "luis"], "CRITICAL")])

z1 = T("Revisa los contratos y los informes de 2024.", "es", M(action="review", object=["contracts", "reports"], scope="UNSPECIFIED"),
       amb=["'de 2024' may modify only 'informes' or both"])
z2 = T("Revisa los contratos de 2024 y los informes de 2024.", "es", M(action="review", object=["contracts", "reports"], scope=dict(year=2024, applies_to="both")))
P("E_scope_exception", z1, z2, "UNDECIDABLE", notes="modifier attachment ambiguity")

lg1 = T("Borra todos los logs excepto los de hoy.", "es", M(action="delete", object="logs", qty=docs, exception=dict(attr="date", value="today")))
lg2 = T("Borra los logs de hoy.", "es", M(action="delete", object="logs", scope=dict(date="today")))
P("E_scope_exception", lg1, lg2, "NOT_EQUIVALENT", [d("exception", "CONTRADICTION", "keep today's", "delete today's", "CRITICAL")])

# ----------------------------------------------------------------------------------------------------------- F reference
fa = T("Usa el segundo archivo.", "es", M(action="use", object="file", ref=dict(kind="ordinal", n=2)))
fb = T("Usa el primer archivo.", "es", M(action="use", object="file", ref=dict(kind="ordinal", n=1)))
P("F_reference", fa, fb, "NOT_EQUIVALENT", [d("ref.n", "SUBSTITUTION", 2, 1, "MAJOR")])

fc = T("Copia el segundo archivo sobre el primero.", "es", M(action="copy", source=dict(kind="ordinal", n=2), target=dict(kind="ordinal", n=1)))
fd = T("Copia el primer archivo sobre el segundo.", "es", M(action="copy", source=dict(kind="ordinal", n=1), target=dict(kind="ordinal", n=2)))
P("F_reference", fc, fd, "NOT_EQUIVALENT", [d("source", "SUBSTITUTION", 2, 1, "CRITICAL"), d("target", "SUBSTITUTION", 1, 2, "CRITICAL")])

fe = T("Compara el segundo archivo con el primero.", "es", M(action="compare", object=[dict(kind="ordinal", n=2), dict(kind="ordinal", n=1)]),
       amb=["whether argument order matters for a comparison is not stated"])
ff = T("Compara el primer archivo con el segundo.", "es", M(action="compare", object=[dict(kind="ordinal", n=1), dict(kind="ordinal", n=2)]),
       amb=["whether argument order matters for a comparison is not stated"])
P("F_reference", fe, ff, "UNDECIDABLE", notes="symmetric operation; order may or may not carry direction (a diff)")

fg = T("Bórralo.", "es", M(action="delete", object=dict(kind="pronoun", resolved=None)), amb=["referent of 'lo' is not in the text"],
       forbid=["any specific object"])
fh = T("Borra el informe.", "es", M(action="delete", object="report"))
P("F_reference", fg, fh, "UNDECIDABLE", notes="unresolved anaphora must stay AMBIGUOUS, never guessed")

fi = T("Usa el último documento.", "es", M(action="use", object="document", ref=dict(kind="recency", which="most_recent")),
       amb=["'último' could mean last in a list or most recent in time"])
fj = T("Usa el documento más reciente.", "es", M(action="use", object="document", ref=dict(kind="recency", which="most_recent")))
P("F_reference", fi, fj, "UNDECIDABLE", notes="'último' is a real ordering ambiguity; relabeled from EQUIVALENT while authoring")

fk = T("Abre el archivo y ciérralo.", "es", M(action=["open", "close"], object="file"))
fl = T("Abre el archivo y cierra el archivo.", "es", M(action=["open", "close"], object="file"))
P("F_reference", fk, fl, "EQUIVALENT", notes="anaphora resolvable inside the sentence")

fm = T("Envía el informe a Ana y a Marta; ella debe aprobarlo.", "es", M(action="send", object="report", recipient=["ana", "marta"], actor=dict(role="approver", who=None)),
       amb=["'ella' = Ana or Marta"])
fn = T("Envía el informe a Ana y a Marta; Marta debe aprobarlo.", "es", M(action="send", object="report", recipient=["ana", "marta"], actor=dict(role="approver", who="marta")))
P("F_reference", fm, fn, "UNDECIDABLE")

# ----------------------------------------------------------------------------------------------------------- H composition / sequence
h1 = T("Borra el caché y después reinicia el servidor.", "es", M(action=["clear_cache", "restart_server"], sequence="in_order"))
h2 = T("Reinicia el servidor y después borra el caché.", "es", M(action=["restart_server", "clear_cache"], sequence="in_order"))
P("H_composition", h1, h2, "NOT_EQUIVALENT", [d("sequence", "DISTORTION", "cache->restart", "restart->cache", "MAJOR")])

h3 = T("Primero borra el caché y luego reinicia.", "es", M(action=["clear_cache", "restart"], sequence="in_order"))
h4 = T("Antes de reiniciar, borra el caché.", "es", M(action=["clear_cache", "restart"], sequence="in_order"))
P("H_composition", h3, h4, "EQUIVALENT")

h5 = T("Lee el informe y el contrato.", "es", M(action="read", object=["report", "contract"], sequence="UNSPECIFIED"))
h6 = T("Lee el contrato y el informe.", "es", M(action="read", object=["report", "contract"], sequence="UNSPECIFIED"))
P("H_composition", h5, h6, "EQUIVALENT", notes="coordinated objects, no sequence stated")

h7 = T("Después de aprobar, publica.", "es", M(action=["approve", "publish"], sequence="in_order"))
h8 = T("Publica y aprueba.", "es", M(action=["publish", "approve"], sequence="UNSPECIFIED"))
P("H_composition", h7, h8, "NOT_EQUIVALENT", [d("sequence", "DISTORTION", "approve->publish", "publish,approve", "CRITICAL")])

h9 = T("Envía el correo después de revisar el adjunto.", "es", M(action=["review_attachment", "send_email"], sequence="in_order"))
h10 = T("Revisa el adjunto antes de enviar el correo.", "es", M(action=["review_attachment", "send_email"], sequence="in_order"))
P("H_composition", h9, h10, "EQUIVALENT")

h11 = T("Ejecuta las pruebas; si pasan, despliega.", "es",
        M(action=["run_tests", "deploy"], sequence="in_order", cond=dict(subject="tests", pred="pass", value=True, guards="deploy")))
h12 = T("Ejecuta las pruebas y despliega.", "es", M(action=["run_tests", "deploy"], sequence="in_order", cond="UNSPECIFIED"))
P("H_composition", h11, h12, "NOT_EQUIVALENT", [d("cond", "LOSS", "tests_pass guards deploy", "UNSPECIFIED", "CRITICAL")])

# ----------------------------------------------------------------------------------------------------------- I ambiguity
i1 = T("Envíalo mañana.", "es", M(action="send", object=dict(kind="pronoun", resolved=None), time=dict(rel="at", value="tomorrow")),
       amb=["referent of 'lo' not in text", "'mañana' is relative to an unknown reference date"],
       forbid=["any specific object", "any absolute date"])
i2 = T("Envíalo hoy.", "es", M(action="send", object=dict(kind="pronoun", resolved=None), time=dict(rel="at", value="today")),
       amb=["referent of 'lo' not in text"], forbid=["any specific object", "any absolute date"])
P("I_ambiguity", i1, i2, "NOT_EQUIVALENT", [d("time.value", "SUBSTITUTION", "tomorrow", "today", "MAJOR")])

i3 = T("Llámame pronto.", "es", M(action="call", time=dict(rel="soon", value="UNSPECIFIED")), amb=["'pronto' has no fixed duration"],
       forbid=["any numeric delay"])
i4 = T("Llámame en 5 minutos.", "es", M(action="call", time=dict(rel="within", value=5, unit="minutes")))
P("I_ambiguity", i3, i4, "NOT_EQUIVALENT", [d("time", "ADDITION", "UNSPECIFIED", "5 minutes", "MODERATE")])

i5 = T("Resume el informe.", "es", M(action="summarize", object="report", length="UNSPECIFIED", format="UNSPECIFIED", audience="UNSPECIFIED",
                                     language="UNSPECIFIED"), forbid=FINF_REPORT)
i6 = T("Resume el informe en un párrafo.", "es", M(action="summarize", object="report", length=dict(mode="exact", value=1, unit="paragraph")))
i7 = T("Resume el informe brevemente.", "es", M(action="summarize", object="report", length=dict(mode="short", value=None)))
P("I_ambiguity", i5, i6, "NOT_EQUIVALENT", [d("length", "ADDITION", "UNSPECIFIED", "1 paragraph", "MODERATE")])
P("I_ambiguity", i5, i7, "NOT_EQUIVALENT", [d("length", "ADDITION", "UNSPECIFIED", "short", "MINOR")])

i8 = T("Trae la cámara de la tienda roja.", "es", M(action="bring", object="camera", scope="UNSPECIFIED"),
       amb=["'roja' modifies the store or the camera"])
i9 = T("Trae la cámara roja de la tienda.", "es", M(action="bring", object=dict(item="camera", color="red"), source="store"))
P("I_ambiguity", i8, i9, "UNDECIDABLE")

P("I_ambiguity", i5, i5, "EQUIVALENT", notes="identical text: ambiguity must be preserved, not resolved; verdict EQUIVALENT")

# ----------------------------------------------------------------------------------------------------------- J semantic injection
j0 = T("Haz un resumen del informe.", "es", TEXTS["Resume el informe."]["canonical_meaning"], forbid=FINF_REPORT)
P("J_injection", i5, j0, "EQUIVALENT", notes="control: paraphrase with no added content")
inj = [
    ("Resume el informe para un público académico.", dict(audience="academic"), "audience", "MODERATE"),
    ("Resume el informe y bórralo.", dict(action=["summarize", "delete"]), "action", "CRITICAL"),
    ("Resume el informe en inglés.", dict(language="en"), "language", "MODERATE"),
    ("Resume el informe y envíalo a todos.", dict(action=["summarize", "send"], recipient="all"), "action", "CRITICAL"),
]
for txt, delta, path, sev in inj:
    mean = dict(TEXTS["Resume el informe."]["canonical_meaning"]); mean.update(delta)
    tt = T(txt, "es", mean)
    P("J_injection", i5, tt, "NOT_EQUIVALENT", [d(path, "ADDITION", "UNSPECIFIED", str(list(delta.values())[0]), sev)])
j5 = T("Traduce el texto.", "es", M(action="translate", object="text", language="UNSPECIFIED"), forbid=["language"])
j6 = T("Traduce el texto al inglés.", "es", M(action="translate", object="text", language="en"))
P("J_injection", j5, j6, "NOT_EQUIVALENT", [d("language", "ADDITION", "UNSPECIFIED", "en", "MODERATE")])
j7 = T("Lista los clientes.", "es", M(action="list", object="customers", scope="UNSPECIFIED"), forbid=["filter"])
j8 = T("Lista los clientes activos.", "es", M(action="list", object="customers", scope=dict(status="active")))
P("J_injection", j7, j8, "NOT_EQUIVALENT", [d("scope.status", "ADDITION", "UNSPECIFIED", "active", "MAJOR")])

# ----------------------------------------------------------------------------------------------------------- K paraphrase / multilingual
sendana = M(action="send", object="report", recipient="ana", time=dict(rel="before", value="friday"))
k_1 = T("Send the report to Ana before Friday.", "en", sendana)
k_2 = T("Envía el informe a Ana antes del viernes.", "es", sendana)
k_3 = T("Envie o relatório para a Ana antes de sexta.", "pt", sendana)
P("K_paraphrase_multilingual", k_1, k_2, "EQUIVALENT")
P("K_paraphrase_multilingual", k_2, k_3, "EQUIVALENT")
k_4 = T("Manda el infrome a Ana antes del viernes.", "es", sendana)
P("K_paraphrase_multilingual", k_2, k_4, "EQUIVALENT", notes="typo")
k_5 = T("Revisa el contrato y dime los riesgos.", "es", M(action=["review", "report_risks"], object="contract"))
k_6 = T("Examina el acuerdo e identifica los peligros.", "es", M(action=["review", "report_risks"], object="contract"),
        amb=["'acuerdo' can be a contract or an informal agreement"])
P("K_paraphrase_multilingual", k_5, k_6, "UNDECIDABLE", notes="synonymy contrato/acuerdo and riesgos/peligros needs judgment; relabeled from EQUIVALENT while authoring")
k_7 = T("Pásame el reporte de ventas, porfa.", "es", M(action="send", object="sales_report", recipient="speaker"))
k_8 = T("Envíame el informe de ventas.", "es", M(action="send", object="sales_report", recipient="speaker"))
P("K_paraphrase_multilingual", k_7, k_8, "EQUIVALENT", notes="politeness marker is pragmatic, not task content")
k_9 = T("Puedes borrar los logs.", "es", M(action="delete", object="logs", modality="permission"))
k_10 = T("Debes borrar los logs.", "es", M(action="delete", object="logs", modality="obligation"))
k_11 = T("Está permitido borrar los logs.", "es", M(action="delete", object="logs", modality="permission"))
P("K_paraphrase_multilingual", k_9, k_10, "NOT_EQUIVALENT", [d("modality", "DISTORTION", "permission", "obligation", "CRITICAL")])
P("K_paraphrase_multilingual", k_9, k_11, "EQUIVALENT")


def write():
    os.makedirs(OUT, exist_ok=True)
    ids = {}
    with open(os.path.join(OUT, "texts.jsonl"), "w", encoding="utf-8") as f:
        for i, (txt, rec) in enumerate(TEXTS.items(), 1):
            tid = f"GT{i:03d}"
            ids[txt] = tid
            graph = [dict(path=k, value=v, status=("UNSPECIFIED" if v in ("UNSPECIFIED", "NONE") else "EXPLICIT")) for k, v in rec["canonical_meaning"].items()]
            row = dict(id=tid, language=rec["language"], source_text=rec["source_text"], canonical_meaning=rec["canonical_meaning"],
                       expected_semantic_graph=graph, ambiguities=rec["ambiguities"], forbidden_inferences=rec["forbidden_inferences"],
                       review_status="author-assigned")
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    with open(os.path.join(OUT, "pairs.jsonl"), "w", encoding="utf-8") as f:
        for i, p in enumerate(PAIRS, 1):
            row = dict(id=f"GP{i:03d}", category=p["category"], text_a=ids[p["text_a"]], text_b=ids[p["text_b"]],
                       expected_equivalence=p["expected_equivalence"], expected_diff=p["expected_diff"], notes=p["notes"],
                       review_status="author-assigned")
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    man = {n: hashlib.sha256(open(os.path.join(OUT, n), "rb").read()).hexdigest() for n in ("texts.jsonl", "pairs.jsonl")}
    json.dump(man, open(os.path.join(OUT, "MANIFEST.json"), "w"), indent=1)
    from collections import Counter
    print(len(TEXTS), "texts", len(PAIRS), "pairs", dict(Counter(p["expected_equivalence"] for p in PAIRS)))
    print(dict(Counter(p["category"] for p in PAIRS)))


if __name__ == "__main__":
    write()
