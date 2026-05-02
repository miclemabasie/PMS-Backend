import requests
from apps.payments.gateway_SDKs.smobilpay.s3_api_auth import S3ApiAuth
from apps.payments.gateway_SDKs.smobilpay.configuration import Configuration
import logging
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


@dataclass
class VerificationResult:
    is_valid: bool


class ServiceNumberVerificationApi:
    def __init__(self, public_token=None, secret_key=None):
        self.config = (
            Configuration()
        )  # Create and configure instance from environment variables
        self.public_token = public_token or self.config.get_api_key()
        self.secret_key = secret_key or self.config.get_api_secret()
        self.api_version = self.config.api_version
        self.base_url = f"{self.config.get_api_url()}/verify"
        self.api_auth = S3ApiAuth(
            self.base_url, self.public_token, self.secret_key
        )  # Instantiate API auth

    def verify_service_number(self, merchant, service_id: int, service_number):
        params = {
            "merchant": merchant,
            "serviceid": service_id,
            "serviceNumber": service_number,
        }
        headers = {
            "Authorization": self.api_auth.create_authorization_header("GET", params),
            "x-api-version": self.api_version,
        }
        return self._make_request(params, headers)

    def _make_request(self, params, headers):
        try:
            response = requests.get(self.base_url, headers=headers, params=params)
            if response.status_code == 200:
                # Convert response JSON to VerificationResult assuming the response structure is {'is_valid': bool}
                result_data = response.json()
                return VerificationResult(is_valid=result_data.get("is_valid"))
            elif response.status_code == 401:
                logging.error("Request could not be authenticated: %s", response.text)
                return "Request could not be authenticated."
            else:
                logging.error(
                    "An error occurred: %s, Status Code: %s",
                    response.text,
                    response.status_code,
                )
                return "An error occurred."
        except requests.RequestException as e:
            logging.error("Network error occurred: %s", str(e))
            return f"Network error occurred: {str(e)}"
