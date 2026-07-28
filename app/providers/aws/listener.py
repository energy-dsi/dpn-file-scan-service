"""
AWS SQS listener.

This module continuously listens for messages from the configured
AWS SQS subscription, processes each message, and completes
or abandons it based on the processing result.
"""

import time

from app.providers.aws.sqs_client import (
    receive_messages,
    delete_message,
)

from app.providers.aws.processor import (
    process_message,
)

from opentelemetry.trace.status import Status, StatusCode
from app.telemetry import tracer, logger, messages_processed, processing_time


def start_aws_listener():

    logger.info("AWS SQS listener started.")

    while True:
        
        with tracer.start_as_current_span(
            "SWS.receive_messages"
        ) as receive_span:

            try:
                start_time = time.perf_counter()
                response = receive_messages()

                messages = response.get(
                    "Messages",
                    [],
                )
                
                receive_span.set_attribute("SQS.message_count", len(messages))

                if not messages:

                    time.sleep(2)
                    continue

                for message in messages:

                    try:                       
                        
                        with tracer.start_as_current_span("SQS.process_message") as span:
                            
                            span.set_attribute("SQS.message_id", str(message.id))
                            
                            logger.info("SQS Message: %s", message)
                            
                            try:                                
                                process_message(message)
                                messages_processed.add(1)
                            except Exception as ex:                            
                                span.record_exception(ex)        
                                span.set_status(Status(StatusCode.ERROR))        
                                logger.exception("Message processing failed.")

                    except Exception as ex:
                        span.record_exception(ex)        
                        span.set_status(Status(StatusCode.ERROR))
                        logger.exception(
                            "Skipping message after processing failure."
                        )

                    try:

                        delete_message(
                            message["ReceiptHandle"]
                        )

                    except Exception as ex:
                        span.record_exception(ex)        
                        span.set_status(Status(StatusCode.ERROR))
                        logger.exception(
                            "Failed to delete message from queue."
                        )

            except Exception as ex:
                span.record_exception(ex)        
                span.set_status(Status(StatusCode.ERROR))
                logger.exception(
                    "SQS listener loop failed, retrying."
                )

                time.sleep(2)
            
            finally:            
                processing_time.record(
                    (time.perf_counter() - start_time) * 1000
                )