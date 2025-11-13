# Lambda Layer Build Migration Notes

## Changes Made

The Lambda layer build infrastructure has been consolidated from two separate CodeBuild projects into a single unified project for better efficiency and easier management.

## What Changed

### Before (Separate Projects)
- **Two CodeBuild projects**: 
  - `document-insight-pypdf-layer-{env}`
  - `document-insight-boto3-layer-{env}`
- **Two buildspec files**:
  - `buildspec_pypdf_layer.yml`
  - `buildspec_boto3_layer.yml`
- **Two separate builds** required to create all layers
- **Build time**: ~6-10 minutes total (2 builds × 3-5 minutes each)

### After (Consolidated Project)
- **One CodeBuild project**: 
  - `document-insight-layers-{env}`
- **One buildspec file**:
  - `buildspec_layers.yml`
- **Single build** creates all 4 layers (pypdf x86_64, pypdf ARM64, boto3 x86_64, boto3 ARM64)
- **Build time**: ~5-8 minutes total (one build)

## Benefits

1. **Simplified Management**: One project to maintain instead of two
2. **Faster Execution**: Single build is faster than two sequential builds
3. **Atomic Updates**: All layers are updated together, ensuring consistency
4. **Reduced Costs**: Fewer CodeBuild executions
5. **Easier Automation**: One command to build everything

## Layer Names (Unchanged)

The layer names remain the same, so no changes are needed to Lambda functions:

- `document-insight-pypdf-layer-{env}-x86-64`
- `document-insight-pypdf-layer-{env}-arm64`
- `document-insight-boto3-layer-{env}-x86-64`
- `document-insight-boto3-layer-{env}-arm64`

## Usage

### Building Layers

```bash
# Old way (no longer used)
aws codebuild start-build --project-name document-insight-pypdf-layer-dev
aws codebuild start-build --project-name document-insight-boto3-layer-dev

# New way (consolidated)
./scripts/build_lambda_layers.sh dev
# Or
aws codebuild start-build --project-name document-insight-layers-dev
```

### Deployment

```bash
# Deploy the updated stack
cdk deploy DocumentInsightLambdaLayerDevStack
```

This will:
1. Remove the old separate CodeBuild projects
2. Create the new consolidated CodeBuild project
3. Keep the same S3 artifacts bucket

## Migration Steps

If you have an existing deployment:

1. **Deploy the updated stack**:
   ```bash
   cdk deploy DocumentInsightLambdaLayerDevStack
   ```

2. **Build the layers using the new project**:
   ```bash
   ./scripts/build_lambda_layers.sh dev
   ```

3. **Verify the layers were created**:
   ```bash
   aws lambda list-layer-versions --layer-name document-insight-pypdf-layer-dev-x86-64 --max-items 1
   aws lambda list-layer-versions --layer-name document-insight-boto3-layer-dev-x86-64 --max-items 1
   ```

4. **Update Lambda functions** (if needed) to use the new layer versions

## Rollback

If you need to rollback to the separate projects approach:

1. Revert the changes to `infrastructure/lambda_layer_stack.py`
2. Use the individual buildspec files
3. Redeploy the stack

However, this should not be necessary as the consolidated approach is functionally equivalent and more efficient.

## Files Modified

- `infrastructure/lambda_layer_stack.py` - Consolidated to single CodeBuild project
- `buildspecs/buildspec_layers.yml` - New consolidated buildspec (created)
- `scripts/build_lambda_layers.sh` - Updated to use single project
- `buildspecs/README.md` - Updated documentation
- `LAMBDA_LAYERS.md` - Updated usage guide

## Files Kept for Reference

- `buildspecs/buildspec_pypdf_layer.yml` - Legacy, not used
- `buildspecs/buildspec_boto3_layer.yml` - Legacy, not used

These can be deleted if desired, but are kept for reference.

## Questions?

If you have any questions about the migration or encounter issues, refer to:
- `buildspecs/README.md` - Detailed buildspec documentation
- `LAMBDA_LAYERS.md` - Complete usage guide
- Build logs in AWS CodeBuild console
