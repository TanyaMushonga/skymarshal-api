import time
from django.db import connections
from django.db.utils import OperationalError
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Django command to wait for database."""

    def handle(self, *args, **options):
        """Entrypoint for command."""
        self.stdout.write('Waiting for database...')
        db_conn = None
        while not db_conn:
            try:
                db_conn = connections['default']
                with db_conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
            except OperationalError:
                self.stdout.write('Database unavailable, waiting 1 second...')
                db_conn = None
                time.sleep(1)

        self.stdout.write(self.style.SUCCESS('Database available!'))
