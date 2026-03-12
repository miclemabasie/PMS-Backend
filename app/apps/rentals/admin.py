from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    PaymentTerm,
    Lease,
    LeaseTenant,
    Payment,
    Vendor,
    MaintenanceRequest,
    Expense,
    Document,
    LeaseStatus,  # added for status constant
)


# ----------------------------------------------------------------------
# Inline Classes
# ----------------------------------------------------------------------


class LeaseTenantInline(admin.TabularInline):
    """Inline for lease tenants (many-to-many through model)."""

    model = LeaseTenant
    extra = 1
    autocomplete_fields = ["tenant"]
    verbose_name = "Tenant"
    verbose_name_plural = "Tenants"


class PaymentInline(admin.TabularInline):
    """Inline for payments within a lease."""

    model = Payment
    extra = 0
    fields = ["amount", "payment_date", "payment_method", "payment_type", "status"]
    readonly_fields = ["payment_date"]
    ordering = ["-payment_date"]


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


@admin.register(PaymentTerm)
class PaymentTermAdmin(admin.ModelAdmin):
    list_display = ["name", "interval_months", "description", "created_at"]
    list_filter = ["interval_months"]
    search_fields = ["name", "description"]
    ordering = ["interval_months"]
    readonly_fields = ["id", "created_at", "updated_at"]
    fieldsets = (
        (None, {"fields": ("name", "interval_months", "description")}),
        (
            "Metadata",
            {"fields": ("id", "created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(Lease)
class LeaseAdmin(admin.ModelAdmin):
    list_display = [
        "id_short",
        "unit_link",
        "tenant_names",
        "start_date",
        "end_date",
        "rent_amount",
        "payment_term",
        "status",
    ]
    list_filter = ["status", "payment_term", "start_date", "end_date"]
    search_fields = [
        "unit__unit_number",
        "unit__property__name",
        "lease_tenants__tenant__user__first_name",
        "lease_tenants__tenant__user__last_name",
    ]
    autocomplete_fields = ["unit", "payment_term", "renewed_from"]
    readonly_fields = ["id", "created_at", "updated_at", "tenant_names"]
    inlines = [LeaseTenantInline, PaymentInline, DocumentInline]
    fieldsets = (
        ("Unit & Dates", {"fields": ("unit", "start_date", "end_date")}),
        (
            "Payment Terms",
            {
                "fields": (
                    "payment_term",
                    "rent_amount",
                    "due_day",
                    "security_deposit",
                    "deposit_paid",
                )
            },
        ),
        ("Late Fees", {"fields": ("late_fee_type", "late_fee_value")}),
        ("Utilities & Documents", {"fields": ("utilities_included", "documents")}),
        ("Status", {"fields": ("status", "termination_reason")}),
        ("Renewal", {"fields": ("renewed_from",)}),
        ("Tenants", {"fields": ("tenant_names",)}),
        (
            "Metadata",
            {"fields": ("id", "created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def id_short(self, obj):
        return str(obj.id)[:8] + "..."

    id_short.short_description = "ID"

    def unit_link(self, obj):
        url = reverse("admin:rentals_unit_change", args=[obj.unit.pk])
        return format_html('<a href="{}">{}</a>', url, obj.unit)

    unit_link.short_description = "Unit"
    unit_link.admin_order_field = "unit__unit_number"

    def tenant_names(self, obj):
        tenants = obj.tenants.all()
        if tenants.exists():
            links = []
            for tenant in tenants:
                url = reverse("admin:rentals_tenant_change", args=[tenant.pk])
                links.append(format_html('<a href="{}">{}</a>', url, str(tenant)))
            return format_html(", ".join([str(l) for l in links]))
        return "No tenants"

    tenant_names.short_description = "Tenant(s)"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        "id_short",
        "lease_link",
        "amount",
        "payment_date",
        "payment_method",
        "payment_type",
        "status",
        "period",
    ]
    list_filter = ["payment_method", "payment_type", "status", "payment_date"]
    search_fields = [
        "lease__unit__unit_number",
        "transaction_id",
        "mobile_reference",
        "tenant__user__first_name",
        "tenant__user__last_name",
    ]
    autocomplete_fields = ["lease", "tenant"]
    readonly_fields = ["id", "created_at", "updated_at"]
    date_hierarchy = "payment_date"
    fieldsets = (
        ("Lease & Tenant", {"fields": ("lease", "tenant")}),
        (
            "Payment Details",
            {
                "fields": (
                    "amount",
                    "payment_date",
                    "payment_method",
                    "payment_type",
                    "status",
                )
            },
        ),
        ("Period Covered", {"fields": ("period_start", "period_end")}),
        ("Transaction Info", {"fields": ("transaction_id", "gateway_response")}),
        (
            "Mobile Money",
            {
                "fields": ("mobile_provider", "mobile_phone", "mobile_reference"),
                "classes": ("collapse",),
            },
        ),
        (
            "Bank / Cash",
            {"fields": ("bank_name", "check_number"), "classes": ("collapse",)},
        ),
        ("Notes", {"fields": ("notes",)}),
        (
            "Metadata",
            {"fields": ("id", "created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def id_short(self, obj):
        return str(obj.id)[:8] + "..."

    id_short.short_description = "ID"

    def lease_link(self, obj):
        url = reverse("admin:rentals_lease_change", args=[obj.lease.pk])
        return format_html('<a href="{}">Lease #{}</a>', url, str(obj.lease.id)[:8])

    lease_link.short_description = "Lease"
    lease_link.admin_order_field = "lease"

    def period(self, obj):
        if obj.period_start and obj.period_end:
            return f"{obj.period_start} to {obj.period_end}"
        return "-"

    period.short_description = "Period"


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ["company_name", "contact_name", "phone", "email", "is_active"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["company_name", "contact_name", "phone", "email", "specialties"]
    readonly_fields = ["id", "created_at", "updated_at"]
    fieldsets = (
        (
            "Company Information",
            {"fields": ("company_name", "contact_name", "phone", "email", "address")},
        ),
        (
            "Services",
            {"fields": ("specialties", "specialties_fr", "notes", "notes_fr")},
        ),
        ("Status", {"fields": ("is_active", "language")}),
        (
            "Metadata",
            {"fields": ("id", "created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(MaintenanceRequest)
class MaintenanceRequestAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "unit_link",
        "priority",
        "status",
        "created_at",
        "assigned_vendor_link",
    ]
    list_filter = ["priority", "status", "created_at"]
    search_fields = ["title", "description", "unit__unit_number"]
    autocomplete_fields = [
        "unit",
        "tenant",
        "requested_by_manager",
        "assigned_vendor",
        "approved_by",
    ]
    readonly_fields = ["id", "created_at", "updated_at", "completed_at"]
    date_hierarchy = "created_at"
    fieldsets = (
        (
            "Request Details",
            {
                "fields": (
                    "unit",
                    "tenant",
                    "requested_by_manager",
                    "title",
                    "description",
                    "language",
                    "title_fr",
                    "description_fr",
                )
            },
        ),
        ("Priority & Status", {"fields": ("priority", "status")}),
        ("Photos", {"fields": ("photos",)}),
        (
            "Vendor Assignment",
            {"fields": ("assigned_vendor", "estimated_cost", "actual_cost")},
        ),
        ("Approval", {"fields": ("approved_by", "approved_at")}),
        ("Completion", {"fields": ("completed_at", "notes")}),
        (
            "Metadata",
            {"fields": ("id", "created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def unit_link(self, obj):
        url = reverse("admin:rentals_unit_change", args=[obj.unit.pk])
        return format_html('<a href="{}">{}</a>', url, obj.unit)

    unit_link.short_description = "Unit"
    unit_link.admin_order_field = "unit__unit_number"

    def assigned_vendor_link(self, obj):
        if obj.assigned_vendor:
            url = reverse("admin:rentals_vendor_change", args=[obj.assigned_vendor.pk])
            return format_html('<a href="{}">{}</a>', url, obj.assigned_vendor)
        return "-"

    assigned_vendor_link.short_description = "Vendor"


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = [
        "category",
        "amount",
        "expense_date",
        "property_link",
        "unit_link",
        "vendor_link",
    ]
    list_filter = ["category", "expense_date", "is_reimbursable", "reimbursed"]
    search_fields = ["description", "property__name", "unit__unit_number"]
    autocomplete_fields = ["property", "unit", "vendor"]
    readonly_fields = ["id", "created_at", "updated_at"]
    date_hierarchy = "expense_date"
    fieldsets = (
        ("Property & Unit", {"fields": ("property", "unit")}),
        (
            "Expense Details",
            {
                "fields": (
                    "category",
                    "amount",
                    "expense_date",
                    "description",
                    "language",
                    "description_fr",
                )
            },
        ),
        ("Vendor", {"fields": ("vendor",)}),
        ("Receipt", {"fields": ("receipt",)}),
        ("Reimbursement", {"fields": ("is_reimbursable", "reimbursed")}),
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

    def unit_link(self, obj):
        if obj.unit:
            url = reverse("admin:rentals_unit_change", args=[obj.unit.pk])
            return format_html('<a href="{}">{}</a>', url, obj.unit)
        return "-"

    unit_link.short_description = "Unit"

    def vendor_link(self, obj):
        if obj.vendor:
            url = reverse("admin:rentals_vendor_change", args=[obj.vendor.pk])
            return format_html('<a href="{}">{}</a>', url, obj.vendor)
        return "-"

    vendor_link.short_description = "Vendor"


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ["name", "content_type", "object_id", "uploaded_by", "created_at"]
    list_filter = ["content_type", "created_at"]
    search_fields = ["name", "description"]
    autocomplete_fields = ["uploaded_by"]
    readonly_fields = ["id", "created_at", "updated_at", "file_link"]
    fieldsets = (
        ("Content Object", {"fields": ("content_type", "object_id")}),
        ("Document Details", {"fields": ("name", "file", "file_link", "description")}),
        ("Uploader", {"fields": ("uploaded_by",)}),
        (
            "Metadata",
            {"fields": ("id", "created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def file_link(self, obj):
        if obj.file:
            return format_html(
                '<a href="{}" target="_blank">Download</a>', obj.file.url
            )
        return "-"

    file_link.short_description = "Download"
