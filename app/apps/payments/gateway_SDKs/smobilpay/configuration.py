import os
from dotenv import load_dotenv
import logging

class Configuration:
    def __init__(self):
        # Initialize logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

        # Load environment variables
        load_dotenv()

        # Enable debug mode based on environment variable
        self.debug_mode = os.getenv('SMOBIL_PAY_API_DEBUG', 'False').lower() == 'true'
        if self.debug_mode:
            logging.getLogger().setLevel(logging.DEBUG)  # Set logging to debug level if debug mode is enabled

        # Setting up configurations from environment variables
        self.live_mode = os.getenv('SMOBIL_PAY_LIVE_MODE', 'True').lower() == 'true'
        self.base_url = os.getenv('SMOBIL_PAY_API_URL_STAGING') if not self.live_mode else os.getenv('SMOBIL_PAY_API_URL')
        self.api_version = os.getenv('SMOBIL_PAY_API_VERSION', '3.0.0')

        # Log the mode of operation and debug status
        logging.info(f"Configuration initialized in {'live' if self.live_mode else 'staging'} mode.")
        logging.debug(f"Debug mode is {'enabled' if self.debug_mode else 'disabled'}.")

        # Ensure required environment variables are set
        self._validate_environment()

    def get_api_key(self):
        key = os.getenv('SMOBIL_PAY_API_KEY')
        logging.debug(f"API Key retrieved: {key}")
        return key

    def get_api_secret(self):
        secret = os.getenv('SMOBIL_PAY_API_SECRET')
        logging.debug(f"API Secret retrieved: {secret}")
        return secret

    def get_api_url(self):
        logging.debug(f"API URL retrieved: {self.base_url}")
        return self.base_url

    def _validate_environment(self):
        required_vars = ['SMOBIL_PAY_API_KEY', 'SMOBIL_PAY_API_SECRET', 'SMOBIL_PAY_API_URL']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            error_message = f"Missing required environment variables: {', '.join(missing_vars)}"
            logging.error(error_message)
            raise EnvironmentError(error_message)
