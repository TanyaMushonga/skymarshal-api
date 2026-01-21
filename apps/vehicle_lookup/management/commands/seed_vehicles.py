from django.core.management.base import BaseCommand
from apps.vehicle_lookup.models import VehicleRegistration
from datetime import date, timedelta
import random

class Command(BaseCommand):
    help = 'Seeds the database with dummy vehicle registrations'

    def handle(self, *args, **options):
        self.stdout.write('Seeding vehicle registrations...')
        
        # Clear existing data
        VehicleRegistration.objects.all().delete()
        
        vehicles_data = [
            {'plate': 'KCA 123A', 'make': 'Toyota', 'model': 'Corolla', 'color': 'White', 'status': 'ACTIVE'},
            {'plate': 'KCB 456B', 'make': 'Subaru', 'model': 'Impreza', 'color': 'Blue', 'status': 'ACTIVE'},
            {'plate': 'KCC 789C', 'make': 'Isuzu', 'model': 'D-Max', 'color': 'Silver', 'status': 'STOLEN'},
            {'plate': 'KCD 012D', 'make': 'Nissan', 'model': 'Note', 'color': 'Red', 'status': 'EXPIRED'},
            {'plate': 'KCE 345E', 'make': 'Honda', 'model': 'Fit', 'color': 'Black', 'status': 'ACTIVE'},
        ]
        
        today = date.today()
        future_date = today + timedelta(days=365)
        past_date = today - timedelta(days=30)
        
        for v in vehicles_data:
            expiry = past_date if v['status'] == 'EXPIRED' else future_date
            
            VehicleRegistration.objects.create(
                license_plate=v['plate'],
                owner_name=f"Owner of {v['plate']}",
                make=v['make'],
                model=v['model'],
                color=v['color'],
                status=v['status'],
                expiry_date=expiry
            )
            
        # Generate 20 more random active vehicles
        makes = ['Toyota', 'Nissan', 'Mazda', 'Honda', 'Subaru']
        colors = ['White', 'Silver', 'Black', 'Blue', 'Red']
        
        for i in range(20):
            plate = f"KCF {random.randint(100, 999)}{random.choice('ABCDEFGH')}"
            VehicleRegistration.objects.create(
                license_plate=plate,
                owner_name=f"Random Owner {i}",
                make=random.choice(makes),
                model="Generic",
                color=random.choice(colors),
                status='ACTIVE',
                expiry_date=future_date
            )

        self.stdout.write(self.style.SUCCESS(f'Successfully seeded {VehicleRegistration.objects.count()} vehicles'))
