import requests
from apps.payments.gateways.smobilpay.models.payment_status_model import (
    PaymentStatusModel,
)
from apps.payments.gateways.smobilpay.s3_api_auth import S3ApiAuth
from apps.payments.gateways.smobilpay.configuration import (
    Configuration,
)  # Import the configuration class
import logging

# Setup basic configuration for logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class PaymentStatusService:
    def __init__(self, public_token=None, secret_key=None):
        self.config = Configuration()  # Create a configuration instance
        self.public_token = public_token if public_token else self.config.get_api_key()
        self.secret_key = secret_key if secret_key else self.config.get_api_secret()
        self.api_version = self.config.api_version
        self.base_url = f"{self.config.get_api_url()}/verifytx"
        self.api_auth = S3ApiAuth(self.base_url, self.public_token, self.secret_key)

    def fetch_payment_status(self, ptn=None, trid=None):
        if not ptn and not trid:
            logging.error("PTN or TRID must be provided.")
            return "PTN or TRID must be provided."

        params = {}
        if ptn:
            params["ptn"] = ptn
        if trid:
            params["trid"] = trid

        headers = {
            "Authorization": self.api_auth.create_authorization_header("GET", params),
            "x-api-version": self.api_version,
        }

        return self._make_request(params, headers)

    def _make_request(self, params, headers):
        try:
            response = requests.get(self.base_url, headers=headers, params=params)
            if response.status_code == 200:
                try:
                    payment_status = response.json()
                    return [PaymentStatusModel(**status) for status in payment_status]
                except KeyError as e:
                    logging.error(f"Key error during model instantiation: {str(e)}")
                    return f"Data parsing error: {str(e)}"
            elif response.status_code == 401:
                logging.error(f"Authentication failed: {response.text}")
                return "Request could not be authenticated."
            else:
                logging.error(
                    f"Unexpected status {response.status_code}: {response.text}"
                )
                return f"An unexpected error occurred with status code: {response.status_code}"
        except requests.RequestException as e:
            logging.error(f"Network error occurred: {str(e)}")
            return f"Network error occurred: {str(e)}"
