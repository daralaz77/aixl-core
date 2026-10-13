"""Smoke test of an INSTALLED aixl wheel (run it from outside the repo, with the repo NOT on sys.path).
   python -m venv /tmp/v && /tmp/v/bin/pip install dist/aixl-*.whl && cd /tmp && /tmp/v/bin/python <repo>/scripts/wheel_smoke.py
Found 2026-10-13: the first wheel failed 7/7 core calls with FileNotFoundError (config.json lived outside the package)."""
import os
import sys

import aixl

if os.path.exists(os.path.join(os.getcwd(), "aixl", "__init__.py")):
    sys.exit("run this from a directory that is not the repo root: it must exercise the INSTALLED package")
from aixl import arbiter, envelope, gate  # noqa: E402
from aixl.atoms import registry  # noqa: E402

checks = {
    "translate": lambda: aixl.to_aixl("Analiza las ventas de Q1 2026.").startswith("V:AIXL"),
    "compare": lambda: aixl.compare("Elimina el reporte.", "No elimines el reporte.").equivalent is False,
    "compare_verified": lambda: aixl.compare_verified("Analiza las ventas de Q1 2026.", "Analyze Q1 2026 sales.")["verdict"] == "EQUIVALENT",
    "ambiguity": lambda: aixl.detect_ambiguity("Borra el reporte.").ambiguous is True,
    "drift": lambda: aixl.detect_drift("Elimina el reporte.", "No elimines el reporte.").critical is True,
    "negotiate": lambda: aixl.negotiate("Archive ticket #77.", "Close ticket #77.") is not None,
    "fingerprint": lambda: len(aixl.semantic_fingerprint("Analiza las ventas de Q1 2026.")) == 16,
    "envelope": lambda: envelope.verify(envelope.seal("Analiza las ventas."), "Analiza las ventas.") == "MATCH",
    "gate": lambda: gate.translate_gated("Compara el documento 1 con el documento 2.")["mode"] in ("AIXL", "NATURAL"),
    "arbiter rules": lambda: len(arbiter.rules_id()) == 16,
    "atoms registry data": lambda: len(registry._load_learned()) > 0,
}
failed = []
for name, fn in checks.items():
    try:
        ok = bool(fn())
    except Exception as e:
        ok, name = False, f"{name} ({type(e).__name__}: {str(e)[:80]})"
    print(("OK   " if ok else "FAIL ") + name)
    if not ok:
        failed.append(name)
print(f"{len(checks) - len(failed)}/{len(checks)} checks passed from {aixl.__file__}")
sys.exit(1 if failed else 0)
