"""
Azure Blob Storage client.
"""

from azure.storage.blob import BlobServiceClient

from opentelemetry.trace import Status
from opentelemetry.trace import StatusCode

from app.config.settings import Settings
from app.providers.azure.auth import get_credential
from app.telemetry import tracer, logger


def get_blob_service(account_name):
    """
    Create BlobServiceClient.
    """

    with tracer.start_as_current_span("storage.get_blob_service") as span:

        span.set_attribute("storage.account", account_name)

        try:

            account_url = f"https://{account_name}.blob.core.windows.net"

            client = BlobServiceClient(
                account_url=account_url, credential=get_credential()
            )

            logger.info("BlobServiceClient created.")

            return client

        except Exception as ex:

            span.record_exception(ex)

            span.set_status(Status(StatusCode.ERROR))

            logger.exception("BlobServiceClient creation failed.")

            raise


def list_blobs(container_name):
    """
    List blobs from container.
    """

    with tracer.start_as_current_span("storage.list_blobs") as span:

        span.set_attribute("storage.container", container_name)

        blob_service = get_blob_service(Settings.DEST_STORAGE_ACCOUNT)

        container_client = blob_service.get_container_client(container_name)

        files = []

        for blob in container_client.list_blobs():

            files.append(
                {
                    "file_name": blob.name,
                    "size": blob.size,
                    "last_modified": str(blob.last_modified),
                }
            )

        logger.info("Listed %s blobs.", len(files))

        return files
