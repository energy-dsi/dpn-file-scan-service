import logging
 
from opentelemetry._logs import get_logger_provider
 
from opentelemetry.sdk._logs import LoggingHandler
 
 
logger = logging.getLogger("file-scan-service")
 
logger.setLevel(logging.INFO)
 
formatter = logging.Formatter(
    "%(asctime)s %(levelname)s %(message)s"
)
 
#
# Console
#
 
console_handler = logging.StreamHandler()
 
console_handler.setFormatter(formatter)
 
#
# OTEL
#
 
otel_handler = LoggingHandler(
    logger_provider=get_logger_provider()
)
 
if not logger.handlers:
 
    logger.addHandler(console_handler)
 
    logger.addHandler(otel_handler)