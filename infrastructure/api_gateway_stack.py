"""
API Gateway Stack for Document Insight Extraction System

This module defines the REST API Gateway with endpoints for document management
and insight extraction, including Cognito authorization and CORS configuration.

Note: WebSocket API for real-time progress updates is defined in websocket_api_stack.py
"""
from aws_cdk import (
    aws_apigateway as apigateway,
    aws_lambda as lambda_,
    aws_cognito as cognito,
    Duration,
)
from constructs import Construct
from infrastructure.base_stack import BaseDocumentInsightStack
from typing import Optional


class ApiGatewayStack(BaseDocumentInsightStack):
    """
    Stack for API Gateway REST API resources.
    
    Creates:
    - REST API with regional endpoint
    - Cognito authorizer for authentication
    - Document management endpoints
    - Insight extraction endpoints
    - CORS configuration
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        env_name: str,
        config: dict,
        cognito_user_pool: cognito.IUserPool,
        **kwargs
    ) -> None:
        """
        Initialize the API Gateway stack.
        
        Args:
            scope: CDK app or parent construct
            construct_id: Unique identifier for this stack
            env_name: Environment name (dev, prod, etc.)
            config: Environment-specific configuration dictionary
            cognito_user_pool: Cognito User Pool for authorization
            **kwargs: Additional stack properties
        """
        super().__init__(scope, construct_id, env_name, config, **kwargs)

        self.cognito_user_pool = cognito_user_pool
        
        # Get throttling configuration from config
        self.throttle_rate = config.get("api_throttle_rate", 1000)
        self.throttle_burst = config.get("api_throttle_burst", 2000)
        
        # Create REST API
        self.rest_api = self._create_rest_api()
        
        # Create Cognito authorizer
        self.authorizer = self._create_cognito_authorizer()
        
        # Store Lambda functions (to be set later)
        self.presigned_url_lambda: Optional[lambda_.IFunction] = None
        self.document_list_lambda: Optional[lambda_.IFunction] = None
        self.insight_extraction_lambda: Optional[lambda_.IFunction] = None
        
        # Export outputs
        self._create_outputs()

    def _create_rest_api(self) -> apigateway.RestApi:
        """
        Create REST API with regional endpoint and CORS configuration.
        
        Returns:
            RestApi construct
        """
        # CORS configuration for AppRunner origin
        # In production, this should be restricted to the specific AppRunner URL
        cors_options = apigateway.CorsOptions(
            allow_origins=apigateway.Cors.ALL_ORIGINS,  # Will be restricted in production
            allow_methods=apigateway.Cors.ALL_METHODS,
            allow_headers=[
                "Content-Type",
                "X-Amz-Date",
                "Authorization",
                "X-Api-Key",
                "X-Amz-Security-Token",
                "X-Amz-User-Agent"
            ],
            allow_credentials=True,
            max_age=Duration.hours(1)
        )

        # Create REST API
        rest_api = apigateway.RestApi(
            self,
            "DocumentInsightRestApi",
            rest_api_name=self.get_resource_name("rest-api"),
            description=f"Document Insight Extraction System REST API - {self.env_name}",
            # Regional endpoint for better performance and lower cost
            endpoint_types=[apigateway.EndpointType.REGIONAL],
            # CORS configuration
            default_cors_preflight_options=cors_options,
            # Deployment configuration
            deploy=True,
            deploy_options=apigateway.StageOptions(
                stage_name=self.env_name,
                # Throttling configuration
                throttling_rate_limit=self.throttle_rate,
                throttling_burst_limit=self.throttle_burst,
                # Logging configuration
                logging_level=apigateway.MethodLoggingLevel.INFO,
                data_trace_enabled=True,
                metrics_enabled=True,
                # Tracing
                tracing_enabled=True
            ),
            # CloudWatch role for logging
            cloud_watch_role=True,
            # API key configuration (optional)
            api_key_source_type=apigateway.ApiKeySourceType.HEADER
        )

        return rest_api

    def _create_cognito_authorizer(self) -> apigateway.CognitoUserPoolsAuthorizer:
        """
        Create Cognito User Pools Authorizer for API Gateway.
        
        Returns:
            CognitoUserPoolsAuthorizer construct
        """
        authorizer = apigateway.CognitoUserPoolsAuthorizer(
            self,
            "DocumentInsightApiAuthorizer",
            cognito_user_pools=[self.cognito_user_pool],
            authorizer_name=self.get_resource_name("api-authorizer"),
            # Token validity - 24 hours
            results_cache_ttl=Duration.hours(24),
            # Identity source - Authorization header
            identity_source="method.request.header.Authorization"
        )

        return authorizer


    def configure_presigned_url_endpoint(
        self,
        presigned_url_lambda: lambda_.IFunction
    ) -> None:
        """
        Configure POST /documents/presigned-url endpoint.
        
        This endpoint generates presigned POST URLs for direct S3 uploads.
        
        Args:
            presigned_url_lambda: Lambda function to generate presigned URLs
        """
        self.presigned_url_lambda = presigned_url_lambda
        
        # Create /documents resource
        documents_resource = self.rest_api.root.add_resource("documents")
        
        # Create /documents/presigned-url resource
        presigned_url_resource = documents_resource.add_resource("presigned-url")
        
        # Create Lambda integration
        presigned_url_integration = apigateway.LambdaIntegration(
            presigned_url_lambda,
            proxy=True,
            integration_responses=[
                apigateway.IntegrationResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": "'*'"
                    }
                )
            ]
        )
        
        # Add POST method with Cognito authorizer
        presigned_url_resource.add_method(
            "POST",
            presigned_url_integration,
            authorizer=self.authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
            method_responses=[
                apigateway.MethodResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": True
                    }
                )
            ]
        )

    def configure_document_list_endpoint(
        self,
        document_list_lambda: lambda_.IFunction
    ) -> None:
        """
        Configure GET /documents endpoint.
        
        This endpoint lists all documents for the authenticated user.
        
        Args:
            document_list_lambda: Lambda function to list documents
        """
        self.document_list_lambda = document_list_lambda
        
        # Get or create /documents resource
        documents_resource = self.rest_api.root.get_resource("documents")
        if not documents_resource:
            documents_resource = self.rest_api.root.add_resource("documents")
        
        # Create Lambda integration
        document_list_integration = apigateway.LambdaIntegration(
            document_list_lambda,
            proxy=True,
            integration_responses=[
                apigateway.IntegrationResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": "'*'"
                    }
                )
            ]
        )
        
        # Add GET method with Cognito authorizer
        documents_resource.add_method(
            "GET",
            document_list_integration,
            authorizer=self.authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
            method_responses=[
                apigateway.MethodResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": True
                    }
                )
            ]
        )

    def configure_insight_extraction_endpoint(
        self,
        insight_extraction_lambda: lambda_.IFunction
    ) -> None:
        """
        Configure POST /insights/extract endpoint.
        
        This endpoint extracts insights from a document using natural language prompts.
        Configured with 300 second timeout for long-running insight generation.
        
        Args:
            insight_extraction_lambda: Lambda function to extract insights
        """
        self.insight_extraction_lambda = insight_extraction_lambda
        
        # Create /insights resource
        insights_resource = self.rest_api.root.add_resource("insights")
        
        # Create /insights/extract resource
        extract_resource = insights_resource.add_resource("extract")
        
        # Create Lambda integration with extended timeout
        insight_extraction_integration = apigateway.LambdaIntegration(
            insight_extraction_lambda,
            proxy=True,
            timeout=Duration.seconds(300),  # 5 minutes for insight generation
            integration_responses=[
                apigateway.IntegrationResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": "'*'"
                    }
                )
            ]
        )
        
        # Add POST method with Cognito authorizer
        extract_resource.add_method(
            "POST",
            insight_extraction_integration,
            authorizer=self.authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
            method_responses=[
                apigateway.MethodResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": True
                    }
                )
            ]
        )

    def configure_insight_retrieval_endpoint(
        self,
        insight_extraction_lambda: lambda_.IFunction
    ) -> None:
        """
        Configure GET /insights/{docId} endpoint.
        
        This endpoint retrieves previously extracted insights from cache.
        
        Args:
            insight_extraction_lambda: Lambda function to retrieve insights
        """
        # Get or create /insights resource
        insights_resource = self.rest_api.root.get_resource("insights")
        if not insights_resource:
            insights_resource = self.rest_api.root.add_resource("insights")
        
        # Create /insights/{docId} resource with path parameter
        doc_id_resource = insights_resource.add_resource("{docId}")
        
        # Create Lambda integration
        insight_retrieval_integration = apigateway.LambdaIntegration(
            insight_extraction_lambda,
            proxy=True,
            integration_responses=[
                apigateway.IntegrationResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": "'*'"
                    }
                )
            ]
        )
        
        # Add GET method with Cognito authorizer
        doc_id_resource.add_method(
            "GET",
            insight_retrieval_integration,
            authorizer=self.authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
            method_responses=[
                apigateway.MethodResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": True
                    }
                )
            ],
            request_parameters={
                "method.request.path.docId": True  # Required path parameter
            }
        )

    def _create_outputs(self) -> None:
        """Create CloudFormation outputs for API endpoints."""
        # API Gateway URL
        self.add_stack_output(
            "RestApiUrl",
            value=self.rest_api.url,
            description="REST API Gateway URL",
            export_name=f"{self.stack_name}-RestApiUrl"
        )
        
        # API Gateway ID
        self.add_stack_output(
            "RestApiId",
            value=self.rest_api.rest_api_id,
            description="REST API Gateway ID",
            export_name=f"{self.stack_name}-RestApiId"
        )
        
        # API Gateway ARN
        self.add_stack_output(
            "RestApiArn",
            value=self.rest_api.arn_for_execute_api(),
            description="REST API Gateway ARN",
            export_name=f"{self.stack_name}-RestApiArn"
        )
        
        # Stage name
        self.add_stack_output(
            "RestApiStage",
            value=self.env_name,
            description="REST API Gateway stage name",
            export_name=f"{self.stack_name}-RestApiStage"
        )
