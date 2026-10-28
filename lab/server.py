"""Semantic Lab web app (stdlib only). python lab/server.py [port]  ->  http://localhost:8765"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aixl import detect_ambiguity, detect_contradiction, detect_drift, semantic_diff, to_aixl  # noqa: E402
from aixl.api.service import compare_verified  # noqa: E402
from aixl.invariants import relay_check  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def decide_state(verified: dict, relay: dict) -> tuple[str, str]:
    """Three-state verdict shown by the page. Never 'PROVEN' unless the verified comparator proved it AND no critical slot changed."""
    if verified.get("verdict") == "UNVERIFIED":
        return "UNVERIFIED", "El texto es demasiado largo para analizarlo."
    if not relay.get("ok", False):
        return "DIFFERENCE", "Un dato crítico (cifra, fecha, negación, condición…) cambió entre A y B."
    if verified.get("verdict") == "NOT_EQUIVALENT" and verified.get("difference_reliable"):
        return "DIFFERENCE", "El comparador encontró una diferencia de significado."
    if verified.get("equivalent") and verified.get("verified"):
        return "PROVEN", "Equivalencia comprobada dentro del vocabulario controlado de AIXL."
    return "NO_PROOF", "No se detectó ningún cambio crítico, pero AIXL no puede probar que signifiquen lo mismo."


class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code); self.send_header("Content-Type", ctype + "; charset=utf-8"); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            return self._send(200, open(os.path.join(HERE, "index.html"), "rb").read(), "text/html")
        self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self):
        if self.path != "/api/compare":
            return self._send(404, json.dumps({"error": "not found"}))
        n = int(self.headers.get("Content-Length", 0))
        try:
            p = json.loads(self.rfile.read(n) or b"{}")
            a, b = str(p.get("a", ""))[:2000], str(p.get("b", ""))[:2000]
        except Exception:                                # noqa: BLE001
            return self._send(400, json.dumps({"error": "bad request"}))
        try:
            verified = compare_verified(a, b)
            relay = relay_check(a, b)
            state, reason = decide_state(verified, relay)
            out = dict(verified)
            out.setdefault("similarity", 0.0)
            out.setdefault("per_dimension", {})
            out.setdefault("differences", [])
            out.setdefault("drift_level", "NO_DRIFT")
            out.update({"state": state, "state_reason": reason, "relay": relay})
            if verified.get("verdict") == "UNVERIFIED":
                return self._send(200, json.dumps({**out, "aixl_a": "", "aixl_b": "", "diff_text": "", "drift_report": {"flag": False},
                                                   "ambiguity_a": {"ambiguous": False, "findings": []}, "ambiguity_b": {"ambiguous": False, "findings": []},
                                                   "contradiction": {"contradiction": False, "alerts": []}}, ensure_ascii=False))
            out.update({"aixl_a": to_aixl(a), "aixl_b": to_aixl(b), "diff_text": semantic_diff(a, b), "drift_report": detect_drift(a, b).to_dict(),
                        "ambiguity_a": detect_ambiguity(a).to_dict(), "ambiguity_b": detect_ambiguity(b).to_dict(),
                        "contradiction": detect_contradiction(a, b).to_dict()})
        except Exception as e:                           # noqa: BLE001 — fail closed
            return self._send(500, json.dumps({"error": f"no se pudo analizar: {type(e).__name__}"}))
        self._send(200, json.dumps(out, ensure_ascii=False))

    def log_message(self, *a):                           # quiet
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    print(f"AIXL Semantic Lab on http://localhost:{port}", flush=True)
    HTTPServer(("127.0.0.1", port), H).serve_forever()
