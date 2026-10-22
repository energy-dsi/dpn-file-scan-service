from unittest.mock import MagicMock, patch

from app.providers.azure.listener import start_azure_listener


@patch("app.providers.azure.listener.get_blob_service")
@patch("app.providers.azure.listener.process_message")
@patch("app.providers.azure.listener.get_receiver")
def test_start_azure_listener_success(
    mock_get_receiver, mock_process_message, mock_get_blob_service
):

    message = MagicMock()

    message.body = [
        b'{"subject":"https://storage/container/blobs/test.txt",  "data":{"scanResultType":"Success"}}'
    ]

    receiver = MagicMock()

    receiver.receive_messages.side_effect = [[message], KeyboardInterrupt()]

    receiver.__enter__.return_value = receiver

    mock_get_receiver.return_value = receiver

    blob_client = MagicMock()
    blob_client.exists.return_value = True

    service_client = MagicMock()
    service_client.get_blob_client.return_value = blob_client

    mock_get_blob_service.return_value = service_client

    try:
        start_azure_listener()
    except KeyboardInterrupt:
        pass

    mock_process_message.assert_called_once_with(message)
    receiver.complete_message.assert_called_once_with(message)


@patch("app.providers.azure.listener.get_blob_service")
@patch("app.providers.azure.listener.process_message")
@patch("app.providers.azure.listener.get_receiver")
def test_start_azure_listener_failure(
    mock_get_receiver, mock_process_message, mock_get_blob_service
):

    message = MagicMock()

    message.body = [
        b'{"subject":"https://storage/container/blobs/test.txt",  "data":{"scanResultType":"Failed"}}'
    ]

    receiver = MagicMock()

    receiver.receive_messages.side_effect = [[message], KeyboardInterrupt()]

    receiver.__enter__.return_value = receiver

    mock_get_receiver.return_value = receiver

    blob_client = MagicMock()
    blob_client.exists.return_value = True

    service_client = MagicMock()
    service_client.get_blob_client.return_value = blob_client

    mock_get_blob_service.return_value = service_client

    try:
        start_azure_listener()
    except KeyboardInterrupt:
        pass

    mock_process_message.assert_called_once_with(message)
    receiver.complete_message.assert_called_once_with(message)


@patch("app.providers.azure.listener.process_message")
@patch("app.providers.azure.listener.get_receiver")
def test_receive_messages_called(mock_get_receiver, mock_process_message):

    receiver = MagicMock()

    receiver.receive_messages.side_effect = [[], KeyboardInterrupt()]

    receiver.__enter__.return_value = receiver

    mock_get_receiver.return_value = receiver

    try:
        start_azure_listener()
    except KeyboardInterrupt:
        pass

    receiver.receive_messages.assert_called_with(max_message_count=10, max_wait_time=5)


@patch("app.providers.azure.listener.get_receiver")
def test_receiver_created(mock_get_receiver):

    receiver = MagicMock()

    receiver.receive_messages.side_effect = KeyboardInterrupt()

    receiver.__enter__.return_value = receiver

    mock_get_receiver.return_value = receiver

    try:
        start_azure_listener()
    except KeyboardInterrupt:
        pass

    mock_get_receiver.assert_called_once()
