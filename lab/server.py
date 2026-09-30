"""Semantic Lab web app (stdlib only). python lab/server.py [port]  ->  http://localhost:8765"""
import json, os, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aixl import compare, detect_ambiguity, detect_contradiction, to_aixl, semantic_diff, detect_drift  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


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
        r = compare(a, b)
        out = r.to_dict()
        out.update({"aixl_a": to_aixl(a), "aixl_b": to_aixl(b), "diff_text": semantic_diff(a, b), "drift_report": detect_drift(a, b).to_dict(),
                    "ambiguity_a": detect_ambiguity(a).to_dict(), "ambiguity_b": detect_ambiguity(b).to_dict(),
                    "contradiction": detect_contradiction(a, b).to_dict()})
        self._send(200, json.dumps(out, ensure_ascii=False))

    def log_message(self, *a):                           # quiet
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    print(f"AIXL Semantic Lab on http://localhost:{port}", flush=True)
    HTTPServer(("127.0.0.1", port), H).serve_forever()
