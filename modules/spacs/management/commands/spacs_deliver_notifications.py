"""Management command to deliver pending outbox notifications (R1-17)."""

from __future__ import annotations

from django.core.management.base import BaseCommand

from modules.spacs.services import notifications


class Command(BaseCommand):
    help = "Drain pending transactional notifications from the SPACS outbox"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=100,
            help="Maximum number of notifications to deliver in this run",
        )

    def handle(self, *args, **options):
        limit = options.get("limit", 100)
        report = notifications.deliver_pending(limit=limit)
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully processed outbox notifications: {report}"
            )
        )
