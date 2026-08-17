import json
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from backend.core.config import settings
from backend.core.logging import get_logger
from backend.core.tracing import get_trace_id

logger = get_logger(__name__)


def get_sqs_client():
    return boto3.client(
        "sqs",
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )


def publish_message(task_id: str, goal: str, trace_id: str) -> Optional[str]:
    if not settings.SQS_QUEUE_URL:
        logger.warning(
            "SQS queue URL not configured, skipping publish",
            extra={"trace_id": trace_id, "task_id": task_id},
        )
        return None

    client = get_sqs_client()
    body = json.dumps({"task_id": task_id, "goal": goal, "trace_id": trace_id})

    try:
        response = client.send_message(
            QueueUrl=settings.SQS_QUEUE_URL,
            MessageBody=body,
            MessageDeduplicationId=task_id,
            MessageGroupId="agentflow-tasks",
        )
        msg_id = response.get("MessageId")
        logger.info(
            "published message to SQS",
            extra={"trace_id": trace_id, "task_id": task_id, "message_id": msg_id},
        )
        return msg_id
    except ClientError as e:
        logger.error(
            "failed to publish message to SQS",
            extra={
                "trace_id": trace_id,
                "task_id": task_id,
                "error": str(e),
            },
        )
        raise


def receive_messages(max_messages: int = 1, wait_time: int = 20) -> list[dict]:
    if not settings.SQS_QUEUE_URL:
        return []

    client = get_sqs_client()
    try:
        response = client.receive_message(
            QueueUrl=settings.SQS_QUEUE_URL,
            MaxNumberOfMessages=max_messages,
            WaitTimeSeconds=wait_time,
            VisibilityTimeout=300,
        )
        return response.get("Messages", [])
    except ClientError as e:
        trace_id = get_trace_id()
        logger.error(
            "failed to receive messages from SQS",
            extra={"trace_id": trace_id, "error": str(e)},
        )
        return []


def delete_message(receipt_handle: str) -> None:
    if not settings.SQS_QUEUE_URL:
        return

    client = get_sqs_client()
    trace_id = get_trace_id()
    try:
        client.delete_message(
            QueueUrl=settings.SQS_QUEUE_URL,
            ReceiptHandle=receipt_handle,
        )
    except ClientError as e:
        logger.error(
            "failed to delete message from SQS",
            extra={"trace_id": trace_id, "error": str(e)},
        )


def get_dlq_depth() -> int:
    if not settings.SQS_DLQ_URL:
        return 0

    client = get_sqs_client()
    try:
        response = client.get_queue_attributes(
            QueueUrl=settings.SQS_DLQ_URL,
            AttributeNames=["ApproximateNumberOfMessages"],
        )
        return int(response["Attributes"]["ApproximateNumberOfMessages"])
    except (ClientError, KeyError, ValueError):
        return 0
