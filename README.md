# Auto Remediation Bot

Forwards CloudWatch alarm events to a KiloCode webhook. Designed to plug into any existing AWS infrastructure without modifying it.

```
CloudWatch Alarm  →  SNS Topic  →  Forwarder Lambda  →  KiloCode Webhook
```

## Supported Serverless Services

| Service | Log Forwarding | Status |
|---|---|---|
| AWS Lambda | [x] Errors, Timeouts, Throttles | Supported |
| API Gateway | [ ] 5XX Errors, Latency, Throttling | Not supported |
| DynamoDB | [ ] Throttled Reads/Writes, Capacity Errors | Not supported |
| SQS | [ ] Dead Letter Queue, Message Age | Not supported |
| Step Functions | [ ] Failed Executions | Not supported |
| EventBridge | [ ] Failed Rule Invocations | Not supported |
| S3 | [ ] 5XX Request Errors | Not supported |

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
  --no-confirm-changeset \
  --parameter-overrides "WebhookUrl=<your-kilocode-webhook-url>"
```

After deployment, note the `ErrorAlarmTopicArn` output — this is the SNS topic ARN you will use to couple existing alarms.

## KiloCode Configuration

1. Create a webhook in KiloCode pointing to the repository that contains both the application code and the AWS IaC (Infrastructure as Code).
2. Copy the webhook URL provided by KiloCode.
3. Pass it as `WebhookUrl` during deployment (see [Deployment](#deployment)).
4. Configure the prompt template below in your KiloCode webhook settings.

**Model used for testing:** Minimax M2.1

### Prompt Template

```
### ROLE
You are an expert DevOps and Serverless Engineer specializing in AWS architectures. You operate as the intelligence engine behind an auto-remediation pipeline (CloudWatch → SNS → Lambda → Kilo Webhook).

### TASK
Your goal is to analyze the error provided below, generate the necessary corrections (commit), and prepare a Pull Request targeting the `main` branch to resolve the incident.

### DECISION LOGIC & GUIDELINES
Analyze the nature of the error in the log and apply one of the following workflows:

1. **Application Code Errors:**
   - If the error is caused by logic, syntax, or runtime exceptions, correct the code to restore functionality.
   - **Constraint:** You must strictly adhere to the existing code style, patterns, and linting rules of the repository.

2. **Infrastructure (IaC) Errors:**
   - If the error is related to infrastructure (e.g., IAM permission policies, Lambda timeouts, memory limits, throttling), resolve it by modifying the Infrastructure as Code (IaC) configuration files.

3. **Complex/Manual Errors:**
   - If the error cannot be resolved programmatically (e.g., requires external decisions, architectural overrides, or is ambiguous), you must generate a documentation file (e.g., `MANUAL_FIX_INSTRUCTIONS.md`) to be included in the commit.
   - This file must contain a clear, step-by-step guide for a human engineer to resolve the issue.

### FINAL VERIFICATION PHASE
Before finalizing the output, you must validate the deployment strategy:
1. **Branch Status:** Confirm that the fix is on a new, dedicated branch and pushed to the remote repository.
2. **PR Target Check:** rigorously verify that the Pull Request is set to merge into **`main`**. Use gh pr create --base main
3. **Integrity Check:** Ensure the PR includes the necessary context for approval (summary, root cause, and solution).

### OUTPUT FORMAT
Your output must be formatted as a formal **Pull Request (PR) Description** containing:
- **Verification Status:** [PASSED] - Branch pushed and PR targets `main`.
- **Target Branch:** `main`
- **Issue Summary:** A concise explanation of the error found.
- **Root Cause:** A technical breakdown of why the error occurred.
- **Proposed Solution:** A detailed explanation of the changes made (Code vs. IaC) or the instructions provided.

### ERROR LOG TO RESOLVE
The specific error payload received from the monitoring system is:
{{body}}
```

### Production Recommendations

- **Webhook Authentication:** Enable the `x-secret-webhook-secret` header in your KiloCode webhook settings to authenticate incoming requests. This prevents unauthorized payloads from triggering the remediation pipeline.
- **Webhook Retry:** Add retry logic with exponential backoff when the webhook returns 5XX or times out, to avoid losing events due to transient failures.
- **Dead Letter Queue:** Configure a DLQ on the forwarder Lambda so that failed events are preserved for later inspection or reprocessing instead of being silently dropped.
- **Throttling Protection:** Add concurrency limits on the forwarder Lambda to prevent a burst of alarms from overwhelming the webhook endpoint.

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

---

## Future Work

- **Agent Skills:** Enable the remediation agent to have configurable "skills" — structured knowledge about the AWS infrastructure architecture, coding guidelines, and business rules of the project. This additional context would allow the agent to generate more accurate and aligned solutions when creating Pull Requests, especially for domain-specific logic or organization-level conventions that cannot be inferred from code alone.
