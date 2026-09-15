"""
Configure OpenTelemetry.
"""

import logging
import os
import requests
from opentelemetry import metrics
from opentelemetry import trace
from opentelemetry._logs import set_logger_provider

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
from app.telemetry import otel_oauth
from app.telemetry.otel_endpoint import GRPC_PROTOCOL, resolve_endpoint
from app.config.settings import Settings

_initialized = False


def _build_http_exporters(resolved, certificate_file, oauth):
    """Build the trace/metric/log exporters for OTLP over HTTP/protobuf.

    The HTTP exporter needs an explicit per-signal endpoint (base URL +
    /v1/traces etc). Auth is attached via a `requests.Session` whose `auth`
    callable (ClientCredentialsAuth) is invoked fresh on every export, so the
    token is always current - unlike the gRPC path, which can only attach a
    static header (see _build_grpc_exporters).
    """
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
        OTLPSpanExporter,
    )
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
        OTLPMetricExporter,
    )
    from opentelemetry.exporter.otlp.proto.http._log_exporter import (
        OTLPLogExporter,
    )

    base_endpoint = resolved.base_endpoint

    def _session_with_auth() -> "requests.Session | None":
        if oauth is None:
            return None
        session = requests.Session()
        session.auth = oauth
        return session

    span_exporter = OTLPSpanExporter(
        endpoint=f"{base_endpoint}/v1/traces",
        certificate_file=certificate_file,
        session=_session_with_auth(),
    )

    metric_exporter = OTLPMetricExporter(
        endpoint=f"{base_endpoint}/v1/metrics",
        certificate_file=certificate_file,
        session=_session_with_auth(),
    )

    log_exporter = OTLPLogExporter(
        endpoint=f"{base_endpoint}/v1/logs",
        certificate_file=certificate_file,
        session=_session_with_auth(),
    )

    return span_exporter, metric_exporter, log_exporter


def _build_grpc_exporters(resolved, certificate_file, oauth):
    """Build the trace/metric/log exporters for OTLP over gRPC.

    Unlike the HTTP exporter, gRPC takes one shared endpoint (no per-signal
    path) and a boolean `insecure` flag rather than a scheme in the URL.
    `insecure` is derived from the resolved scheme (http -> insecure, https
    -> secure) rather than re-reading OTEL_EXPORTER_OTLP_INSECURE directly,
    so an explicit scheme in OTEL_EXPORTER_OTLP_ENDPOINT (which wins over
    the _INSECURE-derived default - see otel_endpoint.py) is respected here
    too. TLS trust is a `grpc.ChannelCredentials` object built from the CA's
    PEM bytes, not a file path.

    OAuth is attached as a STATIC header fetched once at startup - the gRPC
    exporter only accepts a fixed headers dict/tuple at construction time, it
    never calls back for a fresh token per-request the way the HTTP path's
    `requests.Session.auth` does. A token that expires mid-run will start
    failing exports with an auth error until the process restarts; there is
    no live refresh for gRPC here.
    """
    import grpc
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
        OTLPSpanExporter,
    )
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
        OTLPMetricExporter,
    )
    from opentelemetry.exporter.otlp.proto.grpc._log_exporter import (
        OTLPLogExporter,
    )

    base_endpoint = resolved.base_endpoint
    insecure = resolved.scheme == "http"

    credentials = None
    if not insecure:
        if not certificate_file:
            raise RuntimeError(
                "OTEL_EXPORTER_OTLP_INSECURE is false (TLS) but no CA "
                "certificate is available; set OTEL_EXPORTER_OTLP_CERTIFICATE "
                "or a truststore (TRUSTSTORE_PATH)."
            )
        with open(certificate_file, "rb") as handle:
            root_certificates = handle.read()
        credentials = grpc.ssl_channel_credentials(root_certificates=root_certificates)

    headers = otel_oauth.bearer_header_tuple(oauth)

    span_exporter = OTLPSpanExporter(
        endpoint=base_endpoint,
        insecure=insecure,
        credentials=credentials,
        headers=headers,
    )

    metric_exporter = OTLPMetricExporter(
        endpoint=base_endpoint,
        insecure=insecure,
        credentials=credentials,
        headers=headers,
    )

    log_exporter = OTLPLogExporter(
        endpoint=base_endpoint,
        insecure=insecure,
        credentials=credentials,
        headers=headers,
    )

    return span_exporter, metric_exporter, log_exporter


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

    # Make the resolved-endpoint log call below actually visible: raise the
    # root logger to INFO, and give it a console handler if it has none yet
    # (the OTEL LoggingHandler is only attached further down, once the log
    # exporter exists - too late for this startup-validation log). Without
    # both a level AND a handler here, the record is silently dropped
    # (Python's "handler of last resort" only surfaces WARNING+), defeating
    # the "log resolved protocol/host/port/endpoint at startup" requirement.
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    if not root_logger.handlers:
        root_logger.addHandler(logging.StreamHandler())

    #
    # Protocol/scheme/host/port, all resolved in one place (see
    # app/telemetry/otel_endpoint.py). TLS is verified against the provided
    # CA certificate; if none is set, the default certifi bundle is used.
    #

    resolved = resolve_endpoint(
        Settings.OTEL_EXPORTER_OTLP_ENDPOINT,
        Settings.OTEL_EXPORTER_OTLP_INSECURE,
        Settings.OTEL_EXPORTER_OTLP_PROTOCOL,
    )
    base_endpoint = resolved.base_endpoint

    logging.getLogger(__name__).info(
        "OpenTelemetry OTLP target resolved: protocol=%s host=%s port=%s endpoint=%s",
        resolved.protocol,
        resolved.host,
        resolved.port,
        base_endpoint,
    )

    # If a PKCS#12 truststore is present, extract its CA(s) to a temporary PEM
    # and repoint OTEL_EXPORTER_OTLP_CERTIFICATE at it. When no truststore is
    # found this is a no-op and the plain PEM CA (rootCA.crt) is used instead.
    otel_truststore.configure()

    # Read the CA path from the environment AFTER the truststore step, so the
    # extracted PEM wins; falls back to the configured rootCA.crt otherwise.
    certificate_file = os.getenv("OTEL_EXPORTER_OTLP_CERTIFICATE")

    # OAuth2 client-credentials auth against Keycloak. None (no-op) when
    # unset. Shared across all three exporters so they reuse one cached
    # token instead of each fetching their own (relevant for the HTTP path's
    # per-request refresh; the gRPC path only reads it once - see
    # _build_grpc_exporters).
    oauth = otel_oauth.build_auth(verify=certificate_file or True)

    # Protocol selection: "grpc" -> port 4317-style gRPC transport, anything
    # else (default "http/protobuf", per the OTel spec default) -> HTTP. The
    # protocol is already fully resolved in `resolved.protocol` (explicit
    # OTEL_EXPORTER_OTLP_PROTOCOL wins, else defaulted from
    # OTEL_EXPORTER_OTLP_INSECURE - see otel_endpoint.py), so this is a
    # straight comparison rather than re-reading/parsing Settings directly.
    use_grpc = resolved.protocol == GRPC_PROTOCOL

    if use_grpc:
        span_exporter, metric_exporter, log_exporter = _build_grpc_exporters(
            resolved, certificate_file, oauth
        )
    else:
        span_exporter, metric_exporter, log_exporter = _build_http_exporters(
            resolved, certificate_file, oauth
        )

    #
    # Trace Provider
    #

    trace_provider = TracerProvider(resource=resource)
    trace_provider.add_span_processor(BatchSpanProcessor(span_exporter))
    trace.set_tracer_provider(trace_provider)

    #
    # Metric Provider
    #

    metric_reader = PeriodicExportingMetricReader(metric_exporter)

    metrics.set_meter_provider(
        MeterProvider(
            resource=resource,
            metric_readers=[metric_reader],
        )
    )

    #
    # Logger Provider
    #

    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
    set_logger_provider(logger_provider)

    #
    # Attach OpenTelemetry LoggingHandler
    #

    otel_handler = LoggingHandler(logger_provider=logger_provider)

    root_logger = logging.getLogger()

    if not any(isinstance(handler, LoggingHandler) for handler in root_logger.handlers):
        root_logger.addHandler(otel_handler)

    _initialized = True

    logging.getLogger(__name__).info("OpenTelemetry configured successfully.")
