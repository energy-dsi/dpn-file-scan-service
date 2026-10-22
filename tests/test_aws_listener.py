from unittest.mock import MagicMock, patch

import pytest

from app.providers.aws.listener import (
    _handle_message,
    _poll_once,
    start_aws_listener,
)


#
# _handle_message() - happy path: process, count, delete
#
@patch("app.providers.aws.listener.delete_message")
@patch("app.providers.aws.listener.messages_processed")
@patch("app.providers.aws.listener.process_message")
def test_handle_message_success(mock_process, mock_processed, mock_delete):

    message = {"MessageId": "1", "ReceiptHandle": "rh-1"}

    _handle_message(message, MagicMock())

    mock_process.assert_called_once_with(message)

    mock_processed.add.assert_called_once_with(1)

    mock_delete.assert_called_once_with("rh-1")


#
# _handle_message() - processing fails but the message is still deleted
#
@patch("app.providers.aws.listener.delete_message")
@patch("app.providers.aws.listener.process_message")
def test_handle_message_processing_failure(mock_process, mock_delete):

    mock_process.side_effect = Exception("processing failed")

    message = {"MessageId": "1", "ReceiptHandle": "rh-1"}

    # Must not raise; the failure is logged and the message deleted.
    _handle_message(message, MagicMock())

    mock_delete.assert_called_once_with("rh-1")


#
# _handle_message() - deletion failure is recorded on the receive span
#
@patch("app.providers.aws.listener.delete_message")
@patch("app.providers.aws.listener.process_message")
def test_handle_message_delete_failure(mock_process, mock_delete):

    mock_delete.side_effect = Exception("delete failed")

    receive_span = MagicMock()

    message = {"MessageId": "1", "ReceiptHandle": "rh-1"}

    # Must not raise; the delete failure is logged on the receive span.
    _handle_message(message, receive_span)

    receive_span.record_exception.assert_called_once()

    receive_span.set_status.assert_called_once()


#
# _poll_once() - processes each received message
#
@patch("app.providers.aws.listener._handle_message")
@patch("app.providers.aws.listener.receive_messages")
def test_poll_once_with_messages(mock_receive, mock_handle):

    mock_receive.return_value = {
        "Messages": [{"MessageId": "1"}, {"MessageId": "2"}]
    }

    receive_span = MagicMock()

    _poll_once(receive_span)

    receive_span.set_attribute.assert_called_once_with("SQS.message_count", 2)

    assert mock_handle.call_count == 2


#
# _poll_once() - no messages: sleeps and returns without handling
#
@patch("app.providers.aws.listener.time.sleep")
@patch("app.providers.aws.listener._handle_message")
@patch("app.providers.aws.listener.receive_messages")
def test_poll_once_no_messages(mock_receive, mock_handle, mock_sleep):

    mock_receive.return_value = {}

    _poll_once(MagicMock())

    mock_sleep.assert_called_once_with(10)

    mock_handle.assert_not_called()


#
# start_aws_listener() - loop exits on a non-Exception (KeyboardInterrupt)
#
@patch("app.providers.aws.listener._poll_once")
def test_start_aws_listener_stops(mock_poll):

    mock_poll.side_effect = KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):

        start_aws_listener()

    mock_poll.assert_called_once()


#
# start_aws_listener() - transient Exception is caught, loop retries, then stops
#
@patch("app.providers.aws.listener.time.sleep")
@patch("app.providers.aws.listener._poll_once")
def test_start_aws_listener_retries_on_exception(mock_poll, mock_sleep):

    mock_poll.side_effect = [Exception("loop failed"), KeyboardInterrupt()]

    with pytest.raises(KeyboardInterrupt):

        start_aws_listener()

    assert mock_poll.call_count == 2

    # The retry sleep fires once (after the caught Exception, not the interrupt).
    mock_sleep.assert_called_once_with(10)
