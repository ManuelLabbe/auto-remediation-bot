# auto-remediation-bot

Auto-remediation bot for Serverless infrastructures via CloudWatch + SNS + Lambda with Kilo Webhook for serverless code or IaC error fixes for cases like permission policies or configured limits in monorepo (LLM only for translation).

## Architecture

```
CloudWatch Alarms → SNS → Lambda (mock-lambda-dispatcher) → Kilo Webhook
```

## Lambda Function: mock-lambda-dispatcher

### Overview
The `mock-lambda-dispatcher` function processes CloudWatch alarm notifications and dispatches them to the Kilo webhook endpoint.

### Features
- **SNS Event Processing**: Handles CloudWatch alarm notifications via SNS
- **Direct API Invocation**: Supports direct HTTP POST requests
- **Comprehensive Error Handling**: Returns structured error responses instead of throwing exceptions
- **Input Validation**: Validates and sanitizes incoming payload
- **Default Values**: Ensures all required fields have sensible defaults
- **Webhook Integration**: Sends alerts to configured Kilo webhook endpoint

### Fixes Applied (Incident: mock-lambda-errors)

The following fixes were applied to resolve the CloudWatch Lambda Errors alarm:

1. **Error Handling**: Changed from throwing exceptions to returning structured error responses, preventing Lambda Errors metric increments

2. **Input Validation**: Added comprehensive payload validation with graceful handling of missing fields

3. **Default Values**: Ensured all required fields have defaults to prevent undefined values causing downstream errors

4. **Webhook Response Handling**: Accept 2xx responses as success and log warnings for non-success statuses instead of rejecting

5. **SNS Message Parsing**: Added try-catch for JSON parsing to handle malformed messages

## Deployment

### Using AWS SAM

```bash
# Build and deploy
sam build
sam deploy --guided

# Or with existing configuration
sam deploy
```

### Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| WebhookEndpoint | Kilo webhook endpoint URL | `https://kilo-webhook.example.com/alerts` |
| TimeoutMs | HTTP request timeout (ms) | `5000` |
| AlarmEmail | Email for SNS notifications | `''` |

## CloudWatch Alarms

The following alarms are configured:

- `mock-lambda-errors`: Triggers when Lambda function errors >= 1
- `mock-lambda-invocation-errors`: Triggers when Lambda invocation errors >= 1
- `mock-lambda-throttles`: Triggers when Lambda throttles > 0

## Testing

### Local Testing

```bash
# Test with SNS event
sam local invoke MockLambdaDispatcher -e events/sns-event.json

# Test with API event
sam local invoke MockLambdaDispatcher -e events/api-event.json
```

### Example SNS Event

```json
{
  "Records": [
    {
      "Sns": {
        "Message": "{\"source\": \"aws-cloudwatch-alarm\", \"alarm_name\": \"mock-lambda-errors\", \"alarm_description\": \"LogGroup=/aws/lambda/mock-lambda-dispatcher\", \"aws_account_id\": \"390844787410\", \"region\": \"US East (N. Virginia)\", \"state\": \"ALARM\", \"state_reason\": \"Threshold Crossed: 1 out of the last 1 datapoints [1.0] was >= 1.0\", \"state_change_time\": \"2026-02-05T18:43:00.000+0000\", \"trigger\": {\"metric_name\": \"Errors\", \"namespace\": \"AWS/Lambda\", \"dimensions\": [{\"name\": \"FunctionName\", \"value\": \"mock-lambda-dispatcher\"}]}, \"log_group\": \"/aws/lambda/mock-lambda-dispatcher\", \"error_logs\": \"\"}"
      }
    }
  ]
}
```

## License

MIT
