from apps.payments.models import SubscriptionPlan

# Create plans
plans_data = [
    {
        "name": "Basic",
        "description": "Perfect for individual landlords with a small portfolio. Affordable and easy to use.",
        "monthly_price": 5000,
        "features": [
            "Up to 5 units",
            "Property listings (manual)",
            "Manual payment tracking",
            "Basic occupancy reports",
            "Bilingual interface (English/French)",
            "Digital lease agreements",
            "Email support",
        ],
        "is_active": True,
    },
    {
        "name": "Professional",
        "description": "Ideal for growing landlords with multiple properties. Automate rent collection and maintenance.",
        "monthly_price": 15000,
        "features": [
            "Up to 20 units",
            "Automated mobile money collection (MTN MoMo, Orange Money)",
            "Expense tracking",
            "Advanced financial reports",
            "Automated rent reminders",
            "Maintenance request management",
            "Tenant mobile app access",
            "Bulk SMS/email campaigns (up to 500/mo)",
            "Priority email & phone support",
        ],
        "is_active": True,
    },
    {
        "name": "Business",
        "description": "For agencies and large portfolios. Full automation, API access, and dedicated support.",
        "monthly_price": 30000,
        "features": [
            "Unlimited units",
            "Everything in Professional",
            "API access for custom integrations",
            "Multi‑user accounts (teams)",
            "Advanced tenant screening & credit checks",
            "Custom report builder",
            "Dedicated account manager",
            "24/7 phone support",
            "Bulk SMS/email campaigns (unlimited)",
            "Priority listing on tenant portal",
        ],
        "is_active": True,
    },
]

for data in plans_data:
    plan, created = SubscriptionPlan.objects.get_or_create(
        name=data["name"], defaults=data
    )
    if created:
        print(f"✅ Created plan: {plan.name} – {plan.monthly_price} XAF/mo")
    else:
        print(f"⚠️ Plan already exists: {plan.name} (updated if needed)")
        # Optionally update existing plan
        for key, value in data.items():
            setattr(plan, key, value)
        plan.save()
        print(f"   → Updated to latest data")

print("\n🎉 All subscription plans are ready!")
