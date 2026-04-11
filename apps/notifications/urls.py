from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'', views.NotificationViewSet, basename='notification')

urlpatterns = [
    path('test-sms/', views.test_sms, name='test_sms'),
    path('', include(router.urls)),
]
