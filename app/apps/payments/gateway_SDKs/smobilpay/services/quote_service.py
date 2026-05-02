import requests
from apps.payments.gateway_SDKs.smobilpay.models.quote_model import QuoteModel
from apps.payments.gateway_SDKs.smobilpay.s3_api_auth import S3ApiAuth
from apps.payments.gateway_SDKs.smobilpay.configuration import (
    Configuration,
)  # Import the configuration class
import logging


class QuoteService:
    def __init__(self, public_token=None, secret_key=None):
        self.config = Configuration()  # Create a configuration instance
        self.public_token = public_token if public_token else self.config.get_api_key()
        self.secret_key = secret_key if secret_key else self.config.get_api_secret()
        self.api_version = self.config.api_version
        self.base_url = f"{self.config.get_api_url()}/quotestd"
        self.api_auth = S3ApiAuth(self.base_url, self.public_token, self.secret_key)

        logging.debug(f"Service initialized with base URL: {self.base_url}")

    def request_quote(self, payment_item_id, amount):
        payload = {"amount": amount, "payItemId": payment_item_id}
        headers = {
            "Authorization": self.api_auth.create_authorization_header("POST", payload),
            "x-api-version": self.api_version,
            "Content-Type": "application/json",
        }
        logging.debug(f"Requesting quote with payload: {payload}")
        return self._make_request(payload, headers)

    def _make_request(self, payload, headers):
        try:
            response = requests.post(self.base_url, headers=headers, json=payload)
            logging.debug(f"Received response status: {response.status_code}")
            if response.status_code == 200:
                quote_data = response.json()
                return QuoteModel(**quote_data)
            elif response.status_code == 401:
                logging.error("Request could not be authenticated: %s", response.text)
                return "Request could not be authenticated."
            else:
                logging.error(
                    "An error occurred with status code: %s and payload %s",
                    response.status_code,
                    response.content,
                )
                return "An unexpected error occurred."
        except requests.RequestException as e:
            logging.error("Network error occurred: %s", str(e))
            return f"Network error occurred: {str(e)}"
