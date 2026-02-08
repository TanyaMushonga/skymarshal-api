from django.contrib import admin
from django.contrib.gis import admin as gis_admin
from .models import Recommendation, TrafficMetrics, HeatMap, TrafficPattern, AnalyticsReport

@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'confidence_score', 'is_active', 'created_at')
    list_filter = ('category', 'is_active')
    search_fields = ('title', 'description')

@admin.register(TrafficMetrics)
class TrafficMetricsAdmin(gis_admin.GISModelAdmin):
    list_display = ('timestamp', 'drone_id', 'vehicle_count', 'average_speed', 'violation_count')
    list_filter = ('drone_id', 'timestamp')
    search_fields = ('drone_id',)

@admin.register(HeatMap)
class HeatMapAdmin(admin.ModelAdmin):
    list_display = ('date', 'hour', 'metric_type', 'created_at')
    list_filter = ('metric_type', 'date')

@admin.register(TrafficPattern)
class TrafficPatternAdmin(gis_admin.GISModelAdmin):
    list_display = ('pattern_type', 'location_name', 'confidence_score', 'avg_vehicle_count')
    list_filter = ('pattern_type',)
    search_fields = ('location_name',)

@admin.register(AnalyticsReport)
class AnalyticsReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'report_type', 'start_date', 'end_date', 'generated_by', 'is_public')
    list_filter = ('report_type', 'is_public', 'created_at')
    search_fields = ('title', 'summary')
