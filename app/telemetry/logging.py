import json
import logging
 
from datetime import datetime, timezone
 
from opentelemetry._logs import get_logger_provider
from opentelemetry.sdk._logs import LoggingHandler
 
from app.config.settings import Settings
 
 
SEVERITY_MAP = {
    logging.DEBUG: (5, "DEBUG"),
    logging.INFO: (9, "INFO"),
    logging.WARNING: (13, "WARN"),
    logging.ERROR: (17, "ERROR"),
    logging.CRITICAL: (21, "FATAL"),
}
 
 
class OTELJsonFormatter(logging.Formatter):
    """
    Formats Python LogRecords into OTEL-compatible JSON.
    """
 
    def format(self, record: logging.LogRecord) -> str:
 
        now = datetime.now(timezone.utc).isoformat()
 
        severity_number, severity_text = SEVERITY_MAP.get(
            record.levelno,
            (9, "INFO")
        )
 
        log_entry = {
            "timestamp": now,
            "observed_timestamp": now,
            "severity_number": severity_number,
            "severity_text": severity_text,
            "body": record.getMessage(),
            "component": "file-scan-service",
        }
 
        #
        # Include custom attributes passed through logger.info(..., extra={})
        #
 
        reserved = {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "message",
        }
 
        for key, value in record.__dict__.items():
 
            if key not in reserved:
 
                #log_entry["attributes"][key] = value
                log_entry[key] = value
 
        return json.dumps(log_entry, default=str)
 
 
logger = logging.getLogger("file-scan-service")
 
logger.setLevel(logging.INFO)
 
formatter = OTELJsonFormatter()
 
 
#
# Console Handler
#
 
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
 
 
#
# OTEL Handler
#
 
otel_handler = LoggingHandler(
    logger_provider=get_logger_provider()
)
 
otel_handler.setFormatter(formatter)
 
 
if not logger.handlers:
 
    logger.addHandler(console_handler)
    logger.addHandler(otel_handler)