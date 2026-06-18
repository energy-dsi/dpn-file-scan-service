from azure.servicebus import ServiceBusClient, TransportType, ServiceBusMessage
from app.providers.azure.auth import get_credential
import json
from app.config.settings import Settings


def send_message(payload):
    servicebus_client = get_client()
    with servicebus_client:
        sender = servicebus_client.get_topic_sender(
            topic_name=Settings.TOPIC_NAME
        )
        with sender:
            message = ServiceBusMessage(
                json.dumps(payload)
            )
            sender.send_messages(
                message
            )

def get_receiver():

    client = get_client()

    return client.get_subscription_receiver(
        topic_name=Settings.TOPIC_NAME,
        subscription_name=
        Settings.SUBSCRIPTION_NAME
    )

def get_client():

    fully_qualified_namespace = (
        Settings.SERVICE_BUS_NAMESPACE
    )

    return ServiceBusClient(
        fully_qualified_namespace=
        fully_qualified_namespace,
        credential=get_credential(),
        transport_type=TransportType.AmqpOverWebsocket
    )