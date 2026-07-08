"""
Heartbeat thread.
 
Emits telemetry periodically to indicate that
the service is alive.
"""
 
import threading
import time
 
from app.telemetry.tracing import tracer
from app.telemetry.metrics import heartbeat_counter
from app.telemetry.logging import logger
 
 
def heartbeat_worker(interval: int = 60):
    """
    Emit heartbeat every interval seconds.
    """
 
    while True:
 
        with tracer.start_as_current_span("heartbeat") as span:
 
            span.set_attribute(
                "heartbeat.interval",
                interval
            )

            span.set_attribute(
                "component",
                "file-scan-service"
            )
 
            logger.info(
                "Heartbeat: Service heartbeat"
            )
 
            heartbeat_counter.add(
                1,
                {
                    "component": "file-scan-service",
                    "component.type": "ServiceBusListener",
                    "status": "UP"
                }
            )
 
        time.sleep(interval)
 
 
def start_heartbeat(interval: int = 60):
    """
    Start heartbeat thread.
    """
 
    thread = threading.Thread(
        target=heartbeat_worker,
        args=(interval,),
        daemon=True,
        name="heartbeat-thread"
    )
 
    thread.start()