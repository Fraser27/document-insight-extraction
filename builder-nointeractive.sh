#!/usr/bin/bash 
Green='\033[0;32m'
Red='\033[0;31m'
NC='\033[0m'

# Get account ID
account_id=$(aws sts get-caller-identity --query "Account" --output text)

if [ -z "$1" ]
then
    infra_env='dev'
else
    infra_env=$1
fi  

if [ $infra_env != "dev" -a $infra_env != "prod" ]
then
    echo "Environment name can only be dev or prod. example 'sh builder-nointeractive.sh dev' "
    exit 1
fi

echo "Environment: $infra_env"
echo ' '
echo '*************************************************************'
echo '*************************************************************'
echo ' Starting deployment ... '

deployment_region=$(aws ec2 describe-availability-zones --output text --query 'AvailabilityZones[0].RegionName')

echo "--- Upgrading npm ---"
sudo npm install n stable -g
echo "--- Installing cdk ---"
sudo npm install -g aws-cdk@2.192.0

echo "--- Bootstrapping CDK on account in region $deployment_region ---"
cdk bootstrap aws://$(aws sts get-caller-identity --query "Account" --output text)/$deployment_region

CURRENT_UTC_TIMESTAMP=$(date -u +"%Y%m%d%H%M%S")

ls -lrt

echo "--- pip install requirements ---"
python3 -m pip install -r requirements.txt

echo "--- CDK synthesize ---"
cdk synth --context env=$infra_env

echo "--- CDK deploy Lambda Layer Stack ---"
cdk deploy --context env=$infra_env DocumentInsightLambdaLayer${infra_env^}Stack --require-approval never

echo "--- Get Lambda Layer Build Container ---"
project=document-insight-lambda-layer-builder-"$infra_env"
echo project: $project
build_container=$(aws codebuild list-projects|grep -o $project'[^,"]*')
echo container: $build_container

if [ -n "$build_container" ]; then
    echo "--- Trigger Lambda Layer Build ---"
    BUILD_ID=$(aws codebuild start-build --project-name $build_container | jq '.build.id' -r)
    echo Build ID : $BUILD_ID
    if [ "$?" != "0" ]; then
        echo "Could not start CodeBuild project. Continuing without layer build."
    else
        echo "Lambda layer build started successfully."
        
        # Monitor the build
        echo "Monitoring lambda layer build progress..."
        while true; do
          status=$(aws codebuild batch-get-builds --ids $BUILD_ID | jq -r '.builds[0].buildStatus')
          phase=$(aws codebuild batch-get-builds --ids $BUILD_ID | jq -r '.builds[0].currentPhase')
          
          echo "Current status: $status, Phase: $phase"
          
          if [ "$status" == "SUCCEEDED" ] || [ "$status" == "FAILED" ] || [ "$status" == "STOPPED" ]; then
            break
          else
            echo "Build is still in progress... sleeping for 60 seconds"
          fi
          
          sleep 60
        done
        
        if [ $status != "SUCCEEDED" ]; then
            echo "Lambda layer build failed with status: $status"
            echo "Continuing with deployment - layers may use default versions"
        fi
    fi
else
    echo "Lambda layer build project not found. Continuing with deployment."
fi

echo "--- CDK deploy all infrastructure stacks ---"
cdk deploy --context env=$infra_env --all --require-approval never --outputs-file cdk-outputs.json

if [ $? -eq 0 ]; then
    echo "✓ CDK stacks deployed successfully"
else
    echo "CDK deployment failed"
    exit 1
fi

echo "--- Building and pushing frontend Docker image ---"
if [ -f "cdk-outputs.json" ]; then
    ECR_URI=$(cat cdk-outputs.json | grep -o '"ECRRepositoryUri": "[^"]*"' | cut -d'"' -f4 | head -1)
    
    if [ -n "$ECR_URI" ]; then
        echo "ECR Repository: $ECR_URI"
        
        # Login to ECR
        echo "Logging in to ECR..."
        aws ecr get-login-password --region $deployment_region | docker login --username AWS --password-stdin $ECR_URI
        
        # Build Docker image
        echo "Building Docker image..."
        cd frontend
        docker build -t document-insight-ui:latest .
        
        # Tag image
        echo "Tagging image..."
        docker tag document-insight-ui:latest $ECR_URI:latest
        docker tag document-insight-ui:latest $ECR_URI:$(date +%Y%m%d-%H%M%S)
        
        # Push image
        echo "Pushing image to ECR..."
        docker push $ECR_URI:latest
        docker push $ECR_URI:$(date +%Y%m%d-%H%M%S)
        
        cd ..
        
        echo "✓ Docker image pushed successfully"
        
        # Trigger AppRunner deployment
        echo "Triggering AppRunner deployment..."
        APPRUNNER_SERVICE_ARN=$(cat cdk-outputs.json | grep -o '"AppRunnerServiceArn": "[^"]*"' | cut -d'"' -f4 | head -1)
        
        if [ -n "$APPRUNNER_SERVICE_ARN" ]; then
            aws apprunner start-deployment --service-arn "$APPRUNNER_SERVICE_ARN" || echo "Note: AppRunner deployment will start automatically"
        fi
    else
        echo "Warning: Could not find ECR repository URI in outputs"
    fi
else
    echo "Warning: cdk-outputs.json not found"
fi

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""

if [ -f "cdk-outputs.json" ]; then
    echo "Deployment Outputs:"
    echo ""
    
    # Extract key outputs
    REST_API_URL=$(cat cdk-outputs.json | grep -o '"RestApiUrl": "[^"]*"' | cut -d'"' -f4 | head -1)
    WSS_URL=$(cat cdk-outputs.json | grep -o '"WebSocketUrl": "[^"]*"' | cut -d'"' -f4 | head -1)
    APPRUNNER_URL=$(cat cdk-outputs.json | grep -o '"AppRunnerServiceUrl": "[^"]*"' | cut -d'"' -f4 | head -1)
    USER_POOL_ID=$(cat cdk-outputs.json | grep -o '"UserPoolId": "[^"]*"' | cut -d'"' -f4 | head -1)
    USER_POOL_CLIENT_ID=$(cat cdk-outputs.json | grep -o '"UserPoolClientId": "[^"]*"' | cut -d'"' -f4 | head -1)
    
    [ -n "$REST_API_URL" ] && echo "  REST API URL: $REST_API_URL"
    [ -n "$WSS_URL" ] && echo "  WebSocket URL: $WSS_URL"
    [ -n "$APPRUNNER_URL" ] && echo "  Frontend URL: $APPRUNNER_URL"
    [ -n "$USER_POOL_ID" ] && echo "  User Pool ID: $USER_POOL_ID"
    [ -n "$USER_POOL_CLIENT_ID" ] && echo "  User Pool Client ID: $USER_POOL_CLIENT_ID"
    
    echo ""
    echo "Full outputs saved to: cdk-outputs.json"
else
    echo "Note: cdk-outputs.json not found. Check AWS Console for outputs."
fi

echo ""
echo "Next Steps:"
echo "  1. Create a Cognito user: aws cognito-idp admin-create-user --user-pool-id <USER_POOL_ID> --username <EMAIL>"
echo "  2. Access the frontend at the AppRunner URL"
echo "  3. Upload a PDF document and extract insights"
echo ""
echo "Deployment Complete"