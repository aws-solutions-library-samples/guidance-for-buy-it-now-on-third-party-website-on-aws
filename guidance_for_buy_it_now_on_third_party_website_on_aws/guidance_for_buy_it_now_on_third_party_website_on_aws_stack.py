from constructs import Construct
from aws_cdk import (
    Duration,
    Aws,
    Stack,
    CfnOutput,
    RemovalPolicy,
    aws_dynamodb as dynamodb_,
    aws_lambda as lambda_,
    aws_apigateway as apigateway_,
    aws_iam as iam,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_logs as logs,
    aws_ses as ses,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions,
    Duration,
    aws_kms as kms,
    aws_iam as iam,
    #aws_lambda_python_alpha as aws_lambda_python_,
)
import aws_cdk as cdk
import json

class GuidanceForBuyItNowOnThirdPartyWebsiteOnAwsStack(Stack):

    product_url = None
    cart_url = None
    store_url = None
    store_product_url = None
    order_manager_url = None
    store_product_table = None
    api = None
    request_validator = None
    buyitnow_table = None

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        lambdaLayers = lambda_.LayerVersion(self, 'requests-powertools-layer',
                                            code=lambda_.AssetCode(
                                                'lambda/layers/requests-powertools/'),
                                            compatible_runtimes=[lambda_.Runtime.PYTHON_3_9])

        # Lambda auth function
        auth_function = lambda_.Function(self, "BuyitNowAuthTokenLambda",
                                          code=lambda_.Code.from_asset(
                                              './lambda/code/utils'),
                                          handler="api_gateway_authorizer.handler",
                                          runtime=lambda_.Runtime.NODEJS_18_X)
        lambda_authorizer = apigateway_.TokenAuthorizer(self, 
                                                        "BuyitNowAuthorizer", 
                                                        handler=auth_function, 
                                                        results_cache_ttl=Duration.seconds(0))

        log_group = logs.LogGroup(self, "BuyitNow-ApiGatewayAccessLogs")
        self.api = apigateway_.RestApi(
            self, "buy-it-now", cloud_watch_role=True, deploy=True,
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
            default_method_options={"authorizer": lambda_authorizer, "authorization_type": apigateway_.AuthorizationType.CUSTOM}
        )
        self.request_validator = self.api.add_request_validator("BuyitNowRequestValidator", validate_request_parameters=True, validate_request_body=True)
        self.url = self.api.url
        self.buyitnow_table = dynamodb_.Table(self, "buyitnow",
                                              partition_key=dynamodb_.Attribute(name="PK",
                                                                                type=dynamodb_.AttributeType.STRING),
                                              sort_key=dynamodb_.Attribute(name="SK",
                                                                           type=dynamodb_.AttributeType.STRING),
                                              removal_policy=RemovalPolicy.DESTROY,
                                              point_in_time_recovery=True)

        self.setProduct()
        self.setShoppingCart(lambdaLayers=lambdaLayers)
        self.setStores()
        self.setStoreProduct(lambdaLayers=lambdaLayers)
        self.setOrderManager(lambdaLayers=lambdaLayers)

        CfnOutput(self, "Products Management URL", value=self.product_url, export_name="buy-it-now-products-management-url")
        CfnOutput(self, "Cart Management URL", value=self.cart_url, export_name="buy-it-now-cart-management-url")
        CfnOutput(self, "Store Management URL", value=self.store_url, export_name="buy-it-now-store-management-url")
        CfnOutput(self, "Store Product Management URL",
                  value=self.store_product_url, export_name="buy-it-now-store-product-management-url")
        CfnOutput(self, "Order Management URL", value=self.order_manager_url, export_name="buy-it-now-order-management-url")

    def setProduct(self):
        # Create Lambda Function to add/list/get products
        product_lambda = lambda_.Function(self, "ProductLambda",
                                          code=lambda_.Code.from_asset(
                                              './lambda/code'),
                                          handler="product_lambda.productHandler",
                                          runtime=lambda_.Runtime.PYTHON_3_9)
        # Create an environmental variable to pass the table name
        product_lambda.add_environment(
            'BUYITNOW_TABLE', self.buyitnow_table.table_name)
        self.buyitnow_table.grant_read_write_data(product_lambda)

        api_products = self.api.root.add_resource("products")
        api_products.add_method(
            "GET", apigateway_.LambdaIntegration(product_lambda),
            request_validator=self.request_validator,
        )
        # Example POST: https://acsgrblbqf.execute-api.us-east-1.amazonaws.com/prod/products/
        # {
        #   "id":"101",
        #   "name":"Product 1",
        #   "price": "99.99"
        # }
        api_products.add_method(
            "POST", apigateway_.LambdaIntegration(product_lambda),
            request_validator=self.request_validator,
        )
        api_product = api_products.add_resource("{product}")
        # Method to get a specific product based on product id
        # Example GET: https://acsgrblbqf.execute-api.us-east-1.amazonaws.com/prod/products/101
        api_product.add_method("GET", apigateway_.LambdaIntegration(
            product_lambda),
            request_validator=self.request_validator,
        )  # GET /products/{product}
        # Do no use self.api.url to get the url because it causes circular dependencies
        self.product_url = f"https://{self.api.rest_api_id}.execute-api.{Aws.REGION}.amazonaws.com/prod/products"

    def setShoppingCart(self, lambdaLayers):
        shopping_cart_lambda = lambda_.Function(self, "ShoppingCartLambda",
                                                code=lambda_.Code.from_asset(
                                                    "./lambda/code"),
                                                handler="cart_lambda.cartHandler",
                                                layers=[lambdaLayers],
                                                runtime=lambda_.Runtime.PYTHON_3_9)
        # Use PythonFunction if you dont want to manage lambda layers
        # - You will need Docker to use PythonFunction.
        # - PythonFunction is experimental (03/2023)
        #shopping_cart_lambda = aws_lambda_python_.PythonFunction(self, "ShoppingCartLambda",
        #                                  entry="./lambda/code",
        #                                  handler="cartHandler",
        #                                  index="cart_lambda.py",
        #                                  runtime=lambda_.Runtime.PYTHON_3_9)

        shopping_cart_lambda.add_environment(
            "GET_PRODUCT_URL", self.product_url)
        shopping_cart_lambda.add_environment(
            'BUYITNOW_TABLE', self.buyitnow_table.table_name)
        self.buyitnow_table.grant_read_write_data(shopping_cart_lambda)

        api_carts = self.api.root.add_resource("carts")
        api_carts.add_method(
            "GET", apigateway_.LambdaIntegration(shopping_cart_lambda),
            request_validator=self.request_validator,
        )
        # Example POST: https://acsgrblbqf.execute-api.us-east-1.amazonaws.com/prod/carts/
        # {
        #   "partial_cart_id": "0001",
        #   "product_id":"101",
        #   "quantity":"1"
        # }
        api_carts.add_method(
            "POST", apigateway_.LambdaIntegration(shopping_cart_lambda),
            request_validator=self.request_validator,
        )
        api_cart = api_carts.add_resource("{cart_id}")
        # Method to get a specific cart based on cart id
        # Example GET: https://acsgrblbqf.execute-api.us-east-1.amazonaws.com/prod/carts/user_id%23guest-cart_id%230001
        api_cart.add_method(
            "GET", apigateway_.LambdaIntegration(shopping_cart_lambda),
            request_validator=self.request_validator,
        )
        api_cart_product = api_cart.add_resource("{product_id}")
        api_cart_product.add_method(
            "GET", apigateway_.LambdaIntegration(shopping_cart_lambda),
            request_validator=self.request_validator,
        )
        self.cart_url = f"https://{self.api.rest_api_id}.execute-api.{Aws.REGION}.amazonaws.com/prod/carts"

    def setStores(self):
        # Create Lambda Function to add/list/get customers
        stores_lambda = lambda_.Function(self, "StoresLambda",
                                         code=lambda_.Code.from_asset(
                                             './lambda/code'),
                                         handler="stores_lambda.storesHandler",
                                         runtime=lambda_.Runtime.PYTHON_3_9)

        stores_lambda.add_environment(
            'BUYITNOW_TABLE', self.buyitnow_table.table_name)
        self.buyitnow_table.grant_read_write_data(stores_lambda)

        api_stores = self.api.root.add_resource("stores")
        api_stores.add_method(
            "GET", apigateway_.LambdaIntegration(stores_lambda),
            request_validator=self.request_validator,
        )
        # Example POST: https://3ir7i48vu4.execute-api.us-east-1.amazonaws.com/prod/stores
        # {
        #   "id":"2001",
        #   "name":"Walmart",
        #   "address": "1600 Pennsylvania Avenue, DC",
        # }
        api_stores.add_method(
            "POST", apigateway_.LambdaIntegration(stores_lambda),
            request_validator=self.request_validator,
        )
        api_product = api_stores.add_resource("{store}")
        # Example GET: https://3ir7i48vu4.execute-api.us-east-1.amazonaws.com/prod/stores/2001
        api_product.add_method(
            "GET", apigateway_.LambdaIntegration(stores_lambda),
            request_validator=self.request_validator,
        )
        # Do no use self.api.url to get the url because it causes circular dependencies
        self.store_url = f"https://{self.api.rest_api_id}.execute-api.{Aws.REGION}.amazonaws.com/prod/stores"

    def setStoreProduct(self, lambdaLayers):
        # Get the DynamoDB table arn created using the Thirdparty-MockStack stack
        store_product_table_arn = cdk.Fn.import_value("store-product-table-arn")
        store_product_table = dynamodb_.Table.from_table_arn(
            self, "StoreProductTable", table_arn=store_product_table_arn)

        # Create Lambda Function to add/list/get products
        store_products_lambda = lambda_.Function(self, "StoreProductLambda",
                                                 code=lambda_.Code.from_asset(
                                                     './lambda/code'),
                                                 handler="store_products_lambda.storeProductHandler",
                                                 layers=[lambdaLayers],
                                                 timeout=Duration.seconds(300),
                                                 runtime=lambda_.Runtime.PYTHON_3_9)

        # Create an environmental variable to pass the product table name
        store_products_lambda.add_environment(
            'STORE_PRODUCT_TABLE', store_product_table.table_name)
        self.store_product_table = store_product_table
        store_products_lambda.add_environment("GET_CART_URL", self.cart_url)
        store_products_lambda.add_environment("GET_STORES_URL", self.store_url)

        # Give Read and Write access to the table for Lambda function
        store_product_table.grant_read_write_data(store_products_lambda)

        api_store_products = self.api.root.add_resource("store_products")
        api_store_products.add_method(
            "GET", apigateway_.LambdaIntegration(store_products_lambda),
            request_validator=self.request_validator,
        )
        # Example POST: https://acsgrblbqf.execute-api.us-east-1.amazonaws.com/prod/store_products/
        # {
        #   "store_id":"1001",
        #   "product_id":"101",
        #   "product_name":"Product 1",
        #   "price": "99.99"
        # }
        api_store_products.add_method(
            "POST", apigateway_.LambdaIntegration(store_products_lambda),
            request_validator=self.request_validator,
        )
        api_product = api_store_products.add_resource("{product_id}")
        # Example GET: https://acsgrblbqf.execute-api.us-east-1.amazonaws.com/prod/store_products/1001
        api_product.add_method("GET", apigateway_.LambdaIntegration(
            store_products_lambda),
            request_validator=self.request_validator,
        )  # GET /store_products/{product_id}
        api_store_product = api_product.add_resource("{store_id}")
        # Example GET: https://acsgrblbqf.execute-api.us-east-1.amazonaws.com/prod/store_products/1001/101
        api_store_product.add_method("GET", apigateway_.LambdaIntegration(
            store_products_lambda),
            request_validator=self.request_validator,
        )  # GET /store_products/{product_id}/{store_id}
        self.store_product_url = f"https://{self.api.rest_api_id}.execute-api.{Aws.REGION}.amazonaws.com/prod/store_products"

    def setOrderManager(self, lambdaLayers):
        order_manager_lambda = lambda_.Function(self, "OrderManagerLambda",
                                                code=lambda_.Code.from_asset(
                                                    './lambda/code'),
                                                handler="order_manager_lambda.orderManagerHandler",
                                                layers=[lambdaLayers],
                                                runtime=lambda_.Runtime.PYTHON_3_9)
        order_manager_lambda.add_environment(
            'BUYITNOW_TABLE', self.buyitnow_table.table_name)
        self.buyitnow_table.grant_read_write_data(order_manager_lambda)
        validate_payment_gateway_url = cdk.Fn.import_value(
            "validate-payment-gateway-url")
        create_order_gateway_url = cdk.Fn.import_value(
            "create-order-gateway-url")
        pre_order_gateway_url = cdk.Fn.import_value("pre-order-gateway-url")
        verified_identity = self.node.try_get_context("verified_identity")

        sns_key_alias = kms.Alias.from_alias_name(self, "aws_sns_key", "alias/aws/sns")
        my_topic_name = "BuyitNowOrder"
        my_topic = sns.Topic(self, my_topic_name, master_key=sns_key_alias)
        topic_policy = sns.TopicPolicy(self, "TopicPolicy",
            topics=[my_topic]
        )
        topic_policy.document.add_statements(
            iam.PolicyStatement(
                sid="AllowPublishThroughSSLOnly",
                actions=["sns:Publish"],
                effect=iam.Effect.DENY,
                principals=[iam.AnyPrincipal()],
                resources=[my_topic.topic_arn],
                conditions={"Bool":{"aws:SecureTransport": "false"}}
            )
        )
        if verified_identity:
            my_topic.add_subscription(
                subscriptions.EmailSubscription(verified_identity))
        order_manager_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=['sns:Publish', 'sns:ListTopics'],
                effect=iam.Effect.ALLOW,
                resources=['*']
            )
        )

        if (validate_payment_gateway_url):
            order_manager_lambda.add_environment(
                'PAYMENT_GATEWAY', validate_payment_gateway_url)
        if (create_order_gateway_url):
            order_manager_lambda.add_environment(
                'ORDER_GATEWAY', create_order_gateway_url)
        if (pre_order_gateway_url):
            order_manager_lambda.add_environment(
                'PRE_ORDER_GATEWAY', pre_order_gateway_url)
        #order_manager_lambda.add_to_role_policy(
        #    iam.PolicyStatement(
        #        actions=['ses:SendEmail', 'SES:SendRawEmail',
        #                 'ses:SendTemplatedEmail'],
        #        effect=iam.Effect.ALLOW,
        #        resources=['*']
        #    )
        #)
        order_manager_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=['secretsmanager:GetRandomPassword',
                         'secretsmanager:GetSecretValue',
                         'secretsmanager:CreateSecret',
                         'secretsmanager:DescribeSecret',
                         'secretsmanager:GetSecretValue',
                         'secretsmanager:PutSecretValue',
                         'secretsmanager:UpdateSecret'],
                effect=iam.Effect.ALLOW,
                resources=['*']
            )
        )

        capture_order_start = tasks.LambdaInvoke(self, "Capture Order Details",
                                                 lambda_function=order_manager_lambda,
                                                 # Lambda's result is in the attribute `Payload`
                                                 output_path="$.Payload",
                                                 payload=sfn.TaskInput.from_object({
                                                     "body.$": "$.body",
                                                     "header.$": "$.header",
                                                     "step": "start"
                                                 })
                                                 )

        payment_validation = tasks.LambdaInvoke(self, "Validate Payment",
                                                lambda_function=order_manager_lambda,
                                                # Lambda's result is in the attribute `Payload`
                                                output_path="$.Payload",
                                                payload=sfn.TaskInput.from_object({
                                                    "body.$": "$.body",
                                                    "header.$": "$.header",
                                                    "step": "validate"
                                                })
                                                )
        add_customer = tasks.LambdaInvoke(self, "Add Customer",
                                          lambda_function=order_manager_lambda,
                                          # Lambda's result is in the attribute `Payload`
                                          output_path="$.Payload",
                                          payload=sfn.TaskInput.from_object({
                                              "body.$": "$.body",
                                              "header.$": "$.header",
                                              "step": "add_customer"
                                          })
                                          )
        create_order = tasks.LambdaInvoke(self, "Create Order",
                                          lambda_function=order_manager_lambda,
                                          # Lambda's result is in the attribute `Payload`
                                          output_path="$.Payload",
                                          payload=sfn.TaskInput.from_object({
                                              "body.$": "$.body",
                                              "header.$": "$.header",
                                              "step": "create_order",
                                              "customer_id.$": "$.customer_id"
                                          })
                                          )
        capture_3p_order = tasks.LambdaInvoke(self, "Capture 3P Order",
                                              lambda_function=order_manager_lambda,
                                              # Lambda's result is in the attribute `Payload`
                                              output_path="$.Payload",
                                              payload=sfn.TaskInput.from_object({
                                                  "body.$": "$.body",
                                                  "header.$": "$.header",
                                                  "step": "capture_order",
                                                  "order_id.$": "$.order_id",
                                                  "customer_id.$": "$.customer_id"
                                              })
                                              )
        order_failed = sfn.Fail(
            self, "Fail",
            cause='Order Failed',
            error='Order Job returned FAILED'
        )
        order_succeeded = sfn.Succeed(
            self, "Succeeded",
            comment='Order succeeded'
        )

        publish_message = tasks.SnsPublish(self, "Publish message",
                                           topic=my_topic,
                                           message=sfn.TaskInput.from_json_path_at(
                                               "$.message"),
                                           subject=sfn.JsonPath.string_at(
                                               "$.subject"),
                                           result_path=sfn.JsonPath.DISCARD
                                           )

        order_failure = tasks.LambdaInvoke(self, "Order Exception Handler",
                                           lambda_function=order_manager_lambda,
                                           output_path="$.Payload",
                                           payload=sfn.TaskInput.from_object({
                                               "error.$": "$",
                                               "step": "failed"
                                           })
                                           )
        definition = capture_order_start\
            .add_catch(errors=[sfn.Errors.ALL], handler=order_failure, result_path="$.error") \
            .next(payment_validation.add_catch(errors=[sfn.Errors.ALL], handler=order_failure
                                               .add_catch(errors=[sfn.Errors.ALL], handler=order_failed, result_path="$.error")
                                               .next(publish_message), result_path="$.error")
                  .next(sfn.Choice(self, 'Is Payment Valid?')
                        .when(sfn.Condition.string_equals('$.payment_valid', 'FAILED'), order_failure)
                        .when(sfn.Condition.string_equals('$.payment_valid', 'SUCCEEDED'), add_customer
                              .add_catch(errors=[sfn.Errors.ALL], handler=order_failure, result_path="$.error")
                              .next(create_order.add_catch(errors=[sfn.Errors.ALL], handler=order_failure, result_path="$.error"))
                              .next(sfn.Choice(self, 'Was Order Created?')
                                    .when(sfn.Condition.string_equals('$.order_placed', 'FAILED'), order_failure)
                                    .when(sfn.Condition.string_equals('$.order_placed', 'SUCCEEDED'), capture_3p_order
                                          .add_catch(errors=[sfn.Errors.ALL], handler=order_failure, result_path="$.error")
                                          .next(publish_message
                                                .add_catch(errors=[sfn.Errors.ALL], handler=order_failed, result_path="$.error"))
                                          .next(sfn.Choice(self, 'Order Success?')
                                                .when(sfn.Condition.string_equals('$.order_status', 'FAILED'), order_failed)
                                                .when(sfn.Condition.string_equals('$.order_status', 'SUCCEEDED'), order_succeeded)
                                                )
                                          )
                                    )
                              )
                        )
                  )

        log_group = logs.LogGroup(self, "OrderManagerStepFunctionLogGroup")

        sm = sfn.StateMachine(
            self, "OrderManager",
            definition=definition,
            timeout=Duration.minutes(5),
            logs=sfn.LogOptions(
                destination=log_group,
                level=sfn.LogLevel.ALL
            ),
            state_machine_type=sfn.StateMachineType.EXPRESS,
            tracing_enabled=True
        )

        sm.add_to_role_policy(
            iam.PolicyStatement(
                actions=["logs:CreateLogDelivery",
                         "logs:GetLogDelivery",
                         "logs:UpdateLogDelivery",
                         "logs:DeleteLogDelivery",
                         "logs:ListLogDeliveries",
                         "logs:PutLogEvents",
                         "logs:PutResourcePolicy",
                         "logs:DescribeResourcePolicies",
                         "logs:DescribeLogGroups"],
                effect=iam.Effect.ALLOW,
                resources=['*']
            )
        )

        api_order_manager = self.api.root.add_resource("order_manager")
        # Example POST: https://3ir7i48vu4.execute-api.us-east-1.amazonaws.com/prod/order_manager
        # {
        #   "cart_id": "user_id#guest-cart_id#0001",
        #   "store_id": "2001",
        #   "customer": {
        #     "name":"John Doe",
        #     "email":"john@doe.com",
        #     "address": "1600 Pennsylvania Avenue, DC"
        #   },
        #   "payment": {
        #     "app_id": "APPID",
        #     "app_token": "APPTOKEN"
        #   },
        #   "shipping": {
        #     "name":"John Doe 1",
        #     "address": "1600 Pennsylvania Avenue, DC"
        #   },
        #   "loyalty_id": "1234567890"
        # }
        api_order_manager.add_method("ANY", apigateway_.StepFunctionsIntegration.start_execution(
            state_machine=sm, headers=True, authorizer=True),
            request_validator=self.request_validator,
        )
        self.order_manager_url = f"https://{self.api.rest_api_id}.execute-api.{Aws.REGION}.amazonaws.com/prod/order_manager"