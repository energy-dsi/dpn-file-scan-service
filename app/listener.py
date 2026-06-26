"""
Azure Service Bus listener.

This module continuously listens for messages from the configured
Azure Service Bus subscription, processes each message, and completes
or abandons it based on the processing result.
"""

import logging
import time

from app.providers.azure.processor import process_message
from app.providers.azure.servicebus_client import get_receiver

logger = logging.getLogger(__name__)


def start_listener():
    """
    Start listening for Azure Service Bus messages.

    Messages are processed one at a time. Successfully processed
    messages are completed, while failed messages are abandoned.
    """

    receiver = get_receiver()

    with receiver:

        while True:

            messages = receiver.receive_messages(
                max_message_count=10,
                max_wait_time=5
            )

            for message in messages:

                try:

                    logger.info(
                        "Locked Until: %s",
                        message.locked_until_utc
                    )

                    logger.info(
                        "Delivery Count: %s",
                        message.delivery_count
                    )

                    process_message(message)

                    logger.info(
                        "Completing message: %s",
                        message.message_id
                    )

                    start = time.time()

                    logger.info(
                        "Calling complete_message..."
                    )

                    receiver.complete_message(message)

                    logger.info(
                        "complete_message returned in %.2f seconds",
                        time.time() - start
                    )

                    logger.info(
                        "Completed message: %s",
                        message.message_id
                    )

                except Exception as ex:  # pylint: disable=broad-exception-caught

                    logger.exception(
                        "Message processing failed: %s",
                        ex
                    )

                    try:

                        receiver.abandon_message(message)

                        logger.info(
                            "Message abandoned: %s",
                            message.message_id
                        )

                    except Exception as abandon_ex:  # pylint: disable=broad-exception-caught

                        logger.exception(
                            "Failed to abandon message: %s",
                            abandon_ex
                        )