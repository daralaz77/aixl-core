# aixl.telemetry end to end: real SDK -> real collector, OTLP/HTTP and OTLP/gRPC (verified 2026-10-30)

Not part of the test suite (it needs downloads and a collector). To reproduce, in an ISOLATED virtual environment and a scratch folder:
```bash
python3 -m venv v && v/bin/pip install "opentelemetry-sdk==1.45.0" "opentelemetry-exporter-otlp-proto-http==1.45.0"
# official collector (macOS arm64 shown), CHECK THE SUM before running it
BASE=https://github.com/open-telemetry/opentelemetry-collector-releases/releases/download/v0.164.0
curl -sLO "$BASE/otelcol_0.164.0_darwin_arm64.tar.gz" && curl -sLO "$BASE/otelcol_0.164.0_darwin_arm64.tar.gz.sha256"
shasum -a 256 otelcol_0.164.0_darwin_arm64.tar.gz     # must equal the number in the .sha256 file
mkdir bin && tar -xzf otelcol_0.164.0_darwin_arm64.tar.gz -C bin
bin/otelcol --config collector.yaml > collector.log 2>&1 &     # listens on 127.0.0.1 ONLY; debug exporter prints what it receives
v/bin/python emit.py http                                      # the SDK emits 4 evaluations over OTLP/HTTP; then read collector.log
```
Result of the verified run: 4 events with `EventName: gen_ai.evaluation.result`, attributes `gen_ai.evaluation.name`, `gen_ai.evaluation.score.label` (violation / ok / not_equivalent / equivalent_logic), `gen_ai.evaluation.explanation`,
`gen_ai.response.id` (when given) and the `aixl.*` ones; `gen_ai.evaluation.score.value` absent on purpose; the counter `aixl.evaluations` arrived by OTLP metrics; none of the words of the evaluated texts appeared among the 65 attribute values received.

## gRPC
Add the exporter (`v/bin/pip install "opentelemetry-exporter-otlp-proto-grpc==1.45.0"`, which brings `grpcio`), start the collector with `collector_grpc.yaml` (a gRPC receiver ONLY, on 127.0.0.1:4317: no HTTP server exists, so whatever
arrives came over gRPC) and run `v/bin/python emit.py grpc`. Verified run: same 4 `gen_ai.evaluation.result` events, same attributes, the `aixl.evaluations` counter, and none of the words of the texts among the 65 attribute values.

## TLS and mutual TLS (verified 2026-10-30)
`make_certs.sh <dir> [lan-ip]` builds a throw-away CA, a server certificate (SAN: localhost, 127.0.0.1 and the LAN address) and a client certificate. Start the collector with `cfg_tls.yaml.example` (TLS) or `cfg_mtls.yaml.example` (client certificate REQUIRED) after replacing `<scratch>`,
and set `OTLP_TLS_CA` (turns TLS on), `OTLP_TLS_CERT` + `OTLP_TLS_KEY` (client certificate) and `OTLP_HOST` for `emit.py`; `tls_matrix.py` runs the 13 cases (valid ones must arrive, wrong ones must be refused) against a real collector.

## A real backend: Grafana Loki (verified 2026-10-30)
Loki 3.7.9 (single binary, loopback only, filesystem storage, `auth_enabled: false`; SHA-256 checked against the release's `SHA256SUMS`) accepts OTLP logs at `/otlp/v1/logs`: `OTLP_HTTP_BASE=http://127.0.0.1:3100/otlp OTLP_LOGS_ONLY=1 python emit.py http` (Loki has no OTLP metrics endpoint).
Query with the HTTP API (`/loki/api/v1/query_range`, header `X-Loki-Response-Encoding-Flags: categorize-labels` to see structured metadata) or LogQL, e.g. `{service_name="..."} | gen_ai_evaluation_score_label="violation"`.

`loki.yaml` in this folder is the configuration used for that run (loopback only, filesystem storage, `auth_enabled: false`, `allow_structured_metadata: true`). Re-run of 2026-11-01: the readable body (`<name>: <label> — <explanation>`) arrives as the stored log line; start Loki with `-config.file=loki.yaml`. `emit.py` finds the `aixl` package relative to its own location, so if you copy it elsewhere set `PYTHONPATH` to the repo root.

## Bearer-token authentication (verified 2026-11-03)
`otelcol-contrib` 0.164.0 (SHA-256 checked) with the `bearertokenauth` extension on BOTH receivers (`cfg_token.yaml.example`, token from the environment). `token_matrix.py` (run it from a scratch folder holding `v/`, `contrib/otelcol-contrib` and `cfg_token.yaml`) starts it with a random token and runs 8 cases over HTTP and gRPC: the right token arrives (4 events each);
no token, a wrong token and the right token under the `Basic` scheme are all refused (401 / UNAUTHENTICATED) and nothing arrives. The SDK sends the token through `OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer%20<token>"` (the space URL-encoded). 8 of 8 as expected. Loopback only.

## A second backend: VictoriaLogs v1.53.0 (verified 2026-11-03)
Single binary (SHA-256 checked), `-httpListenAddr=127.0.0.1:9428`; logs go to `OTLP_HTTP_BASE=http://127.0.0.1:9428/insert/opentelemetry OTLP_LOGS_ONLY=1 python emit.py http`, query `/select/logsql/query` or the built-in UI at `/select/vmui/`. The readable body is the stored message in the UI. Unlike Loki it KEEPS the dotted attribute names and the event name (`event_name="gen_ai.evaluation.result"`).

## Grafana 13.3.0 UI over Loki (verified 2026-11-03)
Grafana (SHA-256 checked) on `127.0.0.1:3000` with anonymous access (`GF_AUTH_ANONYMOUS_ENABLED=true`, `GF_AUTH_ANONYMOUS_ORG_ROLE=Admin`, `GF_AUTH_DISABLE_LOGIN_FORM=true`) and a provisioned Loki datasource (`http://127.0.0.1:3100`): Explore with `{service_name=~".+"} | gen_ai_evaluation_name=~"aixl.*"` shows the 4 readable lines.
**Found here, fixed:** with no severity, Loki guessed the level from the text and showed `aixl.relay_check: ok — no critical slot ...` as CRITICAL. The event now carries an explicit severity (WARN when a difference was found, INFO otherwise); re-run: `info / warn / info / warn`.

