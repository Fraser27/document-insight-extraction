"""
Lambda Function Stack for Document Insight Extraction System

This module defines Lambda functions for document processing and insight extraction,
including IAM permissions, environment configuration, and layer attachments.
"""
from aws_cdk import (
    Duration,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_s3 as s3,
    aws_logs as logs,
    CfnOutput,
)
from constructs import Construct
from infrastructure.base_stack import BaseDocumentInsightStack
from typing import Optional


class LambdaFunctionStack(BaseDocumentInsightStack):
    """
    Stack for Lambda function resources.
    
    Creates:
    - Document Processing Lambda function
    - Insight Extraction Lambda function (future)
    - IAM roles and permissions
    - CloudWatch log groups
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        env_name: str,
        config: dict,
        **kwargs
    ) -> None:
        """
        Initialize the Lambda Function stack.
        
        Args:
            scope: CDK app or parent construct
            construct_id: Unique identifier for this stack
            env_name: Environment name (dev, prod, etc.)
            config: Environment-specific configuration dictionary
            **kwargs: Additional stack properties
        """
        super().__init__(scope, construct_id, env_name, config, **kwargs)

        # Store references to be set later
        self.documents_bucket: Optional[s3.IBucket] = None
        self.vector_bucket_name: Optional[str] = None
        self.vector_index_arn: Optional[str] = None
        self.websocket_url: Optional[str] = None
        
        # Lambda functions (created later after dependencies are set)
        self.document_processor_lambda: Optional[lambda_.Function] = None
        self.insight_extractor_lambda: Optional[lambda_.Function] = None
        
    def create_document_processor_lambda(
        self,
        documents_bucket: s3.IBucket,
        vector_bucket_name: str,
        vector_index_arn: str,
        websocket_url: str,
        pypdf_layer_arn: str,
        boto3_layer_arn: str
    ) -> lambda_.Function:
        """
        Create the Document Processing Lambda function.
        
        Args:
            documents_bucket: S3 bucket for document storage
            vector_bucket_name: S3 Vector bucket name
            vector_index_arn: S3 Vector index ARN
            websocket_url: WebSocket API URL for progress updates
            pypdf_layer_arn: ARN of pypdf Lambda layer
            boto3_layer_arn: ARN of boto3 Lambda layer
            
        Returns:
            Lambda Function construct
        """
        # Store references
        self.documents_bucket = documents_bucket
        self.vector_bucket_name = vector_bucket_name
        self.vector_index_arn = vector_index_arn
        self.websocket_url = websocket_url
        
        # Create CloudWatch log group
        log_group = logs.LogGroup(
            self,
            "DocumentProcessorLogGroup",
            log_group_name=f"/aws/lambda/{self.get_resource_name('document-processor')}",
            removal_policy=self.removal_policy,
            retention=logs.RetentionDays.ONE_MONTH
        )
        
        # Create Lambda execution role
        execution_role = self._create_document_processor_role()
        
        # Create Lambda layers from ARNs
        pypdf_layer = lambda_.LayerVersion.from_layer_version_arn(
            self,
            "PypdfLayer",
            layer_version_arn=pypdf_layer_arn
        )
        
        boto3_layer = lambda_.LayerVersion.from_layer_version_arn(
            self,
            "Boto3Layer",
            layer_version_arn=boto3_layer_arn
        )
        
        # Create Lambda function
        self.document_processor_lambda = lambda_.Function(
            self,
            "DocumentProcessorLambda",
            function_name=self.get_resource_name("document-processor"),
            description="Process PDF documents: extract text, generate embeddings, store in S3 Vectors",
            runtime=lambda_.Runtime.PYTHON_3_12,
            # x86_64 architecture for pypdf compatibility
            architecture=lambda_.Architecture.X86_64,
            handler="document_processor.handler",
            code=lambda_.Code.from_asset("lambda/document_processor"),
            # Memory and timeout configuration
            memory_size=self.lambda_memory,
            timeout=Duration.seconds(self.lambda_timeout),
            # Attach layers
            layers=[pypdf_layer, boto3_layer],
            # IAM role
            role=execution_role,
            # Environment variables
            environment={
                "VECTOR_BUCKET_NAME": vector_bucket_name,
                "VECTOR_INDEX_ARN": vector_index_arn,
                "EMBED_MODEL_ID": self.embed_model_id,
                "WSS_URL": websocket_url,
                "REGION": self.region,
                "LOG_LEVEL": self.config.get("log_level", "INFO"),
            },
            # CloudWatch Logs
            log_group=log_group,
            # Reserved concurrent executions (optional)
            reserved_concurrent_executions=self.config.get(
                "document_processor_concurrency",
                None
            ),
        )
        
        # Grant S3 permissions
        self._grant_s3_permissions()
        
        # Grant Bedrock permissions
        self._grant_bedrock_permissions()
        
        # Add outputs
        self._add_document_processor_outputs()
        
        return self.document_processor_lambda

    def _create_document_processor_role(self) -> iam.Role:
        """
        Create IAM role for Document Processing Lambda.
        
        Returns:
            IAM Role with necessary permissions
        """
        role = iam.Role(
            self,
            "DocumentProcessorRole",
            role_name=self.get_resource_name("document-processor-role"),
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Execution role for Document Processing Lambda function",
            managed_policies=[
                # Basic Lambda execution permissions
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ]
        )
        
        return role

    def _grant_s3_permissions(self) -> None:
        """Grant S3 permissions to Document Processing Lambda."""
        if not self.document_processor_lambda or not self.documents_bucket:
            raise ValueError("Lambda function and documents bucket must be set first")
        
        # Grant read and delete permissions on documents bucket
        self.documents_bucket.grant_read(self.document_processor_lambda)
        self.documents_bucket.grant_delete(self.document_processor_lambda)
        
        # Grant S3 Vectors permissions (PutVectors, DeleteVectors, QueryVectors)
        self.document_processor_lambda.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:PutObject",
                    "s3:GetObject",
                    "s3:DeleteObject",
                    "s3:ListBucket",
                ],
                resources=[
                    f"arn:aws:s3:::{self.vector_bucket_name}",
                    f"arn:aws:s3:::{self.vector_bucket_name}/*"
                ]
            )
        )
        
        # Grant S3 Vectors API permissions
        self.document_processor_lambda.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:PutVectors",
                    "s3:DeleteVectors",
                    "s3:QueryVectors",
                ],
                resources=[
                    self.vector_index_arn
                ]
            )
        )

    def _grant_bedrock_permissions(self) -> None:
        """Grant Bedrock permissions to Document Processing Lambda."""
        if not self.document_processor_lambda:
            raise ValueError("Lambda function must be set first")
        
        # Grant permission to invoke Bedrock models
        self.document_processor_lambda.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                resources=[
                    # Titan V2 embedding model
                    f"arn:aws:bedrock:{self.region}::foundation-model/{self.embed_model_id}",
                    # Allow any Bedrock model for OCR (flexible)
                    f"arn:aws:bedrock:{self.region}::foundation-model/*"
                ]
            )
        )

    def grant_websocket_permissions(self, websocket_api_arn: str) -> None:
        """
        Grant API Gateway ManageConnections permission for WebSocket.
        
        Args:
            websocket_api_arn: ARN pattern for WebSocket API connections
        """
        if not self.document_processor_lambda:
            raise ValueError("Lambda function must be set first")
        
        self.document_processor_lambda.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "execute-api:ManageConnections",
                    "execute-api:Invoke",
                ],
                resources=[
                    websocket_api_arn
                ]
            )
        )

    def create_insight_extractor_lambda(
        self,
        vector_bucket_name: str,
        vector_index_arn: str,
        dynamodb_table_name: str,
        boto3_layer_arn: str
    ) -> lambda_.Function:
        """
        Create the Insight Extraction Lambda function.
        
        Args:
            vector_bucket_name: S3 Vector bucket name
            vector_index_arn: S3 Vector index ARN
            dynamodb_table_name: DynamoDB cache table name
            boto3_layer_arn: ARN of boto3 Lambda layer
            
        Returns:
            Lambda Function construct
        """
        # Create CloudWatch log group
        log_group = logs.LogGroup(
            self,
            "InsightExtractorLogGroup",
            log_group_name=f"/aws/lambda/{self.get_resource_name('insight-extractor')}",
            removal_policy=self.removal_policy,
            retention=logs.RetentionDays.ONE_MONTH
        )
        
        # Create Lambda execution role
        execution_role = self._create_insight_extractor_role()
        
        # Create Lambda layer from ARN
        boto3_layer = lambda_.LayerVersion.from_layer_version_arn(
            self,
            "InsightBoto3Layer",
            layer_version_arn=boto3_layer_arn
        )
        
        # Create Lambda function
        self.insight_extractor_lambda = lambda_.Function(
            self,
            "InsightExtractorLambda",
            function_name=self.get_resource_name("insight-extractor"),
            description="Extract structured insights from documents using vector search and Bedrock",
            runtime=lambda_.Runtime.PYTHON_3_12,
            # ARM64 architecture for cost optimization
            architecture=lambda_.Architecture.ARM_64,
            handler="insight_extractor.handler",
            code=lambda_.Code.from_asset("lambda/insight_extractor"),
            # Memory and timeout configuration
            memory_size=self.lambda_memory,
            timeout=Duration.seconds(300),  # 5 minutes for insight extraction
            # Attach layer
            layers=[boto3_layer],
            # IAM role
            role=execution_role,
            # Environment variables
            environment={
                "VECTOR_BUCKET_NAME": vector_bucket_name,
                "VECTOR_INDEX_ARN": vector_index_arn,
                "EMBED_MODEL_ID": self.embed_model_id,
                "INSIGHT_MODEL_ID": self.config.get("insight_model_id", "anthropic.claude-3-sonnet-20240229-v1:0"),
                "DYNAMODB_TABLE_NAME": dynamodb_table_name,
                "REGION": self.region,
                "LOG_LEVEL": self.config.get("log_level", "INFO"),
            },
            # CloudWatch Logs
            log_group=log_group,
            # Reserved concurrent executions (optional)
            reserved_concurrent_executions=self.config.get(
                "insight_extractor_concurrency",
                None
            ),
        )
        
        # Add outputs
        self._add_insight_extractor_outputs()
        
        return self.insight_extractor_lambda

    def _create_insight_extractor_role(self) -> iam.Role:
        """
        Create IAM role for Insight Extraction Lambda.
        
        Returns:
            IAM Role with necessary permissions
        """
        role = iam.Role(
            self,
            "InsightExtractorRole",
            role_name=self.get_resource_name("insight-extractor-role"),
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Execution role for Insight Extraction Lambda function",
            managed_policies=[
                # Basic Lambda execution permissions
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ]
        )
        
        return role

    def grant_insight_extractor_s3_permissions(
        self,
        vector_bucket_name: str,
        vector_index_arn: str
    ) -> None:
        """
        Grant S3 Vectors permissions to Insight Extraction Lambda.
        
        Args:
            vector_bucket_name: S3 Vector bucket name
            vector_index_arn: S3 Vector index ARN
        """
        if not self.insight_extractor_lambda:
            raise ValueError("Insight extractor Lambda function must be set first")
        
        # Grant S3 Vectors read permissions
        self.insight_extractor_lambda.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:GetObject",
                    "s3:ListBucket",
                ],
                resources=[
                    f"arn:aws:s3:::{vector_bucket_name}",
                    f"arn:aws:s3:::{vector_bucket_name}/*"
                ]
            )
        )
        
        # Grant S3 Vectors API permissions
        self.insight_extractor_lambda.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:QueryVectors",
                ],
                resources=[
                    vector_index_arn
                ]
            )
        )

    def grant_insight_extractor_bedrock_permissions(self) -> None:
        """Grant Bedrock permissions to Insight Extraction Lambda."""
        if not self.insight_extractor_lambda:
            raise ValueError("Insight extractor Lambda function must be set first")
        
        insight_model_id = self.config.get("insight_model_id", "anthropic.claude-3-sonnet-20240229-v1:0")
        
        # Grant permission to invoke Bedrock models
        self.insight_extractor_lambda.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                resources=[
                    # Titan V2 embedding model
                    f"arn:aws:bedrock:{self.region}::foundation-model/{self.embed_model_id}",
                    # Insight model (Claude or other)
                    f"arn:aws:bedrock:{self.region}::foundation-model/{insight_model_id}",
                ]
            )
        )

    def grant_insight_extractor_dynamodb_permissions(
        self,
        dynamodb_table_arn: str
    ) -> None:
        """
        Grant DynamoDB permissions to Insight Extraction Lambda.
        
        Args:
            dynamodb_table_arn: DynamoDB table ARN
        """
        if not self.insight_extractor_lambda:
            raise ValueError("Insight extractor Lambda function must be set first")
        
        # Grant DynamoDB permissions
        self.insight_extractor_lambda.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:Query",
                ],
                resources=[
                    dynamodb_table_arn,
                    f"{dynamodb_table_arn}/index/*"  # For any GSIs
                ]
            )
        )

    def _add_insight_extractor_outputs(self) -> None:
        """Add CloudFormation outputs for Insight Extraction Lambda."""
        if not self.insight_extractor_lambda:
            return
        
        self.add_stack_output(
            "InsightExtractorLambdaArn",
            value=self.insight_extractor_lambda.function_arn,
            description="ARN of Insight Extraction Lambda function",
            export_name=f"{self.stack_name}-InsightExtractorArn"
        )
        
        self.add_stack_output(
            "InsightExtractorLambdaName",
            value=self.insight_extractor_lambda.function_name,
            description="Name of Insight Extraction Lambda function",
            export_name=f"{self.stack_name}-InsightExtractorName"
        )

    def _add_document_processor_outputs(self) -> None:
        """Add CloudFormation outputs for Document Processing Lambda."""
        if not self.document_processor_lambda:
            return
        
        self.add_stack_output(
            "DocumentProcessorLambdaArn",
            value=self.document_processor_lambda.function_arn,
            description="ARN of Document Processing Lambda function",
            export_name=f"{self.stack_name}-DocumentProcessorArn"
        )
        
        self.add_stack_output(
            "DocumentProcessorLambdaName",
            value=self.document_processor_lambda.function_name,
            description="Name of Document Processing Lambda function",
            export_name=f"{self.stack_name}-DocumentProcessorName"
        )
