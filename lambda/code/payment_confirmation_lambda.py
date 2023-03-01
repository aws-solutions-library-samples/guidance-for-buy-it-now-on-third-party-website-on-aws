import json
import os

import boto3
from boto3.dynamodb.conditions import Key
from utils.common_utils import (
    DecimalEncoder,
    add_customer,
    is_payment_valid,
    get_order_id,
    send_email
)
from aws_lambda_powertools import (
    Logger,
    Tracer
)
#from aws_cdk import (
#    aws_stepfunctions as sfn,
#    aws_stepfunctions_tasks as tasks
#)

sfn = boto3.client('stepfunctions')

logger = Logger()
tracer = Tracer()

client = boto3.client('dynamodb')
dynamodb_ = boto3.resource('dynamodb')

@tracer.capture_lambda_handler
def paymentConfirmationHandler(event, context):
    print(event)
    
    CUSTOMER_URL = os.environ['CUSTOMER_URL']
    ORDERS_TABLE = os.environ['ORDERS_TABLE']
    orders_table = dynamodb_.Table(ORDERS_TABLE)

    if event["httpMethod"] == "POST":
        logger.info(f"EVENT: {event['body']}")
        data = json.loads(event["body"])
        cart_id = data["cart_id"]
        store_id = data["store_id"]
        customer = data["customer"]
        payment = data["payment"]
        shipping = data["shipping"]
        loyalty = data["loyalty"]
        customer.update({"store_loyalty": [{"store_id": store_id, "loyalty_id": loyalty}]})
        print(f"Cart ID: {cart_id}, Store ID: {store_id}, CUSTOMER_URL: {CUSTOMER_URL}")

        #payment_validation = tasks.EvaluateExpression("Payment Validation",
        #    expression="is_payment_valid(payment)",
        #    result_path="$.payment_valid"
        #)

        #sfn.StateMachine("StateMachine",
        #    definition=payment_validation.next(payment_validation)
        #)

        state_machine_name = "CreateOrder"
        state_machine_arn = None

        paginator = sfn.get_paginator('list_state_machines')
        for page in paginator.paginate():
            for machine in page['stateMachines']:
                if machine['name'] == state_machine_name:
                    state_machine_arn = machine['stateMachineArn']
                    break
            if state_machine_arn is not None:
                break
        kwargs = {'stateMachineArn': state_machine_arn, 'name': "place_order"}
        response = sfn.start_execution(**kwargs)
        run_arn = response['executionArn']

        payment_valid = is_payment_valid(payment)
        logger.info(f"Payment {payment_valid}")
        if not payment_valid:
            print(f"Payment is not Valid")
            response = {
                'statusCode': 404,
                'body': json.dumps("Payment Details Invalid")
            }
            return response
        print(f"Payment Validation is a Success")
        add_cust_response = add_customer(CUSTOMER_URL, customer, event['headers'])
        customer_response = add_cust_response.json()
        logger.info(f"Customer Response: {customer_response}")
        customer_id = customer_response["customer_id"]
        # Create Order
        # API Gateway can mock the rest call
        order_id = get_order_id()
        orders_table.put_item(
            Item={
                "order_id": order_id,
                "customer_id": customer_id,
                "cart_id": cart_id,
            })
        json_response = []
        json_response.append({"customer":add_cust_response.ok, "payment": payment_valid})
        # The email body for recipients with non-HTML email clients.
        BODY_TEXT = ("Order successfully placed \r\n"
                     f"Order ID: {order_id}\n"
                     f"Customer ID: {customer_id}\n"
                    )

        # The HTML body of the email.
        BODY_HTML = f"""<html>
        <head></head>
        <body>
          <h1>Order successfully placed</h1>
          <p>
          Order ID: {order_id}<br>
          Customer ID: {customer_id}<br>
          </p>
        </body>
        </html>
            """            
        send_email("vjprince@amazon.com","vjprince@amazon.com","Order placed", html_content=BODY_HTML, text_content=BODY_TEXT, charset="UTF-8")
        response = {
            'statusCode': 200,
            'body': json.dumps(json_response)
        }
    return response