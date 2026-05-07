# apps/reports/repositories.py
from apps.core.base_repository import DjangoRepository
from .models import Expense, TemplateConfig


class ExpenseRepository(DjangoRepository[Expense]):
    def __init__(self):
        super().__init__(Expense)


class TemplateConfigRepository(DjangoRepository[TemplateConfig]):
    def __init__(self):
        super().__init__(TemplateConfig)

    def get_default_for_landlord(self, landlord, template_type):
        return self.model_class.objects.filter(
            landlord=landlord, template_type=template_type, is_default=True
        ).first()

    def get_for_landlord(self, landlord, template_type=None):
        qs = self.model_class.objects.filter(landlord=landlord)
        if template_type:
            qs = qs.filter(template_type=template_type)
        return qs
