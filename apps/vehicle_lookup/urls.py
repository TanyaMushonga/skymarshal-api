from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import VehicleRegistrationViewSet

router = DefaultRouter()
router.register(r'vehicles', VehicleRegistrationViewSet, basename='vehicle')

urlpatterns = [
    path('', include(router.urls)),
]
