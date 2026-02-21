from django.core.management.base import BaseCommand
from django.db import transaction
from apps.detections.models import Detection
from apps.violations.models import Violation, ViolationPayment
from apps.patrols.models import Patrol
from apps.stream_ingestion.models import VideoStream, StreamSession
from apps.vehicle_lookup.models import VehicleRegistration
from apps.analytics.models import Recommendation, TrafficMetrics, HeatMap, TrafficPattern, AnalyticsReport
from apps.notifications.models import Notification

class Command(BaseCommand):
    help = 'Clears all operational data (Detections, Violations, Patrols, etc.) while preserving Users.'

    def handle(self, *args, **options):
        self.stdout.write("Clearing operational data...")
        
        with transaction.atomic():
            # Notifications & Payments (Dependencies first)
            ViolationPayment.objects.all().delete()
            Notification.objects.all().delete()
            
            # Violations & Detections
            Violation.objects.all().delete()
            Detection.objects.all().delete()
            
            # Patrols & Streams
            StreamSession.objects.all().delete()
            # We keep VideoStream definitions, but reset their active status
            VideoStream.objects.all().update(is_active=False)
            Patrol.objects.all().delete()
            
            # Vehicles
            VehicleRegistration.objects.all().delete()
            
            # Analytics
            Recommendation.objects.all().delete()
            TrafficMetrics.objects.all().delete()
            HeatMap.objects.all().delete()
            TrafficPattern.objects.all().delete()
            AnalyticsReport.objects.all().delete()

        self.stdout.write(self.style.SUCCESS("Successfully cleared operational data!"))
