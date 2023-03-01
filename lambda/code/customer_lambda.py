import json
import os
import uuid

import boto3

client = boto3.client('dynamodb')
dynamodb_ = boto3.resource('dynamodb')

def customerHandler(event, context):
    print(event)
    
    TABLE_NAME = os.environ['CUSTOMER_TABLE']
    customers_table = dynamodb_.Table(TABLE_NAME)
    customer = None
    customer_id = None
    if event["pathParameters"] != None:
        customer = event["pathParameters"]["customer"]

    if event["httpMethod"] == "POST":
        print(f"CUSTOMER EVENT: {event['body']}")
        data = json.loads(event["body"])
        #customer = None
        #try:
        #    customer = data["customer"]
        #except KeyError:
        #    print(f"Customer Object not found")
        #if customer == None:
        try:
            customer_id = data["id"]
        except KeyError:
            print(f"No Customer ID. Generate a new ID")
            customer_id = uuid.uuid4().hex
        print(f"Customer ID: {customer_id}")
        #client.put_item(TableName=TABLE_NAME,
        #        Item={
        #            "id": {"S": customer_id},
        #            "name": {"S": data["name"]},
        #            "email": {"S": data["email"]},
        #            "address": {"S": data["address"]},
        #            "payment": {"BOOL": data["payment"]},
        #        })
        customers_table.put_item(
            Item={
                "id": customer_id,
                "name": data["name"],
                "email": data["email"],
                "address": data["address"],
                "payment": data.get("payment", None),
                "store_loyalty": data.get("store_loyalty", None), # List item containing store_id and loyalty_id
            })
        #else:
        #    try:
        #        customer_id = customer["id"]
        #    except KeyError:
        #        print(f"No Customer ID. Generate a new ID")
        #        customer_id = uuid.uuid4().hex
        #    print(f"Customer ID is {customer_id}")
        #    customers_table.put_item(
        #        Item={
        #            "id": customer_id,
        #            "name": customer["name"],
        #            "email": customer["email"],
        #            "address": customer["address"],
        #            "payment": customer["payment"],
        #            "store_loyalty": customer["store_loyalty"], # List item containing store_id and loyalty_id
        #        })
        response = {
            'statusCode': 200,
            'body': json.dumps({"customer_id":customer_id})
        }
    elif event["httpMethod"] == "GET" and customer != None:
        data = client.get_item(TableName=TABLE_NAME, Key={"id": {"S": customer}})
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
                "body": json.dumps('Customer Id not available')
            }

    elif event["httpMethod"] == "GET" and customer == None:
        data = client.scan(TableName=TABLE_NAME)
        items = data["Items"]
        response = {
            "statusCode": 200,
            "body": json.dumps(items)
        }
    return response