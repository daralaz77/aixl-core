"""Bearer-token matrix: starts a REAL otelcol-contrib (bearertokenauth on the HTTP and gRPC receivers) and runs emit.py with the right token, no token, a wrong token and the right token under the wrong scheme.
Run from a scratch folder holding v/ (venv), contrib/otelcol-contrib and cfg_token.yaml; emit.py is taken from the repo (see README.md). The token is generated here and never printed."""
import os
import secrets
import subprocess
import sys
import time

SC = os.getcwd()
EMIT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "emit.py")
PY = SC + "/v/bin/python"
TOKEN = secrets.token_urlsafe(24)
LOG = SC + "/run_token.log"


def events():
    return open(LOG, encoding="utf-8").read().count("EventName: gen_ai.evaluation.result")


def case(name, proto, headers, expect_ok):
    before = events()
    env = {**os.environ, "OTLP_TIMEOUT": "4"}
    env.pop("OTEL_EXPORTER_OTLP_HEADERS", None)
    if headers is not None:
        env["OTEL_EXPORTER_OTLP_HEADERS"] = headers
    r = subprocess.run([PY, EMIT, proto], capture_output=True, text=True, timeout=120, env=env)
    time.sleep(0.8)
    got = events() - before
    ok = got >= 4
    out = (r.stderr + r.stdout)
    why = next((w for w in ("401", "Unauthenticated", "UNAUTHENTICATED", "403", "Unauthorized") if w in out), "")
    print(f"  [{'OK ' if ok == expect_ok else 'MAL'}] {name:<52} esperado={'pasa  ' if expect_ok else 'RECHAZA'} recibidos={got}  {('| ' + why) if (not ok and why) else ''}")
    return ok == expect_ok


p = subprocess.Popen([SC + "/contrib/otelcol-contrib", "--config", SC + "/cfg_token.yaml"], stdout=open(LOG, "w"), stderr=subprocess.STDOUT, env={**os.environ, "AIXL_TEST_TOKEN": TOKEN})
try:
    for _ in range(60):
        if "Everything is ready" in open(LOG).read():
            break
        time.sleep(0.5)
    else:
        print("el colector no arrancó:\n" + open(LOG).read()[-800:])
        sys.exit(2)
    listen = subprocess.run("lsof -nP -iTCP -sTCP:LISTEN | grep otelcol | awk '{print $9}' | tr '\\n' ' '", shell=True, capture_output=True, text=True).stdout.strip()
    print(f"colector contrib con bearertokenauth (escucha: {listen})")
    res = []
    for proto in ("http", "grpc"):
        res += [case(f"{proto}: token correcto", proto, f"Authorization=Bearer%20{TOKEN}", True),
                case(f"{proto}: sin token", proto, None, False),
                case(f"{proto}: token equivocado", proto, "Authorization=Bearer%20" + secrets.token_urlsafe(24), False),
                case(f"{proto}: token correcto con esquema Basic", proto, f"Authorization=Basic%20{TOKEN}", False)]
    print("\nRESULTADO:", "todos como se esperaba" if all(res) else "HAY CASOS MAL")
    sys.exit(0 if all(res) else 1)
finally:
    p.terminate()
    p.wait(timeout=10)
