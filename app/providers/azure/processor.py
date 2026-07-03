"""
Azure message processor.
Processes malware scan events received from Azure Service Bus.
If a file is clean, it is copied to the destination container and
deleted from the source container.

Every major operation is traced using OpenTelemetry.
"""

import json
import time
from time import sleep
from opentelemetry.trace import Status
from opentelemetry.trace import StatusCode
from app.config.settings import Settings
from app.logging.otel_logger import log_scan_event
from app.providers.azure.storage_client import get_blob_service

from app.telemetry import (
    tracer,
    logger,
    files_copied,
    malicious_files,
    processing_time,
)

def parse_message(message):

    """
    Parse Azure Service Bus message.
    """

    with tracer.start_as_current_span("parse_message") as span:

        body = b"".join(
            bytes(chunk)
            for chunk in message.body
        ).decode("utf-8")

        payload = json.loads(body)

        file_name = payload["subject"].split("/blobs/")[-1]

        scan_result = payload["data"]["scanResultType"]

        source_location = (
            f"{Settings.SOURCE_CONTAINER}/{file_name}"
        )

        destination_location = (
            f"{Settings.DEST_CONTAINER}/{file_name}"
        )

        span.set_attribute(
            "file.name",
            file_name
        )

        span.set_attribute(
            "scan.result",
            scan_result
        )

        return (
            file_name,
            scan_result,
            source_location,
            destination_location
        )

def copy_blob(file_name):

    """
    Copy blob to destination storage.
    """

    with tracer.start_as_current_span("copy_blob") as span:

        span.set_attribute(
            "blob.file_name",
            file_name
        )

        source_client = get_blob_service(
            Settings.SOURCE_STORAGE_ACCOUNT
        )

        dest_client = get_blob_service(
            Settings.DEST_STORAGE_ACCOUNT
        )

        source_blob = source_client.get_blob_client(
            Settings.SOURCE_CONTAINER,
            file_name
        )

        dest_blob = dest_client.get_blob_client(
            Settings.DEST_CONTAINER,
            file_name
        )

        if not source_blob.exists():
            return

        logger.info(
            "Starting blob copy: %s",
            file_name
        )

        data = source_blob.download_blob().readall()
 
        dest_blob.upload_blob(
            data,
            overwrite=True
        )

        logger.info(
            "Blob copied successfully."
        )

        return source_blob, dest_blob

def delete_source_blob(
    source_blob,
    dest_blob,
    file_name
):

    """
    Delete source blob after successful copy.
    """

    with tracer.start_as_current_span(
        "delete_source_blob"
    ):

        if not dest_blob.exists():

            raise RuntimeError(
                "Destination blob missing."
            )

        source_blob.delete_blob()

        """ logger.info(
            "Deleted source blob %s",
            file_name
        ) """

def process_clean_file(
    file_name,
    source_location,
    destination_location,
    scan_result,
):

    """
    Process clean file.
    """

    with tracer.start_as_current_span(
        "process_clean_file"
    ):

        logger.info(
            "File Processing Started."
        )

        source_blob, dest_blob = copy_blob(
            file_name
        )

        delete_source_blob(
            source_blob,
            dest_blob,
            file_name
        )

        files_copied.add(1)

        """ log_scan_event(
            file_name,
            source_location,
            destination_location,
            scan_result,
            "File Processed Successfully",
        ) """

        logger.info(
            {
              "file_name": file_name,
              "source_location": source_location,
              "destination_location": destination_location,
              "scan_result": scan_result,
              "status": "File Processed Successfully"
            }
        )

        logger.info(
            "File processed successfully."
        )

def process_malicious_file(
    file_name,
    source_location,
    scan_result,
):

    """
    Process malicious file.
    """

    with tracer.start_as_current_span(
        "process_malicious_file"
    ):

        malicious_files.add(1)

        logger.warning(
            "Malicious file detected: %s",
            file_name
        )

        logger.info(
            {
              "file_name": file_name,
              "source_location": source_location,
              "scan_result": scan_result,
              "status": "File Rejected"
            }
        )

        """ log_scan_event(
            file_name,
            source_location,
            "",
            scan_result,
            "File Rejected",
        ) """

def process_message(message):

    """
    Process one Service Bus message.
    """

    start = time.perf_counter()

    with tracer.start_as_current_span(
        "processor.process_message"
    ) as span:

        try:

            (
                file_name,
                scan_result,
                source_location,
                destination_location,
            ) = parse_message(
                message
            )

            span.set_attribute(
                "file.name",
                file_name
            )

            span.set_attribute(
                "scan.result",
                scan_result
            )

            if scan_result == "No threats found":

                process_clean_file(
                    file_name,
                    source_location,
                    destination_location,
                    scan_result,
                )

            else:

                process_malicious_file(
                    file_name,
                    source_location,
                    scan_result,
                )

        except Exception as ex:

            span.record_exception(ex)

            span.set_status(
                Status(
                    StatusCode.ERROR
                )
            )

            logger.exception(
                "Message processing failed."
            )

            raise

        finally:

            processing_time.record(
                (
                    time.perf_counter()
                    - start
                )
                * 1000
            )
