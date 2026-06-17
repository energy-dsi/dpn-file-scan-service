import json

from app.config.settings import Settings

from app.providers.azure.storage_client import (
    get_blob_service
)

from app.logging.otel_logger import (
    log_scan_event
)


def copy_blob(file_name):

    source_client = get_blob_service(
        Settings.SOURCE_STORAGE_ACCOUNT
    )

    dest_client = get_blob_service(
        Settings.DEST_STORAGE_ACCOUNT
    )

    source_blob = source_client\
        .get_blob_client(
            Settings.SOURCE_CONTAINER,
            file_name
        )

    dest_blob = dest_client\
        .get_blob_client(
            Settings.DEST_CONTAINER,
            file_name
        )

    data = source_blob.download_blob().readall()

    dest_blob.upload_blob(
        data,
        overwrite=True
    )


def process_message(message):

    payload = json.loads(
        str(message)
    )

    file_name = payload["fileName"]

    scan_result = payload["scanResult"]

    source_location = (
        f"{Settings.SOURCE_CONTAINER}/{file_name}"
    )

    if scan_result == "OK":

        copy_blob(file_name)

        log_scan_event(
            file_name,
            source_location,
            scan_result,
            "COPIED"
        )

    else:

        log_scan_event(
            file_name,
            source_location,
            scan_result,
            "MALICIOUS"
        )