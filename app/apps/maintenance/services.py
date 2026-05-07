# apps/maintenance/services.py
from typing import Optional, List
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from apps.core.base_service import BaseService
from apps.maintenance.models import MaintenanceRequest, Vendor
from apps.maintenance.repositories import MaintenanceRequestRepository
from apps.reports.models import Expense, ExpenseCategory
from apps.reports.repositories import ExpenseRepository


class MaintenanceService(BaseService[MaintenanceRequest]):
    def __init__(self):
        super().__init__(MaintenanceRequestRepository())
        self.expense_repo = ExpenseRepository()

    @transaction.atomic
    def complete_request(self, request_id: str, actual_cost: Decimal, notes: str = ""):
        """Mark a maintenance request as completed and create an expense record."""
        request = self.get_by_id(request_id)
        if not request:
            raise ValueError("Request not found")
        if request.status != "in_progress":
            raise ValueError("Request must be 'in_progress' to complete")
        request.status = "completed"
        request.actual_cost = actual_cost
        request.completed_at = timezone.now()
        if notes:
            request.notes = notes
        request.save()

        # Create expense record
        expense = Expense.objects.create(
            property=request.unit.property,
            unit=request.unit,
            category=ExpenseCategory.MAINTENANCE,
            amount=actual_cost,
            expense_date=timezone.now().date(),
            description=f"Maintenance: {request.title}",
            vendor=request.assigned_vendor,
            maintenance_request=request,
            is_reimbursable=request.tenant
            is not None,  # if tenant requested, may be reimbursable
            reimbursed=False,
        )
        return expense

    @transaction.atomic
    def approve_request(self, request_id: str, manager_id):
        """Approve a maintenance request (manager approval)."""
        request = self.get_by_id(request_id)
        if not request:
            raise ValueError("Request not found")
        if request.status != "submitted":
            raise ValueError("Request must be submitted before approval")
        request.status = "assigned"  # or directly "in_progress"? We'll use assigned.
        request.approved_by_id = manager_id
        request.approved_at = timezone.now()
        request.save()
        return request
