from aws_cdk import (
    Duration,
    Stack,
    aws_ecr as ecr,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_apigateway as apigateway,
)
import os
from dotenv import load_dotenv
from constructs import Construct


class CouchbaseChatStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        load_dotenv(dotenv_path='.env')

        repository = ecr.Repository.from_repository_name(
            self, "chat", "chat"
        )

        lambda_function = _lambda.DockerImageFunction(
            self, "ChatFunction",
            code=_lambda.DockerImageCode.from_ecr(repository, tag_or_digest="latest"),
            environment={
                'CB_CONN_STR': str(os.getenv('CB_CONN_STR')),
                'CB_USERNAME': str(os.getenv('CB_USERNAME')),
                'CB_PASSWORD': str(os.getenv('CB_PASSWORD')),
                'CB_BUCKET': str(os.getenv('CB_BUCKET')),
                'CB_SCOPE': str(os.getenv('CB_SCOPE')),
                'CB_COLLECTION': str(os.getenv('CB_COLLECTION')),
                'CB_INDEX_NAME': str(os.getenv('CB_INDEX_NAME'))
            },
            timeout=Duration.seconds(90),  # Adjust the timeout as needed
        )

        lambda_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=["arn:aws:bedrock:ap-south-1::*"]
            )
        )

        api = apigateway.RestApi(self, "CouchbaseBedrockChatAPI",
                                 rest_api_name="ChatLambdaService",
                                 description="API Gateway to send question to Chat Lambda Function"
                                 )

        api_resource = api.root.add_resource("chat")
        lambda_integration = apigateway.LambdaIntegration(
            handler=lambda_function,
            proxy=True
        )

        api_resource.add_method(
            "POST", lambda_integration,
            authorization_type=apigateway.AuthorizationType.NONE,
            method_responses=[
                apigateway.MethodResponse(status_code="200")
            ]
        )
