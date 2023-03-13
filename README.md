
# Guidance for Buy-it-Now on third party websites on AWS

This repository has a CDK app to demonstrate how to build a Buy-it-Now capability from a third party store. This CDK app will use Lambda, Step Functions, DynamoDB, API Gateway, Simple Notification Service (SNS) and Secrets Manager.

### Table of Contents
- [Introduction](#introduction)
- [Pre-requisites](#pre-requisites)
- [Deployment](#deployment)
- [Validation](#validation)
  - [Initialization of Products, Stores and Products in Stores](#initialization-of-products-stores-and-products-in-stores)
  - [Buy-it-Now Process](#buy-it-now-process)
  - [Step function steps](#step-function-steps)
- [Cleanup](#cleanup)
- [FAQ](#faq)

## Introduction

The Buy-it-Now tool enables consumers to purchase Consumer packaged goods(CPG) products directly from retailers without leaving the brand website.

The Buy-it-Now guidance enables the consumers that visit CPG brand websites to learn about the brand and to buy the product while remaining on the brand website.  This guidance enables CPGs to offer the consumer the option to purchase their favorite brand items directly from retail sites like Walmart.com, Amazon.com and Target.com and still remain in the brand website.  This guidance enables CPGs to keep valuable consumers on their brand sites while still offering the ability to to purchase their products from online retailer.  This enables CPGs to maintain a high quality brand experience (capture 1st party data on the consumer based on the purchase) where as today the consumer typically leaves the brand website and complete the purchase on the retailer site with limited brand information.  CPG can offer consumers a broader set of brand offerings including new innovative test products only available at select retailers.  The Buy-it-Now guidance enables CPGs to still send the sales transaction to the retailer however they maintain the consumer experience on their brand site.

## Pre-requisites
- python3 v3.9.x with venv package
- Node
- AWS CLI
- AWS Account with CLI access
- curl 7.82.0 or greater.
  - A REST client like insomnia or postman can be used instead of curl
- jq (optional if using curl)

More details about the pre-requisites to run the CDK app can be found in https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html#getting_started_prerequisites

## Deployment
The steps to deploy the guidance are as follows:

1. Clone the `main` repository
```
git clone git@github.com:aws-solutions-library-samples/guidance-for-buy-it-now-on-third-party-website-on-aws.git
cd guidance-for-buy-it-now-on-third-party-website-on-aws
```

2. Create a virtualenv on MacOS and Linux
```
python3 -m venv .venv
```

3. After the virtualenv is created, you can use the following step to activate your virtualenv.
```
$ source .venv/bin/activate
```
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;If you are a Windows platform, you would activate the virtualenv like this:
```
% .venv\Scripts\activate.bat
```
4. Once the virtualenv is activated, you can install the required dependencies.
```
$ pip install -r requirements.txt
```

5. At this point you can view the available stacks to deploy using the command

```
$ cdk ls
```
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;You should see 2 stacks Thirdparty-MockStack and guidance-for-buy-it-now-on-third-party-website-on-aws stack

6. You will first need to deploy the Thirdparty-MockStack. This stack is used to mock third party resources in our guidance. This stack will spin up 1 API Gateway with 3 mock endpoints and 1 DynamoDB table.
   - DynamoDB: This is used to store product details like name and price from different stores
   - API Gateway:
     - Payment Gateway: This mock endpoint allows us to validate the payment details submitted by the customer
     - Pre-Order Gateway: This mock endpoint allows us to lock the inventory at the third party retailers side
     - Order Gateway: This mock endpoint allows us to place an order to the third party retailers site.

```
cdk deploy Thirdparty-MockStack
```

7. You will deploy the `guidance-for-buy-it-now-on-third-party-website-on-aws` stack using the below command. You will need to pass a valid email address to get the order confirmation/failure emails as you test the stack.
```
cdk deploy guidance-for-buy-it-now-on-third-party-website-on-aws -c verified_identity=<EMAIL ADDRESS>
```

Capture the following URL's that will be output from the above command.
```
guidance-for-buy-it-now-on-third-party-website-on-aws.CartManagementURL =  https://<UNIQUE ID>.execute-api.<REGION>.amazonaws.com/prod/carts

guidance-for-buy-it-now-on-third-party-website-on-aws.OrderManagementURL = https://<UNIQUE ID>.execute-api.<REGION>.amazonaws.com/prod/order_manager

guidance-for-buy-it-now-on-third-party-website-on-aws.ProductsManagementURL = https://<UNIQUE ID>.execute-api.<REGION>.amazonaws.com/prod/products

guidance-for-buy-it-now-on-third-party-website-on-aws.StoreManagementURL = https://<UNIQUE ID>.execute-api.<REGION>.amazonaws.com/prod/stores

guidance-for-buy-it-now-on-third-party-website-on-aws.StoreProductManagementURL = https://<UNIQUE ID>.execute-api.<REGION>.amazonaws.com/prod/store_products
```

8. You will get an email to the email address provided by the above command from AWS SNS to confirm subscription to the SNS topic. Click the "Confirm subscription" link. This is needed to allow AWS SNS to send emails of the status of the order.

You are now ready to test the guidance.

## Validation

In this section, we will first populate some test data and then we will go through the steps to place an order

### Initialization of Products, Stores and Products in Stores

Populate products to be used for testing
```
curl https://<UNIQUE ID>.execute-api.<REGION>.amazonaws.com/prod/products/ \
--json  @- << EOF
{
    "id":"101",
    "name":"Product 1",
    "price": "99.99"
}
EOF

curl https://<UNIQUE ID>.execute-api.<REGION>.amazonaws.com/prod/products/ \
--json  @- << EOF
{
    "id":"102",
    "name":"Product 2",
    "price": "199.99"
}
EOF
```

Populate a list of third party stores for testing
```
curl https://<UNIQUE ID>.execute-api.<REGION>.amazonaws.com/prod/stores/ \
--json  @- << EOF
{
    "id":"2001",
    "name":"Store 1",
    "address": "1600 Pennsylvania Avenue, DC"
}
EOF

curl https://<UNIQUE ID>.execute-api.<REGION>.amazonaws.com/prod/stores/ \
--json  @- << EOF
{
    "id":"2002",
    "name":"Store 2",
    "address": "1600 Pennsylvania Avenue, DC"
}
EOF
```

Populate the 2 third party stores created above with the 2 products as shown below.
```
curl https://<UNIQUE ID>.execute-api.<REGION>.amazonaws.com/prod/store_products \
--json  @- << EOF
{
    "store_id":"2001",
    "product_id":"101",
    "product_name":"Product 1",
    "price": "89.99"
}
EOF

curl https://<UNIQUE ID>.execute-api.<REGION>.amazonaws.com/prod/store_products \
--json  @- << EOF
{
    "store_id":"2002",
    "product_id":"101",
    "product_name":"Product 1",
    "price": "79.99"
}
EOF

curl https://<UNIQUE ID>.execute-api.<REGION>.amazonaws.com/prod/store_products \
--json  @- << EOF
{
    "store_id":"2001",
    "product_id":"102",
    "product_name":"Product 2",
    "price": "59.99"
}
EOF

curl https://<UNIQUE ID>.execute-api.<REGION>.amazonaws.com/prod/store_products \
--json  @- << EOF
{
    "store_id":"2002",
    "product_id":"102",
    "product_name":"Product 2",
    "price": "49.99"
}
EOF
```
### Buy-it-Now Process
We are now ready to proceed with viewing the products, adding the products to be purchased into a cart, viewing the price of products from the 2 stores we created for testing and placing an order. The flow chart below shows the order process steps.

![Order Process Steps](/assets/images/order_flowchart.png)

1. The customer navigating to the CPG brand site will see all the products available using the command below. The output should show the 2 sample products we added.
```
curl https://<UNIQUE ID>.execute-api.<REGION>.amazonaws.com/prod/products/ | jq .
```
2. When the customer is ready to buy the products from the site, the below commands will be executed. We are adding 2 products to the customers cart
```
curl https://<UNIQUE ID>.execute-api.<REGION>.amazonaws.com/prod/carts/ \
--json @- << EOF
{
    "partial_cart_id": "0001",
    "product_id":"101",
    "quantity":"2"
}
EOF

curl https://<UNIQUE ID>.execute-api.<REGION>.amazonaws.com/prod/carts/ \
--json @- << EOF
{
    "partial_cart_id": "0001",
    "product_id":"102",
    "quantity":"3"
}
EOF
```
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;To get the contents of the cart, you can run the below command
```
curl https://<UNIQUE ID>.execute-api.<REGION>.amazonaws.com/prod/carts/user_id%23guest-cart_id%230001 | jq .
```

3. When the customer is ready to view the total cost of items to be purchased from the 2 stores, the below command is run. In this command, we are able to pass a loyalty id for a store to get special deals if applicable. This allows the customer to choose the store where they want to place the order.
```
curl https://<UNIQUE ID>.execute-api.<REGION>.amazonaws.com/prod/store_products/ \
--json @- << EOF | jq .
{
    "cart_id":"user_id#guest-cart_id#0001",
    "store_id": "2001",
    "loyalty_id": "1234567890"
}
EOF
```
4. When the customer places the order, the below command should be run. In the below command, you will notice 2 headers "is_valid" and "place_order". The reason for these headers is to simulate failures in the step function that is used to place the order. You should receive an email with the status of the order.
```
curl https://<UNIQUE ID>.execute-api.<REGION>.amazonaws.com/prod/order_manager/ \
-H "is_valid:true" \
-H "place_order:true" \
--json @- << EOF | jq .
{
    "cart_id": "user_id#guest-cart_id#0001",
    "store_id": "2001",
    "customer": {
        "name":"John Doe",
        "email":"john@doe.com",
        "address": "1600 Pennsylvania Avenue, DC"
    },
    "payment": {
        "app_id": "APPID",
        "app_token": "APPTOKEN"
    },
    "shipping": {
        "name":"John Doe 1",
        "address": "1600 Pennsylvania Avenue, DC"
    },
    "loyalty_id": "1234567890"
}
EOF
``` 
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;The above command will start a step function that does the steps shown in the diagram below.
![Step Function Image](/assets/images/stepfunctions_graph_light.png)

### Step function steps:
The step function is used to manage the various steps that need to occur when an order is placed. We use the step "Order Exception Handler" to handle failure scenarios. In this guidance, we update the order status as FAILED in the DynamoDB when this step is triggered. This step will also send a failure email if you have subscribed to the SNS Topic.

1. In the `Capture Order Details`, we update the DynamoDB to capture the order event. We also call the third party mock "Pre-Order Gateway". The goal here is to let the third part store know about the order and lock the inventory based on the order details.

2. In `Validate Payment` step, we call the mock "Payment Gateway" to validate the payment details are valid. We are using APPID and APPTOKEN as the username and password that will be used to authenticate with the payment processor. Since these values are sensitive, we create these values as secrets in the AWS Secret Manager. In this demo, we will automatically create a secret in case the AWS Secret Manager does not have entries for APPID and APPTOKEN.<br><br>
The header "is_valid" is used to let the mock "Payment Gateway" return a success or failure response.

3. If the payment details are valid, we add the customer and store loyalty details to the DynamoDB table in the `Add Customer` step.

4. In `Create Order` step, we call the mock "Order Gateway" to place the order.<br><br>
The header "place_order" is used to let the mock "Order Gateway" return a success or failure response.

5. If the order was successfully created, we capture the third party order details in our DynamoDB table in the `Capture 3P Order` step.

6. The `Publish message` step is used to publish the state of the order to the SNS Topic. If you subscribed to the SNS Topic you received in the email, then you should see an email notification with the status of the order.

## Cleanup
After testing the guidance, you will be able to clean up the AWS resources using the below commands
```
cdk destroy guidance-for-buy-it-now-on-third-party-website-on-aws
cdk destroy Thirdparty-MockStack
```

## FAQ
- How do I add a new lambda layer in this guidance?<br><br>
If the updates you made to this guidance require you to add a dependency as a lambda layer, follow the steps below:
  - Navigate to `lambda/layers`
  ```
  cd lambda/layers
  ```
  - Create a new folder `<MY-DEPENDENCY-NAME>` and navigate into it
  ```
  mkdir <MY-DEPENDENCY-NAME>
  cd <MY-DEPENDENCY-NAME>
  ```
  - Run the below command
  ```
  pip install "<MY-DEPENDENCY-NAME>" --target ./python/lib/python3.9/site-packages
  ```
  - In the guidance stack, add your layer `<MY-DEPENDENCY-NAME>` using the below snippet
  ```
  my_dependency_name_layer = lambda_.LayerVersion(self, '<MY-DEPENDENCY-NAME>',
                                            code=lambda_.AssetCode(
                                                'lambda/layers/<MY-DEPENDENCY-NAME>/'),
                                            compatible_runtimes=[lambda_.Runtime.PYTHON_3_9])
  ```
  - Add the `my_dependency_name_layer` layer to any lambda function that needs it
  - Run the `cdk deploy` command shown below
  ```
  cdk deploy guidance-for-buy-it-now-on-third-party-website-on-aws -c verified_identity=<EMAIL ADDRESS>
  ```
- How do I upgrade the `requests` and `aws-lambda-powertools[all]` lambda layers?<br><br>
To upgrade the version of the layers , you can follow the below steps
  - Navigate to `lambda/layers` folder
  ```
  cd lambda/layers/requests-powertools
  ```
  - Install the latest `requests` and `aws-lambda-powertools[all]` modules
  ```
  pip install requests \
  --target ./python/lib/python3.9/site-packages --upgrade

  pip install "aws-lambda-powertools[all]" \
  --target ./python/lib/python3.9/site-packages --upgrade 
  ```
  - Run the `cdk deploy` command shown below to update the stack
  ```
  cdk deploy guidance-for-buy-it-now-on-third-party-website-on-aws -c verified_identity=<EMAIL ADDRESS>
  ```