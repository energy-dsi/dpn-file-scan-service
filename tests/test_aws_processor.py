import json

from unittest.mock import MagicMock, patch

import pytest

from app.providers.aws.processor import (
    parse_message,
    process_clean_file,
    process_malicious_file,
    process_message,
)


def _detail(scan_status="COMPLETED", scan_result="NO_THREATS_FOUND"):
    return {
        "scanStatus": scan_status,
        "scanResultDetails": {"scanResultStatus": scan_result},
        "s3ObjectDetails": {"bucketName": "inbound", "objectKey": "file.txt"},
    }


#
# parse_message() - direct SQS delivery (the body is the event itself)
#
def test_parse_message_direct():

    body = json.dumps({"detail": _detail()})

    with patch("app.providers.aws.processor.Settings.S3_BUCKET_OUTBOUND", "outbound"):

        result = parse_message({"Body": body})

    assert result == (
        "file.txt",
        "inbound",
        "COMPLETED",
        "NO_THREATS_FOUND",
        "inbound/file.txt",
        "outbound/file.txt",
    )


#
# parse_message() - SNS -> SQS delivery (event wrapped in a "Message" field)
#
def test_parse_message_sns_envelope():

    inner = json.dumps({"detail": _detail(scan_result="THREATS_FOUND")})

    body = json.dumps({"Type": "Notification", "Message": inner})

    with patch("app.providers.aws.processor.Settings.S3_BUCKET_OUTBOUND", "outbound"):

        result = parse_message({"Body": body})

    assert result[0] == "file.txt"
    assert result[1] == "inbound"
    assert result[3] == "THREATS_FOUND"


#
# process_clean_file() - copies then removes the source
#
@patch("app.providers.aws.processor.files_copied")
@patch("app.providers.aws.processor.delete_source")
@patch("app.providers.aws.processor.copy_object")
def test_process_clean_file(mock_copy, mock_delete, mock_files_copied):

    process_clean_file(
        "file.txt",
        "inbound",
        "inbound/file.txt",
        "outbound/file.txt",
        "NO_THREATS_FOUND",
    )

    mock_copy.assert_called_once_with("file.txt", source_bucket="inbound")

    mock_delete.assert_called_once_with("file.txt", bucket="inbound")

    mock_files_copied.add.assert_called_once_with(1)


#
# process_malicious_file() - deletes the malicious source (quarantine disabled)
#
@patch("app.providers.aws.processor.malicious_files")
@patch("app.providers.aws.processor.delete_source")
def test_process_malicious_file(mock_delete, mock_malicious):

    process_malicious_file(
        "virus.exe",
        "inbound",
        "inbound/virus.exe",
        "THREATS_FOUND",
    )

    mock_malicious.add.assert_called_once_with(1)

    mock_delete.assert_called_once_with("virus.exe", bucket="inbound")


#
# process_message() - clean file routed to process_clean_file
#
@patch("app.providers.aws.processor.process_clean_file")
@patch("app.providers.aws.processor.parse_message")
def test_process_message_clean(mock_parse, mock_clean):

    mock_parse.return_value = (
        "file.txt",
        "inbound",
        "COMPLETED",
        "NO_THREATS_FOUND",
        "inbound/file.txt",
        "outbound/file.txt",
    )

    process_message({"Body": "x"})

    mock_clean.assert_called_once_with(
        "file.txt",
        "inbound",
        "inbound/file.txt",
        "outbound/file.txt",
        "NO_THREATS_FOUND",
    )


#
# process_message() - malicious file routed to process_malicious_file
#
@patch("app.providers.aws.processor.process_malicious_file")
@patch("app.providers.aws.processor.parse_message")
def test_process_message_malicious(mock_parse, mock_malicious):

    mock_parse.return_value = (
        "virus.exe",
        "inbound",
        "COMPLETED",
        "THREATS_FOUND",
        "inbound/virus.exe",
        "outbound/virus.exe",
    )

    process_message({"Body": "x"})

    mock_malicious.assert_called_once_with(
        "virus.exe",
        "inbound",
        "inbound/virus.exe",
        "THREATS_FOUND",
    )


#
# process_message() - incomplete scan is skipped (neither path taken)
#
@patch("app.providers.aws.processor.process_malicious_file")
@patch("app.providers.aws.processor.process_clean_file")
@patch("app.providers.aws.processor.parse_message")
def test_process_message_incomplete_scan(mock_parse, mock_clean, mock_malicious):

    mock_parse.return_value = (
        "file.txt",
        "inbound",
        "IN_PROGRESS",
        "NO_THREATS_FOUND",
        "inbound/file.txt",
        "outbound/file.txt",
    )

    process_message({"Body": "x"})

    mock_clean.assert_not_called()

    mock_malicious.assert_not_called()


#
# process_message() - parsing failure is re-raised
#
@patch("app.providers.aws.processor.parse_message")
def test_process_message_exception(mock_parse):

    mock_parse.side_effect = Exception("parsing failed")

    with pytest.raises(Exception):

        process_message({"Body": "x"})
