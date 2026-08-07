"""
AWS SQS listener.

This module continuously listens for messages from the configured
AWS SQS subscription, processes each message, and completes
or abandons it based on the processing result.
"""

import time

from opentelemetry.trace.status import Status, StatusCode

from app.providers.aws.sqs_client import (
    receive_messages,
    delete_message,
)

from app.providers.aws.processor import (
    process_message,
)

from app.telemetry import tracer, logger, messages_processed, processing_time

POLL_INTERVAL_SECONDS = 10


def _handle_message(message, receive_span):
    """Process a single SQS message, then delete it from the queue."""

    with tracer.start_as_current_span("SQS.process_message") as span:

        span.set_attribute("SQS.message_id", str(message.get("MessageId")))

        logger.info("SQS Message: %s", message)

        try:
            process_message(message)
            messages_processed.add(1)
        except Exception as ex:
            span.record_exception(ex)
            span.set_status(Status(StatusCode.ERROR))
            logger.exception("Message processing failed.")

    try:
        delete_message(message["ReceiptHandle"])
    except Exception as ex:
        receive_span.record_exception(ex)
        receive_span.set_status(Status(StatusCode.ERROR))
        logger.exception("Failed to delete message from queue.")


def _poll_once(receive_span):
    """Receive one batch of messages and process each of them."""

    response = receive_messages()

    messages = response.get("Messages", [])

    receive_span.set_attribute("SQS.message_count", len(messages))

    if not messages:
        time.sleep(POLL_INTERVAL_SECONDS)
        return

    for message in messages:
        _handle_message(message, receive_span)


def start_aws_listener():

    logger.info("AWS SQS listener started.")

    while True:

        with tracer.start_as_current_span(
            "SQS.receive_messages"
        ) as receive_span:

            start_time = time.perf_counter()

            try:
                _poll_once(receive_span)

            except Exception as ex:
                receive_span.record_exception(ex)
                receive_span.set_status(Status(StatusCode.ERROR))
                logger.exception("SQS listener loop failed, retrying.")
                time.sleep(POLL_INTERVAL_SECONDS)

            finally:
                processing_time.record(
                    (time.perf_counter() - start_time) * 1000
                )
