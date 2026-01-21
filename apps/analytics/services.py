from django.db.models import Count, Avg, F
from django.utils import timezone
from datetime import timedelta
from apps.violations.models import Violation
from apps.detections.models import Detection
from .models import Recommendation

class InferenceEngine:
    @staticmethod
    def generate_recommendations():
        """
        Runs heuristics/models to generate recommendations.
        Should be run periodically (e.g. daily/hourly task).
        """
        # Clear old active recommendations (optional, or archive them)
        Recommendation.objects.filter(is_active=True).update(is_active=False)
        
        last_24h = timezone.now() - timedelta(hours=24)
        last_7d = timezone.now() - timedelta(days=7)

        recommendations = []

        # Rule 1: High Violation Density
        # If > 50 violations in last 24h, recommend high alert.
        recent_violation_count = Violation.objects.filter(created_at__gte=last_24h).count()
        if recent_violation_count > 50:
            rec = Recommendation.objects.create(
                title="High Violation Surge Detected",
                description=f"Detected {recent_violation_count} violations in the last 24 hours. Suggest increasing patrol frequency immediately.",
                category='ALLOCATION',
                confidence_score=0.95
            )
            recommendations.append(rec)
            
        # Rule 2: Speeding Trend in Specific Zone (Mocking Zone logic via metadata if available)
        # For prototype, we check average speed of all detections
        avg_speed = Detection.objects.filter(timestamp__gte=last_24h).aggregate(avg=Avg('speed'))['avg']
        if avg_speed and avg_speed > 70: # Assuming general limit is 60
            rec = Recommendation.objects.create(
                title="System-wide Speeding Trend",
                description=f"Average detected speed is {avg_speed:.1f} km/h, significantly above standard limits. Consider public safety campaign.",
                category='SAFETY',
                confidence_score=0.80
            )
            recommendations.append(rec)

        # Rule 3: Low Patrol Coverage (Mock)
        # If no detections in last 6 hours, suggest check
        last_detection = Detection.objects.order_by('-timestamp').first()
        if last_detection and last_detection.timestamp < timezone.now() - timedelta(hours=6):
            rec = Recommendation.objects.create(
                title="Patrol Gap Detected",
                description="No detections received in over 6 hours. Verify drone fleet status or schedule new patrols.",
                category='MAINTENANCE',
                confidence_score=0.85
            )
            recommendations.append(rec)
            
        return recommendations

    @staticmethod
    def get_dashboard_metrics():
        today = timezone.now()
        start_of_day = today.replace(hour=0, minute=0, second=0, microsecond=0)
        
        total_violations_today = Violation.objects.filter(created_at__gte=start_of_day).count()
        active_patrols = 0 # Need patrol app import or direct query if circular import issue
        # To avoid circular import, we can do loose coupling or simple import inside method
        try:
            from apps.patrols.models import Patrol
            active_patrols = Patrol.objects.filter(status='ACTIVE').count()
        except ImportError:
            pass

        return {
            'violations_today': total_violations_today,
            'active_patrols': active_patrols,
            'avg_compliance_score': 85.5, # Placeholder or agg from ComplianceScore
            'system_status': 'OPERATIONAL'
        }
