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
        read_only_fields = ['status', 'winners'] # pool_amount IS WRITABLE NOW

class LotteryViewSet(viewsets.ModelViewSet):
    queryset = LotteryEvent.objects.all()
    serializer_class = LotteryEventSerializer
    permission_classes = [permissions.IsAdminUser]

    @action(detail=True, methods=['post'])
    def run_draw(self, request, pk=None):
        lottery = self.get_object()
        
        if lottery.status != 'OPEN':
            return Response({'error': 'Lottery already drawn or closed'}, status=400)
        
        # 1. Validate Pool
        if lottery.pool_amount <= 0:
            return Response({'error': 'Pool amount must be greater than 0. Please set a pool amount.'}, status=400)
        
        pool = float(lottery.pool_amount)
        
        # 2. Select Candidates (Use Configured Minimum Points)
        min_pts = lottery.minimum_points
        candidates = ComplianceScore.objects.filter(safe_driving_points__gte=min_pts)
        candidate_list = list(candidates)
        
        if not candidate_list:
             return Response({'error': f'No eligible drivers found with > {min_pts} points'}, status=400)

        # 3. Pick Winners (3 winners or less)
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
