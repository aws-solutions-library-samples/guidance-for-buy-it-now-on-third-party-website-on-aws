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
logger = Logger()
tracer = Tracer()

@tracer.capture_method
def get_or_create_secret(secretsmanager_client, name=None):
    secret_value = None
    secret_obj = None
    try:
        logger.info(f"Getting Secret for: {name}")
        secret_obj = get_secret_value(secretsmanager_client, name)
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            logger.error("The requested secret " + name + " was not found")
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            logger.error("The request was invalid due to:", e)
        elif e.response['Error']['Code'] == 'InvalidParameterException':
            logger.error("The request had invalid params:", e)
        elif e.response['Error']['Code'] == 'DecryptionFailure':
            logger.error("The requested secret can't be decrypted using the provided KMS key:", e)
        elif e.response['Error']['Code'] == 'InternalServiceError':
            logger.error("An error occurred on service side:", e)
    if secret_obj == None:
        logger.info(f"Creating Secret for: {name}")
        create(secretsmanager_client, name, get_random_password(secretsmanager_client, 20))
        secret_obj = get_secret_value(secretsmanager_client, name, None)

    if secret_obj != None:
        secret_value = secret_obj['SecretString']
    logger.info(f"Secret '{name}' has value '{secret_value}'")
    return secret_value


@tracer.capture_method
def get_secret_value(secretsmanager_client, name=None, stage=None):
    """
    Gets the value of a secret.
    :param name: The name of the secret to retrieve. If this is None, the
                 an error is thrown
    :param stage: The stage of the secret to retrieve. If this is None, the
                  current stage is retrieved.
    :return: The value of the secret. When the secret is a string, the value is
             contained in the `SecretString` field. When the secret is bytes,
             it is contained in the `SecretBinary` field.
    """
    if name is None:
        raise ValueError

    try:
        kwargs = {'SecretId': name}
        if stage is not None:
            kwargs['VersionStage'] = stage
        response = secretsmanager_client.get_secret_value(**kwargs)
        logger.info("Got value for secret %s.", name)
    except ClientError:
        logger.exception("Couldn't get value for secret %s.", name)
        raise
    else:
        return response

@tracer.capture_method
def get_random_password(secretsmanager_client, pw_length):
        """
        Gets a randomly generated password.
        :param pw_length: The length of the password.
        :return: The generated password.
        """
        try:
            response = secretsmanager_client.get_random_password(
                PasswordLength=pw_length)
            password = response['RandomPassword']
            logger.info("Got random password.")
        except ClientError:
            logger.exception("Couldn't get random password.")
            raise
        else:
            return password

@tracer.capture_method
def create(secretsmanager_client, name, secret_value):
        """
        Creates a new secret. The secret value can be a string or bytes.
        :param name: The name of the secret to create.
        :param secret_value: The value of the secret.
        :return: Metadata about the newly created secret.
        """
        try:
            kwargs = {'Name': name}
            if isinstance(secret_value, str):
                kwargs['SecretString'] = secret_value
            elif isinstance(secret_value, bytes):
                kwargs['SecretBinary'] = secret_value
            response = secretsmanager_client.create_secret(**kwargs)
            logger.info("Created secret %s.", name)
        except ClientError:
            logger.exception("Couldn't get secret %s.", name)
            raise
        else:
            return response