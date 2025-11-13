# Document Insight Extraction - Project Structure

## Overview
This document describes the complete project structure for Task 1: CDK project setup and core infrastructure.

## Directory Structure

```
document-insight-extraction/
├── app.py                          # Main CDK application entry point
├── cdk.json                        # CDK configuration with dev/prod contexts
├── cdk.context.json                # CDK runtime context (auto-generated)
├── requirements.txt                # Python dependencies for CDK
├── requirements-dev.txt            # Development dependencies
├── setup.py                        # Python package configuration
├── .gitignore                      # Git ignore patterns
├── LICENSE                         # MIT License
├── README.md                       # Project documentation
├── ARCHITECTURE.md                 # Architecture documentation
├── buildspec.yml                   # CodeBuild specification
├── deploy.sh                       # Deployment automation script
├── destroy.sh                      # Resource cleanup script
│
├── infrastructure/                 # CDK stack definitions
│   ├── __init__.py                # Package initialization
│   └── base_stack.py              # Base stack with common utilities
│
├── lambda/                         # Lambda function code (placeholder)
│   └── __init__.py                # Package initialization
│
├── frontend/                       # React application (placeholder)
│   └── .gitkeep                   # Directory placeholder
│
└── tests/                          # Test suite (placeholder)
    └── __init__.py                # Package initialization
```

## Key Files Created

### 1. app.py
- CDK application entry point
- Environment configuration loading
- Stack instantiation
- Common tagging

### 2. infrastructure/base_stack.py
- Base stack class with common functionality
- Standardized naming conventions
- Configuration management
- Resource naming helpers
- Stack output utilities
- Common tags

### 3. cdk.json
- CDK app configuration
- Feature flags for CDK behavior
- Environment contexts (dev/prod):
  - S3 bucket names
  - DynamoDB table names
  - Lambda configuration (memory, timeout)
  - Bedrock model IDs
  - API throttling settings
  - AppRunner configuration
  - Cognito settings

### 4. requirements.txt
- aws-cdk-lib==2.192.0
- constructs>=10.0.0,<11.0.0
- boto3>=1.34.0

### 5. Deployment Scripts
- **deploy.sh**: Automated deployment with environment selection
- **destroy.sh**: Safe resource cleanup with confirmation

## Configuration Details

### Development Environment (dev)
```json
{
  "lambda_memory": 3008,
  "lambda_timeout": 600,
  "apprunner_cpu": "2048",
  "apprunner_memory": "4096",
  "api_throttle_rate": 1000
}
```

### Production Environment (prod)
```json
{
  "lambda_memory": 10240,
  "lambda_timeout": 900,
  "apprunner_cpu": "4096",
  "apprunner_memory": "8192",
  "api_throttle_rate": 5000
}
```

## Naming Conventions

### Resource Naming Pattern
`{project}-{resource-type}-{env}-{suffix}`

Examples:
- S3 Bucket: `doc-insight-docs-dev-123456789012`
- Lambda: `document-insight-lambda-dev-processor`
- DynamoDB: `doc-insight-cache-dev`

### Stack Naming Pattern
`DocumentInsight{Env}Stack`

Examples:
- Development: `DocumentInsightDevStack`
- Production: `DocumentInsightProdStack`

## Tagging Strategy

All resources are tagged with:
- **Project**: DocumentInsightExtraction
- **Environment**: dev/prod
- **ManagedBy**: CDK
- **Application**: DocumentProcessing

## Next Steps

The following stacks will be implemented in subsequent tasks:

1. **Task 2**: Cognito Authentication Stack
2. **Task 3**: S3 Bucket Infrastructure
3. **Task 4**: Lambda Layer Build Infrastructure
4. **Task 5**: DynamoDB Cache Table
5. **Task 6**: API Gateway REST API
6. **Task 7**: API Gateway WebSocket API
7. **Task 8**: Document Processing Lambda
8. **Task 9**: Insight Extraction Lambda
9. **Task 10**: React Frontend Application
10. **Task 11**: AppRunner Hosting Infrastructure
11. **Task 12**: Deployment and Configuration

## Usage

### Deploy to Development
```bash
./deploy.sh dev
```

### Deploy to Production
```bash
./deploy.sh prod
```

### Destroy Resources
```bash
./destroy.sh dev
```

### Manual CDK Commands
```bash
# Synthesize CloudFormation template
cdk synth --context env=dev

# Deploy stacks
cdk deploy --context env=dev --all

# List stacks
cdk ls --context env=dev

# View differences
cdk diff --context env=dev
```

## Requirements Satisfied

This implementation satisfies the following requirements from the spec:

- **Requirement 10.1**: All AWS resources defined using AWS CDK with Python
- **Requirement 10.2**: Separate CDK Stack modules created (base stack foundation)
- **Requirement 10.2**: Environment configuration with dev/prod contexts
- **Requirement 10.2**: Common tags and naming conventions established

## Task Completion Checklist

- [x] Create main CDK app entry point with environment configuration
- [x] Define base stack class with common tags and naming conventions
- [x] Configure cdk.json with context parameters for dev/prod environments
- [x] Set up requirements.txt with CDK dependencies
