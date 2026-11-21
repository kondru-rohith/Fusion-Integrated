"""Transactional notification delivery and outbox management (BR-SPACS-008)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.utils import timezone

from modules.directory import contracts as directory
from modules.spacs.models import NotificationOutbox

log = logging.getLogger("fusion.spacs.notify")

TOPICS = {
    "application.submitted",
    "application.correction_required",
    "application.resubmitted",
    "application.verified",
    "application.approved",
    "application.rejected",
    "application.withdrawn",
    "renewal.reminder",
    "renewal.submitted",
    "renewal.approved",
    "renewal.rejected",
    "sla.escalation",
    "award.published",
}


def enqueue(
    *,
    topic: str,
    dedupe_key: str,
    subject: str,
    body: str,
    recipient_user_id: int | None = None,
    recipient_email: str = "",
    payload: dict | None = None,
) -> NotificationOutbox | None:
    """Queue one notification inside the caller's transaction. Returns None if already queued."""
    if topic not in TOPICS:
        raise ValueError(f"Unknown notification topic {topic!r}.")
    if recipient_user_id is None and not recipient_email:
        raise ValueError("A notification needs a recipient.")

    try:
        with transaction.atomic():
            return NotificationOutbox.objects.create(
                topic=topic,
                dedupe_key=dedupe_key,
                recipient_user_id=recipient_user_id,
                recipient_email=recipient_email,
                subject=subject,
                body=body,
                payload=payload or {},
            )
    except IntegrityError:
        log.debug("spacs.notify.duplicate key=%s", dedupe_key)
        return None


@dataclass
class DeliveryReport:
    sent: int = 0
    failed: int = 0
    skipped_capped: int = 0
    deferred: int = 0

    def __str__(self) -> str:
        return (
            f"sent={self.sent} failed={self.failed} "
            f"capped={self.skipped_capped} deferred={self.deferred}"
        )


def _backoff_ready(row: NotificationOutbox, now) -> bool:
    if row.attempts == 0:
        return True
    wait = timedelta(minutes=2 ** (row.attempts - 1))
    return (now - row.updated_at) >= wait


def _sent_today(recipient_user_id: int | None, now) -> int:
    if recipient_user_id is None:
        return 0
    since = now - timedelta(hours=24)
    return NotificationOutbox.objects.filter(
        recipient_user_id=recipient_user_id, status="sent", sent_at__gte=since
    ).count()


CLAIM_TIMEOUT = timedelta(minutes=10)


def _reclaim_stranded(now) -> int:
    return NotificationOutbox.objects.filter(
        status="sending", claimed_at__lt=now - CLAIM_TIMEOUT
    ).update(status="pending", claimed_at=None)


def _claim(row: NotificationOutbox) -> bool:
    return (
        NotificationOutbox.objects.filter(pk=row.pk, status="pending").update(
            status="sending", claimed_at=timezone.now()
        )
        == 1
    )


def deliver_pending(*, limit: int | None = None, now=None) -> DeliveryReport:
    """Drain pending notifications safely across concurrent workers."""
    now = now or timezone.now()
    _reclaim_stranded(now)
    limit = limit or getattr(settings, "NOTIFY_MAX_PER_RUN", 500)
    max_attempts = getattr(settings, "NOTIFY_MAX_ATTEMPTS", 5)
    daily_cap = getattr(settings, "NOTIFY_DAILY_CAP_PER_RECIPIENT", 20)
    report = DeliveryReport()

    queue = list(NotificationOutbox.objects.filter(status="pending").order_by("created_at")[:limit])
    if not queue:
        return report

    # Bulk lookup recipients
    user_ids = {r.recipient_user_id for r in queue if r.recipient_user_id is not None}
    users = directory.get_users(list(user_ids)) if user_ids else {}

    for row in queue:
        if not _backoff_ready(row, now):
            report.deferred += 1
            continue

        email = row.recipient_email
        if not email and row.recipient_user_id in users:
            email = users[row.recipient_user_id].email

        if not email:
            row.status = "failed"
            row.last_error = "Recipient email could not be resolved."
            row.save(update_fields=["status", "last_error", "updated_at"])
            report.failed += 1
            continue

        if _sent_today(row.recipient_user_id, now) >= daily_cap:
            row.status = "suppressed"
            row.last_error = "Daily notification cap reached."
            row.save(update_fields=["status", "last_error", "updated_at"])
            report.skipped_capped += 1
            continue

        if not _claim(row):
            continue

        try:
            from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "spacs@iiitdmj.ac.in")
            send_mail(row.subject, row.body, from_email, [email], fail_silently=False)
            row.status = "sent"
            row.sent_at = timezone.now()
            row.save(update_fields=["status", "sent_at", "updated_at"])
            report.sent += 1
        except (OSError, RuntimeError, ValueError) as exc:
            row.attempts += 1
            row.last_error = str(exc)[:300]
            row.status = "failed" if row.attempts >= max_attempts else "pending"
            row.claimed_at = None
            row.save(update_fields=["status", "attempts", "last_error", "claimed_at", "updated_at"])
            report.failed += 1

    return report
