import json
import os

import boto3

client = boto3.client('dynamodb')
dynamodb_ = boto3.resource('dynamodb')

def storesHandler(event, context):
    print(event)
    
    store = None
    BUYITNOW_TABLE_NAME = os.environ['BUYITNOW_TABLE']
    buyitnow_table = dynamodb_.Table(BUYITNOW_TABLE_NAME)
    PK = None
    SK = None
    if event["pathParameters"] != None:
        store = event["pathParameters"]["store"]
        PK = "stores"
        SK = store

    if event["httpMethod"] == "POST":
        data = json.loads(event["body"])
        PK = "stores"
        SK = data["id"]

        buyitnow_table.put_item(
                Item={
                    "PK": PK,
                    "SK": SK,
                    "id": SK,
                    "name": data["name"],
                    "address": data["address"],
                })
        response = {
            'statusCode': 200,
            'body': json.dumps('Store Added')
        }
    elif event["httpMethod"] == "GET" and store != None:
        data = buyitnow_table.get_item(Key={"PK": PK, "SK": SK})
        print(data)
        if "Item" in data:
            item = data["Item"]
            response = {
                "statusCode": 200,
                "body": json.dumps(item)
            }
        else:
            response = {
                "statusCode": 200,
                "body": json.dumps('Store Id not available')
            }

    elif event["httpMethod"] == "GET" and store == None:
        data = buyitnow_table.query(KeyConditionExpression=
                                    boto3.dynamodb.conditions.Key('PK')
                                    .eq('stores'))
        items = data["Items"]
        response = {
            "statusCode": 200,
            "body": json.dumps(items)
        }
    return response