from fastapi import FastAPI
from contextlib import asynccontextmanager
import threading
from app.config.settings import Settings

from app.api.routes import router
from app.listener import start_listener



@asynccontextmanager
async def lifespan(app):

    listener_thread = threading.Thread(
        target=start_listener,
        daemon=True
    )

    listener_thread.start()

    yield

app = FastAPI(
    title="File Scan App",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(router)