from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    Owner,
    Manager,
    Property,
    PropertyOwnership,
    Unit,  # added for status constant
)

from apps.rentals.models import (
    LeaseTenant,
    MaintenanceRequest,
    Expense,
    Document,
    LeaseStatus,
)

# ----------------------------------------------------------------------
# Inline Classes
# ----------------------------------------------------------------------


class PropertyOwnershipInline(admin.TabularInline):
    """Inline for property ownership (many-to-many through model)."""

    model = PropertyOwnership
    extra = 1
    autocomplete_fields = ["owner"]
    verbose_name = "Owner"
    verbose_name_plural = "Owners"


class LeaseTenantInline(admin.TabularInline):
    """Inline for lease tenants (many-to-many through model)."""

    model = LeaseTenant
    extra = 1
    autocomplete_fields = ["tenant"]
    verbose_name = "Tenant"
    verbose_name_plural = "Tenants"


class UnitInline(admin.TabularInline):
    """Inline for units within a property."""

    model = Unit
    extra = 1
    fields = [
        "unit_number",
        "unit_type",
        "status",
        "default_rent_amount",
        "link_to_detail",
    ]
    readonly_fields = ["link_to_detail"]

    def link_to_detail(self, obj):
        if obj.pk:
            url = reverse("admin:rentals_unit_change", args=[obj.pk])
            return format_html('<a href="{}">Edit</a>', url)
        return "-"

    link_to_detail.short_description = "Actions"


class MaintenanceRequestInline(admin.TabularInline):
    """Inline for maintenance requests within a unit."""

    model = MaintenanceRequest
    extra = 0
    fields = ["title", "priority", "status", "created_at"]
    readonly_fields = ["created_at"]
    ordering = ["-created_at"]


class ExpenseInline(admin.TabularInline):
    """Inline for expenses within a property."""

    model = Expense
    extra = 0
    fields = ["category", "amount", "expense_date", "description"]
    readonly_fields = ["expense_date"]
    ordering = ["-expense_date"]


class DocumentInline(GenericTabularInline):
    """Generic inline for documents attached to any model."""

    model = Document
    extra = 1
    fields = ["name", "file", "description", "uploaded_by", "created_at"]
    readonly_fields = ["created_at"]


@admin.register(Owner)
class OwnerAdmin(admin.ModelAdmin):
    list_display = [
        "user_link",
        "preferred_payout_method",
        "mobile_money_number",
        "tax_id",
        "created_at",
    ]
    list_filter = ["preferred_payout_method", "created_at"]
    search_fields = [
        "user__email",
        "user__first_name",
        "user__last_name",
        "bank_account_name",
        "tax_id",
    ]
    autocomplete_fields = ["user"]
    readonly_fields = ["id", "created_at", "updated_at"]
    fieldsets = (
        ("User Information", {"fields": ("user",)}),
        (
            "Payout Details",
            {
                "fields": (
                    "preferred_payout_method",
                    "mobile_money_number",
                    "bank_account_name",
                    "bank_name",
                    "bank_account_number",
                    "bank_code",
                )
            },
        ),
        ("Tax Information", {"fields": ("tax_id",)}),
        (
            "Metadata",
            {"fields": ("id", "created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def user_link(self, obj):
        url = reverse("admin:users_user_change", args=[obj.user.pk])
        return format_html(
            '<a href="{}">{}</a>', url, obj.user.get_full_name() or obj.user.email
        )

    user_link.short_description = "User"
    user_link.admin_order_field = "user__email"


@admin.register(Manager)
class ManagerAdmin(admin.ModelAdmin):
    list_display = ["user_link", "commission_rate", "is_active", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["user__email", "user__first_name", "user__last_name"]
    autocomplete_fields = ["user", "managed_properties"]
    readonly_fields = ["id", "created_at", "updated_at"]
    fieldsets = (
        ("User Information", {"fields": ("user",)}),
        (
            "Management Details",
            {"fields": ("commission_rate", "is_active", "managed_properties")},
        ),
        (
            "Metadata",
            {"fields": ("id", "created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def user_link(self, obj):
        url = reverse("admin:users_user_change", args=[obj.user.pk])
        return format_html(
            '<a href="{}">{}</a>', url, obj.user.get_full_name() or obj.user.email
        )

    user_link.short_description = "User"
    user_link.admin_order_field = "user__email"


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "property_type",
        "city",
        "units_count",
        "is_active",
        "created_at",
    ]
    list_filter = ["property_type", "is_active", "city", "country"]
    search_fields = ["name", "address_line1", "city", "description"]
    readonly_fields = ["id", "created_at", "updated_at", "units_count"]
    inlines = [PropertyOwnershipInline, UnitInline, ExpenseInline, DocumentInline]
    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "name",
                    "property_type",
                    "description",
                    "language",
                    "name_fr",
                    "description_fr",
                )
            },
        ),
        (
            "Address",
            {
                "fields": (
                    "address_line1",
                    "address_line2",
                    "city",
                    "state",
                    "country",
                    "postal_code",
                )
            },
        ),
        (
            "Cameroon Specifics",
            {
                "fields": (
                    "has_generator",
                    "has_water_tank",
                    "amenities",
                    "amenities_fr",
                )
            },
        ),
        ("Media", {"fields": ("images",)}),
        ("Management", {"fields": ("is_active",)}),  # FIX: removed invalid "managers"
        (
            "Metadata",
            {
                "fields": ("id", "created_at", "updated_at", "units_count"),
                "classes": ("collapse",),
            },
        ),
    )

    def units_count(self, obj):
        return obj.units.count()

    units_count.short_description = "Total Units"


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = [
        "__str__",
        "property_link",
        "unit_type",
        "status",
        "default_rent_amount",
        "current_tenant",
    ]
    list_filter = ["status", "unit_type", "property__city"]
    search_fields = ["unit_number", "property__name", "property__address_line1"]
    autocomplete_fields = ["property"]
    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
        "current_lease_link",
        "current_tenant",
    ]
    inlines = [MaintenanceRequestInline, DocumentInline]
    fieldsets = (
        ("Property & Identification", {"fields": ("property", "unit_number")}),
        (
            "Unit Details",
            {"fields": ("unit_type", "floor", "size_m2", "bedrooms", "bathrooms")},
        ),
        (
            "Pricing",
            {
                "fields": (
                    "default_rent_amount",
                    "default_payment_term",
                    "default_security_deposit",
                )
            },
        ),
        ("Status", {"fields": ("status",)}),
        (
            "Cameroon Specifics",
            {
                "fields": (
                    "amenities",
                    "amenities_fr",
                    "water_meter_number",
                    "electricity_meter_number",
                    "has_prepaid_meter",
                )
            },
        ),
        ("Media & Custom Fields", {"fields": ("images", "custom_fields", "language")}),
        ("Current Lease Info", {"fields": ("current_lease_link", "current_tenant")}),
        (
            "Metadata",
            {"fields": ("id", "created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def property_link(self, obj):
        url = reverse("admin:rentals_property_change", args=[obj.property.pk])
        return format_html('<a href="{}">{}</a>', url, obj.property.name)

    property_link.short_description = "Property"
    property_link.admin_order_field = "property__name"

    # FIXED: use proper query for active lease
    def current_lease_link(self, obj):
        active_lease = obj.leases.filter(status=LeaseStatus.ACTIVE).first()
        if active_lease:
            url = reverse("admin:rentals_lease_change", args=[active_lease.pk])
            return format_html('<a href="{}">Lease #{}</a>', url, active_lease.pk)
        return "No active lease"

    current_lease_link.short_description = "Current Lease"

    # FIXED: use proper query for active lease and its tenants
    def current_tenant(self, obj):
        active_lease = obj.leases.filter(status=LeaseStatus.ACTIVE).first()
        if active_lease:
            tenants = active_lease.tenants.all()
            if tenants.exists():
                return ", ".join([str(t) for t in tenants])
        return "Vacant"

    current_tenant.short_description = "Current Tenant(s)"
