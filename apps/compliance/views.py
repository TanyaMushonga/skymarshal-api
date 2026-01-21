from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum
from .models import LotteryEvent, ComplianceScore
from rest_framework import serializers
from apps.violations.models import Violation
import random

class LotteryEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = LotteryEvent
        fields = '__all__'
        read_only_fields = ['pool_amount', 'status', 'winners']

class LotteryViewSet(viewsets.ModelViewSet):
    queryset = LotteryEvent.objects.all()
    serializer_class = LotteryEventSerializer
    permission_classes = [permissions.IsAdminUser]

    @action(detail=True, methods=['post'])
    def run_draw(self, request, pk=None):
        lottery = self.get_object()
        
        if lottery.status != 'OPEN':
            return Response({'error': 'Lottery already drawn or closed'}, status=400)
        
        # 1. Calculate Pool (Mock Logic: 10% of all fines collected ever, or simpler: 1000 flat)
        # Real logic: Aggregate Violation.fine_amount where status='PAID' (if we had paid status tracking)
        # For prototype: Sum of ALL fines assigned * 0.10
        total_fines = Violation.objects.aggregate(total=Sum('fine_amount'))['total'] or 0.00
        pool = float(total_fines) * 0.10
        lottery.pool_amount = pool
        
        # 2. Select Candidates (Points > 50, for example)
        # Or simply top 20%? Let's say anyone with > 10 points
        candidates = ComplianceScore.objects.filter(safe_driving_points__gte=10)
        candidate_list = list(candidates)
        
        if not candidate_list:
             return Response({'error': 'No eligible drivers (need > 10 pts)'}, status=400)

        # 3. Pick Winners (3 winners)
        num_winners = min(3, len(candidate_list))
        winners_scores = random.sample(candidate_list, num_winners)
        
        won_vehs = []
        for score in winners_scores:
            lottery.winners.add(score.vehicle)
            won_vehs.append(score.vehicle)
            
            # 4. Notify Winner
            if score.vehicle.owner_phone_number:
                from apps.notifications.tasks import send_sms_to_citizen
                msg = (f"CONGRATULATIONS {score.vehicle.owner_name}! "
                       f"You've won a share of the safe driving pool: ${pool/num_winners:.2f}. "
                       f"Keep driving safely! - SkyMarshal")
                send_sms_to_citizen.delay(score.vehicle.owner_phone_number, msg)

        lottery.status = 'DRAWN'
        lottery.save()
        
        return Response({
            'status': 'Drawn',
            'pool': pool,
            'winners_count': len(won_vehs),
            'winners': [v.license_plate for v in won_vehs]
        })
