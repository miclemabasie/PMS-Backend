import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import TimeStampedUUIDModel
from apps.users.models import User

# ----------------------------------------------------------------------
# Documents and communication
# ----------------------------------------------------------------------


class Document(TimeStampedUUIDModel):
    """
    Generic document attached to any model (Property, Unit, Lease, Tenant, etc.)
    Uses Django's ContentTypes framework for flexibility.
    """

    from django.contrib.contenttypes.fields import GenericForeignKey
    from django.contrib.contenttypes.models import ContentType

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = (
        models.UUIDField()
    )  # because our models use UUID as primary key (id field)
    content_object = GenericForeignKey("content_type", "object_id")

    name = models.CharField(_("Document name"), max_length=255)
    file = models.FileField(_("File"), upload_to="documents/%Y/%m/")
    description = models.TextField(_("Description"), blank=True)
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_documents",
        verbose_name=_("Uploaded by"),
    )

    class Meta:
        verbose_name = _("Document")
        verbose_name_plural = _("Documents")
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]

    def __str__(self):
        return self.name
