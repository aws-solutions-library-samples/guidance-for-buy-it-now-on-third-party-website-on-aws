import json
import os

import boto3
from boto3.dynamodb.conditions import Key
from utils.common_utils import (
    DecimalEncoder
)

client = boto3.client('dynamodb')
dynamodb_ = boto3.resource('dynamodb')

def storeSelectorHandler(event, context):
    print(event)
    
    TABLE_NAME = os.environ['CART_TABLE']
    cart_table = dynamodb_.Table(TABLE_NAME)

    if event["httpMethod"] == "POST":
        data = json.loads(event["body"])
        cart_id = data["cart_id"]
        store_id = data["store_id"]
        print(f"Cart ID: {cart_id}, Store ID: {store_id}, Table: {cart_table.table_name}")
        query_response = cart_table.query(KeyConditionExpression=Key("user_id_cart_id").eq(cart_id))
        print(f"DATA: {query_response}")
        data = query_response["Items"]
        for i in query_response[u'Items']:
            print(json.dumps(i, cls=DecimalEncoder))
            product_id = i["product_id"]
            cart_table.update_item(
                Key={'user_id_cart_id': cart_id, "product_id": product_id},
                ExpressionAttributeNames={
                    "#store_id": "store_id",
                },
                UpdateExpression="SET #store_id=:s",
                ExpressionAttributeValues={
                    ':s': store_id},
                ReturnValues="UPDATED_NEW")
        while 'LastEvaluatedKey' in query_response:
            query_response = cart_table.query(
                KeyConditionExpression=Key("user_id_cart_id").eq(cart_id),
                ExclusiveStartKey=query_response['LastEvaluatedKey']
            )
            data.update(response["Items"])
            for i in query_response['Items']:
                print(json.dumps(i, cls=DecimalEncoder))
                product_id = i["product_id"]
                cart_table.update_item(
                    Key={'user_id_cart_id': cart_id, "product_id": product_id},
                    ExpressionAttributeNames={
                        "#store_id": "store_id",
                    },
                    UpdateExpression="SET #store_id=:s",
                    ExpressionAttributeValues={
                        ':s': store_id},
                    ReturnValues="UPDATED_NEW")

        #if "Items" in data:
        #    item = data["Items"]
        #    response = {
        #        "statusCode": 200,
        #        "body": json.dumps(item, cls=DecimalEncoder)
        #    }
        #else:
        #    response = {
        #        "statusCode": 200,
        #        "body": json.dumps(f"Cart Id {cart_id} not available")
        #    }
        #cart_table.update_item(
        #    Key={'user_id_cart_id': cart_id},
        #    ExpressionAttributeNames={
        #        "#store_id": "store_id",
        #    },
        #    UpdateExpression="SET #store_id=:s",
        #    ExpressionAttributeValues={
        #        ':s': store_id},
        #    ReturnValues="UPDATED_NEW")

        response = {
            'statusCode': 200,
            'body': json.dumps('Store Selected')
        }
    return response

    def scan_table(dynamo_client, *, TableName, **kwargs):
        paginator = client.get_paginator("scan")

        for page in paginator.paginate(TableName=TableName, **kwargs):
            yield from page["Items"]