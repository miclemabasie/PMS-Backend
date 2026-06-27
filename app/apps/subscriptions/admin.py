from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import BaseSubscriptionFeatureGroup, SubscriptionPlan, SubscriptionInvoice


@admin.register(BaseSubscriptionFeatureGroup)
class BaseSubscriptionFeatureGroupAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_active", "created_at", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    readonly_fields = ("id", "created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("name", "description", "is_active")}),
        (
            _("Permissions & Quotas (JSON)"),
            {
                "fields": ("permissions",),
                "description": _(
                    "Define permissions and quotas as a JSON object. "
                    "Example: {'can_create_properties': true, 'max_properties': 5, ...}"
                ),
            },
        ),
        (
            _("Timestamps"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "monthly_price",
        "feature_group",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active", "feature_group")
    search_fields = ("name", "description")
    readonly_fields = ("id", "created_at", "updated_at")
    autocomplete_fields = ("feature_group",)
    fieldsets = (
        (None, {"fields": ("name", "description", "monthly_price", "is_active")}),
        (
            _("Feature Group"),
            {
                "fields": ("feature_group",),
                "description": _(
                    "Select a feature group. All capabilities are inherited from the group."
                ),
            },
        ),
        (
            _("Discount & Cap"),
            {
                "fields": (
                    "transaction_fee_discount_percent",
                    "platform_fee_cap_override",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            _("Timestamps"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(SubscriptionInvoice)
class SubscriptionInvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "owner",
        "plan",
        "amount",
        "status",
        "due_date",
        "paid_at",
        "created_at",
    )
    list_filter = ("status", "due_date", "created_at")
    search_fields = ("owner__user__email", "owner__user__username", "plan__name")
    readonly_fields = ("id", "created_at", "updated_at")
    # ✅ Remove autocomplete_fields to avoid missing search_fields on Payment
    # autocomplete_fields = ("owner", "plan", "payment")
    fieldsets = (
        (None, {"fields": ("owner", "plan", "amount", "due_date", "status")}),
        (
            _("Payment Details"),
            {
                "fields": ("payment", "paid_at"),
                "classes": ("collapse",),
            },
        ),
        (
            _("Retry & Error"),
            {
                "fields": ("retry_count", "error_message"),
                "classes": ("collapse",),
            },
        ),
        (
            _("Timestamps"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.status == "paid":
            return self.readonly_fields + (
                "owner",
                "plan",
                "amount",
                "due_date",
                "status",
            )
        return self.readonly_fields
