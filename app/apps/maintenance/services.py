import logging
from typing import List, Optional, Dict, Any
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.conf import settings

from apps.core.base_service import BaseService
from apps.maintenance.models import MaintenanceRequest, MaintenanceRequestImage
from apps.maintenance.repositories import MaintenanceRequestRepository
from apps.reports.repositories import ExpenseRepository
from apps.reports.models import Expense
from apps.properties.models import Unit
from apps.tenants.models import Tenant
from apps.maintenance.tasks import (
    send_maintenance_notification,
    send_maintenance_status_update
)

logger = logging.getLogger(__name__)


class MaintenanceService(BaseService[MaintenanceRequest]):
    def __init__(self):
        super().__init__(MaintenanceRequestRepository())
        self.expense_repo = ExpenseRepository()

    @transaction.atomic
    def create_request(
        self, 
        unit_id: str, 
        title: str, 
        description: str, 
        priority: str, 
        tenant_id: str = None, 
        notes: str = "", 
        images: List = None
    ) -> MaintenanceRequest:
        # 1. Validate and get unit
        try:
            unit = Unit.objects.get(id=unit_id)
        except Unit.DoesNotExist:
            raise ValueError(f"Unit with ID {unit_id} does not exist")

        # 2. Validate priority
        valid_priorities = ['low', 'medium', 'high', 'emergency']
        if priority not in valid_priorities:
            raise ValueError(f"Invalid priority. Must be one of: {', '.join(valid_priorities)}")

        # 3. Get tenant if provided
        tenant = None
        if tenant_id:
            try:
                tenant = Tenant.objects.get(id=tenant_id)
            except Tenant.DoesNotExist:
                raise ValueError(f"Tenant with ID {tenant_id} does not exist")

        # 4. Create the request (unit and tenant are now defined)
        request_obj = MaintenanceRequest.objects.create(
            unit=unit,
            tenant=tenant,
            title=title,
            description=description,
            priority=priority,
            status='submitted',
            notes=notes or ''
        )

        # 5. Handle images (max 5)
        if images:
            for image in images[:5]:
                MaintenanceRequestImage.objects.create(
                    maintenance_request=request_obj,
                    image=image
                )

        # 6. Send notifications asynchronously (to landlords, managers, and tenant confirmation)
        self._send_notifications_async(request_obj)

        logger.info(f"Maintenance request created: {request_obj.id} for unit {unit.unit_number}")
        return request_obj

    @transaction.atomic
    def update_status(self, request_id: str, new_status: str, user) -> MaintenanceRequest:
        request_obj = self.repository.get_by_id(request_id)
        if not request_obj:
            raise ValueError(f"Maintenance request with ID {request_id} not found")

        allowed_transitions = self._get_allowed_transitions(request_obj.status)
        if new_status not in allowed_transitions:
            raise ValueError(
                f"Cannot transition from '{request_obj.status}' to '{new_status}'. "
                f"Allowed transitions: {', '.join(allowed_transitions)}"
            )

        if new_status == 'completed':
            return self._handle_completion(request_obj, user)

        request_obj.status = new_status
        request_obj.save(update_fields=['status', 'updated_at'])

        self._send_status_notifications(request_obj, new_status, user)

        logger.info(f"Maintenance request {request_id} status updated to {new_status}")
        return request_obj

    @transaction.atomic
    def complete_request(self, request_id: str, actual_cost: Decimal, notes: str = "") -> MaintenanceRequest:
        request_obj = self.repository.get_by_id(request_id)
        if not request_obj:
            raise ValueError(f"Maintenance request with ID {request_id} not found")

        if request_obj.status != 'in_progress':
            raise ValueError(f"Request must be 'in_progress' to complete. Current status: {request_obj.status}")

        return self._handle_completion(request_obj, actual_cost=actual_cost, notes=notes)

    def _handle_completion(self, request_obj: MaintenanceRequest, user=None, actual_cost: Decimal = None, notes: str = "") -> MaintenanceRequest:
        request_obj.status = 'completed'
        request_obj.completed_at = timezone.now()
        if actual_cost:
            request_obj.actual_cost = actual_cost
        if notes:
            request_obj.notes = notes
        request_obj.save()

        if actual_cost:
            Expense.objects.create(
                property=request_obj.unit.property,
                unit=request_obj.unit,
                category='maintenance',
                amount=actual_cost,
                expense_date=timezone.now().date(),
                description=f"Maintenance: {request_obj.title}",
                vendor=request_obj.assigned_vendor,
                maintenance_request=request_obj,
                is_reimbursable=False,
                reimbursed=False
            )
            logger.info(f"Expense created for maintenance request {request_obj.id}")

        self._send_status_notifications(request_obj, 'completed', user, actual_cost)
        return request_obj

    def _send_notifications_async(self, request_obj: MaintenanceRequest):
        property_obj = request_obj.unit.property
        recipients = self._get_recipients(property_obj)
        if not recipients:
            logger.info(f"No recipients found for maintenance request {request_obj.id}")
            return

        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
        link = f"{frontend_url}/dashboard/landlord/maintenance"

        context = {
            'tenant_name': request_obj.tenant.user.get_full_name() if request_obj.tenant else 'A tenant',
            'property_name': property_obj.name,
            'unit_number': request_obj.unit.unit_number,
            'title': request_obj.title,
            'description': request_obj.description,
            'priority': request_obj.priority,
            'request_id': str(request_obj.id),
            'link': link,
            'subject': f'New Maintenance Request: {request_obj.title}'
        }

        for recipient in recipients:
            send_maintenance_notification.delay(
                recipient,
                context,
                'emails/maintenance/new_request.html'
            )

        if request_obj.tenant and request_obj.tenant.user.email:
            tenant_context = context.copy()
            tenant_context['tenant_name'] = request_obj.tenant.user.get_full_name()
            tenant_link = f"{frontend_url}/dashboard/tenant/maintenance"
            tenant_context['link'] = tenant_link
            tenant_context['subject'] = f'Request Submitted: {request_obj.title}'
            send_maintenance_notification.delay(
                request_obj.tenant.user.email,
                tenant_context,
                'emails/maintenance/request_confirmation.html'
            )

    def _send_status_notifications(self, request_obj: MaintenanceRequest, status: str, user=None, actual_cost: Decimal = None):
        property_obj = request_obj.unit.property
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')

        context = {
            'property_name': property_obj.name,
            'unit_number': request_obj.unit.unit_number,
            'title': request_obj.title,
            'priority': request_obj.priority,
            'link': f"{frontend_url}/dashboard/landlord/maintenance",
            'request_id': str(request_obj.id),
        }
        if actual_cost:
            context['actual_cost'] = str(actual_cost)

        if request_obj.tenant and request_obj.tenant.user.email:
            tenant_context = context.copy()
            tenant_context['recipient_name'] = request_obj.tenant.user.get_full_name()
            tenant_context['link'] = f"{frontend_url}/dashboard/tenant/maintenance"
            send_maintenance_status_update.delay(
                request_obj.tenant.user.email,
                tenant_context,
                status,
                is_tenant=True
            )

        recipients = self._get_recipients(property_obj)
        for recipient in recipients:
            recipient_context = context.copy()
            recipient_context['recipient_name'] = recipient
            recipient_context['link'] = f"{frontend_url}/dashboard/landlord/maintenance"
            send_maintenance_status_update.delay(
                recipient,
                recipient_context,
                status,
                is_tenant=False
            )

    def _get_recipients(self, property_obj) -> List[str]:
        recipients = set()
        for owner in property_obj.owners.all():
            if owner.user.email:
                recipients.add(owner.user.email)
        for manager in property_obj.managers.all():
            if manager.user.email:
                recipients.add(manager.user.email)
        return list(recipients)

    def _get_allowed_transitions(self, current_status: str) -> List[str]:
        transitions = {
            'submitted': ['in_progress', 'cancelled'],
            'in_progress': ['completed', 'cancelled'],
            'completed': [],
            'cancelled': []
        }
        return transitions.get(current_status, [])

    def get_requests_for_user(self, user) -> List[MaintenanceRequest]:
        return self.repository.get_queryset_for_user(user)

    def apply_filters(self, queryset, filters: Dict[str, Any]):
        if filters.get('status'):
            queryset = self.repository.filter_by_status(queryset, filters['status'])
        if filters.get('priority'):
            queryset = self.repository.filter_by_priority(queryset, filters['priority'])
        if filters.get('property'):
            queryset = self.repository.filter_by_property(queryset, filters['property'])
        return queryset