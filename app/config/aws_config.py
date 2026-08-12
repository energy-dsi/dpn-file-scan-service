"""
AWS configuration.

Creates reusable boto3 clients/resources for:

- S3 (MinIO locally / AWS S3 in cloud)
- SQS
- SNS
"""

from __future__ import annotations

import boto3

from botocore.config import Config

from app.config.settings import Settings


#
# Shared boto configuration
#

AWS_CONFIG = Config(
    region_name=Settings.AWS_REGION,
    retries={
        "max_attempts": 3,
        "mode": "standard",
    },
    s3={
        "addressing_style": "path",
    },
)


#
# Credentials
#
# Explicit keys are only passed to boto3 when set. Otherwise boto3 falls
# back to its default credential chain (env vars, shared config, instance
# or task role), which avoids hardcoding/expiring credentials in settings.
#

def _credential_kwargs():
    """
    Return boto3 credential kwargs, omitting unset values so the default
    credential chain is used instead.
    """

    kwargs = {}

    if Settings.AWS_ACCESS_KEY_ID:

        kwargs["aws_access_key_id"] = Settings.AWS_ACCESS_KEY_ID

    if Settings.AWS_SECRET_ACCESS_KEY:

        kwargs["aws_secret_access_key"] = Settings.AWS_SECRET_ACCESS_KEY

    if Settings.AWS_SESSION_TOKEN:

        kwargs["aws_session_token"] = Settings.AWS_SESSION_TOKEN

    return kwargs


#
# S3 (MinIO or AWS)
#

def get_s3_client():
    """
    Return configured S3 client.
    """

    kwargs = {
        "service_name": "s3",
        **_credential_kwargs(),
        "config": AWS_CONFIG,
        "verify": Settings.S3_VERIFY_SSL,
    }

    #
    # Local MinIO
    #

    if Settings.S3_ENDPOINT:

        kwargs["endpoint_url"] = Settings.S3_ENDPOINT

    return boto3.client(**kwargs)


def get_s3_resource():
    """
    Return configured S3 resource.
    """

    kwargs = {
        "service_name": "s3",
        **_credential_kwargs(),
        "config": AWS_CONFIG,
        "verify": Settings.S3_VERIFY_SSL,
    }

    if Settings.S3_ENDPOINT:

        kwargs["endpoint_url"] = Settings.S3_ENDPOINT

    return boto3.resource(**kwargs)


#
# SQS
#

def get_sqs_client():
    """
    Return configured SQS client.
    """

    kwargs = {
        "service_name": "sqs",
        **_credential_kwargs(),
        "config": AWS_CONFIG,
    }

    if Settings.SQS_ENDPOINT:

        kwargs["endpoint_url"] = Settings.SQS_ENDPOINT

    return boto3.client(**kwargs)


#
# SNS
#

def get_sns_client():
    """
    Return configured SNS client.
    """

    kwargs = {
        "service_name": "sns",
        **_credential_kwargs(),
        "config": AWS_CONFIG,
    }

    if Settings.SNS_ENDPOINT:

        kwargs["endpoint_url"] = Settings.SNS_ENDPOINT

    return boto3.client(**kwargs)