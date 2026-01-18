from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DroneViewSet, TelemetryViewSet

router = DefaultRouter()
router.register(r'drones', DroneViewSet, basename='drone')
router.register(r'telemetry', TelemetryViewSet, basename='telemetry')

urlpatterns = [
    path('', include(router.urls)),
]
