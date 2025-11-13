# Insight Extractor Lambda Function

This Lambda function extracts structured insights from documents using vector search and Amazon Bedrock.

## Overview

The Insight Extractor Lambda handles two main operations:
1. **Extract Insights** (POST): Query document vectors and generate insights using Bedrock
2. **Retrieve Insights** (GET): Fetch cached insights from DynamoDB

## Architecture

```
API Gateway → Lambda → {
    Cache Manager → DynamoDB (check/store cache)
    Vector Query → S3 Vectors (semantic search)
    Insight Generator → Bedrock (Claude 3 Sonnet)
}
```

## Components

### cache_manager.py
- Check DynamoDB cache for existing insights
- Store new insights with 24-hour TTL
- Retrieve all cached insights for a document

### vector_query.py
- Generate query embeddings using Titan V2
- Query S3 Vectors with metadata filtering (by docId)
- Calculate cosine similarity for ranking
- Return top-k relevant text chunks

### insight_generator.py
- Format prompts with context chunks
- Invoke Bedrock (Claude 3 Sonnet) for insight extraction
- Parse and validate JSON responses
- Return structured insights

### insight_extractor.py
- Main Lambda handler
- Route POST/GET requests
- Orchestrate cache → query → generate flow
- Return API Gateway responses

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `VECTOR_BUCKET_NAME` | S3 Vector bucket name | `doc-insight-vectors-dev` |
| `VECTOR_INDEX_ARN` | S3 Vector index ARN | `arn:aws:s3:us-east-1:...` |
| `EMBED_MODEL_ID` | Titan V2 embedding model | `amazon.titan-embed-text-v2:0` |
| `INSIGHT_MODEL_ID` | Claude model for insights | `anthropic.claude-3-sonnet-20240229-v1:0` |
| `DYNAMODB_TABLE_NAME` | Cache table name | `doc-insight-cache-dev` |
| `REGION` | AWS region | `us-east-1` |
| `LOG_LEVEL` | Logging level | `INFO` |

## API Endpoints

### POST /insights/extract

Extract insights from a document.

**Request:**
```json
{
  "docId": "my-document",
  "prompt": "What are the key findings in this document?"
}
```

**Response (Cache Hit):**
```json
{
  "insights": {
    "summary": "...",
    "keyPoints": ["...", "..."],
    "entities": [...],
    "answer": "...",
    "confidence": 0.95
  },
  "source": "cache",
  "timestamp": 1234567890,
  "modelId": "anthropic.claude-3-sonnet-20240229-v1:0",
  "chunkCount": 5,
  "expiresAt": 1234654290
}
```

**Response (Generated):**
```json
{
  "insights": {
    "summary": "...",
    "keyPoints": ["...", "..."],
    "entities": [...],
    "answer": "...",
    "confidence": 0.95
  },
  "source": "generated",
  "chunkCount": 5,
  "processingTime": 12.34,
  "modelId": "anthropic.claude-3-sonnet-20240229-v1:0",
  "timestamp": 1234567890
}
```

### GET /insights/{docId}

Retrieve all cached insights for a document.

**Response:**
```json
{
  "docId": "my-document",
  "insights": [
    {
      "prompt": "What are the key findings?",
      "insights": {...},
      "extractionTimestamp": 1234567890,
      "expiresAt": 1234654290,
      "modelId": "anthropic.claude-3-sonnet-20240229-v1:0",
      "chunkCount": 5
    }
  ],
  "count": 1
}
```

## Workflow

### Insight Extraction Flow

1. **Receive Request**: Parse docId and prompt from API Gateway event
2. **Check Cache**: Query DynamoDB for existing insights
   - If found: Return cached insights immediately
   - If not found: Continue to generation
3. **Generate Query Embedding**: Use Titan V2 to embed the prompt
4. **Query Vectors**: Search S3 Vectors with metadata filter (docId)
5. **Retrieve Top-K Chunks**: Get 5 most relevant text chunks
6. **Generate Insights**: Call Bedrock with prompt + context
7. **Parse Response**: Extract and validate JSON insights
8. **Store in Cache**: Save to DynamoDB with 24-hour TTL
9. **Return Response**: Send insights to client

### Cache Retrieval Flow

1. **Receive Request**: Parse docId from path parameters
2. **Query DynamoDB**: Get all non-expired insights for document
3. **Format Response**: Return list of cached insights
4. **Return Response**: Send to client

## Performance

- **Cache Hit**: < 500ms (DynamoDB query only)
- **Cache Miss**: < 30s (vector query + Bedrock generation)
- **Memory**: 3008 MB (ARM64 for cost optimization)
- **Timeout**: 300 seconds (5 minutes)

## Error Handling

- **400 Bad Request**: Missing docId or prompt
- **404 Not Found**: No vectors found for document
- **500 Internal Server Error**: Processing failures

All errors include descriptive messages and are logged to CloudWatch.

## Dependencies

- **boto3**: AWS SDK (provided by Lambda layer)
- **Python 3.12**: Runtime

## Testing

```bash
# Test locally with SAM
sam local invoke InsightExtractorFunction -e events/extract.json

# Test deployed function
aws lambda invoke \
  --function-name doc-insight-dev-insight-extractor \
  --payload '{"body": "{\"docId\": \"test\", \"prompt\": \"test\"}"}' \
  response.json
```

## Monitoring

- **CloudWatch Logs**: `/aws/lambda/doc-insight-dev-insight-extractor`
- **Metrics**: Invocations, Duration, Errors, Throttles
- **X-Ray**: Distributed tracing (if enabled)

## Cost Optimization

1. **ARM64 Architecture**: 10% cost reduction vs x86_64
2. **DynamoDB Cache**: Reduces Bedrock API calls
3. **24-hour TTL**: Automatic cache cleanup
4. **Top-K Limiting**: Only retrieve 5 chunks (configurable)
