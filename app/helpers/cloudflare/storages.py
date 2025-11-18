import helpers.storages.mixins as mixins
from storages.backends.s3 import S3Storage


class CloudflareStorage(S3Storage):
    pass


class StaticFileStorage(mixins.DefaultACLMixin, CloudflareStorage):
    """
    For staticfiles
    """

    location = "staticfiles"
    default_acl = "public-read"


class MediaFileStorage(mixins.DefaultACLMixin, CloudflareStorage):
    """
    For general uploads
    """

    location = "mediafiles"
    default_acl = "public-read"


class ProtectedMediaStorage(mixins.DefaultACLMixin, CloudflareStorage):
    """
    For user private uploads
    """

    location = "protected"
    default_acl = "private"
