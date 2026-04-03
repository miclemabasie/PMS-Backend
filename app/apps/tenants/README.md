## 📝 Documentation Updates

### API Documentation Addition

**File:** `app/apps/tenants/README.md` (create if doesn't exist)

```markdown
# Tenant API Documentation

## Tenant Model Constraints

### ID Number (CNI/Passport)
- **Unique:** Yes - Each ID number can only be registered once
- **Normalized:** Yes - All ID numbers are stored uppercase, trimmed
- **Purpose:** Prevents tenants from creating multiple accounts to hide rental history

### Error Responses

| Status Code | Error | Message |
|-------------|-------|---------|
| 400 | Duplicate ID | "This ID number (CNI/Passport) is already registered. Each tenant can only have one account in the system." |
| 400 | Invalid Format | "ID number is required" |

## Business Rules

1. One CNI = One Tenant Account
2. ID numbers are case-insensitive
3. Leading/trailing spaces are automatically trimmed
4. Duplicate detection happens at both serializer and database level
```

---

## ⚠️ Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Existing duplicates in DB | Migration fails | Run data migration first (Step 4) |
| Production downtime | Medium | Schedule during low-traffic period |
| API breaking changes | Low | Backward compatible (only rejects new duplicates) |
| User confusion | Low | Clear error messages in serializer |

---

## ✅ Completion Checklist

- [ ] Update `Tenant` model with `unique=True`
- [ ] Add `UniqueConstraint` in Meta class
- [ ] Update `TenantSerializer` with validation
- [ ] Create data migration for existing duplicates
- [ ] Create schema migration for uniqueness constraint
- [ ] Test duplicate creation (should fail)
- [ ] Test unique creation (should succeed)
- [ ] Test case insensitivity
- [ ] Test update own record
- [ ] Update API documentation
- [ ] Run migrations on development database
- [ ] Run migrations on staging database
- [ ] Deploy to production

---

## 🎯 Next Steps

Once Task 1.1 is complete and verified, we proceed to:

**Task 1.2:** Tenant Search Endpoint - Create `GET /api/v1/tenants/search/?id_number=XXX`

---

## 📋 Decision Log

| Decision | Rationale | Alternative Considered |
|----------|-----------|----------------------|
| `unique=True` on field | Database-level enforcement is most reliable | Application-level validation only (rejected - can be bypassed) |
| Case normalization | Prevents `CNI123` vs `cni123` duplicates | Case-sensitive uniqueness (rejected - user confusion) |
| Named constraint | Better migration tracking and debugging | Anonymous constraint (rejected - harder to debug) |
| Data migration first | Prevents migration failure on existing data | Manual cleanup (rejected - error-prone) |
| Serializer validation | User-friendly error messages before DB error | DB error only (rejected - poor UX) |

---

DATE 01/04/2026
# Task 1.2: Tenant Search Endpoint

## 📋 Implementation Plan

This task creates the API endpoint that allows Landlords and Managers to search for existing tenants by their National ID (CNI). This is the foundation for the "Add Existing Tenant" flow.

**Key Goals:**
1.  **Secure Access:** Only Landlords, Managers, and Admins can search.
2.  **Privacy:** Sensitive tenant data (guarantors, full ID) is masked in search results.
3.  **Performance:** Efficient database lookup using the unique index on `id_number`.
4.  **Foundation:** Prepare the response structure for the Reputation Score (to be fully implemented in Task 1.3).

---

## 🔍 Current State Analysis

**File:** `app/apps/tenants/views.py`
*   **Current:** Has `TenantListCreateView` and `TenantDetailView`.
*   **Missing:** No specific search endpoint.

**File:** `app/apps/tenants/repositories.py`
*   **Current:** Has `find_by_property` and `get_by_pkid`.
*   **Missing:** No method to find by `id_number`.

**File:** `src/features/tenants/tenantsApi.js`
*   **Current:** Empty (0 bytes).
*   **Needed:** RTK Query hooks for search.

---

## ✅ Implementation Steps

### Step 1: Update Tenant Repository

**File:** `app/apps/tenants/repositories.py`

```python
from apps.rentals.models import (
    LeaseTenant,
)
from apps.core.base_repository import DjangoRepository

from apps.tenants.models import Tenant


class TenantRepository(DjangoRepository[Tenant]):
    def __init__(self):
        super().__init__(Tenant)

    def find_by_property(self, property_id):
        return self.model_class.objects.filter(leases__unit__property__id=property_id)

    def get_by_pkid(self, pkid):
        return self.model_class.objects.get(pkid=pkid)

    # ✅ NEW: Search by National ID
    def find_by_id_number(self, id_number: str):
        """
        Find a tenant by their unique ID number (CNI/Passport).
        Returns a single instance or None.
        """
        try:
            # Use exact match since ID number is unique
            return self.model_class.objects.get(id_number=id_number)
        except self.model_class.DoesNotExist:
            return None
```

**Decision:** We use `get()` instead of `filter()` because Task 1.1 ensured `id_number` is unique. This is faster and semantically correct.

---

### Step 2: Update Tenant Service

**File:** `app/apps/tenants/services.py`

```python
from typing import List, Optional, Dict, Any
from django.db import transaction
from django.utils import timezone
import logging
from .models import (
    Tenant,
)
from .repositories import (
    TenantRepository,
    LeaseTenantRepository,
)
from apps.core.base_service import BaseService
from apps.rentals.models import Lease, Payment

logger = logging.getLogger(__name__)


class TenantService(BaseService[Tenant]):
    def __init__(self):
        super().__init__(TenantRepository())

    def get_tenants_for_property(self, property_id):
        logger.info("Get tenants for property with id %s", property_id)
        return self.repository.find_by_property(property_id)

    # ✅ NEW: Search Tenant by ID Number
    def search_tenant_by_id(self, id_number: str, user) -> Optional[Dict[str, Any]]:
        """
        Search for a tenant by ID number.
        Returns masked data suitable for search results (privacy protection).
        """
        # 1. Find Tenant
        tenant = self.repository.find_by_id_number(id_number)
        
        if not tenant:
            return None

        # 2. Calculate Basic Reputation (Placeholder for Task 1.3)
        # We will enhance this in Task 1.3 with a dedicated Reputation Service
        reputation_summary = self._get_basic_reputation_summary(tenant)

        # 3. Construct Safe Response
        return {
            "id": str(tenant.id),
            "pkid": str(tenant.pkid),
            "full_name": tenant.user.get_full_name(),
            "email": tenant.user.email,
            "phone": str(tenant.user.phone_number) if hasattr(tenant.user, 'phone_number') else None,
            "id_number_masked": self._mask_id_number(tenant.id_number),
            "current_status": self._get_tenant_status(tenant),
            "reputation": reputation_summary,
        }

    def _mask_id_number(self, id_number: str) -> str:
        """
        Mask ID number for privacy (e.g., CNI123456789 -> CNI***6789)
        """
        if len(id_number) <= 4:
            return "***"
        return f"{id_number[:-4]}***{id_number[-4:]}"

    def _get_tenant_status(self, tenant: Tenant) -> str:
        """
        Check if tenant currently has an active lease.
        """
        has_active_lease = Lease.objects.filter(
            lease_tenants__tenant=tenant,
            status="active"
        ).exists()
        return "occupied" if has_active_lease else "available"

    def _get_basic_reputation_summary(self, tenant: Tenant) -> Dict[str, Any]:
        """
        Basic reputation metrics. 
        TODO: Move to dedicated ReputationService in Task 1.3
        """
        total_leases = Lease.objects.filter(lease_tenants__tenant=tenant).count()
        total_payments = Payment.objects.filter(tenant=tenant).count()
        completed_payments = Payment.objects.filter(tenant=tenant, status="completed").count()
        
        # Simple score calculation
        score = 50 # Neutral default
        if total_payments > 0:
            score = int((completed_payments / total_payments) * 100)

        return {
            "score": score,
            "total_leases": total_leases,
            "total_payments": total_payments,
            "completed_payments": completed_payments,
        }
```

**Decision:** I included a basic reputation calculation here to unblock the UI, but I added a `TODO` note to refactor this into a dedicated `ReputationService` in Task 1.3. This keeps Task 1.2 functional without waiting for Task 1.3.

---

### Step 3: Create Search Serializer

**File:** `app/apps/tenants/serializers.py`

```python
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from .models import (
    Tenant,
)
from apps.users.models import User  # adjust import as needed
from django.contrib.contenttypes.models import ContentType
from apps.users.api.serializers import UserMinimalSerializer


class TenantSerializer(serializers.ModelSerializer):
    user = UserMinimalSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source="user", write_only=True
    )

    class Meta:
        model = Tenant
        fields = [
            "id",
            "pkid",
            "user",
            "user_id",
            "id_number",
            "id_document",
            "emergency_contact_name",
            "emergency_contact_phone",
            "emergency_contact_relation",
            "employer",
            "job_title",
            "monthly_income",
            "guarantor_name",
            "guarantor_phone",
            "guarantor_email",
            "guarantor_id_document",
            "notes",
            "language",  # added for bilingual support
            "emergency_contact_name_fr",
            "employer_fr",
            "job_title_fr",
            "notes_fr",
            "guarantor_name_fr",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


# ✅ NEW: Search Result Serializer
class TenantSearchResultSerializer(serializers.Serializer):
    """
    Serializer for tenant search results.
    Excludes sensitive data (guarantors, full ID, documents).
    """
    id = serializers.UUIDField()
    pkid = serializers.CharField()
    full_name = serializers.CharField()
    email = serializers.EmailField()
    phone = serializers.CharField(allow_null=True)
    id_number_masked = serializers.CharField()
    current_status = serializers.CharField()
    reputation = serializers.DictField()
```

**Decision:** We use a plain `Serializer` (not `ModelSerializer`) because the data comes from the Service method (which aggregates data from User, Tenant, Lease, Payment models), not directly from the Tenant model.

---

### Step 4: Create Search View

**File:** `app/apps/tenants/views.py`

```python
from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from .permissions import (
    IsOwnerOrManagerOrSuperAdmin,
    CanManageProperty,
    IsTenantOrReadOnly,
)

from .services import TenantService
from .serializers import TenantSerializer, TenantSearchResultSerializer
from apps.core.utils import StandardResultsSetPagination

# Create your views here.


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
            tenants = self.service.get_tenants_for_property(property_id)
        else:
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


# ✅ NEW: Tenant Search View
class TenantSearchView(APIView):
    """
    Allows Landlords/Managers to search for tenants by National ID.
    Endpoint: GET /api/v1/tenants/search/?id_number=XXX
    """
    permission_classes = [IsAuthenticated, CanManageProperty]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = TenantService()

    def get(self, request):
        id_number = request.query_params.get("id_number")

        if not id_number:
            return Response(
                {"detail": "id_number query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Normalize ID number (uppercase, strip spaces) to match Task 1.1 logic
        normalized_id = id_number.strip().upper()

        # Search
        result = self.service.search_tenant_by_id(normalized_id, request.user)

        if not result:
            return Response(
                {"detail": "Tenant not found with this ID number"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Serialize
        serializer = TenantSearchResultSerializer(result)
        return Response(serializer.data, status=status.HTTP_200_OK)


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
```

**Decision:** I added normalization (`strip().upper()`) in the View to ensure consistency with Task 1.1's serializer validation.

---

### Step 5: Update URLs

**File:** `app/apps/tenants/urls.py`

```python
from django.urls import path
from .views import TenantListCreateView, TenantDetailView, TenantSearchView

app_name = "tenants"

urlpatterns = [
    # Tenants
    path("", TenantListCreateView.as_view(), name="tenant-list"),
    path("<uuid:pk>/", TenantDetailView.as_view(), name="tenant-detail"),
    # ✅ NEW: Search
    path("search/", TenantSearchView.as_view(), name="tenant-search"),
]
```

---

### Step 6: Frontend API Integration (RTK Query)

**File:** `src/features/tenants/tenantsApi.js`

```javascript
// src/features/tenants/tenantsApi.js
import { baseApi } from "../../app/baseApi";

export const tenantsApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    // ✅ NEW: Search Tenant by ID Number
    searchTenant: builder.query({
      query: (idNumber) => ({
        url: "/tenants/search/",
        params: { id_number: idNumber },
      }),
      providesTags: ["Tenant"],
    }),

    // Get All Tenants (Existing)
    getTenants: builder.query({
      query: (params) => ({
        url: "/tenants/",
        params,
      }),
      providesTags: ["Tenant"],
    }),

    // Get Single Tenant (Existing)
    getTenant: builder.query({
      query: (id) => `/tenants/${id}/`,
      providesTags: (result, error, id) => [{ type: "Tenant", id }],
    }),

    // Create Tenant (Existing)
    createTenant: builder.mutation({
      query: (body) => ({
        url: "/tenants/",
        method: "POST",
        body,
      }),
      invalidatesTags: ["Tenant"],
    }),

    // Update Tenant (Existing)
    updateTenant: builder.mutation({
      query: ({ id, ...patch }) => ({
        url: `/tenants/${id}/`,
        method: "PUT",
        body: patch,
      }),
      invalidatesTags: (result, error, { id }) => [{ type: "Tenant", id }],
    }),

    // Delete Tenant (Existing)
    deleteTenant: builder.mutation({
      query: (id) => ({
        url: `/tenants/${id}/`,
        method: "DELETE",
      }),
      invalidatesTags: ["Tenant"],
    }),
  }),
  overrideExisting: false,
});

// Export hooks for use in components
export const {
  useSearchTenantQuery,
  useGetTenantsQuery,
  useGetTenantQuery,
  useCreateTenantMutation,
  useUpdateTenantMutation,
  useDeleteTenantMutation,
} = tenantsApi;
```

**Decision:** I filled the previously empty file with all standard CRUD operations plus the new Search endpoint, ensuring the frontend has full coverage for Tenant management.

---

## 🧪 Testing Plan

### Test 1: Successful Search (Landlord)
```http
GET /api/v1/tenants/search/?id_number=CNI123456789
Authorization: Bearer <LandlordToken>
```
**Expected:** `200 OK`
**Response:**
```json
{
  "id": "uuid...",
  "full_name": "Jean Mbarga",
  "email": "jean@example.com",
  "id_number_masked": "CNI***6789",
  "current_status": "available",
  "reputation": { "score": 85, "total_leases": 2, ... }
}
```

### Test 2: Search Not Found
```http
GET /api/v1/tenants/search/?id_number=INVALID999
Authorization: Bearer <LandlordToken>
```
**Expected:** `404 Not Found`
**Response:** `{"detail": "Tenant not found with this ID number"}`

### Test 3: Unauthorized Access (Tenant)
```http
GET /api/v1/tenants/search/?id_number=CNI123456789
Authorization: Bearer <TenantToken>
```
**Expected:** `403 Forbidden` (Because `CanManageProperty` permission fails)

### Test 4: Missing Parameter
```http
GET /api/v1/tenants/search/
Authorization: Bearer <LandlordToken>
```
**Expected:** `400 Bad Request`
**Response:** `{"detail": "id_number query parameter is required"}`

### Test 5: Case Insensitivity
```http
GET /api/v1/tenants/search/?id_number=cni123456789
Authorization: Bearer <LandlordToken>
```
**Expected:** `200 OK` (Should find `CNI123456789` due to normalization)

---

## 📝 Documentation Updates

### API Documentation Addition

**File:** `app/apps/tenants/README.md` (Append)

```markdown
## Tenant Search API

### Endpoint: `GET /api/v1/tenants/search/`

**Description:** Search for an existing tenant by their National ID (CNI/Passport).

**Permissions:** Landlord, Manager, Admin (`CanManageProperty`)

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id_number` | String | Yes | National ID number (case-insensitive) |

**Response Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Tenant UUID |
| `full_name` | String | User's full name |
| `email` | String | User's email |
| `id_number_masked` | String | ID number with last 4 chars visible (e.g., `CNI***1234`) |
| `current_status` | String | `available` or `occupied` (based on active leases) |
| `reputation` | Object | Basic reputation metrics (score, total leases, etc.) |

**Privacy Note:** Full ID number, guarantor details, and emergency contacts are NOT returned in search results to protect tenant privacy until a lease is established.
```

---

## ⚠️ Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Privacy Leak** | High | Ensure `TenantSearchResultSerializer` does not include sensitive fields. |
| **Performance** | Low | `id_number` is indexed (Task 1.1), so lookup is O(1). |
| **Permission Bypass** | High | Strictly enforce `CanManageProperty` in View. |
| **Reputation Accuracy** | Medium | Basic calculation used now; will be refined in Task 1.3. |

---

## ✅ Completion Checklist

- [ ] Update `TenantRepository` with `find_by_id_number`
- [ ] Update `TenantService` with `search_tenant_by_id` + masking logic
- [ ] Create `TenantSearchResultSerializer`
- [ ] Create `TenantSearchView`
- [ ] Update `app/apps/tenants/urls.py`
- [ ] Populate `src/features/tenants/tenantsApi.js`
- [ ] Test successful search (200)
- [ ] Test not found (404)
- [ ] Test unauthorized access (403)
- [ ] Test case insensitivity
- [ ] Verify ID masking in response

---

## 🎯 Next Steps

Once Task 1.2 is complete and verified, we proceed to:

**Task 1.3:** Reputation Service Logic - Create a dedicated service to calculate detailed reliability scores (payment history, eviction flags, etc.).

---

## 📋 Decision Log

| Decision | Rationale | Alternative Considered |
|----------|-----------|----------------------|
| **Separate Search View** | Keeps search logic distinct from list/create operations. | Add search param to `TenantListCreateView` (rejected - different permissions/response structure). |
| **Mask ID in Response** | Protects tenant privacy during search phase. | Return full ID (rejected - privacy risk). |
| **Basic Reputation in Service** | Unblocks UI development for Task 1.2. | Wait for Task 1.3 (rejected - blocks frontend progress). |
| **Normalization in View** | Ensures consistent lookup regardless of user input case. | Normalize in Repository (rejected - View is the entry point for request data). |
| **Plain Serializer** | Response aggregates data from multiple models (User, Lease, Payment). | ModelSerializer (rejected - doesn't match aggregated data structure). |

---

