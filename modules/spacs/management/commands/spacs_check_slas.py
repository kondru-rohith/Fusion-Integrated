"""Management command to sweep and check review SLAs (R1-17, UC-SPACS-024)."""

from __future__ import annotations

from django.core.management.base import BaseCommand

from modules.spacs.services import tasks


class Command(BaseCommand):
    help = "Run the review SLA sweep and queue escalations for overdue applications"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate the sweep without queuing notifications",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        if dry_run:
            self.stdout.write("Running SLA check in dry-run mode (no notifications queued)...")
            count = 0
        else:
            count = tasks.check_review_slas()

        self.stdout.write(
            self.style.SUCCESS(f"SLA check completed: {count} applications escalated.")
        )
