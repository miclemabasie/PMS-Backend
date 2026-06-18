from django.contrib import admin
from .models import SubscriptionInvoice, SubscriptionPlan, BaseSubscriptionFeatureGroup

admin.site.register(SubscriptionInvoice)
admin.site.register(SubscriptionPlan)
admin.site.register(BaseSubscriptionFeatureGroup)
