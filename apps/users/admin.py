from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

class UserAdmin(BaseUserAdmin):
    ordering = ['email']
    list_display = ('email', 'first_name', 'last_name', 'role', 'force_number', 'is_on_duty', 'is_certified_pilot')
    list_filter = ('role', 'is_on_duty', 'is_certified_pilot', 'is_2fa_enabled', 'is_active')
    search_fields = ('email', 'first_name', 'last_name', 'force_number', 'phone_number')
    readonly_fields = ('created_at', 'last_login', 'created_by')
    
    # Fieldsets for edit view
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'phone_number', 'force_number', 'unit_id')}),
        ('Role & Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Certification', {'fields': ('is_certified_pilot', 'pilot_license_number', 'license_expiry_date')}),
        ('Tactical', {'fields': ('is_on_duty', 'last_known_lat', 'last_known_lon')}),
        ('Security', {'fields': ('is_2fa_enabled', 'requires_password_change')}),
        ('Audit', {'fields': ('created_at', 'last_login', 'created_by')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password', 'first_name', 'last_name', 'role'),
        }),
    )

admin.site.register(User, UserAdmin)
