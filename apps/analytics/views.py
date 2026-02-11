from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Recommendation, TrafficMetrics, HeatMap, TrafficPattern, AnalyticsReport
from .services import InferenceEngine
from rest_framework import serializers
from django.db.models import Count, Sum
from apps.patrols.models import Patrol
from apps.violations.models import Violation
from apps.detections.models import Detection
from apps.patrols.serializers import PatrolSerializer
from apps.violations.serializers import ViolationSerializer
from django.utils import timezone
from datetime import timedelta

# Serializers
class RecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recommendation
        fields = '__all__'

class TrafficMetricsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrafficMetrics
        fields = '__all__'

class HeatMapSerializer(serializers.ModelSerializer):
    class Meta:
        model = HeatMap
        fields = '__all__'

class TrafficPatternSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrafficPattern
        fields = '__all__'

class AnalyticsReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticsReport
        fields = '__all__'

from rest_framework.pagination import PageNumberPagination

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 1000

# ViewSets
class AdminAnalyticsViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAdminUser]

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """
        Main Admin Dashboard API.
        Returns metrics + active recommendations.
        """
        if not Recommendation.objects.filter(is_active=True).exists():
            InferenceEngine.generate_recommendations()
            
        metrics = InferenceEngine.get_dashboard_metrics()
        recommendations = Recommendation.objects.filter(is_active=True).order_by('-confidence_score')
        
        return Response({
            'metrics': metrics,
            'recommendations': RecommendationSerializer(recommendations, many=True).data
        })

    @action(detail=False, methods=['post'])
    def run_inference(self, request):
        """
        Force run the inference engine.
        """
        recs = InferenceEngine.generate_recommendations()
        return Response({
            'status': 'Inference Complete',
            'recommendations_generated': len(recs),
            'data': RecommendationSerializer(recs, many=True).data
        })
    
    @action(detail=False, methods=['get'])
    def metrics(self, request):
        """
        Get time-series traffic metrics.
        Supports filtering: drone_id, start_date, end_date
        """
        queryset = TrafficMetrics.objects.all().order_by('-timestamp')
        
        # Clean Filters
        drone_id = request.query_params.get('drone_id')
        if drone_id:
            queryset = queryset.filter(drone_id=drone_id)
            
        start_date = request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)
            
        end_date = request.query_params.get('end_date')
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)

        # Pagination
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = TrafficMetricsSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        # Fallback if pagination disabled (though it's enabled above)
        return Response(TrafficMetricsSerializer(queryset, many=True).data)

    @action(detail=False, methods=['get'])
    def heatmap(self, request):
        """
        Get heatmap. Filters: date (YYYY-MM-DD), hour (0-23), metric_type.
        Defaults to latest available if no filters.
        """
        queryset = HeatMap.objects.all()
        
        date = request.query_params.get('date')
        if date:
            queryset = queryset.filter(date=date)
            
        hour = request.query_params.get('hour')
        if hour:
            queryset = queryset.filter(hour=hour)
            
        metric_type = request.query_params.get('metric_type')
        if metric_type:
            queryset = queryset.filter(metric_type=metric_type)
            
        # Get one map
        latest = queryset.order_by('-date', '-hour').first()
        if latest:
            return Response(HeatMapSerializer(latest).data)
        return Response({})

    @action(detail=False, methods=['get'])
    def patterns(self, request):
        """
        Get identified traffic patterns.
        """
        queryset = TrafficPattern.objects.all().order_by('-created_at')
        
        pattern_type = request.query_params.get('pattern_type')
        if pattern_type:
            queryset = queryset.filter(pattern_type=pattern_type)
            
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            return paginator.get_paginated_response(TrafficPatternSerializer(page, many=True).data)
            
        return Response(TrafficPatternSerializer(queryset, many=True).data)

    @action(detail=False, methods=['get'])
    def reports(self, request):
        """
        List generated reports.
        """
        queryset = AnalyticsReport.objects.all().order_by('-created_at')
        
        report_type = request.query_params.get('report_type')
        if report_type:
            queryset = queryset.filter(report_type=report_type)
            
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            return paginator.get_paginated_response(AnalyticsReportSerializer(page, many=True).data)
            
        return Response(AnalyticsReportSerializer(queryset, many=True).data)

class OfficerAnalyticsViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def my_stats(self, request):
        """
        Returns stats specific to the logged-in officer.
        """
        user = request.user
        
        # Real stats queries
        total_patrols = Patrol.objects.filter(officer=user).count()
        total_violations = Violation.objects.filter(patrol__officer=user).count()
        total_detections = Detection.objects.filter(patrol__officer=user).count()
        
        # Calculate hours patrolled this week
        one_week_ago = timezone.now() - timedelta(days=7)
        weekly_patrols = Patrol.objects.filter(
            officer=user, 
            start_time__gte=one_week_ago,
            status='COMPLETED'
        )
        
        total_duration_seconds = 0
        for p in weekly_patrols:
            if p.end_time:
                total_duration_seconds += (p.end_time - p.start_time).total_seconds()
        
        hours_patrolled = round(total_duration_seconds / 3600, 1)

        return Response({
            'officer': user.email,
            'officer_name': f"{user.first_name} {user.last_name}".strip() or user.email,
            'hours_patrolled_this_week': hours_patrolled,
            'violations_issued': total_violations,
            'total_detections': total_detections,
            'total_patrols': total_patrols,
            'assigned_zone_risk_level': 'MODERATE',
            'performance_rating': 4.8 
        })

class OfficerDashboardViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        """
        Comprehensive dashboard summary for the mobile home page.
        """
        user = request.user
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # 1. Active Patrol
        active_patrol = Patrol.objects.filter(officer=user, status='ACTIVE').first()
        active_patrol_data = PatrolSerializer(active_patrol).data if active_patrol else None

        # 2. Today's Stats
        today_stats = {
            'patrols': Patrol.objects.filter(officer=user, start_time__gte=today_start).count(),
            'detections': Detection.objects.filter(patrol__officer=user, timestamp__gte=today_start).count(),
            'violations': Violation.objects.filter(patrol__officer=user, created_at__gte=today_start).count(),
        }

        # 3. Recent Violations/Alerts
        recent_violations = Violation.objects.filter(
            patrol__officer=user
        ).order_by('-created_at')[:5]
        
        return Response({
            'active_patrol': active_patrol_data,
            'today_stats': today_stats,
            'recent_alerts': ViolationSerializer(recent_violations, many=True).data,
            'is_on_duty': user.is_on_duty
        })
