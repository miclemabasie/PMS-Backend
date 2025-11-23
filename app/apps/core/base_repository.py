from abc import ABC, abstractmethod
from typing import List, Optional, TypeVar, Generic, Dict, Any
from django.db import models
from django.core.exceptions import ObjectDoesNotExist

T = TypeVar("T", bound=models.Model)


class BaseRepository(ABC, Generic[T]):
    """Abstract base repository."""

    @abstractmethod
    def get(self, id: Any) -> Optional[T]:
        pass

    @abstractmethod
    def filter(self, **filters) -> List[T]:
        pass

    @abstractmethod
    def create(self, **data) -> T:
        pass

    @abstractmethod
    def update(self, instance: T, **data) -> T:
        pass

    @abstractmethod
    def delete(self, instance: T) -> None:
        pass


class DjangoRepository(BaseRepository[T]):
    """Django ORM implementation of BaseRepository."""

    def __init__(self, model_class: T):
        self.model_class = model_class

    def get(self, id: Any) -> Optional[T]:
        try:
            return self.model_class.objects.get(pk=id)
        except ObjectDoesNotExist:
            return None

    def filter(self, **filters) -> List[T]:
        return list(self.model_class.objects.filter(**filters))

    def create(self, **data) -> T:
        return self.model_class.objects.create(**data)

    def update(self, instance: T, **data) -> T:
        for key, value in data.items():
            setattr(instance, key, value)
        instance.save()
        return instance

    def delete(self, instance: T) -> None:
        instance.delete()
