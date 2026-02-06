# Auto Remediation Bot

Forwards CloudWatch alarm events to a KiloCode webhook. Designed to plug into any existing AWS infrastructure without modifying it.

```
CloudWatch Alarm  →  SNS Topic  →  Forwarder Lambda  →  KiloCode Webhook
```

## Supported Serverless Services

| Service | Log Forwarding | Status |
|---|---|---|
| AWS Lambda | [x] Errors, Timeouts, Throttles | Supported |
| API Gateway | [ ] 5XX Errors, Latency, Throttling | Planned |
| DynamoDB | [ ] Throttled Reads/Writes, Capacity Errors | Planned |
| SQS | [ ] Dead Letter Queue, Message Age | Planned |
| Step Functions | [ ] Failed Executions | Planned |
| EventBridge | [ ] Failed Rule Invocations | Planned |
| S3 | [ ] 5XX Request Errors | Planned |

## Prerequisites

- AWS CLI configured with a valid profile
- AWS SAM CLI installed
- An AWS account with permissions to create Lambda, SNS, CloudWatch, and IAM resources

## Deployment

Build and deploy the forwarder stack:

```bash
sam build
sam deploy \
  --stack-name auto-remediation-bot \
  --profile <your-aws-profile> \
  --region us-east-1 \
  --capabilities CAPABILITY_IAM \
  --resolve-s3 \
  --no-confirm-changeset
```

After deployment, note the `ErrorAlarmTopicArn` output — this is the SNS topic ARN you will use to couple existing alarms.

## KiloCode Configuration

<!-- TODO: Add KiloCode webhook configuration instructions -->

## Coupling an Existing Alarm

To connect any existing CloudWatch alarm to the forwarder, add the SNS topic ARN as an alarm action. This is the only change needed — no modifications to the existing infrastructure.

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name <your-alarm-name> \
  --alarm-actions arn:aws:sns:us-east-1:<account-id>:error-alarm-forwarder \
  --namespace <your-namespace> \
  --metric-name <your-metric> \
  --dimensions Name=<dim-name>,Value=<dim-value> \
  --statistic Sum \
  --period 60 \
  --evaluation-periods 1 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --treat-missing-data notBreaching \
  --profile <your-aws-profile> \
  --region us-east-1
```

---

## Mock Infrastructure (Demo / Testing)

The `mock/` directory contains a standalone Lambda with intentional bugs that simulates a pre-existing client infrastructure. It has no knowledge of the forwarder or KiloCode.

### Deploy the Mock

```bash
sam build --template-file mock/template.yaml
sam deploy \
  --template-file mock/template.yaml \
  --stack-name mock-infrastructure \
  --profile <your-aws-profile> \
  --region us-east-1 \
  --capabilities CAPABILITY_IAM \
  --resolve-s3 \
  --no-confirm-changeset
```

### Couple the Mock Alarm to the Forwarder

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name mock-lambda-errors \
  --alarm-actions arn:aws:sns:us-east-1:<account-id>:error-alarm-forwarder \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=mock-lambda-dispatcher \
  --statistic Sum \
  --period 60 \
  --evaluation-periods 1 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --treat-missing-data notBreaching \
  --profile <your-aws-profile> \
  --region us-east-1
```

### Test Commands

The mock Lambda includes three functions, each with a different intentional bug:

**Function A — ZeroDivisionError** (empty list)

```bash
aws lambda invoke \
  --function-name mock-lambda-dispatcher \
  --profile <your-aws-profile> \
  --region us-east-1 \
  --cli-binary-format raw-in-base64-out \
  --payload '{"function": "a", "items": []}' \
  /dev/stdout
```

**Function B — TypeError** (string + int concatenation)

```bash
aws lambda invoke \
  --function-name mock-lambda-dispatcher \
  --profile <your-aws-profile> \
  --region us-east-1 \
  --cli-binary-format raw-in-base64-out \
  --payload '{"function": "b", "name": "Alice", "age": 30}' \
  /dev/stdout
```

**Function C — Timeout** (sleep exceeds 1s Lambda timeout)

```bash
aws lambda invoke \
  --function-name mock-lambda-dispatcher \
  --profile <your-aws-profile> \
  --region us-east-1 \
  --cli-binary-format raw-in-base64-out \
  --payload '{"function": "c", "duration": 2}' \
  /dev/stdout
```

### Force Alarm (Manual Trigger)

The mock dispatcher catches exceptions internally, so CloudWatch does not count them as Lambda `Errors`. To test the full end-to-end flow, force the alarm state manually:

```bash
aws cloudwatch set-alarm-state \
  --alarm-name mock-lambda-errors \
  --state-value ALARM \
  --state-reason "Manual test" \
  --profile <your-aws-profile> \
  --region us-east-1
```
