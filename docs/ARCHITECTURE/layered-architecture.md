# 🧱 Layered Architecture

The codebase follows a strict 4-layer pattern to keep business logic decoupled from frameworks.

## Layer Breakdown

| Layer          | Location                                                 | Responsibility                                            |
| -------------- | -------------------------------------------------------- | --------------------------------------------------------- |
| **API**        | `apps/*/views.py`, `apps/*/serializers.py`               | Request parsing, validation, routing, response formatting |
| **Service**    | `apps/*/services.py`, `apps/core/base_service.py`        | Business rules, transactions, workflow orchestration      |
| **Repository** | `apps/*/repositories.py`, `apps/core/base_repository.py` | Data access, query building, role-based filtering         |
| **Model**      | `apps/*/models.py`                                       | Schema definition, constraints, signals, `__str__`        |

## How It Works (Flow Example)

```python
# 1. API Layer (View)
class PropertyViewSet(viewsets.ModelViewSet):
    def perform_create(self, serializer):
        service = PropertyService()
        service.create(owner=self.request.user.owner_profile, **serializer.validated_data)

# 2. Service Layer
class PropertyService(BaseService):
    @transaction.atomic
    def create(self, owner, **data):
        # Business validation
        if data.get("starting_amount") <= 0:
            raise ValidationError("Amount must be positive")

        # Delegate to repository
        return self.repository.create(owner=owner, **data)

# 3. Repository Layer
class PropertyRepository(DjangoRepository[Property]):
    def get_queryset(self, user):
        if user.is_superuser: return Property.objects.all()
        if hasattr(user, "owner_profile"): return Property.objects.filter(owners=user.owner_profile)
        return Property.objects.none()

# 4. Model Layer
class Property(TimeStampedUUIDModel):
    name = models.CharField(max_length=255)
    # ... constraints, indexes, signals
```

## Why This Pattern?

- 🔍 **Testability**: Mock `Repository` to unit-test `Service` without hitting DB
- 🛡️ **Security**: Role filtering lives in `Repository`, not scattered across views
- 🔄 **Maintainability**: Swap ORM or add caching without touching services/views
- 📐 **Consistency**: All apps follow identical structure → faster onboarding

> ⚠️ **Rule**: Never call `.objects.filter()` directly in views or serializers. Always go through `Service → Repository`.
