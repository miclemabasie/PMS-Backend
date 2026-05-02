import requests
from apps.payments.gateway_SDKs.smobilpay.models.account_model import AccountModel
from apps.payments.gateway_SDKs.smobilpay.s3_api_auth import S3ApiAuth
from apps.payments.gateway_SDKs.smobilpay.configuration import (
    Configuration,
)  # Import the configuration class
import logging

# Setup basic configuration for logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class AccountService:
    def __init__(self, public_token=None, secret_key=None):
        self.config = Configuration()  # Create a configuration instance
        self.public_token = public_token if public_token else self.config.get_api_key()
        self.secret_key = secret_key if secret_key else self.config.get_api_secret()
        self.api_version = self.config.api_version
        self.base_url = f"{self.config.get_api_url()}/account"
        self.api_auth = S3ApiAuth(self.base_url, self.public_token, self.secret_key)

    def fetch_account_info(self):
        headers = {
            "Authorization": self.api_auth.create_authorization_header("GET"),
            "x-api-version": self.api_version,
        }
        return self._make_request(headers)

    def _make_request(self, headers):
        try:
            response = requests.get(self.base_url, headers=headers)
            if response.status_code == 200:
                account_data = response.json()
                return AccountModel(**account_data)
            elif response.status_code == 401:
                logging.error("Request could not be authenticated: %s", response.text)
                return "Request could not be authenticated."
            else:
                logging.error(
                    "An unexpected error occurred with status code: %s",
                    response.status_code,
                )
                return "An unexpected error occurred."
        except requests.RequestException as e:
            logging.error("Network error occurred: %s", str(e))
            return f"Network error occurred: {str(e)}"
