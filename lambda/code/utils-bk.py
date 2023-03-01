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
    product_id_url = get_product_url+f"products/{product_id}"
    logger.info(product_id_url)
    product = requests.get(product_id_url)
    if product != None:
        productJson = product.json()
        logger.info(f"Type: {type(productJson)}")
        logger.info(f"Len: {len(productJson)}")
        logger.info(f"ID: {productJson['id']}")
        logger.info(f"Prod ID: {productJson['id']['S']}")
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
    cart_id_url = cart_url+f"carts/{encoded_cart_id}"
    logger.info(f'Cart ID URL: {cart_id_url}')
    cart = requests.get(cart_id_url)
    response = cart.json()
    logger.info(f"Cart Data: {response}")
    return response

@tracer.capture_method
def get_stores(stores_url):
    logger.info(f'Stores Url: {stores_url}')
    all_stores_url = f"{stores_url}stores"
    logger.info(f'All Stores URL: {all_stores_url}')
    stores = requests.get(all_stores_url)
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
        response = {"customer_id":customer_id}
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
def validate_payment(payment):
    # Replace this will a valid API call to your 3P payment processor
    # to validate the payment and billing details
    response = True
    return response

@tracer.capture_method
def is_payment_valid(payment):
    payment_response = validate_payment(payment) 
    return payment_response

@tracer.capture_method
def get_cart_id(headers):
    try:
        cookie = SimpleCookie()
        cookie.load(headers["Cookie"])
        cart_id = cookie["cart_id"].value
        logger.info("Existing Cart Id: "+cart_id)
    except:
        cart_id = str(uuid.uuid4)
        logger.info("Generated Cart Id: "+cart_id)
    return cart_id

@tracer.capture_method
def get_order_id():
    order_id = uuid.uuid4().hex
    print(f"order Id {order_id}")
    return order_id

@tracer.capture_method
def multiply(value1,value2):
    total_price = Decimal(value1)*Decimal(value2)
    cents = Decimal('.01')
    money = total_price.quantize(cents, ROUND_HALF_UP)
    return money


@tracer.capture_method
def generate_header(cart_id):
    headers = {}
    cookie = SimpleCookie()
    cookie["cart_id"] = cart_id
    headers["Set-Cookie"] = cookie["cart_id"].OutputString()
    return headers

@tracer.capture_method
def send_email(sender,receiver,subject,html_content, text_content, charset):
    ses_client = boto3.client('ses')
    #ses_client.grant
    # Try to send the email.
    try:
        #Provide the contents of the email.
        response = ses_client.send_email(
            Destination={
                'ToAddresses': [
                    receiver,
                ],
            },
            Message={
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
            Source=sender,
        )
    # Display an error if something goes wrong.	
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        logger.info(f"Email sent! Message ID: {response['MessageId']}"),
        logger.info(f"Response: {response}")
        return response
    return None