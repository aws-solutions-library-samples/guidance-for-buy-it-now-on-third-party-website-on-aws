from aws_cdk.aws_apigateway import IntegrationResponse, MethodResponse, IntegrationResponse, MethodResponse
from aws_cdk import App, CfnOutput, NestedStack, NestedStackProps, Stack, Aws
from constructs import Construct
from aws_cdk.aws_apigateway import Deployment, Method, MockIntegration, PassthroughBehavior, RestApi, Stage
from aws_cdk import (
    RemovalPolicy,
    aws_apigateway as apigw,
    aws_dynamodb as dynamodb_,
)
import json


class MockStack(Stack):
    def __init__(self, scope):
        super().__init__(scope, "Thirdparty-MockStack")

        rest_api = RestApi(self, "ThirdParty-MockStack-RestApi",
                           cloud_watch_role=True,
                           deploy=True
                           )
        rest_api.root.add_method("ANY")
        # api = RestApi.from_rest_api_attributes(self, "RestApi",
        #    rest_api_id=rest_api.rest_api_id,
        #    root_resource_id=rest_api.rest_api_root_resource_id
        # )
        method = rest_api.root.add_resource("validate_payment").add_method("POST", MockIntegration(
            # This is the response that we send back to the front end method_response.
            # This is used to modify the response from request_temnplates
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
            }
        ),
            # This is the response that is sent back to the REST client.
            # The integration_response.response_templates is returned if not reponse_models is available
            method_responses=[MethodResponse(status_code="200")],
            # request_parameters={
            #    "method.request.querystring.APPID": False
            # }
        )
        CfnOutput(self, "Payment Gateway URL", export_name="validate-payment-gateway-url",
                  value=f"https://{rest_api.rest_api_id}.execute-api.{Aws.REGION}.amazonaws.com/prod/validate_payment"
                  )
        rest_api.root.add_resource("create_order").add_method("POST", MockIntegration(
            # This is the response that we send back to the front end method_response.
            # This is used to modify the response from request_temnplates
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
            # request_parameters={
            #    "method.request.querystring.APPID": False
            # }
        )
        CfnOutput(self, "Create Order URL", export_name="create-order-gateway-url",
                  value=f"https://{rest_api.rest_api_id}.execute-api.{Aws.REGION}.amazonaws.com/prod/create_order"
                  )
        rest_api.root.add_resource("pre_order").add_method("POST", MockIntegration(
            # This is the response that we send back to the front end method_response.
            # This is used to modify the response from request_temnplates
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
            # request_parameters={
            #    "method.request.querystring.APPID": False
            # }
        )
        CfnOutput(self, "Pre-Order Gateway URL", export_name="pre-order-gateway-url",
                  value=f"https://{rest_api.rest_api_id}.execute-api.{Aws.REGION}.amazonaws.com/prod/pre_order"
                  )
        store_product_table = dynamodb_.Table(self, "StoreProduct",
                                              partition_key=dynamodb_.Attribute(name="product_id",
                                                                                type=dynamodb_.AttributeType.STRING),
                                              sort_key=dynamodb_.Attribute(name="store_id",
                                                                           type=dynamodb_.AttributeType.STRING),
                                              removal_policy=RemovalPolicy.DESTROY)
        CfnOutput(self, "Store Product Table", export_name="store-product-table-arn",
                  value=store_product_table.table_arn
                  )
        # CfnOutput(self, "TEST VALUE", export_name="test-value",
        #          value="my test value"
        #          )
