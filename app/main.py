"""
Main entry point for the File Scan Service.
"""

import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.config.settings import Settings
from app.providers.azure.listener import start_azure_listener
from app.providers.aws.listener import start_aws_listener


# Initialize OpenTelemetry
import app.telemetry  # noqa: F401

from app.telemetry import logger
from app.telemetry.configure import configure_telemetry
from app.telemetry.heartbeat import start_heartbeat


@asynccontextmanager
async def lifespan(_app):
    """
    Manage the application lifecycle.

    Starts the appropriate background process based on the configured
    cloud provider.
    """
    configure_telemetry()
    start_heartbeat(interval=60)

    logger.info("Starting File Scan Service. Provider=%s", Settings.CLOUD_PROVIDER_TYPE)

    if Settings.CLOUD_PROVIDER_TYPE == "AZURE":

        listener_thread = threading.Thread(
            target=start_azure_listener, daemon=True, name="servicebus-listener"
        )

        listener_thread.start()

        logger.info("Azure Service Bus listener started.")

    elif Settings.CLOUD_PROVIDER_TYPE == "S3":

        logger.info("Starting AWS processor.")

        # pylint: disable=import-outside-toplevel,import-error,no-name-in-module
        listener_thread = threading.Thread(
            target=start_aws_listener, daemon=True, name="sqs-listener"
        )

        listener_thread.start()
        logger.info("AWS SQS listener started.")

    elif Settings.CLOUD_PROVIDER_TYPE == "GCP":

        logger.info("Starting GCP processor.")

        # pylint: disable=import-outside-toplevel,import-error,no-name-in-module
        from app.providers.gcp.processor import process

        process()

    else:

        logger.error("Unsupported cloud provider: %s", Settings.CLOUD_PROVIDER_TYPE)

        raise ValueError(
            f"Unsupported cloud provider: {Settings.CLOUD_PROVIDER_TYPE}"
        )

    yield

    logger.info("Stopping File Scan Service.")


app = FastAPI(title="File Scan App", version="1.0.0", lifespan=lifespan)

app.include_router(router)
