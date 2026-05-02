import requests
from apps.payments.gateway_SDKs.smobilpay.models.service_model import ServiceModel
from apps.payments.gateway_SDKs.smobilpay.s3_api_auth import S3ApiAuth
from apps.payments.gateway_SDKs.smobilpay.configuration import (
    Configuration,
)  # Import the configuration class
import logging

# Setup basic configuration for logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class ServiceApi:
    def __init__(self, public_token=None, secret_key=None):
        self.config = Configuration()  # Create a configuration instance
        self.public_token = public_token if public_token else self.config.get_api_key()
        self.secret_key = secret_key if secret_key else self.config.get_api_secret()
        self.api_version = self.config.api_version

    def fetch_services(self):
        url = f"{self.config.get_api_url()}/service"
        headers = self._prepare_headers(url)
        return self._make_request(url, headers, multiple=True)

    def fetch_service_by_id(self, service_id: int):
        url = f"{self.config.get_api_url()}/service/{service_id}"
        headers = self._prepare_headers(url)
        return self._make_request(url, headers, multiple=False)

    def _prepare_headers(self, url):
        api_auth = S3ApiAuth(url, self.public_token, self.secret_key)
        return {
            "Authorization": api_auth.create_authorization_header("GET"),
            "x-api-version": self.api_version,
        }

    def _make_request(self, url, headers, multiple=False):
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return self._parse_response(response.json(), multiple)
            elif response.status_code == 404:
                logging.error("Service not found for URL: %s", url)
                return "Service does not exist."
            elif response.status_code == 401:
                logging.error("Request could not be authenticated.")
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

    def _parse_response(self, data, multiple):
        if multiple:
            return [ServiceModel(**service) for service in data]
        else:
            return ServiceModel(**data)
