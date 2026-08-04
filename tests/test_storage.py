from unittest.mock import MagicMock, patch

from app.providers.azure.storage_client import get_blob_service, list_blobs


@patch("app.providers.azure.storage_client.get_credential")
@patch("app.providers.azure.storage_client.BlobServiceClient")
def test_get_blob_service(mock_blob_service_client, mock_get_credential):

    mock_credential = MagicMock()

    mock_get_credential.return_value = mock_credential

    get_blob_service("storageaccount01")

    mock_blob_service_client.assert_called_once_with(
        account_url="<<your specific value>>",
        credential=mock_credential,
    )


@patch("app.providers.azure.storage_client.get_blob_service")
def test_list_blobs(mock_get_blob_service):

    blob1 = MagicMock()

    blob1.name = "file1.txt"

    blob1.size = 100

    blob1.last_modified = "2026-06-19"

    blob2 = MagicMock()

    blob2.name = "file2.pdf"

    blob2.size = 200

    blob2.last_modified = "2026-06-20"

    container_client = MagicMock()

    container_client.list_blobs.return_value = [blob1, blob2]

    blob_service = MagicMock()

    blob_service.get_container_client.return_value = container_client

    mock_get_blob_service.return_value = blob_service

    result = list_blobs("outbound-container")

    assert len(result) == 2

    assert result[0]["file_name"] == ("file1.txt")

    assert result[0]["size"] == 100

    assert result[1]["file_name"] == ("file2.pdf")

    assert result[1]["size"] == 200


@patch("app.providers.azure.storage_client.get_blob_service")
def test_list_blobs_empty(mock_get_blob_service):

    container_client = MagicMock()

    container_client.list_blobs.return_value = []

    blob_service = MagicMock()

    blob_service.get_container_client.return_value = container_client

    mock_get_blob_service.return_value = blob_service

    result = list_blobs("outbound-container")

    assert result == []


@patch("app.providers.azure.storage_client.get_blob_service")
def test_list_blobs_container_called(mock_get_blob_service):

    container_client = MagicMock()

    container_client.list_blobs.return_value = []

    blob_service = MagicMock()

    blob_service.get_container_client.return_value = container_client

    mock_get_blob_service.return_value = blob_service

    list_blobs("test-container")

    blob_service.get_container_client.assert_called_once_with("test-container")
