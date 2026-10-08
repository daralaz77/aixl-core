"""Phase 0 safety net: record the current observable behaviour of the pipeline so refactors can be proven neutral.
Regenerate ONLY when a behaviour change is intended:  python -m benchmarks.characterization --write
Uses the dev set + hand-picked edge cases (NO real user messages are stored). Date is frozen so relative-time texts are reproducible."""
import datetime as _real_dt
import json
import sys
from contextlib import contextmanager
from pathlib import Path

GOLDEN = Path(__file__).resolve().parent.parent / "tests" / "golden" / "characterization.json"
FROZEN = _real_dt.date(2026, 10, 8)

EXTRA = [
    "Hola", "creo que ya revisa", "si muestrame", "redacta el correo", "ya me logee por favor correlo tu", "listo revisa",
    "No elimines los datos originales.", "Do not translate the report.", "Nunca envíes el resultado.",
    "Resume este documento en cinco puntos y conserva solamente la información más importante.",
    "Please translate the attached quarterly report into English, keep all numbers unchanged, and return the result as JSON.",
    "Compara el reporte de ventas de Q1 2026 con el de Q2 2026 y genera un informe en PDF para la empresa Acme.",
    "Analiza las ventas de hoy.", "Analyze this week's videos.", "Ventas de la semana pasada.", "Analiza las ventas del mes pasado.",
    "Traduza este documento para inglês.", "Compare dataset #77 with dataset #81.", "Envía el reporte a ana@example.com mañana.",
    "borra el modelo de Ollama", "Analiza 100 usuarios.", "Analiza 1000 usuarios.", "Procesa 50 usuarios.", "yes show me", "ok revisa",
]


class _FixedDate(_real_dt.date):
    @classmethod
    def today(cls):
        return cls(FROZEN.year, FROZEN.month, FROZEN.day)


@contextmanager
def frozen_today():
    import aixl.translators.natural_to_semantic as n
    old_dt, old_n = _real_dt.date, n.date
    _real_dt.date = _FixedDate
    n.date = _FixedDate
    try:
        yield
    finally:
        _real_dt.date, n.date = old_dt, old_n


def corpus():
    import benchmarks.dataset as d
    seen = []
    for name in ("EQ", "DIFF", "NEG_EQ", "NEG_NEQ", "QTY_EQ", "QTY_NEQ", "DATE_EQ", "DATE_NEQ"):
        for a, b in getattr(d, name):
            for t in (a, b):
                if t not in seen:
                    seen.append(t)
    for t in EXTRA:
        if t not in seen:
            seen.append(t)
    return seen


def snapshot_one(text):
    from aixl.envelope import seal
    from aixl.gate import compact, translate_gated
    from aixl.serialization.aixl_codec import encode
    from aixl.telegraph import TelegraphError, to_telegraph
    from aixl.translators.natural_to_semantic import to_graph
    g = to_graph(text)
    wire = compact(encode(g))
    gate = translate_gated(text)
    try:
        tele = to_telegraph(wire)
    except TelegraphError as e:
        tele = "ERR:" + str(e)
    env = seal(text)
    return {"compact": wire, "fp": gate["fingerprint"], "gate": [gate["mode"], gate["reason"], gate["tokens_aixl"]],
            "tele": tele, "env": [env["verifiable"], env["fp"]]}


def snapshot():
    with frozen_today():
        return {t: snapshot_one(t) for t in corpus()}


if __name__ == "__main__":
    if "--write" in sys.argv:
        GOLDEN.write_text(json.dumps(snapshot(), ensure_ascii=False, indent=1, sort_keys=True) + "\n")
        print("wrote", GOLDEN, len(json.loads(GOLDEN.read_text())), "texts")
    else:
        print(json.dumps(snapshot(), ensure_ascii=False, indent=1)[:600])
