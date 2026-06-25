import os

from dotenv import load_dotenv

load_dotenv()


class Settings:

    CLOUD_PROVIDER_TYPE = os.getenv("CLOUD_PROVIDER_TYPE", "AZURE")

    TENANT_ID = os.getenv("TENANT_ID")
    CLIENT_ID = os.getenv("CLIENT_ID")
    CLIENT_SECRET = os.getenv("CLIENT_SECRET")

    SERVICE_BUS_NAMESPACE = os.getenv("SERVICE_BUS_NAMESPACE")

    TOPIC_NAME = os.getenv("TOPIC_NAME")

    SUBSCRIPTION_NAME = os.getenv("SUBSCRIPTION_NAME")

    SOURCE_STORAGE_ACCOUNT = os.getenv("SOURCE_STORAGE_ACCOUNT")

    SOURCE_CONTAINER = os.getenv("SOURCE_CONTAINER")

    DEST_STORAGE_ACCOUNT = os.getenv("DEST_STORAGE_ACCOUNT")

    DEST_CONTAINER = os.getenv("DEST_CONTAINER")
