from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router
router = DefaultRouter()
router.register(r'streams', views.VideoStreamViewSet, basename='videostream')
router.register(r'sessions', views.StreamSessionViewSet, basename='streamsession')

urlpatterns = [
    path('', include(router.urls)),
]
