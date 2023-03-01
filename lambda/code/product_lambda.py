import json
import os

import boto3

client = boto3.client('dynamodb')
dynamodb_ = boto3.resource('dynamodb')

def productHandler(event, context):
    print(event)
    
    #TABLE_NAME = os.environ['PRODUCT_TABLE']
    product = None
    BUYITNOW_TABLE_NAME = os.environ['BUYITNOW_TABLE']
    buyitnow_table = dynamodb_.Table(BUYITNOW_TABLE_NAME)
    PK = None
    SK = None
    if event["pathParameters"] != None:
        product = event["pathParameters"]["product"]
        #PK = "product_"+product
        #SK = product
        PK = "products"
        SK = product

    if event["httpMethod"] == "POST":
        data = json.loads(event["body"])
        PK = "products"
        SK = data["id"]
        #client.put_item(TableName=TABLE_NAME,
        #        Item={
        #            "id": {"S": data["id"]},
        #            "name": {"S": data["name"]},
        #            "price": {"N": data["price"]},
        #        })
        #buyitnow_table.put_item(
        #        Item={
        #            "id": "product_"+data["id"],
        #            "name": data["name"],
        #            "price": data["price"],
        #        })
        buyitnow_table.put_item(
                Item={
                    "PK": PK,
                    "SK": SK,
                    "id": SK,
                    "name": data["name"],
                    "price": data["price"],
                })
        response = {
            'statusCode': 200,
            'body': json.dumps('Product Added')
        }
    elif event["httpMethod"] == "GET" and product != None:
        data = buyitnow_table.get_item(Key={"PK": PK, "SK": SK})
        #data = client.get_item(TableName=TABLE_NAME, Key={"id": {"S": product}})
        if "Item" in data:
            item = data["Item"]
            response = {
                "statusCode": 200,
                "body": json.dumps(item)
            }
        else:
            response = {
                "statusCode": 200,
                "body": json.dumps('Product Id not available')
            }
    elif event["httpMethod"] == "GET" and product == None:
        #data = client.scan(TableName=TABLE_NAME)
        #data = buyitnow_table.scan()
        #data = buyitnow_table.query(Select='ALL_ATTRIBUTES',
        #                            KeyConditions={
        #                                'PK': {
        #                                    'AttributeValueList': [
        #                                        'product'
        #                                    ],
        #                                    'ComparisonOperator': 'BEGINS_WITH'
        #                                }
        #                            })
        data = buyitnow_table.query(KeyConditionExpression=
                                    boto3.dynamodb.conditions.Key('PK')
                                    .eq('products'))
        items = data["Items"]
        response = {
            "statusCode": 200,
            "body": json.dumps(items)
        }
    return response