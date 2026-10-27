"""Measurement-pilot report: how often does meaning change between hops, from a partner's anonymised sample.

Two steps, because the detector's alert rate is NOT the real change rate (alerts include false alarms and it misses some corruptions):
  1. analyze  : run the offline detector on every pair, write results + a LABELING SHEET (a stratified random sample the humans label CAMBIO / IGUAL)
  2. report   : combine detector results and the human labels into the estimate of the REAL change rate with a 95 % credible interval, apply the pre-agreed decision rule
                (< 4 % stop, 4-15 % pivot, >= 15 % go) and write the report (counts only; no text of the partner's data is copied into it).

  python -m benchmarks.pilot_report analyze pairs.jsonl --out DIR [--sample 60]
  python -m benchmarks.pilot_report report DIR labels.csv --partner NAME [--labels2 second_person.csv] [--judges sonnet.tsv haiku.tsv] [--demo]

pairs.jsonl: one JSON per line {"id", "source", "relay", "flow" (optional)}.   labels.csv: id,label   with label in CAMBIO | IGUAL.
Estimate: real_rate = flagged_share * precision_of_flagged + unflagged_share * miss_rate_of_unflagged; the two rates come from the labeled sample (Beta posteriors,
20,000 draws, fixed seed); the shares are exact (known from all pairs). Not the detector's recall on a benchmark: measured on THIS partner's flow."""
import argparse
import collections
import csv
import json
import os
import random
import sys

import aixl

STOP_BELOW, GO_AT_OR_ABOVE = 0.04, 0.15          # agreed before measuring (pitch, slide 10): <4 % stop, 4-15 % pivot, >=15 % go


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    a = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return (max(0.0, (c - a) / d), min(1.0, (c + a) / d))


def estimate(n_flag: int, n_unflag: int, k_flag_real: int, n_flag_lab: int, k_unflag_real: int, n_unflag_lab: int, draws: int = 20000, seed: int = 7):
    """(point, low, high) of the real change rate over ALL pairs from the labeled strata."""
    n = n_flag + n_unflag
    if n == 0:
        return (0.0, 0.0, 1.0)
    f = n_flag / n
    prec = (k_flag_real / n_flag_lab) if n_flag_lab else 0.0
    miss = (k_unflag_real / n_unflag_lab) if n_unflag_lab else 0.0
    rng = random.Random(seed)
    xs = sorted(f * rng.betavariate(k_flag_real + 1, n_flag_lab - k_flag_real + 1) + (1 - f) * rng.betavariate(k_unflag_real + 1, n_unflag_lab - k_unflag_real + 1)
                for _ in range(draws))
    return (f * prec + (1 - f) * miss, xs[int(0.025 * draws)], xs[int(0.975 * draws) - 1])


def zone(point: float, low: float, high: float):
    """(decision, certain). Certain only when the whole interval sits inside one zone."""
    z = "PARAR" if point < STOP_BELOW else "SEGUIR" if point >= GO_AT_OR_ABOVE else "PIVOTAR"
    certain = (high < STOP_BELOW) if z == "PARAR" else (low >= GO_AT_OR_ABOVE) if z == "SEGUIR" else (low >= STOP_BELOW and high < GO_AT_OR_ABOVE)
    return z, certain


def analyze(pairs_path: str, out_dir: str, sample: int = 60, seed: int = 11):
    os.makedirs(out_dir, exist_ok=True)
    rows = [json.loads(line) for line in open(pairs_path, encoding="utf-8") if line.strip()]
    res = []
    for r in rows:
        v = aixl.relay_check(r["source"], r["relay"])
        res.append({"id": r["id"], "flow": r.get("flow", "-"), "flagged": not v["ok"], "families": sorted({x["family"] for x in v["violations"]})})
    with open(os.path.join(out_dir, "results.jsonl"), "w", encoding="utf-8") as f:
        for x in res:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    rng = random.Random(seed)
    flagged = [r for r, x in zip(rows, res) if x["flagged"]]
    unflagged = [r for r, x in zip(rows, res) if not x["flagged"]]
    pick = rng.sample(flagged, min(sample, len(flagged))) + rng.sample(unflagged, min(sample, len(unflagged)))
    rng.shuffle(pick)                                              # the labeler must not know which pairs the detector flagged
    with open(os.path.join(out_dir, "labeling_sheet.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "source", "relay", "label (CAMBIO | IGUAL)"])
        for r in pick:
            w.writerow([r["id"], r["source"], r["relay"], ""])
    print(f"{len(rows)} pairs: {len(flagged)} flagged, {len(unflagged)} not. Labeling sheet with {len(pick)} pairs (shuffled, detector result hidden): {out_dir}/labeling_sheet.csv")
    print("Give it to TWO people independently; keep only (id, label) in labels.csv; delete the sheet afterwards (it contains the partner's text).")


def _read_judges(paths):
    votes = []
    for p in paths:
        v = {}
        for row in csv.reader(open(p, encoding="utf-8"), delimiter="\t"):
            if len(row) >= 2:
                v[row[0].strip()] = row[1].strip().upper()
        votes.append(v)
    return votes


def _read_labels(path):
    lab = {}
    for row in csv.reader(open(path, encoding="utf-8")):
        if len(row) >= 2 and row[1].strip().upper() in ("CAMBIO", "IGUAL"):
            lab[row[0].strip()] = row[1].strip().upper() == "CAMBIO"
    return lab


def report(out_dir: str, labels_path: str, partner: str, judges=None, demo: bool = False, labels2_path: str | None = None) -> str:
    res = [json.loads(line) for line in open(os.path.join(out_dir, "results.jsonl"), encoding="utf-8")]
    lab = _read_labels(labels_path)
    agree_txt = ""
    if labels2_path:
        lab2 = _read_labels(labels2_path)
        both = [i for i in lab if i in lab2]
        same = [i for i in both if lab[i] == lab2[i]]
        agree_txt = f"Acuerdo entre las dos personas: {len(same)} de {len(both)} pares ({100 * len(same) / max(len(both), 1):.1f} %); los {len(both) - len(same)} en desacuerdo se excluyeron de la estimación."
        lab = {i: lab[i] for i in same}
    n = len(res)
    flagged = [x for x in res if x["flagged"]]
    unflagged = [x for x in res if not x["flagged"]]
    lf = [lab[x["id"]] for x in flagged if x["id"] in lab]
    lu = [lab[x["id"]] for x in unflagged if x["id"] in lab]
    k1, n1, k0, n0 = sum(lf), len(lf), sum(lu), len(lu)
    point, low, high = estimate(len(flagged), len(unflagged), k1, n1, k0, n0)
    dec, certain = zone(point, low, high)
    fam = collections.Counter(f for x in flagged for f in x["families"])
    flows = collections.defaultdict(lambda: [0, 0])
    for x in res:
        flows[x["flow"]][1] += 1
        flows[x["flow"]][0] += x["flagged"]
    p1 = wilson(k1, n1)
    p0 = wilson(k0, n0)
    pct = lambda x: f"{100 * x:.1f} %"            # noqa: E731
    L = []
    L.append(f"# Informe del piloto de medición — {partner}")
    if demo:
        L.append("\n> **EJEMPLO DE DEMOSTRACIÓN, no es un resultado de ningún socio.** Se generó con relays escritos por modelos (los de `data/relays`) y con etiquetas conocidas de antemano, solo para mostrar el formato y comprobar el cálculo.")
    L.append(f"\n## 1. Resumen\n- **Traspasos analizados:** {n}.\n- **Tasa real estimada de cambio de significado:** **{pct(point)}** (intervalo 95 %: {pct(low)} – {pct(high)}).")
    L.append(f"- **Decisión según la regla acordada** (< 4 % parar · 4–15 % pivotar · ≥ 15 % seguir): **{dec}**" + ("." if certain else
             " — **no concluyente**: el intervalo cruza un umbral; hay que ampliar la muestra etiquetada antes de decidir."))
    L.append("\n## 2. Método\nUn detector sin modelo y sin conexión revisó cada par (origen → reenvío) y señaló los que cambiaron un dato crítico (negación, cifra, fecha, hora, condición, modalidad, nombre, acción, destinatario…). "
             "Como las alertas no son cambios reales, dos personas etiquetaron de forma independiente una muestra aleatoria **estratificada** (pares señalados y no señalados, mezclados y sin saber cuáles eran) como CAMBIO o IGUAL. "
             "La tasa real combina la precisión de las alertas y la tasa de cambios que el detector no vio, cada una medida en su estrato.")
    L.append(f"\n## 3. Resultados\n| Medida | Valor |\n|---|---|\n| Pares señalados por el detector | {len(flagged)} de {n} ({pct(len(flagged) / n if n else 0)}) |")
    L.append(f"| Etiquetados entre los señalados | {n1}; de ellos CAMBIO real: {k1} → precisión de las alertas {pct(k1 / n1 if n1 else 0)} (IC 95 %: {pct(p1[0])} – {pct(p1[1])}) |")
    L.append(f"| Etiquetados entre los NO señalados | {n0}; de ellos CAMBIO real: {k0} → cambios que el detector no vio {pct(k0 / n0 if n0 else 0)} (IC 95 %: {pct(p0[0])} – {pct(p0[1])}) |")
    L.append(f"| **Tasa real de cambio estimada** | **{pct(point)}** (IC 95 %: {pct(low)} – {pct(high)}) |")
    L.append("\n**Qué tipo de dato cambió** (familias señaladas por el detector, sobre los pares señalados):\n")
    L.append("| Familia | Pares |\n|---|---|")
    for f, c in fam.most_common(12):
        L.append(f"| {f} | {c} |")
    if len(flows) > 1:
        L.append("\n**Por flujo:**\n\n| Flujo | Señalados / total |\n|---|---|")
        for k, (a, b) in sorted(flows.items()):
            L.append(f"| {k} | {a} / {b} ({pct(a / b if b else 0)}) |")
    if judges:
        vs = _read_judges(judges)
        c = collections.Counter()
        for x in res:
            ys = [v.get(x["id"], "") for v in vs]
            c["SAME" if all(y == "SAME" for y in ys) else "DIFFERENT" if any(y == "DIFFERENT" for y in ys) else "UNSURE"] += 1
        L.append(f"\n**Árbitro de dos jueces** (solo si el socio lo autorizó): IGUAL {c['SAME']} · DISTINTO {c['DIFFERENT']} · INDECISO {c['UNSURE']} de {n}.")
    L.append("\n## 4. Qué significa para el socio\n- Si la decisión es **SEGUIR**: hay un problema real y frecuente; el siguiente paso es poner la revisión en el punto del flujo donde más cambia (ver familias).\n"
             "- Si es **PIVOTAR**: el problema existe pero es moderado; conviene limitarlo a los flujos donde un error cuesta mucho.\n- Si es **PARAR**: el significado casi no cambia en este flujo; se cierra el piloto y este informe es el resultado.")
    L.append("\n## 5. Límites\n- La muestra es de un solo flujo y de tamaño limitado; el intervalo muestra cuánto se puede confiar en la cifra.\n- Las etiquetas son humanas y pueden discrepar. " + (agree_txt or "No se aportó la segunda persona: el acuerdo entre etiquetadores no se pudo medir.") + "\n"
             "- El detector es para traspasos casi literales; en resúmenes que reformulan genera falsas alarmas (por eso la tasa se estima con las etiquetas y no con las alertas).\n"
             "- No se evaluó a personas ni a agentes individuales, no se entrenó ningún modelo y no se publica nada que identifique al socio sin su autorización escrita.")
    L.append("\n## 6. Confidencialidad y borrado\nEste informe contiene solo conteos y porcentajes. La muestra y la hoja de etiquetado se suprimen dentro del plazo del acuerdo de confidencialidad y se confirma por escrito.")
    text = "\n".join(L) + "\n"
    with open(os.path.join(out_dir, "informe.md"), "w", encoding="utf-8") as f:
        f.write(text)
    return text


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analyze"); a.add_argument("pairs"); a.add_argument("--out", required=True); a.add_argument("--sample", type=int, default=60)
    r = sub.add_parser("report"); r.add_argument("dir"); r.add_argument("labels"); r.add_argument("--partner", required=True); r.add_argument("--judges", nargs="*"); r.add_argument("--demo", action="store_true"); r.add_argument("--labels2")
    args = ap.parse_args(argv)
    if args.cmd == "analyze":
        analyze(args.pairs, args.out, args.sample)
    else:
        print(report(args.dir, args.labels, args.partner, args.judges, args.demo, args.labels2))


if __name__ == "__main__":
    sys.exit(main())
