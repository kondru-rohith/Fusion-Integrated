"""Management command to send renewal reminders for eligible scholarships (R1-17, UC-SPACS-025)."""

from __future__ import annotations

from django.core.management.base import BaseCommand

from modules.spacs.services import tasks


class Command(BaseCommand):
    help = "Send reminders to students eligible for scholarship renewal"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate the reminder sweep without queuing notifications",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        if dry_run:
            self.stdout.write("Running renewal reminder sweep in dry-run mode...")
            count = 0
        else:
            count = tasks.send_renewal_reminders()

        self.stdout.write(
            self.style.SUCCESS(f"Renewal reminder sweep completed: {count} reminded.")
        )
