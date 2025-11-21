import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from deep_translator import GoogleTranslator

from .models import Property, Unit, MaintenanceRequest, Vendor, Tenant, Expense

logger = logging.getLogger(__name__)


def translate_text(text, source="auto", target="fr"):
    """Translate a single string using Google Translate."""
    if not text or not isinstance(text, str):
        return text
    try:
        translator = GoogleTranslator(source=source, target=target)
        return translator.translate(text)
    except Exception as e:
        logger.error(f"Translation failed: {e} - text: {text[:50]}...")
        return text  # fallback to original


def translate_list(items, source="auto", target="fr"):
    """Translate each string in a list."""
    if not items:
        return []
    return [translate_text(item, source, target) for item in items]


def perform_translation(instance, fields):
    """
    Generic translation routine.
    - instance: the model instance
    - fields: list of tuples (source_field, target_field, is_list)
    """
    source_lang = getattr(instance, "language", "en")
    target_lang = "fr" if source_lang == "en" else "en"
    updated_fields = {}

    for src_field, tgt_field, is_list in fields:
        # Skip if source field hasn't changed (tracker)
        tracker = getattr(instance, "tracker", None)
        if tracker and not tracker.has_changed(src_field):
            continue

        src_value = getattr(instance, src_field)
        if src_value:
            if is_list:
                translated = translate_list(
                    src_value, source=source_lang, target=target_lang
                )
            else:
                translated = translate_text(
                    src_value, source=source_lang, target=target_lang
                )
            setattr(instance, tgt_field, translated)
            updated_fields[tgt_field] = translated

    if updated_fields:
        # Update only the translation fields to avoid recursion
        type(instance).objects.filter(pk=instance.pk).update(**updated_fields)


# ----------------------------------------------------------------------
# Signal handlers for each model
# ----------------------------------------------------------------------


@receiver(post_save, sender=Property)
def translate_property(sender, instance, **kwargs):
    fields = [
        ("name", "name_fr", False),
        ("description", "description_fr", False),
        ("amenities", "amenities_fr", True),
    ]
    perform_translation(instance, fields)


@receiver(post_save, sender=Unit)
def translate_unit(sender, instance, **kwargs):
    fields = [
        ("amenities", "amenities_fr", True),
    ]
    perform_translation(instance, fields)


@receiver(post_save, sender=MaintenanceRequest)
def translate_maintenance_request(sender, instance, **kwargs):
    fields = [
        ("title", "title_fr", False),
        ("description", "description_fr", False),
    ]
    perform_translation(instance, fields)


@receiver(post_save, sender=Vendor)
def translate_vendor(sender, instance, **kwargs):
    fields = [
        ("company_name", "company_name_fr", False),
        ("contact_name", "contact_name_fr", False),
        ("address", "address_fr", False),
        ("specialties", "specialties_fr", True),
        ("notes", "notes_fr", False),
    ]
    perform_translation(instance, fields)


@receiver(post_save, sender=Tenant)
def translate_tenant(sender, instance, **kwargs):
    fields = [
        ("emergency_contact_name", "emergency_contact_name_fr", False),
        ("employer", "employer_fr", False),
        ("job_title", "job_title_fr", False),
        ("notes", "notes_fr", False),
        ("guarantor_name", "guarantor_name_fr", False),
    ]
    perform_translation(instance, fields)


@receiver(post_save, sender=Expense)
def translate_expense(sender, instance, **kwargs):
    fields = [
        ("description", "description_fr", False),
    ]
    perform_translation(instance, fields)
