import json
from unittest.mock import MagicMock, patch

from app.providers.azure.processor import (
    copy_blob,
    delete_source_blob,
    parse_message,
    process_clean_file,
    process_malicious_file,
    process_message,
)


#
# parse_message()
#


@patch("app.providers.azure.processor.Settings")
def test_parse_message(mock_settings):

    mock_settings.SOURCE_CONTAINER = "dp-consumer-raw"
    mock_settings.DEST_CONTAINER = "dp-consumer-stage"

    payload = {
        "subject": "storageAccounts/demo/blobs/test.txt",
        "data": {"scanResultType": "No threats found"},
    }

    message = MagicMock()
    message.body = [json.dumps(payload).encode()]

    (
        file_name,
        scan_result,
        source_location,
        destination_location,
    ) = parse_message(message)

    assert file_name == "test.txt"
    assert scan_result == "No threats found"
    assert source_location == "dp-consumer-raw/test.txt"
    assert destination_location == "dp-consumer-stage/test.txt"


#
# copy_blob()
#


@patch("app.providers.azure.processor.sleep")
@patch("app.providers.azure.processor.get_blob_service")
def test_copy_blob(mock_get_blob_service, mock_sleep):

    source_blob = MagicMock()

    source_blob.download_blob.return_value.readall.return_value = b"test file"

    dest_blob = MagicMock()

    source_client = MagicMock()

    source_client.get_blob_client.return_value = source_blob

    dest_client = MagicMock()

    dest_client.get_blob_client.return_value = dest_blob

    mock_get_blob_service.side_effect = [source_client, dest_client]

    returned_source, returned_dest = copy_blob("sample.txt")

    source_blob.download_blob.assert_called_once()

    dest_blob.upload_blob.assert_called_once_with(b"test file", overwrite=True)

    assert returned_source == source_blob
    assert returned_dest == dest_blob


#
# delete_source_blob()
#


def test_delete_source_blob():

    source_blob = MagicMock()

    dest_blob = MagicMock()
    dest_blob.exists.return_value = True

    delete_source_blob(source_blob, dest_blob, "sample.txt")

    source_blob.delete_blob.assert_called_once()


def test_delete_source_blob_destination_missing():

    source_blob = MagicMock()

    dest_blob = MagicMock()
    dest_blob.exists.return_value = False

    import pytest

    with pytest.raises(RuntimeError):

        delete_source_blob(source_blob, dest_blob, "sample.txt")


#
# process_clean_file()
#


@patch("app.providers.azure.processor.files_copied")
# @patch("app.providers.azure.processor.log_scan_event")
@patch("app.providers.azure.processor.delete_source_blob")
@patch("app.providers.azure.processor.copy_blob")
def test_process_clean_file(
    mock_copy,
    mock_delete,
    mock_log,
):

    source_blob = MagicMock()
    dest_blob = MagicMock()

    mock_copy.return_value = (
        source_blob,
        dest_blob,
    )

    process_clean_file(
        "test.txt",
        "dp-consumer-raw/test.txt",
        "dp-consumer-stage/test.txt",
        "No threats found",
    )

    mock_copy.assert_called_once_with("test.txt")

    mock_delete.assert_called_once_with(
        source_blob,
        dest_blob,
        "test.txt",
    )

    # mock_counter.add.assert_called_once_with(1)

    """ mock_log.assert_called_once_with(
        "test.txt",
        "dp-consumer-raw/test.txt",
        "dp-consumer-stage/test.txt",
        "No threats found",
        "File Processed Successfully",
    ) """


#
# process_malicious_file()
#


@patch("app.providers.azure.processor.malicious_files")
# @patch("app.providers.azure.processor.log_scan_event")
def test_process_malicious_file(
    mock_log,
):

    process_malicious_file(
        "bad.exe",
        "dp-consumer-raw/bad.exe",
        "Malicious",
    )

    # mock_counter.add.assert_called_once_with(1)

    """ mock_log.assert_called_once_with(
        "bad.exe",
        "dp-consumer-raw/bad.exe",
        "Malicious",
        "File Rejected",
    ) """


#
# process_message() - clean
#


@patch("app.providers.azure.processor.process_clean_file")
@patch("app.providers.azure.processor.parse_message")
def test_process_message_clean(
    mock_parse,
    mock_clean,
):

    mock_parse.return_value = (
        "test.txt",
        "No threats found",
        "dp-consumer-raw/test.txt",
        "dp-consumer-stage/test.txt",
    )

    process_message(MagicMock())

    mock_clean.assert_called_once_with(
        "test.txt",
        "dp-consumer-raw/test.txt",
        "dp-consumer-stage/test.txt",
        "No threats found",
    )


#
# process_message() - malicious
#


@patch("app.providers.azure.processor.process_malicious_file")
@patch("app.providers.azure.processor.parse_message")
def test_process_message_malicious(
    mock_parse,
    mock_malicious,
):

    mock_parse.return_value = (
        "bad.exe",
        "Malicious",
        "dp-consumer-raw/bad.exe",
        "quaratine/bad.exe",
    )

    process_message(MagicMock())

    mock_malicious.assert_called_once_with(
        "bad.exe",
        "dp-consumer-raw/bad.exe",
        "Malicious",
    )


#
# process_message() exception
#


@patch("app.providers.azure.processor.parse_message")
def test_process_message_exception(
    mock_parse,
):

    import pytest

    mock_parse.side_effect = Exception("Parsing failed")

    with pytest.raises(Exception):

        process_message(MagicMock())
