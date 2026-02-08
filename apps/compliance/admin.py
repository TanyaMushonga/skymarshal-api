from django.contrib import admin
from .models import ComplianceScore, LotteryEvent

@admin.register(ComplianceScore)
class ComplianceScoreAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'safe_driving_points', 'last_observation', 'created_at')
    search_fields = ('vehicle__license_plate',)
    readonly_fields = ('created_at', 'updated_at', 'last_observation')

@admin.register(LotteryEvent)
class LotteryEventAdmin(admin.ModelAdmin):
    list_display = ('name', 'draw_date', 'pool_amount', 'status', 'created_at')
    list_filter = ('status', 'draw_date')
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at')
    filter_horizontal = ('winners',)
