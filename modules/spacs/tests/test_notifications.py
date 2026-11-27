"""Tests for transactional notification outbox (delivery, backoff, and deduplication)."""

from datetime import timedelta

import pytest
from django.utils import timezone

from conftest import make_session
from fusion_auth.client import UserRef
from modules.spacs.models import NotificationOutbox
from modules.spacs.services import notifications

pytestmark = pytest.mark.django_db


def test_enqueue_and_deduplication():
    """Duplicate notification events with identical dedupe keys must be ignored (BR-SPACS-014)."""
    # 1. Enqueue first notification
    queued_1 = notifications.enqueue(
        topic="application.submitted",
        dedupe_key="app.submitted:1001:2026-27",
        subject="Application Submitted",
        body="Your application has been received.",
        recipient_user_id=1001,
    )
    assert queued_1 is not None
    assert NotificationOutbox.objects.count() == 1

    # 2. Enqueue duplicate notification
    queued_2 = notifications.enqueue(
        topic="application.submitted",
        dedupe_key="app.submitted:1001:2026-27",
        subject="Duplicate Application Submitted",
        body="Duplicate text",
        recipient_user_id=1001,
    )
    assert queued_2 is None
    assert NotificationOutbox.objects.count() == 1


def test_delivery_drains_pending_and_marks_sent(stub_iam, monkeypatch):
    """Deliver pending notifications to recipient emails."""
    user = UserRef(
        user_id=1001,
        username="u1001",
        display_name="Alice",
        kind="student",
        email="alice@iiitdmj.ac.in",
    )
    stub_iam(make_session(user_id=9), users={1001: user})

    notifications.enqueue(
        topic="application.submitted",
        dedupe_key="app.submitted:test",
        subject="Application Received",
        body="Hello Alice",
        recipient_user_id=1001,
    )

    sent_emails = []

    def mock_send_mail(subject, body, from_email, recipient_list, fail_silently=False):
        sent_emails.append((subject, body, recipient_list))

    monkeypatch.setattr("modules.spacs.services.notifications.send_mail", mock_send_mail)

    report = notifications.deliver_pending()
    assert report.sent == 1
    assert len(sent_emails) == 1
    assert sent_emails[0][2] == ["alice@iiitdmj.ac.in"]

    row = NotificationOutbox.objects.first()
    assert row.status == "sent"
    assert row.sent_at is not None


def test_exponential_backoff_on_failure(stub_iam, monkeypatch):
    """Failed delivery attempts record errors and back off exponentially."""
    user = UserRef(
        user_id=1001,
        username="u1001",
        display_name="Alice",
        kind="student",
        email="alice@iiitdmj.ac.in",
    )
    stub_iam(make_session(user_id=9), users={1001: user})

    notifications.enqueue(
        topic="application.submitted",
        dedupe_key="app.submitted:fail_test",
        subject="Fail Test",
        body="Body",
        recipient_user_id=1001,
    )

    def failing_send_mail(*args, **kwargs):
        raise OSError("SMTP connection timeout")

    monkeypatch.setattr("modules.spacs.services.notifications.send_mail", failing_send_mail)

    now = timezone.now()
    report = notifications.deliver_pending(now=now)
    assert report.failed == 1

    row = NotificationOutbox.objects.first()
    assert row.attempts == 1
    assert row.status == "pending"
    assert "SMTP connection timeout" in row.last_error

    # Immediate second delivery run should defer due to exponential backoff
    report2 = notifications.deliver_pending(now=now + timedelta(seconds=10))
    assert report2.deferred == 1
    assert report2.sent == 0


def test_daily_rate_limiting(stub_iam, monkeypatch):
    """Recipients are capped at daily maximum limit to prevent spam (BR-SPACS-014)."""
    user = UserRef(
        user_id=1001,
        username="u1001",
        display_name="Alice",
        kind="student",
        email="alice@iiitdmj.ac.in",
    )
    stub_iam(make_session(user_id=9), users={1001: user})

    now = timezone.now()
    # Create 20 already-sent records in past 24 hours
    for i in range(20):
        NotificationOutbox.objects.create(
            topic="application.submitted",
            dedupe_key=f"already.sent:{i}",
            subject=f"Notice {i}",
            body="Text",
            recipient_user_id=1001,
            recipient_email="alice@iiitdmj.ac.in",
            status="sent",
            sent_at=now - timedelta(hours=2),
        )

    # 21st notification should be suppressed
    notifications.enqueue(
        topic="application.submitted",
        dedupe_key="should.suppress",
        subject="Notice 21",
        body="Text",
        recipient_user_id=1001,
    )

    monkeypatch.setattr("modules.spacs.services.notifications.send_mail", lambda *args, **kw: None)
    report = notifications.deliver_pending(now=now)
    assert report.skipped_capped == 1

    row = NotificationOutbox.objects.get(dedupe_key="should.suppress")
    assert row.status == "suppressed"
