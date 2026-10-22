from unittest.mock import patch

import pytest

from app.providers.aws import storage
from app.providers.aws.storage import (
    copy_object,
    delete_source,
    quarantine,
)


#
# copy_object() - copies inbound -> outbound using default source bucket
#
@patch("app.providers.aws.storage.s3")
def test_copy_object_default_bucket(mock_s3):

    with patch.object(storage.Settings, "S3_BUCKET_INBOUND", "inbound"), \
         patch.object(storage.Settings, "S3_BUCKET_OUTBOUND", "outbound"):

        copy_object("file.txt")

    mock_s3.copy_object.assert_called_once_with(
        CopySource={"Bucket": "inbound", "Key": "file.txt"},
        Bucket="outbound",
        Key="file.txt",
    )


#
# copy_object() - explicit source bucket overrides the default
#
@patch("app.providers.aws.storage.s3")
def test_copy_object_explicit_source(mock_s3):

    with patch.object(storage.Settings, "S3_BUCKET_OUTBOUND", "outbound"):

        copy_object("file.txt", source_bucket="custom")

    assert mock_s3.copy_object.call_args.kwargs["CopySource"] == {
        "Bucket": "custom",
        "Key": "file.txt",
    }


#
# copy_object() - boto3 failure is re-raised
#
@patch("app.providers.aws.storage.s3")
def test_copy_object_failure(mock_s3):

    mock_s3.copy_object.side_effect = Exception("copy failed")

    with pytest.raises(Exception):

        copy_object("file.txt")


#
# delete_source() - deletes from default inbound bucket
#
@patch("app.providers.aws.storage.s3")
def test_delete_source_default_bucket(mock_s3):

    with patch.object(storage.Settings, "S3_BUCKET_INBOUND", "inbound"):

        delete_source("file.txt")

    mock_s3.delete_object.assert_called_once_with(
        Bucket="inbound",
        Key="file.txt",
    )


#
# delete_source() - explicit bucket overrides the default
#
@patch("app.providers.aws.storage.s3")
def test_delete_source_explicit_bucket(mock_s3):

    delete_source("file.txt", bucket="custom")

    mock_s3.delete_object.assert_called_once_with(
        Bucket="custom",
        Key="file.txt",
    )


#
# delete_source() - boto3 failure is re-raised
#
@patch("app.providers.aws.storage.s3")
def test_delete_source_failure(mock_s3):

    mock_s3.delete_object.side_effect = Exception("delete failed")

    with pytest.raises(Exception):

        delete_source("file.txt")


#
# quarantine() - copies to the quarantine bucket then removes the source
#
@patch("app.providers.aws.storage.delete_source")
@patch("app.providers.aws.storage.s3")
def test_quarantine_success(mock_s3, mock_delete):

    with patch.object(storage.Settings, "S3_BUCKET_INBOUND", "inbound"), \
         patch.object(storage.Settings, "S3_BUCKET_QUARANTINE", "quarantine"):

        quarantine("virus.exe")

    mock_s3.copy_object.assert_called_once_with(
        CopySource={"Bucket": "inbound", "Key": "virus.exe"},
        Bucket="quarantine",
        Key="virus.exe",
    )

    mock_delete.assert_called_once_with("virus.exe", bucket=None)


#
# quarantine() - copy failure is re-raised and the source is NOT deleted
#
@patch("app.providers.aws.storage.delete_source")
@patch("app.providers.aws.storage.s3")
def test_quarantine_copy_failure(mock_s3, mock_delete):

    mock_s3.copy_object.side_effect = Exception("quarantine copy failed")

    with pytest.raises(Exception):

        quarantine("virus.exe")

    mock_delete.assert_not_called()
