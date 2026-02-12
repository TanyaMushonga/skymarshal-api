from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AdminAnalyticsViewSet, OfficerAnalyticsViewSet, OfficerDashboardViewSet

router = DefaultRouter()
# ViewSets are ViewSets not ModelViewSets, so we explicit register if using router 
# or manual paths. Since they are ViewSets (ViewSet), router works if we provide basename.
router.register(r'admin', AdminAnalyticsViewSet, basename='admin-analytics')
router.register(r'officer', OfficerAnalyticsViewSet, basename='officer-analytics')
router.register(r'dashboard', OfficerDashboardViewSet, basename='officer-dashboard')

urlpatterns = [
    path('', include(router.urls)),
]
