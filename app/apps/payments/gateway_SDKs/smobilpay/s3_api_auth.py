import os
import hmac
import hashlib
import base64
from urllib import parse
import secrets
import time
import requests
import uuid


class HMACSignature:
    def __init__(self, method, url, params):
        self.method = method
        self.url = url
        self.params = params

    def generate(self, secret):
        signature_raw = hmac.new(
            secret.encode(), self.get_base_string().encode(), hashlib.sha1
        ).digest()
        return base64.b64encode(signature_raw).decode()

    def get_base_string(self):
        glue = "&"
        # Sort the parameters
        sorted_params = sorted(self.params.items())
        # Construct the parameter string
        parameter_string = "&".join(
            f"{key}={str(value)}" for key, value in sorted_params
        )
        # Generate and return the base string
        return f"{self.method.upper()}{glue}{parse.quote(self.url, safe='-')}{glue}{parse.quote(parameter_string, safe='-')}"


class S3ApiAuth:
    def __init__(self, api_url, public_token, secret_key):
        self.api_url = api_url
        self.public_token = public_token
        self.secret_key = secret_key
        # Read the DEBUG flag from environment variables
        self.debug = os.getenv("SMOBIL_PAY_API_DEBUG", "False") == "True"

        if self.debug:
            print(f"Initialized API URL: {self.api_url}")
            print(f"Using public token: {self.public_token}")

    def timestamp(self):
        timestamp = str(int(time.time()))
        if self.debug:
            print(f"Generated Timestamp: {timestamp}")
        return timestamp

    def create_authorization_header(self, method, additional_params=None):
        timestamp = str(int(time.time()))
        # Ensure nonce is unique per request
        nonce = f"{timestamp}{uuid.uuid4().hex[:8]}"
        parameters = {
            "s3pAuth_nonce": nonce,
            "s3pAuth_signature_method": "HMAC-SHA1",
            "s3pAuth_timestamp": timestamp,
            "s3pAuth_token": self.public_token,
            **(additional_params if additional_params else {}),
        }
        signature_helper = HMACSignature(method, self.api_url, parameters)
        signature = signature_helper.generate(self.secret_key)
        auth_header = (
            f's3pAuth, s3pAuth_nonce="{nonce}", s3pAuth_signature="{signature}", '
            f's3pAuth_signature_method="HMAC-SHA1", s3pAuth_timestamp="{timestamp}", '
            f's3pAuth_token="{self.public_token}"'
        )
        if self.debug:
            print(f"Authorization Header: {auth_header}")
        return auth_header

    def make_request(self, method, additional_params=None, version="3.0.0"):
        full_url = f"{self.api_url}"
        if self.debug:
            print(f"Full API URL: {full_url}")

        headers = {
            "Authorization": self.create_authorization_header(
                method, additional_params
            ),
            "x-api-version": version,
            "Content-Type": "application/json",
        }

        try:
            response = requests.request(method, self.api_url, headers=headers)
            response.raise_for_status()  # Raises an HTTPError for bad responses
            return response
        except requests.HTTPError as http_err:
            if self.debug:
                print(f"HTTP error occurred: {http_err}")
            return {"error": str(http_err), "status_code": response.status_code}
        except Exception as err:
            if self.debug:
                print(f"An error occurred: {err}")
            return {"error": str(err)}
