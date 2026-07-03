from django.contrib import admin
from .models import MaintenanceRequest, Vendor


admin.site.register(MaintenanceRequest)
admin.site.register(Vendor)


