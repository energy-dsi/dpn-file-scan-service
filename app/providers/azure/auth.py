"""
Azure authentication.
 
Provides Azure Service Principal credentials using secrets mounted
from Kubernetes/Key Vault.
"""
 
from pathlib import Path
 
from azure.identity import ClientSecretCredential
from opentelemetry.trace import Status
from opentelemetry.trace import StatusCode
 
from app.config.settings import Settings
from app.telemetry import tracer, logger
 
 
def read_secret(path: str) ->str:
    """
    Read secret from mounted file.
    """
 
    with tracer.start_as_current_span(
        "auth.read_secret"
    ) as span:
 
        span.set_attribute(
            "secret.file",
            path
        )
 
        try:
 
            value = (
                Path(path)
                .read_text()
                .strip()
            )
 
            return value
 
        except FileNotFoundError as ex:
 
            span.record_exception(ex)
 
            span.set_status(
                Status(StatusCode.ERROR)
            )
 
            logger.exception(
                "Secret file not found."
            )
 
            raise RuntimeError(
                f"Secret file not found: {path}"
            ) from ex
 
 
def get_credential():
    """
    Return Azure Service Principal credential.
    """
 
    with tracer.start_as_current_span(
        "auth.get_credential"
    ) as span:
 
        try:
 
            client_id = read_secret(
                Settings.CLIENT_ID_FILE
            )
 
            client_secret = read_secret(
                Settings.CLIENT_SECRET_FILE
            )
 
            credential = ClientSecretCredential(
                tenant_id=Settings.TENANT_ID,
                client_id=client_id,
                client_secret=client_secret
            )
 
            logger.info(
                "Azure credential created."
            )
 
            return credential
 
        except Exception as ex:
 
            span.record_exception(ex)
 
            span.set_status(
                Status(StatusCode.ERROR)
            )
 
            logger.exception(
                "Credential creation failed."
            )
 
            raise