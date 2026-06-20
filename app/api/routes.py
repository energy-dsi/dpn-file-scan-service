from fastapi import APIRouter, HTTPException
from typing import Any
from app.providers.azure.storage_client import (
    list_blobs
)
from app.providers.azure.servicebus_client import (
    send_message
)
from app.config.settings import Settings

router = APIRouter()

@router.get("/health")
def health_check():
    
    return {
        "status":"UP"
    }

@router.get("/version")
def version():
    
    return{
        "application":"file-scan-app",
        "version":"1.0.0"
    }

@router.get("/outbound/files")
def get_outbound_files():
    try:
        files = list_blobs(
            Settings.DEST_CONTAINER
        )
        return {
            "container": Settings.DEST_CONTAINER,
            "count": len(files),
            "files": files
        }
    except Exception as ex:
        raise HTTPException(
            status_code=500,
            detail=str(ex)
        )

@router.get("/inbound/files")
def get_inbound_files():
    try:
        files = list_blobs(
            Settings.SOURCE_CONTAINER
        )
        return {
            "container": Settings.SOURCE_CONTAINER,
            "count": len(files),
            "files": files
        }
    except Exception as ex:
        raise HTTPException(
            status_code=500,
            detail=str(ex)
        )

@router.post("/servicebus/send")

def publish_message():

    try:

        send_message(payload)

        return {
            "status": "SUCCESS",
            "message": "Message published"
        }

    except Exception as ex:

        raise HTTPException(
            status_code=500,
            detail=str(ex)
        )
 