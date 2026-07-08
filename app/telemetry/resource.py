from opentelemetry.sdk.resources import Resource
from app.config.settings import Settings

resource = Resource.create(
    {
        "service.name": Settings.OTEL_SERVICE_NAME,
        "service.version": Settings.OTEL_SERVICE_VERSION,
        "deployment.environment": Settings.ENVIRONMENT,
        "telemetry.sdk.name": "opentelemetry",
        "telemetry.sdk.language": "python",
        "component": "file-scan-service",
    }
)
