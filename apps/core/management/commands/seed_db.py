import random
import uuid
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.gis.geos import Point
from django.db import transaction

from apps.users.models import User
from apps.drones.models import Drone, DroneStatus, GPSLocation, DroneAPIKey
from apps.vehicle_lookup.models import VehicleRegistration
from apps.patrols.models import Patrol
from apps.detections.models import Detection
from apps.violations.models import Violation
from apps.compliance.models import ComplianceScore, LotteryEvent
from apps.analytics.models import Recommendation, TrafficMetrics, HeatMap, TrafficPattern, AnalyticsReport
from apps.notifications.models import Notification


class Command(BaseCommand):
    help = 'Seeds the database with comprehensive test data for SkyMarshal'

    def handle(self, *args, **options):
        self.stdout.write('Starting database seeding...')
        
        try:
            with transaction.atomic():
                self.clear_existing_data()
                
                self.stdout.write('Seeding Users...')
                users = self.seed_users()
                self.stdout.write('Seeding Drones...')
                drones = self.seed_drones(users)
                self.stdout.write('Seeding Vehicles...')
                vehicles = self.seed_vehicles()
                self.stdout.write('Seeding Patrols...')
                patrols = self.seed_patrols(users, drones)
                self.stdout.write('Seeding Detections...')
                detections = self.seed_detections(drones, patrols)
                self.stdout.write('Seeding Violations...')
                violations = self.seed_violations(patrols, detections)
                self.stdout.write('Seeding Compliance...')
                self.seed_compliance(vehicles)
                self.stdout.write('Seeding Analytics...')
                self.seed_analytics(users, drones)
                self.stdout.write('Seeding Notifications...')
                self.seed_notifications(users)
                
            self.stdout.write(self.style.SUCCESS('Successfully seeded the database.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Seeding failed: {str(e)}'))
            raise e

    def clear_existing_data(self):
        self.stdout.write('Clearing existing data...')
        # Clear in reverse order of dependencies
        Notification.objects.all().delete()
        AnalyticsReport.objects.all().delete()
        TrafficPattern.objects.all().delete()
        HeatMap.objects.all().delete()
        TrafficMetrics.objects.all().delete()
        Recommendation.objects.all().delete()
        LotteryEvent.objects.all().delete()
        ComplianceScore.objects.all().delete()
        Violation.objects.all().delete()
        Detection.objects.all().delete()
        Patrol.objects.all().delete()
        VehicleRegistration.objects.all().delete()
        DroneAPIKey.objects.all().delete()
        DroneStatus.objects.all().delete()
        GPSLocation.objects.all().delete()
        Drone.objects.all().delete()
        User.objects.exclude(is_superuser=True).delete()

    def seed_users(self):
        self.stdout.write('Seeding users...')
        users = []
        
        # Create Admins
        for i in range(3):
            user = User.objects.create(
                email=f'admin{i}@skymarshal.local',
                first_name=f'Admin',
                last_name=str(i),
                role='admin',
                is_staff=True,
                force_number=f'ADM-{1000+i}'
            )
            user.set_password('password123')
            user.save()
            users.append(user)
            
        # Create Officers
        for i in range(12):
            user = User.objects.create(
                email=f'officer{i}@skymarshal.local',
                first_name=f'Officer',
                last_name=str(i),
                role='officer',
                force_number=f'OFF-{2000+i}',
                unit_id=f'UNIT-{i // 4 + 1}',
                is_certified_pilot=True,
                pilot_license_number=f'PILOT-{5000+i}',
                license_expiry_date=timezone.now().date() + timedelta(days=365),
                is_on_duty=random.choice([True, False])
            )
            user.set_password('password123')
            user.save()
            users.append(user)
            
        return users

    def seed_drones(self, users):
        self.stdout.write('Seeding drones...')
        drones = []
        models = ['DJI Matrice 300', 'Skydio X2', 'Parrot Anafi USA', 'Autel Evo II']
        officers = [u for u in users if u.role == 'officer']
        
        for i in range(10):
            drone = Drone.objects.create(
                drone_id=f'DR-{i:03d}',
                name=f'Sky Hawk {i+1}',
                model=random.choice(models),
                serial_number=str(uuid.uuid4())[:18].upper(),
                assigned_officer=random.choice(officers) if i < 8 else None,
                max_speed=random.choice([60.0, 75.0, 80.0])
            )
            
            # Status
            DroneStatus.objects.create(
                drone=drone,
                battery_level=random.randint(15, 100),
                signal_strength=random.randint(60, 100),
                status=random.choice(['online', 'offline', 'online', 'maintenance'])
            )
            
            # API Key
            DroneAPIKey.objects.get_or_create(drone=drone)
            
            # Initial GPS
            GPSLocation.objects.create(
                drone=drone,
                location=Point(36.8219 + random.uniform(-0.05, 0.05), -1.2921 + random.uniform(-0.05, 0.05)),
                altitude=random.uniform(50, 150)
            )
            
            drones.append(drone)
        return drones

    def seed_vehicles(self):
        self.stdout.write('Seeding vehicles...')
        vehicles = []
        makes = ['Toyota', 'Nissan', 'Mazda', 'Honda', 'Subaru', 'Mercedes', 'BMW', 'Volkswagen']
        colors = ['White', 'Silver', 'Black', 'Blue', 'Red', 'Gray']
        statuses = ['ACTIVE', 'ACTIVE', 'ACTIVE', 'STOLEN', 'EXPIRED']
        
        for i in range(40):
            plate = f"K{random.choice('ABCDEF')}{random.choice('ABCDEF')} {random.randint(100, 999)}{random.choice('ABCDEF')}"
            status = random.choice(statuses)
            v = VehicleRegistration.objects.create(
                license_plate=plate,
                owner_name=f"Citizen {i}",
                owner_phone_number=f"+25470000{i:04d}",
                make=random.choice(makes),
                model="Standard Module",
                color=random.choice(colors),
                status=status,
                expiry_date=timezone.now().date() + timedelta(days=random.randint(-30, 365))
            )
            vehicles.append(v)
        return vehicles

    def seed_patrols(self, users, drones):
        self.stdout.write('Seeding patrols...')
        patrols = []
        officers = [u for u in users if u.role == 'officer']
        
        # Past Patrols
        for i in range(15):
            start = timezone.now() - timedelta(days=random.randint(1, 14), hours=random.randint(0, 23))
            end = start + timedelta(hours=random.randint(1, 4))
            p = Patrol.objects.create(
                drone=random.choice(drones),
                officer=random.choice(officers),
                start_time=start,
                end_time=end,
                status='COMPLETED',
                patrol_config={"speed_limit": 60, "mode": "highway"}
            )
            patrols.append(p)
            
        # Active Patrols
        for i in range(3):
            p = Patrol.objects.create(
                drone=random.choice(drones),
                officer=random.choice(officers),
                start_time=timezone.now() - timedelta(minutes=random.randint(10, 60)),
                status='ACTIVE',
                patrol_config={"speed_limit": 50, "mode": "urban"}
            )
            patrols.append(p)
            
        return patrols

    def seed_detections(self, drones, patrols):
        self.stdout.write('Seeding detections...')
        detections = []
        vehicle_types = ['car', 'truck', 'motorcycle', 'bus']
        
        for p in patrols:
            # Seed 5-10 detections per patrol
            num_detections = random.randint(5, 10)
            # Ensure at least 3 detections are speeding (above p.patrol_config.get('speed_limit', 60))
            limit = float(p.patrol_config.get('speed_limit', 60))
            
            for i in range(num_detections):
                # 40% chance of speeding for interesting data
                is_speeding = random.random() < 0.4
                if is_speeding:
                    speed = random.uniform(limit + 5, limit + 60)
                else:
                    speed = random.uniform(20, limit - 2)
                
                d = Detection.objects.create(
                    drone=p.drone,
                    patrol=p,
                    timestamp=p.start_time + timedelta(minutes=random.randint(5, 120)),
                    frame_number=i * 100,
                    vehicle_type=random.choice(vehicle_types),
                    confidence=random.uniform(0.7, 0.99),
                    box_coordinates=[random.randint(0, 100) for _ in range(4)],
                    license_plate=f"K{random.choice('ABC')}{random.choice('XYZ')} {random.randint(100, 999)}",
                    speed=speed,
                    location=Point(36.8219 + random.uniform(-0.02, 0.02), -1.2921 + random.uniform(-0.02, 0.02)),
                    altitude=random.uniform(20, 100)
                )
                detections.append(d)
        return detections

    def seed_violations(self, patrols, detections):
        self.stdout.write('Seeding violations...')
        violations = []
        # Scope limited to SPEEDING only
        violation_types = ['SPEEDING']
        
        # Signals already create some violations for speeding detections.
        # We supplement or ensure consistent data here.
        potential_violations = [d for d in detections if d.speed > 60] # Basic filter
        sample_size = min(len(potential_violations), 30)
        if sample_size > 0:
            for det in random.sample(potential_violations, sample_size):
                v_type = 'SPEEDING'
                v, created = Violation.objects.get_or_create(
                    detection=det,
                    defaults={
                        'patrol': det.patrol,
                        'violation_type': v_type,
                        'status': random.choice(['NEW', 'PROCESSED', 'CITATION_SENT']),
                        'fine_amount': Decimal(random.randint(50, 200)),
                        'description': f"Detected {v_type} at {det.speed:.1f} km/h"
                    }
                )
                violations.append(v)
        return violations

    def seed_compliance(self, vehicles):
        self.stdout.write('Seeding compliance data...')
        for v in vehicles:
            ComplianceScore.objects.create(
                vehicle=v,
                safe_driving_points=random.randint(0, 100)
            )
            
        for i in range(5):
            le = LotteryEvent.objects.create(
                name=f"Safe Driver Monthly Reward #{i+1}",
                draw_date=timezone.now().date() + timedelta(days=random.randint(-30, 30)),
                pool_amount=Decimal(random.randint(500, 5000)),
                minimum_points=random.randint(10, 50),
                status=random.choice(['OPEN', 'DRAWN', 'PAID'])
            )
            if le.status != 'OPEN':
                # Add 3 random winners
                le.winners.add(*random.sample(list(vehicles), 3))

    def seed_analytics(self, users, drones):
        self.stdout.write('Seeding analytics data...')
        
        # Recommendations
        for i in range(10):
            Recommendation.objects.create(
                title=f"Traffic Optimization Suggestion {i+1}",
                description=f"Based on pattern analysis, we recommend adjusting patrol frequency in zone {i // 3 + 1}.",
                category=random.choice(['ALLOCATION', 'SAFETY', 'MAINTENANCE', 'POLICY']),
                confidence_score=random.uniform(0.6, 0.95),
                is_active=random.choice([True, True, False])
            )
            
        # Traffic Metrics
        for drone in drones:
            for h in range(12):
                ts = timezone.now() - timedelta(hours=h)
                TrafficMetrics.objects.create(
                    timestamp=ts,
                    location=Point(36.8219, -1.2921),
                    drone_id=drone.drone_id,
                    vehicle_count=random.randint(50, 500),
                    average_speed=random.uniform(40, 90),
                    violation_count=random.randint(0, 10)
                )
                
        # Heatmaps
        for i in range(5):
            HeatMap.objects.get_or_create(
                date=timezone.now().date() - timedelta(days=i),
                hour=random.randint(8, 20),
                metric_type='volume',
                defaults={
                    'location_grid': {"data": [[random.random() for _ in range(10)] for _ in range(10)]},
                    'min_lat': -1.4, 'max_lat': -1.2, 'min_lon': 36.7, 'max_lon': 36.9
                }
            )
            
        # Patterns
        TrafficPattern.objects.create(
            pattern_type='peak_hour',
            location=Point(36.8219, -1.2921),
            location_name="Waiyaki Way Intersection",
            days_of_week=[0, 1, 2, 3, 4],
            start_hour=7,
            end_hour=9,
            avg_vehicle_count=1200,
            avg_speed=15.5,
            confidence_score=0.92
        )
        
        # Reports
        admins = [u for u in users if u.role == 'admin']
        for i in range(5):
            AnalyticsReport.objects.create(
                report_type=random.choice(['daily', 'weekly']),
                title=f"System Performance Report - Week {i+1}",
                start_date=timezone.now().date() - timedelta(days=7*(i+1)),
                end_date=timezone.now().date() - timedelta(days=7*i),
                report_data={"total_violations": random.randint(100, 500), "top_drone": "DR-005"},
                summary="Overall traffic safety compliance increased by 5% this period.",
                generated_by=random.choice(admins)
            )

    def seed_notifications(self, users):
        self.stdout.write('Seeding notifications...')
        types = ['violation_detected', 'patrol_started', 'low_battery', 'system_alert']
        for user in users:
            for i in range(random.randint(3, 8)):
                Notification.objects.create(
                    recipient=user,
                    title=f"Test Notification {i+1}",
                    message=f"This is a sample notification for testing the {random.choice(types)} event flow.",
                    notification_type=random.choice(types),
                    is_read=random.choice([True, False])
                )
