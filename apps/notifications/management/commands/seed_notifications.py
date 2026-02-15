import random
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.users.models import User
from apps.notifications.models import Notification

class Command(BaseCommand):
    help = 'Seeds notifications for a specific user'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, help='Email of the user to seed notifications for', default='tanyaradzwatmushonga@gmail.com')
        parser.add_argument('--count', type=int, help='Number of notifications to seed', default=10)

    def handle(self, *args, **options):
        email = options['email']
        count = options['count']

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            user = User.objects.first()
            if not user:
                self.stdout.write(self.style.ERROR('No users found in the database.'))
                return
            self.stdout.write(self.style.WARNING(f'User with email "{email}" not found. Seeding for "{user.email}" instead.'))

        notification_types = [
            ('violation_detected', 'Violation Detected'),
            ('patrol_started', 'Patrol Started'),
            ('patrol_ended', 'Patrol Ended'),
            ('low_battery', 'Low Battery'),
            ('system_alert', 'System Alert'),
            ('general', 'General'),
        ]

        sample_messages = [
            "A new speeding violation has been detected in Zone A.",
            "Patrol mission Alpha-1 has successfully started.",
            "Drone DR-005 has returned to base and ended its patrol.",
            "Warning: Drone DR-002 battery level is below 15%.",
            "System maintenance scheduled for 02:00 AM.",
            "New security update available for the telemetry module.",
            "Weather conditions are suboptimal for flight in the north sector.",
            "Unauthorized drone activity reported near the peri-urban boundary.",
            "Patrol schedule for tomorrow has been updated.",
            "Your daily patrol summary report is now ready."
        ]

        self.stdout.write(f'Seeding {count} notifications for {user.email}...')

        for i in range(count):
            n_type, n_title = random.choice(notification_types)
            message = random.choice(sample_messages)
            
            Notification.objects.create(
                recipient=user,
                title=n_title,
                message=message,
                notification_type=n_type,
                is_read=random.choice([True, False]),
                created_at=timezone.now() - timezone.timedelta(hours=random.randint(0, 48))
            )

        self.stdout.write(self.style.SUCCESS(f'Successfully seeded {count} notifications.'))
