import json

from app.config.settings import Settings

from app.providers.azure.storage_client import (
    get_blob_service
)

from app.logging.otel_logger import (
    log_scan_event
)


def fetch_blob_name():

    source_client = get_blob_service(
        Settings.SOURCE_STORAGE_ACCOUNT
    )

    container_client = source_client.get_container_client(Settings.SOURCE_CONTAINER)

    try:
        blob_list = container_client.list_blobs()
        first_blob = next(blob_list, None)
        return first_blob.name
    except StopIteration:
        print("Container is empty!")


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

    print("dest_blob: ", dest_blob)

    data = source_blob.download_blob().readall()

    dest_blob.upload_blob(
        data,
        overwrite=True
    )


def process_message(message):

    body = b"".join(
        bytes(chunk)
        for chunk in message.body
        ).decode("utf-8")

    payload = json.loads(body)

    print("Type of Logs after change: ", type(payload))

    #file_name = fetch_blob_name()
    #print("SOURCE_CONTAINER_FILE: ",file_name)

    
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
            "COPIED"
        )
    else:
        print("Malicious!")
            
        log_scan_event(
            file_name,
            source_location,
            scan_result,
            "MALICIOUS"
        )