from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PatrolViewSet

router = DefaultRouter()
router.register(r'patrols', PatrolViewSet, basename='patrol')

urlpatterns = [
    path('', include(router.urls)),
]
