# yourapp/management/commands/populate_test_data.py
import json
import logging
import os
import random
import time
from datetime import date, timedelta
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.db import transaction, IntegrityError
from faker import Faker
from faker.providers import phone_number

# Suppress noisy logs
logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
logging.getLogger("apps.rentals.signals").setLevel(logging.WARNING)
logging.getLogger("apps.users.signals").setLevel(logging.WARNING)

from apps.users.models import User, Profile, DataDeletionRequest
from apps.rentals.models import (
    PaymentTerm,
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
    Owner,
    Manager,
    Tenant,
)

User = get_user_model()
fake = Faker("en_US")
fake.add_provider(phone_number)

STATE_FILE = Path(".populate_state.json")


class Command(BaseCommand):
    help = "Smart resumable data population for development"

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete all existing data and reset state",
        )
        parser.add_argument(
            "--count", type=int, default=50, help="Base number of records"
        )
        parser.add_argument("--seed", type=int, default=42, help="Random seed")
        parser.add_argument(
            "--reset", action="store_true", help="Reset state without flushing data"
        )

    def handle(self, *args, **options):
        self.flush = options["flush"]
        self.base_count = options["count"]
        self.seed = options["seed"]
        self.reset_state = options["reset"]

        random.seed(self.seed)
        fake.seed_instance(self.seed)
        self.start_time = time.time()

        # Style shortcuts
        self.success = self.style.SUCCESS
        self.warning = self.style.WARNING
        self.error = self.style.ERROR
        self.info = self.style.NOTICE

        # Initialize or load state
        self.state = self._load_state()

        if self.flush:
            self._flush_all()
            self._reset_state()
        elif self.reset_state:
            self._reset_state()

        self.stdout.write(self.info("Starting smart data population..."))

        try:
            # Define sections in order
            self._run_section("payment_terms", self._create_payment_terms, total=4)
            self._run_section(
                "users", self._create_users, total=self._get_user_totals()
            )
            self._run_section(
                "vendors", self._create_vendors, total=max(1, self.base_count // 5)
            )
            self._run_section(
                "properties", self._create_properties, total=max(1, self.base_count)
            )
            self._run_section(
                "leases",
                self._create_leases,
                total=int(len(self._get_created_ids("unit")) * 0.7),
            )
            self._run_section(
                "payments", self._create_payments, total=None
            )  # dynamic total
            self._run_section(
                "maintenance",
                self._create_maintenance_requests,
                total=max(1, self.base_count * 2),
            )
            self._run_section(
                "expenses", self._create_expenses, total=max(1, self.base_count * 3)
            )
            self._run_section(
                "documents", self._create_documents, total=max(1, self.base_count * 2)
            )
            self._run_section(
                "misc", self._create_misc, total=max(1, self.base_count // 10)
            )

            # All done – delete state file
            if STATE_FILE.exists():
                STATE_FILE.unlink()
            elapsed = time.time() - self.start_time
            self.stdout.write(
                self.success(f"\n✅ All sections completed in {elapsed:.2f} seconds!")
            )

        except Exception as e:
            self.stdout.write(
                self.error(f"\n❌ Failed at section '{self.state['current_section']}'")
            )
            raise CommandError(f"Population failed: {e}")

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------
    def _load_state(self):
        """Load state from file or create new."""
        if STATE_FILE.exists() and not self.flush and not self.reset_state:
            with open(STATE_FILE) as f:
                state = json.load(f)
            self.stdout.write(
                self.info(f"📂 Resuming from previous state (seed {state.get('seed')})")
            )
            return state
        return {
            "seed": self.seed,
            "current_section": None,
            "sections": {},
            "created_ids": {},  # store created object IDs per model
        }

    def _save_state(self):
        """Write state to file."""
        with open(STATE_FILE, "w") as f:
            json.dump(self.state, f, indent=2)

    def _reset_state(self):
        """Delete state file and clear internal state."""
        if STATE_FILE.exists():
            STATE_FILE.unlink()
        self.state = {
            "seed": self.seed,
            "current_section": None,
            "sections": {},
            "created_ids": {},
        }
        self.stdout.write(self.warning("State reset."))

    def _get_created_ids(self, model_name):
        """Return set of IDs already created for a given model."""
        return set(self.state["created_ids"].get(model_name, []))

    def _add_created_id(self, model_name, obj_id):
        """Record a created object ID."""
        if model_name not in self.state["created_ids"]:
            self.state["created_ids"][model_name] = []
        # Store as string because UUID may not be JSON serializable
        self.state["created_ids"][model_name].append(str(obj_id))
        self._save_state()

    def _run_section(self, name, func, total):
        """Run a section if not already completed, with progress tracking."""
        self.state["current_section"] = name
        section = self.state["sections"].get(
            name, {"completed": False, "last_index": 0, "total": total}
        )

        if section.get("completed"):
            self.stdout.write(self.info(f"⏭️  Skipping {name} (already completed)"))
            return

        self.stdout.write(self.info(f"\n▶️  Starting {name}..."))
        start_index = section.get("last_index", 0)
        if total is not None and start_index >= total:
            self.state["sections"][name] = {
                "completed": True,
                "last_index": total,
                "total": total,
            }
            self._save_state()
            return

        # Call the section function with progress
        new_last_index = func(start_index, total)

        # Mark completed
        self.state["sections"][name] = {
            "completed": True,
            "last_index": new_last_index,
            "total": total,
        }
        self._save_state()
        self.stdout.write(self.success(f"  ✅ {name} completed"))

    # ------------------------------------------------------------------
    # Progress display
    # ------------------------------------------------------------------
    def _log_progress(self, current, total, message):
        if total is None:
            self.stdout.write(f"\r  ⟳ {current} {message}", ending="")
        else:
            percent = (current / total) * 100 if total else 0
            bar_length = 20
            filled = int(bar_length * current // total) if total else 0
            bar = "█" * filled + "░" * (bar_length - filled)
            self.stdout.write(f"\r  {bar} {current}/{total} {message}", ending="")
        if current == total:
            self.stdout.write()

    # ------------------------------------------------------------------
    # Data creation methods (now resumable)
    # ------------------------------------------------------------------
    def _create_payment_terms(self, start, total):
        """Payment terms are static – create if not exist."""
        terms = [
            {"name": "Monthly", "interval_months": 1, "description": "Pay every month"},
            {
                "name": "Quarterly",
                "interval_months": 3,
                "description": "Pay every 3 months",
            },
            {
                "name": "Yearly",
                "interval_months": 12,
                "description": "Pay once per year",
            },
            {
                "name": "Weekly",
                "interval_months": 0.25,
                "description": "Pay every week",
            },
        ]
        self.payment_terms = {}
        for term_data in terms:
            term, _ = PaymentTerm.objects.get_or_create(
                name=term_data["name"],
                defaults={
                    "interval_months": term_data["interval_months"],
                    "description": term_data["description"],
                },
            )
            self.payment_terms[term.name.lower()] = term
            self._add_created_id("paymentterm", term.id)
        return len(terms)

    def _get_user_totals(self):
        """Calculate total users to create."""
        return (
            max(1, self.base_count // 10)  # owners
            + max(1, self.base_count // 15)  # managers
            + self.base_count * 2  # tenants
            + max(1, self.base_count // 5)
        )  # regular

    def _create_users(self, start, total):
        """Create users with roles, resuming from start index."""
        # We'll create users sequentially, each with a role based on index ranges
        roles_ranges = [
            ("owner", max(1, self.base_count // 10)),
            ("manager", max(1, self.base_count // 15)),
            ("tenant", self.base_count * 2),
            ("user", max(1, self.base_count // 5)),
        ]
        # Flatten to a list of roles
        role_sequence = []
        for role, count in roles_ranges:
            role_sequence.extend([role] * count)

        self.owners = []
        self.managers = []
        self.tenants = []
        self.users = []

        created_ids = self._get_created_ids("user")

        for i in range(start, total):
            self._log_progress(i + 1, total, f"users (role: {role_sequence[i]})")
            role = role_sequence[i]

            # Try to create user with unique email
            for attempt in range(10):
                try:
                    user = self._create_single_user(role)
                    break
                except IntegrityError:
                    # Email duplicate, try another
                    continue
            else:
                raise Exception("Could not generate unique email after 10 attempts")

            self._add_created_id("user", user.id)
            self.users.append(user)

            # Create role-specific profile
            if role == "owner":
                owner = Owner.objects.create(
                    user=user,
                    preferred_payout_method=random.choice(
                        ["bank_transfer", "mtn_momo", "orange_money"]
                    ),
                    mobile_money_number=(
                        fake.phone_number() if random.random() > 0.3 else None
                    ),
                    bank_account_name=fake.name(),
                    bank_name=fake.company(),
                    bank_account_number=fake.iban(),
                    bank_code=fake.swift(),
                    tax_id=fake.random_number(digits=9, fix_len=True),
                )
                self.owners.append(owner)
                self._add_created_id("owner", owner.id)
            elif role == "manager":
                manager = Manager.objects.create(
                    user=user,
                    commission_rate=round(random.uniform(5, 15), 2),
                    is_active=random.random() > 0.1,
                )
                self.managers.append(manager)
                self._add_created_id("manager", manager.id)
            elif role == "tenant":
                tenant = Tenant.objects.create(
                    user=user,
                    id_number=fake.random_number(digits=8, fix_len=True),
                    id_document=None,
                    emergency_contact_name=fake.name(),
                    emergency_contact_phone=fake.phone_number(),
                    emergency_contact_relation=random.choice(
                        ["Spouse", "Parent", "Sibling", "Friend"]
                    ),
                    employer=fake.company(),
                    job_title=fake.job(),
                    monthly_income=random.randint(100000, 2000000),
                    guarantor_name=fake.name() if random.random() > 0.3 else "",
                    guarantor_phone=(
                        fake.phone_number() if random.random() > 0.5 else ""
                    ),
                    guarantor_email=fake.email() if random.random() > 0.5 else "",
                    notes=fake.text(max_nb_chars=200) if random.random() > 0.7 else "",
                    language=random.choice(["en", "fr"]),
                    emergency_contact_name_fr=(
                        fake.name() if random.random() > 0.5 else ""
                    ),
                    employer_fr=fake.company() if random.random() > 0.5 else "",
                    job_title_fr=fake.job() if random.random() > 0.5 else "",
                    notes_fr=(
                        fake.text(max_nb_chars=200) if random.random() > 0.5 else ""
                    ),
                    guarantor_name_fr=fake.name() if random.random() > 0.3 else "",
                )
                self.tenants.append(tenant)
                self._add_created_id("tenant", tenant.id)

            # Save state after each user
            self.state["sections"]["users"] = {"last_index": i + 1, "total": total}
            self._save_state()

        return total

    def _create_single_user(self, role):
        """Create one user with guaranteed unique email."""
        first_name = fake.first_name()
        last_name = fake.last_name()
        # Generate email with a random suffix to avoid collisions
        local_part = f"{first_name.lower()}.{last_name.lower()}"
        domain = fake.free_email_domain()
        email = f"{local_part}.{random.randint(1,999999)}@{domain}"

        user = User.objects.create_user(
            email=email,
            password="password123",
            username=f"{local_part}{random.randint(1,999)}",
            first_name=first_name,
            last_name=last_name,
            role=role,
            is_active=True,
            is_staff=(role in ["admin", "moderator"]),
        )
        # Update profile
        profile = user.profile
        profile.bio = fake.text(max_nb_chars=200) if random.random() > 0.3 else ""
        profile.gender = random.choice(["male", "female", "other"])
        profile.country = "CM"
        profile.city = random.choice(
            ["Yaoundé", "Douala", "Bamenda", "Garoua", "Kousséri"]
        )
        profile.address = fake.street_address()
        profile.phone_number = fake.phone_number()
        profile.profile_photo = f'https://randomuser.me/api/portraits/{random.choice(["men","women"])}/{random.randint(1,99)}.jpg'
        profile.save()
        return user

    def _create_vendors(self, start, total):
        """Create vendors."""
        created_ids = self._get_created_ids("vendor")
        self.vendors = list(Vendor.objects.filter(id__in=created_ids))  # load existing

        for i in range(start, total):
            self._log_progress(i + 1, total, "vendors")
            vendor = Vendor.objects.create(
                company_name=fake.company() if random.random() > 0.2 else "",
                contact_name=fake.name(),
                phone=fake.phone_number(),
                email=fake.email() if random.random() > 0.3 else "",
                address=fake.address(),
                specialties=random.sample(
                    ["plumbing", "electrical", "cleaning", "painting", "carpentry"],
                    k=random.randint(1, 3),
                ),
                notes=fake.text(max_nb_chars=100) if random.random() > 0.5 else "",
                is_active=random.random() > 0.1,
                language=random.choice(["en", "fr"]),
                company_name_fr=fake.company() if random.random() > 0.5 else "",
                contact_name_fr=fake.name() if random.random() > 0.5 else "",
                address_fr=fake.address() if random.random() > 0.5 else "",
                specialties_fr=[],
                notes_fr=fake.text(max_nb_chars=100) if random.random() > 0.5 else "",
            )
            self.vendors.append(vendor)
            self._add_created_id("vendor", vendor.id)

            self.state["sections"]["vendors"] = {"last_index": i + 1, "total": total}
            self._save_state()
        return total

    def _create_properties(self, start, total):
        """Create properties and their units."""
        # Load existing owners and managers from state IDs
        owner_ids = self._get_created_ids("owner")
        self.owners = list(Owner.objects.filter(id__in=owner_ids))
        manager_ids = self._get_created_ids("manager")
        self.managers = list(Manager.objects.filter(id__in=manager_ids))

        created_prop_ids = self._get_created_ids("property")
        self.properties = list(Property.objects.filter(id__in=created_prop_ids))
        created_unit_ids = self._get_created_ids("unit")
        self.units = list(Unit.objects.filter(id__in=created_unit_ids))

        for i in range(start, total):
            self._log_progress(i + 1, total, "properties")
            prop = self._create_single_property()
            self.properties.append(prop)
            self._add_created_id("property", prop.id)

            # Create units for this property
            if prop.property_type == "land":
                unit_count = 0
            elif prop.property_type == "house":
                unit_count = random.randint(1, 3)
            else:
                unit_count = random.randint(2, 10)

            for u in range(unit_count):
                unit = self._create_single_unit(prop, u + 1)
                self.units.append(unit)
                self._add_created_id("unit", unit.id)

            self.state["sections"]["properties"] = {"last_index": i + 1, "total": total}
            self._save_state()
        return total

    def _create_single_property(self):
        prop_type = random.choice(["apartment", "house", "commercial", "land", "other"])
        city = random.choice(["Yaoundé", "Douala", "Bamenda", "Garoua", "Kousséri"])
        name = f"{prop_type.title()} in {city} - {fake.street_name()}"
        prop = Property.objects.create(
            name=name,
            property_type=prop_type,
            description=fake.text(max_nb_chars=500) if random.random() > 0.3 else "",
            address_line1=fake.street_address(),
            address_line2=fake.secondary_address() if random.random() > 0.5 else "",
            city=city,
            state=(
                "Centre"
                if city == "Yaoundé"
                else "Littoral" if city == "Douala" else "North-West"
            ),
            country="CM",
            postal_code=fake.postcode(),
            has_generator=random.random() > 0.5,
            has_water_tank=random.random() > 0.6,
            amenities=random.sample(
                ["parking", "security", "pool", "gym", "elevator"],
                k=random.randint(0, 4),
            ),
            images=[
                f"https://picsum.photos/400/300?random={random.randint(1,1000)}"
                for _ in range(random.randint(1, 3))
            ],
            is_active=random.random() > 0.05,
            language=random.choice(["en", "fr"]),
            name_fr=fake.catch_phrase() if random.random() > 0.5 else "",
            description_fr=fake.text(max_nb_chars=500) if random.random() > 0.5 else "",
            amenities_fr=[],
        )
        # Assign owners
        if self.owners:
            num_owners = random.randint(1, min(3, len(self.owners)))
            selected = random.sample(self.owners, num_owners)
            total_percent = 0
            for idx, owner in enumerate(selected):
                if idx == len(selected) - 1:
                    percent = 100 - total_percent
                else:
                    max_possible = 90 - total_percent
                    if max_possible <= 10:
                        percent = 10
                    else:
                        percent = random.randint(10, max_possible)
                total_percent += percent
                po = PropertyOwnership.objects.create(
                    property=prop,
                    owner=owner,
                    percentage=percent,
                    is_primary=(idx == 0),
                )
                self._add_created_id("propertyownership", po.id)
        return prop

    def _create_single_unit(self, prop, idx):
        unit_type = random.choice(
            ["studio", "1_bed", "2_bed", "3_bed", "shop", "office", "other"]
        )
        # Fix random.choices usage
        status = random.choices(
            ["vacant", "occupied", "maintenance"], weights=[0.3, 0.6, 0.1]
        )[0]
        unit = Unit.objects.create(
            property=prop,
            unit_number=f"{idx:02d}",
            unit_type=unit_type,
            floor=random.randint(0, 5) if prop.property_type != "house" else None,
            size_m2=random.randint(20, 200),
            bedrooms=(
                0
                if unit_type in ["shop", "office", "other"]
                else int(unit_type[0]) if unit_type[0].isdigit() else 0
            ),
            bathrooms=random.randint(1, 3) if "bed" in unit_type else 1,
            default_rent_amount=random.randint(50000, 500000),
            default_payment_term=random.choice(list(self.payment_terms.values())),
            default_security_deposit=random.randint(50000, 1000000),
            status=status,
            amenities=random.sample(
                ["aircon", "wifi", "furnished", "balcony"], k=random.randint(0, 3)
            ),
            images=[
                f"https://picsum.photos/400/300?random={random.randint(1,1000)}"
                for _ in range(random.randint(1, 2))
            ],
            water_meter_number=(
                fake.bothify(text="WAT-####-??") if random.random() > 0.5 else ""
            ),
            electricity_meter_number=(
                fake.bothify(text="ELEC-####-??") if random.random() > 0.5 else ""
            ),
            has_prepaid_meter=random.random() > 0.7,
            custom_fields={},
            language=random.choice(["en", "fr"]),
            amenities_fr=[],
        )
        return unit

    def _create_leases(self, start, total):
        """Create leases linking units and tenants."""
        # Load created tenants and units
        tenant_ids = self._get_created_ids("tenant")
        self.tenants = list(Tenant.objects.filter(id__in=tenant_ids))
        unit_ids = self._get_created_ids("unit")
        self.units = list(Unit.objects.filter(id__in=unit_ids))

        if not self.units or not self.tenants:
            self.stdout.write(self.warning("  ⚠️ No units/tenants to create leases"))
            return 0

        lease_units = random.sample(self.units, min(total, len(self.units)))
        self.leases = []
        self.lease_tenants = []

        created_lease_ids = self._get_created_ids("lease")
        self.leases = list(Lease.objects.filter(id__in=created_lease_ids))

        for i in range(start, min(total, len(lease_units))):
            self._log_progress(i + 1, total, "leases")
            unit = lease_units[i]
            start_date = fake.date_between(start_date="-2y", end_date="today")
            duration = random.choice([3, 6, 12, 24])
            end_date = start_date + timedelta(days=30 * duration)
            term = unit.default_payment_term or random.choice(
                list(self.payment_terms.values())
            )
            rent = unit.default_rent_amount * (term.interval_months or 1)

            # Fix random.choices usage
            status = random.choices(
                ["active", "expired", "terminated", "renewed"],
                weights=[0.6, 0.2, 0.1, 0.1],
            )[0]

            lease = Lease.objects.create(
                unit=unit,
                start_date=start_date,
                end_date=end_date,
                payment_term=term,
                rent_amount=rent,
                due_day=random.randint(1, 28),
                security_deposit=unit.default_security_deposit
                or random.randint(50000, 500000),
                deposit_paid=random.random() > 0.2,
                late_fee_type=random.choice(["fixed", "percentage"]),
                late_fee_value=(
                    random.randint(5000, 50000) if random.random() > 0.3 else 0
                ),
                utilities_included=random.sample(
                    ["water", "electricity", "internet"], k=random.randint(0, 2)
                ),
                documents=[f"https://example.com/lease_{random.randint(1,100)}.pdf"],
                status=status,
                termination_reason=fake.sentence() if random.random() > 0.8 else "",
            )
            self.leases.append(lease)
            self._add_created_id("lease", lease.id)

            # Add tenants
            num_tenants = random.randint(1, min(3, len(self.tenants)))
            for idx, tenant in enumerate(random.sample(self.tenants, num_tenants)):
                lt = LeaseTenant.objects.create(
                    lease=lease,
                    tenant=tenant,
                    is_primary=(idx == 0),
                    signed_at=timezone.now() - timedelta(days=random.randint(0, 30)),
                )
                self.lease_tenants.append(lt)
                self._add_created_id("leasetenant", lt.id)

            self.state["sections"]["leases"] = {"last_index": i + 1, "total": total}
            self._save_state()

        return min(total, len(lease_units))

    def _create_payments(self, start, total):
        """Create payments for active leases."""
        lease_ids = self._get_created_ids("lease")
        self.leases = list(Lease.objects.filter(id__in=lease_ids, status="active"))

        if not self.leases:
            return 0

        payments_created = 0
        today = date.today()
        # We'll process each lease and create payments; total is dynamic, so we track payments count
        for lease in self.leases:
            current = lease.start_date
            while current < today and current < lease.end_date:
                interval = lease.payment_term.interval_months
                period_end = current + timedelta(days=30 * interval) - timedelta(days=1)
                if period_end > lease.end_date:
                    period_end = lease.end_date

                if random.random() < 0.9:
                    # Fix random.choices
                    status = random.choices(
                        ["pending", "completed", "failed"], weights=[0.1, 0.85, 0.05]
                    )[0]
                    payment = Payment.objects.create(
                        lease=lease,
                        tenant=(
                            random.choice(lease.tenants.all())
                            if lease.tenants.exists()
                            else None
                        ),
                        amount=lease.rent_amount,
                        payment_date=current + timedelta(days=random.randint(0, 10)),
                        payment_method=random.choice(
                            ["mtn_momo", "orange_money", "bank_transfer", "cash"]
                        ),
                        payment_type="rent",
                        status=status,
                        period_start=current,
                        period_end=period_end,
                        transaction_id=fake.uuid4() if status != "pending" else "",
                        mobile_provider=(
                            random.choice(["MTN", "Orange"])
                            if random.random() > 0.5
                            else ""
                        ),
                        mobile_phone=(
                            fake.phone_number() if random.random() > 0.5 else ""
                        ),
                        mobile_reference=fake.uuid4() if random.random() > 0.5 else "",
                        bank_name=fake.company() if random.random() > 0.5 else "",
                        check_number=(
                            fake.bothify(text="CHK-####")
                            if random.random() > 0.5
                            else ""
                        ),
                        notes=(
                            fake.text(max_nb_chars=100) if random.random() > 0.7 else ""
                        ),
                        gateway_response=(
                            {} if random.random() > 0.5 else {"ref": fake.uuid4()}
                        ),
                    )
                    payments_created += 1
                    self._add_created_id("payment", payment.id)

                    # Progress display (no total)
                    self._log_progress(payments_created, None, "payments created")

                current = period_end + timedelta(days=1)

        return payments_created  # return count as "last_index"

    def _create_maintenance_requests(self, start, total):
        """Create maintenance requests."""
        unit_ids = self._get_created_ids("unit")
        self.units = list(Unit.objects.filter(id__in=unit_ids))
        tenant_ids = self._get_created_ids("tenant")
        self.tenants = list(Tenant.objects.filter(id__in=tenant_ids))
        manager_ids = self._get_created_ids("manager")
        self.managers = list(Manager.objects.filter(id__in=manager_ids))
        vendor_ids = self._get_created_ids("vendor")
        self.vendors = list(Vendor.objects.filter(id__in=vendor_ids))

        created_ids = self._get_created_ids("maintenancerequest")

        for i in range(start, total):
            self._log_progress(i + 1, total, "maintenance requests")
            unit = random.choice(self.units)
            tenant = (
                random.choice(self.tenants)
                if self.tenants and random.random() > 0.3
                else None
            )
            manager = (
                random.choice(self.managers)
                if self.managers and random.random() > 0.3
                else None
            )
            vendor = (
                random.choice(self.vendors)
                if self.vendors and random.random() > 0.5
                else None
            )
            status = random.choice(
                ["submitted", "assigned", "in_progress", "completed", "cancelled"]
            )
            priority = random.choice(["low", "medium", "high", "emergency"])

            req = MaintenanceRequest.objects.create(
                unit=unit,
                tenant=tenant,
                requested_by_manager=manager,
                title=fake.sentence(nb_words=6),
                description=fake.text(max_nb_chars=300),
                priority=priority,
                status=status,
                photos=[
                    f"https://picsum.photos/400/300?random={random.randint(1,1000)}"
                    for _ in range(random.randint(0, 2))
                ],
                assigned_vendor=vendor,
                estimated_cost=(
                    random.randint(10000, 200000) if random.random() > 0.3 else None
                ),
                actual_cost=(
                    random.randint(10000, 200000) if status == "completed" else None
                ),
                approved_by=manager if random.random() > 0.3 else None,
                approved_at=(
                    timezone.now() - timedelta(days=random.randint(1, 30))
                    if random.random() > 0.5
                    else None
                ),
                completed_at=(
                    timezone.now() - timedelta(days=random.randint(1, 30))
                    if status == "completed"
                    else None
                ),
                notes=fake.text(max_nb_chars=150) if random.random() > 0.5 else "",
                language=random.choice(["en", "fr"]),
                title_fr=fake.sentence(nb_words=6) if random.random() > 0.5 else "",
                description_fr=(
                    fake.text(max_nb_chars=300) if random.random() > 0.5 else ""
                ),
            )
            self._add_created_id("maintenancerequest", req.id)

            self.state["sections"]["maintenance"] = {
                "last_index": i + 1,
                "total": total,
            }
            self._save_state()
        return total

    def _create_expenses(self, start, total):
        """Create expenses."""
        prop_ids = self._get_created_ids("property")
        self.properties = list(Property.objects.filter(id__in=prop_ids))
        vendor_ids = self._get_created_ids("vendor")
        self.vendors = list(Vendor.objects.filter(id__in=vendor_ids))

        created_ids = self._get_created_ids("expense")

        for i in range(start, total):
            self._log_progress(i + 1, total, "expenses")
            prop = random.choice(self.properties)
            unit = (
                random.choice(prop.units.all())
                if prop.units.exists() and random.random() > 0.5
                else None
            )
            vendor = (
                random.choice(self.vendors)
                if self.vendors and random.random() > 0.5
                else None
            )
            category = random.choice(
                [
                    "maintenance",
                    "utility",
                    "tax",
                    "insurance",
                    "management_fee",
                    "other",
                ]
            )
            is_reimbursable = random.random() > 0.7

            exp = Expense.objects.create(
                property=prop,
                unit=unit,
                category=category,
                amount=random.randint(5000, 500000),
                expense_date=fake.date_between(start_date="-1y", end_date="today"),
                description=fake.sentence() if random.random() > 0.3 else "",
                vendor=vendor,
                receipt=None,
                is_reimbursable=is_reimbursable,
                reimbursed=random.random() > 0.5 if is_reimbursable else False,
                language=random.choice(["en", "fr"]),
                description_fr=fake.sentence() if random.random() > 0.5 else "",
            )
            self._add_created_id("expense", exp.id)

            self.state["sections"]["expenses"] = {"last_index": i + 1, "total": total}
            self._save_state()
        return total

    def _create_documents(self, start, total):
        """Create documents."""
        prop_ids = self._get_created_ids("property")
        self.properties = list(Property.objects.filter(id__in=prop_ids))
        unit_ids = self._get_created_ids("unit")
        self.units = list(Unit.objects.filter(id__in=unit_ids))
        lease_ids = self._get_created_ids("lease")
        self.leases = list(Lease.objects.filter(id__in=lease_ids))
        tenant_ids = self._get_created_ids("tenant")
        self.tenants = list(Tenant.objects.filter(id__in=tenant_ids))
        user_ids = self._get_created_ids("user")
        self.users = list(User.objects.filter(id__in=user_ids))

        ctypes = {
            "property": ContentType.objects.get_for_model(Property),
            "unit": ContentType.objects.get_for_model(Unit),
            "lease": ContentType.objects.get_for_model(Lease),
            "tenant": ContentType.objects.get_for_model(Tenant),
        }

        created_ids = self._get_created_ids("document")

        for i in range(start, total):
            self._log_progress(i + 1, total, "documents")
            model_type = random.choice(["property", "unit", "lease", "tenant"])
            ct = ctypes[model_type]
            obj = None
            if model_type == "property" and self.properties:
                obj = random.choice(self.properties)
            elif model_type == "unit" and self.units:
                obj = random.choice(self.units)
            elif model_type == "lease" and self.leases:
                obj = random.choice(self.leases)
            elif model_type == "tenant" and self.tenants:
                obj = random.choice(self.tenants)
            if not obj:
                continue

            doc = Document.objects.create(
                content_type=ct,
                object_id=obj.id,
                name=fake.catch_phrase(),
                file=f"https://example.com/documents/{fake.uuid4()}.pdf",
                description=(
                    fake.text(max_nb_chars=150) if random.random() > 0.5 else ""
                ),
                uploaded_by=random.choice(self.users) if self.users else None,
            )
            self._add_created_id("document", doc.id)

            self.state["sections"]["documents"] = {"last_index": i + 1, "total": total}
            self._save_state()
        return total

    def _create_misc(self, start, total):
        """Create data deletion requests."""
        user_ids = self._get_created_ids("user")
        self.users = list(User.objects.filter(id__in=user_ids))

        created_ids = self._get_created_ids("datadeletionrequest")

        for i in range(start, total):
            self._log_progress(i + 1, total, "deletion requests")
            user = (
                random.choice(self.users)
                if self.users and random.random() > 0.3
                else None
            )
            email = user.email if user else fake.email()
            req = DataDeletionRequest.objects.create(
                user=user,
                email=email,
                request_type=random.choice(["account", "data"]),
                status=random.choice(
                    ["pending", "processing", "completed", "rejected"]
                ),
                data_to_delete={
                    "fields": random.sample(
                        ["profile", "payments", "leases"], k=random.randint(1, 3)
                    )
                },
                verified_at=(
                    timezone.now() - timedelta(days=random.randint(1, 10))
                    if random.random() > 0.5
                    else None
                ),
                processed_at=(
                    timezone.now() - timedelta(days=random.randint(1, 5))
                    if random.random() > 0.5
                    else None
                ),
                notes=fake.text(max_nb_chars=100) if random.random() > 0.7 else "",
            )
            self._add_created_id("datadeletionrequest", req.id)

            self.state["sections"]["misc"] = {"last_index": i + 1, "total": total}
            self._save_state()
        return total

    def _flush_all(self):
        """Delete all data in correct order."""
        models_to_flush = [
            Document,
            Payment,
            LeaseTenant,
            Lease,
            MaintenanceRequest,
            Expense,
            PropertyOwnership,
            Unit,
            Property,
            Vendor,
            Manager,
            Tenant,
            Owner,
            DataDeletionRequest,
            Profile,
            User,
            PaymentTerm,
        ]
        for model in models_to_flush:
            count, _ = model.objects.all().delete()
            self.stdout.write(f"  🗑️ Deleted {count} {model.__name__} records")
