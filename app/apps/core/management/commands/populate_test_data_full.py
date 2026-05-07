import random
import logging
import string
from datetime import date, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()

from apps.users.models import Profile
from apps.tenants.models import Tenant
from apps.properties.models import (
    Owner,
    Manager,
    Property,
    PropertyOwnership,
    Unit,
    PropertyType,
    UnitType,
)
from apps.payments.models import PaymentPlan, Installment, RentalAgreement, Payment

# Disable connection logs
logging.getLogger("urllib3").setLevel(logging.WARNING)


# ------------------------------------------------------------------
# Realistic Data Generators (Stdlib only)
# ------------------------------------------------------------------
CAMEROON_CITIES = [
    "Douala",
    "Yaoundé",
    "Bamenda",
    "Buea",
    "Limbe",
    "Kribi",
    "Garoua",
    "Maroua",
    "Ebolowa",
    "Ngaoundéré",
]
PROPERTY_NAMES = [
    "Residence",
    "Apartments",
    "Villas",
    "Complex",
    "Homes",
    "Plaza",
    "Tower",
    "Gardens",
]
FIRST_NAMES = [
    "Jean",
    "Paul",
    "Marie",
    "Emmanuel",
    "Amina",
    "Felix",
    "Grace",
    "Samuel",
    "Nadine",
    "David",
    "Sarah",
    "Joseph",
]
LAST_NAMES = [
    "Moukam",
    "Ngassa",
    "Fotso",
    "Tchana",
    "Biyong",
    "Kuate",
    "Mbah",
    "Ewolo",
    "Tafon",
    "Njoya",
    "Mbarga",
    "Fomo",
]
AMENITIES_LIST = [
    "wifi",
    "parking",
    "security",
    "generator",
    "water_tank",
    "elevator",
    "gym",
    "laundry",
    "ac",
    "balcony",
]
MOBILE_PROVIDERS = ["MTN Cameroon", "Orange Cameroon"]
PAYMENT_METHODS = ["mtn_momo", "orange_money", "bank_transfer", "cash"]
PAYMENT_STATUSES = (
    ["completed"] * 80 + ["pending"] * 10 + ["failed"] * 5 + ["refunded"] * 5
)


def _rand_email(name, i):
    return f"{name.lower().replace(' ', '')}{i}@{random.choice(['gmail.com', 'yahoo.fr', 'outlook.com'])}"


def _rand_phone():
    prefix = random.choice(["65", "67", "68", "69"])
    return f"+237{prefix}{random.randint(10000000, 99999999)}"


def _rand_id_number(i):
    return f"CNI-2024-{i:05d}-{random.randint(1000, 9999)}"


def _rand_json_list():
    return random.sample(AMENITIES_LIST, k=random.randint(2, 5))


def _rand_decimal(min_val, max_val, places=0):
    return Decimal(random.randint(min_val, max_val))


class Command(BaseCommand):
    help = "Populates the database with realistic, production-scale seed data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--properties", type=int, default=8, help="Number of properties to create"
        )
        parser.add_argument(
            "--units-per-property", type=int, default=12, help="Units per property"
        )
        parser.add_argument(
            "--tenants", type=int, default=40, help="Number of tenants to create"
        )
        parser.add_argument(
            "--agreements", type=int, default=30, help="Number of rental agreements"
        )
        parser.add_argument(
            "--payments-per-agreement",
            type=int,
            default=4,
            help="Historical payments per agreement",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            self.stdout.write(
                self.style.ERROR("⛔ Realistic seeding is disabled in production mode.")
            )
            return

        self.stdout.write(
            self.style.WARNING("🌍 Starting realistic database population...")
        )
        self.stdout.write(
            f"   ↳ {options['properties']} Properties, {options['units_per_property']} units/prop, {options['tenants']} Tenants, {options['agreements']} Agreements"
        )

        try:
            with transaction.atomic():
                users = self._seed_users()
                # profiles = self._seed_profiles(users)
                owners = self._seed_owners(users)
                managers = self._seed_managers(users)
                tenants = self._seed_tenants(users, options["tenants"])
                payment_plans = self._seed_payment_plans()
                properties = self._seed_properties(options["properties"], owners)
                units = self._seed_units(properties, options["units_per_property"])
                agreements = self._seed_agreements(
                    units, tenants, payment_plans, options["agreements"]
                )
                self._seed_payments(agreements, options["payments_per_agreement"])
                self._assign_managers(managers, properties)

            self.stdout.write(
                self.style.SUCCESS("\n✅ Realistic database populated successfully!")
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ Failed to populate: {str(e)}"))
            raise

    # =========================================================================
    # 1. USERS & PROFILES
    # =========================================================================
    def _seed_users(self):
        self.stdout.write("  ↳ Creating Users...")
        users = {}
        roles = {
            "admin": ("admin", "System", "Admin", True, True),
            "landlord": ("landlord", "John", "Moukam", False, False),
            "manager": ("manager", "Grace", "Tchana", False, False),
        }
        for role_key, (username, first, last, is_staff, is_superuser) in roles.items():
            user, _ = User.objects.get_or_create(
                email=f"{username}@pms.local",
                defaults={
                    "username": username,
                    "first_name": first,
                    "last_name": last,
                    "role": role_key,
                    "is_active": True,
                    "is_staff": is_staff,
                    "is_superuser": is_superuser,
                },
            )
            if not user.has_usable_password():
                user.set_password(f"{username}123")
                user.save(update_fields=["password"])
            users[role_key] = user

        return users

    def _seed_profiles(self, users):
        self.stdout.write("  ↳ Creating Base Profiles...")
        for role, user in users.items():
            Profile.objects.get_or_create(
                user=user,
                defaults={
                    "phone_number": _rand_phone(),
                    "country": "CM",
                    "city": random.choice(CAMEROON_CITIES),
                    "address": f"{random.randint(10, 999)} {role.title()} St.",
                    "gender": random.choice(["male", "female", "other"]),
                },
            )

    # =========================================================================
    # 2. ROLE PROFILES (Owner, Manager, Tenant)
    # =========================================================================
    def _seed_owners(self, users):
        self.stdout.write("  ↳ Creating Owner Profile...")
        owner, _ = Owner.objects.get_or_create(
            user=users["landlord"],
            defaults={
                "preferred_payout_method": "bank_transfer",
                "mobile_money_number": _rand_phone(),
                "bank_account_name": f"{users['landlord'].first_name} {users['landlord'].last_name} LLC",
                "bank_name": random.choice(
                    ["Afriland First Bank", "Ecobank", "BICEC", "Société Générale"]
                ),
                "bank_account_number": "".join(random.choices(string.digits, k=10)),
                "bank_code": random.choice(["AFRIBANK", "ECOBANK", "BICEC", "SGCB"]),
                "tax_id": f"NIU-{random.randint(100000000, 999999999)}",
            },
        )
        return [owner]

    def _seed_managers(self, users):
        self.stdout.write("  ↳ Creating Manager Profile...")
        mgr, _ = Manager.objects.get_or_create(
            user=users["manager"],
            defaults={"commission_rate": Decimal("5.00"), "is_active": True},
        )
        return [mgr]

    def _seed_tenants(self, users, count):
        self.stdout.write(f"  ↳ Creating {count} Tenants...")
        tenants = []
        for i in range(1, count + 1):
            u, _ = User.objects.get_or_create(
                email=_rand_email("tenant", i),
                defaults={
                    "username": f"tenant{i}",
                    "first_name": random.choice(FIRST_NAMES),
                    "last_name": random.choice(LAST_NAMES),
                    "role": "tenant",
                    "is_active": True,
                },
            )
            if not u.has_usable_password():
                u.set_password("tenant123")
                u.save(update_fields=["password"])

            Profile.objects.get_or_create(
                user=u,
                defaults={
                    "phone_number": _rand_phone(),
                    "country": "CM",
                    "city": random.choice(CAMEROON_CITIES),
                },
            )

            t, _ = Tenant.objects.get_or_create(
                user=u,
                defaults={
                    "id_number": _rand_id_number(i),
                    "is_discoverable": random.choice([True, True, True, False]),
                    "is_verified": random.choice([True, False]),
                    "is_primary": True,
                    "emergency_contact_name": f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
                    "emergency_contact_phone": _rand_phone(),
                    "emergency_contact_relation": random.choice(
                        ["Parent", "Sibling", "Spouse"]
                    ),
                    "employer": random.choice(
                        [
                            "Orange Cameroon",
                            "MTN Cameroon",
                            "Ecowas Bank",
                            "UNICEF",
                            "Self-Employed",
                        ]
                    ),
                    "job_title": random.choice(
                        [
                            "Engineer",
                            "Accountant",
                            "Teacher",
                            "Developer",
                            "Nurse",
                            "Trader",
                        ]
                    ),
                    "monthly_income": _rand_decimal(150000, 2500000),
                    "guarantor_name": f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
                    "guarantor_phone": _rand_phone(),
                    "notes": "Seeded for realistic testing.",
                    "language": random.choice(["en", "fr"]),
                },
            )
            tenants.append(t)
        return tenants

    # =========================================================================
    # 3. PAYMENT PLANS & INSTALLMENTS
    # =========================================================================
    def _seed_payment_plans(self):
        self.stdout.write("  ↳ Creating Payment Plans...")
        plans = {}

        # Monthly Plan
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
        plans["monthly"] = monthly

        # Yearly Plan
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
        # Installments for Yearly
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
        plans["yearly"] = yearly
        return plans

    # =========================================================================
    # 4. PROPERTIES & OWNERSHIP
    # =========================================================================
    def _seed_properties(self, count, owners):
        self.stdout.write(f"  ↳ Creating {count} Properties...")
        properties = []
        for i in range(1, count + 1):
            prop_name = (
                f"{random.choice(FIRST_NAMES)} {random.choice(PROPERTY_NAMES)} {i}"
            )
            p, _ = Property.objects.get_or_create(
                name=prop_name,
                defaults={
                    "property_type": random.choice(PropertyType.values),
                    "description": f"Well-maintained {random.choice(PROPERTY_NAMES).lower()} in {random.choice(CAMEROON_CITIES)}.",
                    "address_line1": f"{random.randint(10, 999)} {random.choice(['Avenue', 'Rue', 'Boulevard'])} de la {random.choice(['Liberté', 'Indépendance', 'Réunification', 'Paix'])}",
                    "address_line2": f"Quartier {random.choice(['Akwa', 'Bonanjo', 'Melen', 'Nkwen', 'Bastos', 'Koumassi'])}",
                    "city": random.choice(CAMEROON_CITIES),
                    "state": random.choice(
                        ["Littoral", "Centre", "West", "Southwest", "Northwest", "East"]
                    ),
                    "country": "CM",
                    "postal_code": str(random.randint(1000, 99999)),
                    "has_generator": random.choice([True, True, False]),
                    "has_water_tank": random.choice([True, False]),
                    "amenities": _rand_json_list(),
                    "status": random.choice(["ACTIVE", "MAINTENANCE"]),
                    "starting_amount": _rand_decimal(50000, 300000),
                    "top_amount": _rand_decimal(500000, 1500000),
                    "is_active": True,
                    "language": random.choice(["en", "fr"]),
                },
            )
            PropertyOwnership.objects.get_or_create(
                property=p,
                owner=owners[0],
                defaults={"percentage": Decimal("100.00"), "is_primary": True},
            )
            properties.append(p)
        return properties

    # =========================================================================
    # 5. UNITS
    # =========================================================================
    def _seed_units(self, properties, count_per_prop):
        self.stdout.write("  ↳ Creating Units...")
        all_units = []
        for prop in properties:
            for i in range(1, count_per_prop + 1):
                floor = random.randint(1, 5)
                unit_num = f"{floor}{i:02d}"
                u, _ = Unit.objects.get_or_create(
                    property=prop,
                    unit_number=unit_num,
                    defaults={
                        "unit_type": random.choice(UnitType.values),
                        "floor": floor,
                        "size_m2": random.randint(25, 120),
                        "bedrooms": random.randint(1, 3),
                        "bathrooms": random.randint(1, 2),
                        "default_rent_amount": _rand_decimal(80000, 600000),
                        "default_security_deposit": _rand_decimal(50000, 300000),
                        "status": random.choices(
                            ["vacant", "occupied", "maintenance"], weights=[30, 60, 10]
                        )[0],
                        "amenities": _rand_json_list(),
                        "images": [],
                        "water_meter_number": f"WM-{random.randint(1000, 9999)}-{unit_num}",
                        "electricity_meter_number": f"EM-{random.randint(1000, 9999)}-{unit_num}",
                        "has_prepaid_meter": random.choice([True, False]),
                        "custom_fields": {
                            "orientation": random.choice(
                                ["North", "South", "East", "West"]
                            )
                        },
                        "language": random.choice(["en", "fr"]),
                    },
                )
                all_units.append(u)
        return all_units

    # =========================================================================
    # 6. RENTAL AGREEMENTS
    # =========================================================================
    def _seed_agreements(self, units, tenants, plans, count):
        self.stdout.write(f"  ↳ Creating {count} Rental Agreements...")
        agreements = []
        occupied_units = [u for u in units if u.status == "occupied"]
        # Fallback if not enough occupied units
        available_units = (
            occupied_units[:count] + units[: max(0, count - len(occupied_units))]
        )
        available_units = list(dict.fromkeys(available_units))[:count]

        for i in range(min(count, len(available_units))):
            unit = available_units[i]
            tenant = random.choice(tenants)
            plan = random.choice([plans["monthly"], plans["yearly"]])

            # Update unit status
            unit.status = "occupied"
            unit.save(update_fields=["status"])

            a, _ = RentalAgreement.objects.get_or_create(
                unit=unit,
                tenant=tenant,
                defaults={
                    "payment_plan": plan,
                    "coverage_end_date": date.today()
                    + timedelta(days=random.randint(30, 730)),
                    "installment_status": (
                        {"1": "completed", "2": "pending"}
                        if plan.mode == "yearly"
                        else {}
                    ),
                    "is_active": random.choice([True, True, False]),
                },
            )
            agreements.append(a)
        return agreements

    # =========================================================================
    # 7. PAYMENTS (Historical Realism)
    # =========================================================================
    def _seed_payments(self, agreements, per_agreement):
        self.stdout.write("  ↳ Creating Historical Payments...")
        for agg in agreements:
            base_amount = agg.unit.default_rent_amount
            for i in range(per_agreement):
                # Simulate historical periods going backwards
                months_ago = i * random.choice([1, 3, 6])
                p_start = date.today() - timedelta(days=30 * months_ago)
                p_end = p_start + timedelta(days=30)

                status = random.choice(PAYMENT_STATUSES)
                method = random.choice(PAYMENT_METHODS)
                min_amount = base_amount * Decimal("0.5")
                max_amount = base_amount * Decimal("1.2")

                amount = (
                    base_amount
                    if status == "completed"
                    else _rand_decimal(int(min_amount), int(max_amount))
                )

                Payment.objects.get_or_create(
                    agreement=agg,
                    period_start=p_start,
                    period_end=p_end,
                    amount=amount,
                    defaults={
                        "months_covered": Decimal("1.00"),
                        "payment_method": method,
                        "status": status,
                        "transaction_id": f"TXN-{random.choice(['MOMO', 'OM', 'BANK'])}-{random.randint(100000, 999999)}",
                        "mobile_provider": (
                            random.choice(MOBILE_PROVIDERS)
                            if "momo" in method or "orange" in method
                            else ""
                        ),
                        "mobile_phone": (
                            _rand_phone()
                            if "momo" in method or "orange" in method
                            else ""
                        ),
                        "mobile_reference": (
                            f"REF-{random.randint(100000, 999999)}"
                            if "momo" in method or "orange" in method
                            else ""
                        ),
                        "bank_name": (
                            random.choice(["Ecobank", "BICEC", "Afriland"])
                            if method == "bank_transfer"
                            else ""
                        ),
                        "notes": f"{'Historical' if i > 0 else 'Current'} {method.replace('_', ' ').title()} payment.",
                        "gateway_response": {
                            "code": 200,
                            "message": (
                                "Success" if status == "completed" else "Declined"
                            ),
                        },
                    },
                )

    # =========================================================================
    # 8. MANAGER ASSIGNMENTS
    # =========================================================================
    def _assign_managers(self, managers, properties):
        self.stdout.write("  ↳ Assigning Managers to Properties...")
        for prop in properties:
            # Assign 1-2 managers randomly
            mgrs = random.sample(managers, k=min(len(managers), random.randint(1, 2)))
            for m in mgrs:
                m.managed_properties.add(prop)
