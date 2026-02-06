import json
import logging
import os
import urllib.request
from datetime import datetime, timezone, timedelta

import boto3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

logs_client = boto3.client("logs")

WEBHOOK_URL = os.environ["WEBHOOK_URL"]


def lambda_handler(event, context):
    record = event["Records"][0]
    alarm_message = json.loads(record["Sns"]["Message"])

    if alarm_message.get("NewStateValue") != "ALARM":
        logger.info("Ignoring non-ALARM state: %s", alarm_message.get("NewStateValue"))
        return {"statusCode": 200, "body": "ignored"}

    log_group = resolve_log_group(alarm_message)
    state_change_time = alarm_message.get("StateChangeTime")
    error_logs = fetch_error_logs(log_group, state_change_time) if log_group else ""

    post_to_webhook(alarm_message, log_group, error_logs)

    return {"statusCode": 200, "body": "forwarded"}


def resolve_log_group(alarm_message):
    dimensions = (
        alarm_message.get("Trigger", {}).get("Dimensions") or []
    )
    for dim in dimensions:
        if dim.get("name") == "FunctionName":
            return f"/aws/lambda/{dim['value']}"
    return None


def fetch_error_logs(log_group, state_change_time=None):
    if state_change_time:
        try:
            end = datetime.fromisoformat(state_change_time.replace("+0000", "+00:00"))
        except (ValueError, AttributeError):
            end = datetime.now(timezone.utc)
    else:
        end = datetime.now(timezone.utc)

    start = end - timedelta(minutes=5)

    try:
        response = logs_client.filter_log_events(
            logGroupName=log_group,
            startTime=int(start.timestamp() * 1000),
            endTime=int(end.timestamp() * 1000),
            limit=20,
        )
    except Exception:
        logger.exception("Failed to fetch logs from %s", log_group)
        return ""

    messages = [evt.get("message", "") for evt in response.get("events", [])]
    return "\n".join(messages)


def post_to_webhook(alarm_message, log_group, error_logs):
    trigger = alarm_message.get("Trigger", {})
    dimensions = trigger.get("Dimensions") or []

    payload = {
        "source": "aws-cloudwatch-alarm",
        "alarm_name": alarm_message.get("AlarmName", ""),
        "alarm_description": alarm_message.get("AlarmDescription", ""),
        "aws_account_id": alarm_message.get("AWSAccountId", ""),
        "region": alarm_message.get("Region", ""),
        "state": alarm_message.get("NewStateValue", ""),
        "state_reason": alarm_message.get("NewStateReason", ""),
        "state_change_time": alarm_message.get("StateChangeTime", ""),
        "trigger": {
            "metric_name": trigger.get("MetricName", ""),
            "namespace": trigger.get("Namespace", ""),
            "dimensions": [
                {"name": d.get("name", ""), "value": d.get("value", "")}
                for d in dimensions
            ],
        },
        "log_group": log_group or "",
        "error_logs": error_logs,
    }

    body = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        WEBHOOK_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "AutoRemediationBot/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            logger.info("Webhook responded %s", resp.status)
    except Exception:
        logger.exception("Failed to POST to webhook")
        raise
