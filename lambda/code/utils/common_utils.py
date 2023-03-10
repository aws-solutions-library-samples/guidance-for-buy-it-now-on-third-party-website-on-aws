import os
import json
import uuid
import requests
import boto3
from botocore.exceptions import ClientError
from aws_lambda_powertools import (
    Tracer,
    Logger
)
from http.cookies import SimpleCookie
from decimal import (
    Decimal,
    ROUND_HALF_UP
)
from utils.secret_utils import (
    get_or_create_secret
)

logger = Logger()
tracer = Tracer()


class NotFoundException(Exception):
    pass


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return json.JSONEncoder.default(self, obj)


@tracer.capture_method
def get_product(product_id):
    get_product_url = os.environ["GET_PRODUCT_URL"]
    logger.info(f'Product Url: {get_product_url}')
    # product_id_url = get_product_url+f"products/{product_id}"
    product_id_url = get_product_url+f"/{product_id}"
    logger.info(product_id_url)
    product = requests.get(product_id_url)
    if product != None:
        productJson = product.json()
        # logger.info(f"Type: {type(productJson)}")
        # logger.info(f"Len: {len(productJson)}")
        # logger.info(f"ID: {productJson['id']}")
        # logger.info(f"Prod ID: {productJson['id']['S']}")
    logger.info(f"JSON: {product.json()}")
    logger.info(f"TEXT: {product.text}")
    try:
        response = product.json()
    except KeyError:
        logger.warn("No product found with id %s", product_id)
        raise NotFoundException
    return response


@tracer.capture_method
def get_cart(cart_id, cart_url):
    logger.info(f'Cart Url: {cart_url}')
    encoded_cart_id = requests.utils.quote(cart_id)
    # cart_id_url = cart_url+f"carts/{encoded_cart_id}"
    cart_id_url = cart_url+f"/{encoded_cart_id}"
    logger.info(f'Cart ID URL: {cart_id_url}')
    cart = requests.get(cart_id_url)
    response = cart.json()
    logger.info(f"Cart Data: {response}")
    return response


@tracer.capture_method
def get_stores(stores_url):
    logger.info(f'Stores Url: {stores_url}')
    # all_stores_url = f"{stores_url}stores"
    # logger.info(f'All Stores URL: {all_stores_url}')
    # stores = requests.get(all_stores_url)
    logger.info(f'All Stores URL: {stores_url}')
    stores = requests.get(stores_url)
    response = stores.json()
    logger.info(f"Stores Data: {response}")
    return response


@tracer.capture_method
def add_customer(customer_url, customer, headers):
    logger.info(f"Customer URL: {customer_url}, Customer: {customer}")
    response = None
    if isGuest(headers):
        logger.info(f"User is 'guest'")
        response = requests.post(customer_url, json=customer)
    else:
        customer_id = get_user_id(headers)
        logger.info(f"User is '{customer_id}'")
        response = {"customer_id": customer_id}
    return response

# This method is used as a placeholder to get a valid user id
# based on the authentication method used.
#
# Example: If we use cognito, we could pass in the jwt token
# to this method that could be sent to the cognitojwt.decode() method
# to get the "sub" (globally unique ID for the user)


@tracer.capture_method
def get_user_id(headers):
    user_id = "guest"
    try:
        user_id = headers["Authorization"].value
    except:
        logger.info("Authorization not present. User 'guest' user")
    logger.info("Authorization: "+user_id)
    return user_id


@tracer.capture_method
def isGuest(headers):
    return "guest" == get_user_id(headers)


@tracer.capture_method
def validate_payment_appid_apptoken(secretsmanager_client, appid, apptoken):
    # Replace this will a valid API call to your 3P payment processor
    # to validate the payment and billing details
    app_id = get_or_create_secret(secretsmanager_client, appid)
    app_token = get_or_create_secret(secretsmanager_client, apptoken)
    logger.info(
        f"SECRET app_id[{appid}]: {app_id}, app_token[{apptoken}]: {app_token}")
    response = True
    return response


@tracer.capture_method
def create_3p_order(secretsmanager_client, payment, shipping, headers, create_order_url):
    # Replace this will a valid API call to your 3P payment processor
    # to validate the payment and billing details
    app_id = get_or_create_secret(secretsmanager_client, payment["app_id"])
    app_token = get_or_create_secret(
        secretsmanager_client, payment["app_token"])
    logger.info(
        f"SECRET app_id[{payment['app_id']}]: {app_id}, app_token[{payment['app_token']}]: {app_token}")
    json_body = {
       payment["app_id"]: app_id,
       payment["app_token"]: app_token,
       "shipping": shipping
    }
    logger.info(f"Order Body: {json_body}")
    logger.info(f"HEADERS {headers}")
    valid_header = None
    try:
        valid_header = {
            "place_order": headers["place_order"]
        }
    except KeyError:
        logger.info(f"Header is_valid not found")
    response = None
    logger.info(f"Valid Header: {valid_header}")
    if (valid_header):
        logger.info(f"header valid")
        response = requests.post(
            create_order_url, json=json_body, headers=valid_header)
        # response = requests.post(payment_processor_url, json=json_body, headers=headers)
    else:
        logger.info(f"header invalid")
        response = requests.post(create_order_url, json=json_body)

    response_json = response.json()
    logger.info(f"order response: {response_json}")
    return response_json


@tracer.capture_method
def pre_order(cart_id, headers, pre_order_url):
    json_body = {
       "cart_id": cart_id
    }
    logger.info(f"pre_order url: {pre_order_url}")
    logger.info(f"pre_order body: {json_body}")
    logger.info(f"HEADERS {headers}")
    response = None
    response = requests.post(pre_order_url, json=json_body)

    response_json = response.json()
    logger.info(f"pre_order payment response: {response_json}")
    return response_json


@ tracer.capture_method
def validate_payment(secretsmanager_client, payment, headers, payment_processor_url):
    # Replace this will a valid API call to your 3P payment processor
    # to validate the payment and billing details
    app_id = get_or_create_secret(secretsmanager_client, payment["app_id"])
    app_token = get_or_create_secret(
        secretsmanager_client, payment["app_token"])
    logger.info(
        f"SECRET app_id[{payment['app_id']}]: {app_id}, app_token[{payment['app_token']}]: {app_token}")
    json_body = {
       payment["app_id"]: app_id,
       payment["app_token"]: app_token
    }
    logger.info(f"payment body: {json_body}")
    logger.info(f"HEADERS {headers}")
    valid_header = None
    try:
        valid_header = {
            "is_valid": headers["is_valid"]
        }
    except KeyError:
        logger.info(f"Header is_valid not found")
    response = None
    logger.info(f"Valid Header: {valid_header}")
    if (valid_header):
        logger.info(f"header valid")
        response = requests.post(payment_processor_url,
                               json=json_body, headers=valid_header)
        # response = requests.post(payment_processor_url, json=json_body, headers=headers)
    else:
        logger.info(f"header invalid")
        response = requests.post(payment_processor_url, json=json_body)

    response_json = response.json()
    logger.info(f"payment response: {response_json}")
    valid = response_json["valid"]
    return valid


@ tracer.capture_method
def is_payment_valid(secretsmanager_client, payment, headers, payment_processor_url):
    payment_response = validate_payment(
        secretsmanager_client, payment, headers, payment_processor_url)
    return payment_response


@ tracer.capture_method
def is_payment_valid_appid_apptoken(secretsmanager_client, appid, apptoken):
    payment_response = validate_payment_appid_apptoken(
        secretsmanager_client, appid, apptoken)
    return payment_response


@ tracer.capture_method
def get_partial_cart_id(cart_id):
    partial_cart_id = cart_id.split("#")[-1]
    logger.info("Partial Cart Id: "+partial_cart_id)
    return partial_cart_id

@ tracer.capture_method
def get_cart_id(headers):
    try:
        cookie=SimpleCookie()
        cookie.load(headers["Cookie"])
        cart_id=cookie["cart_id"].value
        logger.info("Existing Cart Id: "+cart_id)
    except:
        cart_id=str(uuid.uuid4)
        logger.info("Generated Cart Id: "+cart_id)
    return cart_id

@ tracer.capture_method
def generate_customer_id():
    customer_id=uuid.uuid4().hex
    print(f"Generated Customer ID {customer_id}")
    return customer_id

@ tracer.capture_method
def get_mock_order_id():
    order_id=uuid.uuid4().hex
    print(f"order Id {order_id}")
    return order_id

@ tracer.capture_method
def multiply(value1, value2):
    total_price=Decimal(value1)*Decimal(value2)
    cents=Decimal('.01')
    money=total_price.quantize(cents, ROUND_HALF_UP)
    return money


@ tracer.capture_method
def generate_header(cart_id):
    headers={}
    cookie=SimpleCookie()
    cookie["cart_id"]=cart_id
    headers["Set-Cookie"]=cookie["cart_id"].OutputString()
    return headers

@ tracer.capture_method
def send_email(sender, receiver, subject, html_content, text_content, charset):
    ses_client=boto3.client('ses')
    # ses_client.grant
    # Try to send the email.
    try:
        # Provide the contents of the email.
        response=ses_client.send_email(
            Destination = {
                'ToAddresses': [
                    receiver,
                ],
            },
            Message = {
                'Body': {
                    'Html': {
                        'Charset': charset,
                        'Data': html_content,
                    },
                    'Text': {
                        'Charset': charset,
                        'Data': text_content,
                    },
                },
                'Subject': {
                    'Charset': charset,
                    'Data': subject,
                },
            },
            Source = sender,
        )
    # Display an error if something goes wrong.
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        logger.info(f"Email sent! Message ID: {response['MessageId']}"),
        logger.info(f"Response: {response}")
        return response
    return None

@ tracer.capture_method
def send_templated_email(sender, receiver, template_name, template_data):
    ses_client=boto3.client('ses')
    # ses_client.grant
    # Try to send the email.
    try:
        logger.info(f"Sender: {sender}")
        logger.info(f"Receiver: {receiver}")
        logger.info(f"Template name: {template_name}")
        logger.info(f"Template data: {template_data}")
        # Provide the contents of the email.
        response=ses_client.send_templated_email(Source = sender,
            Destination = {
                'ToAddresses': [
                    receiver,
                ],
            },
            Template = template_name,
            TemplateData = template_data
        )
        # response = ses_client.send_templated_email(Source='vjprince@amazon.com',
        #    Destination={
        #        'ToAddresses': [
        #            'vjprince@amazon.com',
        #        ],
        #    },
        #    Template='OrderEmailConfirmation',
        #    TemplateData='{ \"order_id\":\"795e0d9e53bb4925a0ea6ff0fa0dcaf2\", \"customer_id\":\"10001\" }'
        # )
        logger.info(f"Email response: {response}")
    # Display an error if something goes wrong.
    except ClientError as e:
        logger.info(f"Email Exception: {e}")
    # Display an error if something goes wrong.
        print(e.response['Error']['Message'])
    else:
        logger.info(f"Email sent! Message ID: {response['MessageId']}"),
        logger.info(f"Response: {response}")
        return response
    return None
