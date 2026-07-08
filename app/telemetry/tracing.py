from opentelemetry import trace

""" from opentelemetry.sdk.trace import (
    TracerProvider
)
 
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor
)
 
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter
)
 
from app.telemetry.resource import resource
 
 
provider = TracerProvider(
    resource=resource
)
 
processor = BatchSpanProcessor(
    OTLPSpanExporter(
        endpoint="http://localhost:4317"
    )
)
 
provider.add_span_processor(
    processor
)
 
trace.set_tracer_provider(
    provider
) """

tracer = trace.get_tracer("file-scan-service")
