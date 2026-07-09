from opentelemetry import metrics



meter = metrics.get_meter("file-scan-service")

messages_counter = meter.create_counter("messages_processed")

files_counter = meter.create_counter("files_copied")

malware_counter = meter.create_counter("malicious_files")

processing_time = meter.create_histogram("processing_duration_ms")

heartbeat_counter = meter.create_counter(
    name="heartbeat_total", description="Heartbeat count", unit="1"
)
