import json
import time

from opentelemetry.trace import Status
from opentelemetry.trace import StatusCode
from app.config.settings import Settings

from app.telemetry import (
    tracer,
    logger,
    files_copied,
    malicious_files,
    processing_time,
)

from app.providers.aws.storage import (
    copy_object,
    delete_source,
    quarantine,
)

#
# GuardDuty malware protection scan outcomes
# https://docs.aws.amazon.com/guardduty/latest/ug/malware-protection-s3-object-scan-events.html
#
SCAN_STATUS_COMPLETED = "COMPLETED"

SCAN_RESULT_NO_THREATS = "NO_THREATS_FOUND"

SCAN_RESULT_THREATS_FOUND = "THREATS_FOUND"


def parse_message(message):
    """
    Parse AWS SQS message.
    """

    with tracer.start_as_current_span("parse_message") as span:

        body = b"".join(bytes(chunk) for chunk in message.body).decode("utf-8")

        envelope = json.loads(body)

        #
        # SNS -> SQS wraps the event JSON in a "Message" field;
        # a direct SQS delivery is already the event itself.
        #
        if isinstance(envelope, dict) and "Message" in envelope:
            payload = json.loads(envelope["Message"])
        else:
            payload = envelope

        detail = payload["detail"]

        scan_status = detail["scanStatus"]

        scan_result = detail["scanResultDetails"]["scanResultStatus"]

        s3_object_details = detail["s3ObjectDetails"]

        bucket_name = s3_object_details["bucketName"]

        file_name = s3_object_details["objectKey"]

        source_location = f"{bucket_name}/{file_name}"

        destination_location = (
            f"{Settings.S3_BUCKET_OUTBOUND}/{file_name}"
        )
        
        span.set_attribute("file.name", file_name)

        span.set_attribute("scan.result", scan_result)

        return (
            file_name,
            bucket_name,
            scan_status,
            scan_result,
            source_location,
            destination_location,
        )

def process_clean_file(

    file_name,
    bucket_name,
    source_location,
    destination_location,
    scan_result,
):
    """
    Process clean file.
    """

    with tracer.start_as_current_span("process_clean_file"):

        logger.info(
            "Copying clean file %s",
            file_name,
        )

        copy_object(file_name, source_bucket=bucket_name)

        delete_source(file_name, bucket=bucket_name)

        files_copied.add(1)

        logger.info(
            "Copied %s successfully",
            file_name,
            extra={
                "file_name": file_name,
                "scan_result": scan_result,
                "source": source_location,
                "destination": destination_location,
            },
        )

def process_malicious_file(

    file_name,
    bucket_name,
    source_location,
    scan_result,
):
    """
    Process malicious file.
    """

    with tracer.start_as_current_span("process_malicious_file"):

        malicious_files.add(1)

        logger.warning(
            "Malicious file detected %s",
            file_name,
        )

        quarantine(file_name, source_bucket=bucket_name)

        logger.warning(

            "File moved to quarantine",

            extra={
                "file_name": file_name,
                "scan_result": scan_result,
                "source": source_location,
            },
        )

def process_message(message):
    """
    Process one SQS message.
    """

    start = time.perf_counter()

    with tracer.start_as_current_span("processor.process_message") as span:
        try:

            (
                file_name,
                bucket_name,
                scan_status,
                scan_result,
                source_location,
                destination_location,
            ) = parse_message(
                message
            )

            span.set_attribute("file.name", file_name)

            span.set_attribute("scan.result", scan_result)

            if scan_status != SCAN_STATUS_COMPLETED:

                logger.warning(
                    "Scan for %s did not complete (status=%s), skipping.",
                    file_name,
                    scan_status,
                )

            elif scan_result == SCAN_RESULT_NO_THREATS:

                process_clean_file(
                    file_name,
                    bucket_name,
                    source_location,
                    destination_location,
                    scan_result,
                )

            else:

                process_malicious_file(
                    file_name,
                    bucket_name,
                    source_location,
                    scan_result,
                )

        except Exception as ex:

            span.record_exception(ex)
            
            span.set_status(Status(StatusCode.ERROR))

            logger.error("Message processing failed.")

            raise

        finally:

            elapsed = (
                time.perf_counter() - start
            ) * 1000

            processing_time.record(
                elapsed
            )