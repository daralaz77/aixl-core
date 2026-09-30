"""The six mandatory demos of the master prompt (DEMO level: same author as the code, see BENCHMARK.md)."""
import subprocess, sys, os
import aixl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_demo1_equivalent():
    assert aixl.compare("Analiza las ventas del primer trimestre de 2026.", "Examina las ventas de Q1 2026.").equivalent


def test_demo2_time_drift():
    r = aixl.compare("Analiza las ventas de Q1 2026.", "Analiza las ventas de Q2 2026.")
    assert not r.equivalent and [d.field for d in r.differences] == ["TIME"] and r.drift_level in ("MAJOR_DRIFT", "CRITICAL_DRIFT")


def test_demo3_negation_critical():
    r = aixl.compare("Elimina el reporte.", "No elimines el reporte.")
    assert not r.equivalent and r.critical_changes and r.critical_changes[0].field == "NEGATION"


def test_demo4_quantity():
    r = aixl.compare("Analiza 100 registros.", "Analiza 1000 registros.")
    assert not r.equivalent and [d.field for d in r.differences] == ["QUANTITY"]


def test_demo5_constraint():
    r = aixl.compare("Confianza >= 0.90", "Confianza >= 0.70")
    assert not r.equivalent and "MODIFIERS" in [d.field for d in r.differences]


def test_demo6_ambiguous():
    assert aixl.detect_ambiguity("Analiza los datos recientes.").ambiguous


def test_cli_commands_run_without_error():
    for args in (["translate", "Analiza las ventas de Q1 2026"], ["compare", "Analiza las ventas de Q1 2026", "Examina las ventas del primer trimestre de 2026"],
                 ["diff", "Analiza las ventas de Q1 2026", "Analiza las ventas de Q2 2026"], ["drift", "Analiza las ventas de Q1 2026", "Analiza las ventas de Q2 2026"], ["demo"]):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "cli.py")] + args, capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, (args, r.stderr)
        assert r.stdout.strip()


def test_api_surface_of_the_master_prompt():
    for name in ("translate", "to_semantic", "to_aixl", "from_aixl", "compare", "compare_aixl", "semantic_diff", "detect_drift", "detect_ambiguity", "detect_contradiction"):
        assert callable(getattr(aixl, name))
    a, b = aixl.to_aixl("Analiza las ventas de Q1 2026"), aixl.to_aixl("Examina las ventas del primer trimestre de 2026")
    assert aixl.compare_aixl(a, b).equivalent and aixl.from_aixl(a).canonical()["time"] == ("Q1-2026",)
