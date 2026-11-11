from unittest.mock import MagicMock, patch

import pytest

import app.telemetry.configure as configure_module
from app.telemetry.otel_endpoint import OtelEndpointError


def _reset_initialized():
    configure_module._initialized = False


#
# insecure=true -> gRPC builder used, with the resolved grpc/4317 endpoint
#
@patch("app.telemetry.configure._build_http_exporters")
@patch("app.telemetry.configure._build_grpc_exporters")
@patch("app.telemetry.configure.otel_oauth.build_auth", return_value=None)
@patch("app.telemetry.configure.otel_truststore.configure")
def test_insecure_true_uses_grpc_builder(
    mock_truststore, mock_build_auth, mock_grpc_builder, mock_http_builder
):
    _reset_initialized()
    mock_grpc_builder.return_value = (MagicMock(), MagicMock(), MagicMock())

    with patch.object(configure_module.Settings, "TESTING", False), patch.object(
        configure_module.Settings, "ENABLE_TELEMETRY", True
    ), patch.object(
        configure_module.Settings, "OTEL_EXPORTER_OTLP_ENDPOINT", "collector"
    ), patch.object(
        configure_module.Settings, "OTEL_EXPORTER_OTLP_INSECURE", True
    ), patch.object(
        configure_module.Settings, "OTEL_EXPORTER_OTLP_PROTOCOL", None
    ):
        configure_module.configure_telemetry()

    mock_grpc_builder.assert_called_once()
    mock_http_builder.assert_not_called()

    resolved_arg = mock_grpc_builder.call_args[0][0]
    assert resolved_arg.protocol == "grpc"
    assert resolved_arg.scheme == "http"
    assert resolved_arg.port == 4317


#
# insecure=false -> HTTP builder used, with the resolved http/protobuf/4318
# endpoint
#
@patch("app.telemetry.configure._build_http_exporters")
@patch("app.telemetry.configure._build_grpc_exporters")
@patch("app.telemetry.configure.otel_oauth.build_auth", return_value=None)
@patch("app.telemetry.configure.otel_truststore.configure")
def test_insecure_false_uses_http_builder(
    mock_truststore, mock_build_auth, mock_grpc_builder, mock_http_builder
):
    _reset_initialized()
    mock_http_builder.return_value = (MagicMock(), MagicMock(), MagicMock())

    with patch.object(configure_module.Settings, "TESTING", False), patch.object(
        configure_module.Settings, "ENABLE_TELEMETRY", True
    ), patch.object(
        configure_module.Settings, "OTEL_EXPORTER_OTLP_ENDPOINT", "collector"
    ), patch.object(
        configure_module.Settings, "OTEL_EXPORTER_OTLP_INSECURE", False
    ), patch.object(
        configure_module.Settings, "OTEL_EXPORTER_OTLP_PROTOCOL", None
    ):
        configure_module.configure_telemetry()

    mock_http_builder.assert_called_once()
    mock_grpc_builder.assert_not_called()

    resolved_arg = mock_http_builder.call_args[0][0]
    assert resolved_arg.protocol == "http/protobuf"
    assert resolved_arg.scheme == "https"
    assert resolved_arg.port == 4318


#
# explicit endpoint override (scheme + port) takes precedence over the
# insecure-derived default, even though the protocol still follows insecure
#
@patch("app.telemetry.configure._build_http_exporters")
@patch("app.telemetry.configure._build_grpc_exporters")
@patch("app.telemetry.configure.otel_oauth.build_auth", return_value=None)
@patch("app.telemetry.configure.otel_truststore.configure")
def test_explicit_endpoint_scheme_and_port_override_insecure_default(
    mock_truststore, mock_build_auth, mock_grpc_builder, mock_http_builder
):
    _reset_initialized()
    mock_grpc_builder.return_value = (MagicMock(), MagicMock(), MagicMock())

    with patch.object(configure_module.Settings, "TESTING", False), patch.object(
        configure_module.Settings, "ENABLE_TELEMETRY", True
    ), patch.object(
        configure_module.Settings,
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "https://collector:9999",
    ), patch.object(
        configure_module.Settings, "OTEL_EXPORTER_OTLP_INSECURE", True
    ), patch.object(
        configure_module.Settings, "OTEL_EXPORTER_OTLP_PROTOCOL", None
    ):
        configure_module.configure_telemetry()

    resolved_arg = mock_grpc_builder.call_args[0][0]
    assert resolved_arg.scheme == "https"
    assert resolved_arg.port == 9999
    assert resolved_arg.base_endpoint == "https://collector:9999"


#
# explicit OTEL_EXPORTER_OTLP_PROTOCOL override takes precedence over what
# insecure would otherwise select
#
@patch("app.telemetry.configure._build_http_exporters")
@patch("app.telemetry.configure._build_grpc_exporters")
@patch("app.telemetry.configure.otel_oauth.build_auth", return_value=None)
@patch("app.telemetry.configure.otel_truststore.configure")
def test_explicit_protocol_override_wins_over_insecure_default(
    mock_truststore, mock_build_auth, mock_grpc_builder, mock_http_builder
):
    _reset_initialized()
    mock_http_builder.return_value = (MagicMock(), MagicMock(), MagicMock())

    with patch.object(configure_module.Settings, "TESTING", False), patch.object(
        configure_module.Settings, "ENABLE_TELEMETRY", True
    ), patch.object(
        configure_module.Settings, "OTEL_EXPORTER_OTLP_ENDPOINT", "collector"
    ), patch.object(
        configure_module.Settings, "OTEL_EXPORTER_OTLP_INSECURE", True
    ), patch.object(
        configure_module.Settings, "OTEL_EXPORTER_OTLP_PROTOCOL", "http/protobuf"
    ):
        configure_module.configure_telemetry()

    mock_http_builder.assert_called_once()
    mock_grpc_builder.assert_not_called()


#
# missing/invalid configuration fails fast at startup, before any exporter
# is built
#
@patch("app.telemetry.configure._build_http_exporters")
@patch("app.telemetry.configure._build_grpc_exporters")
@patch("app.telemetry.configure.otel_truststore.configure")
def test_missing_endpoint_raises_at_startup(
    mock_truststore, mock_grpc_builder, mock_http_builder
):
    _reset_initialized()

    with patch.object(configure_module.Settings, "TESTING", False), patch.object(
        configure_module.Settings, "ENABLE_TELEMETRY", True
    ), patch.object(
        configure_module.Settings, "OTEL_EXPORTER_OTLP_ENDPOINT", None
    ), patch.object(
        configure_module.Settings, "OTEL_EXPORTER_OTLP_INSECURE", True
    ), patch.object(
        configure_module.Settings, "OTEL_EXPORTER_OTLP_PROTOCOL", None
    ):
        with pytest.raises(OtelEndpointError):
            configure_module.configure_telemetry()

    mock_grpc_builder.assert_not_called()
    mock_http_builder.assert_not_called()


#
# gRPC builder requires a CA certificate when the resolved scheme is secure
# (https) - an explicit https override with insecure=true and no
# certificate must still fail rather than silently connecting without TLS
# trust
#
def test_grpc_builder_requires_certificate_when_secure():
    from app.telemetry.configure import _build_grpc_exporters
    from app.telemetry.otel_endpoint import resolve_endpoint

    resolved = resolve_endpoint("https://collector:9999", insecure=True)

    with pytest.raises(RuntimeError):
        _build_grpc_exporters(resolved, None, None)
