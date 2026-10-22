import json
from unittest.mock import MagicMock, patch

import pytest
from azure.servicebus import ServiceBusReceiveMode

from app.providers.azure.servicebus_client import (
    get_client,
    get_receiver,
    peek_messages,
    send_message,
)


# =====================================================
# Helper for OpenTelemetry Span
# =====================================================


def create_mock_span():

    span = MagicMock()

    cm = MagicMock()

    cm.__enter__.return_value = span

    cm.__exit__.return_value = None

    return cm


# =====================================================
# get_client()
# =====================================================


@patch("app.providers.azure.servicebus_client.logger")
@patch("app.providers.azure.servicebus_client.tracer")
@patch("app.providers.azure.servicebus_client.get_credential")
@patch("app.providers.azure.servicebus_client.ServiceBusClient")
@patch("app.providers.azure.servicebus_client.Settings")
def test_get_client(
    mock_settings,
    mock_servicebus_client,
    mock_get_credential,
    mock_tracer,
    mock_logger,
):

    mock_tracer.start_as_current_span.return_value = create_mock_span()

    mock_settings.SERVICE_BUS_NAMESPACE = "<<your specific value>>"

    credential = MagicMock()

    mock_get_credential.return_value = credential

    get_client()

    mock_servicebus_client.assert_called_once_with(
        fully_qualified_namespace="<<your specific value>>",
        credential=credential,
        transport_type=mock_servicebus_client.call_args.kwargs["transport_type"],
    )

    mock_logger.info.assert_called_once()


# =====================================================
# get_client exception
# =====================================================


@patch("app.providers.azure.servicebus_client.tracer")
@patch("app.providers.azure.servicebus_client.get_credential")
@patch("app.providers.azure.servicebus_client.ServiceBusClient")
def test_get_client_exception(
    mock_servicebus_client,
    mock_get_credential,
    mock_tracer,
):

    span = MagicMock()

    cm = MagicMock()

    cm.__enter__.return_value = span

    cm.__exit__.return_value = None

    mock_tracer.start_as_current_span.return_value = cm

    mock_get_credential.return_value = MagicMock()

    mock_servicebus_client.side_effect = RuntimeError("SB Error")

    with pytest.raises(RuntimeError):

        get_client()

    span.record_exception.assert_called_once()


# =====================================================
# get_receiver()
# =====================================================


@patch("app.providers.azure.servicebus_client.tracer")
@patch("app.providers.azure.servicebus_client.get_client")
def test_get_receiver(
    mock_get_client,
    mock_tracer,
):

    mock_tracer.start_as_current_span.return_value = create_mock_span()

    receiver = MagicMock()

    client = MagicMock()

    client.get_subscription_receiver.return_value = receiver

    mock_get_client.return_value = client

    result = get_receiver()

    assert result == receiver


@patch("app.providers.azure.servicebus_client.Settings")
@patch("app.providers.azure.servicebus_client.tracer")
@patch("app.providers.azure.servicebus_client.get_client")
def test_get_receiver_parameters(
    mock_get_client,
    mock_tracer,
    mock_settings,
):

    mock_tracer.start_as_current_span.return_value = create_mock_span()

    mock_settings.TOPIC_NAME = "topic"

    mock_settings.SUBSCRIPTION_NAME = "subscription"

    receiver = MagicMock()

    client = MagicMock()

    client.get_subscription_receiver.return_value = receiver

    mock_get_client.return_value = client

    get_receiver()

    client.get_subscription_receiver.assert_called_once_with(
        topic_name="topic",
        subscription_name="subscription",
        receive_mode=ServiceBusReceiveMode.PEEK_LOCK,
    )


# =====================================================
# send_message()
# =====================================================


@patch("app.providers.azure.servicebus_client.logger")
@patch("app.providers.azure.servicebus_client.tracer")
@patch("app.providers.azure.servicebus_client.ServiceBusMessage")
@patch("app.providers.azure.servicebus_client.get_client")
def test_send_message(
    mock_get_client,
    mock_message,
    mock_tracer,
    mock_logger,
):

    mock_tracer.start_as_current_span.return_value = create_mock_span()

    client = MagicMock()

    client.__enter__.return_value = client

    sender = MagicMock()

    sender.__enter__.return_value = sender

    client.get_topic_sender.return_value = sender

    mock_get_client.return_value = client

    payload = {"status": "OK"}

    send_message(payload)

    mock_message.assert_called_once_with(json.dumps(payload))

    sender.send_messages.assert_called_once()

    mock_logger.info.assert_called_once()


# =====================================================
# peek_messages()
# =====================================================


@patch("app.providers.azure.servicebus_client.tracer")
@patch("app.providers.azure.servicebus_client.get_client")
def test_peek_messages_success(
    mock_get_client,
    mock_tracer,
):

    mock_tracer.start_as_current_span.return_value = create_mock_span()

    client = MagicMock()

    client.__enter__.return_value = client

    receiver = MagicMock()

    receiver.__enter__.return_value = receiver

    client.get_subscription_receiver.return_value = receiver

    mock_get_client.return_value = client

    message = MagicMock()

    message.message_id = "1"

    message.sequence_number = 10

    message.delivery_count = 0

    message.body = [json.dumps({"status": "OK"}).encode()]

    receiver.peek_messages.return_value = [message]

    result = peek_messages()

    assert len(result) == 1

    assert result[0]["body"]["status"] == "OK"


@patch("app.providers.azure.servicebus_client.tracer")
@patch("app.providers.azure.servicebus_client.get_client")
def test_peek_messages_plain_text(
    mock_get_client,
    mock_tracer,
):

    mock_tracer.start_as_current_span.return_value = create_mock_span()

    client = MagicMock()

    client.__enter__.return_value = client

    receiver = MagicMock()

    receiver.__enter__.return_value = receiver

    client.get_subscription_receiver.return_value = receiver

    mock_get_client.return_value = client

    message = MagicMock()

    message.message_id = "1"

    message.sequence_number = 1

    message.delivery_count = 0

    message.body = [b"hello"]

    receiver.peek_messages.return_value = [message]

    result = peek_messages()

    assert result[0]["body"] == "hello"


@patch("app.providers.azure.servicebus_client.tracer")
@patch("app.providers.azure.servicebus_client.get_client")
def test_peek_messages_empty(
    mock_get_client,
    mock_tracer,
):

    mock_tracer.start_as_current_span.return_value = create_mock_span()

    client = MagicMock()

    client.__enter__.return_value = client

    receiver = MagicMock()

    receiver.__enter__.return_value = receiver

    receiver.peek_messages.return_value = []

    client.get_subscription_receiver.return_value = receiver

    mock_get_client.return_value = client

    assert peek_messages() == []


@patch("app.providers.azure.servicebus_client.tracer")
@patch("app.providers.azure.servicebus_client.get_client")
def test_peek_messages_exception(
    mock_get_client,
    mock_tracer,
):

    mock_tracer.start_as_current_span.return_value = create_mock_span()

    client = MagicMock()

    client.__enter__.return_value = client

    receiver = MagicMock()

    receiver.__enter__.return_value = receiver

    client.get_subscription_receiver.return_value = receiver

    mock_get_client.return_value = client

    message = MagicMock()

    type(message).body = property(
        lambda self: (_ for _ in ()).throw(Exception("Body Error"))
    )

    receiver.peek_messages.return_value = [message]

    with pytest.raises(Exception, match="Body Error"):

        peek_messages()


@patch("app.providers.azure.servicebus_client.tracer")
@patch("app.providers.azure.servicebus_client.get_client")
def test_peek_messages_max_count(
    mock_get_client,
    mock_tracer,
):

    mock_tracer.start_as_current_span.return_value = create_mock_span()

    client = MagicMock()

    client.__enter__.return_value = client

    receiver = MagicMock()

    receiver.__enter__.return_value = receiver

    receiver.peek_messages.return_value = []

    client.get_subscription_receiver.return_value = receiver

    mock_get_client.return_value = client

    peek_messages(max_count=5)

    receiver.peek_messages.assert_called_once_with(max_message_count=5)
