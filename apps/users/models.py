from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils.translation import gettext_lazy as _
from .managers import CustomUserManager

from apps.core.models import TimestampedModel

ROLE_CHOICES = (
    ('admin', 'Admin'),
    ('officer', 'Officer'),
    ('dispatcher', 'Dispatcher'),
)
class User(AbstractBaseUser, PermissionsMixin, TimestampedModel):
    email = models.EmailField(_('email address'), unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)

    # Role & Hierarchy
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='officer')
    force_number = models.CharField(max_length=50, blank=True, null=True, unique=True, help_text="Officer Force Number")
    unit_id = models.CharField(max_length=50, blank=True, null=True)

    # Certification (Drone Specific)
    is_certified_pilot = models.BooleanField(default=False)
    pilot_license_number = models.CharField(max_length=100, blank=True, null=True)
    license_expiry_date = models.DateField(blank=True, null=True)

    # Security & 2FA
    phone_number = models.CharField(max_length=20, blank=True, null=True, unique=True, help_text="Contact phone number for 2FA")
    is_2fa_enabled = models.BooleanField(default=False)
    requires_password_change = models.BooleanField(default=True, help_text="Forces user to change password on next login")

    # Tactical Location Data
    last_known_lat = models.FloatField(null=True, blank=True)
    last_known_lon = models.FloatField(null=True, blank=True)
    is_on_duty = models.BooleanField(default=False)

    # Audit Trail
    created_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_users')

    @property
    def is_officer(self):
        return self.role == 'officer'
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
