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

def list_blobs(container_name):
 
    blob_service = get_blob_service(
        Settings.DEST_STORAGE_ACCOUNT
    )
 
    container_client = (
        blob_service.get_container_client(
            container_name
        )
    )
 
    files = []
 
    for blob in container_client.list_blobs():
 
        files.append({
            "file_name": blob.name,
            "size": blob.size,
            "last_modified": str(
                blob.last_modified
            )
        })
 
    return files