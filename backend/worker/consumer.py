import json
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services import queue
from backend.core.logging import get_logger
from backend.worker.agent import run_agent

logger = get_logger(__name__)


def run_consumer():
    logger.info("starting SQS consumer loop")
    while True:
        try:
            messages = queue.receive_messages(max_messages=1, wait_time=20)
            for message in messages:
                receipt_handle = message["ReceiptHandle"]
                try:
                    body = json.loads(message["Body"])
                    task_id = body.get("task_id")
                    goal = body.get("goal")
                    trace_id = body.get("trace_id")
                    logger.info(
                        "received SQS message running agent",
                        extra={
                            "trace_id": trace_id,
                            "task_id": task_id,
                            "goal": goal,
                            "message_id": message.get("MessageId"),
                        },
                    )
                    run_agent(task_id)
                    logger.info(
                        "agent completed deleting message",
                        extra={
                            "trace_id": trace_id,
                            "task_id": task_id,
                            "message_id": message.get("MessageId"),
                        },
                    )
                    queue.delete_message(receipt_handle)
                except Exception as inner:
                    logger.error(
                        "error processing message will retry",
                        extra={
                            "error": str(inner),
                            "message_id": message.get("MessageId"),
                            "task_id": body.get("task_id") if "body" in locals() else None,
                        },
                    )
        except KeyboardInterrupt:
            logger.info("consumer stopped by user")
            break
        except Exception as e:
            logger.error(
                "error in consumer loop sleeping before retry",
                extra={"error": str(e)},
            )
            time.sleep(5)


if __name__ == "__main__":
    run_consumer()
