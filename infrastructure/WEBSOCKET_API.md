# WebSocket API Documentation

## Overview

The WebSocket API provides real-time bidirectional communication between the frontend and backend for document processing progress updates.

## Architecture

The WebSocket API is implemented using AWS API Gateway V2 with the following components:

- **WebSocket API**: API Gateway V2 with WEBSOCKET protocol
- **Routes**: $connect, $disconnect, $default, and progress
- **Integration**: Lambda proxy integration for connection handling
- **IAM Role**: Allows API Gateway to invoke Lambda functions

## Routes

### $connect
- **Purpose**: Handles new WebSocket connections
- **Trigger**: When a client establishes a WebSocket connection
- **Handler**: Connection handler Lambda function
- **Use Case**: Authenticate connection, store connection ID

### $disconnect
- **Purpose**: Handles WebSocket disconnections
- **Trigger**: When a client closes the WebSocket connection
- **Handler**: Connection handler Lambda function
- **Use Case**: Clean up connection ID from storage

### $default
- **Purpose**: Handles messages that don't match any specific route
- **Trigger**: When a client sends a message without a matching route
- **Handler**: Connection handler Lambda function
- **Use Case**: Default message processing, error handling

### progress
- **Purpose**: Handles document processing progress updates
- **Trigger**: When a client sends a message with action="progress"
- **Handler**: Connection handler Lambda function
- **Use Case**: Request progress updates for a specific document

## Route Selection

The WebSocket API uses the following route selection expression:
```
$request.body.action
```

This means messages should include an `action` field to route to specific handlers:
```json
{
  "action": "progress",
  "docId": "document-id-here"
}
```

## Message Flow

### Client → Server (Incoming)
1. Client sends message with action field
2. API Gateway routes to appropriate Lambda function
3. Lambda processes message and returns response

### Server → Client (Outgoing)
1. Lambda function calls API Gateway Management API
2. API Gateway sends message to specific connection ID
3. Client receives message via WebSocket

## Progress Update Messages

### Processing Started
```json
{
  "status": "processing_started",
  "docId": "uuid",
  "totalPages": 100
}
```

### Progress Update
```json
{
  "status": "progress",
  "docId": "uuid",
  "pagesProcessed": 50,
  "totalPages": 100
}
```

### Processing Complete
```json
{
  "status": "processing_complete",
  "docId": "uuid"
}
```

### Error
```json
{
  "status": "error",
  "errorCode": "PROCESSING_FAILED",
  "message": "Error description",
  "docId": "uuid",
  "recoverable": false
}
```

## IAM Permissions

### API Gateway → Lambda
The WebSocket API has an IAM role that allows it to invoke Lambda functions:
- Action: `lambda:InvokeFunction`
- Resource: Connection handler Lambda ARN

### Lambda → API Gateway
Lambda functions need permission to send messages to connected clients:
- Action: `execute-api:ManageConnections`
- Resource: `arn:aws:execute-api:{region}:{account}:{api-id}/{stage}/*`

This permission is granted via the `grant_manage_connections()` method.

## Configuration

The WebSocket API is configured with the following settings:

- **Throttling**: Configurable via `api_throttle_rate` and `api_throttle_burst` in cdk.json
- **Logging**: INFO level with data trace enabled
- **Metrics**: Detailed metrics enabled
- **Timeout**: 29 seconds (API Gateway maximum)

## Usage in CDK

### Creating the Stack
```python
websocket_api_stack = WebSocketApiStack(
    app,
    "WebSocketApiStack",
    env_name="dev",
    config=config
)
```

### Configuring Routes
```python
# After creating Lambda function
websocket_api_stack.configure_websocket_routes(
    connection_handler_lambda=connection_handler
)

# Add WebSocket URL output
websocket_api_stack.add_websocket_url_output()
```

### Granting Permissions
```python
# Grant Lambda permission to send messages to clients
websocket_api_stack.grant_manage_connections(
    document_processor_lambda
)
```

## Frontend Integration

### Connecting
```javascript
const wsUrl = 'wss://{api-id}.execute-api.{region}.amazonaws.com/{stage}';
const ws = new WebSocket(wsUrl);

ws.onopen = () => {
  console.log('WebSocket connected');
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  handleProgressUpdate(message);
};
```

### Sending Messages
```javascript
ws.send(JSON.stringify({
  action: 'progress',
  docId: 'document-id'
}));
```

## Monitoring

### CloudWatch Logs
- API Gateway access logs: `/aws/apigateway/{api-name}/{stage}`
- Lambda function logs: `/aws/lambda/{function-name}`

### CloudWatch Metrics
- Connection count
- Message count
- Integration latency
- Error count

## Security

### Authentication
Currently configured with `NONE` authorization type. In production, consider:
- Cognito User Pool authorizer
- Lambda authorizer
- IAM authorization

### Connection Management
- Connection IDs should be stored securely
- Implement connection timeout
- Clean up stale connections

## Troubleshooting

### Connection Fails
- Check Lambda function permissions
- Verify IAM role for API Gateway
- Check CloudWatch logs for errors

### Messages Not Received
- Verify connection ID is valid
- Check Lambda has ManageConnections permission
- Verify API Gateway endpoint URL

### High Latency
- Check Lambda cold start times
- Review Lambda memory allocation
- Monitor API Gateway throttling
