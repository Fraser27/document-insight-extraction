#!/bin/bash

# Script to build all Lambda layers using CodeBuild
# This script triggers a single CodeBuild project that creates both pypdf and boto3 layers

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get environment (default to dev)
ENV=${1:-dev}

echo -e "${GREEN}Building all Lambda layers for environment: ${ENV}${NC}"

# Get AWS region
REGION=${AWS_REGION:-us-east-1}
echo -e "${YELLOW}Using AWS region: ${REGION}${NC}"

# Project name
PROJECT_NAME="document-insight-layers-${ENV}"

echo -e "${YELLOW}Starting build for all layers (pypdf and boto3)...${NC}"

# Start the build
BUILD_ID=$(aws codebuild start-build \
    --project-name "${PROJECT_NAME}" \
    --region "${REGION}" \
    --query 'build.id' \
    --output text)

if [ -z "$BUILD_ID" ]; then
    echo -e "${RED}Failed to start build${NC}"
    exit 1
fi

echo -e "${GREEN}Build started with ID: ${BUILD_ID}${NC}"
echo -e "${YELLOW}Waiting for build to complete...${NC}"
echo -e "${YELLOW}This will build 4 layers: pypdf (x86_64 + ARM64) and boto3 (x86_64 + ARM64)${NC}"

# Wait for build to complete
aws codebuild wait build-complete \
    --ids "${BUILD_ID}" \
    --region "${REGION}"

# Get build status
BUILD_STATUS=$(aws codebuild batch-get-builds \
    --ids "${BUILD_ID}" \
    --region "${REGION}" \
    --query 'builds[0].buildStatus' \
    --output text)

if [ "$BUILD_STATUS" == "SUCCEEDED" ]; then
    echo -e "\n${GREEN}=== All Lambda layers built successfully! ===${NC}\n"
    
    # Get logs URL
    LOGS_URL=$(aws codebuild batch-get-builds \
        --ids "${BUILD_ID}" \
        --region "${REGION}" \
        --query 'builds[0].logs.deepLink' \
        --output text)
    
    echo -e "${YELLOW}View detailed build logs at:${NC}"
    echo -e "${LOGS_URL}\n"
    
    # Get artifact location
    ARTIFACT_LOCATION=$(aws codebuild batch-get-builds \
        --ids "${BUILD_ID}" \
        --region "${REGION}" \
        --query 'builds[0].artifacts.location' \
        --output text)
    
    echo -e "${YELLOW}Build artifacts stored at:${NC}"
    echo -e "${ARTIFACT_LOCATION}\n"
    
    echo -e "${GREEN}Layer ARNs have been published. Check the build logs for details.${NC}"
    echo -e "${YELLOW}You can now deploy the Lambda functions that use these layers.${NC}"
    
    exit 0
else
    echo -e "\n${RED}Build failed with status: ${BUILD_STATUS}${NC}\n"
    
    # Show logs URL
    LOGS_URL=$(aws codebuild batch-get-builds \
        --ids "${BUILD_ID}" \
        --region "${REGION}" \
        --query 'builds[0].logs.deepLink' \
        --output text)
    echo -e "${RED}Check logs at: ${LOGS_URL}${NC}"
    
    exit 1
fi
