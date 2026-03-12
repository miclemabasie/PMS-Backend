from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .permissions import (
    IsOwnerOrManagerOrSuperAdmin,
    CanManageProperty,
    IsTenantOrReadOnly,
)
from .services import (
    PropertyService,
    UnitService,
    LeaseService,
    TenantService,
    PaymentService,
    MaintenanceRequestService,
    VendorService,
    ExpenseService,
    DocumentService,
    OwnerService,
    ManagerService,
    PaymentTermService,
)
from .serializers import (
    PropertySerializer,
    UnitSerializer,
    LeaseSerializer,
    TenantSerializer,
    PaymentSerializer,
    MaintenanceRequestSerializer,
    VendorSerializer,
    ExpenseSerializer,
    DocumentSerializer,
    PaymentTermSerializer,
    OwnerSerializer,
    ManagerSerializer,
)
from .utils import StandardResultsSetPagination


# ----------------------------------------------------------------------
# PaymentTerm Views
# ----------------------------------------------------------------------
class PaymentTermListCreateView(APIView):
    permission_classes = [IsAuthenticated, CanManageProperty]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = PaymentTermService()
        self.paginator = StandardResultsSetPagination()

    def get(self, request):
        terms = self.service.get_all()
        page = self.paginator.paginate_queryset(terms, request)
        serializer = PaymentTermSerializer(page, many=True)
        return self.paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = PaymentTermSerializer(data=request.data)
        if serializer.is_valid():
            term = self.service.create(**serializer.validated_data)
            output = PaymentTermSerializer(term)
            return Response(output.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PaymentTermDetailView(APIView):
    permission_classes = [IsAuthenticated, CanManageProperty]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = PaymentTermService()

    def get(self, request, pk):
        term = self.service.get_by_id(pk)
        if not term:
            return Response({"detail": "Not found"}, status=404)
        serializer = PaymentTermSerializer(term)
        return Response(serializer.data)

    def put(self, request, pk):
        term = self.service.get_by_id(pk)
        if not term:
            return Response({"detail": "Not found"}, status=404)
        serializer = PaymentTermSerializer(term, data=request.data)
        if serializer.is_valid():
            updated = self.service.update(pk, **serializer.validated_data)
            output = PaymentTermSerializer(updated)
            return Response(output.data)
        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        deleted = self.service.delete(pk)
        if deleted:
            return Response(status=204)
        return Response({"detail": "Not found"}, status=404)


# ----------------------------------------------------------------------
# Owner Views
# ----------------------------------------------------------------------
class OwnerListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = OwnerService()
        self.paginator = StandardResultsSetPagination()

    def get(self, request):
        # Only superadmin can list all owners; others see only themselves
        if request.user.is_superuser:
            owners = self.service.get_all()
        else:
            # raise an exception if the user is not superadmin
            return Response({"detail": "Permission denied"}, status=403)

        page = self.paginator.paginate_queryset(owners, request)
        serializer = OwnerSerializer(page, many=True)
        return self.paginator.get_paginated_response(serializer.data)

    def post(self, request):
        # Only superadmin can create arbitrary owners; otherwise create for self
        serializer = OwnerSerializer(data=request.data)
        if serializer.is_valid():
            if request.user.role != "superadmin":
                serializer.validated_data["user"] = request.user
            owner = self.service.create(**serializer.validated_data)
            output = OwnerSerializer(owner)
            return Response(output.data, status=201)
        return Response(serializer.errors, status=400)


class OwnerDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = OwnerService()

    def get(self, request, pk):
        owner = self.service.get_by_id(pk)
        if not owner:
            return Response({"detail": "Not found"}, status=404)
        # Only owner themselves or superadmin can view
        if not request.user.is_superuser and owner.user != request.user:
            return Response({"detail": "Permission denied"}, status=403)
        serializer = OwnerSerializer(owner)
        return Response(serializer.data)

    def put(self, request, pk):
        owner = self.service.get_by_id(pk)
        if not owner:
            return Response({"detail": "Not found"}, status=404)
        if not request.user.is_superuser and owner.user != request.user:
            return Response({"detail": "Permission denied"}, status=403)
        serializer = OwnerSerializer(owner, data=request.data, partial=True)
        if serializer.is_valid():
            updated = self.service.update(pk, **serializer.validated_data)
            output = OwnerSerializer(updated)
            return Response(output.data)
        return Response(serializer.errors, status=400)


# ----------------------------------------------------------------------
# Manager Views (similar pattern) – omitted for brevity
# ----------------------------------------------------------------------


# ----------------------------------------------------------------------
# Tenant Views
# ----------------------------------------------------------------------
class TenantListCreateView(APIView):
    permission_classes = [IsAuthenticated, CanManageProperty]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = TenantService()
        self.paginator = StandardResultsSetPagination()

    def get(self, request):
        # Filter by property if provided
        property_id = request.query_params.get("property")
        if property_id:
            # Get all tenants with leases in that property
            print("there was a property id", property_id)
            tenants = self.service.get_tenants_for_property(property_id)
        else:
            print("there was no property id")
            tenants = self.service.get_all()
        page = self.paginator.paginate_queryset(tenants, request)
        serializer = TenantSerializer(page, many=True)
        return self.paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = TenantSerializer(data=request.data)
        if serializer.is_valid():
            tenant = self.service.create(**serializer.validated_data)
            output = TenantSerializer(tenant)
            return Response(output.data, status=201)
        return Response(serializer.errors, status=400)


class TenantDetailView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrManagerOrSuperAdmin]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = TenantService()

    def get(self, request, pk):
        tenant = self.service.get_by_id(pk)
        if not tenant:
            return Response({"detail": "Not found"}, status=404)
        self.check_object_permissions(request, tenant)
        serializer = TenantSerializer(tenant)
        return Response(serializer.data)

    def put(self, request, pk):
        tenant = self.service.get_by_id(pk)
        if not tenant:
            return Response({"detail": "Not found"}, status=404)
        self.check_object_permissions(request, tenant)
        serializer = TenantSerializer(tenant, data=request.data, partial=True)
        if serializer.is_valid():
            updated = self.service.update(pk, **serializer.validated_data)
            output = TenantSerializer(updated)
            return Response(output.data)
        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        tenant = self.service.get_by_id(pk)
        if not tenant:
            return Response({"detail": "Not found"}, status=404)
        self.check_object_permissions(request, tenant)
        # Only allow if no active lease
        if tenant.leases.filter(status="active").exists():
            return Response(
                {"detail": "Cannot delete tenant with active lease"}, status=400
            )
        self.service.delete(pk)
        return Response(status=204)


# ----------------------------------------------------------------------
# Property Views
# ----------------------------------------------------------------------
class PropertyListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = PropertyService()
        self.paginator = StandardResultsSetPagination()

    def get(self, request):
        properties = self.service.get_properties_for_user(request.user)
        page = self.paginator.paginate_queryset(properties, request)
        serializer = PropertySerializer(page, many=True, context={"request": request})
        return self.paginator.get_paginated_response(serializer.data)

    def post(self, request):
        # Ensure user has owner profile
        owner_service = OwnerService()
        owner = owner_service.get_or_create_for_user(request.user)
        serializer = PropertySerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            property = self.service.create_property(
                data=serializer.validated_data,
                owner=owner,
                manager_ids=request.data.get("managers", []),
            )
            output = PropertySerializer(property, context={"request": request})
            return Response(output.data, status=201)
        return Response(serializer.errors, status=400)


class PropertyDetailView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrManagerOrSuperAdmin]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = PropertyService()

    def get(self, request, pk):
        property = self.service.get_by_id(pk)
        if not property:
            return Response({"detail": "Not found"}, status=404)
        self.check_object_permissions(request, property)
        serializer = PropertySerializer(property, context={"request": request})
        return Response(serializer.data)

    def put(self, request, pk):
        property = self.service.get_by_id(pk)
        if not property:
            return Response({"detail": "Not found"}, status=404)
        self.check_object_permissions(request, property)
        serializer = PropertySerializer(
            property, data=request.data, partial=False, context={"request": request}
        )
        if serializer.is_valid():
            updated = self.service.update_property(
                pk, serializer.validated_data, manager_ids=request.data.get("managers")
            )
            output = PropertySerializer(updated, context={"request": request})
            return Response(output.data)
        return Response(serializer.errors, status=400)

    def patch(self, request, pk):
        property = self.service.get_by_id(pk)
        if not property:
            return Response({"detail": "Not found"}, status=404)
        self.check_object_permissions(request, property)
        serializer = PropertySerializer(
            property, data=request.data, partial=True, context={"request": request}
        )
        if serializer.is_valid():
            updated = self.service.update_property(
                pk, serializer.validated_data, manager_ids=request.data.get("managers")
            )
            output = PropertySerializer(updated, context={"request": request})
            return Response(output.data)
        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        property = self.service.get_by_id(pk)
        if not property:
            return Response({"detail": "Not found"}, status=404)
        self.check_object_permissions(request, property)
        # Check if any units exist
        if property.units.exists():
            return Response(
                {"detail": "Cannot delete property with units. Delete units first."},
                status=400,
            )
        self.service.delete(pk)
        return Response(status=204)


# ----------------------------------------------------------------------
# Unit Views
# ----------------------------------------------------------------------
class UnitListCreateView(APIView):
    permission_classes = [IsAuthenticated, CanManageProperty]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = UnitService()
        self.paginator = StandardResultsSetPagination()

    def get(self, request):
        property_id = request.query_params.get("property")
        if property_id:
            units = self.service.get_units_for_property(property_id)
        else:
            units = self.service.get_all()
        page = self.paginator.paginate_queryset(units, request)
        serializer = UnitSerializer(page, many=True, context={"request": request})
        return self.paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = UnitSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            unit = self.service.create(**serializer.validated_data)
            output = UnitSerializer(unit, context={"request": request})
            return Response(output.data, status=201)
        return Response(serializer.errors, status=400)


class UnitDetailView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrManagerOrSuperAdmin]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = UnitService()

    def get(self, request, pk):
        unit = self.service.get_by_id(pk)
        if not unit:
            return Response({"detail": "Not found"}, status=404)
        self.check_object_permissions(request, unit)
        serializer = UnitSerializer(unit, context={"request": request})
        return Response(serializer.data)

    def put(self, request, pk):
        unit = self.service.get_by_id(pk)
        if not unit:
            return Response({"detail": "Not found"}, status=404)
        self.check_object_permissions(request, unit)
        serializer = UnitSerializer(
            unit, data=request.data, partial=True, context={"request": request}
        )
        if serializer.is_valid():
            updated = self.service.update(pk, **serializer.validated_data)
            output = UnitSerializer(updated, context={"request": request})
            return Response(output.data)
        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        unit = self.service.get_by_id(pk)
        if not unit:
            return Response({"detail": "Not found"}, status=404)
        self.check_object_permissions(request, unit)
        if unit.status == "occupied":
            return Response({"detail": "Cannot delete occupied unit"}, status=400)
        self.service.delete(pk)
        return Response(status=204)


# ----------------------------------------------------------------------
# Lease Views
# ----------------------------------------------------------------------
class LeaseListCreateView(APIView):
    permission_classes = [IsAuthenticated, CanManageProperty]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = LeaseService()
        self.paginator = StandardResultsSetPagination()

    def get(self, request):
        # Filter by unit or tenant
        unit_id = request.query_params.get("unit")
        tenant_id = request.query_params.get("tenant")
        if unit_id:
            leases = self.service.repository.filter(unit_id=unit_id)
        elif tenant_id:
            leases = self.service.repository.filter(lease_tenants__tenant_id=tenant_id)
        else:
            leases = self.service.get_all()
        page = self.paginator.paginate_queryset(leases, request)
        serializer = LeaseSerializer(page, many=True, context={"request": request})
        return self.paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = LeaseSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            tenant_ids = request.data.get("tenant_ids", [])
            if not tenant_ids:
                return Response({"detail": "At least one tenant required"}, status=400)
            try:
                lease = self.service.create_lease(serializer.validated_data, tenant_ids)
                output = LeaseSerializer(lease, context={"request": request})
                return Response(output.data, status=201)
            except ValueError as e:
                return Response({"detail": str(e)}, status=400)
        return Response(serializer.errors, status=400)


class LeaseDetailView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrManagerOrSuperAdmin]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = LeaseService()

    def get(self, request, pk):
        lease = self.service.get_by_id(pk)
        if not lease:
            return Response({"detail": "Not found"}, status=404)
        self.check_object_permissions(request, lease)
        serializer = LeaseSerializer(lease, context={"request": request})
        return Response(serializer.data)

    def put(self, request, pk):
        lease = self.service.get_by_id(pk)
        if not lease:
            return Response({"detail": "Not found"}, status=404)
        self.check_object_permissions(request, lease)
        # Only allow editing if not active? Or allow some fields.
        serializer = LeaseSerializer(
            lease, data=request.data, partial=True, context={"request": request}
        )
        if serializer.is_valid():
            updated = self.service.update(pk, **serializer.validated_data)
            output = LeaseSerializer(updated, context={"request": request})
            return Response(output.data)
        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        lease = self.service.get_by_id(pk)
        if not lease:
            return Response({"detail": "Not found"}, status=404)
        self.check_object_permissions(request, lease)
        # Only allow delete if not active
        if lease.status == "active":
            return Response(
                {"detail": "Cannot delete active lease. Terminate it first."},
                status=400,
            )
        self.service.delete(pk)
        return Response(status=204)


# Custom actions for lease
class LeaseTerminateView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrManagerOrSuperAdmin]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = LeaseService()

    def post(self, request, pk):
        lease = self.service.get_by_id(pk)
        if not lease:
            return Response({"detail": "Not found"}, status=404)
        self.check_object_permissions(request, lease)
        termination_date = request.data.get("termination_date")
        reason = request.data.get("reason", "")
        if not termination_date:
            return Response({"detail": "termination_date required"}, status=400)
        updated = self.service.terminate_lease(pk, termination_date, reason)
        if updated:
            serializer = LeaseSerializer(updated, context={"request": request})
            return Response(serializer.data)
        return Response({"detail": "Lease not active"}, status=400)


class LeaseRenewView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrManagerOrSuperAdmin]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = LeaseService()

    def post(self, request, pk):
        lease = self.service.get_by_id(pk)
        if not lease:
            return Response({"detail": "Not found"}, status=404)
        self.check_object_permissions(request, lease)
        new_end_date = request.data.get("new_end_date")
        new_rent = request.data.get("new_rent_amount")
        if not new_end_date:
            return Response({"detail": "new_end_date required"}, status=400)
        new_lease = self.service.renew_lease(pk, new_end_date, new_rent)
        if new_lease:
            serializer = LeaseSerializer(new_lease, context={"request": request})
            return Response(serializer.data, status=201)
        return Response({"detail": "Could not renew lease"}, status=400)


# ----------------------------------------------------------------------
# Payment Views
# ----------------------------------------------------------------------
class PaymentListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = PaymentService()
        self.paginator = StandardResultsSetPagination()

    def get(self, request):
        lease_id = request.query_params.get("lease")
        if lease_id:
            payments = self.service.get_payments_for_lease(lease_id)
        else:
            # For superadmin, all; for others, filter by accessible leases
            if request.user.role == "superadmin":
                payments = self.service.get_all()
            else:
                # Get leases the user can see, then payments
                # Simplified: return empty for now
                payments = []
        page = self.paginator.paginate_queryset(payments, request)
        serializer = PaymentSerializer(page, many=True, context={"request": request})
        return self.paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = PaymentSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            try:
                payment = self.service.record_payment(
                    lease_id=serializer.validated_data["lease"].id,
                    data=serializer.validated_data,
                )
                output = PaymentSerializer(payment, context={"request": request})
                return Response(output.data, status=201)
            except ValueError as e:
                return Response({"detail": str(e)}, status=400)
        return Response(serializer.errors, status=400)


class PaymentDetailView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrManagerOrSuperAdmin]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = PaymentService()

    def get(self, request, pk):
        payment = self.service.get_by_id(pk)
        if not payment:
            return Response({"detail": "Not found"}, status=404)
        self.check_object_permissions(request, payment)
        serializer = PaymentSerializer(payment, context={"request": request})
        return Response(serializer.data)

    def put(self, request, pk):
        payment = self.service.get_by_id(pk)
        if not payment:
            return Response({"detail": "Not found"}, status=404)
        self.check_object_permissions(request, payment)
        # Restrict editing completed payments?
        serializer = PaymentSerializer(
            payment, data=request.data, partial=True, context={"request": request}
        )
        if serializer.is_valid():
            updated = self.service.update(pk, **serializer.validated_data)
            output = PaymentSerializer(updated, context={"request": request})
            return Response(output.data)
        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        payment = self.service.get_by_id(pk)
        if not payment:
            return Response({"detail": "Not found"}, status=404)
        self.check_object_permissions(request, payment)
        # Only allow delete if not completed? Or admin only.
        self.service.delete(pk)
        return Response(status=204)


# ----------------------------------------------------------------------
# Maintenance Request Views
# ----------------------------------------------------------------------
class MaintenanceRequestListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = MaintenanceRequestService()
        self.paginator = StandardResultsSetPagination()

    def get(self, request):
        unit_id = request.query_params.get("unit")
        status_filter = request.query_params.get("status")
        filters = {}
        if unit_id:
            filters["unit_id"] = unit_id
        if status_filter:
            filters["status"] = status_filter
        # For tenants, show only their unit's requests
        if hasattr(request.user, "tenant_profile"):
            tenant = request.user.tenant_profile
            filters["unit__lease_tenants__tenant"] = tenant
        requests = self.service.repository.filter(**filters)
        page = self.paginator.paginate_queryset(requests, request)
        serializer = MaintenanceRequestSerializer(
            page, many=True, context={"request": request}
        )
        return self.paginator.get_paginated_response(serializer.data)

    def post(self, request):

        serializer = MaintenanceRequestSerializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            # If tenant, set tenant automatically
            if hasattr(request.user, "tenant_profile"):
                request.data["tenant"] = request.user.tenant_profile
            req = self.service.create(**serializer.validated_data)
            output = MaintenanceRequestSerializer(req, context={"request": request})
            return Response(output.data, status=201)
        return Response(serializer.errors, status=400)


class MaintenanceRequestDetailView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrManagerOrSuperAdmin]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = MaintenanceRequestService()

    def get(self, request, pk):
        req = self.service.get_by_id(pk)
        if not req:
            return Response({"detail": "Not found"}, status=404)
        self.check_object_permissions(request, req)
        serializer = MaintenanceRequestSerializer(req, context={"request": request})
        return Response(serializer.data)

    def put(self, request, pk):
        req = self.service.get_by_id(pk)
        if not req:
            return Response({"detail": "Not found"}, status=404)
        self.check_object_permissions(request, req)
        serializer = MaintenanceRequestSerializer(
            req, data=request.data, partial=True, context={"request": request}
        )
        if serializer.is_valid():
            updated = self.service.update(pk, **serializer.validated_data)
            output = MaintenanceRequestSerializer(updated, context={"request": request})
            return Response(output.data)
        return Response(serializer.errors, status=400)


# Custom actions
class MaintenanceRequestAssignView(APIView):
    permission_classes = [IsAuthenticated, CanManageProperty]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = MaintenanceRequestService()

    def post(self, request, pk):
        req = self.service.get_by_id(pk)
        if not req:
            return Response({"detail": "Not found"}, status=404)
        self.check_object_permissions(request, req)
        vendor_id = request.data.get("vendor_id")
        estimated_cost = request.data.get("estimated_cost")
        if not vendor_id:
            return Response({"detail": "vendor_id required"}, status=400)
        updated = self.service.assign_vendor(pk, vendor_id, estimated_cost)
        serializer = MaintenanceRequestSerializer(updated, context={"request": request})
        return Response(serializer.data)


class MaintenanceRequestCompleteView(APIView):
    permission_classes = [IsAuthenticated, CanManageProperty]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = MaintenanceRequestService()

    def post(self, request, pk):
        req = self.service.get_by_id(pk)
        if not req:
            return Response({"detail": "Not found"}, status=404)
        self.check_object_permissions(request, req)
        actual_cost = request.data.get("actual_cost")
        notes = request.data.get("notes", "")
        if actual_cost is None:
            return Response({"detail": "actual_cost required"}, status=400)
        updated = self.service.complete_request(pk, actual_cost, notes)
        serializer = MaintenanceRequestSerializer(updated, context={"request": request})
        return Response(serializer.data)


# ----------------------------------------------------------------------
# Vendor Views
# ----------------------------------------------------------------------
class VendorListCreateView(APIView):
    permission_classes = [IsAuthenticated, CanManageProperty]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = VendorService()
        self.paginator = StandardResultsSetPagination()

    def get(self, request):
        vendors = self.service.get_all()
        page = self.paginator.paginate_queryset(vendors, request)
        serializer = VendorSerializer(page, many=True, context={"request": request})
        return self.paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = VendorSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            vendor = self.service.create(**serializer.validated_data)
            output = VendorSerializer(vendor, context={"request": request})
            return Response(output.data, status=201)
        return Response(serializer.errors, status=400)


class VendorDetailView(APIView):
    permission_classes = [IsAuthenticated, CanManageProperty]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = VendorService()

    def get(self, request, pk):
        vendor = self.service.get_by_id(pk)
        if not vendor:
            return Response({"detail": "Not found"}, status=404)
        serializer = VendorSerializer(vendor, context={"request": request})
        return Response(serializer.data)

    def put(self, request, pk):
        vendor = self.service.get_by_id(pk)
        if not vendor:
            return Response({"detail": "Not found"}, status=404)
        serializer = VendorSerializer(
            vendor, data=request.data, partial=True, context={"request": request}
        )
        if serializer.is_valid():
            updated = self.service.update(pk, **serializer.validated_data)
            output = VendorSerializer(updated, context={"request": request})
            return Response(output.data)
        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        vendor = self.service.get_by_id(pk)
        if not vendor:
            return Response({"detail": "Not found"}, status=404)
        self.service.delete(pk)
        return Response(status=204)


# ----------------------------------------------------------------------
# Expense Views
# ----------------------------------------------------------------------
class ExpenseListCreateView(APIView):
    permission_classes = [IsAuthenticated, CanManageProperty]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = ExpenseService()
        self.paginator = StandardResultsSetPagination()

    def get(self, request):
        property_id = request.query_params.get("property")
        filters = {}
        if property_id:
            filters["property_id"] = property_id
        expenses = self.service.repository.filter(**filters)
        page = self.paginator.paginate_queryset(expenses, request)
        serializer = ExpenseSerializer(page, many=True, context={"request": request})
        return self.paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = ExpenseSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            expense = self.service.create(**serializer.validated_data)
            output = ExpenseSerializer(expense, context={"request": request})
            return Response(output.data, status=201)
        return Response(serializer.errors, status=400)


class ExpenseDetailView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrManagerOrSuperAdmin]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = ExpenseService()

    def get(self, request, pk):
        expense = self.service.get_by_id(pk)
        if not expense:
            return Response({"detail": "Not found"}, status=404)
        self.check_object_permissions(request, expense)
        serializer = ExpenseSerializer(expense, context={"request": request})
        return Response(serializer.data)

    def put(self, request, pk):
        expense = self.service.get_by_id(pk)
        if not expense:
            return Response({"detail": "Not found"}, status=404)
        self.check_object_permissions(request, expense)
        serializer = ExpenseSerializer(
            expense, data=request.data, partial=True, context={"request": request}
        )
        if serializer.is_valid():
            updated = self.service.update(pk, **serializer.validated_data)
            output = ExpenseSerializer(updated, context={"request": request})
            return Response(output.data)
        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        expense = self.service.get_by_id(pk)
        if not expense:
            return Response({"detail": "Not found"}, status=404)
        self.check_object_permissions(request, expense)
        self.service.delete(pk)
        return Response(status=204)


# ----------------------------------------------------------------------
# Document Views
# ----------------------------------------------------------------------
class DocumentListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = DocumentService()
        self.paginator = StandardResultsSetPagination()

    def get(self, request):
        # Filter by content_type and object_id
        content_type = request.query_params.get("content_type")
        object_id = request.query_params.get("object_id")
        filters = {}
        if content_type and object_id:
            filters["content_type__model"] = content_type
            filters["object_id"] = object_id
        docs = self.service.repository.filter(**filters)
        page = self.paginator.paginate_queryset(docs, request)
        serializer = DocumentSerializer(page, many=True, context={"request": request})
        return self.paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = DocumentSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            # Set uploaded_by to current user
            serializer.validated_data["uploaded_by"] = request.user
            doc = self.service.create(**serializer.validated_data)
            output = DocumentSerializer(doc, context={"request": request})
            return Response(output.data, status=201)
        return Response(serializer.errors, status=400)


class DocumentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = DocumentService()

    def get(self, request, pk):
        doc = self.service.get_by_id(pk)
        if not doc:
            return Response({"detail": "Not found"}, status=404)
        # Check permission on the related object
        related_obj = doc.content_object
        if related_obj and hasattr(self, "check_object_permissions"):
            try:
                self.check_object_permissions(request, related_obj)
            except Exception:
                return Response({"detail": "Permission denied"}, status=403)
        serializer = DocumentSerializer(doc, context={"request": request})
        return Response(serializer.data)

    def delete(self, request, pk):
        doc = self.service.get_by_id(pk)
        if not doc:
            return Response({"detail": "Not found"}, status=404)
        # Only uploader or admin can delete
        if not request.user.is_superuser and doc.uploaded_by != request.user:
            return Response({"detail": "Permission denied"}, status=403)
        self.service.delete(pk)
        return Response(status=204)
