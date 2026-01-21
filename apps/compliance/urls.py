from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LotteryViewSet

router = DefaultRouter()
router.register(r'lotteries', LotteryViewSet, basename='lottery')

urlpatterns = [
    path('', include(router.urls)),
]
