from azure.servicebus import ServiceBusClient

from app.providers.azure.auth import get_credential

from app.config.settings import Settings


def get_receiver():

    fully_qualified_namespace = (
        Settings.SERVICE_BUS_NAMESPACE
    )

    client = ServiceBusClient(
        fully_qualified_namespace=
        fully_qualified_namespace,
        credential=get_credential()
    )

    return client.get_subscription_receiver(
        topic_name=Settings.TOPIC_NAME,
        subscription_name=
        Settings.SUBSCRIPTION_NAME
    )