"""End-to-end check of aixl.telemetry with the REAL OpenTelemetry SDK against a REAL collector. Usage: emit.py [http|grpc]  (http -> 127.0.0.1:4318, grpc -> 127.0.0.1:4317). See README.md in this folder."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from opentelemetry import metrics
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import SimpleLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource

PROTOCOL = sys.argv[1] if len(sys.argv) > 1 else "http"
if PROTOCOL == "grpc":
    from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    LOG_EXPORTER = lambda: OTLPLogExporter(endpoint="127.0.0.1:4317", insecure=True)                       # noqa: E731
    METRIC_EXPORTER = lambda: OTLPMetricExporter(endpoint="127.0.0.1:4317", insecure=True)                 # noqa: E731
else:
    from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
    LOG_EXPORTER = lambda: OTLPLogExporter(endpoint="http://127.0.0.1:4318/v1/logs")                       # noqa: E731
    METRIC_EXPORTER = lambda: OTLPMetricExporter(endpoint="http://127.0.0.1:4318/v1/metrics")              # noqa: E731

res = Resource.create({"service.name": "aixl-e2e-test-" + PROTOCOL})
lp = LoggerProvider(resource=res)
lp.add_log_record_processor(SimpleLogRecordProcessor(LOG_EXPORTER()))
set_logger_provider(lp)
mp = MeterProvider(resource=res, metric_readers=[PeriodicExportingMetricReader(METRIC_EXPORTER(), export_interval_millis=3_600_000)])
metrics.set_meter_provider(mp)

from aixl import telemetry as T

print("SDK real, transport", PROTOCOL, "; telemetry.available() =", T.available())
r1 = T.relay_check_evaluated("Send the report to Ana before Friday at 5 pm.", "Send the report to Luis before Monday.", response_id="resp-e2e-1")
r2 = T.relay_check_evaluated("Send the report to Ana.", "Send the report to Ana.")
r3 = T.compare_verified_evaluated("Elimina el reporte.", "No elimines el reporte.")
r4 = T.logic_compare_evaluated("It is not true that we ship and we invoice.", "We do not ship or we do not invoice.", response_id="resp-e2e-2")
print("relay violation ok?", r1["ok"], "| relay identical ok?", r2["ok"], "| compare verdict:", r3["verdict"], "| logic:", r4["verdict"])
print("force_flush logs:", lp.force_flush(), "| metrics:", mp.force_flush())
