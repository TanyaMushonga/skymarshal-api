from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LotteryViewSet, ComplianceScoreViewSet

router = DefaultRouter()
router.register(r'lotteries', LotteryViewSet, basename='lottery')
router.register(r'scores', ComplianceScoreViewSet, basename='compliance-score')

urlpatterns = [
    path('', include(router.urls)),
]
