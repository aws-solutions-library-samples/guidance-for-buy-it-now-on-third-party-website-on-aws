import json
import os
import uuid

import boto3
from utils.common_utils import (
    is_payment_valid,
    create_3p_order,
    get_user_id,
    pre_order,
    get_partial_cart_id
)
from aws_lambda_powertools import (
    Logger,
    Tracer
)

sfn = boto3.client('stepfunctions')
sns = boto3.client('sns')

logger = Logger()
tracer = Tracer()

client = boto3.client('dynamodb')
dynamodb_ = boto3.resource('dynamodb')
session = boto3.session.Session()
secretsmanager_client = session.client(
    service_name='secretsmanager',
    region_name=session.region_name
)

SUCCESS_VALUE = "SUCCEEDED"
FAILED_VALUE = "FAILED"

@tracer.capture_lambda_handler
def orderManagerHandler(event, context):
    print(event)

    PAYMENT_GATEWAY = os.environ['PAYMENT_GATEWAY']
    ORDER_GATEWAY = os.environ['ORDER_GATEWAY']
    PRE_ORDER_GATEWAY = os.environ['PRE_ORDER_GATEWAY']
    BUYITNOW_TABLE_NAME = os.environ['BUYITNOW_TABLE']
    buyitnow_table = dynamodb_.Table(BUYITNOW_TABLE_NAME)
    PK = None
    SK = None
    SK_PREORDER = "order#PREORDER"

    logger.info(f"ORDER EVENT: {event}")

    step = None
    try:
        step = event["step"]
    except KeyError:
        logger.info(f"Key Not found: event['step']")

    logger.info(f"STEP: {step}")
    if step == "failed":
        logger.info("Failure triggered")
        error_json = event['error']
        logger.info(f"error_json: {error_json}")
        cart_id = error_json['body']['cart_id']
        logger.info(f"Failed Cart ID: {cart_id}")
        logger.info(f"Body: {error_json['body']}")
        logger.info(f"Headers: {error_json['header']}")
        customer_id = "Not Available"
        order_id = "Not Available"
        try:
            customer_id = event["customer_id"]
        except KeyError:
            logger.info("No customer_id available")
        try:
            order_id = event["order_id"]
        except KeyError:
            logger.info("No order_id available")
        PK = cart_id
        SK = SK_PREORDER
        buyitnow_table.update_item(
            Key={'PK': PK, 'SK': SK},
            ExpressionAttributeNames={
                "#order_status": "status",
            },
            UpdateExpression="SET #order_status=:os",
            ExpressionAttributeValues={
                ':os': FAILED_VALUE},
            ReturnValues="UPDATED_NEW")
        response = {
            'statusCode': 200,
            'order_status': FAILED_VALUE,
            'body': error_json['body'],
            'header': error_json['header'],
            'customer_id': customer_id,
            'order_id': order_id,
            'message': get_message(event, FAILED_VALUE),
            'subject': get_subject(event, FAILED_VALUE)
        }
        return response
    logger.info(f"BODY: {event['body']}")
    logger.info(f"Body Type: {type(event['body'])}")
    if type(event['body']) == dict:
        data = event["body"]
    elif type(event['body']) == str:
        data = json.loads(event["body"])
    logger.info(f"DATA: {data}")
    cart_id = data["cart_id"]
    store_id = data["store_id"]
    customer = data["customer"]
    payment = data["payment"]
    shipping = data["shipping"]
    loyalty_id = data["loyalty_id"]
    customer.update(
        {"store_loyalty": [{"store_id": store_id, "loyalty_id": loyalty_id}]})
    print(f"Cart ID: {cart_id}, Store ID: {store_id}")
    header = None
    try:
        header = event["header"]
    except KeyError:
        logger.info("No header available")

    if step == "start":
        # Create pre-order - using mock endpoint
        PK = cart_id
        SK = SK_PREORDER
        buyitnow_table.update_item(
            Key={'PK': PK, 'SK': SK},
            ExpressionAttributeNames={
                "#order_status": "status",
            },
            UpdateExpression="SET #order_status=:os",
            ExpressionAttributeValues={
                ':os': 'STARTED'},
            ReturnValues="UPDATED_NEW")
        pre_order_response = pre_order(cart_id, header, PRE_ORDER_GATEWAY)
        pre_order_state = pre_order_response['pre_order_state']
        logger.info(
            f"Pre-order Response: {pre_order_state}")
        if "INVENTORY LOCKED" != pre_order_state:
            raise Exception("Pre-Order Failed")
        response = {
            'body': event["body"],
            'header': header,
            'cart_id': cart_id,
            'pre_order_state': pre_order_state
        }
        return response
    if step == "validate":
        # Validate payment - using mock endpoint
        logger.info(f"payment gateway url: {PAYMENT_GATEWAY}")
        payment_valid = is_payment_valid(
            secretsmanager_client, payment, header, PAYMENT_GATEWAY)
        logger.info(f"Payment {payment_valid}")
        response = {
            'body': event["body"],
            'header': header,
            'cart_id': cart_id,
            'payment_valid': SUCCESS_VALUE if payment_valid else FAILED_VALUE
        }
        if not payment_valid:
            raise Exception(json.dumps(response))
        return response
    if step == "add_customer":
        customer_id = uuid.uuid4().hex
        PK = cart_id
        user_id = get_user_id(event["header"])
        SK = "userid#"+user_id
        buyitnow_table.update_item(
            Key={'PK': PK, 'SK': SK},
            ExpressionAttributeNames={
                "#customer_id": "customer_id",
                "#name": "name",
                "#email": "email",
                "#address": "address",
                "#payment_id": "payment_id",
                "#payment_token": "payment_token",
                "#loyalty_id": "loyalty_id",
                "#store_id": "store_id",
                "#shipping_name": "shipping_name",
                "#shipping_address": "shipping_address",
            },
            UpdateExpression="SET #customer_id=:c, \
                    #name=:n, \
                    #email=:e, \
                    #address=:a, \
                    #payment_id=:pi, \
                    #payment_token=:pt, \
                    #loyalty_id=:l, \
                    #store_id=:si, \
                    #shipping_name=:sn, \
                    #shipping_address=:sa",
            ExpressionAttributeValues={
                ':c': customer_id,
                ':n': customer['name'],
                ':e': customer['email'],
                ':a': customer['address'],
                ':pi': payment['app_id'],
                ':pt': payment['app_token'],
                ':l': loyalty_id,
                ':si': store_id,
                ':sn': shipping['name'],
                ':sa': shipping['address'], },
            ReturnValues="UPDATED_NEW")
        response = {
            'body': event["body"],
            'header': header,
            'customer_id': customer_id,
        }
        return response
    if step == "create_order":
        # Create Order - using mock endpoint
        order_response = create_3p_order(
            secretsmanager_client, payment, shipping, header, ORDER_GATEWAY)
        order_placed = order_response["order_placed"]
        logger.info(f"Order Placed: {order_placed}")
        PK = cart_id
        if order_placed:
            order_id = order_response["order_id"]
            logger.info(f"Order ID: {order_id}")
            response = {
                'body': event["body"],
                'header': header,
                'customer_id': event["customer_id"],
                'order_id': order_id,
                'order_placed': SUCCESS_VALUE if order_placed else FAILED_VALUE
            }
        else:
            response = {
                'body': event["body"],
                'header': header,
                'customer_id': event["customer_id"],
                'order_placed': SUCCESS_VALUE if order_placed else FAILED_VALUE
            }
        logger.info(f"Order Created Response: {json.dumps(response)}")
        return response
    if step == "capture_order":
        order_id = event['order_id']
        logger.info(f"Capture Order ID: {order_id}")
        PK = cart_id
        SK = "order#"+order_id
        logger.info(f"Capture Order PK: {PK}, SK: {SK}")
        buyitnow_table.update_item(
            Key={'PK': PK, 'SK': SK},
            ExpressionAttributeNames={
                "#order_id": "id",
                "#order_status": "status",
            },
            UpdateExpression="SET #order_id=:oi, #order_status=:os",
            ExpressionAttributeValues={
                ':oi': order_id, ':os': 'PLACED'},
            ReturnValues="UPDATED_NEW")
        SK = SK_PREORDER
        buyitnow_table.delete_item(Key={"PK": PK, "SK": SK})
        partial_cart_id = get_partial_cart_id(cart_id)
        logger.info(
            f"Partial Cart ID: {partial_cart_id} from Cart ID: {cart_id}")
        SK = "cart#"+partial_cart_id
        buyitnow_table.update_item(
            Key={'PK': PK, 'SK': SK},
            ExpressionAttributeNames={
                "#cart_status": "status",
            },
            UpdateExpression="SET #cart_status=:cs",
            ExpressionAttributeValues={
                ':cs': 'CLOSED'},
            ReturnValues="UPDATED_NEW")
        response = {
            'body': event["body"],
            'header': header,
            'customer_id': event["customer_id"],
            'order_id': event["order_id"],
            'order_status': SUCCESS_VALUE,
            'message': get_message(event, SUCCESS_VALUE),
            'subject': get_subject(event, SUCCESS_VALUE)
        }
        logger.info(f"Capture Order Response: {response}")
        return response
    response = {
        'statusCode': 200,
        'body': json.dumps("Step was missing")
    }
    return response


def get_message(event, status):
    message = "Unexpected error message"
    if (status == SUCCESS_VALUE):
        message = ("Order successfully placed \r\n\n"
                   f"Order ID: {event['order_id']}\n"
                   f"Customer Name: {event['body']['customer']['name']}\n"
                   f"Customer ID: {event['customer_id']}\n"
                   )
    else:
        message = "The order could not be placed"
    logger.info(f"Message: {message}")
    return message


def get_subject(event, status):
    subject = "Unexpected subject"
    if (status == SUCCESS_VALUE):
        subject = "Order successfull"
    else:
        subject = "Order failed"
    logger.info(f"Subject: {subject}")
    return subject
