# ADR-001: Repository Pattern for Data Access

| Metadata | Value |
|----------|-------|
| Status | `accepted` |
| Date | 2026-02-01 |
| Deciders | Backend Team |
| Related | `apps/core/base_repository.py`, `apps/*/repositories.py` |

## Context
Django's ORM encourages direct `.objects.filter()` calls in views. This leads to:
- Scattered query logic
- Hard-to-test view code
- Inconsistent role filtering
- Tight coupling to Django ORM

## Decision
Implement a generic `BaseRepository[T]` abstracted behind `DjangoRepository[T]`. All data access flows through this layer.

```python
class BaseRepository(ABC, Generic[T]):
    @abstractmethod def get(self, id) -> Optional[T]: ...
    @abstractmethod def filter(self, **kwargs) -> List[T]: ...
    @abstractmethod def create(self, **data) -> T: ...
    @abstractmethod def update(self, instance: T, **data) -> T: ...
    @abstractmethod def delete(self, instance: T) -> None: ...
```

## Consequences
✅ Services are fully testable with mocked repositories  
✅ Role-based filtering centralized in `get_queryset(user)`  
✅ Easy to swap ORM or add caching layer later  
⚠️ Slightly more boilerplate for simple CRUD  
⚠️ Requires team discipline (no direct ORM calls in views)

## Validation
- 85%+ test coverage on repository methods
- Zero direct `.objects` calls in `views.py` or `serializers.py`
- CI enforces via custom lint check (future)

## References
- `apps/core/base_repository.py`
- `apps/properties/repositories.py`
- `pytest` fixtures mocking `DjangoRepository`