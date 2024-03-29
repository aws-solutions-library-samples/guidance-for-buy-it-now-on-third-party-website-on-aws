import json
import os

import boto3
from boto3.dynamodb.conditions import Key

from aws_lambda_powertools import (
    Logger,
    Tracer
)

from utils.common_utils import (
    DecimalEncoder,
    NotFoundException,
    get_cart,
    get_stores,
    multiply
)

dynamodb_ = boto3.resource('dynamodb')
client = boto3.client('dynamodb')
logger = Logger()
tracer = Tracer()


def storeProductHandler(event, context):
    print(event)

    TABLE_NAME = os.environ['STORE_PRODUCT_TABLE']
    CART_URL = os.environ['GET_CART_URL']
    STORES_URL = os.environ['GET_STORES_URL']
    store_product_table = dynamodb_.Table(TABLE_NAME)
    product_id = None
    store_id = None
    if event["pathParameters"] != None and event["httpMethod"] == "GET":
        try:
            product_id = event["pathParameters"]["product_id"]
            store_id = event["pathParameters"]["store_id"]
        except KeyError:
            pass

    if event["httpMethod"] == "POST":
        data = json.loads(event["body"])
        store_id = None
        product_id = None
        cart_id = None
        try:
            store_id = data["store_id"]
            product_id = data["product_id"]
            logger.info(f"{store_id}_{product_id}")
        except KeyError:
            pass
        try:
            cart_id = data["cart_id"]
            logger.info(f"Cart ID: {cart_id}")
        except KeyError:
            pass
        if store_id != None and product_id != None:
            client.put_item(TableName=TABLE_NAME,
                            Item={
                                "store_id": {"S": data["store_id"]},
                                "product_id": {"S": data["product_id"]},
                                "product_name": {"S": data["product_name"]},
                                "price": {"N": data["price"]},
                            })
            response = {
                'statusCode': 200,
                'body': json.dumps('Store Product Added')
            }
        #
        # Get the total cost of the items in the cart
        #
        elif cart_id != None:
            try:
                cart_contents = get_cart(cart_id=cart_id, cart_url=CART_URL, headers=event['headers'])
                if cart_contents != None or len(cart_contents) == 0:
                    logger.info(f"Cart Id: {cart_id} does not exist")
                logger.info(f"Cart contains cart_contents: {cart_contents}")
                stores = get_stores(stores_url=STORES_URL, headers=event['headers'])
                logger.info(f"Stores: {stores}")
                store_obj = []
                json_obj = []
                input_store_id = None
                input_loyalty_id = None
                try:
                    input_store_id = data["store_id"]
                    input_loyalty_id = data["loyalty_id"]
                    logger.info(f"{input_store_id}_{input_loyalty_id}")
                except KeyError:
                    pass
                for store in stores:
                    store_id = store["id"]
                    logger.info(f"Store: {store}")
                    total_cost = 0
                    for product in cart_contents:
                        if not product['SK'].startswith("product"):
                            continue
                        product_id = product["id"]
                        quantity = product["quantity"]
                        logger.info(
                            f"Store ID: {store_id}, Product ID: {product_id}, Quantity: {quantity}")
                        data = store_product_table.get_item(
                            Key={"product_id": product_id, "store_id": store_id})
                        try:
                            item = data["Item"]
                            price = item["price"]
                            money = multiply(price, quantity)
                            logger.info(
                                f"Store ID: {store_id}, Product ID: {product_id}, Price: {price}, Total Price: {money}, Quantity: {quantity}")
                            logger.info(f"Item: {item}")
                            json_obj.append({"store_id": store_id, "product_id": product_id,
                                            "price": price, "quantity": quantity, "cost": money})
                            total_cost += money
                        except KeyError:
                            logger.info(
                                f"No Products for Store ID: {store_id}, Product ID: {product_id}")
                    if len(json_obj) > 0:
                        logger.info(
                            f"JSON_OBJ is not empty \
                                Store ID: {store_id}, \
                                Input Store ID: {input_store_id}, \
                                Input Loyalty ID: {input_loyalty_id}")
                        if (store_id == input_store_id and input_loyalty_id != None):
                            logger.info(
                                f"Matched Store ID: {store_id}. Loyalty ID: {input_loyalty_id}")
                            store_obj.append(
                                {"store_id": store_id, "total_cost": total_cost, "loyalty_id": input_loyalty_id, "items": json_obj})
                        else:
                            logger.info(
                                f"No Matched Store ID: {store_id}. Loyalty ID: {input_loyalty_id}")
                            store_obj.append(
                                {"store_id": store_id, "total_cost": total_cost, "items": json_obj})
                    json_obj = []
            except NotFoundException:
                logger.error(f"get_product failed for product_id {product_id}")
                response = {
                    "statusCode": 200,
                    "body": json.dumps(f"Product Id '{product_id}' not available")
                }
            response = {
                'statusCode': 200,
                'body': json.dumps(store_obj, cls=DecimalEncoder)
            }
    elif event["httpMethod"] == "GET" and product_id != None and store_id == None:
        data = store_product_table.query(
            KeyConditionExpression=Key("product_id").eq(product_id))
        logger.info(f"DATA: {data}")
        if "Items" in data:
            item = data["Items"]
            response = {
                "statusCode": 200,
                "body": json.dumps(item, cls=DecimalEncoder)
            }
        else:
            response = {
                "statusCode": 200,
                "body": json.dumps(f"Product Id {product_id} not available")
            }
    elif event["httpMethod"] == "GET" and product_id != None and store_id != None:
        key = f'{{"product_id": {{"S": {product_id}}}, "store_id": {{"S": {store_id}}}}}'
        logger.info(f"Key: {key}")
        data = client.get_item(TableName=TABLE_NAME, Key={"product_id": {
                               "S": product_id}, "store_id": {"S": store_id}})
        if "Item" in data:
            item = data["Item"]
            response = {
                "statusCode": 200,
                "body": json.dumps(item)
            }
        else:
            response = {
                "statusCode": 200,
                "body": json.dumps(f"Store {store_id} does not have product {product_id}")
            }
    elif event["httpMethod"] == "GET" and product_id == None:
        data = client.scan(TableName=TABLE_NAME)
        items = data["Items"]
        response = {
            "statusCode": 200,
            "body": json.dumps(items)
        }
    return response
