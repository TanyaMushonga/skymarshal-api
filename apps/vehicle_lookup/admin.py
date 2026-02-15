from django.contrib import admin
from .models import VehicleRegistration

@admin.register(VehicleRegistration)
class VehicleRegistrationAdmin(admin.ModelAdmin):
    list_display = ('license_plate', 'owner_name', 'make', 'model', 'expiry_date')
    list_filter = ('make',)
    search_fields = ('license_plate', 'owner_name')
    ordering = ('license_plate',)
