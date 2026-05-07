from decimal import Decimal
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from django.db.models import Sum, Count, Q, F, DecimalField
from django.db.models.functions import TruncMonth, TruncDate
from django.utils import timezone
from apps.payments.models import Payment, RentalAgreement
from apps.reports.models import Expense
from apps.properties.models import Property, Unit, Owner
from apps.maintenance.models import MaintenanceRequest
from apps.core.base_service import BaseService
from apps.payments.repositories import PaymentRepository, RentalAgreementRepository
from apps.reports.repositories import ExpenseRepository


class FinancialReportService:
    """Service for generating financial and operational reports."""

    def __init__(self):
        self.payment_repo = PaymentRepository()
        self.expense_repo = ExpenseRepository()
        self.agreement_repo = RentalAgreementRepository()

    def get_property_summary(
        self,
        property_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        group_by: str = "month",
    ) -> Dict[str, Any]:
        """
        Returns financial summary for a property over a date range.
        group_by: "month" (default) or "day"
        """
        if not start_date:
            start_date = timezone.now() - timedelta(days=365)
        if not end_date:
            end_date = timezone.now()

        # Ensure property exists and user has permission (handled in view)
        # 1. Income from completed payments
        income_qs = Payment.objects.filter(
            agreement__unit__property_id=property_id,
            status="completed",
            payment_date__range=[start_date, end_date],
        )

        # 2. Expenses
        expense_qs = Expense.objects.filter(
            property_id=property_id, expense_date__range=[start_date, end_date]
        )

        # 3. Maintenance requests (costs)
        maintenance_qs = MaintenanceRequest.objects.filter(
            unit__property_id=property_id, created_at__range=[start_date, end_date]
        )

        # Grouping logic
        if group_by == "month":
            trunc_func = TruncMonth
            date_field_income = "payment_date"
            date_field_expense = "expense_date"
            date_field_maint = "created_at"
        else:  # day
            trunc_func = TruncDate

        # Aggregate income by period
        income_by_period = (
            income_qs.annotate(period=trunc_func(date_field_income))
            .values("period")
            .annotate(
                total=Sum("amount"),
                platform_fees=Sum("fee_breakdown__platform_fee"),
                gateway_fees=Sum("fee_breakdown__gateway_fee"),
                landlord_net=Sum("net_landlord_amount"),
            )
            .order_by("period")
        )

        # Aggregate expenses by period
        expenses_by_period = (
            expense_qs.annotate(period=trunc_func(date_field_expense))
            .values("period", "category")
            .annotate(total=Sum("amount"))
            .order_by("period")
        )

        # Aggregate maintenance costs (approved/completed)
        maint_by_period = (
            maintenance_qs.filter(
                status__in=["completed", "in_progress"], actual_cost__isnull=False
            )
            .annotate(period=trunc_func(date_field_maint))
            .values("period")
            .annotate(total_cost=Sum("actual_cost"), count=Count("id"))
            .order_by("period")
        )

        # Build time series
        periods = self._generate_periods(start_date, end_date, group_by)

        income_series = []
        expense_series = []
        maint_series = []
        net_series = []

        for period in periods:
            period_key = period.isoformat()[:10]  # YYYY-MM-DD or YYYY-MM
            # Income
            inc = next(
                (
                    i
                    for i in income_by_period
                    if i["period"].isoformat()[:10] == period_key
                ),
                None,
            )
            income_val = float(inc["total"]) if inc else 0.0
            # Expenses
            exp = [
                e
                for e in expenses_by_period
                if e["period"].isoformat()[:10] == period_key
            ]
            expense_val = sum(float(e["total"]) for e in exp)
            # Maintenance
            maint = next(
                (
                    m
                    for m in maint_by_period
                    if m["period"].isoformat()[:10] == period_key
                ),
                None,
            )
            maint_val = float(maint["total_cost"]) if maint else 0.0

            income_series.append(income_val)
            expense_series.append(expense_val)
            maint_series.append(maint_val)
            net_series.append(income_val - expense_val - maint_val)

        # Compute occupancy
        units = Unit.objects.filter(property_id=property_id)
        unit_ids = list(units.values_list("id", flat=True))
        occupancy_series = self._compute_occupancy_series(
            unit_ids, start_date, end_date, group_by
        )

        return {
            "property_id": str(property_id),
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "group_by": group_by,
            },
            "labels": [
                p.strftime("%b %Y") if group_by == "month" else p.strftime("%Y-%m-%d")
                for p in periods
            ],
            "income": income_series,
            "expenses": expense_series,
            "maintenance_costs": maint_series,
            "net": net_series,
            "occupancy": occupancy_series,
        }

    def get_owner_overview(
        self,
        owner_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Aggregate across all properties owned by a landlord."""
        from apps.properties.models import PropertyOwnership

        owned_properties = Property.objects.filter(ownership_records__owner_id=owner_id)
        property_ids = list(owned_properties.values_list("id", flat=True))

        total_income = 0
        total_expenses = 0
        total_maintenance = 0
        total_net = 0

        property_details = []
        for prop_id in property_ids:
            summary = self.get_property_summary(
                prop_id, start_date, end_date, group_by="month"
            )
            # Sum totals across all periods
            total_income += sum(summary["income"])
            total_expenses += sum(summary["expenses"])
            total_maintenance += sum(summary["maintenance_costs"])
            total_net += sum(summary["net"])

            property_details.append(
                {
                    "property_id": prop_id,
                    "name": Property.objects.get(id=prop_id).name,
                    "total_income": sum(summary["income"]),
                    "total_expenses": sum(summary["expenses"]),
                    "total_maintenance": sum(summary["maintenance_costs"]),
                    "net": sum(summary["net"]),
                }
            )

        return {
            "owner_id": str(owner_id),
            "overall": {
                "total_income": total_income,
                "total_expenses": total_expenses,
                "total_maintenance": total_maintenance,
                "net": total_net,
            },
            "properties": property_details,
        }

    def get_receipt_data(self, payment_id: str) -> Dict[str, Any]:
        """Returns complete data for a single payment receipt, including template config."""
        payment = Payment.objects.select_related(
            "agreement__unit__property", "agreement__tenant__user"
        ).get(id=payment_id)

        agreement = payment.agreement
        unit = agreement.unit
        property = unit.property
        tenant = agreement.tenant
        owner = property.owners.first()  # Primary owner

        # Get landlord's receipt template
        from apps.reports.models import TemplateConfig

        try:
            template = TemplateConfig.objects.get(
                landlord=owner, template_type="receipt", is_default=True
            )
        except TemplateConfig.DoesNotExist:
            template = None

        return {
            "payment": {
                "id": str(payment.id),
                "amount": float(payment.amount),
                "payment_date": payment.payment_date.isoformat(),
                "method": payment.payment_method,
                "status": payment.status,
                "transaction_id": payment.transaction_id,
                "fee_breakdown": payment.fee_breakdown,  # already JSON
                "net_landlord_amount": (
                    float(payment.net_landlord_amount)
                    if payment.net_landlord_amount
                    else None
                ),
                "period_start": (
                    payment.period_start.isoformat() if payment.period_start else None
                ),
                "period_end": (
                    payment.period_end.isoformat() if payment.period_end else None
                ),
                "months_covered": (
                    float(payment.months_covered) if payment.months_covered else None
                ),
            },
            "tenant": {
                "name": tenant.user.get_full_name(),
                "email": tenant.user.email,
                "phone": (
                    str(tenant.user.profile.phone_number)
                    if hasattr(tenant.user, "profile")
                    else None
                ),
            },
            "property": {
                "id": str(property.id),
                "name": property.name,
                "address": f"{property.address_line1}, {property.city}, {property.country.name}",
            },
            "unit": {
                "number": unit.unit_number,
                "type": unit.unit_type,
            },
            "landlord": {
                "name": owner.user.get_full_name(),
                "email": owner.user.email,
                "phone": (
                    str(owner.mobile_money_number)
                    if owner.mobile_money_number
                    else None
                ),
            },
            "template": {
                "layout": template.selected_layout if template else 1,
                "primary_color": template.primary_color if template else "#1E3A8A",
                "secondary_color": template.secondary_color if template else "#F59E0B",
                "agency_name": (
                    template.agency_name if template else owner.user.get_full_name()
                ),
                "agency_address": template.agency_address if template else "",
                "agency_phone": (
                    template.agency_phone
                    if template
                    else str(owner.mobile_money_number or "")
                ),
                "agency_email": template.agency_email if template else owner.user.email,
                "logo_url": template.logo.url if template and template.logo else None,
                "footer_text": template.footer_text if template else "",
                "show_property_name": template.show_property_name if template else True,
            },
        }

    def get_maintenance_summary(
        self,
        property_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Detailed maintenance analytics for a property."""
        if not start_date:
            start_date = timezone.now() - timedelta(days=365)
        if not end_date:
            end_date = timezone.now()

        # Maintenance requests in range
        requests = MaintenanceRequest.objects.filter(
            unit__property_id=property_id, created_at__range=[start_date, end_date]
        )

        total_estimated = requests.aggregate(total=Sum("estimated_cost"))["total"] or 0
        total_actual = requests.aggregate(total=Sum("actual_cost"))["total"] or 0

        # By status
        by_status = requests.values("status").annotate(
            count=Count("id"), total_actual=Sum("actual_cost")
        )

        # By priority
        by_priority = requests.values("priority").annotate(
            count=Count("id"), total_actual=Sum("actual_cost")
        )

        # By vendor
        by_vendor = requests.values(
            "assigned_vendor__company_name", "assigned_vendor__contact_name"
        ).annotate(count=Count("id"), total_actual=Sum("actual_cost"))

        # Expenses linked to maintenance (separate from actual_cost)
        expenses = Expense.objects.filter(
            property_id=property_id,
            expense_date__range=[start_date, end_date],
            category="maintenance",
        )
        total_expenses = expenses.aggregate(total=Sum("amount"))["total"] or 0

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "summary": {
                "total_requests": requests.count(),
                "total_estimated_cost": float(total_estimated),
                "total_actual_cost": float(total_actual),
                "total_extra_expenses": float(total_expenses),
                "average_cost_per_request": (
                    float(total_actual / requests.count())
                    if requests.count() > 0
                    else 0
                ),
            },
            "by_status": list(by_status),
            "by_priority": list(by_priority),
            "by_vendor": list(by_vendor),
        }

    def _generate_periods(
        self, start: datetime, end: datetime, group_by: str
    ) -> List[datetime]:
        """Generate list of period start dates (first of month or day)."""
        periods = []
        if group_by == "month":
            current = start.replace(day=1)
            while current <= end:
                periods.append(current)
                # next month
                if current.month == 12:
                    current = current.replace(year=current.year + 1, month=1)
                else:
                    current = current.replace(month=current.month + 1)
        else:  # day
            current = start
            while current <= end:
                periods.append(current)
                current += timedelta(days=1)
        return periods

    def _compute_occupancy_series(
        self, unit_ids: List[str], start: datetime, end: datetime, group_by: str
    ) -> List[float]:
        """Compute occupancy percentage per period based on rental agreements."""
        # For simplicity, use active agreements and their coverage_end_date
        # A unit is occupied if there is an active agreement covering that day.
        # This is a placeholder; full implementation would iterate over days and check coverage.
        periods = self._generate_periods(start, end, group_by)
        occupancy = []
        for period in periods:
            if group_by == "month":
                month_start = period
                month_end = (period.replace(day=28) + timedelta(days=4)).replace(
                    day=1
                ) - timedelta(days=1)
            else:
                month_start = period
                month_end = period
            # count occupied days sum across units
            total_days = (month_end - month_start).days + 1
            occupied_days = 0
            for unit_id in unit_ids:
                # Get agreements that were active during this period
                agreements = RentalAgreement.objects.filter(
                    unit_id=unit_id,
                    is_active=True,
                    start_date__lte=month_end,
                    coverage_end_date__gte=month_start,
                )
                if agreements.exists():
                    # For simplicity, if any agreement covers any day of period, consider whole period occupied
                    occupied_days += total_days
            occupancy_percent = (
                (occupied_days / (len(unit_ids) * total_days)) * 100 if unit_ids else 0
            )
            occupancy.append(round(occupancy_percent, 2))
        return occupancy
