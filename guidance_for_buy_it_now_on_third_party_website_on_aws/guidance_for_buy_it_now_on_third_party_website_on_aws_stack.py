from constructs import Construct
from aws_cdk import (
    CfnParameter,
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
    aws_secretsmanager as secretsmanager,
    aws_ses as ses,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions
)
import json


POWERTOOLS_BASE_NAME = 'AWSLambdaPowertools'
# Find latest from github.com/awslabs/aws-lambda-powertools-python/releases
POWERTOOLS_VER = '2.6.0'
POWERTOOLS_ARN = 'arn:aws:serverlessrepo:eu-west-1:057560766410:applications/aws-lambda-powertools-python-layer'

class GuidanceForBuyItNowOnThirdPartyWebsiteOnAwsStack(Stack):

    product_url = None
    #customer_url = None
    cart_url = None
    store_url = None
    store_product_url = None
    order_manager_url = None
    #shopping_cart_table = None
    #stores_table = None
    store_product_table = None
    #orders_table = None
    api = None
    buyitnow_table = None

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        lambdaLayers = lambda_.LayerVersion(self, 'lambda-layer',
                      code = lambda_.AssetCode('lambda/layers/'),
                      compatible_runtimes = [lambda_.Runtime.PYTHON_3_9])
        powertools_layer = lambda_.LayerVersion.from_layer_version_arn(self, id="lambda-powertools",
                        layer_version_arn=f"arn:aws:lambda:us-east-1:017000801446:layer:AWSLambdaPowertoolsPythonV2:18")
        #secrets_manager_layer = lambda_.LayerVersion.from_layer_version_arn(self, id="secrets-layer",
        #                layer_version_arn=f"arn:aws:lambda:us-east-1:177933569100:layer:AWS-Parameters-and-Secrets-Lambda-Extension:4")

        self.api = apigateway_.RestApi(self, "buy-it-now", cloud_watch_role=True, deploy=True)
        self.url = self.api.url
        self.buyitnow_table = dynamodb_.Table(self, "buyitnow",
                        partition_key=dynamodb_.Attribute(name="PK", 
                                        type=dynamodb_.AttributeType.STRING),
                        sort_key=dynamodb_.Attribute(name="SK", 
                                        type=dynamodb_.AttributeType.STRING),
                        removal_policy=RemovalPolicy.DESTROY)

        self.setProduct()
        #self.setCustomer()
        self.setShoppingCart(lambdaLayers=lambdaLayers, powertools_layer=powertools_layer)
        self.setStores()
        self.setStoreProduct(lambdaLayers=lambdaLayers, powertools_layer=powertools_layer)
        #self.setStoreSelector(lambdaLayers=lambdaLayers, powertools_layer=powertools_layer)
        self.setOrderManager(lambdaLayers=lambdaLayers, powertools_layer=powertools_layer)

        CfnOutput(self, "Products Management URL", value=self.product_url)
        #CfnOutput(self, "Customers Management URL", value=self.customer_url)
        CfnOutput(self, "Cart Management URL", value=self.cart_url)
        CfnOutput(self, "Store Management URL", value=self.store_url)
        CfnOutput(self, "Store Product Management URL", value=self.store_product_url)
        CfnOutput(self, "Order Management URL", value=self.order_manager_url)

    def setProduct(self):
        # Create Products Table in DynamoDB
        #product_table = dynamodb_.Table(self, "Products", 
        #        partition_key=dynamodb_.Attribute(name="id", 
        #        type=dynamodb_.AttributeType.STRING),
        #        removal_policy=RemovalPolicy.DESTROY)

        # Create Lambda Function to add/list/get products
        product_lambda = lambda_.Function(self, "ProductLambda",
                code=lambda_.Code.from_asset('./lambda/code'),
                handler="product_lambda.productHandler",
                runtime=lambda_.Runtime.PYTHON_3_9)
        
        # Create an environmental variable to pass the product table name
        #product_lambda.add_environment('PRODUCT_TABLE', product_table.table_name)
        product_lambda.add_environment('BUYITNOW_TABLE', self.buyitnow_table.table_name)
        self.buyitnow_table.grant_read_write_data(product_lambda)

        # Give Read and Write access to the table for Lambda function
        #product_table.grant_read_write_data(product_lambda)

        api_products = self.api.root.add_resource("products")
        api_products.add_method("GET", apigateway_.LambdaIntegration(product_lambda))
        # Example POST: https://acsgrblbqf.execute-api.us-east-1.amazonaws.com/prod/products/
        # {
        #   "id":"101",
        #   "name":"Product 1",
        #   "price": "99.99"
        # }
        api_products.add_method("POST", apigateway_.LambdaIntegration(product_lambda))
        api_product = api_products.add_resource("{product}")
        # Method to get a specific product based on product id
        # Example GET: https://acsgrblbqf.execute-api.us-east-1.amazonaws.com/prod/products/101
        api_product.add_method("GET", apigateway_.LambdaIntegration(product_lambda)) # GET /products/{product}
        # Do no use self.api.url to get the url because it causes circular dependencies
        self.product_url=f"https://{self.api.rest_api_id}.execute-api.{Aws.REGION}.amazonaws.com/prod/products"
        #self.product_url = self.api.url

        # Create API gateway for Lambda function
        #product_gateway = apigateway_.LambdaRestApi(self, "product_api", 
        #        handler=product_lambda, proxy=False)

        ## Create Root REST endpoint to be used for product management
        #products = product_gateway.root.add_resource("products")
        ## Method to list all products in table
        ## Example GET: https://acsgrblbqf.execute-api.us-east-1.amazonaws.com/prod/products/
        #products.add_method("GET") # GET /products
        ## Method to add a product to the table
        ## Example POST: https://acsgrblbqf.execute-api.us-east-1.amazonaws.com/prod/products/
        ## {
        ##   "id":"101",
        ##   "name":"Product 1",
        ##   "price": "99.99"
        ## }
        #products.add_method("POST") # POST /products

        ## Method to add a path parameter
        #product = products.add_resource("{product}")
        ## Method to get a specific product based on product id
        ## Example GET: https://acsgrblbqf.execute-api.us-east-1.amazonaws.com/prod/products/101
        #product.add_method("GET") # GET /products/{product}

        #self.product_url = product_gateway.url

    #def setCustomer(self):
    #    # Create Customer Table
    #    #customer_table = dynamodb_.Table(self, "Customers",
    #    #        partition_key=dynamodb_.Attribute(name="id", 
    #    #        type=dynamodb_.AttributeType.STRING),
    #    #        removal_policy=RemovalPolicy.DESTROY)

    #    # Create Lambda Function to add/list/get customers
    #    customer_lambda = lambda_.Function(self, "CustomersLambda",
    #            code=lambda_.Code.from_asset('./lambda/code'),
    #            handler="customer_lambda.customerHandler",
    #            runtime=lambda_.Runtime.PYTHON_3_9)

    #    #customer_lambda.add_environment('CUSTOMER_TABLE', customer_table.table_name)
    #    customer_lambda.add_environment('BUYITNOW_TABLE', self.buyitnow_table.table_name)
    #    self.buyitnow_table.grant_read_write_data(customer_lambda)
    #    
    #    #customer_table.grant_read_write_data(customer_lambda)

    #    ## Need to add a schema in the API gateway for validation
    #    #customer_schema = {
    #    #    "type": "object",
    #    #    "properties": {
    #    #        "id": {"type": "string"},
    #    #        "name": {"type": "string"},
    #    #        "email": {"type": "string"},
    #    #        "address": {"type": "string"},
    #    #        "payment": {"type": "boolean"},
    #    #        "store_loyalty": {
    #    #            "type": "array", 
    #    #            "items": { 
    #    #                "type": "object", 
    #    #                "properties": {
    #    #                    "store_id": {"type": "string"}, 
    #    #                    "loyalty_id": {"type": "string"}
    #    #                }
    #    #            }
    #    #        },
    #    #    },
    #    #    "required": [ "id", "name", "email", "address" ]
    #    #}
    #    api_customers = self.api.root.add_resource("customers")
    #    api_customers.add_method("GET", apigateway_.LambdaIntegration(customer_lambda))
    #    # Example POST: https://3ir7i48vu4.execute-api.us-east-1.amazonaws.com/prod/customers
    #    # {
    #    #   "id":"1001",
    #    #   "name":"John Doe 1",
    #    #   "email":"john@doe.com",
    #    #   "address": "1600 Pennsylvania Avenue, DC",
    #    #   "payment": true
    #    # }
    #    api_customers.add_method("POST", apigateway_.LambdaIntegration(customer_lambda))
    #    api_customer = api_customers.add_resource("{customer}")
    #    # Example GET: https://3ir7i48vu4.execute-api.us-east-1.amazonaws.com/prod/customers/1001
    #    api_customer.add_method("GET", apigateway_.LambdaIntegration(customer_lambda))
    #    self.customer_url=f"https://{self.api.rest_api_id}.execute-api.{Aws.REGION}.amazonaws.com/prod/customers"
    #    #self.customer_url = f"{self.api.url}customers"

    #    ## Create API gateway for Lambda function
    #    #customer_gateway = apigateway_.LambdaRestApi(self, "customer_api", 
    #    #        handler=customer_lambda, proxy=False)
    #    ### Need to add a schema in the API gateway for validation
    #    ##customer_schema = {
    #    ##    "type": "object",
    #    ##    "properties": {
    #    ##        "id": {"type": "string"},
    #    ##        "name": {"type": "string"},
    #    ##        "email": {"type": "string"},
    #    ##        "address": {"type": "string"},
    #    ##        "payment": {"type": "boolean"},
    #    ##        "store_loyalty": {
    #    ##            "type": "array", 
    #    ##            "items": { 
    #    ##                "type": "object", 
    #    ##                "properties": {
    #    ##                    "store_id": {"type": "string"}, 
    #    ##                    "loyalty_id": {"type": "string"}
    #    ##                }
    #    ##            }
    #    ##        },
    #    ##    },
    #    ##    "required": [ "id", "name", "email", "address" ]
    #    ##}

    #    #customers = customer_gateway.root.add_resource("customers")
    #    ## Example GET: https://3ir7i48vu4.execute-api.us-east-1.amazonaws.com/prod/customers
    #    #customers.add_method("GET")
    #    ## Example POST: https://3ir7i48vu4.execute-api.us-east-1.amazonaws.com/prod/customers
    #    ## {
    #    ##   "id":"1001",
    #    ##   "name":"John Doe 1",
    #    ##   "email":"john@doe.com",
    #    ##   "address": "1600 Pennsylvania Avenue, DC",
    #    ##   "payment": true
    #    ## }
    #    #customers.add_method("POST")

    #    #customer = customers.add_resource("{customer}")
    #    ## Example GET: https://3ir7i48vu4.execute-api.us-east-1.amazonaws.com/prod/customers/1001
    #    #customer.add_method("GET")
    #    ##self.customer_url = f"{customer_gateway.url}customers"

    def setShoppingCart(self, lambdaLayers, powertools_layer):
        #shopping_cart = dynamodb_.Table(self, "ShoppingCart",
        #                partition_key=dynamodb_.Attribute(name="user_id_cart_id", 
        #                                type=dynamodb_.AttributeType.STRING),
        #                sort_key=dynamodb_.Attribute(name="product_id", 
        #                                type=dynamodb_.AttributeType.STRING),
        #                removal_policy=RemovalPolicy.DESTROY)
        
        shopping_cart_lambda = lambda_.Function(self, "ShoppingCartLambda",
                        code=lambda_.Code.from_asset("./lambda/code"),
                        handler="cart_lambda.cartHandler",
                        layers = [lambdaLayers, powertools_layer],
                        runtime=lambda_.Runtime.PYTHON_3_9)
        
        #shopping_cart_lambda.add_environment("CART_TABLE", shopping_cart.table_name)
        shopping_cart_lambda.add_environment("GET_PRODUCT_URL", self.product_url)
        shopping_cart_lambda.add_environment('BUYITNOW_TABLE', self.buyitnow_table.table_name)
        self.buyitnow_table.grant_read_write_data(shopping_cart_lambda)
        #self.shopping_cart_table = shopping_cart
        #shopping_cart.grant_read_write_data(shopping_cart_lambda)

        api_carts = self.api.root.add_resource("carts")
        api_carts.add_method("GET", apigateway_.LambdaIntegration(shopping_cart_lambda))
        api_carts.add_method("POST", apigateway_.LambdaIntegration(shopping_cart_lambda))
        api_cart = api_carts.add_resource("{cart_id}")
        api_cart.add_method("GET", apigateway_.LambdaIntegration(shopping_cart_lambda))
        api_cart_product = api_cart.add_resource("{product_id}")
        api_cart_product.add_method("GET", apigateway_.LambdaIntegration(shopping_cart_lambda))
        self.cart_url=f"https://{self.api.rest_api_id}.execute-api.{Aws.REGION}.amazonaws.com/prod/carts"
        #self.cart_url = self.api.url

        #cart_gateway = apigateway_.LambdaRestApi(self, "cart_api",
        #                handler=shopping_cart_lambda, proxy=False)
        #carts = cart_gateway.root.add_resource("carts")
        #carts.add_method("GET")
        #carts.add_method("POST")

        #cart = carts.add_resource("{cart_id}")
        #cart.add_method("GET")

        ##product = cart.add_resource("product")
        #cart_product = cart.add_resource("{product_id}")
        #cart_product.add_method("GET")

        #self.cart_url = cart_gateway.url

    def setStores(self):
        # Create Stores Table
        #stores_table = dynamodb_.Table(self, "Stores",
        #        partition_key=dynamodb_.Attribute(name="id", 
        #        type=dynamodb_.AttributeType.STRING),
        #        removal_policy=RemovalPolicy.DESTROY)

        # Create Lambda Function to add/list/get customers
        stores_lambda = lambda_.Function(self, "StoresLambda",
                code=lambda_.Code.from_asset('./lambda/code'),
                handler="stores_lambda.storesHandler",
                runtime=lambda_.Runtime.PYTHON_3_9)

        #stores_lambda.add_environment('STORES_TABLE', stores_table.table_name)
        stores_lambda.add_environment('BUYITNOW_TABLE', self.buyitnow_table.table_name)
        self.buyitnow_table.grant_read_write_data(stores_lambda)
        #self.stores_table = stores_table
        
        #stores_table.grant_read_write_data(stores_lambda)

        api_stores = self.api.root.add_resource("stores")
        api_stores.add_method("GET", apigateway_.LambdaIntegration(stores_lambda))
        # Example POST: https://3ir7i48vu4.execute-api.us-east-1.amazonaws.com/prod/stores
        # {
        #   "id":"2001",
        #   "name":"Walmart",
        #   "address": "1600 Pennsylvania Avenue, DC",
        # }
        api_stores.add_method("POST", apigateway_.LambdaIntegration(stores_lambda))
        api_product = api_stores.add_resource("{store}")
        ## Example GET: https://3ir7i48vu4.execute-api.us-east-1.amazonaws.com/prod/stores/2001
        api_product.add_method("GET", apigateway_.LambdaIntegration(stores_lambda))
        # Do no use self.api.url to get the url because it causes circular dependencies
        self.store_url=f"https://{self.api.rest_api_id}.execute-api.{Aws.REGION}.amazonaws.com/prod/stores"

        ## Create API gateway for Lambda function
        #stores_gateway = apigateway_.LambdaRestApi(self, "stores_api", 
        #        handler=stores_lambda, proxy=False)

        #stores = stores_gateway.root.add_resource("stores")
        ## Example GET: https://3ir7i48vu4.execute-api.us-east-1.amazonaws.com/prod/stores
        #stores.add_method("GET")
        ## Example POST: https://3ir7i48vu4.execute-api.us-east-1.amazonaws.com/prod/stores
        ## {
        ##   "id":"2001",
        ##   "name":"Walmart",
        ##   "address": "1600 Pennsylvania Avenue, DC",
        ## }
        #stores.add_method("POST")

        #store = stores.add_resource("{store}")
        ## Example GET: https://3ir7i48vu4.execute-api.us-east-1.amazonaws.com/prod/stores/2001
        #store.add_method("GET")

        #self.store_url = stores_gateway.url

    def setStoreProduct(self, lambdaLayers, powertools_layer):
        store_product_table = dynamodb_.Table(self, "StoreProduct",
                        partition_key=dynamodb_.Attribute(name="product_id", 
                                        type=dynamodb_.AttributeType.STRING),
                        sort_key=dynamodb_.Attribute(name="store_id", 
                                        type=dynamodb_.AttributeType.STRING),
                        removal_policy=RemovalPolicy.DESTROY)
        #store_product_table = dynamodb_.Table(self, "StoreProducts", 
        #        partition_key=dynamodb_.Attribute(name="id", 
        #        type=dynamodb_.AttributeType.STRING))

        # Create Lambda Function to add/list/get products
        store_products_lambda = lambda_.Function(self, "StoreProductLambda",
                code=lambda_.Code.from_asset('./lambda/code'),
                handler="store_products_lambda.storeProductHandler",
                layers = [lambdaLayers, powertools_layer],
                timeout =  Duration.seconds(300),
                runtime=lambda_.Runtime.PYTHON_3_9)
        
        # Create an environmental variable to pass the product table name
        store_products_lambda.add_environment('STORE_PRODUCT_TABLE', store_product_table.table_name)
        self.store_product_table = store_product_table
        store_products_lambda.add_environment("GET_CART_URL", self.cart_url)
        store_products_lambda.add_environment("GET_STORES_URL", self.store_url)

        # Give Read and Write access to the table for Lambda function
        store_product_table.grant_read_write_data(store_products_lambda)

        api_store_products = self.api.root.add_resource("store_products")
        api_store_products.add_method("GET", apigateway_.LambdaIntegration(store_products_lambda))
        # Example POST: https://acsgrblbqf.execute-api.us-east-1.amazonaws.com/prod/store_products/
        # {
        #   "store_id":"1001",
        #   "product_id":"101",
        #   "product_name":"Product 1",
        #   "price": "99.99"
        # }
        api_store_products.add_method("POST", apigateway_.LambdaIntegration(store_products_lambda))
        api_product = api_store_products.add_resource("{product_id}")
        # Example GET: https://acsgrblbqf.execute-api.us-east-1.amazonaws.com/prod/store_products/1001
        api_product.add_method("GET", apigateway_.LambdaIntegration(store_products_lambda)) # GET /store_products/{product_id}
        api_store_product = api_product.add_resource("{store_id}")
        # Example GET: https://acsgrblbqf.execute-api.us-east-1.amazonaws.com/prod/store_products/1001/101
        api_store_product.add_method("GET", apigateway_.LambdaIntegration(store_products_lambda)) # GET /store_products/{product_id}/{store_id}
        self.store_product_url=f"https://{self.api.rest_api_id}.execute-api.{Aws.REGION}.amazonaws.com/prod/store_products"

        # Create API gateway for Lambda function
        #store_product_gateway = apigateway_.LambdaRestApi(self, "store_product_api", 
        #        handler=store_products_lambda, proxy=False)

        ## Create Root REST endpoint to be used for product management
        #store_products = store_product_gateway.root.add_resource("store_products")
        ## Method to list all products in table
        ## Example GET: https://acsgrblbqf.execute-api.us-east-1.amazonaws.com/prod/store_products/
        #store_products.add_method("GET") # GET /store_products
        ## Method to add a product to the table
        ## Example POST: https://acsgrblbqf.execute-api.us-east-1.amazonaws.com/prod/store_products/
        ## {
        ##   "store_id":"1001",
        ##   "product_id":"101",
        ##   "product_name":"Product 1",
        ##   "price": "99.99"
        ## }
        #store_products.add_method("POST") # POST /store_products

        ## Method to add a path parameter
        ##store_product = store_products.add_resource("{store_product}")
        #product = store_products.add_resource("{product_id}")
        #product.add_method("GET") # GET /store_products/{product_id}
        #store_product = product.add_resource("{store_id}")
        ## Method to get a specific store product based on id (<store_id>_<product_id>)
        ## Example GET: https://acsgrblbqf.execute-api.us-east-1.amazonaws.com/prod/store_products/1001_101
        #store_product.add_method("GET") # GET /store_products/{product_id}/{store_id}

        #self.store_product_url = store_product_gateway.url

    # Set the selected Store ID to the cart
    #def setStoreSelector(self, lambdaLayers, powertools_layer):
    #    store_selector_lambda = lambda_.Function(self, "StoreSelectorLambda",
    #            code=lambda_.Code.from_asset('./lambda/code'),
    #            handler="store_selector_lambda.storeSelectorHandler",
    #            layers = [lambdaLayers, powertools_layer],
    #            runtime=lambda_.Runtime.PYTHON_3_9)
    #    store_selector_lambda.add_environment('CART_TABLE', self.shopping_cart_table.table_name)
    #    store_selector_lambda.add_environment('BUYITNOW_TABLE', self.buyitnow_table.table_name)
    #    self.buyitnow_table.grant_read_write_data(store_selector_lambda)
    #    self.shopping_cart_table.grant_read_write_data(store_selector_lambda)

    #    api_store_selector = self.api.root.add_resource("store_selector")
    #    api_store_selector.add_method("POST", apigateway_.LambdaIntegration(store_selector_lambda))

    #    #store_selector_gateway = apigateway_.LambdaRestApi(self, "store_selector_api", 
    #    #        handler=store_selector_lambda, proxy=False)
    #    #store_selector = store_selector_gateway.root.add_resource("store_selector")
    #    #store_selector.add_method("POST")

    # If customer payment attribute is False, show credit card form
    # If customer payment attribute is True, show saved cards details with default card selected
    #def setPaymentConfirmation(self, lambdaLayers, powertools_layer):
    #    orders_table = dynamodb_.Table(self, "Orders",
    #            partition_key=dynamodb_.Attribute(name="order_id", 
    #            type=dynamodb_.AttributeType.STRING))
    #    self.orders_table = orders_table

    #    payment_validation = tasks.EvaluateExpression(self, "Payment Validation",
    #        expression="is_payment_valid(payment)",
    #        result_path="$.payment_valid"
    #    )

    #    create_order_step_function = sfn.StateMachine(self, "CreateOrder",
    #        definition=payment_validation
    #    )
    #    
    #    payment_confirmation_lambda = lambda_.Function(self, "PaymentConfirmationLambda",
    #            code=lambda_.Code.from_asset('./lambda/code'),
    #            handler="payment_confirmation_lambda.paymentConfirmationHandler",
    #            layers = [lambdaLayers, powertools_layer],
    #            runtime=lambda_.Runtime.PYTHON_3_9)
    #    payment_confirmation_lambda.add_environment("CUSTOMER_URL", self.customer_url)
    #    payment_confirmation_lambda.add_environment('ORDERS_TABLE', orders_table.table_name)
    #    orders_table.grant_read_write_data(payment_confirmation_lambda)

    #    #role = iam.Role(self, "Role",
    #    #    assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")
    #    #)       
    #    #create_order_step_function.grant_start_execution(role)
    #    #create_order_step_function.grant_read(role)
    #    #create_order_step_function.grant_start_execution(payment_confirmation_lambda)
    #    #create_order_step_function.grant_read(payment_confirmation_lambda)
    #    create_order_step_function.grant_start_execution(payment_confirmation_lambda.role)
    #    create_order_step_function.grant_read(payment_confirmation_lambda.role)

    #    #payment_confirmation_lambda.addToRolePolicy(iam.PolicyStatement({
    #    #        actions: ['ses:SendEmail', 'SES:SendRawEmail'],
    #    #        resources: ['*'],
    #    #        effect: iam.Effect.ALLOW,
    #    #}));

    #    payment_confirmation_lambda.add_to_role_policy(
    #            iam.PolicyStatement(
    #                    actions=['ses:SendEmail', 'SES:SendRawEmail'],
    #                    effect= iam.Effect.ALLOW,
    #                    resources=['*']
    #            )
    #    )

    #    payment_confirmation_gateway = apigateway_.LambdaRestApi(self, "payment_confirmation_api", 
    #            handler=payment_confirmation_lambda, proxy=False)
    #    payment_confirmation = payment_confirmation_gateway.root.add_resource("payment")
    #    payment_confirmation.add_method("POST")

    # Create a new order table and add the cart details
    # Clear the cart
    #def setCreateOrder(self):
    #    create_order_lambda = lambda_.Function(self, "CreateOrderLambda",
    #            code=lambda_.Code.from_asset('./lambda/code'),
    #            handler="create_order_lambda.createOrderHandler",
    #            runtime=lambda_.Runtime.PYTHON_3_9)

    def setOrderManager(self, lambdaLayers, powertools_layer):
        #orders_table = dynamodb_.Table(self, "Orders",
        #        partition_key=dynamodb_.Attribute(name="order_id", 
        #        type=dynamodb_.AttributeType.STRING),
        #        removal_policy=RemovalPolicy.DESTROY)
        #self.orders_table = orders_table

        #appid_secret = secretsmanager.Secret(self, "APPID")
        #apptoken_secret = secretsmanager.Secret(self, "APPTOKEN")

        #payment_validation = tasks.EvaluateExpression(self, "Payment Validation",
        #    expression="is_payment_valid(payment)",
        #    result_path="$.payment_valid"
        #)

        #create_order_step_function = sfn.StateMachine(self, "CreateOrder",
        #    definition=payment_validation
        #)

        # Create SES Template
        #BODY_HTML = "<html>"
        #"<head></head>"
        #"<body>"
        #"<h1>Order successfully placed</h1>"
        #"<p>"
        #"Order ID: {{order_id}}<br>"
        #"Customer ID: {{customer_id}}<br>"
        #"</p>"
        #"</body>"
        #"</html>"
        #BODY_TEXT = "Order successfully placed \r\n"
        #"Order ID: {{order_id}}\n"
        #"Customer ID: {{customer_id}}\n"

        BODY_HTML = """<html>
        <head></head>
        <body>
        <h1>Order successfully placed</h1>
        <p>
        Order ID: {{order_id}}<br>
        Customer Name: {{customer_name}}<br>
        Customer ID: {{customer_id}}<br>
        </p>
        </body>
        </html>"""
        BODY_TEXT = """Order successfully placed \r\n
                            Order ID: {{order_id}}\n
                            Customer Name: {{customer_name}}\n
                            Customer ID: {{customer_id}}\n"""
        EMAIL_TEMPLATE_NAME = "OrderEmailConfirmation" 

        cfn_template = ses.CfnTemplate(self, "OrderConfirmationEmailTemplate",
            template=ses.CfnTemplate.TemplateProperty(
                subject_part="Greetings, {{customer_name}}!",
                html_part=BODY_HTML,
                template_name=EMAIL_TEMPLATE_NAME,
                text_part=BODY_TEXT
            )
        )

        order_manager_lambda = lambda_.Function(self, "OrderManagerLambda",
                code=lambda_.Code.from_asset('./lambda/code'),
                handler="order_manager_lambda.orderManagerHandler",
                layers = [lambdaLayers, powertools_layer],
                runtime=lambda_.Runtime.PYTHON_3_9)
        #order_manager_lambda.add_environment("CUSTOMER_URL", self.customer_url)
        #order_manager_lambda.add_environment('ORDERS_TABLE', orders_table.table_name)
        order_manager_lambda.add_environment('EMAIL_TEMPLATE_NAME', EMAIL_TEMPLATE_NAME)
        order_manager_lambda.add_environment('BUYITNOW_TABLE', self.buyitnow_table.table_name)
        self.buyitnow_table.grant_read_write_data(order_manager_lambda)
        payment_gateway_url = self.node.try_get_context("payment_gateway")
        order_gateway_url = self.node.try_get_context("order_gateway")
        verified_identity = self.node.try_get_context("verified_identity")

        my_topic = sns.Topic(self, "BuyitNowOrder")
        my_topic.topic_arn
        #email_address = CfnParameter(self, "email-param")
        my_topic.add_subscription(subscriptions.EmailSubscription(verified_identity))
        order_manager_lambda.add_to_role_policy(
                iam.PolicyStatement(
                        actions=['sns:Publish', 'sns:ListTopics'],
                        effect= iam.Effect.ALLOW,
                        resources=['*']
                )
        )

        if(payment_gateway_url):
            order_manager_lambda.add_environment('PAYMENT_GATEWAY', payment_gateway_url)
        if(order_gateway_url):
            order_manager_lambda.add_environment('ORDER_GATEWAY', order_gateway_url)
        if(verified_identity):
            order_manager_lambda.add_environment('VERIFIED_IDENTITY', verified_identity)
        #orders_table.grant_read_write_data(order_manager_lambda)
        order_manager_lambda.add_to_role_policy(
                iam.PolicyStatement(
                        actions=['ses:SendEmail', 'SES:SendRawEmail', 'ses:SendTemplatedEmail'],
                        effect= iam.Effect.ALLOW,
                        resources=['*']
                )
        )
        #order_manager_lambda.add_environment('APPID', appid_secret.secret_name)
        #appid_secret.grant_read(order_manager_lambda.role)
        #appid_secret.grant_write(order_manager_lambda.role)
        #order_manager_lambda.add_environment('APPTOKEN', apptoken_secret.secret_name)
        #apptoken_secret.grant_read(order_manager_lambda.role)
        #apptoken_secret.grant_write(order_manager_lambda.role)
        order_manager_lambda.add_to_role_policy(
                iam.PolicyStatement(
                        actions=['secretsmanager:GetRandomPassword',
                                'secretsmanager:GetSecretValue',
                                'secretsmanager:CreateSecret',
                                'secretsmanager:DescribeSecret',
                                'secretsmanager:GetSecretValue',
                                'secretsmanager:PutSecretValue',
                                'secretsmanager:UpdateSecret'],
                        effect= iam.Effect.ALLOW,
                        resources=['*']
                )
        )
        

        #payment_validation = tasks.LambdaInvoke(self, "Validate Payment",
        #    lambda_function=order_manager_lambda,
        #    # Lambda's result is in the attribute `Payload`
        #    output_path="$.Payload",
        #    payload=sfn.TaskInput.from_object({
        #        "body": sfn.JsonPath.string_at("$"),
        #        "step": "start"
        #    })
        #)
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
        wait_job = sfn.Wait(
            self, "Wait 10 Seconds",
            time=sfn.WaitTime.duration(Duration.seconds(10))
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
        send_email = tasks.LambdaInvoke(self, "Send Email",
            lambda_function=order_manager_lambda,
            # Lambda's result is in the attribute `Payload`
            output_path="$.Payload",
            payload=sfn.TaskInput.from_object({
                "body.$": "$.body",
                "header.$": "$.header",
                "step": "send_email",
                "customer_id.$": "$.customer_id",
                "order_id.$": "$.order_id"
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

        #is_payment_valid_choice = sfn.Choice(self, "Is payment valid?") \
        #        .when(sfn.Condition.string_equals('$.payment_valid', 'FAILED'), order_failed) \
        #        .when(sfn.Condition.string_equals('$.payment_valid', 'SUCCEEDED'), add_customer) \
        #        .otherwise(wait_job)

        #definition = payment_validation\
        #    .next(sfn.Choice(self, 'Is Payment Valid?')
        #          .when(sfn.Condition.string_equals('$.payment_valid', 'FAILED'), order_failed)
        #          .when(sfn.Condition.string_equals('$.payment_valid', 'SUCCEEDED'), add_customer
        #                .next(create_order)\
        #                .next(send_email)\
        #                .next(sfn.Choice(self, 'Order Complete?')
        #                      .when(sfn.Condition.string_equals('$.order_status', 'FAILED'), order_failed)
        #                      .when(sfn.Condition.string_equals('$.order_status', 'SUCCEEDED'), order_succeeded)
        #                )
        #        ))
        #send_failure_notification = sfn.Pass(self, "SendFailureNotification")

        order_failure = tasks.LambdaInvoke(self, "Order Exception Handler",
            lambda_function=order_manager_lambda,
            output_path="$.Payload",
            payload=sfn.TaskInput.from_object({
                #"body.$": "$.body",
                #"header.$": "$.header",
                "error.$": "$.error.Cause",
                "step": "failed"
            })
        )
        definition = capture_order_start \
            .next(payment_validation.add_catch(errors=[sfn.Errors.ALL], handler=order_failure
                    .next(order_failed), result_path="$.error") \
                .next(sfn.Choice(self, 'Is Payment Valid?')
                    .when(sfn.Condition.string_equals('$.payment_valid', 'FAILED'), order_failed)
                    .when(sfn.Condition.string_equals('$.payment_valid', 'SUCCEEDED'), add_customer
                        .next(create_order.add_catch(errors=[sfn.Errors.ALL], handler=order_failure, result_path="$.error"))\
                        .next(sfn.Choice(self, 'Was Order Created?')
                            .when(sfn.Condition.string_equals('$.order_placed', 'FAILED'), order_failed)
                            .when(sfn.Condition.string_equals('$.order_placed', 'SUCCEEDED'), capture_3p_order
                                .next(send_email)
                                .next(sfn.Choice(self, 'Confirmation Email Sent?')
                                    .when(sfn.Condition.string_equals('$.order_status', 'FAILED'), order_failed)
                                    .when(sfn.Condition.string_equals('$.order_status', 'SUCCEEDED'), order_succeeded)
                                )
                            )
                        )
                    )
                )
            )
        

            #.next(add_customer)\
            #.next(send_order)\
            #.next(send_email)\
            #.next(sfn.Choice(self, 'Order Complete?')
            #      .when(sfn.Condition.string_equals('$.status', 'FAILED'), order_failed)
            #      .when(sfn.Condition.string_equals('$.status', 'SUCCEEDED'), order_succeeded)
            #      .otherwise(wait_job))

        log_group = logs.LogGroup(self, "OrderManagerStepFunctionLogGroup")

        sm = sfn.StateMachine(
            self, "OrderManager",
            definition=definition,
            timeout=Duration.minutes(5),
            logs=sfn.LogOptions(
                destination=log_group,
                level=sfn.LogLevel.ALL
            ),
            state_machine_type = sfn.StateMachineType.EXPRESS
        )

        #with open('./sfn-order.json') as f:
        #    definition = json.load(f)
        #definition = json.dumps(definition, indent = 4)
        #sfn.CfnStateMachine(self, "om", definition_string=definition)

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
                        effect= iam.Effect.ALLOW,
                        resources=['*']
                )
        )

        #state_machine = sfn.StateMachine(self, "OrderManager",
        #                                 definition=tasks.LambdaInvoke(self, "MyLambdaTask",
        #                                    lambda_function=hello_function).next(
        #                                    sfn.Succeed(self, "GreetedWorld")))

        #create_order_step_function.grant_start_execution(order_manager_lambda.role)
        #create_order_step_function.grant_read(order_manager_lambda.role)

        #order_manager_lambda.addToRolePolicy(iam.PolicyStatement({
        #        actions: ['ses:SendEmail', 'SES:SendRawEmail'],
        #        resources: ['*'],
        #        effect: iam.Effect.ALLOW,
        #}));


        api_order_manager = self.api.root.add_resource("order_manager")
        ## Example POST: https://3ir7i48vu4.execute-api.us-east-1.amazonaws.com/prod/stores
        #{
        #  "cart_id": "user_id#guest-cart_id#0001",
        #  "store_id": "2002",
        #  "customer": {
        #    "id":"10001",
        #    "name":"Joohn Dooe 1",
        #    "email":"joohn@dooe.com",
        #    "address": "1600 Pennsylvania Avenue, DC"
        #  },
        #  "payment": {
        #    "app_id": "APPID",
        #    "app_token": "APPTOKEN"
        #  },
        #  "shipping": {
        #    "name":"Joohn Dooe 1",
        #    "address": "1600 Pennsylvania Avenue, DC"
        #  },
        #  "loyalty_id": "1234567890"
        #}
        api_order_manager.add_method("ANY", apigateway_.StepFunctionsIntegration.start_execution(state_machine=sm, headers=True, authorizer=True))
        self.order_manager_url=f"https://{self.api.rest_api_id}.execute-api.{Aws.REGION}.amazonaws.com/prod/order_manager"

        #ses_template = {
        #  "Template": {
        #    "TemplateName": "OrderEmailConfirmation",
        #    "SubjectPart": "Greetings, {{customer_id}}!",
        #    "HtmlPart": BODY_HTML,
        #    "TextPart": BODY_TEXT
        #  }
        #}


        #apigateway_.StepFunctionsRestApi(self, 
        #            "OrderManagerAPI",
        #            headers=True,
        #            authorizer=True,
        #            state_machine = sm)

        #order_confirmation = api.root.add_resource("payment")
        #order_confirmation.add_method("POST")