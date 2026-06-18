# app/subscriptions/management/commands/setup_subscription_data.py

from django.core.management.base import BaseCommand
from apps.subscriptions.models import BaseSubscriptionFeatureGroup, SubscriptionPlan


class Command(BaseCommand):
    help = "Create initial subscription feature groups and plans"

    def handle(self, *args, **options):
        # Define feature groups data
        feature_groups = [
            {
                "name": "Free",
                "description": "For landlords just getting started. Limited to a single property and a handful of units. No advanced features. Ideal for testing or very small portfolios.",
                "permissions": {
                    "can_create_properties": True,
                    "max_properties": 1,
                    "can_create_units": True,
                    "max_units_total": 2,
                    "max_units_per_property": 2,
                    "can_manage_tenants": True,
                    "max_tenants_total": 5,
                    "can_manage_leases": True,
                    "can_manage_maintenance": True,
                    "can_manage_vendors": False,
                    "can_use_advanced_reports": False,
                    "can_use_bulk_sms": False,
                    "can_use_manual_payments": False,
                    "can_use_api_access": False,
                    "can_use_priority_support": False,
                    "can_use_wallet": True,
                    "can_use_wallet_deposits": True,
                    "can_use_wallet_withdrawals": False,
                    "can_view_tenant_payment_history": True,
                    "can_edit_property_managers": False,
                    "can_manage_subscription": False,
                    "can_receive_receipts": True,
                    "can_enable_multi_currency": False,
                    "can_use_co_ownership": False,
                    "can_use_escrow": False,
                    "max_maintenance_requests_per_month": 5,
                    "max_storage_mb": 50,
                    "can_use_branding": False,
                    "can_use_webhooks": False,
                    "can_use_custom_payment_plans": False,
                    "can_use_payment_plan_templates": False,
                },
                "is_active": True,
            },
            {
                "name": "Basic",
                "description": "Perfect for individual landlords with a small portfolio. Includes core property and tenant management, mobile money payments, and wallet support. No advanced reporting or bulk messaging.",
                "permissions": {
                    "can_create_properties": True,
                    "max_properties": 5,
                    "can_create_units": True,
                    "max_units_total": 20,
                    "max_units_per_property": 10,
                    "can_manage_tenants": True,
                    "max_tenants_total": 50,
                    "can_manage_leases": True,
                    "can_manage_maintenance": True,
                    "can_manage_vendors": True,
                    "can_use_advanced_reports": False,
                    "can_use_bulk_sms": False,
                    "can_use_manual_payments": False,
                    "can_use_api_access": False,
                    "can_use_priority_support": False,
                    "can_use_wallet": True,
                    "can_use_wallet_deposits": True,
                    "can_use_wallet_withdrawals": False,
                    "can_view_tenant_payment_history": True,
                    "can_edit_property_managers": False,
                    "can_manage_subscription": False,
                    "can_receive_receipts": True,
                    "can_enable_multi_currency": False,
                    "can_use_co_ownership": False,
                    "can_use_escrow": False,
                    "max_maintenance_requests_per_month": 15,
                    "max_storage_mb": 200,
                    "can_use_branding": False,
                    "can_use_webhooks": False,
                    "can_use_custom_payment_plans": False,
                    "can_use_payment_plan_templates": False,
                },
                "is_active": True,
            },
            {
                "name": "Standard",
                "description": "Designed for professional landlords and growing agencies. Unlocks bulk SMS/email, advanced reports, manual payment recording, and property manager assignments. Higher quotas for properties and units.",
                "permissions": {
                    "can_create_properties": True,
                    "max_properties": 20,
                    "can_create_units": True,
                    "max_units_total": 100,
                    "max_units_per_property": 20,
                    "can_manage_tenants": True,
                    "max_tenants_total": 200,
                    "can_manage_leases": True,
                    "can_manage_maintenance": True,
                    "can_manage_vendors": True,
                    "can_use_advanced_reports": True,
                    "can_use_bulk_sms": True,
                    "can_use_manual_payments": True,
                    "can_use_api_access": False,
                    "can_use_priority_support": False,
                    "can_use_wallet": True,
                    "can_use_wallet_deposits": True,
                    "can_use_wallet_withdrawals": False,
                    "can_view_tenant_payment_history": True,
                    "can_edit_property_managers": True,
                    "can_manage_subscription": False,
                    "can_receive_receipts": True,
                    "can_enable_multi_currency": False,
                    "can_use_co_ownership": True,
                    "can_use_escrow": False,
                    "max_maintenance_requests_per_month": 50,
                    "max_storage_mb": 500,
                    "can_use_branding": False,
                    "can_use_webhooks": False,
                    "can_use_custom_payment_plans": True,
                    "can_use_payment_plan_templates": False,
                },
                "is_active": True,
            },
            {
                "name": "Premium",
                "description": "Unlimited everything. Full feature set including API access, priority support, white‑label branding, webhooks, custom payment plans, and co‑ownership. Designed for large agencies and property management companies.",
                "permissions": {
                    "can_create_properties": True,
                    "max_properties": None,
                    "can_create_units": True,
                    "max_units_total": None,
                    "max_units_per_property": None,
                    "can_manage_tenants": True,
                    "max_tenants_total": None,
                    "can_manage_leases": True,
                    "can_manage_maintenance": True,
                    "can_manage_vendors": True,
                    "can_use_advanced_reports": True,
                    "can_use_bulk_sms": True,
                    "can_use_manual_payments": True,
                    "can_use_api_access": True,
                    "can_use_priority_support": True,
                    "can_use_wallet": True,
                    "can_use_wallet_deposits": True,
                    "can_use_wallet_withdrawals": True,
                    "can_view_tenant_payment_history": True,
                    "can_edit_property_managers": True,
                    "can_manage_subscription": True,
                    "can_receive_receipts": True,
                    "can_enable_multi_currency": True,
                    "can_use_co_ownership": True,
                    "can_use_escrow": True,
                    "max_maintenance_requests_per_month": None,
                    "max_storage_mb": None,
                    "can_use_branding": True,
                    "can_use_webhooks": True,
                    "can_use_custom_payment_plans": True,
                    "can_use_payment_plan_templates": True,
                },
                "is_active": True,
            },
        ]

        # Create feature groups
        for group_data in feature_groups:
            group, created = BaseSubscriptionFeatureGroup.objects.get_or_create(
                name=group_data["name"],
                defaults={
                    "description": group_data["description"],
                    "permissions": group_data["permissions"],
                    "is_active": group_data["is_active"],
                },
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"Created feature group: {group.name}")
                )
            else:
                self.stdout.write(
                    f"Feature group '{group.name}' already exists, updating..."
                )
                group.description = group_data["description"]
                group.permissions = group_data["permissions"]
                group.is_active = group_data["is_active"]
                group.save()

        # Define plans (reference by feature group name)
        plans = [
            {
                "name": "Free Plan",
                "description": "For landlords just getting started. One property, two units, basic features.",
                "monthly_price": 0,
                "feature_group_name": "Free",
                "is_active": True,
            },
            {
                "name": "Basic Plan",
                "description": "Perfect for individual landlords with a small portfolio. Core features, wallet support.",
                "monthly_price": 5000,
                "feature_group_name": "Basic",
                "is_active": True,
            },
            {
                "name": "Standard Plan",
                "description": "For professional landlords and growing agencies. Bulk messaging, advanced reports, manual payments.",
                "monthly_price": 15000,
                "feature_group_name": "Standard",
                "is_active": True,
            },
            {
                "name": "Premium Plan",
                "description": "Unlimited everything. Full feature set, API access, priority support, white-label branding.",
                "monthly_price": 30000,
                "feature_group_name": "Premium",
                "is_active": True,
            },
        ]

        # Create plans
        for plan_data in plans:
            try:
                feature_group = BaseSubscriptionFeatureGroup.objects.get(
                    name=plan_data["feature_group_name"]
                )
            except BaseSubscriptionFeatureGroup.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(
                        f"Feature group '{plan_data['feature_group_name']}' not found. Skipping plan."
                    )
                )
                continue

            plan, created = SubscriptionPlan.objects.get_or_create(
                name=plan_data["name"],
                defaults={
                    "description": plan_data["description"],
                    "monthly_price": plan_data["monthly_price"],
                    "feature_group": feature_group,
                    "is_active": plan_data["is_active"],
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created plan: {plan.name}"))
            else:
                # Optionally update existing plan
                plan.description = plan_data["description"]
                plan.monthly_price = plan_data["monthly_price"]
                plan.feature_group = feature_group
                plan.is_active = plan_data["is_active"]
                plan.save()
                self.stdout.write(f"Updated plan: {plan.name}")

        self.stdout.write(self.style.SUCCESS("Subscription data setup complete."))
