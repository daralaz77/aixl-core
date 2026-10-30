import os
import re
import subprocess
import time

"""TLS / mTLS matrix: starts a REAL collector with each cfg_<name>.yaml, runs the emit.py cases (the ones that must pass AND the ones that must be refused) and counts what the collector received.
Run it from a scratch folder that holds venv_dir/v, tls/ (make_certs.sh), collector_dl/bin/otelcol and the three cfg_*.yaml (see README.md)."""
SC = os.getcwd(); T = SC + "/tls"; PY = SC + "/venv_dir/v/bin/python"; EMIT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "emit.py")
LAN = open(T + "/lan_ip.txt").read().strip()
def events(log): return open(log, encoding="utf-8").read().count("EventName: gen_ai.evaluation.result")
def run_case(log, name, proto, env, host, expect_ok):
    before = events(log)
    e = dict(os.environ, OTLP_TIMEOUT="4", OTLP_HOST=host, **env)
    r = subprocess.run([PY, EMIT, proto], capture_output=True, text=True, timeout=120, env=e)
    time.sleep(0.8)
    got = events(log) - before
    err = ""
    m = re.findall(r"(SSLError[^\n]{0,90}|certificate verify failed[^\n]{0,60}|UNAVAILABLE[^\n]{0,70}|Connection refused[^\n]{0,40}|handshake[^\n]{0,60}|Max retries[^\n]{0,40}|bad certificate[^\n]{0,40}|tlsv13 alert[^\n]{0,50}|Failed to export[^\n]{0,70})", r.stderr + r.stdout)
    err = (m[0] if m else "")[:90]
    ok = got >= 4
    verdict = "OK " if ok == expect_ok else "MAL"
    print(f"  [{verdict}] {name:<46} esperado={'pasa  ' if expect_ok else 'RECHAZA'} recibidos={got}  {('| ' + err) if (not ok and err) else ''}")
    return ok == expect_ok
def with_collector(cfg, cases):
    log = f"{SC}/run_{cfg}.log"
    p = subprocess.Popen([SC + "/collector_dl/bin/otelcol", "--config", f"{SC}/cfg_{cfg}.yaml"], stdout=open(log, "w"), stderr=subprocess.STDOUT)
    try:
        for _ in range(40):
            if "Everything is ready" in open(log).read(): break
            time.sleep(0.5)
        listen = subprocess.run("lsof -nP -iTCP -sTCP:LISTEN | grep otelcol | awk '{print $9}' | tr '\\n' ' '", shell=True, capture_output=True, text=True).stdout.strip()
        print(f"\n== colector con {cfg}  (escucha: {listen})")
        return all([run_case(log, *c) for c in cases])
    finally:
        p.terminate(); p.wait(timeout=10)
CA = {"OTLP_TLS_CA": T + "/ca.pem"}; CLI = {"OTLP_TLS_CERT": T + "/client.pem", "OTLP_TLS_KEY": T + "/client.key"}
res = []
res.append(with_collector("tls", [
    ("http + TLS confiando en la CA", "http", CA, "127.0.0.1", True), ("grpc + TLS confiando en la CA", "grpc", CA, "127.0.0.1", True),
    ("http + TLS SIN confiar en la CA (raíces del sistema)", "http", {"OTLP_TLS": "1"}, "127.0.0.1", False), ("grpc + TLS SIN confiar en la CA", "grpc", {"OTLP_TLS": "1"}, "127.0.0.1", False),
    ("http en claro hacia un puerto TLS", "http", {}, "127.0.0.1", False), ("grpc en claro hacia un puerto TLS", "grpc", {}, "127.0.0.1", False)]))
res.append(with_collector("mtls", [
    ("http mTLS con certificado de cliente", "http", {**CA, **CLI}, "127.0.0.1", True), ("grpc mTLS con certificado de cliente", "grpc", {**CA, **CLI}, "127.0.0.1", True),
    ("http TLS SIN certificado de cliente", "http", CA, "127.0.0.1", False), ("grpc TLS SIN certificado de cliente", "grpc", CA, "127.0.0.1", False)]))
if LAN:
    res.append(with_collector("mtls_lan", [
        (f"http mTLS por la IP de la red {LAN}", "http", {**CA, **CLI}, LAN, True), (f"grpc mTLS por la IP de la red {LAN}", "grpc", {**CA, **CLI}, LAN, True),
        ("http a loopback (el colector NO escucha ahí)", "http", {**CA, **CLI}, "127.0.0.1", False)]))
print("\nRESULTADO GLOBAL:", "todos los casos se comportaron como se esperaba" if all(res) else "HAY CASOS INESPERADOS")
