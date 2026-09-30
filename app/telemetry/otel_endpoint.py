"""
otel_endpoint - single source of truth for resolving the OTLP protocol,
scheme, host, and port that OTEL_EXPORTER_OTLP_ENDPOINT/_INSECURE/_PROTOCOL
describe together.

Why this exists
----------------
Three independent settings jointly describe one thing - which collector to
talk to, and how:

    OTEL_EXPORTER_OTLP_ENDPOINT     host, or host:port, or scheme://host:port
    OTEL_EXPORTER_OTLP_INSECURE     "true"/"false"
    OTEL_EXPORTER_OTLP_PROTOCOL     "grpc" or "http/protobuf"

Resolving them used to happen inline in app/telemetry/configure.py, with the
scheme/port/protocol choice repeated wherever it was needed. This module
resolves all four (protocol, scheme, host, port) in one place, so
configure.py (and anything else that needs to know where the collector is)
calls one function instead of re-deriving the same defaults.

Defaulting rules
-----------------
OTEL_EXPORTER_OTLP_INSECURE selects the DEFAULT protocol/scheme/port - it is
a convenience default, not an override:

    insecure=true   -> protocol grpc,          scheme http,  port 4317
    insecure=false  -> protocol http/protobuf, scheme https, port 4318

Any of the three that is EXPLICITLY given always wins over the value
insecure would otherwise default it to:

    - OTEL_EXPORTER_OTLP_PROTOCOL, if set, is used regardless of insecure.
    - A scheme given in OTEL_EXPORTER_OTLP_ENDPOINT (e.g. "https://host") is
      used regardless of insecure.
    - A port given in OTEL_EXPORTER_OTLP_ENDPOINT (e.g. "host:9999") is used
      regardless of insecure.

Only a HOST is mandatory; nothing else can be defaulted (there is no sane
guess for "which collector"), so a missing or unparsable
OTEL_EXPORTER_OTLP_ENDPOINT is a hard OtelEndpointError, not a silent
fallback.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlsplit

GRPC_PROTOCOL = "grpc"
HTTP_PROTOCOL = "http/protobuf"

GRPC_DEFAULT_PORT = 4317
HTTP_DEFAULT_PORT = 4318

GRPC_DEFAULT_SCHEME = "http"
HTTP_DEFAULT_SCHEME = "https"


class OtelEndpointError(RuntimeError):
    """Raised when the OTLP endpoint cannot be resolved.

    Deliberately fatal: telemetry configuration that cannot determine where
    to send data should fail loudly at startup rather than silently produce
    a malformed or empty endpoint.
    """


@dataclass(frozen=True)
class ResolvedEndpoint:
    """The fully-resolved OTLP transport target."""

    protocol: str  # "grpc" or "http/protobuf"
    scheme: str  # "http" or "https"
    host: str
    port: int

    @property
    def base_endpoint(self) -> str:
        """The scheme://host:port base URL (no per-signal path)."""
        return f"{self.scheme}://{self.host}:{self.port}"


def resolve_endpoint(
    raw_endpoint: Optional[str],
    insecure: bool,
    explicit_protocol: Optional[str] = None,
) -> ResolvedEndpoint:
    """Resolve the OTLP protocol/scheme/host/port from the given settings.

    *raw_endpoint* is OTEL_EXPORTER_OTLP_ENDPOINT (already merged with the
    legacy OTEL_ENDPOINT fallback by the caller, if applicable). Accepts a
    bare host, "host:port", or a full "scheme://host[:port]" URL.

    Raises OtelEndpointError if no host can be determined, or if a given
    port is not a valid integer.
    """
    endpoint = (raw_endpoint or "").strip().rstrip("/")

    if not endpoint:
        raise OtelEndpointError(
            "OTEL_EXPORTER_OTLP_ENDPOINT (or OTEL_ENDPOINT) must be set - a "
            "collector host is required; only its scheme, port, and "
            "protocol are defaulted from OTEL_EXPORTER_OTLP_INSECURE."
        )

    default_scheme = GRPC_DEFAULT_SCHEME if insecure else HTTP_DEFAULT_SCHEME
    default_port = GRPC_DEFAULT_PORT if insecure else HTTP_DEFAULT_PORT
    default_protocol = GRPC_PROTOCOL if insecure else HTTP_PROTOCOL

    protocol = (explicit_protocol or "").strip().lower() or default_protocol

    if "://" in endpoint:
        parts = urlsplit(endpoint)
        scheme = parts.scheme or default_scheme
        host = parts.hostname or ""
        try:
            port = parts.port or default_port
        except ValueError as exc:
            raise OtelEndpointError(
                f"invalid port in OTEL_EXPORTER_OTLP_ENDPOINT={endpoint!r}: {exc}"
            ) from exc
    else:
        host, _, port_str = endpoint.partition(":")
        if port_str:
            try:
                port = int(port_str)
            except ValueError as exc:
                raise OtelEndpointError(
                    f"invalid port in OTEL_EXPORTER_OTLP_ENDPOINT={endpoint!r}: "
                    f"{port_str!r} is not a number"
                ) from exc
        else:
            port = default_port
        scheme = default_scheme

    if not host:
        raise OtelEndpointError(
            f"could not determine a collector host from "
            f"OTEL_EXPORTER_OTLP_ENDPOINT={endpoint!r}"
        )

    return ResolvedEndpoint(protocol=protocol, scheme=scheme, host=host, port=port)
