import json
import os

import boto3
import requests

from boto3.dynamodb.conditions import Key

from utils.common_utils import (
    get_product,
    get_user_id,
    NotFoundException,
    DecimalEncoder
)

from aws_lambda_powertools import (
    Logger,
    Tracer
)

logger = Logger()
tracer = Tracer()
dynamodb_ = boto3.resource('dynamodb')
client = boto3.client('dynamodb')


@tracer.capture_lambda_handler
def cartHandler(event, context):
    print(event)

    cart_id_param = None
    product_id_param = None
    BUYITNOW_TABLE_NAME = os.environ['BUYITNOW_TABLE']
    buyitnow_table = dynamodb_.Table(BUYITNOW_TABLE_NAME)
    PK = None
    SK = None
    if event["pathParameters"] != None:
        try:
            cart_id_param = event["pathParameters"]["cart_id"]
            PK = cart_id_param
            product_id_param = event["pathParameters"]["product_id"]
            SK = "product#"+product_id_param
        except KeyError:
            pass
    logger.info(f"Cart is: {cart_id_param}")
    logger.info(f"Product ID is: {product_id_param}")

    if event["httpMethod"] == "POST":
        data = json.loads(event["body"])
        logger.info(f"Headers: {event['headers']}")
        product_id = data["product_id"]
        partial_cart_id = data["partial_cart_id"]
        logger.info(f"Partial Cart ID: {partial_cart_id}")
        logger.info(f"Product ID: {product_id}")
        quantity = data["quantity"]
        try:
            quantity = int(quantity)
        except ValueError:
            pass
        logger.info(f"Quantity: {quantity}")
        user_id = get_user_id(event["headers"])
        logger.info(f"User Id: {user_id}")
        try:
            product = get_product(product_id=product_id)
            logger.info(f"Product: {product}")
        except NotFoundException:
            logger.error(f"get_product failed for product_id {product_id}")
            response = {
                "statusCode": 200,
                "body": json.dumps(f"Product Id '{product_id}' not available")
            }
        partition_key = f"user_id#{user_id}-cart_id#{partial_cart_id}"
        logger.info(f"Partition Key: {partition_key}")
        sort_key = f"{product_id}"
        logger.info(f"Sort Key: {sort_key}")
        PK = partition_key
        SK = "product#"+sort_key
        buyitnow_table.update_item(
            Key={'PK': PK, 'SK': SK},
            ExpressionAttributeNames={
                "#product_id": "id",
                "#quantity": "quantity",
            },
            UpdateExpression="ADD #quantity :q SET #product_id=:p",
            ExpressionAttributeValues={
                ':q': quantity, ':p': product['id']},
            ReturnValues="UPDATED_NEW")
        # Put User ID
        SK = "userid#"+user_id
        buyitnow_table.put_item(
            Item={
                "PK": PK,
                "SK": SK,
                "id": user_id,
            })
        # Put Cart ID
        SK = "cart#"+partial_cart_id
        buyitnow_table.put_item(
            Item={
                "PK": PK,
                "SK": SK,
                "id": partial_cart_id,
            })
        response = {
            "statusCode": 200,
            "body": json.dumps(f"Product {product_id} added to cart")
        }
    elif event["httpMethod"] == "GET" and cart_id_param == None:
        response = {
            "statusCode": 200,
            "body": json.dumps("Cannot Query without Cart ID")
        }
    elif event["httpMethod"] == "GET" and cart_id_param != None and product_id_param == None:
        decoded_cart_id = requests.utils.unquote(cart_id_param)
        key = f'{{"user_id_cart_id": {{"S": {decoded_cart_id}}}'
        logger.info(f"Key: {key}")
        data = buyitnow_table.query(KeyConditionExpression=Key('PK').eq(
            decoded_cart_id) & Key('SK').begins_with('product#'))
        logger.info(f'DATA: {data}')
        if "Items" in data:
            items = data["Items"]
            logger.info(f'ITEMS: {items}')
            response = {
                "statusCode": 200,
                "body": json.dumps(items, cls=DecimalEncoder)
            }
        else:
            response = {
                "statusCode": 200,
                "body": json.dumps('Cart not available')
            }
    elif event["httpMethod"] == "GET" and cart_id_param != None and product_id_param != None:
        decoded_cart_id = requests.utils.unquote(cart_id_param)
        decoded_product_id = requests.utils.unquote(product_id_param)
        SK = "product#"+decoded_product_id
        key = f'{{"PK": {{"S": {decoded_cart_id}}}, "SK": {{"S": {SK}}}}}'
        logger.info(f"Key: {key}")
        data = buyitnow_table.query(KeyConditionExpression=Key(
            'PK').eq(decoded_cart_id) & Key('SK').eq(SK))
        logger.info(f"Data: {json.dumps(data, cls=DecimalEncoder)}")
        if "Items" in data:
            item = data["Items"]
            response = {
                "statusCode": 200,
                "body": json.dumps(item, cls=DecimalEncoder)
            }
        else:
            response = {
                "statusCode": 200,
                "body": json.dumps('Product not available in cart')
            }
    return response
