import json
import os

import boto3

client = boto3.client('dynamodb')
dynamodb_ = boto3.resource('dynamodb')

def storesHandler(event, context):
    print(event)
    
    #TABLE_NAME = os.environ['STORES_TABLE']
    #stores_table = dynamodb_.Table(TABLE_NAME)
    store = None
    BUYITNOW_TABLE_NAME = os.environ['BUYITNOW_TABLE']
    buyitnow_table = dynamodb_.Table(BUYITNOW_TABLE_NAME)
    PK = None
    SK = None
    if event["pathParameters"] != None:
        store = event["pathParameters"]["store"]
        #PK = "store_"+store
        #SK = store
        PK = "stores"
        SK = store

    if event["httpMethod"] == "POST":
        data = json.loads(event["body"])
        #PK = "store_"+data["id"]
        #SK = data["id"]
        PK = "stores"
        SK = data["id"]

        #stores_table.put_item(
        #        Item={
        #            "id": data["id"],
        #            "name": data["name"],
        #            "address": data["address"],
        #        })

        #client.put_item(TableName=TABLE_NAME,
        #        Item={
        #            "id": {"S": data["id"]},
        #            "name": {"S": data["name"]},
        #            "address": {"S": data["address"]},
        #        })
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
        #data = stores_table.get_item(Key={"id": store})
        #data = client.get_item(TableName=TABLE_NAME, Key={"id": {"S": store}})
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
        #data = stores_table.scan()
        #data = client.scan(TableName=TABLE_NAME)
        #data = buyitnow_table.scan()
        data = buyitnow_table.query(KeyConditionExpression=
                                    boto3.dynamodb.conditions.Key('PK')
                                    .eq('stores'))
        items = data["Items"]
        response = {
            "statusCode": 200,
            "body": json.dumps(items)
        }
    return response