"""
Application settings.
"""

import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """
    Application configuration.
    """

    # ----------------------------------------
    # Cloud
    # ----------------------------------------

    CLOUD_PROVIDER_TYPE = os.getenv("CLOUD_PROVIDER_TYPE", "AZURE")

    # ----------------------------------------
    # OpenTelemetry
    # ----------------------------------------

    ENABLE_TELEMETRY = os.getenv("ENABLE_TELEMETRY", "true").lower() == "true"

    OTEL_ENDPOINT = os.getenv("OTEL_ENDPOINT", "http://dpn-otel-collector-health:4317")

    OTEL_EXPORTER_OTLP_PROTOCOL = os.getenv("OTEL_EXPORTER_OTLP_PROTOCOL", "grpc")

    OTEL_EXPORTER_OTLP_INSECURE = os.getenv("OTEL_EXPORTER_OTLP_INSECURE", "true")

    OTEL_SERVICE_NAME = os.getenv("SERVICE_NAME", "file-scan-service")

    OTEL_SERVICE_VERSION = os.getenv("SERVICE_VERSION", "1.0.0")

    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

    TESTING = os.getenv("TESTING", "false").lower() == "true"

    TENANT_ID = os.getenv("TENANT_ID")
    CLIENT_ID_FILE = os.getenv("CLIENT_ID_FILE")

    CLIENT_SECRET_FILE = os.getenv("CLIENT_SECRET_FILE")

    CLIENT_ID = os.getenv("CLIENT_ID")

    CLIENT_SECRET = os.getenv("CLIENT_SECRET")

    SERVICE_BUS_NAMESPACE = os.getenv("SERVICE_BUS_NAMESPACE")

    TOPIC_NAME = os.getenv("TOPIC_NAME")

    SUBSCRIPTION_NAME = os.getenv("SUBSCRIPTION_NAME")

    SOURCE_STORAGE_ACCOUNT = os.getenv("SOURCE_STORAGE_ACCOUNT")

    SOURCE_CONTAINER = os.getenv("SOURCE_CONTAINER")

    DEST_STORAGE_ACCOUNT = os.getenv("DEST_STORAGE_ACCOUNT")

    DEST_CONTAINER = os.getenv("DEST_CONTAINER")
