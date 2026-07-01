from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import (
    Property,
    Owner,
    Unit,
    PropertyOwnership,
    Manager,
    PropertyImage,
    UnitImage,
    OwnerPaymentConfig,
    PropertyPaymentConfig,
    TermTemplate,
)

admin.site.register(TermTemplate)

# ============================================================
# Inlines
# ============================================================
class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 1
    fields = ("image", "alt_text", "is_primary")
    readonly_fields = ("id",)


class UnitImageInline(admin.TabularInline):
    model = UnitImage
    extra = 1
    fields = ("image", "alt_text", "is_primary")
    readonly_fields = ("id",)


class PropertyOwnershipInline(admin.TabularInline):
    model = PropertyOwnership
    extra = 1
    fields = ("owner", "percentage", "is_primary")
    readonly_fields = ("id",)
    autocomplete_fields = ("owner",)  # requires OwnerAdmin to have search_fields


# ============================================================
# Owner Admin
# ============================================================
@admin.register(Owner)
class OwnerAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "subscription_plan",
        "subscription_status",
        "subscription_end_date",
        "preferred_payout_method",
    )
    # ✅ Fix: use 'user__is_active' because is_active is on User
    list_filter = ("subscription_status", "preferred_payout_method", "user__is_active")
    search_fields = (
        "user__email",
        "user__username",
        "user__first_name",
        "user__last_name",
    )
    autocomplete_fields = ("user", "subscription_plan")
    readonly_fields = ("id", "created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("user",)}),
        (
            _("Subscription"),
            {
                "fields": (
                    "subscription_plan",
                    "subscription_status",
                    "subscription_start_date",
                    "subscription_end_date",
                )
            },
        ),
        (
            _("Payout Details"),
            {
                "fields": (
                    "preferred_payout_method",
                    "mobile_money_number",
                    "bank_account_name",
                    "bank_name",
                    "bank_account_number",
                    "bank_code",
                    "tax_id",
                )
            },
        ),
        (
            _("Timestamps"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


# ============================================================
# Manager Admin
# ============================================================
@admin.register(Manager)
class ManagerAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "commission_rate", "is_active")
    list_filter = ("is_active",)
    search_fields = ("user__email", "user__username")
    autocomplete_fields = ("user",)
    readonly_fields = ("id", "created_at", "updated_at")
    filter_horizontal = ("managed_properties",)


# ============================================================
# Property Admin
# ============================================================
@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "property_type",
        "city",
        "status",
        "is_active",
        "created_at",
    )
    list_filter = ("property_type", "status", "is_active", "city", "country")
    search_fields = ("name", "address_line1", "city", "description")
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = (PropertyImageInline, PropertyOwnershipInline)
    # ✅ Remove filter_horizontal because 'owners' uses a custom through model
    # filter_horizontal = ("owners",)
    fieldsets = (
        (None, {"fields": ("name", "property_type", "description", "is_active")}),
        (
            _("Address"),
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
            _("Cameroon Specifics"),
            {"fields": ("has_generator", "has_water_tank", "amenities")},
        ),
        (
            _("Pricing"),
            {
                "fields": (
                    "starting_amount",
                    "top_amount",
                    "status",
                )
            },
        ),
        (
            _("Multilingual"),
            {
                "fields": (
                    "language",
                    "name_fr",
                    "description_fr",
                    "amenities_fr",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            _("Timestamps"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


# ============================================================
# Unit Admin
# ============================================================
@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "unit_number",
        "property",
        "unit_type",
        "status",
        "default_rent_amount",
        "monthly_rent",
    )
    list_filter = ("unit_type", "status", "rent_duration_type", "property")
    search_fields = ("unit_number", "property__name")
    readonly_fields = ("id", "created_at", "updated_at")
    # ✅ Remove autocomplete_fields that require PaymentPlanAdmin.search_fields
    # autocomplete_fields = ("property", "default_payment_plan")
    # Use raw_id_fields or select2 fallback if needed; we'll remove for now.
    inlines = (UnitImageInline,)
    fieldsets = (
        (None, {"fields": ("property", "unit_number", "unit_type", "status")}),
        (
            _("Rent & Deposit"),
            {
                "fields": (
                    "default_rent_amount",
                    "monthly_rent",
                    "yearly_rent",
                    "default_security_deposit",
                    "rent_duration_type",
                )
            },
        ),
        (
            _("Unit Details"),
            {
                "fields": (
                    "floor",
                    "size_m2",
                    "bedrooms",
                    "bathrooms",
                    "amenities",
                    "custom_fields",
                )
            },
        ),
        (
            _("Metering"),
            {
                "fields": (
                    "water_meter_number",
                    "electricity_meter_number",
                    "has_prepaid_meter",
                )
            },
        ),
        (
            _("Multilingual"),
            {
                "fields": ("language", "amenities_fr"),
                "classes": ("collapse",),
            },
        ),
        (
            _("Timestamps"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


# ============================================================
# Property Ownership Admin
# ============================================================
@admin.register(PropertyOwnership)
class PropertyOwnershipAdmin(admin.ModelAdmin):
    list_display = ("id", "property", "owner", "percentage", "is_primary")
    list_filter = ("is_primary",)
    search_fields = ("property__name", "owner__user__email")
    readonly_fields = ("id", "created_at", "updated_at")
    autocomplete_fields = ("property", "owner")


# ============================================================
# Property Image Admin
# ============================================================
@admin.register(PropertyImage)
class PropertyImageAdmin(admin.ModelAdmin):
    list_display = ("id", "property", "is_primary", "image_preview")
    list_filter = ("is_primary",)
    search_fields = ("property__name", "alt_text")
    readonly_fields = ("id",)

    def image_preview(self, obj):
        if obj.image:
            return f'<img src="{obj.image.url}" width="100" height="100" />'
        return "-"

    image_preview.allow_tags = True
    image_preview.short_description = _("Preview")


# ============================================================
# Unit Image Admin
# ============================================================
@admin.register(UnitImage)
class UnitImageAdmin(admin.ModelAdmin):
    list_display = ("id", "unit", "is_primary", "image_preview")
    list_filter = ("is_primary",)
    search_fields = ("unit__unit_number", "alt_text")
    readonly_fields = ("id",)

    def image_preview(self, obj):
        if obj.image:
            return f'<img src="{obj.image.url}" width="100" height="100" />'
        return "-"

    image_preview.allow_tags = True
    image_preview.short_description = _("Preview")


# ============================================================
# OwnerPaymentConfig Admin
# ============================================================
@admin.register(OwnerPaymentConfig)
class OwnerPaymentConfigAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "owner",
        "platform_fee_percent",
        "platform_fee_cap",
        "gateway_fee_percent",
        "pricing_model",
        "is_active",
    )
    list_filter = ("pricing_model", "is_active")
    search_fields = ("owner__user__email",)
    readonly_fields = ("id", "created_at", "updated_at")
    autocomplete_fields = ("owner",)
    fieldsets = (
        (None, {"fields": ("owner", "is_active")}),
        (
            _("Fee Rates"),
            {
                "fields": (
                    "platform_fee_percent",
                    "platform_fee_cap",
                    "gateway_fee_percent",
                    "fixed_extra_fee",
                )
            },
        ),
        (
            _("Payer Rules"),
            {
                "fields": (
                    "platform_fee_payer",
                    "gateway_fee_payer",
                    "wallet_fee_payer",
                )
            },
        ),
        (
            _("Other Settings"),
            {
                "fields": (
                    "gateway_methods",
                    "pricing_model",
                )
            },
        ),
        (
            _("Timestamps"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


# ============================================================
# PropertyPaymentConfig Admin
# ============================================================
@admin.register(PropertyPaymentConfig)
class PropertyPaymentConfigAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "property",
        "pricing_model",
        "platform_fee_payer",
        "gateway_fee_payer",
        "enable_wallet_payments",
        "allow_manual_payments",
        "is_active",
    )
    list_filter = (
        "pricing_model",
        "enable_wallet_payments",
        "allow_manual_payments",
        "is_active",
    )
    search_fields = ("property__name",)
    readonly_fields = ("id", "created_at", "updated_at")
    # ✅ Remove autocomplete_fields to avoid missing search_fields on PaymentPlan
    # autocomplete_fields = ("property", "default_payment_plan")
    fieldsets = (
        (None, {"fields": ("property", "is_active")}),
        (
            _("Pricing & Payer Rules"),
            {
                "fields": (
                    "pricing_model",
                    "platform_fee_payer",
                    "gateway_fee_payer",
                    "wallet_fee_payer",
                    "gateway_methods",
                )
            },
        ),
        (
            _("Overrides & Defaults"),
            {
                "fields": (
                    "fee_overrides",
                    "default_payment_plan",
                )
            },
        ),
        (
            _("Feature Flags"),
            {
                "fields": (
                    "enable_wallet_payments",
                    "allow_manual_payments",
                    "manual_payment_requires_verification",
                    "currency",
                )
            },
        ),
        (
            _("Timestamps"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
