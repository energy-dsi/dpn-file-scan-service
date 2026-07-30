"""
AWS S3 Storage client.
"""

from app.config.settings import Settings
from app.config.aws_config import get_s3_client

from opentelemetry.trace import Status
from opentelemetry.trace import StatusCode

from app.telemetry import tracer, logger


s3 = get_s3_client()


def copy_object(file_name, source_bucket=None):

    with tracer.start_as_current_span("storage.copy_object") as span:
        
        span.set_attribute("storage.source_bucket", source_bucket)
        span.set_attribute("storage.file_name", file_name)
        
        copy_source = {
            "Bucket": source_bucket or Settings.S3_BUCKET_INBOUND,
            "Key": file_name,
        }

        try:
            s3.copy_object(
                CopySource=copy_source,
                Bucket=Settings.S3_BUCKET_OUTBOUND,
                Key=file_name,
            )
            logger.info("S3 copy done.")
        except Exception as ex:
            span.record_exception(ex)
            span.set_status(Status(StatusCode.ERROR))
            logger.exception(
                "S3 copy failed (%s/%s -> %s/%s).",
                copy_source["Bucket"],
                file_name,
                Settings.S3_BUCKET_OUTBOUND,
                file_name,
            )
            raise


def delete_source(file_name, bucket=None):

    with tracer.start_as_current_span("storage.delete_source") as span:
            
        span.set_attribute("storage.source_bucket", bucket)
        span.set_attribute("storage.file_name", file_name)
        
        try:
            s3.delete_object(
                Bucket=bucket or Settings.S3_BUCKET_INBOUND,
                Key=file_name,
            )
            logger.info("S3 delete done.")
        except Exception as ex:
            span.record_exception(ex)
            span.set_status(Status(StatusCode.ERROR))
            logger.exception(
                "S3 delete failed (%s/%s).",
                bucket or Settings.S3_BUCKET_INBOUND,
                file_name,
            )
            raise


def quarantine(file_name, source_bucket=None):

    with tracer.start_as_current_span("storage.quarantine") as span:

        span.set_attribute("storage.source_bucket", source_bucket)
        span.set_attribute("storage.file_name", file_name)

        copy_source = {
            "Bucket": source_bucket or Settings.S3_BUCKET_INBOUND,
            "Key": file_name,
        }

        try:
            s3.copy_object(
                CopySource=copy_source,
                Bucket=Settings.S3_BUCKET_QUARANTINE,
                Key=file_name,
            )
            logger.info("S3 quarantine copy done.")
        except Exception as ex:
            span.record_exception(ex)
            span.set_status(Status(StatusCode.ERROR))
            logger.exception(
                "S3 quarantine copy failed (%s/%s -> %s/%s).",
                copy_source["Bucket"],
                file_name,
                Settings.S3_BUCKET_QUARANTINE,
                file_name,
            )
            raise

    delete_source(file_name, bucket=source_bucket)