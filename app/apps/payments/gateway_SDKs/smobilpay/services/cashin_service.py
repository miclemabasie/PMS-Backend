import requests
from typing import List
from apps.payments.gateway_SDKs.smobilpay.models.cashin_model import CashinModel
from apps.payments.gateway_SDKs.smobilpay.s3_api_auth import S3ApiAuth
from apps.payments.gateway_SDKs.smobilpay.configuration import (
    Configuration,
)  # Import the configuration class
import logging

# Setup basic configuration for logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class CashinService:
    def __init__(self, public_token=None, secret_key=None):
        self.config = Configuration()  # Create a configuration instance
        self.public_token = public_token if public_token else self.config.get_api_key()
        self.secret_key = secret_key if secret_key else self.config.get_api_secret()
        self.api_version = self.config.api_version
        self.base_url = f"{self.config.get_api_url()}/cashin"
        self.api_auth = S3ApiAuth(self.base_url, self.public_token, self.secret_key)

    def fetch_cashins(self, service_id: int = None):
        params = {"serviceid": service_id} if service_id is not None else {}
        headers = {
            "Authorization": self.api_auth.create_authorization_header("GET", params),
            "x-api-version": self.api_version,
        }
        return self._make_request(params, headers)

    def _make_request(self, params, headers):
        try:
            response = requests.get(self.base_url, headers=headers, params=params)
            if response.status_code == 200:
                cashins_data = response.json()
                return [CashinModel(**cashin) for cashin in cashins_data]
            elif response.status_code == 401:
                logging.error("Request could not be authenticated: %s", response.text)
                return "Request could not be authenticated."
            else:
                logging.error(
                    "An error occurred with status code: %s and payload %s",
                    response.status_code,
                    response.content,
                )
                return "An error occurred."
        except requests.RequestException as e:
            logging.error("Network error occurred: %s", str(e))
            return f"Network error occurred: {str(e)}"
