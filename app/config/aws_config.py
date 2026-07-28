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

AWS_ACCESS_KEY = Settings.AWS_ACCESS_KEY_ID

AWS_SECRET_KEY = Settings.AWS_SECRET_ACCESS_KEY


#
# S3 (MinIO or AWS)
#

def get_s3_client():
    """
    Return configured S3 client.
    """

    kwargs = {
        "service_name": "s3",
        "aws_access_key_id": AWS_ACCESS_KEY,
        "aws_secret_access_key": AWS_SECRET_KEY,
        "config": AWS_CONFIG,
    }

    #
    # Local MinIO
    #

    if Settings.S3_ENDPOINT:

        kwargs["endpoint_url"] = Settings.S3_ENDPOINT

        kwargs["verify"] = False

    return boto3.client(**kwargs)


def get_s3_resource():
    """
    Return configured S3 resource.
    """

    kwargs = {
        "service_name": "s3",
        "aws_access_key_id": AWS_ACCESS_KEY,
        "aws_secret_access_key": AWS_SECRET_KEY,
        "config": AWS_CONFIG,
    }

    if Settings.S3_ENDPOINT:

        kwargs["endpoint_url"] = Settings.S3_ENDPOINT

        kwargs["verify"] = False

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
        "aws_access_key_id": AWS_ACCESS_KEY,
        "aws_secret_access_key": AWS_SECRET_KEY,
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
        "aws_access_key_id": AWS_ACCESS_KEY,
        "aws_secret_access_key": AWS_SECRET_KEY,
        "config": AWS_CONFIG,
    }

    if Settings.SNS_ENDPOINT:

        kwargs["endpoint_url"] = Settings.SNS_ENDPOINT

    return boto3.client(**kwargs)