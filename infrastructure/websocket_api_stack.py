"""
WebSocket API Stack for Document Insight Extraction System

This module defines the WebSocket API Gateway for real-time progress updates
during document processing, including connection management and message routing.
"""
from aws_cdk import (
    aws_apigatewayv2 as apigatewayv2,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_logs as logs,
    CfnOutput,
    RemovalPolicy,
)
from constructs import Construct
from infrastructure.base_stack import BaseDocumentInsightStack
from typing import Optional


class WebSocketApiStack(BaseDocumentInsightStack):
    """
    Stack for API Gateway WebSocket API resources.
    
    Creates:
    - WebSocket API for real-time communication
    - Routes: $connect, $disconnect, $default, progress
    - Lambda integrations for connection management
    - IAM roles for API Gateway to invoke Lambda
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
        Initialize the WebSocket API stack.
        
        Args:
            scope: CDK app or parent construct
            construct_id: Unique identifier for this stack
            env_name: Environment name (dev, prod, etc.)
            config: Environment-specific configuration dictionary
            **kwargs: Additional stack properties
        """
        super().__init__(scope, construct_id, env_name, config, **kwargs)

        # Store Lambda function references (to be set later)
        self.connection_handler_lambda: Optional[lambda_.IFunction] = None
        
        # Create WebSocket API
        self.websocket_api = self._create_websocket_api()
        
        # Store route and integration references
        self.connect_route: Optional[apigatewayv2.CfnRoute] = None
        self.disconnect_route: Optional[apigatewayv2.CfnRoute] = None
        self.default_route: Optional[apigatewayv2.CfnRoute] = None
        self.progress_route: Optional[apigatewayv2.CfnRoute] = None
        
        # Store deployment and stage references
        self.deployment: Optional[apigatewayv2.CfnDeployment] = None
        self.stage: Optional[apigatewayv2.CfnStage] = None
        
        # Export outputs
        self._create_outputs()

    def _create_websocket_api(self) -> apigatewayv2.CfnApi:
        """
        Create WebSocket API with route selection expression.
        
        Returns:
            CfnApi construct for WebSocket protocol
        """
        # Create CloudWatch log group for WebSocket API
        log_group = logs.LogGroup(
            self,
            "WebSocketApiLogGroup",
            log_group_name=f"/aws/apigateway/{self.get_resource_name('websocket-api')}",
            removal_policy=self.removal_policy,
            retention=logs.RetentionDays.ONE_MONTH
        )
        
        # Create WebSocket API
        websocket_api = apigatewayv2.CfnApi(
            self,
            "DocumentInsightWebSocketApi",
            name=self.get_resource_name("websocket-api"),
            protocol_type="WEBSOCKET",
            description=f"Document Insight Extraction System WebSocket API - {self.env_name}",
            # Route selection expression - determines which route to invoke
            # Uses the 'action' field from the message body
            route_selection_expression="$request.body.action",
        )
        
        return websocket_api

    def configure_websocket_routes(
        self,
        connection_handler_lambda: lambda_.IFunction
    ) -> None:
        """
        Configure WebSocket routes and Lambda integrations.
        
        Creates routes for:
        - $connect: Client connection establishment
        - $disconnect: Client disconnection
        - $default: Default message handler
        - progress: Document processing progress updates
        
        Args:
            connection_handler_lambda: Lambda function to handle WebSocket connections
        """
        self.connection_handler_lambda = connection_handler_lambda
        
        # Create IAM role for API Gateway to invoke Lambda
        integration_role = self._create_integration_role()
        
        # Create Lambda integration
        integration = self._create_lambda_integration(integration_role)
        
        # Create routes
        self.connect_route = self._create_route(
            route_id="ConnectRoute",
            route_key="$connect",
            integration_id=integration.ref,
            description="Handle WebSocket connection establishment"
        )
        
        self.disconnect_route = self._create_route(
            route_id="DisconnectRoute",
            route_key="$disconnect",
            integration_id=integration.ref,
            description="Handle WebSocket disconnection"
        )
        
        self.default_route = self._create_route(
            route_id="DefaultRoute",
            route_key="$default",
            integration_id=integration.ref,
            description="Handle default WebSocket messages"
        )
        
        self.progress_route = self._create_route(
            route_id="ProgressRoute",
            route_key="progress",
            integration_id=integration.ref,
            description="Handle document processing progress updates"
        )
        
        # Create deployment and stage
        self._create_deployment_and_stage()

    def _create_integration_role(self) -> iam.Role:
        """
        Create IAM role for API Gateway to invoke Lambda functions.
        
        Returns:
            IAM Role with Lambda invoke permissions
        """
        role = iam.Role(
            self,
            "WebSocketIntegrationRole",
            role_name=self.get_resource_name("websocket-integration-role"),
            assumed_by=iam.ServicePrincipal("apigateway.amazonaws.com"),
            description="Role for API Gateway WebSocket to invoke Lambda functions"
        )
        
        # Grant permission to invoke Lambda function
        if self.connection_handler_lambda:
            self.connection_handler_lambda.grant_invoke(role)
        
        return role

    def _create_lambda_integration(
        self,
        integration_role: iam.Role
    ) -> apigatewayv2.CfnIntegration:
        """
        Create Lambda proxy integration for WebSocket API.
        
        Args:
            integration_role: IAM role for API Gateway to invoke Lambda
            
        Returns:
            CfnIntegration construct
        """
        integration = apigatewayv2.CfnIntegration(
            self,
            "WebSocketLambdaIntegration",
            api_id=self.websocket_api.ref,
            integration_type="AWS_PROXY",
            integration_uri=(
                f"arn:aws:apigateway:{self.region}:lambda:path/2015-03-31/functions/"
                f"{self.connection_handler_lambda.function_arn}/invocations"
            ),
            credentials_arn=integration_role.role_arn,
            # Content handling
            content_handling_strategy="CONVERT_TO_TEXT",
            # Timeout in milliseconds (29 seconds - API Gateway max)
            timeout_in_millis=29000,
        )
        
        return integration

    def _create_route(
        self,
        route_id: str,
        route_key: str,
        integration_id: str,
        description: str = ""
    ) -> apigatewayv2.CfnRoute:
        """
        Create a WebSocket route.
        
        Args:
            route_id: Unique identifier for the route construct
            route_key: Route key ($connect, $disconnect, $default, or custom)
            integration_id: Integration ID to associate with this route
            description: Human-readable description
            
        Returns:
            CfnRoute construct
        """
        route = apigatewayv2.CfnRoute(
            self,
            route_id,
            api_id=self.websocket_api.ref,
            route_key=route_key,
            target=f"integrations/{integration_id}",
            # Authorization - will be configured later if needed
            authorization_type="NONE",
            # Operation name for CloudWatch metrics
            operation_name=route_key.replace("$", "").replace("_", "-") or "default",
        )
        
        return route

    def _create_deployment_and_stage(self) -> None:
        """
        Create deployment and stage for WebSocket API.
        
        The deployment must depend on all routes to ensure they are created first.
        """
        # Create deployment
        self.deployment = apigatewayv2.CfnDeployment(
            self,
            "WebSocketApiDeployment",
            api_id=self.websocket_api.ref,
            description=f"Deployment for {self.env_name} environment"
        )
        
        # Add dependencies on all routes
        if self.connect_route:
            self.deployment.add_dependency(self.connect_route)
        if self.disconnect_route:
            self.deployment.add_dependency(self.disconnect_route)
        if self.default_route:
            self.deployment.add_dependency(self.default_route)
        if self.progress_route:
            self.deployment.add_dependency(self.progress_route)
        
        # Create CloudWatch log group for stage
        stage_log_group = logs.LogGroup(
            self,
            "WebSocketStageLogGroup",
            log_group_name=f"/aws/apigateway/{self.get_resource_name('websocket-api')}/{self.env_name}",
            removal_policy=self.removal_policy,
            retention=logs.RetentionDays.ONE_MONTH
        )
        
        # Create stage
        self.stage = apigatewayv2.CfnStage(
            self,
            "WebSocketApiStage",
            api_id=self.websocket_api.ref,
            stage_name=self.env_name,
            deployment_id=self.deployment.ref,
            description=f"WebSocket API stage for {self.env_name} environment",
            # Default route settings
            default_route_settings=apigatewayv2.CfnStage.RouteSettingsProperty(
                # Throttling
                throttling_burst_limit=self.config.get("api_throttle_burst", 2000),
                throttling_rate_limit=self.config.get("api_throttle_rate", 1000),
                # Logging
                logging_level="INFO",
                data_trace_enabled=True,
                detailed_metrics_enabled=True,
            ),
            # Access logging
            access_log_settings=apigatewayv2.CfnStage.AccessLogSettingsProperty(
                destination_arn=stage_log_group.log_group_arn,
                format='$context.requestId $context.routeKey $context.status'
            )
        )

    def get_websocket_url(self) -> str:
        """
        Get the WebSocket API URL.
        
        Returns:
            WebSocket URL in format: wss://{api-id}.execute-api.{region}.amazonaws.com/{stage}
        """
        if not self.stage:
            raise ValueError("Stage not created yet. Call configure_websocket_routes first.")
        
        return f"wss://{self.websocket_api.ref}.execute-api.{self.region}.amazonaws.com/{self.env_name}"

    def grant_manage_connections(self, grantee: iam.IGrantable) -> iam.Grant:
        """
        Grant permission to manage WebSocket connections.
        
        This allows Lambda functions to send messages to connected clients.
        
        Args:
            grantee: The principal to grant permissions to (e.g., Lambda function)
            
        Returns:
            Grant object
        """
        return iam.Grant.add_to_principal(
            grantee=grantee,
            actions=["execute-api:ManageConnections"],
            resource_arns=[
                f"arn:aws:execute-api:{self.region}:{self.account}:{self.websocket_api.ref}/{self.env_name}/*"
            ]
        )

    def add_websocket_url_output(self) -> None:
        """
        Add WebSocket URL output after stage is created.
        
        This must be called after configure_websocket_routes.
        """
        if not self.stage:
            raise ValueError("Stage not created yet. Call configure_websocket_routes first.")
        
        # WebSocket API URL
        websocket_url = f"wss://{self.websocket_api.ref}.execute-api.{self.region}.amazonaws.com/{self.env_name}"
        
        self.add_stack_output(
            "WebSocketApiUrl",
            value=websocket_url,
            description="WebSocket API Gateway URL",
            export_name=f"{self.stack_name}-WebSocketApiUrl"
        )
        
        # Stage name
        self.add_stack_output(
            "WebSocketApiStage",
            value=self.env_name,
            description="WebSocket API Gateway stage name",
            export_name=f"{self.stack_name}-WebSocketApiStage"
        )

    def _create_outputs(self) -> None:
        """Create CloudFormation outputs for WebSocket API."""
        # WebSocket API ID
        self.add_stack_output(
            "WebSocketApiId",
            value=self.websocket_api.ref,
            description="WebSocket API Gateway ID",
            export_name=f"{self.stack_name}-WebSocketApiId"
        )
        
        # Note: WebSocket URL output is added via add_websocket_url_output()
        # after the stage is created in configure_websocket_routes()
