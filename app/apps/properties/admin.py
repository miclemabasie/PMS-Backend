from django.contrib import admin
from .models import Property, Owner, Unit, PropertyOwnership

admin.site.register(Owner)
admin.site.register(Unit)
admin.site.register(PropertyOwnership)
admin.site.register(Property)
