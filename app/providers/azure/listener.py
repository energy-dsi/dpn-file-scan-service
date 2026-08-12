"""
Azure Service Bus listener.

This module continuously listens for messages from the configured
Azure Service Bus subscription, processes each message, and completes
or abandons it based on the processing result.
"""

import logging
import json
import time

from app.providers.azure.processor import process_message
from app.providers.azure.servicebus_client import get_receiver
from app.providers.azure.storage_client import get_blob_service
from app.config.settings import Settings

from opentelemetry.trace.status import Status, StatusCode
from app.telemetry import tracer, logger, messages_processed, processing_time


def start_azure_listener():
    """
    Start listening for Azure Service Bus messages.

    Messages are processed one at a time. Successfully processed
    messages are completed, while failed messages are abandoned.
    """

    logger.info("Starting Azure Service Bus listener...")

    receiver = get_receiver()

    with receiver:

        while True:

            with tracer.start_as_current_span(
                "servicebus.receive_messages"
            ) as receive_span:

                messages = receiver.receive_messages(
                    max_message_count=10, max_wait_time=5
                )

                receive_span.set_attribute("servicebus.message_count", len(messages))

            for message in messages:

                body = b"".join(bytes(chunk) for chunk in message.body).decode("utf-8")

                payload = json.loads(body)

                file_name = payload["subject"].split("/blobs/")[-1]
                scan_result = payload["data"]["scanResultType"]

                source_client = get_blob_service(Settings.SOURCE_STORAGE_ACCOUNT)

                source_blob = source_client.get_blob_client(
                    Settings.SOURCE_CONTAINER, file_name
                )

                if not source_blob.exists() and scan_result == "No threats found":
                    continue

                start_time = time.perf_counter()

                with tracer.start_as_current_span("servicebus.process_message") as span:

                    span.set_attribute("servicebus.message_id", str(message.message_id))

                    span.set_attribute(
                        "servicebus.delivery_count", message.delivery_count
                    )

                    span.set_attribute(
                        "servicebus.locked_until", str(message.locked_until_utc)
                    )

                    logger.info("Service Bus Message: %s", message)

                    """ logger.info(
                        "Processing Message ID=%s",
                        message.message_id
                    ) """

                    try:

                        process_message(message)

                        messages_processed.add(1)

                        with tracer.start_as_current_span(
                            "servicebus.complete_message"
                        ):

                            logger.info("Completing Message=%s", message.message_id)

                            receiver.complete_message(message)

                        logger.info("Completed Message=%s", message.message_id)

                    except Exception as ex:

                        span.record_exception(ex)

                        span.set_status(Status(StatusCode.ERROR))

                        logger.exception("Message processing failed.")

                        try:

                            with tracer.start_as_current_span(
                                "servicebus.abandon_message"
                            ):

                                receiver.abandon_message(message)

                            logger.info("Message abandoned=%s", message.message_id)

                        except Exception as abandon_ex:

                            span.record_exception(abandon_ex)

                            logger.exception("Failed to abandon message.")

                    finally:

                        processing_time.record(
                            (time.perf_counter() - start_time) * 1000
                        )
