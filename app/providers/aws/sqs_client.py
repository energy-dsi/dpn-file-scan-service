"""
AWS SQS client.
"""

import json

from app.config.settings import Settings
from app.config.aws_config import get_sqs_client

from opentelemetry.trace import Status
from opentelemetry.trace import StatusCode
from app.telemetry import tracer, logger


from functools import lru_cache

@lru_cache(maxsize=1)
def get_sqs():
    return get_sqs_client()


def get_queue_url():

    sqs = get_sqs()

    logger.info(
        f"SQS Queue = {Settings.SQS_QUEUE}"
    )

    logger.info(
        f"SQS Endpoint = {Settings.SQS_ENDPOINT}"
    )
    
    response = sqs.get_queue_url(
        QueueName=Settings.SQS_QUEUE
    )

    return response["QueueUrl"]


def receive_messages():

    url = get_queue_url()
    sqs = get_sqs()

    return sqs.receive_message(
        QueueUrl=url,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=10,
    )


def delete_message(receipt_handle):

    url = get_queue_url()
    sqs = get_sqs()

    sqs.delete_message(
        QueueUrl=url,
        ReceiptHandle=receipt_handle,
    )