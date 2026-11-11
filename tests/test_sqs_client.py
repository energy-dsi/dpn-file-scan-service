from unittest.mock import MagicMock, patch

from app.providers.aws import sqs_client
from app.providers.aws.sqs_client import (
    get_sqs,
    get_queue_url,
    receive_messages,
    delete_message,
)


#
# get_sqs() — the boto3 client is created once and cached (lru_cache).
#
@patch("app.providers.aws.sqs_client.get_sqs_client")
def test_get_sqs_creates_and_caches_client(mock_get_sqs_client):

    get_sqs.cache_clear()

    client = MagicMock()

    mock_get_sqs_client.return_value = client

    first = get_sqs()

    second = get_sqs()

    assert first is client

    assert second is client

    # Cached: the underlying factory is called only once for repeated calls.
    mock_get_sqs_client.assert_called_once()

    get_sqs.cache_clear()


#
# get_queue_url() — resolves the queue URL from the configured queue name.
#
@patch("app.providers.aws.sqs_client.get_sqs")
def test_get_queue_url(mock_get_sqs):

    sqs = MagicMock()

    sqs.get_queue_url.return_value = {"QueueUrl": "https://sqs.local/my-queue"}

    mock_get_sqs.return_value = sqs

    with patch.object(sqs_client.Settings, "SQS_QUEUE", "my-queue"):

        url = get_queue_url()

    assert url == "https://sqs.local/my-queue"

    sqs.get_queue_url.assert_called_once_with(QueueName="my-queue")


#
# receive_messages() — polls the resolved queue URL for a single message.
#
@patch("app.providers.aws.sqs_client.get_queue_url")
@patch("app.providers.aws.sqs_client.get_sqs")
def test_receive_messages(mock_get_sqs, mock_get_queue_url):

    sqs = MagicMock()

    sqs.receive_message.return_value = {"Messages": [{"MessageId": "1"}]}

    mock_get_sqs.return_value = sqs

    mock_get_queue_url.return_value = "https://sqs.local/my-queue"

    result = receive_messages()

    assert result == {"Messages": [{"MessageId": "1"}]}

    sqs.receive_message.assert_called_once_with(
        QueueUrl="https://sqs.local/my-queue",
        MaxNumberOfMessages=1,
        WaitTimeSeconds=10,
    )


#
# delete_message() — deletes a message using its receipt handle.
#
@patch("app.providers.aws.sqs_client.get_queue_url")
@patch("app.providers.aws.sqs_client.get_sqs")
def test_delete_message(mock_get_sqs, mock_get_queue_url):

    sqs = MagicMock()

    mock_get_sqs.return_value = sqs

    mock_get_queue_url.return_value = "https://sqs.local/my-queue"

    delete_message("receipt-123")

    sqs.delete_message.assert_called_once_with(
        QueueUrl="https://sqs.local/my-queue",
        ReceiptHandle="receipt-123",
    )
