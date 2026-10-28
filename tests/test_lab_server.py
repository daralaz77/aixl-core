"""Semantic Lab: the page's three-state verdict must never say PROVEN without proof."""
import json
import threading
import urllib.request
from http.server import HTTPServer

import pytest

from aixl.api.service import compare_verified
from aixl.invariants import relay_check
from lab.server import H, decide_state


def state(a, b):
    return decide_state(compare_verified(a, b), relay_check(a, b))[0]


@pytest.mark.parametrize("a,b", [("Analiza las ventas de Q1 2026.", "Analiza las ventas de Q2 2026."), ("Elimina el reporte.", "No elimines el reporte."),
                                 ("Analiza 100 registros.", "Analiza 1000 registros."), ("Confianza >= 0.90", "Confianza >= 0.70")])
def test_critical_changes_are_flagged(a, b):
    assert state(a, b) == "DIFFERENCE"


def test_unprovable_paraphrase_is_never_proven():
    assert state("Envía el informe a Ana.", "Mándale a Ana el informe.") == "NO_PROOF"


def test_controlled_vocabulary_equivalence_can_be_proven():
    assert state("Analiza las ventas del primer trimestre de 2026.", "Examina las ventas de Q1 2026.") == "PROVEN"


def test_oversize_input_is_not_analysed():
    assert decide_state({"verdict": "UNVERIFIED"}, {"ok": True})[0] == "UNVERIFIED"


def test_http_roundtrip_and_bad_request():
    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        req = urllib.request.Request(base + "/api/compare", json.dumps({"a": "Elimina el reporte.", "b": "No elimines el reporte."}).encode(),
                                     {"Content-Type": "application/json"})
        d = json.loads(urllib.request.urlopen(req).read())
        assert d["state"] == "DIFFERENCE" and "relay" in d
        html = urllib.request.urlopen(base + "/").read().decode()
        assert "COMPARAR" in html and 'aria-live="polite"' in html
    finally:
        srv.shutdown()
