import pytest

from app.telemetry.otel_endpoint import (
    GRPC_PROTOCOL,
    HTTP_PROTOCOL,
    OtelEndpointError,
    resolve_endpoint,
)


#
# insecure=true -> defaults to grpc, scheme http, port 4317
#
def test_insecure_true_defaults_to_grpc():

    resolved = resolve_endpoint("dpn-otel-collector-health", insecure=True)

    assert resolved.protocol == GRPC_PROTOCOL
    assert resolved.scheme == "http"
    assert resolved.host == "dpn-otel-collector-health"
    assert resolved.port == 4317
    assert resolved.base_endpoint == "http://dpn-otel-collector-health:4317"


def test_insecure_true_with_host_only_still_defaults_port():

    resolved = resolve_endpoint("collector", insecure=True)

    assert resolved.port == 4317
    assert resolved.protocol == GRPC_PROTOCOL


#
# insecure=false -> defaults to http/protobuf, scheme https, port 4318
#
def test_insecure_false_defaults_to_http_protobuf():

    resolved = resolve_endpoint("dpn-otel-collector-health", insecure=False)

    assert resolved.protocol == HTTP_PROTOCOL
    assert resolved.scheme == "https"
    assert resolved.host == "dpn-otel-collector-health"
    assert resolved.port == 4318
    assert resolved.base_endpoint == "https://dpn-otel-collector-health:4318"


#
# explicit endpoint override - scheme/port given in the endpoint win over
# whatever insecure would otherwise default them to
#
def test_explicit_scheme_and_port_override_insecure_default():

    resolved = resolve_endpoint(
        "https://custom-collector:9999", insecure=True
    )

    assert resolved.scheme == "https"
    assert resolved.port == 9999
    assert resolved.host == "custom-collector"
    # protocol still defaults from insecure since it wasn't given explicitly
    assert resolved.protocol == GRPC_PROTOCOL


def test_explicit_port_without_scheme_overrides_default_port():

    resolved = resolve_endpoint("collector:4444", insecure=False)

    assert resolved.port == 4444
    assert resolved.scheme == "https"


def test_explicit_protocol_overrides_insecure_derived_default():

    resolved = resolve_endpoint(
        "collector", insecure=True, explicit_protocol="http/protobuf"
    )

    assert resolved.protocol == HTTP_PROTOCOL
    # scheme/port still default from insecure since only protocol was given
    assert resolved.scheme == "http"
    assert resolved.port == 4317


#
# missing/invalid configuration
#
def test_missing_endpoint_raises():

    with pytest.raises(OtelEndpointError):
        resolve_endpoint(None, insecure=True)


def test_blank_endpoint_raises():

    with pytest.raises(OtelEndpointError):
        resolve_endpoint("   ", insecure=False)


def test_invalid_port_in_host_colon_port_form_raises():

    with pytest.raises(OtelEndpointError):
        resolve_endpoint("collector:not-a-port", insecure=True)


def test_invalid_port_in_url_form_raises():

    with pytest.raises(OtelEndpointError):
        resolve_endpoint("https://collector:not-a-port", insecure=False)


def test_url_with_no_host_raises():

    with pytest.raises(OtelEndpointError):
        resolve_endpoint("https://:4318", insecure=False)
