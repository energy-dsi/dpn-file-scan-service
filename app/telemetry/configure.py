"""
Configure OpenTelemetry.
"""

import logging
import os
from opentelemetry import metrics
from opentelemetry import trace
from opentelemetry._logs import set_logger_provider

from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter

from opentelemetry.sdk.metrics import MeterProvider

from opentelemetry.sdk.metrics.export import (
    PeriodicExportingMetricReader,
)

from opentelemetry.sdk.trace import TracerProvider

from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
)

from opentelemetry.sdk._logs import (
    LoggerProvider,
    LoggingHandler,
)
from opentelemetry.sdk._logs.export import (
    BatchLogRecordProcessor,
)

from app.telemetry.resource import resource
from app.telemetry import otel_truststore
from app.config.settings import Settings

_initialized = False


def configure_telemetry():
    """
    Configure OpenTelemetry exactly once.
    """

    global _initialized

    if _initialized:
        return

    #
    # Skip completely during tests
    #

    if Settings.TESTING:
        return

    if not Settings.ENABLE_TELEMETRY:
        return

    #
    # OTLP over HTTP/protobuf. The HTTP exporter uses an explicit per-signal
    # endpoint, so the base URL (https://<collector>:4318) must have the
    # signal path appended. TLS is verified against the provided CA
    # certificate (PEM); if none is set, the default certifi bundle is used.
    #

    base_endpoint = (Settings.OTEL_EXPORTER_OTLP_ENDPOINT or "").rstrip("/")

    if not base_endpoint:
        raise RuntimeError(
            "OTEL_EXPORTER_OTLP_ENDPOINT (or OTEL_ENDPOINT) must be set when "
            "telemetry is enabled."
        )

    # If a PKCS#12 truststore is present, extract its CA(s) to a temporary PEM
    # and repoint OTEL_EXPORTER_OTLP_CERTIFICATE at it. When no truststore is
    # found this is a no-op and the plain PEM CA (rootCA.crt) is used instead.
    otel_truststore.configure()

    # Read the CA path from the environment AFTER the truststore step, so the
    # extracted PEM wins; falls back to the configured rootCA.crt otherwise.
    certificate_file = os.getenv("OTEL_EXPORTER_OTLP_CERTIFICATE")

    #
    # Trace Provider
    #

    trace_provider = TracerProvider(resource=resource)

    trace_provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=f"{base_endpoint}/v1/traces",
                certificate_file=certificate_file,
            )
        )
    )

    trace.set_tracer_provider(trace_provider)

    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(
            endpoint=f"{base_endpoint}/v1/metrics",
            certificate_file=certificate_file,
        )
    )

    metrics.set_meter_provider(
        MeterProvider(
            resource=resource,
            metric_readers=[metric_reader],
        )
    )

    logger_provider = LoggerProvider(resource=resource)

    logger_provider.add_log_record_processor(
        BatchLogRecordProcessor(
            OTLPLogExporter(
                endpoint=f"{base_endpoint}/v1/logs",
                certificate_file=certificate_file,
            )
        )
    )

    set_logger_provider(logger_provider)

    #
    # Attach OpenTelemetry LoggingHandler
    #

    otel_handler = LoggingHandler(logger_provider=logger_provider)

    root_logger = logging.getLogger()

    root_logger.setLevel(logging.INFO)

    if not any(isinstance(handler, LoggingHandler) for handler in root_logger.handlers):
        root_logger.addHandler(otel_handler)

    _initialized = True

    logging.getLogger(__name__).info("OpenTelemetry configured successfully.")
