"""Celery tasks for SPACS."""

from __future__ import annotations

from celery import shared_task

from modules.spacs.services import notifications, tasks


@shared_task(name="spacs.deliver_notifications")
def deliver_notifications():
    """Drain outbox notifications."""
    report = notifications.deliver_pending()
    return str(report)


@shared_task(name="spacs.check_review_slas")
def check_review_slas():
    """Review SLA reminder and escalation sweep (UC-SPACS-024)."""
    count = tasks.check_review_slas()
    return f"escalated={count}"


@shared_task(name="spacs.send_renewal_reminders")
def send_renewal_reminders():
    """Scholarship renewal reminder sweep (UC-SPACS-025)."""
    count = tasks.send_renewal_reminders()
    return f"reminded={count}"
