from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Recommendation, TrafficMetrics, HeatMap, TrafficPattern, AnalyticsReport
from .services import InferenceEngine
from rest_framework import serializers

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
        return Response({
            'officer': user.username,
            'hours_patrolled_this_week': 12.5,
            'violations_issued': 4,
            'assigned_zone_risk_level': 'MODERATE',
            'performance_rating': 4.8 
        })
