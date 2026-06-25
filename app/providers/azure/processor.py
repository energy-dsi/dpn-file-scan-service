import json
from time import sleep

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

    print("source_client_blob: ", source_client)

    dest_client = get_blob_service(
        Settings.DEST_STORAGE_ACCOUNT
    )

    print("dest_client_blob: ", dest_client)

    source_blob = source_client\
        .get_blob_client(
            Settings.SOURCE_CONTAINER,
            file_name
        )

    print("source_blob: ", source_blob)

    dest_blob = dest_client\
        .get_blob_client(
            Settings.DEST_CONTAINER,
            file_name
        )
        
    copy_operation = (
        dest_blob.start_copy_from_url(
            source_blob.url
        )
    )

    copy_id = copy_operation["copy_id"]

    while True:

        properties = dest_blob.get_blob_properties()

        status = (
            properties.copy.status
        )

        if status == "success":
            break

        if status == "failed":
            raise Exception(
                "Blob copy failed"
            )
            
        sleep(1)
        
    if dest_blob.exists():

        source_blob.delete_blob()

    else:

        raise Exception(
            "Destination blob not found"
        )
        
    print(
        f"Copied and deleted: {file_name}"
    )


def process_message(message):

    body = b"".join(
        bytes(chunk)
        for chunk in message.body
        ).decode("utf-8")

    payload = json.loads(body)

    print("Type of Logs after change: ", type(payload))

    
    result = payload["data"]["scanResultType"]
    file_name = payload["subject"].split("/blobs/")[-1]
    scan_result = result
    source_location = (
        f"{Settings.SOURCE_CONTAINER}/{file_name}"
    )

    if result == "No threats found":
        print("No threats found")

        copy_blob(file_name)

        log_scan_event(
            file_name,
            source_location,
            scan_result,
            "COPIED_AND_DELETED"
        )
    else:
        print("Malicious!")
            
        log_scan_event(
            file_name,
            source_location,
            scan_result,
            "MALICIOUS"
        )