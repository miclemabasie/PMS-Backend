import pytest
from decimal import Decimal
from apps.maintenance.services import MaintenanceService
from apps.maintenance.models import MaintenanceStatus

pytestmark = pytest.mark.django_db


class TestMaintenanceService:
    def test_approve_request_success(self, maintenance_request, manager_user):
        service = MaintenanceService()
        approved = service.approve_request(
            str(maintenance_request.id), manager_user.manager_profile.pkid
        )
        assert approved.status == MaintenanceStatus.ASSIGNED
        assert approved.approved_by == manager_user.manager_profile
        assert approved.approved_at is not None

    def test_approve_request_already_approved_fails(
        self, maintenance_request, manager_user
    ):
        service = MaintenanceService()
        service.approve_request(
            str(maintenance_request.id), manager_user.manager_profile.pkid
        )
        with pytest.raises(ValueError, match="must be submitted"):
            service.approve_request(
                str(maintenance_request.id), manager_user.manager_profile.pkid
            )

    def test_complete_request_success(self, maintenance_request, manager_user):
        service = MaintenanceService()
        approved = service.approve_request(
            str(maintenance_request.id), manager_user.manager_profile.pkid
        )
        approved.status = "in_progress"
        approved.save()
        expense = service.complete_request(str(approved.id), Decimal(27000), "Fixed")
        assert expense.amount == 27000
        assert expense.maintenance_request == approved
        approved.refresh_from_db()
        assert approved.status == "completed"
        assert approved.actual_cost == 27000
        assert approved.completed_at is not None
