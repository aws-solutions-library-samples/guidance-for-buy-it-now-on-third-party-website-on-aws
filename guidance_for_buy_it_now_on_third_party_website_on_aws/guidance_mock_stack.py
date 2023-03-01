from aws_cdk.aws_apigateway import IntegrationResponse, MethodResponse, IntegrationResponse, MethodResponse
from aws_cdk import App, CfnOutput, NestedStack, NestedStackProps, Stack, Aws
from constructs import Construct
from aws_cdk.aws_apigateway import Deployment, Method, MockIntegration, PassthroughBehavior, RestApi, Stage
from aws_cdk import aws_apigateway as apigw
import json

class RootStack(Stack):
    def __init__(self, scope):
        super().__init__(scope, "mock-api-RootStack")

        rest_api = RestApi(self, "RestApi",
            cloud_watch_role=True,
            deploy=True
        )
        rest_api.root.add_method("ANY")
        #api = RestApi.from_rest_api_attributes(self, "RestApi",
        #    rest_api_id=rest_api.rest_api_id,
        #    root_resource_id=rest_api.rest_api_root_resource_id
        #)
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
            #request_parameters={
            #    "method.request.querystring.APPID": False
            #}
        )
        CfnOutput(self, "Payment Gateway URL",
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
            #request_parameters={
            #    "method.request.querystring.APPID": False
            #}
        )
        CfnOutput(self, "Create Order URL",
            value=f"https://{rest_api.rest_api_id}.execute-api.{Aws.REGION}.amazonaws.com/prod/create_order"
        )

        #CfnOutput(self, "BooksURL",
        #    value=f"https://{rest_api.rest_api_id}.execute-api.{Aws.REGION}.amazonaws.com/prod/books"
        #)

    #def create_mock_stack(self, rest_api_id=None, root_resource_id=None):
    #    api = RestApi.from_rest_api_attributes(self, "RestApi",
    #        rest_api_id=rest_api_id,
    #        root_resource_id=root_resource_id
    #    )
    #    method = api.root.add_resource("validate_payment").add_method("POST", MockIntegration(
    #        # This is the response that we send back to the front end method_response.
    #        # This is used to modify the response from request_temnplates
    #        integration_responses=[IntegrationResponse(
    #            status_code="200",
    #            response_templates={
    #                "application/json": "{\"is_valid\":\"VALID\"}"
    #            }
    #        )],
    #        passthrough_behavior=PassthroughBehavior.NEVER,
    #        # This is the response from the api-gateway backend - only for Mock
    #        request_templates={
    #             "application/json": "{\"statusCode\":200}"
    #        }
    #        ),
    #        # This is the response that is sent back to the REST client.
    #        # The integration_response.response_templates is returned if not reponse_models is available
    #        method_responses=[MethodResponse(status_code="200")]
    #    )

#class PetsStack(NestedStack):
#
#    def __init__(self, scope, *, rest_api_id=None, root_resource_id=None, parameters=None, timeout=None, notificationArns=None, removalPolicy=None, description=None, response_model=None):
#        #super().__init__(scope, "integ-restapi-import-PetsStack", rest_api_id=rest_api_id, root_resource_id=root_resource_id, parameters=parameters, timeout=timeout, notificationArns=notificationArns, removalPolicy=removalPolicy, description=description)
#        super().__init__(scope, "integ-restapi-import-PetsStack")
#
#        self.methods = []
#        api = RestApi.from_rest_api_attributes(self, "RestApi",
#            rest_api_id=rest_api_id,
#            root_resource_id=root_resource_id
#        )
#        #response_model = api.add_model("ResponseModel",
#        #    content_type="application/json",
#        #    model_name="ResponseModel",
#        #    schema=apigw.JsonSchema(
#        #        schema=apigw.JsonSchemaVersion.DRAFT4,
#        #        title="pollResponse",
#        #        type=apigw.JsonSchemaType.OBJECT,
#        #        properties={
#        #            "is_valid": apigw.JsonSchema(type=apigw.JsonSchemaType.STRING),
#        #        }
#        #    )
#        #)
#
#        method = api.root.add_resource("validate_payment").add_method("POST", MockIntegration(
#            # This is the response that we send back to the front end method_response.
#            # This is used to modify the response from request_temnplates
#            integration_responses=[IntegrationResponse(
#                status_code="200",
#                response_templates={
#                    "application/json": "{\"is_valid\":\"VALID\"}"
#                }
#                #response_parameters={
#                #    "application/json": "{\"is_valid\":\"'VALID'\"}"
#                #}
#                #response_parameters={
#                #    "is_valid": "VALID"
#                #},
#            )],
#            #integration_responses=[{
#            #    'statusCode':'200',
#            #    'is_valid':'VALID'
#            #}],
#            passthrough_behavior=PassthroughBehavior.NEVER,
#            # This is the response from the api-gateway backend - only for Mock
#            request_templates={
#                "application/json": "{\"statusCode\":200}"
#            }
#        ),
#            # This is the response that is sent back to the REST client.
#            # The integration_response.response_templates is returned if not reponse_models is available
#            method_responses=[MethodResponse(status_code="200")]
#            #method_responses=[MethodResponse(status_code="200",
#            #    response_models={
#            #        "application/json": "{\"is_valid\":\"VALID\"}"
#            #    }
#            #)]
#            #method_responses=[MethodResponse(status_code="200",
#            #    response_models={
#            #        "application/json": response_model
#            #    }
#            #)]
#        )
#
#        self.methods.append(method)

#class BooksStack(NestedStack):
#
#    def __init__(self, scope, *, rest_api_id=None, root_resource_id=None, parameters=None, timeout=None, notificationArns=None, removalPolicy=None, description=None, response_model=None):
#        #super().__init__(scope, "integ-restapi-import-BooksStack", rest_api_id=rest_api_id, root_resource_id=root_resource_id, parameters=parameters, timeout=timeout, notificationArns=notificationArns, removalPolicy=removalPolicy, description=description)
#        super().__init__(scope, "integ-restapi-import-BooksStack")
#
#        self.methods = []
#        api = RestApi.from_rest_api_attributes(self, "RestApi",
#            rest_api_id=rest_api_id,
#            root_resource_id=root_resource_id
#        )
#
#        #response_model = api.add_model("ResponseModel",
#        #    content_type="application/json",
#        #    model_name="ResponseModel",
#        #    schema=apigw.JsonSchema(
#        #        schema=apigw.JsonSchemaVersion.DRAFT4,
#        #        title="pollResponse",
#        #        type=apigw.JsonSchemaType.OBJECT,
#        #        properties={
#        #            "is_valid": apigw.JsonSchema(type=apigw.JsonSchemaType.STRING),
#        #        }
#        #    )
#        #)
#
#        method = api.root.add_resource("books").add_method("GET", MockIntegration(
#            integration_responses=[IntegrationResponse(
#                status_code="200",
#                response_templates={
#                    "application/json": "{\"is_valid\":\"VALID\"}"
#                }
#                #response_parameters={
#                #    "application/json": "{\"is_valid\":\"'VALID'\"}"
#                #}
#                #response_parameters={
#                #    "is_valid": "VALID"
#                #},
#            )],
#            #integration_responses=[{
#            #    'statusCode':'200',
#            #    'is_valid':'VALID'
#            #}],
#            passthrough_behavior=PassthroughBehavior.NEVER,
#            request_templates={
#                "application/json": "{\"statusCode\":200}"
#            }
#        ),
#            #method_responses=[MethodResponse(status_code="200")]
#            #method_responses=[MethodResponse(status_code="200",
#            #    response_models={
#            #        "application/json": "{\"is_valid\":\"VALID\"}"
#            #    }
#            #)]
#            method_responses=[MethodResponse(status_code="200",
#                response_models={
#                    "application/json": response_model
#                }
#            )]
#        )
#        self.methods.append(method)

#class DeployStack(NestedStack):
#    def __init__(self, scope, *, rest_api_id=None, methods=None, parameters=None, timeout=None, notificationArns=None, removalPolicy=None, description=None):
#        #super().__init__(scope, "integ-restapi-import-DeployStack", rest_api_id=rest_api_id, methods=methods, parameters=parameters, timeout=timeout, notificationArns=notificationArns, removalPolicy=removalPolicy, description=description)
#        super().__init__(scope, "integ-restapi-import-DeployStack")
#
#        deployment = Deployment(self, "Deployment",
#            api=RestApi.from_rest_api_id(self, "RestApi", rest_api_id)
#        )
#        if methods:
#            for method in methods:
#                deployment.node.add_dependency(method)
#        Stage(self, "Stage", deployment=deployment)

#RootStack(App())