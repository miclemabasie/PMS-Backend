import requests
from apps.payments.gateways.smobilpay.models.ping_model import PingModel
from apps.payments.gateways.smobilpay.s3_api_auth import S3ApiAuth
from apps.payments.gateways.smobilpay.configuration import (
    Configuration,
)  # Import the configuration class
import logging

# Setup basic configuration for logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class PingService:
    def __init__(self, public_token=None, secret_key=None):
        config = Configuration()  # Create a configuration instance
        public_token = public_token if public_token else config.get_api_key()
        secret_key = secret_key if secret_key else config.get_api_secret()

        # Set up API authentication and version
        self.full_url = f"{config.get_api_url()}/ping"
        self.api_auth = S3ApiAuth(self.full_url, public_token, secret_key)
        self.api_version = config.api_version

    def ping(self):
        headers = {
            "Authorization": self.api_auth.create_authorization_header("GET"),
            "x-api-version": self.api_version,
        }
        try:
            response = requests.get(self.full_url, headers=headers)
            if response.status_code == 200:
                return PingModel(**response.json())
            elif response.status_code == 401:
                logging.error("Authentication failed: %s", response.text)
                return PingModel(error="Request could not be authenticated.")
            else:
                logging.error("Failed to ping: %s", response.text)
                return PingModel(error="An error occurred.")
        except requests.RequestException as e:
            logging.error("Network error occurred: %s", str(e))
            return PingModel(error=f"Network error occurred: {str(e)}")
