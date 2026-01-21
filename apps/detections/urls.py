from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DetectionViewSet

router = DefaultRouter()
router.register(r'events', DetectionViewSet, basename='detection')

urlpatterns = [
    path('', include(router.urls)),
]
