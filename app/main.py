import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.config.settings import Settings
from app.listener import start_listener


@asynccontextmanager
async def lifespan(app):

    if Settings.CLOUD_PROVIDER_TYPE == "AZURE":

        listener_thread = threading.Thread(target=start_listener, daemon=True)

        listener_thread.start()

        yield

    elif Settings.CLOUD_PROVIDER_TYPE == "S3":

        from app.providers.aws.processor import process

        process()

    elif Settings.CLOUD_PROVIDER_TYPE == "GCP":

        from app.providers.gcp.processor import process

        process()

    else:

        raise ValueError("Unsupported Provider")


app = FastAPI(title="File Scan App", version="1.0.0", lifespan=lifespan)

app.include_router(router)
