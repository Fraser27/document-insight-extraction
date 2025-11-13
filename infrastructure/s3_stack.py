"""
S3 Bucket Stack for Document Insight Extraction System

This module defines S3 buckets for document storage and vector embeddings,
including CORS configuration, event notifications, and vector search capabilities.
"""
from aws_cdk import (
    aws_s3 as s3,
    aws_lambda as lambda_,
    aws_s3_notifications as s3n,
    CfnOutput,
    RemovalPolicy,
)
from constructs import Construct
from infrastructure.base_stack import BaseDocumentInsightStack
from typing import Optional


class S3BucketStack(BaseDocumentInsightStack):
    """
    Stack for S3 bucket resources.
    
    Creates:
    - S3 bucket for document storage with CORS configuration
    - S3 Vector bucket for embeddings with metadata filtering
    - Event notifications for Lambda triggers
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
        Initialize the S3 bucket stack.
        
        Args:
            scope: CDK app or parent construct
            construct_id: Unique identifier for this stack
            env_name: Environment name (dev, prod, etc.)
            config: Environment-specific configuration dictionary
            **kwargs: Additional stack properties
        """
        super().__init__(scope, construct_id, env_name, config, **kwargs)

        # Create document storage bucket
        self.documents_bucket = self._create_documents_bucket()
        
        # Create vector storage bucket
        self.vector_bucket = self._create_vector_bucket()
        
        # Store Lambda functions for event notifications (set later)
        self.document_processor_lambda: Optional[lambda_.IFunction] = None
        
        # Export outputs
        self._create_outputs()

    def _create_documents_bucket(self) -> s3.Bucket:
        """
        Create S3 bucket for document storage with CORS configuration.
        
        Returns:
            S3 Bucket construct
        """
        # CORS configuration for presigned POST uploads
        cors_rule = s3.CorsRule(
            allowed_methods=[
                s3.HttpMethods.GET,
                s3.HttpMethods.POST,
                s3.HttpMethods.PUT,
                s3.HttpMethods.HEAD
            ],
            allowed_origins=["*"],  # Will be restricted to AppRunner URL in production
            allowed_headers=["*"],
            exposed_headers=[
                "ETag",
                "x-amz-server-side-encryption",
                "x-amz-request-id",
                "x-amz-id-2"
            ],
            max_age=3000
        )

        # Create bucket with configuration
        bucket = s3.Bucket(
            self,
            "DocumentsBucket",
            bucket_name=f"{self.documents_bucket_name}-{self.region}",
            # Versioning disabled for cost optimization
            versioned=False,
            # Encryption at rest
            encryption=s3.BucketEncryption.S3_MANAGED,
            # Block public access
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            # CORS configuration
            cors=[cors_rule],
            # Removal policy based on environment
            removal_policy=self.removal_policy,
            auto_delete_objects=self.removal_policy == RemovalPolicy.DESTROY,
            # Lifecycle rules for cost optimization
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteOldDocuments",
                    enabled=True,
                    expiration=None,  # No automatic expiration by default
                    abort_incomplete_multipart_upload_after=None,
                    noncurrent_version_expiration=None
                )
            ],
            # Enable server access logging (optional)
            server_access_logs_prefix="access-logs/",
            # Enforce SSL
            enforce_ssl=True
        )

        return bucket

    def _create_vector_bucket(self) -> s3.CfnBucket:
        """
        Create S3 Vector bucket for embeddings with metadata filtering.
        
        Uses CfnBucket to create a VECTORSEARCH type bucket with vector index
        configuration for semantic search capabilities.
        
        Returns:
            S3 CfnBucket construct
        """
        # Get vector dimensions from config
        vector_dimensions = self.config.get("vector_dimensions", 1024)
        
        # Create vector bucket using L1 construct for VECTORSEARCH type
        vector_bucket = s3.CfnBucket(
            self,
            "VectorBucket",
            bucket_name=f"{self.vector_bucket_name}-{self.region}",
            # Vector search bucket type
            bucket_type="VECTORSEARCH",
            # Vector index configuration
            vector_configuration=s3.CfnBucket.VectorConfigurationProperty(
                dimensions=vector_dimensions,
                # Cosine similarity for semantic search
                distance_metric="COSINE",
                # Filterable metadata keys for document-specific queries
                filterable_metadata_keys=[
                    "docId",
                    "pageRange",
                    "uploadTimestamp"
                ],
                # Non-filterable metadata for context retrieval
                non_filterable_metadata_keys=[
                    "textChunk"
                ]
            ),
            # Public access configuration
            public_access_block_configuration=s3.CfnBucket.PublicAccessBlockConfigurationProperty(
                block_public_acls=True,
                block_public_policy=True,
                ignore_public_acls=True,
                restrict_public_buckets=True
            ),
            # Encryption configuration
            bucket_encryption=s3.CfnBucket.BucketEncryptionProperty(
                server_side_encryption_configuration=[
                    s3.CfnBucket.ServerSideEncryptionRuleProperty(
                        server_side_encryption_by_default=s3.CfnBucket.ServerSideEncryptionByDefaultProperty(
                            sse_algorithm="AES256"
                        ),
                        bucket_key_enabled=True
                    )
                ]
            )
        )
        
        # Apply removal policy
        vector_bucket.apply_removal_policy(self.removal_policy)
        
        return vector_bucket

    def configure_event_notifications(
        self,
        document_processor_lambda: lambda_.IFunction
    ) -> None:
        """
        Configure S3 event notifications to trigger Lambda functions.
        
        Sets up notifications for:
        - OBJECT_CREATED events -> Document Processing Lambda
        - OBJECT_REMOVED_DELETE events -> Document Processing Lambda (cleanup)
        
        Args:
            document_processor_lambda: Lambda function to process documents
        """
        self.document_processor_lambda = document_processor_lambda
        
        # Add Lambda destination for OBJECT_CREATED events
        self.documents_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(document_processor_lambda),
            s3.NotificationKeyFilter(
                prefix="",
                suffix=".pdf"
            )
        )
        
        # Add Lambda destination for OBJECT_REMOVED_DELETE events
        self.documents_bucket.add_event_notification(
            s3.EventType.OBJECT_REMOVED_DELETE,
            s3n.LambdaDestination(document_processor_lambda),
            s3.NotificationKeyFilter(
                prefix="",
                suffix=".pdf"
            )
        )
        
        # Grant S3 service principal permission to invoke Lambda
        document_processor_lambda.add_permission(
            "AllowS3Invocation",
            principal=lambda_.ServicePrincipal("s3.amazonaws.com"),
            source_arn=self.documents_bucket.bucket_arn,
            action="lambda:InvokeFunction"
        )

    def _create_outputs(self) -> None:
        """Create CloudFormation outputs for bucket names and ARNs."""
        # Documents bucket outputs
        self.add_stack_output(
            "DocumentsBucketName",
            value=self.documents_bucket.bucket_name,
            description="S3 bucket name for document storage",
            export_name=f"{self.stack_name}-DocumentsBucketName"
        )
        
        self.add_stack_output(
            "DocumentsBucketArn",
            value=self.documents_bucket.bucket_arn,
            description="S3 bucket ARN for document storage",
            export_name=f"{self.stack_name}-DocumentsBucketArn"
        )
        
        # Vector bucket outputs
        self.add_stack_output(
            "VectorBucketName",
            value=self.vector_bucket.ref,
            description="S3 Vector bucket name for embeddings",
            export_name=f"{self.stack_name}-VectorBucketName"
        )
        
        self.add_stack_output(
            "VectorBucketArn",
            value=self.vector_bucket.attr_arn,
            description="S3 Vector bucket ARN for embeddings",
            export_name=f"{self.stack_name}-VectorBucketArn"
        )
        
        # Vector index ARN (constructed from bucket ARN)
        vector_index_arn = f"{self.vector_bucket.attr_arn}/index/*"
        self.add_stack_output(
            "VectorIndexArn",
            value=vector_index_arn,
            description="S3 Vector index ARN for queries",
            export_name=f"{self.stack_name}-VectorIndexArn"
        )
