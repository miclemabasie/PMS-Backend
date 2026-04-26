import json
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()

# Strict imports matching ONLY the models you provided
from apps.users.models import Profile
from apps.tenants.models import Tenant
from apps.properties.models import Owner, Manager, Property, PropertyOwnership, Unit
from apps.payments.models import PaymentPlan, Installment, RentalAgreement, Payment


class Command(BaseCommand):
    help = "Populates database with seed data for Users, Tenants, Properties, and Payments."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            self.stdout.write(
                self.style.ERROR("⛔ Database seeding is disabled in production mode.")
            )
            return

        self.stdout.write(self.style.WARNING("🌱 Starting database population..."))
        try:
            with transaction.atomic():
                users = self._seed_users()
                profiles = self._seed_profiles(users)
                payment_plans = self._seed_payment_plans()
                properties = self._seed_properties(profiles)
                units = self._seed_units(properties)
                agreements = self._seed_agreements(units, profiles, payment_plans)
                self._seed_payments(agreements)

            self.stdout.write(
                self.style.SUCCESS("\n✅ Successfully populated database!")
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ Failed to populate: {str(e)}"))
            raise

    # =========================================================================
    # 1. USERS (Custom AbstractBaseUser, email=USERNAME_FIELD)
    # =========================================================================
    def _seed_users(self):
        self.stdout.write("  ↳ Creating Users...")

        def _create_user(email, username, role, is_staff=False, is_superuser=False):
            user, _ = User.objects.get_or_create(
                email=email,
                defaults={
                    "username": username,
                    "first_name": username.capitalize(),
                    "last_name": "User",
                    "role": role,
                    "is_staff": is_staff,
                    "is_superuser": is_superuser,
                    "is_active": True,
                },
            )
            # Only set password if newly created or unusable
            if not user.has_usable_password():
                user.set_password(f"{username}123")
                user.save(update_fields=["password"])
            return user

        landlord = _create_user("landlord@example.com", "landlord", "landlord")
        manager = _create_user("manager@example.com", "manager", "manager")
        tenant = _create_user("tenant@example.com", "tenant", "tenant")
        return {"landlord": landlord, "manager": manager, "tenant": tenant}

    # =========================================================================
    # 2. PROFILES (Base Profile, Owner, Manager, Tenant)
    # =========================================================================
    def _seed_profiles(self, users):
        self.stdout.write("  ↳ Creating Profiles & Roles...")

        # Base User Profile
        for role, user in users.items():
            Profile.objects.get_or_create(
                user=user,
                defaults={
                    "phone_number": f"+2376{role[:3]}00000",
                    "country": "CM",
                    "city": "Douala",
                    "address": f"123 {role.title()} St.",
                    "gender": "other",
                },
            )

        # Owner Profile
        owner, _ = Owner.objects.get_or_create(
            user=users["landlord"],
            defaults={
                "preferred_payout_method": "bank_transfer",
                "mobile_money_number": "+237670000000",
                "bank_account_name": "Landlord LLC",
                "bank_name": "Afriland First Bank",
                "bank_account_number": "1234567890",
                "bank_code": "AFRIBANK",
                "tax_id": "NIU-0012345678",
            },
        )

        # Manager Profile
        manager_profile, _ = Manager.objects.get_or_create(
            user=users["manager"],
            defaults={
                "commission_rate": Decimal("5.00"),
                "is_active": True,
            },
        )

        # Tenant Profile (id_number is unique)
        tenant_profile, _ = Tenant.objects.get_or_create(
            user=users["tenant"],
            defaults={
                "id_number": "CNI-2026-SEED-001",
                "is_discoverable": True,
                "is_verified": False,
                "is_primary": True,
                "emergency_contact_name": "Parent Name",
                "emergency_contact_phone": "+237680000000",
                "emergency_contact_relation": "Parent",
                "employer": "Example Corp",
                "job_title": "Developer",
                "monthly_income": Decimal("500000"),
                "guarantor_name": "Guarantor Name",
                "guarantor_phone": "+237690000000",
                "guarantor_email": "guarantor@example.com",
                "notes": "Seed tenant for testing.",
                "language": "en",
            },
        )

        return {"owner": owner, "manager": manager_profile, "tenant": tenant_profile}

    # =========================================================================
    # 3. PAYMENT PLANS & INSTALLMENTS
    # =========================================================================
    def _seed_payment_plans(self):
        self.stdout.write("  ↳ Creating Payment Plans & Installments...")

        monthly, _ = PaymentPlan.objects.get_or_create(
            name="Standard Monthly",
            defaults={
                "mode": "monthly",
                "allowed_monthly_terms": [1, 3, 6],
                "max_months": 12,
                "show_full_payment_option": True,
                "enforce_installment_order": False,
                "allow_custom_amount": False,
                "amount_step": 1000,
                "late_fee_rules": {"grace_days": 5, "percentage": 5.0},
                "is_active": True,
            },
        )

        yearly, _ = PaymentPlan.objects.get_or_create(
            name="Yearly Installment Plan",
            defaults={
                "mode": "yearly",
                "allowed_monthly_terms": [],
                "max_months": 12,
                "show_full_payment_option": True,
                "enforce_installment_order": True,
                "allow_custom_amount": False,
                "amount_step": 50000,
                "late_fee_rules": {"grace_days": 0, "percentage": 10.0},
                "is_active": True,
            },
        )

        # Installments for Yearly Plan
        Installment.objects.get_or_create(
            payment_plan=yearly,
            order_index=1,
            defaults={
                "percent": Decimal("40.00"),
                "due_date": date.today() + timedelta(days=30),
            },
        )
        Installment.objects.get_or_create(
            payment_plan=yearly,
            order_index=2,
            defaults={
                "percent": Decimal("60.00"),
                "due_date": date.today() + timedelta(days=180),
            },
        )

        return {"monthly": monthly, "yearly": yearly}

    # =========================================================================
    # 4. PROPERTIES & OWNERSHIP
    # =========================================================================
    def _seed_properties(self, profiles):
        self.stdout.write("  ↳ Creating Properties...")

        prop, _ = Property.objects.get_or_create(
            name="Sunset Apartments",
            defaults={
                "property_type": "apartment_building",
                "description": "Modern apartments in Douala with 24/7 security.",
                "address_line1": "123 Boulevard de la Liberté",
                "address_line2": "Akwa",
                "city": "Douala",
                "state": "Littoral",
                "country": "CM",
                "postal_code": "40000",
                "has_generator": True,
                "has_water_tank": True,
                "amenities": ["wifi", "parking", "gym", "security"],
                "status": "active",
                "starting_amount": Decimal("150000"),
                "top_amount": Decimal("450000"),
                "is_active": True,
                "language": "en",
                "name_fr": "",
                "description_fr": "",
                "amenities_fr": [],
            },
        )

        # Link Owner via Through Model
        PropertyOwnership.objects.get_or_create(
            property=prop,
            owner=profiles["owner"],
            defaults={"percentage": Decimal("100.00"), "is_primary": True},
        )

        # Assign Manager (M2M)
        profiles["manager"].managed_properties.add(prop)

        return [prop]

    # =========================================================================
    # 5. UNITS
    # =========================================================================
    def _seed_units(self, properties):
        self.stdout.write("  ↳ Creating Units...")
        prop = properties[0]

        u1, _ = Unit.objects.get_or_create(
            property=prop,
            unit_number="101",
            defaults={
                "unit_type": "2_bed",
                "floor": 1,
                "size_m2": 85,
                "bedrooms": 2,
                "bathrooms": 1,
                "default_rent_amount": Decimal("250000"),  # Required field
                "default_security_deposit": Decimal("250000"),
                "status": "vacant",
                "amenities": ["air_conditioning", "balcony"],
                "images": [],
                "water_meter_number": "WM-101",
                "electricity_meter_number": "EM-101",
                "has_prepaid_meter": True,
                "custom_fields": {},
                "language": "en",
                "amenities_fr": [],
            },
        )

        u2, _ = Unit.objects.get_or_create(
            property=prop,
            unit_number="102",
            defaults={
                "unit_type": "studio",
                "floor": 1,
                "size_m2": 45,
                "bedrooms": 1,
                "bathrooms": 1,
                "default_rent_amount": Decimal("180000"),
                "status": "occupied",
                "amenities": ["wifi", "shared_kitchen"],
                "water_meter_number": "WM-102",
                "electricity_meter_number": "EM-102",
                "has_prepaid_meter": False,
            },
        )
        return [u1, u2]

    # =========================================================================
    # 6. RENTAL AGREEMENTS (Replaces Lease)
    # =========================================================================
    def _seed_agreements(self, units, profiles, payment_plans):
        self.stdout.write("  ↳ Creating Rental Agreements...")

        # Note: start_date is auto_now_add=True, so we DO NOT pass it.
        agreement, _ = RentalAgreement.objects.get_or_create(
            unit=units[1],
            tenant=profiles["tenant"],
            defaults={
                "payment_plan": payment_plans["yearly"],
                "coverage_end_date": date.today() + timedelta(days=365),
                "installment_status": {"1": "pending", "2": "pending"},
                "is_active": True,
            },
        )
        return [agreement]

    # =========================================================================
    # 7. PAYMENTS
    # =========================================================================
    def _seed_payments(self, agreements):
        self.stdout.write("  ↳ Creating Payments...")
        today = date.today()

        # Note: payment_date is auto_now_add=True, so we DO NOT pass it.
        Payment.objects.get_or_create(
            agreement=agreements[0],
            amount=Decimal("1080000"),  # 60% of yearly rent
            period_start=today,
            period_end=today + timedelta(days=180),
            defaults={
                "months_covered": Decimal("6.00"),
                "payment_method": "mtn_momo",
                "status": "completed",
                "transaction_id": "TXN-MOMO-99887766",
                "mobile_provider": "MTN Cameroon",
                "mobile_phone": "+237680000000",
                "mobile_reference": "REF-556677",
                "notes": "Initial installment payment.",
                "gateway_response": {"code": 200, "message": "Success"},
            },
        )
