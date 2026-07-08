"""
Azure Service Bus client.
"""

import json

from azure.servicebus import (
    ServiceBusClient,
    ServiceBusMessage,
    ServiceBusReceiveMode,
    TransportType,
)

from opentelemetry.trace import Status
from opentelemetry.trace import StatusCode

from app.config.settings import Settings
from app.providers.azure.auth import get_credential
from app.telemetry import tracer, logger


def get_client():
    """
    Create Service Bus client.
    """

    with tracer.start_as_current_span("servicebus.get_client") as span:

        span.set_attribute("servicebus.namespace", Settings.SERVICE_BUS_NAMESPACE)

        try:

            client = ServiceBusClient(
                fully_qualified_namespace=Settings.SERVICE_BUS_NAMESPACE,
                credential=get_credential(),
                transport_type=TransportType.AmqpOverWebsocket,
            )

            logger.info("Service Bus client created.")

            return client

        except Exception as ex:

            span.record_exception(ex)

            span.set_status(Status(StatusCode.ERROR))

            raise


def get_receiver():
    """
    Return Service Bus receiver.
    """

    with tracer.start_as_current_span("servicebus.get_receiver") as span:

        span.set_attribute("servicebus.topic", Settings.TOPIC_NAME)

        span.set_attribute("servicebus.subscription", Settings.SUBSCRIPTION_NAME)

        client = get_client()

        return client.get_subscription_receiver(
            topic_name=Settings.TOPIC_NAME,
            subscription_name=Settings.SUBSCRIPTION_NAME,
            receive_mode=ServiceBusReceiveMode.PEEK_LOCK,
        )


def send_message(payload):
    """
    Send message to Service Bus.
    """

    with tracer.start_as_current_span("servicebus.send_message") as span:

        span.set_attribute("servicebus.topic", Settings.TOPIC_NAME)

        client = get_client()

        with client:

            sender = client.get_topic_sender(topic_name=Settings.TOPIC_NAME)

            with sender:

                sender.send_messages(ServiceBusMessage(json.dumps(payload)))

        logger.info("Message sent.")


def peek_messages(max_count=20):
    """
    Peek Service Bus messages.
    """

    with tracer.start_as_current_span("servicebus.peek_messages"):

        client = get_client()

        results = []

        with client:

            receiver = client.get_subscription_receiver(
                topic_name=Settings.TOPIC_NAME,
                subscription_name=Settings.SUBSCRIPTION_NAME,
            )

            with receiver:

                messages = receiver.peek_messages(max_message_count=max_count)

                for msg in messages:

                    body = b"".join(bytes(chunk) for chunk in msg.body).decode("utf-8")

                    try:

                        body = json.loads(body)

                    except Exception:
                        pass

                    results.append(
                        {
                            "message_id": msg.message_id,
                            "sequence_number": msg.sequence_number,
                            "delivery_count": msg.delivery_count,
                            "body": body,
                        }
                    )

        return results
