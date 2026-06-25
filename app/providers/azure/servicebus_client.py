import json

from azure.servicebus import (ServiceBusClient, ServiceBusMessage,
                              ServiceBusReceiveMode, TransportType)

from app.config.settings import Settings
from app.providers.azure.auth import get_credential


def send_message(payload):
    servicebus_client = get_client()
    with servicebus_client:
        sender = servicebus_client.get_topic_sender(topic_name=Settings.TOPIC_NAME)
        with sender:
            message = ServiceBusMessage(json.dumps(payload))
            sender.send_messages(message)


def get_receiver():

    client = get_client()

    return client.get_subscription_receiver(
        topic_name=Settings.TOPIC_NAME,
        subscription_name=Settings.SUBSCRIPTION_NAME,
        receive_mode=ServiceBusReceiveMode.PEEK_LOCK,
    )


def get_client():

    fully_qualified_namespace = Settings.SERVICE_BUS_NAMESPACE

    return ServiceBusClient(
        fully_qualified_namespace=fully_qualified_namespace,
        credential=get_credential(),
        transport_type=TransportType.AmqpOverWebsocket,
    )


def peek_messages(max_count: int = 20):

    servicebus_client = get_client()

    results = []

    with servicebus_client:

        receiver = servicebus_client.get_subscription_receiver(
            topic_name=Settings.TOPIC_NAME, subscription_name=Settings.SUBSCRIPTION_NAME
        )

        with receiver:

            messages = receiver.peek_messages(max_message_count=max_count)

            for msg in messages:

                try:

                    body = b"".join(bytes(chunk) for chunk in msg.body).decode("utf-8")

                    try:
                        payload = json.loads(body)
                    except Exception:
                        payload = body

                    results.append(
                        {
                            "message_id": msg.message_id,
                            "sequence_number": msg.sequence_number,
                            "delivery_count": msg.delivery_count,
                            "body": payload,
                        }
                    )

                except Exception as ex:

                    results.append({"message_id": msg.message_id, "error": str(ex)})

    return results
