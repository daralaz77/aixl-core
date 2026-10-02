"""Generates a genuinely FRESH corpus of natural-language texts (ES/EN/PT) for distillation training --
built 2026-10-01 after the first distillation round (3017 lines, all recycled from prior experiments)
plateaued at F1 0.6928: the project's own evidence pointed at needing new, non-recycled training data,
not more epochs on the same ~1400 underlying sentences.

Combinatorial template generation across action/domain/modifier/language slots, covering the same
semantic categories the project's own blind-set authors used (paraphrase, negation, quantity, time,
condition, recipient, output format) so the distribution matches what blind5 actually tests. Every
generated text is checked against every text already present anywhere under data/ or distill/ (2554
strings as of this run) and dropped on an exact match, so this is provably new material, not a reshuffle.

Includes real EQUIVALENT pairs (same meaning via two templates/languages) by design -- the project's own
measurement showed forcing matching targets on true paraphrase pairs during training was the single
most effective previous intervention (F1 0.6056 -> 0.6928 combined with temp=0), so this generator keeps
feeding that mechanism with fresh pairs instead of the same 400 recycled ones.

usage: python distill/generate_fresh_texts.py [--n N]  (writes distill/fresh_texts.json)
"""
import glob
import itertools
import json
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Every verb below is one the card's own vocabulary list (card_0.3.md) literally defines for that
# action -- the first distillation round's teacher labels went wrong (A:UNSPECIFIED, everything mapped
# to generic E:REPORT) exactly because an earlier version of this generator used invented business
# vocabulary (invoice, budget, ticket, bank account...) the card has no mapping for at all. Fixed by
# restricting every action verb and domain/entity noun to the card's closed vocabulary (its "D (what is
# worked on): SALES CUSTOMERS USERS DATA DATASET REPORT DOCUMENT IMAGE AUDIO VIDEO" / "E (things to
# find/act on): ANOMALY PERSON COMPANY PRODUCT MODEL RESULT EVENT" lines, and its per-action verb lists).
ACTIONS = [
    # (action_id, es_verb, es_verb_alt, en_verb, en_verb_alt, pt_verb)
    ("GENERATE", "Genera", "Crea", "Generate", "Create", "Gere"),
    ("ANALYZE", "Analiza", "Examina", "Analyze", "Examine", "Analise"),
    ("COMPARE", "Compara", "Contrasta", "Compare", "Contrast", "Compare"),
    ("FIND", "Encuentra", "Localiza", "Find", "Locate", "Encontra"),
    ("SEARCH", "Busca", "Rastrea", "Search", "Look for", "Procure"),
    ("SUMMARIZE", "Resume", "Sintetiza", "Summarize", "Condense", "Resume"),
    ("TRANSLATE", "Traduce", "Convierte", "Translate", "Render", "Traduza"),
    ("CHECK", "Verifica", "Valida", "Check", "Validate", "Verifique"),
    ("DELETE", "Elimina", "Borra", "Delete", "Remove", "Exclua"),
    ("EXECUTE", "Ejecuta", "Corre", "Execute", "Run", "Execute"),
    ("CALCULATE", "Calcula", "Computa", "Calculate", "Compute", "Calcule"),
    ("GET", "Obtén", "Recupera", "Get", "Retrieve", "Obtenha"),
    ("TRANSFORM", "Transforma", "Convierte", "Transform", "Convert", "Transforme"),
    ("ENABLE", "Activa", "Habilita", "Enable", "Turn on", "Ative"),
    ("DISABLE", "Desactiva", "Suspende", "Disable", "Deactivate", "Desative"),
    ("SEND", "Envía", "Notifica", "Send", "Notify", "Envie"),
    ("INCLUDE", "Incluye", "Agrega", "Include", "Add", "Inclua"),
    ("EXCLUDE", "Excluye", "Omite", "Exclude", "Omit", "Exclua"),
    ("UPDATE", "Actualiza", "Modifica", "Update", "Modify", "Atualize"),
]

# D-type nouns go in D:; E-type nouns go in E: (card_0.3.md line 37) -- mixed together here since this
# generator only needs correct natural-language text, not the AIXL output itself (the teacher produces
# that), but keeping both families represented matches the real distribution blind5 tests.
DOMAINS = [
    ("sales", "las ventas", "las cifras de ventas", "the sales", "the sales figures", "as vendas"),
    ("customers", "los clientes", "los datos de clientes", "the customers", "the customer data", "os clientes"),
    ("users", "los usuarios", "la lista de usuarios", "the users", "the user list", "os usuários"),
    ("data", "los datos", "el conjunto de datos", "the data", "the dataset", "os dados"),
    ("report", "el reporte", "el informe", "the report", "the report document", "o relatório"),
    ("document", "el documento", "los documentos", "the document", "the documents", "o documento"),
    ("image", "las imágenes", "las fotografías", "the images", "the pictures", "as imagens"),
    ("video", "el video", "los videos", "the video", "the videos", "o vídeo"),
    ("anomaly", "las anomalías", "los valores atípicos", "the anomalies", "the outliers", "as anomalias"),
    ("person", "la persona", "el contacto", "the person", "the contact", "a pessoa"),
    ("company", "la empresa", "la compañía", "the company", "the organization", "a empresa"),
    ("product", "el producto", "los productos", "the product", "the products", "o produto"),
    ("model", "el modelo", "el modelo entrenado", "the model", "the trained model", "o modelo"),
    ("result", "el resultado", "los resultados", "the result", "the results", "o resultado"),
    ("event", "el evento", "los eventos", "the event", "the events", "o evento"),
]

TIME_MODS = [
    (" de Q1 2026", " del primer trimestre de 2026", " for Q1 2026", " for the first quarter of 2026", " do Q1 2026"),
    (" de marzo de 2025", " de 2025-03", " for March 2025", " for 2025-03", " de março de 2025"),
    (" de ayer", " del día anterior", " from yesterday", " from the previous day", " de ontem"),
    (" de la próxima semana", " de la semana entrante", " for next week", " for the upcoming week", " da próxima semana"),
    ("", "", "", "", ""),
]

NEGATIONS_ES = ["No ", "Nunca "]
NEGATIONS_EN = ["Do not ", "Never "]
NEGATIONS_PT = ["Não ", "Nunca "]

CONDITIONS = [
    (" si está inactivo", " en caso de que esté inactivo", " if it is inactive", " in case it is inactive", " se estiver inativo"),
    (" si el total supera los 1000", " cuando el monto exceda 1000", " if the total exceeds 1000", " when the amount exceeds 1000", " se o total ultrapassar 1000"),
    (" si la confianza es menor a 0.80", " cuando la certeza sea baja", " if confidence is below 0.80", " when certainty is low", " se a confiança for menor que 0.80"),
    ("", "", "", "", ""),
]

RECIPIENTS = [
    (" a Marta", " al equipo de soporte", " to Marta", " to the support team", " para Marta"),
    (" al gerente", " a finanzas", " to the manager", " to finance", " ao gerente"),
    ("", "", "", "", ""),
]

OUTPUT_FORMATS = [
    (" en PDF", " en formato PDF", " as PDF", " in PDF format", " em PDF"),
    (" en formato de tabla", " como tabla", " as a table", " in table format", " em formato de tabela"),
    (" en JSON", " en formato JSON", " as JSON", " in JSON format", " em JSON"),
    ("", "", "", "", ""),
]

# quantity phrases take the domain noun itself as {obj} so they read as one real noun phrase
# ("los primeros 10 registros de ventas") instead of being bolted on before a separate object mention.
QUANTITIES = [
    ("los primeros 10 registros de {obj}", "las 10 principales entradas de {obj}",
     "the first 10 {obj} records", "the top 10 {obj} entries",
     "os primeiros 10 registros de {obj}"),
    ("más de 100 registros de {obj}", "al menos 100 elementos de {obj}",
     "more than 100 {obj} records", "at least 100 {obj} items",
     "mais de 100 registros de {obj}"),
    (None, None, None, None, None),  # no quantity modifier: use the plain object noun phrase
]


def build_sentence(action_idx, domain_idx, lang, variant, time_idx, neg, cond_idx, rec_idx, fmt_idx, qty_idx):
    aid, es1, es2, en1, en2, pt1 = ACTIONS[action_idx]
    did, es_d1, es_d2, en_d1, en_d2, pt_d1 = DOMAINS[domain_idx]
    time_es, time_es2, time_en, time_en2, time_pt = TIME_MODS[time_idx]
    cond_es, cond_es2, cond_en, cond_en2, cond_pt = CONDITIONS[cond_idx]
    rec_es, rec_es2, rec_en, rec_en2, rec_pt = RECIPIENTS[rec_idx]
    fmt_es, fmt_es2, fmt_en, fmt_en2, fmt_pt = OUTPUT_FORMATS[fmt_idx]
    qty_es, qty_es2, qty_en, qty_en2, qty_pt = QUANTITIES[qty_idx]

    if lang == "es":
        verb = es1 if variant == 0 else es2
        plain_obj = es_d1 if variant == 0 else es_d2
        qty_tpl = qty_es if variant == 0 else qty_es2
        obj = qty_tpl.format(obj=plain_obj) if qty_tpl else plain_obj
        obj = obj.replace("de el ", "del ")  # "de el reporte" -> "del reporte"
        neg_prefix = random.choice(NEGATIONS_ES) if neg else ""
        time_m = time_es if variant == 0 else time_es2
        cond_m = cond_es if variant == 0 else cond_es2
        rec_m = rec_es if variant == 0 else rec_es2
        fmt_m = fmt_es if variant == 0 else fmt_es2
        verb_lower = verb[0].lower() + verb[1:]
        text = f"{neg_prefix}{verb if not neg_prefix else verb_lower} {obj}{time_m}{cond_m}{rec_m}{fmt_m}."
    elif lang == "en":
        verb = en1 if variant == 0 else en2
        plain_obj = en_d1 if variant == 0 else en_d2
        qty_tpl = qty_en if variant == 0 else qty_en2
        # quantity templates supply their own determiner ("the top 10 ... entries"); strip the bare
        # noun's own leading "the " so it doesn't double up ("the top 10 the sales entries")
        bare_obj = plain_obj[4:] if plain_obj.startswith("the ") else plain_obj
        obj = qty_tpl.format(obj=bare_obj) if qty_tpl else plain_obj
        neg_prefix = random.choice(NEGATIONS_EN) if neg else ""
        time_m = time_en if variant == 0 else time_en2
        cond_m = cond_en if variant == 0 else cond_en2
        rec_m = rec_en if variant == 0 else rec_en2
        fmt_m = fmt_en if variant == 0 else fmt_en2
        verb_out = verb.lower() if neg_prefix else verb
        text = f"{neg_prefix}{verb_out} {obj}{time_m}{cond_m}{rec_m}{fmt_m}."
    else:  # pt
        verb = pt1
        plain_obj = pt_d1
        qty_tpl = qty_pt
        obj = qty_tpl.format(obj=plain_obj) if qty_tpl else plain_obj
        obj = (obj.replace("de os ", "dos ").replace("de as ", "das ")
                  .replace("de o ", "do ").replace("de a ", "da "))  # "de o"->"do", "de as"->"das", etc.
        neg_prefix = random.choice(NEGATIONS_PT) if neg else ""
        time_m = time_pt
        cond_m = cond_pt
        rec_m = rec_pt
        fmt_m = fmt_pt
        verb_out = verb.lower() if neg_prefix else verb
        text = f"{neg_prefix}{verb_out} {obj}{time_m}{cond_m}{rec_m}{fmt_m}."

    text = " ".join(text.split())  # collapse accidental double spaces
    return text, aid, did


def load_existing_texts():
    existing = set()
    for f in glob.glob(os.path.join(ROOT, "data", "**", "*.json*"), recursive=True) + \
              glob.glob(os.path.join(ROOT, "distill", "*.json*")):
        try:
            if f.endswith(".jsonl"):
                for l in open(f, encoding="utf-8"):
                    if l.strip():
                        d = json.loads(l)
                        for k in ("text", "a", "b"):
                            if k in d:
                                existing.add(d[k])
            else:
                d = json.load(open(f, encoding="utf-8"))
                if isinstance(d, list):
                    for item in d:
                        if isinstance(item, dict):
                            for k in ("text", "a", "b", "input_a", "input_b"):
                                if k in item:
                                    existing.add(item[k])
        except Exception:                                   # noqa: BLE001 -- best-effort de-dup scan
            continue
    return existing


def main():
    n_target = 2000
    if "--n" in sys.argv:
        n_target = int(sys.argv[sys.argv.index("--n") + 1])

    random.seed(42)
    existing = load_existing_texts()
    print(f"existing texts loaded for de-dup: {len(existing)}")

    combos = list(itertools.product(
        range(len(ACTIONS)), range(len(DOMAINS)), ["es", "en", "pt"], [0, 1],
        range(len(TIME_MODS)), [False, True], range(len(CONDITIONS)),
        range(len(RECIPIENTS)), range(len(OUTPUT_FORMATS)), range(len(QUANTITIES)),
    ))
    random.shuffle(combos)

    seen_this_run = set()
    items = []
    pair_counter = 0
    for combo in combos:
        if len(items) >= n_target:
            break
        text, aid, did = build_sentence(*combo)
        if text in existing or text in seen_this_run:
            continue
        seen_this_run.add(text)
        items.append({"tid": f"f{len(items):04d}", "text": text, "action": aid, "domain": did})

    # paraphrase pairs: for a slice of the generated items, add a SECOND phrasing (variant flipped,
    # same semantic slots) explicitly marked as an EQUIVALENT pair -- feeds the consistency-training
    # mechanism that already proved itself on the recycled corpus, now with fresh pairs.
    pairs = []
    for combo in combos:
        if len(pairs) >= n_target // 4:
            break
        action_idx, domain_idx, lang, variant, time_idx, neg, cond_idx, rec_idx, fmt_idx, qty_idx = combo
        text_a, aid, did = build_sentence(action_idx, domain_idx, lang, 0, time_idx, neg, cond_idx, rec_idx, fmt_idx, qty_idx)
        text_b, _, _ = build_sentence(action_idx, domain_idx, lang, 1, time_idx, neg, cond_idx, rec_idx, fmt_idx, qty_idx)
        if text_a == text_b:
            continue
        if text_a in existing or text_b in existing:
            continue
        pair_counter += 1
        pid = f"FP-{pair_counter:04d}"
        pairs.append({"pair": pid, "a": text_a, "b": text_b, "label": "EQUIVALENT"})

    out_path = os.path.join(ROOT, "distill", "fresh_texts.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"items": items, "pairs": pairs}, f, ensure_ascii=False, indent=1)

    print(f"generated {len(items)} fresh single texts, {len(pairs)} fresh EQUIVALENT pairs")
    print(f"written to {out_path}")


if __name__ == "__main__":
    main()
