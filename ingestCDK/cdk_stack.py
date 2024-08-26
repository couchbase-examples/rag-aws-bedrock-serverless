from aws_cdk import (
    Duration,
    Stack,
    aws_sqs as sqs,
    aws_ecr as ecr,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_apigateway as apigateway,
)
import os
from dotenv import load_dotenv
from constructs import Construct


class CouchbaseIngestStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        load_dotenv(dotenv_path='.env')
        
        queue = sqs.Queue(
            self, "CouchbaseBedrockQueue",
            visibility_timeout=Duration.seconds(90)
        )
        
        repository = ecr.Repository.from_repository_name(
            self, "queue-to-bedrock-to-couchbase", "queue-to-bedrock-to-couchbase"
        )
        
        lambda_function = _lambda.DockerImageFunction(
            self, "IngestionFunction",
            code=_lambda.DockerImageCode.from_ecr(repository, tag_or_digest="latest"),
            environment={
                'SQS_QUEUE_URL': queue.queue_url,
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
        
        sqs_to_lambda_role = iam.Role(
            self, "SQSToLambdaRole",
            assumed_by=iam.ServicePrincipal("sqs.amazonaws.com")
        )

        # Attach policy to the role
        sqs_to_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["lambda:InvokeFunction"],
                resources=[lambda_function.function_arn]
            )
        )

        _lambda.EventSourceMapping(
            self, "SQSTrigger",
            target=lambda_function,
            event_source_arn=queue.queue_arn,
            batch_size=10  # Adjust the batch size as needed
        )
        
        queue.grant_consume_messages(lambda_function)
        
        lambda_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=["arn:aws:bedrock:ap-south-1::foundation-model/amazon.titan-embed-image-v1"]
            )
        )
        
        api = apigateway.RestApi(self, "CouchbaseBedrockAPI",
            rest_api_name="SQSService",
            description="API Gateway to send data to SQS queue."
        )
        
        # Create a resource and POST method in API Gateway
        sqs_integration = apigateway.AwsIntegration(
            service="sqs",
            path=f"{self.account}/{queue.queue_name}",
            integration_http_method="POST",
            options=apigateway.IntegrationOptions(
                credentials_role=iam.Role(
                    self, "ApiGatewaySqsRole",
                    assumed_by=iam.ServicePrincipal("apigateway.amazonaws.com"),
                    managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSQSFullAccess")]
                ),
                request_parameters={
                    "integration.request.header.Content-Type": "'application/x-www-form-urlencoded'"
                },
                request_templates={
                    "application/json": f"Action=SendMessage&MessageBody=$input.body&QueueUrl={queue.queue_url}"
                },
                integration_responses=[
                    apigateway.IntegrationResponse(
                        status_code="200",
                        response_templates={"application/json": ""}
                    )
                ]
            )
        )

        api_resource = api.root.add_resource("send")
        api_resource.add_method(
            "POST", sqs_integration,
            authorization_type=apigateway.AuthorizationType.NONE,
            method_responses=[
                apigateway.MethodResponse(status_code="200")
            ]
        )