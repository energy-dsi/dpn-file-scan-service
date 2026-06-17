from azure.storage.blob import BlobServiceClient

from app.providers.azure.auth import get_credential

from app.config.settings import Settings


def get_blob_service(account_name):

    account_url = (
        f"https://{account_name}.blob.core.windows.net"
    )

    return BlobServiceClient(
        account_url=account_url,
        credential=get_credential()
    )