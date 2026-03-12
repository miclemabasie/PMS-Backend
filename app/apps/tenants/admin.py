from django.contrib import admin
from apps.rentals.admin import DocumentInline
from .models import Tenant


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = [
        "user__username",
        "id_number",
        "emergency_contact_name",
        "created_at",
    ]
    list_filter = ["created_at"]
    search_fields = [
        "user__email",
        "user__first_name",
        "user__last_name",
        "id_number",
    ]
    autocomplete_fields = ["user"]
    readonly_fields = ["id", "created_at", "updated_at"]
    inlines = [DocumentInline]
