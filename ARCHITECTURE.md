# Document Insight Extraction System - Architecture

## Overview

This document describes the architecture and design decisions for the Document Insight Extraction System, a serverless application built with AWS CDK.

## Core Components

### 1. Infrastructure Layer (CDK)

**Base Stack** (`infrastructure/base_stack.py`)
- Provides common functionality for all stacks
- Manages environment-specific configuration
- Implements standardized naming conventions
- Handles resource tagging

**Future Stacks:**
- Cognito Stack: User authentication and authorization
- S3 Stack: Document storage and vector embeddings
- Lambda Stack: Document processing and insight extraction
- API Gateway Stack: REST and WebSocket APIs
- DynamoDB Stack: Insight caching
- AppRunner Stack: Frontend hosting

### 2. Processing Layer (Lambda)

**Document Processing Lambda** (Future)
- PDF text extraction using PyPDF2
- Image detection and OCR via Bedrock
- Text chunking with recursive splitter
- Embedding generation with Titan V2
- Vector storage in S3 Vectors
- WebSocket progress notifications

**Insight Extraction Lambda** (Future)
- DynamoDB cache checking
- Vector similarity search
- Bedrock-powered insight generation
- Cache management with TTL

### 3. Storage Layer

**S3 Buckets:**
- Document Bucket: Raw PDF storage
- Vector Bucket: Embeddings with metadata

**DynamoDB:**
- Cache Table: Insights with 24-hour TTL

### 4. API Layer

**REST API:**
- POST /documents/presigned-url
- GET /documents
- POST /insights/extract
- GET /insights/{docId}

**WebSocket API:**
- Real-time processing updates
- Connection management
- Progress notifications

### 5. Frontend Layer (React)

**Components:**
- Document upload with progress
- Document selection
- Prompt input
- Insight display

## Design Patterns

### Event-Driven Architecture
- S3 events trigger Lambda processing
- Asynchronous document processing
- Decoupled components

### Caching Strategy
- DynamoDB with TTL for insights
- Cache-first retrieval pattern
- Automatic expiration

### Metadata Filtering
- S3 Vectors metadata for document isolation
- Efficient per-document queries
- Scalable multi-tenant design

## Configuration Management

### Environment Contexts
All configuration is managed through `cdk.json` context:

```json
{
  "dev": {
    "lambda_memory": 3008,
    "lambda_timeout": 600,
    ...
  },
  "prod": {
    "lambda_memory": 10240,
    "lambda_timeout": 900,
    ...
  }
}
```

### Resource Naming
Pattern: `{project}-{resource-type}-{env}-{suffix}`

Example: `document-insight-lambda-dev-processor`

### Tagging Strategy
All resources tagged with:
- Project: DocumentInsightExtraction
- Environment: dev/prod
- ManagedBy: CDK
- Application: DocumentProcessing

## Security Architecture

### Authentication
- Cognito User Pools for user management
- JWT tokens for API authorization
- 24-hour token validity

### Authorization
- API Gateway Cognito authorizers
- IAM roles with least privilege
- Resource-level permissions

### Encryption
- S3: SSE-S3 encryption at rest
- DynamoDB: AWS-managed encryption
- TLS 1.2+ for data in transit

### Network Security
- API Gateway regional endpoints
- CORS configuration for AppRunner
- VPC endpoints (optional for production)

## Scalability

### Lambda
- Concurrent execution limits
- Reserved concurrency for critical functions
- ARM64 architecture for cost optimization

### DynamoDB
- On-demand billing mode
- Auto-scaling (future)
- Point-in-time recovery

### API Gateway
- Throttling: 1000-5000 req/sec
- Burst capacity: 2000-10000 req/sec
- Regional distribution

### AppRunner
- Auto-scaling: 1-10 instances (dev)
- Auto-scaling: 2-25 instances (prod)
- Health checks and automatic recovery

## Monitoring and Observability

### CloudWatch Metrics (Future)
- Lambda invocations, errors, duration
- API Gateway request count, latency
- DynamoDB read/write capacity
- Custom business metrics

### CloudWatch Logs
- Structured logging in JSON format
- Log retention: 30 days
- Log groups per Lambda function

### X-Ray Tracing (Future)
- End-to-end request tracing
- Service map visualization
- Performance bottleneck identification

### Alarms (Future)
- Lambda error rate > 5%
- API Gateway 5xx > 1%
- DynamoDB throttling
- S3 Vectors query latency > 5s

## Cost Optimization

### Compute
- Lambda ARM64 for 10% cost reduction
- Right-sized memory allocation
- Efficient batch processing

### Storage
- S3 lifecycle policies
- DynamoDB on-demand billing
- TTL for automatic cleanup

### AI Services
- Batch embedding requests
- Cache to reduce Bedrock calls
- Efficient prompt engineering

## Deployment Strategy

### CI/CD Pipeline (Future)
1. Code commit triggers build
2. Run unit and integration tests
3. Build Lambda layers via CodeBuild
4. Deploy infrastructure with CDK
5. Build and push frontend Docker image
6. Deploy to AppRunner

### Blue-Green Deployment
- Lambda aliases for versioning
- API Gateway stages
- Gradual traffic shifting

### Rollback Strategy
- CloudFormation stack rollback
- Lambda version pinning
- Database backup and restore

## Future Enhancements

1. **Multi-format Support**: DOCX, PPTX, images
2. **Advanced OCR**: AWS Textract integration
3. **Streaming Responses**: Real-time insight generation
4. **Collaborative Features**: Document sharing
5. **Custom Models**: Fine-tuned embeddings
6. **Analytics Dashboard**: Usage metrics and trends
7. **Batch Processing**: Bulk document uploads
8. **Version Control**: Document and insight history

## Development Workflow

### Local Development
1. Create virtual environment
2. Install dependencies
3. Configure AWS credentials
4. Synthesize CDK templates
5. Deploy to dev environment

### Testing
1. Unit tests for Lambda functions
2. Integration tests for APIs
3. End-to-end tests for workflows
4. Load testing for performance

### Code Quality
- Black for code formatting
- Flake8 for linting
- MyPy for type checking
- Pre-commit hooks

## References

- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/)
- [Amazon Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [S3 Vectors Documentation](https://docs.aws.amazon.com/s3/)
- [AWS Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
