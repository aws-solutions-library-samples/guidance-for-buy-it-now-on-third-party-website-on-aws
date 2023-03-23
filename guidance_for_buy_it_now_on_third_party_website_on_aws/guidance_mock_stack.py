from aws_cdk.aws_apigateway import IntegrationResponse, MethodResponse, IntegrationResponse, MethodResponse
from aws_cdk import CfnOutput, Stack, Aws
from aws_cdk.aws_apigateway import MockIntegration, PassthroughBehavior, RestApi
from aws_cdk import (
    RemovalPolicy,
    aws_dynamodb as dynamodb_,
    aws_logs as logs,
    aws_apigateway as apigateway_,
    aws_lambda as lambda_,
    Duration,
    aws_iam as iam,
    Aws,
    ArnFormat,
)
from cdk_nag import (
    NagSuppressions
)
from constructs import Construct
# This stack is used to mock third party services used in this guidance.
# The following resources are created:
# * Payment Gateway URL - Used to validate payment details
# * Pre-Order Gateway URL - Used to lock inventory at the start of the order process
# * Order Gateway URL - Used to place order to third party store api endpoint
# * StoreProduct DynamoDB table - This stores the product details from multiple stores
class MockStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, description: str, **kwargs) -> None:
        super().__init__(scope, construct_id, description=description, **kwargs)

        log_group = logs.LogGroup(self, "BuyitNow-Mock-ApiGatewayAccessLogs")
        lambda_role = iam.Role(self, "ThirdPartyCustomAuthLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Custom Authentication Lambda role for ThirdParty stack"
        )
        # Lambda auth function
        auth_function = lambda_.Function(self, "ThirdpartyAuthTokenLambda",
                                          code=lambda_.Code.from_asset(
                                              './lambda/code/utils'),
                                          handler="api_gateway_authorizer.handler",
                                          runtime=lambda_.Runtime.NODEJS_18_X,
                                          role=lambda_role)
        lambda_auth_policy = iam.Policy(self, 'ThirdPartyLambdaAuthPolicy', statements=[
            iam.PolicyStatement(
                actions=["logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"],
                effect=iam.Effect.ALLOW,
                resources=[
                    Stack.of(self).format_arn(
                        service="logs",
                        arn_format=ArnFormat.COLON_RESOURCE_NAME,
                        resource="log-group", 
                        resource_name="/aws/lambda/"+auth_function.function_name
                    ),
                    Stack.of(self).format_arn(
                        service="logs",
                        arn_format=ArnFormat.COLON_RESOURCE_NAME,
                        resource="log-group", 
                        resource_name="/aws/lambda/"+auth_function.function_name+":*"
                    ),
                ]
            )]
        )
        lambda_auth_policy.attach_to_role(auth_function.role)
        NagSuppressions.add_resource_suppressions(lambda_auth_policy, suppressions=[
            {
                "id": 'AwsSolutions-IAM5',
                "reason": f"Only suppresses AwsSolutions-IAM5 /aws/lambda/{auth_function.function_name}:* \
                            This is needed to allow the role to create log streams inside the log group",
                "applies_to": [{
                    "regex":f"/^Resource::arn:<[A-Za-z:]+>:logs:<[A-Za-z:]+>:<[A-Za-z:]+>:log-group:/aws/lambda/{auth_function.function_name}:\*$/g"
                }],
            }
        ])

        lambda_authorizer = apigateway_.TokenAuthorizer(self, "ThirdpartyAuthorizer", 
                                                        handler=auth_function, 
                                                        results_cache_ttl=Duration.seconds(0))
        rest_api = RestApi(self, "ThirdParty-MockStack-RestApi",
                                cloud_watch_role=False,
                                deploy=True,
                                deploy_options=apigateway_.StageOptions(
                                    logging_level=apigateway_.MethodLoggingLevel.INFO,
                                    metrics_enabled=True,
                                    access_log_destination=apigateway_.LogGroupLogDestination(log_group),
                                    access_log_format=apigateway_.AccessLogFormat.custom(f"{apigateway_.AccessLogField.context_request_id()} \
                                        {apigateway_.AccessLogField.context_identity_source_ip()} \
                                        {apigateway_.AccessLogField.context_http_method()} \
                                        {apigateway_.AccessLogField.context_error_message()} \
                                        {apigateway_.AccessLogField.context_error_message_string()}")
                                ),
                                default_method_options={"authorizer": lambda_authorizer, "authorization_type": apigateway_.AuthorizationType.CUSTOM},
                            )
        req_validator = rest_api.add_request_validator("MockRequestValidator", validate_request_parameters=True, validate_request_body=True)
        validate_payment_model = apigateway_.Model(self, id="ValidatePaymentModel",
                         rest_api=rest_api,
                         content_type="application/json",
                         model_name="ValidatePaymentModel",
                         schema=apigateway_.JsonSchema(
                            schema=apigateway_.JsonSchemaVersion.DRAFT4,
                            type=apigateway_.JsonSchemaType.OBJECT,
                            properties={
                                "APPID": apigateway_.JsonSchema(type=apigateway_.JsonSchemaType.STRING),
                                "APPTOKEN": apigateway_.JsonSchema(type=apigateway_.JsonSchemaType.STRING)
                            },
                        ))
        method = rest_api.root.add_resource("validate_payment").add_method("POST", MockIntegration(
            # This is the response that we send back to the front end method_response.
            # This is used to modify the response from request_templates
            integration_responses=[IntegrationResponse(
                status_code="200",
                response_templates={
                    "application/json":
                        """
                        #if( $input.params('is_valid') == true )
                          {"valid": true}
                        #else
                          {"valid": false}
                        #end
                        """
                }
            )],
            passthrough_behavior=PassthroughBehavior.NEVER,
            # This is the response from the api-gateway backend - only for Mock
            request_templates={
                "application/json": "{\"statusCode\":200}"
            },
        ),
            # This is the response that is sent back to the REST client.
            # The integration_response.response_templates is returned if not reponse_models is available
            method_responses=[MethodResponse(status_code="200")],
            request_models={"application/json": validate_payment_model},
            request_validator=req_validator,
        )
        CfnOutput(self, "Payment Gateway URL", export_name="validate-payment-gateway-url",
                  value=f"https://{rest_api.rest_api_id}.execute-api.{Aws.REGION}.amazonaws.com/prod/validate_payment"
                  )
        create_order_model = apigateway_.Model(self, id="CreateOrderModel",
                         rest_api=rest_api,
                         content_type="application/json",
                         model_name="CreateOrderModel",
                         schema=apigateway_.JsonSchema(
                            schema=apigateway_.JsonSchemaVersion.DRAFT4,
                            type=apigateway_.JsonSchemaType.OBJECT,
                            properties={
                                "APPID": apigateway_.JsonSchema(type=apigateway_.JsonSchemaType.STRING),
                                "APPTOKEN": apigateway_.JsonSchema(type=apigateway_.JsonSchemaType.STRING),
                                "shipping": apigateway_.JsonSchema(type=apigateway_.JsonSchemaType.OBJECT,
                                    properties={
                                        "name": apigateway_.JsonSchema(type=apigateway_.JsonSchemaType.STRING),
                                        "address": apigateway_.JsonSchema(type=apigateway_.JsonSchemaType.STRING)
                                    },
                                    required=["name", "address"]
                                )
                            },
                            required=["shipping"]
                        ))
        rest_api.root.add_resource("create_order").add_method("POST", MockIntegration(
            # This is the response that we send back to the front end method_response.
            # This is used to modify the response from request_templates
            integration_responses=[IntegrationResponse(
                status_code="200",
                response_templates={
                    "application/json":
                        """
                        #if( $input.params('place_order') == true )
                          {"order_placed": true,"order_id":"$context.requestTimeEpoch"}
                        #else
                          {"order_placed": false}
                        #end
                        """
                }
            )],
            passthrough_behavior=PassthroughBehavior.NEVER,
            # This is the response from the api-gateway backend - only for Mock
            request_templates={
                "application/json": "{\"statusCode\":200}"
            }
        ),
            # This is the response that is sent back to the REST client.
            # The integration_response.response_templates is returned if not reponse_models is available
            method_responses=[MethodResponse(status_code="200")],
            request_models={"application/json": create_order_model},
            request_validator=req_validator,
        )
        CfnOutput(self, "Create Order URL", export_name="create-order-gateway-url",
                  value=f"https://{rest_api.rest_api_id}.execute-api.{Aws.REGION}.amazonaws.com/prod/create_order"
                  )
        create_pre_order_model = apigateway_.Model(self, id="CreatePreOrderModel",
                         rest_api=rest_api,
                         content_type="application/json",
                         model_name="CreatePreOrderModel",
                         schema=apigateway_.JsonSchema(
                            schema=apigateway_.JsonSchemaVersion.DRAFT4,
                            type=apigateway_.JsonSchemaType.OBJECT,
                            properties={
                                "cart_id": apigateway_.JsonSchema(type=apigateway_.JsonSchemaType.STRING),
                            },
                            required=["cart_id"]
                        ))
        rest_api.root.add_resource("pre_order").add_method("POST", MockIntegration(
            # This is the response that we send back to the front end method_response.
            # This is used to modify the response from request_templates
            integration_responses=[IntegrationResponse(
                status_code="200",
                response_templates={
                    "application/json":
                        """
                        {"pre_order_state": "INVENTORY LOCKED"}
                        """
                }
            )],
            passthrough_behavior=PassthroughBehavior.NEVER,
            # This is the response from the api-gateway backend - only for Mock
            request_templates={
                "application/json": "{\"statusCode\":200}"
            }
        ),
            # This is the response that is sent back to the REST client.
            # The integration_response.response_templates is returned if not reponse_models is available
            method_responses=[MethodResponse(status_code="200")],
            request_models={"application/json": create_pre_order_model},
            request_validator=req_validator,
        )
        CfnOutput(self, "Pre-Order Gateway URL", export_name="pre-order-gateway-url",
                  value=f"https://{rest_api.rest_api_id}.execute-api.{Aws.REGION}.amazonaws.com/prod/pre_order"
                  )
        store_product_table = dynamodb_.Table(self, "StoreProduct",
                                              partition_key=dynamodb_.Attribute(name="product_id",
                                                                                type=dynamodb_.AttributeType.STRING),
                                              sort_key=dynamodb_.Attribute(name="store_id",
                                                                           type=dynamodb_.AttributeType.STRING),
                                              removal_policy=RemovalPolicy.DESTROY,
                                              point_in_time_recovery=True)
        CfnOutput(self, "Store Product Table", export_name="store-product-table-arn",
                  value=store_product_table.table_arn
                  )
