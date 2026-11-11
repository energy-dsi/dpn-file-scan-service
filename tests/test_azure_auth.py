from unittest.mock import call, patch

import pytest

from app.providers.azure import auth
from app.providers.azure.auth import read_secret, get_credential


#
# read_secret() - reads and strips the secret file contents
#
def test_read_secret_success(tmp_path):

    secret_file = tmp_path / "client-id"

    secret_file.write_text("  my-secret-value  ")

    assert read_secret(str(secret_file)) == "my-secret-value"


#
# read_secret() - a missing file raises a RuntimeError
#
def test_read_secret_missing_file(tmp_path):

    missing = tmp_path / "does-not-exist"

    with pytest.raises(RuntimeError):

        read_secret(str(missing))


#
# get_credential() - builds a ClientSecretCredential from the mounted secrets
#
@patch("app.providers.azure.auth.ClientSecretCredential")
@patch("app.providers.azure.auth.read_secret")
def test_get_credential_success(mock_read_secret, mock_credential_cls):

    mock_read_secret.side_effect = ["client-id", "client-secret"]

    with patch.object(auth.Settings, "TENANT_ID", "tenant-123"), \
         patch.object(auth.Settings, "CLIENT_ID_FILE", "/mnt/id"), \
         patch.object(auth.Settings, "CLIENT_SECRET_FILE", "/mnt/secret"):

        result = get_credential()

    assert result is mock_credential_cls.return_value

    mock_credential_cls.assert_called_once_with(
        tenant_id="tenant-123",
        client_id="client-id",
        client_secret="client-secret",
    )

    assert mock_read_secret.call_args_list == [
        call("/mnt/id"),
        call("/mnt/secret"),
    ]


#
# get_credential() - a secret-read failure propagates
#
@patch("app.providers.azure.auth.read_secret")
def test_get_credential_failure(mock_read_secret):

    mock_read_secret.side_effect = RuntimeError("secret file not found")

    with pytest.raises(RuntimeError):

        get_credential()
