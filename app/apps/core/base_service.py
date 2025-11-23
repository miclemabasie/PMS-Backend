from typing import List, Optional, TypeVar, Generic
from .base_repository import BaseRepository

T = TypeVar("T")


class BaseService(Generic[T]):
    """Base service with common CRUD operations."""

    def __init__(self, repository: BaseRepository[T]):
        self.repository = repository

    def get_by_id(self, id) -> Optional[T]:
        return self.repository.get(id)

    def get_all(self, **filters) -> List[T]:
        return self.repository.filter(**filters)

    def create(self, **data) -> T:
        # You can add pre‑create validation here
        return self.repository.create(**data)

    def update(self, id, **data) -> Optional[T]:
        instance = self.get_by_id(id)
        if instance:
            return self.repository.update(instance, **data)
        return None

    def delete(self, id) -> bool:
        instance = self.get_by_id(id)
        if instance:
            self.repository.delete(instance)
            return True
        return False
