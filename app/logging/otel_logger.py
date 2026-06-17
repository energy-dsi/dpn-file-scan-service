import logging
import json
from datetime import datetime


logger = logging.getLogger("file-scanner")

logger.setLevel(logging.INFO)

handler = logging.StreamHandler()

logger.addHandler(handler)


def log_scan_event(
    file_name,
    source_location,
    scan_result_type,
    status
):

    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "file_name": file_name,
        "source_location": source_location,
        "scan_result_type": scan_result_type,
        "status": status
    }

    logger.info(json.dumps(event))