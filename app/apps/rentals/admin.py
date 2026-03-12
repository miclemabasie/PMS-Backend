from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    PaymentTerm,
    Owner,
    Manager,
    Property,
    PropertyOwnership,
    Unit,
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
    autocomplete_fields = ["property", "default_payment_term"]
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
