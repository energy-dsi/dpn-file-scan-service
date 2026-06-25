from pathlib import Path
from azure.identity import ClientSecretCredential

from app.config.settings import Settings

def read_secret(path: str) -> str:

    try:

        return (
            Path(path)
            .read_text()
            .strip()
        )

    except FileNotFoundError:

        raise RuntimeError(
            f"Secret file not found: {path}"
        )

def get_credential():

    client_id = read_secret(
        Settings.CLIENT_ID_FILE
    )

    client_secret = read_secret(
        Settings.CLIENT_SECRET_FILE
    )

    return ClientSecretCredential(
        tenant_id=Settings.TENANT_ID,
        client_id=client_id,
        client_secret=client_secret
    )