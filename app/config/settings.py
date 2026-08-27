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

    OTEL_ENDPOINT = os.getenv("OTEL_ENDPOINT")

    # Standard OTLP endpoint (base URL, e.g. https://<collector>:4318).
    # Falls back to the legacy OTEL_ENDPOINT for backward compatibility.
    OTEL_EXPORTER_OTLP_ENDPOINT = (
        os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or os.getenv("OTEL_ENDPOINT")
    )

    OTEL_EXPORTER_OTLP_PROTOCOL = os.getenv("OTEL_EXPORTER_OTLP_PROTOCOL", "http/protobuf")

    # Path to the CA certificate (PEM) used to verify the collector's TLS
    # certificate. Required for HTTPS; if unset, the default certifi bundle is
    # used (which will NOT trust a private root CA).
    OTEL_EXPORTER_OTLP_CERTIFICATE = os.getenv("OTEL_EXPORTER_OTLP_CERTIFICATE")

    TRUSTSTORE_PASSWORD = os.getenv("TRUSTSTORE_PASSWORD")

    # Optional override for the PKCS#12 truststore location. When set, this
    # path is tried first, ahead of the hardcoded container/local-dev
    # defaults in app/telemetry/otel_truststore.py. Supports multiple
    # candidate paths separated by os.pathsep (";" on Windows, ":" on
    # Linux/macOS), tried in order.
    TRUSTSTORE_PATH = os.getenv("TRUSTSTORE_PATH")

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
    
    AWS_REGION = os.getenv("AWS_REGION", "eu-west-2")

    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")

    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

    AWS_SESSION_TOKEN = os.getenv("AWS_SESSION_TOKEN")

    # Only set this for a local MinIO endpoint. Leave unset against real
    # AWS so boto3 resolves the correct regional endpoint from AWS_REGION.
    S3_ENDPOINT = os.getenv("S3_ENDPOINT")

    # TLS verification for S3. Keep enabled against real AWS; set to
    # "false" only for local MinIO with a self-signed certificate.
    S3_VERIFY_SSL = os.getenv("S3_VERIFY_SSL", "true").lower() == "true"

    S3_BUCKET_INBOUND = os.getenv("S3_BUCKET_INBOUND")
    
    S3_BUCKET_OUTBOUND = os.getenv("S3_BUCKET_OUTBOUND")
    
    S3_BUCKET_QUARANTINE = os.getenv("S3_BUCKET_QUARANTINE")

    SQS_ENDPOINT = os.getenv("SQS_ENDPOINT")

    SNS_ENDPOINT = os.getenv("SNS_ENDPOINT")

    SNS_TOPIC = os.getenv("SNS_TOPIC")

    SQS_QUEUE = os.getenv("SQS_QUEUE")
