# Lambda Layer Build Specifications

This directory contains AWS CodeBuild buildspec files for creating Lambda layers used by the Document Insight Extraction System.

## Overview

The system uses a single consolidated CodeBuild project that builds all Lambda layers in one execution:

1. **pypdf Layer**: Contains PyPDF2 library for PDF text extraction
2. **boto3 Layer**: Contains the latest boto3 and botocore with S3 Vectors API support

Each layer is built for both x86_64 and ARM64 architectures (4 total layers) to support different Lambda function configurations.

## Buildspec Files

### buildspec_layers.yml (Primary)

This is the main buildspec that builds all Lambda layers in a single execution:

**Features:**
- Builds pypdf layer with PyPDF2 and dependencies
- Builds boto3 layer with latest boto3/botocore and S3 Vectors API support
- Creates layers for both x86_64 and ARM64 architectures
- Publishes all 4 layers to AWS Lambda
- Outputs comprehensive layer information in JSON format

**Layer Names Created:**
- `document-insight-pypdf-layer-{env}-x86-64`
- `document-insight-pypdf-layer-{env}-arm64`
- `document-insight-boto3-layer-{env}-x86-64`
- `document-insight-boto3-layer-{env}-arm64`

**Runtime Compatibility:**
- pypdf layers: Python 3.12
- boto3 layers: Python 3.12, 3.11, 3.10

### Legacy Buildspec Files

The individual buildspec files (`buildspec_pypdf_layer.yml` and `buildspec_boto3_layer.yml`) are kept for reference but are no longer used by the infrastructure. The consolidated approach is more efficient.

## Building Layers

### Using the Helper Script (Recommended)

The easiest way to build all layers is using the provided script:

```bash
# Build all layers for dev environment
./scripts/build_lambda_layers.sh dev

# Build all layers for prod environment
./scripts/build_lambda_layers.sh prod
```

This single command will build all 4 layers (pypdf x86_64, pypdf ARM64, boto3 x86_64, boto3 ARM64) in one execution.

### Manual Build via AWS CLI

You can also trigger the build manually:

```bash
# Set your environment and region
ENV=dev
REGION=us-east-1

# Build all layers with one command
aws codebuild start-build \
  --project-name document-insight-layers-${ENV} \
  --region ${REGION}
```

### Via AWS Console

1. Navigate to AWS CodeBuild in the AWS Console
2. Find the project: `document-insight-layers-{env}`
3. Click "Start build"
4. Monitor the build progress and logs (builds all 4 layers)

## Build Process

The consolidated buildspec follows this process:

1. **Install Phase**: Set up Python 3.12 and build dependencies
2. **Pre-Build Phase**: Display configuration and verify versions
3. **Build Phase**:
   - Build pypdf layer for x86_64 and ARM64
   - Publish pypdf layer versions to AWS Lambda
   - Build boto3 layer for x86_64 and ARM64
   - Publish boto3 layer versions to AWS Lambda
4. **Post-Build Phase**: Output all layer ARNs and comprehensive version information

## Build Artifacts

Each build produces:
- `pypdf-layer-x86_64.zip`: pypdf layer for x86_64 architecture
- `pypdf-layer-arm64.zip`: pypdf layer for ARM64 architecture
- `boto3-layer-x86_64.zip`: boto3 layer for x86_64 architecture
- `boto3-layer-arm64.zip`: boto3 layer for ARM64 architecture
- `layer_info.json`: Comprehensive metadata including all layer ARNs and versions

Artifacts are stored in the S3 bucket: `document-insight-layer-artifacts-{env}-{account-id}`

## Build Time

The consolidated build typically takes 5-8 minutes to complete all 4 layers, which is more efficient than running separate builds.

## Layer Usage

### In CDK Code

```python
from aws_cdk import aws_lambda as lambda_

# Reference the layer by ARN
pypdf_layer = lambda_.LayerVersion.from_layer_version_arn(
    self,
    "PypdfLayer",
    layer_version_arn=f"arn:aws:lambda:{region}:{account}:layer:document-insight-pypdf-layer-{env}-x86-64:{version}"
)

# Use in Lambda function
lambda_.Function(
    self,
    "DocumentProcessor",
    runtime=lambda_.Runtime.PYTHON_3_12,
    architecture=lambda_.Architecture.X86_64,
    layers=[pypdf_layer],
    # ... other configuration
)
```

### Getting Layer ARNs

After a successful build, you can retrieve layer ARNs:

```bash
# List layer versions
aws lambda list-layer-versions \
  --layer-name document-insight-pypdf-layer-dev-x86-64 \
  --region us-east-1

# Get specific version ARN
aws lambda get-layer-version \
  --layer-name document-insight-pypdf-layer-dev-x86-64 \
  --version-number 1 \
  --region us-east-1 \
  --query 'LayerVersionArn' \
  --output text
```

## Updating Layers

To update a layer with new package versions:

1. Modify the buildspec file if needed (e.g., pin specific versions)
2. Trigger a new build using the script or AWS CLI
3. A new layer version will be published automatically
4. Update your Lambda functions to use the new layer version

## Architecture Selection

- **x86_64**: Use for Lambda functions that require maximum compatibility or specific x86-only packages
- **ARM64**: Use for Lambda functions on Graviton2 processors (10% cost savings, better performance for some workloads)

## Troubleshooting

### Build Failures

If a build fails:

1. Check the CodeBuild logs in the AWS Console
2. Verify IAM permissions for the CodeBuild role
3. Ensure the layer name doesn't conflict with existing layers
4. Check that pip can resolve all package dependencies

### Layer Size Issues

Lambda layers have a 250 MB unzipped size limit:

- The pypdf layer is typically ~5 MB
- The boto3 layer is typically ~50 MB
- Both are well within limits

### Import Errors in Lambda

If you get import errors when using the layers:

1. Verify the layer is attached to your Lambda function
2. Check that the architecture matches (x86_64 vs ARM64)
3. Ensure the Python runtime version is compatible
4. Verify the layer was built successfully

## Environment Variables

The buildspec files use these environment variables:

- `LAYER_NAME`: Base name for the layer (set by CodeBuild project)
- `AWS_REGION`: AWS region for publishing layers (set by CodeBuild project)
- `AWS_ACCOUNT_ID`: AWS account ID (set by CodeBuild project)

## Caching

Both buildspecs use pip caching to speed up subsequent builds:
- Cache location: `/root/.cache/pip`
- Reduces build time by ~30-50% for repeated builds

## Cost Considerations

- CodeBuild charges per build minute (typically 2-5 minutes per layer)
- S3 storage for artifacts (minimal cost)
- Lambda layer storage (free for first 75 GB)
- Estimated cost per build: $0.01 - $0.05

## Best Practices

1. **Version Control**: Keep buildspec files in version control
2. **Tagging**: Tag layer versions with meaningful descriptions
3. **Testing**: Test layers in dev environment before prod
4. **Cleanup**: Periodically delete old layer versions to reduce clutter
5. **Documentation**: Document any custom package versions or configurations
