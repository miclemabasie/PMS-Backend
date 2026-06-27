# apps/dashboard/services.py
from django.utils import timezone
from django.db import models
from django.conf import settings

from apps.properties.repositories import PropertyRepository
from apps.tenants.repositories import TenantRepository
from apps.maintenance.repositories import MaintenanceRequestRepository
from apps.payments.models import Payment, RentalAgreement
from apps.maintenance.models import MaintenanceRequest

# # Optional notification import
# try:
#     from apps.notifications.models import Notification
# except ImportError:
#     Notification = None


class LandlordDashboardService:
    def __init__(self):
        self.property_repo = PropertyRepository()
        self.tenant_repo = TenantRepository()
        self.maintenance_repo = MaintenanceRequestRepository()

    def get_stats(self, owner_id):
        # 1. Total properties (repository returns QuerySet, so .count() works)
        total_properties = self.property_repo.find_by_owner(owner_id).count()

        # 2. Active tenants
        active_tenants = (
            RentalAgreement.objects.filter(
                unit__property__ownership_records__owner_id=owner_id, is_active=True
            )
            .values("tenant")
            .distinct()
            .count()
        )

        # 3. Monthly revenue
        now = timezone.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_revenue = (
            Payment.objects.filter(
                agreement__unit__property__ownership_records__owner_id=owner_id,
                status="completed",
                payment_date__gte=start_of_month,
                payment_date__lte=now,
            ).aggregate(total=models.Sum("amount"))["total"]
            or 0
        )

        # 4. Pending repairs – use model directly because repository returns list
        pending_repairs = (
            MaintenanceRequest.objects.filter(
                unit__property__ownership_records__owner_id=owner_id
            )
            .exclude(status__in=["completed", "cancelled"])
            .count()
        )

        # 5. Recent payments (last 5)
        recent_payments_qs = (
            Payment.objects.filter(
                agreement__unit__property__ownership_records__owner_id=owner_id,
                status="completed",
            )
            .select_related("agreement__tenant__user", "agreement__unit__property")
            .order_by("-payment_date")[:5]
        )

        recent_payments = []
        for p in recent_payments_qs:
            recent_payments.append(
                {
                    "id": str(p.id),
                    "tenant": p.agreement.tenant.user.get_full_name(),
                    "amount": int(p.amount),
                    "method": p.get_payment_method_display(),
                    "date": p.payment_date.isoformat(),
                    "unit": f"{p.agreement.unit.property.name} - Unit {p.agreement.unit.unit_number}",
                    "status": p.status,
                }
            )

        # 6. Notifications (if notification app is installed)
        notifications = []
        # if Notification is not None and "apps.notifications" in settings.INSTALLED_APPS:
        #     notif_qs = Notification.objects.filter(
        #         user__owner_profile__pkid=owner_id, status="sent"
        #     ).order_by("-created_at")[:5]
        #     notifications = [
        #         {
        #             "id": str(n.id),
        #             "title": n.subject,
        #             "message": n.body[:100],
        #             "created_at": n.created_at.isoformat(),
        #         }
        #         for n in notif_qs
        #     ]

        return {
            "total_properties": total_properties,
            "active_tenants": active_tenants,
            "monthly_revenue": monthly_revenue,
            "pending_repairs": pending_repairs,
            "recent_payments": recent_payments,
            "notifications": notifications,
        }
