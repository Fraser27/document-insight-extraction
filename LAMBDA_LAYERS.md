# Lambda Layers Setup Guide

This document provides a quick reference for setting up and using Lambda layers in the Document Insight Extraction System.

## Quick Start

### 1. Deploy the Lambda Layer Stack

```bash
# Deploy the infrastructure
cdk deploy DocumentInsightLambdaLayerDevStack

# Or for production
cdk deploy DocumentInsightLambdaLayerProdStack
```

This creates:
- S3 bucket for build artifacts
- CodeBuild projects for pypdf and boto3 layers
- IAM roles with necessary permissions

### 2. Build the Layers

```bash
# Build all layers (pypdf and boto3, both x86_64 and ARM64) for dev environment
./scripts/build_lambda_layers.sh dev

# Or trigger via AWS CLI
aws codebuild start-build --project-name document-insight-layers-dev
```

This single command builds all 4 layers in one execution (~5-8 minutes).

### 3. Get Layer ARNs

After successful builds, retrieve the layer ARNs:

```bash
# List pypdf layer versions
aws lambda list-layer-versions \
  --layer-name document-insight-pypdf-layer-dev-x86-64 \
  --max-items 1

# List boto3 layer versions
aws lambda list-layer-versions \
  --layer-name document-insight-boto3-layer-dev-arm64 \
  --max-items 1
```

## Layer Details

### pypdf Layer

**Purpose**: PDF text extraction using PyPDF2

**Architectures**:
- `document-insight-pypdf-layer-{env}-x86-64`
- `document-insight-pypdf-layer-{env}-arm64`

**Runtime**: Python 3.12

**Size**: ~5 MB

**Use Case**: Document Processing Lambda (x86_64)

### boto3 Layer

**Purpose**: Latest AWS SDK with S3 Vectors API support

**Architectures**:
- `document-insight-boto3-layer-{env}-x86-64`
- `document-insight-boto3-layer-{env}-arm64`

**Runtimes**: Python 3.12, 3.11, 3.10

**Size**: ~50 MB

**Use Cases**: 
- Document Processing Lambda (x86_64)
- Insight Extraction Lambda (ARM64)

## Using Layers in Lambda Functions

### Example: Document Processing Lambda

```python
from aws_cdk import aws_lambda as lambda_

# Get layer ARNs from environment or SSM Parameter Store
pypdf_layer_arn = "arn:aws:lambda:us-east-1:123456789012:layer:document-insight-pypdf-layer-dev-x86-64:1"
boto3_layer_arn = "arn:aws:lambda:us-east-1:123456789012:layer:document-insight-boto3-layer-dev-x86-64:1"

# Create Lambda function with layers
document_processor = lambda_.Function(
    self,
    "DocumentProcessor",
    runtime=lambda_.Runtime.PYTHON_3_12,
    architecture=lambda_.Architecture.X86_64,
    handler="document_processor.handler",
    code=lambda_.Code.from_asset("lambda/document_processor"),
    layers=[
        lambda_.LayerVersion.from_layer_version_arn(self, "PypdfLayer", pypdf_layer_arn),
        lambda_.LayerVersion.from_layer_version_arn(self, "Boto3Layer", boto3_layer_arn)
    ],
    memory_size=3008,
    timeout=Duration.seconds(600)
)
```

### Example: Insight Extraction Lambda (ARM64)

```python
# Get ARM64 boto3 layer
boto3_layer_arn = "arn:aws:lambda:us-east-1:123456789012:layer:document-insight-boto3-layer-dev-arm64:1"

insight_extractor = lambda_.Function(
    self,
    "InsightExtractor",
    runtime=lambda_.Runtime.PYTHON_3_12,
    architecture=lambda_.Architecture.ARM64,  # Graviton2 for cost savings
    handler="insight_extractor.handler",
    code=lambda_.Code.from_asset("lambda/insight_extractor"),
    layers=[
        lambda_.LayerVersion.from_layer_version_arn(self, "Boto3LayerArm", boto3_layer_arn)
    ],
    memory_size=3008,
    timeout=Duration.seconds(300)
)
```

## Automation

### Store Layer ARNs in SSM Parameter Store

After building layers, store ARNs for easy reference:

```bash
# Store pypdf layer ARN
aws ssm put-parameter \
  --name "/document-insight/dev/layer/pypdf-x86-64" \
  --value "arn:aws:lambda:us-east-1:123456789012:layer:document-insight-pypdf-layer-dev-x86-64:1" \
  --type String \
  --overwrite

# Store boto3 layer ARNs
aws ssm put-parameter \
  --name "/document-insight/dev/layer/boto3-x86-64" \
  --value "arn:aws:lambda:us-east-1:123456789012:layer:document-insight-boto3-layer-dev-x86-64:1" \
  --type String \
  --overwrite

aws ssm put-parameter \
  --name "/document-insight/dev/layer/boto3-arm64" \
  --value "arn:aws:lambda:us-east-1:123456789012:layer:document-insight-boto3-layer-dev-arm64:1" \
  --type String \
  --overwrite
```

### Retrieve in CDK

```python
from aws_cdk import aws_ssm as ssm

# Retrieve layer ARN from SSM
pypdf_layer_arn = ssm.StringParameter.value_from_lookup(
    self,
    parameter_name="/document-insight/dev/layer/pypdf-x86-64"
)
```

## Maintenance

### Updating Layers

When you need to update packages:

1. Rebuild all layers:
   ```bash
   ./scripts/build_lambda_layers.sh dev
   # Or via AWS CLI
   aws codebuild start-build --project-name document-insight-layers-dev
   ```

2. Get the new version numbers:
   ```bash
   # Check pypdf layer
   aws lambda list-layer-versions \
     --layer-name document-insight-pypdf-layer-dev-x86-64 \
     --max-items 1 \
     --query 'LayerVersions[0].Version'
   
   # Check boto3 layer
   aws lambda list-layer-versions \
     --layer-name document-insight-boto3-layer-dev-x86-64 \
     --max-items 1 \
     --query 'LayerVersions[0].Version'
   ```

3. Update Lambda functions to use the new versions

### Cleanup Old Versions

Lambda allows up to 100 versions per layer. Clean up old versions:

```bash
# List all versions
aws lambda list-layer-versions \
  --layer-name document-insight-pypdf-layer-dev-x86-64

# Delete specific version
aws lambda delete-layer-version \
  --layer-name document-insight-pypdf-layer-dev-x86-64 \
  --version-number 1
```

## Troubleshooting

### Build Fails

1. Check CodeBuild logs in AWS Console
2. Verify IAM permissions
3. Check buildspec syntax

### Lambda Can't Import Package

1. Verify layer is attached to function
2. Check architecture matches (x86_64 vs ARM64)
3. Verify Python runtime compatibility
4. Test layer locally:
   ```bash
   # Download layer
   aws lambda get-layer-version \
     --layer-name document-insight-pypdf-layer-dev-x86-64 \
     --version-number 1 \
     --query 'Content.Location' \
     --output text | xargs curl -o layer.zip
   
   # Extract and test
   unzip layer.zip
   python3 -c "import sys; sys.path.insert(0, 'python'); import PyPDF2; print(PyPDF2.__version__)"
   ```

### S3 Vectors API Not Available

If boto3 layer doesn't include S3 Vectors support:

1. Verify boto3 version is >= 1.34.0
2. Check build logs for errors
3. Rebuild all layers with latest boto3:
   ```bash
   ./scripts/build_lambda_layers.sh dev
   ```

## Cost Optimization

- Use ARM64 architecture where possible (10% cost savings)
- Share layers across multiple Lambda functions
- Delete unused layer versions
- Use CodeBuild caching to reduce build times

## Next Steps

After setting up layers:

1. Deploy Lambda function stacks that use these layers
2. Test Lambda functions with the layers
3. Monitor Lambda execution for import errors
4. Set up automated layer updates in CI/CD pipeline

## Resources

- [AWS Lambda Layers Documentation](https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html)
- [AWS CodeBuild Documentation](https://docs.aws.amazon.com/codebuild/latest/userguide/welcome.html)
- [PyPDF2 Documentation](https://pypdf2.readthedocs.io/)
- [Boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
