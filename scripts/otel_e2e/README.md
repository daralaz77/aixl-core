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
