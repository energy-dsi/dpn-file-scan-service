from opentelemetry import metrics

""" from opentelemetry.sdk.metrics import (
    MeterProvider
)
 
from opentelemetry.sdk.metrics.export import (
    PeriodicExportingMetricReader
)
 
from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
    OTLPMetricExporter
)
 
from app.telemetry.resource import resource
 
 
reader = PeriodicExportingMetricReader(
    OTLPMetricExporter(
        endpoint="http://localhost:4317"
    )
)
 
provider = MeterProvider(
    resource=resource,
    metric_readers=[reader]
)
 
metrics.set_meter_provider(
    provider
) """

meter = metrics.get_meter("file-scan-service")

messages_counter = meter.create_counter("messages_processed")

files_counter = meter.create_counter("files_copied")

malware_counter = meter.create_counter("malicious_files")

processing_time = meter.create_histogram("processing_duration_ms")

heartbeat_counter = meter.create_counter(
    name="heartbeat_total", description="Heartbeat count", unit="1"
)
