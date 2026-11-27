"""Scheduled sweeps and event-triggered background services (UC-024, 025, 026, BR-013, 017, 022)."""

from __future__ import annotations

import logging
from datetime import timedelta

from django.utils import timezone

from modules.spacs.models import ScholarshipApplication
from modules.spacs.services import notifications

log = logging.getLogger("fusion.spacs.tasks")


def check_review_slas(now=None) -> int:
    """Issue SLA reminder and escalation notifications (UC-SPACS-024, BR-SPACS-013)."""
    now = now or timezone.now()
    pending_apps = ScholarshipApplication.objects.filter(
        status__in=["submitted", "under_verification", "verified", "verification_concern"]
    ).select_related("catalogue_version__entry")

    escalations_count = 0
    for app in pending_apps:
        sla_days = app.catalogue_version.sla_threshold_days
        threshold = now - timedelta(days=sla_days)

        # Check if overdue
        ref_time = app.resubmitted_at or app.submitted_at or app.created_at
        if ref_time and ref_time < threshold:
            recipient_id = app.assigned_assistant_id or 9  # Assistant or office default
            queued = notifications.enqueue(
                topic="sla.escalation",
                dedupe_key=f"sla.escalation:{app.pk}:{now.date().isoformat()}",
                subject=f"Review SLA Overdue: {app.application_number}",
                body=(
                    f"Application {app.application_number} ({app.status}) "
                    f"has been pending beyond {sla_days} days."
                ),
                recipient_user_id=recipient_id,
                payload={"application_id": app.pk, "status": app.status},
            )
            if queued:
                escalations_count += 1

    return escalations_count


def send_renewal_reminders(now=None) -> int:
    """Notify students eligible for scholarship renewal (UC-SPACS-025, BR-SPACS-017)."""
    now = now or timezone.now()
    renewable_apps = ScholarshipApplication.objects.filter(
        status="approved",
        catalogue_version__is_renewable=True,
    ).select_related("catalogue_version__entry")

    reminders_count = 0
    for app in renewable_apps:
        v = app.catalogue_version
        if (
            v.renewal_window_end
            and (v.renewal_window_end - timedelta(days=7)) <= now <= v.renewal_window_end
        ):
            queued = notifications.enqueue(
                topic="renewal.reminder",
                dedupe_key=f"renewal.reminder:{app.pk}:{v.academic_year}",
                subject=f"Scholarship Renewal Reminder: {v.entry.title}",
                body=(
                    f"The renewal window for {v.entry.title} ({v.academic_year}) "
                    f"closes on {v.renewal_window_end.strftime('%d %b %Y')}. "
                    "Submit your renewal application promptly."
                ),
                recipient_user_id=app.user_id,
            )
            if queued:
                reminders_count += 1

    return reminders_count


def reassign_pending_tasks(
    role_code: str,
    old_user_id: int,
    new_user_id: int,
) -> int:
    """Reassign pending tasks to new role holder (UC-SPACS-026, BR-SPACS-022)."""
    if role_code == "spacs_assistant":
        updated = ScholarshipApplication.objects.filter(
            assigned_assistant_id=old_user_id,
            status__in=["submitted", "under_verification", "resubmitted"],
        ).update(assigned_assistant_id=new_user_id)
        log.info(
            "spacs.tasks.reassigned assistant tasks from u%s to u%s (count=%s)",
            old_user_id,
            new_user_id,
            updated,
        )
        return updated
    return 0
