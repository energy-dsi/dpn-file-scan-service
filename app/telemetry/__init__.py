"""
Initialize telemetry.
"""

from app.telemetry.tracing import tracer
from app.telemetry.metrics import (
    meter,
    messages_counter as messages_processed,
    files_counter as files_copied,
    malware_counter as malicious_files,
    processing_time as processing_time,
    heartbeat_counter as heartbeat_counter,
)
from app.telemetry.logging import logger
from app.telemetry.configure import configure_telemetry

__all__ = [
    "tracer",
    "meter",
    "messages_processed",
    "files_copied",
    "malicious_files",
    "processing_time",
    "logger",
    "configure_telemetry",
    "heartbeat_counter",
]
