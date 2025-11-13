"""
AppRunner Hosting Stack for Document Insight Extraction System

This module defines the AppRunner service infrastructure for hosting the React frontend,
including ECR repository for Docker images, CodeBuild project for building and pushing
the Docker image, and AppRunner service configuration.
"""
from aws_cdk import (
    Duration,
    aws_ecr as ecr,
    aws_apprunner as apprunner,
    aws_iam as iam,
    aws_codebuild as codebuild,
    aws_s3 as s3,
    CfnOutput,
)
from constructs import Construct
from .base_stack import BaseDocumentInsightStack
from typing import Dict, Any


class AppRunnerHostingStack(BaseDocumentInsightStack):
    """
    Stack for AppRunner hosting infrastructure.
    
    Creates:
    - ECR repository for UI Docker images
    - CodeBuild project for building and pushing Docker images
    - AppRunner service with auto-scaling
    - IAM roles for AppRunner and CodeBuild
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        env_name: str,
        config: Dict[str, Any],
        api_endpoint: str,
        wss_endpoint: str,
        user_pool_id: str,
        user_pool_client_id: str,
        **kwargs
    ) -> None:
        """
        Initialize the AppRunner hosting stack.
        
        Args:
            scope: CDK app or parent construct
            construct_id: Unique identifier for this stack
            env_name: Environment name (dev, prod, etc.)
            config: Environment-specific configuration
            api_endpoint: API Gateway REST endpoint URL
            wss_endpoint: WebSocket API endpoint URL
            user_pool_id: Cognito User Pool ID
            user_pool_client_id: Cognito User Pool Client ID
            **kwargs: Additional stack properties
        """
        super().__init__(scope, construct_id, env_name, config, **kwargs)

        self.api_endpoint = api_endpoint
        self.wss_endpoint = wss_endpoint
        self.user_pool_id = user_pool_id
        self.user_pool_client_id = user_pool_client_id

        # Create S3 bucket for build artifacts
        self.artifacts_bucket = self._create_artifacts_bucket()

        # Create ECR repository
        self.ecr_repository = self._create_ecr_repository()

        # Create AppRunner service
        self.apprunner_service = self._create_apprunner_service()

        # Create CodeBuild project for UI build
        self.ui_build_project = self._create_ui_build_project()

        # Export outputs
        self._create_outputs()

    def _create_artifacts_bucket(self) -> s3.Bucket:
        """
        Create S3 bucket for CodeBuild artifacts.
        
        Returns:
            S3 Bucket construct
        """
        bucket = s3.Bucket(
            self,
            "UIBuildArtifactsBucket",
            bucket_name=f"{self.project_name}-ui-artifacts-{self.env_name}-{self.account}",
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=self.removal_policy,
            auto_delete_objects=(self.env_name == "dev")
        )
        
        return bucket

    def _create_ecr_repository(self) -> ecr.Repository:
        """
        Create ECR repository for UI Docker images.
        
        Returns:
            ECR Repository construct
        """
        repository = ecr.Repository(
            self,
            "UIRepository",
            repository_name=self.get_resource_name("ui-repo"),
            removal_policy=self.removal_policy,
            image_scan_on_push=True,
            lifecycle_rules=[
                ecr.LifecycleRule(
                    description="Keep last 10 images",
                    max_image_count=10,
                    rule_priority=1
                )
            ]
        )

        return repository

    def _create_apprunner_service(self) -> apprunner.CfnService:
        """
        Create AppRunner service for hosting the React frontend.
        
        Returns:
            AppRunner Service construct
        """
        # Create IAM role for AppRunner instance
        instance_role = iam.Role(
            self,
            "AppRunnerInstanceRole",
            assumed_by=iam.ServicePrincipal("tasks.apprunner.amazonaws.com"),
            description="IAM role for AppRunner instance"
        )

        # Create IAM role for AppRunner to access ECR
        access_role = iam.Role(
            self,
            "AppRunnerAccessRole",
            assumed_by=iam.ServicePrincipal("build.apprunner.amazonaws.com"),
            description="IAM role for AppRunner to access ECR",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSAppRunnerServicePolicyForECRAccess"
                )
            ]
        )

        # Get configuration values
        cpu = self.config.get("apprunner_cpu", "2048")  # 2 vCPU
        memory = self.config.get("apprunner_memory", "4096")  # 4 GB
        min_instances = self.config.get("apprunner_min_instances", 1)
        max_instances = self.config.get("apprunner_max_instances", 10)

        # Create AppRunner service
        service = apprunner.CfnService(
            self,
            "UIService",
            service_name=self.get_resource_name("ui-service"),
            source_configuration=apprunner.CfnService.SourceConfigurationProperty(
                authentication_configuration=apprunner.CfnService.AuthenticationConfigurationProperty(
                    access_role_arn=access_role.role_arn
                ),
                image_repository=apprunner.CfnService.ImageRepositoryProperty(
                    image_identifier=f"{self.ecr_repository.repository_uri}:latest",
                    image_repository_type="ECR",
                    image_configuration=apprunner.CfnService.ImageConfigurationProperty(
                        port="80",
                        runtime_environment_variables=[
                            apprunner.CfnService.KeyValuePairProperty(
                                name="REACT_APP_API_ENDPOINT",
                                value=self.api_endpoint
                            ),
                            apprunner.CfnService.KeyValuePairProperty(
                                name="REACT_APP_WSS_ENDPOINT",
                                value=self.wss_endpoint
                            ),
                            apprunner.CfnService.KeyValuePairProperty(
                                name="REACT_APP_USER_POOL_ID",
                                value=self.user_pool_id
                            ),
                            apprunner.CfnService.KeyValuePairProperty(
                                name="REACT_APP_USER_POOL_CLIENT_ID",
                                value=self.user_pool_client_id
                            ),
                            apprunner.CfnService.KeyValuePairProperty(
                                name="REACT_APP_REGION",
                                value=self.region
                            )
                        ]
                    )
                )
            ),
            instance_configuration=apprunner.CfnService.InstanceConfigurationProperty(
                cpu=cpu,
                memory=memory,
                instance_role_arn=instance_role.role_arn
            ),
            auto_scaling_configuration_arn=None,  # Use default auto-scaling
            health_check_configuration=apprunner.CfnService.HealthCheckConfigurationProperty(
                protocol="HTTP",
                path="/health",
                interval=10,
                timeout=5,
                healthy_threshold=1,
                unhealthy_threshold=5
            )
        )

        return service

    def _create_ui_build_project(self) -> codebuild.Project:
        """
        Create CodeBuild project for building and deploying the React UI.
        
        Returns:
            CodeBuild Project construct
        """
        # Create IAM role for CodeBuild
        codebuild_role = iam.Role(
            self,
            "UIBuildRole",
            assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
            description="Role for UI build CodeBuild project",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AWSCodeBuildDeveloperAccess"
                )
            ]
        )
        
        # Grant ECR permissions
        self.ecr_repository.grant_pull_push(codebuild_role)
        
        # Grant S3 permissions for artifacts
        self.artifacts_bucket.grant_read_write(codebuild_role)
        
        # Grant AppRunner permissions to trigger deployment
        codebuild_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "apprunner:StartDeployment",
                    "apprunner:DescribeService"
                ],
                resources=[self.apprunner_service.attr_service_arn]
            )
        )
        
        # Grant CloudWatch Logs permissions
        codebuild_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                resources=[
                    f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/codebuild/*"
                ]
            )
        )
        
        # Create CodeBuild project
        project = codebuild.Project(
            self,
            "UIBuildProject",
            project_name=f"{self.project_name}-ui-build-{self.env_name}",
            description="Build and deploy React UI to AppRunner",
            role=codebuild_role,
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
                compute_type=codebuild.ComputeType.MEDIUM,
                privileged=True  # Required for Docker builds
            ),
            build_spec=codebuild.BuildSpec.from_source_filename(
                "buildspecs/buildspec_dockerize_ui.yml"
            ),
            timeout=Duration.minutes(30),
            artifacts=codebuild.Artifacts.s3(
                bucket=self.artifacts_bucket,
                include_build_id=True,
                package_zip=True,
                path="ui-builds"
            ),
            environment_variables={
                "PROJECT_NAME": codebuild.BuildEnvironmentVariable(
                    value=self.project_name
                ),
                "ENV_NAME": codebuild.BuildEnvironmentVariable(
                    value=self.env_name
                ),
                "AWS_REGION": codebuild.BuildEnvironmentVariable(
                    value=self.region
                ),
                "ECR_REPOSITORY_URI": codebuild.BuildEnvironmentVariable(
                    value=self.ecr_repository.repository_uri
                ),
                "APPRUNNER_SERVICE_ARN": codebuild.BuildEnvironmentVariable(
                    value=self.apprunner_service.attr_service_arn
                )
            },
            cache=codebuild.Cache.local(
                codebuild.LocalCacheMode.CUSTOM,
                codebuild.LocalCacheMode.DOCKER_LAYER
            )
        )
        
        return project

    def _create_outputs(self) -> None:
        """Create CloudFormation outputs for the stack."""
        # ECR repository URI
        self.add_stack_output(
            "ECRRepositoryUri",
            self.ecr_repository.repository_uri,
            description="ECR repository URI for UI Docker images"
        )

        # ECR repository name
        self.add_stack_output(
            "ECRRepositoryName",
            self.ecr_repository.repository_name,
            description="ECR repository name"
        )

        # AppRunner service URL
        self.add_stack_output(
            "AppRunnerServiceUrl",
            f"https://{self.apprunner_service.attr_service_url}",
            description="AppRunner service URL for the frontend application"
        )

        # AppRunner service ARN
        self.add_stack_output(
            "AppRunnerServiceArn",
            self.apprunner_service.attr_service_arn,
            description="AppRunner service ARN"
        )

        # CodeBuild project name
        self.add_stack_output(
            "UIBuildProjectName",
            self.ui_build_project.project_name,
            description="CodeBuild project name for UI builds"
        )

        # Artifacts bucket name
        self.add_stack_output(
            "ArtifactsBucketName",
            self.artifacts_bucket.bucket_name,
            description="S3 bucket for UI build artifacts"
        )
