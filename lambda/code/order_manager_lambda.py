import json
import os
import uuid

import boto3
from boto3.dynamodb.conditions import Key
from utils.common_utils import (
    DecimalEncoder,
    add_customer,
    is_payment_valid,
    is_payment_valid_appid_apptoken,
    get_mock_order_id,
    send_email,
    send_templated_email,
    create_3p_order,
    get_user_id,
    get_cart_id
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
#secretsmanager_client = boto3.client('secretsmanager')
session = boto3.session.Session()
secretsmanager_client = session.client(
    service_name='secretsmanager',
    region_name=session.region_name
)

@tracer.capture_lambda_handler
def orderManagerHandler(event, context):
    print(event)
    
    #CUSTOMER_URL = os.environ['CUSTOMER_URL']
    #ORDERS_TABLE = os.environ['ORDERS_TABLE']
    PAYMENT_GATEWAY = os.environ['PAYMENT_GATEWAY']
    ORDER_GATEWAY = os.environ['ORDER_GATEWAY']
    EMAIL_TEMPLATE_NAME = os.environ['EMAIL_TEMPLATE_NAME']
    VERIFIED_IDENTITY = os.environ['VERIFIED_IDENTITY']
    BUYITNOW_TABLE_NAME = os.environ['BUYITNOW_TABLE']
    buyitnow_table = dynamodb_.Table(BUYITNOW_TABLE_NAME)
    PK = None
    SK = None
    SK_PREORDER = "order#PREORDER"
    #APPID = os.environ['APPID']
    #APPTOKEN = os.environ['APPTOKEN']
    #orders_table = dynamodb_.Table(ORDERS_TABLE)

    logger.info(f"ORDER EVENT: {event}")

    step = None
    try:
        step = event["step"] 
    except KeyError:
        logger.info(f"Key Not found: event['step']")

    logger.info(f"STEP: {step}")
    if step == "failed":
        logger.info("Failure triggered")
        error_message = json.loads(event['error'])['errorMessage']
        logger.info(f"ERROR: {error_message}")
        cart_id = json.loads(error_message)['cart_id']
        logger.info(f"Failed Cart ID: {cart_id}")
        #error_message = json.dumps(error_message)
        #logger.info(f"Error message dump: {error_message}")
        #error_message = json.loads(error_message)
        #logger.info(f"Error message loads: {error_message}")
        #logger.info(f"Error message loads type: {type(error_message)}")
        #logger.info(f"Error Cart ID: {json.loads(error_message)}")
        #logger.info(f"Error Cart ID: {json.loads(error_message)['cart_id']}")
        #logger.info(f"Error Cart ID: {json.loads(event['error'])['errorMessage']['body']['cart_id']}")
        PK = cart_id
        SK = SK_PREORDER
        buyitnow_table.update_item(
            Key={'PK': PK, 'SK': SK},
            ExpressionAttributeNames={
                "#order_status": "status",
            },
            UpdateExpression="SET #order_status=:os",
            ExpressionAttributeValues={
                ':os': 'FAILED'},
            ReturnValues="UPDATED_NEW")
        response = {
            'statusCode': 200,
            'body': "Order Failed, cleanup completed"
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
    customer.update({"store_loyalty": [{"store_id": store_id, "loyalty_id": loyalty_id}]})
    print(f"Cart ID: {cart_id}, Store ID: {store_id}")
    #print(f"Cart ID: {cart_id}, Store ID: {store_id}, CUSTOMER_URL: {CUSTOMER_URL}")
    header = None
    try:
        header = event["header"]
    except KeyError:
        logger.info("No header available")
    if step == "start":
        # Create pre-order
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
        response = {
            'body': event["body"],
            'header': header,
            'cart_id': cart_id,
        }
        return response
    if step == "validate":
        logger.info(f"payment gateway url: {PAYMENT_GATEWAY}")
        payment_valid = is_payment_valid(secretsmanager_client, payment, header, PAYMENT_GATEWAY)
        #payment_valid = is_payment_valid_appid_apptoken(secretsmanager_client, APPID, APPTOKEN)
        logger.info(f"Payment {payment_valid}")
        response = {
            'body': event["body"],
            'header': header,
            'cart_id': cart_id,
            'payment_valid': "SUCCEEDED" if payment_valid else "FAILED"
        }
        #if not payment_valid: raise Exception(json.dumps({"cart_id":cart_id}))
        if not payment_valid: raise Exception(json.dumps(response))
        return response
    if step == "add_customer":
        #add_cust_response = add_customer(CUSTOMER_URL, customer, header)
        #customer_response = add_cust_response.json()
        #logger.info(f"Customer Response: {customer_response}")
        #customer_id = None
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
        #buyitnow_table.put_item(
        #    Item={
        #        "PK": cart_id,
        #        "id": customer_id,
        #        "name": data["name"],
        #        "email": data["email"],
        #        "address": data["address"],
        #        "payment": data.get("payment", None),
        #        "store_loyalty": data.get("store_loyalty", None), # List item containing store_id and loyalty_id
        #    })
        #try:
        #    customer_id = customer_response["customer_id"]
        #except KeyError:
        #    logger.info(f"Customer Id not available")
        #logger.info(f"Customer ID: {customer_id}")
        response = {
            'body': event["body"],
            'header': header,
            'customer_id': customer_id,
        }
        return response
    if step == "create_order":
        # Create Order
        # API Gateway can mock the rest call
        #order_id = get_mock_order_id()
        order_response = create_3p_order(secretsmanager_client, payment, shipping, header, ORDER_GATEWAY)
        order_placed = order_response["order_placed"]
        logger.info(f"Order Placed: {order_placed}")
        PK = cart_id
        #user_id = get_user_id(event["header"])
        #SK = "userid#"+user_id
        if order_placed :
            order_id = order_response["order_id"]
            logger.info(f"Order ID: {order_id}")
            ##orders_table.put_item(
            ##    Item={
            ##        "order_id": order_id,
            ##        "customer_id": event["customer_id"],
            ##        "cart_id": cart_id,
            ##    })
            #SK = "order#"+order_id
            #buyitnow_table.update_item(
            #    Key={'PK': PK, 'SK': SK},
            #    ExpressionAttributeNames={
            #        "#order_id": "id",
            #        "#order_status": "status",
            #    },
            #    UpdateExpression="SET #order_id=:oi, #order_status=:os",
            #    ExpressionAttributeValues={
            #        ':oi': order_id, ':os': 'PLACED'},
            #    ReturnValues="UPDATED_NEW")
            #SK = SK_PREORDER
            #buyitnow_table.delete_item(Key={"PK": PK, "SK": SK})
            #sub_cart_id = get_cart_id(event["header"])
            #SK = "userid#"+sub_cart_id
            #buyitnow_table.update_item(
            #    Key={'PK': PK, 'SK': SK},
            #    ExpressionAttributeNames={
            #        "#cart_status": "status",
            #    },
            #    UpdateExpression="SET #cart_status=:cs",
            #    ExpressionAttributeValues={
            #        ':cs': 'CLOSED'},
            #    ReturnValues="UPDATED_NEW")
            response = {
                'body': event["body"],
                'header': header,
                'customer_id': event["customer_id"],
                'order_id': order_id,
                'order_placed': "SUCCEEDED" if order_placed else "FAILED"
            }
        else :
            response = {
                'body': event["body"],
                'header': header,
                'customer_id': event["customer_id"],
                'order_placed': "SUCCEEDED" if order_placed else "FAILED"
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
        sub_cart_id = get_cart_id(event["header"])
        SK = "cart#"+sub_cart_id
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
            'order_id': event["order_id"]
        }
        return response
    if step == "send_email":
        topic = "BuyitNowOrder"
        sns_topic_arn = "".join([tp['TopicArn'] for tp in sns.list_topics()['Topics'] if topic in tp['TopicArn']])
        status = "SUCCEEDED"
        message = "Unexpected error message"
        subject = "Unexpected subject"
        try:
            status = event["status"] 
        except KeyError:
            logger.info(f"Key Not found: event['status']")
        if(status == "SUCCEEDED"):
            subject = "Order successfull"
            message = ("Order successfully placed \r\n\n"
                         f"Order ID: {event['order_id']}\n"
                         f"Customer Name: {event['body']['customer']['name']}\n"
                         f"Customer ID: {event['customer_id']}\n"
                        )
        else:
            subject = "Order failed"
            message = "The order could not be placed"
        sns.publish(TopicArn=sns_topic_arn, Message=message, Subject=subject)
        response = {
            'statusCode': 200,
            'order_status': status,
            'body': "SNS confirmation email sent"
        }
        return response
        ## The email body for recipients with non-HTML email clients.
        #BODY_TEXT = ("Order successfully placed \r\n"
        #             f"Order ID: {event['order_id']}\n"
        #             f"Customer Name: {event['body']['customer']['name']}\n"
        #             f"Customer ID: {event['customer_id']}\n"
        #            )

        ## The HTML body of the email.
        #BODY_HTML = f"""<html>
        #<head></head>
        #<body>
        #  <h1>Order successfully placed</h1>
        #  <p>
        #  Order ID: {event['order_id']}<br>
        #  Customer Name: {event['body']['customer']['name']}<br>
        #  Customer ID: {event['customer_id']}<br>
        #  </p>
        #</body>
        #</html>
        #    """            
        #template_data = {"order_id": event['order_id'], "customer_id": event['customer_id'], "customer_name": event['body']['customer']['name']}
        ##template_data = "{\"order_id\": \""+event['order_id']+"\", \"customer_id\": \""+event['customer_id']+"\"}"
        #logger.info(f"Template Data: {template_data}")
        #logger.info(f"Template Data String: {json.dumps(template_data)}")
        ##logger.info(f"Template Data String: {template_data}")
        #email_response = send_templated_email(sender=VERIFIED_IDENTITY, 
        #    receiver=VERIFIED_IDENTITY, 
        #    template_name=EMAIL_TEMPLATE_NAME, 
        #    template_data=json.dumps(template_data))
        ##email_response = send_templated_email("vjprince@amazon.com","vjprince@amazon.com", EMAIL_TEMPLATE_NAME, template_data=json.dumps(template_data))
        ##email_response = send_templated_email("vjprince@amazon.com","vjprince@amazon.com", EMAIL_TEMPLATE_NAME, template_data=template_data)
        ##email_response = send_email("vjprince@amazon.com","vjprince@amazon.com","Order placed", html_content=BODY_HTML, text_content=BODY_TEXT, charset="UTF-8")
        #if email_response != None:
        #    logger.info(f"Order Response Metadata: {email_response}")
        #    response = {
        #        'order_status': "SUCCEEDED" if email_response["ResponseMetadata"]["HTTPStatusCode"] == 200 else "FAILED"
        #    }
        #else:
        #    response = {
        #        'order_status': "FAILED"
        #    }
        #logger.info(f"Order Email Status: {response}")
        #return response
    response = {
        'statusCode': 200,
        'body': json.dumps("Step was missing")
    }
    return response
