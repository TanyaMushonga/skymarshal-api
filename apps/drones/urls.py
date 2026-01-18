from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DroneViewSet, GPSLocationViewSet, DroneStatusViewSet

router = DefaultRouter()
router.register(r'drones', DroneViewSet, basename='drone')
router.register(r'gps-locations', GPSLocationViewSet, basename='gps-location')
router.register(r'drone-status', DroneStatusViewSet, basename='drone-status')

urlpatterns = [
    path('', include(router.urls)),
]
