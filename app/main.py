"""
Main entry point for the File Scan Service.
"""

import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.config.settings import Settings
from app.listener import start_listener


@asynccontextmanager
async def lifespan(_app):
    """
    Manage the application lifecycle.

    Starts the appropriate background process based on the configured
    cloud provider.
    """

    if Settings.CLOUD_PROVIDER_TYPE == "AZURE":

        listener_thread = threading.Thread(
            target=start_listener,
            daemon=True,
            name="servicebus-listener"
        )

        listener_thread.start()

    elif Settings.CLOUD_PROVIDER_TYPE == "S3":

        # pylint: disable=import-outside-toplevel,import-error,no-name-in-module
        from app.providers.aws.processor import process

        process()

    elif Settings.CLOUD_PROVIDER_TYPE == "GCP":

        # pylint: disable=import-outside-toplevel,import-error,no-name-in-module
        from app.providers.gcp.processor import process

        process()

    else:

        raise ValueError(
            f"Unsupported cloud provider: "
            f"{Settings.CLOUD_PROVIDER_TYPE}"
        )

    yield


app = FastAPI(
    title="File Scan App",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(router)