from pathlib import Path

import environ

env = environ.Env(DEBUG=(bool, False))
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

environ.Env.read_env(BASE_DIR / ".env")


CLOUDFLARE_R2_CONFIG_OPTIONS = {}

bucket_name = env("CLOUDFLARE_R2_BUCKET")
endpoint_url = env("CLOUDFLARE_R2_BUCKET_ENDPOINT")
access_key = env("CLOUDFLARE_R2_ACCESS_KEY")
secret_key = env("CLOUDFLARE_R2_SECRET_KEY")
security_token = env("CLOUDFLARE_R2_TOKEN")

if all([bucket_name, endpoint_url, access_key, secret_key, security_token]):
    CLOUDFLARE_R2_CONFIG_OPTIONS = {
        "bucket_name": env("CLOUDFLARE_R2_BUCKET"),
        "default_acl": None,  # "private"
        "signature_version": "s3v4",
        "endpoint_url": env("CLOUDFLARE_R2_BUCKET_ENDPOINT"),
        "access_key": env("CLOUDFLARE_R2_ACCESS_KEY"),
        "secret_key": env("CLOUDFLARE_R2_SECRET_KEY"),
    }
