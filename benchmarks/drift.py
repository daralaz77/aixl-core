"""Drift benchmark: distribution of drift levels per pair type + the spec §40 critical pairs."""
import json

from aixl import detect_drift

CRITICAL_PAIRS = [("Elimina el reporte.", "No elimines el reporte."), ("Permite eliminar el reporte.", "Prohíbe eliminar el reporte."),
    ("Envía el reporte.", "No envíes el reporte."), ("Haz público el reporte.", "Haz privado el reporte."), ("Analiza 100 registros.", "Analiza 1000 registros."),
    ("Analiza las ventas de Q1 2026.", "Analiza las ventas de Q2 2026."), ("Activa la alerta.", "Desactiva la alerta."),
    ("Analiza los reportes antes de 2026-03-15.", "Analiza los reportes después de 2026-03-15.")]
NON_CRITICAL = [("Analiza las ventas.", "Examina las ventas."), ("Genera un informe en PDF.", "Genera un informe en JSON.")]

if __name__ == "__main__":
    out = []
    for a, b in CRITICAL_PAIRS + NON_CRITICAL:
        r = detect_drift(a, b)
        out.append({"a": a, "b": b, "level": r.level, "critical_flag": r.critical, "fields": [d.field for d in r.differences]})
    print(json.dumps(out, indent=1, ensure_ascii=False))
    n = sum(1 for o in out[:len(CRITICAL_PAIRS)] if o["level"] == "CRITICAL_DRIFT")
    print(f"critical pairs flagged CRITICAL_SEMANTIC_DRIFT: {n}/{len(CRITICAL_PAIRS)}")
