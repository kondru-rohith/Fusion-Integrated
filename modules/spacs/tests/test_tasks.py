"""Tests for scheduled tasks, Celery wrappers, management commands (R1-10, R1-17).

Covers:
- services/tasks.py: check_review_slas, send_renewal_reminders, reassign_pending_tasks
- tasks.py: Celery wrapper tasks
- management commands: spacs_check_slas, spacs_send_renewal_reminders, spacs_deliver_notifications

UC-SPACS-024 (SLA monitoring), UC-SPACS-025 (renewal reminders), UC-SPACS-026 (task reassignment)
BR-SPACS-013 (SLA threshold), BR-SPACS-017 (renewal window), BR-SPACS-022 (task reassignment)
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

import pytest
from django.utils import timezone

from modules.spacs.models import (
    CatalogueEntry,
    CatalogueVersion,
    ScholarshipApplication,
)
from modules.spacs.services import tasks as task_svc

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def catalogue_entry():
    return CatalogueEntry.objects.create(
        code="mcm-tasks-test",
        title="MCM Scholarship (Tasks Test)",
        kind="scholarship",
        status="active",
    )


@pytest.fixture()
def catalogue_version(catalogue_entry):
    today = timezone.now().date()
    return CatalogueVersion.objects.create(
        entry=catalogue_entry,
        version_number=1,
        academic_year="2026-27",
        policy_reference="REF/TASK/01",
        valid_from=today,
        valid_to=today + datetime.timedelta(days=365),
        application_window_start=timezone.now() - datetime.timedelta(days=30),
        application_window_end=timezone.now() + datetime.timedelta(days=30),
        sla_threshold_days=7,
        status="published",
    )


@pytest.fixture()
def renewable_version(catalogue_entry):
    now = timezone.now()
    today = now.date()
    return CatalogueVersion.objects.create(
        entry=catalogue_entry,
        version_number=2,
        academic_year="2026-27",
        policy_reference="REF/TASK/02",
        valid_from=today,
        valid_to=today + datetime.timedelta(days=365),
        is_renewable=True,
        renewal_window_start=now - datetime.timedelta(days=3),
        renewal_window_end=now + datetime.timedelta(days=4),  # within 7-day reminder window
        sla_threshold_days=7,
        status="published",
    )


@pytest.fixture()
def submitted_app(catalogue_version):
    """Application submitted more than 7 days ago — overdue for SLA."""
    old_time = timezone.now() - datetime.timedelta(days=10)
    app = ScholarshipApplication.objects.create(
        user_id=2001,
        application_number="SPACS-TEST-SLA-001",
        catalogue_entry=catalogue_version.entry,
        catalogue_version=catalogue_version,
        academic_year="2026-27",
        cycle="2026-27",
        status="submitted",
        annual_income_declared=Decimal("400000"),
        cpi_at_apply=Decimal("8.0"),
    )
    # Backdate submitted_at
    ScholarshipApplication.objects.filter(pk=app.pk).update(submitted_at=old_time, created_at=old_time)
    return app


@pytest.fixture()
def fresh_submitted_app(catalogue_version):
    """Application submitted today — not overdue."""
    return ScholarshipApplication.objects.create(
        user_id=2002,
        application_number="SPACS-TEST-SLA-002",
        catalogue_entry=catalogue_version.entry,
        catalogue_version=catalogue_version,
        academic_year="2026-27",
        cycle="2026-27",
        status="submitted",
        annual_income_declared=Decimal("400000"),
        cpi_at_apply=Decimal("8.0"),
        submitted_at=timezone.now(),
    )


@pytest.fixture()
def approved_renewable_app(renewable_version):
    """Approved application eligible for renewal with window open."""
    return ScholarshipApplication.objects.create(
        user_id=2003,
        application_number="SPACS-TEST-REN-001",
        catalogue_entry=renewable_version.entry,
        catalogue_version=renewable_version,
        academic_year="2026-27",
        cycle="2026-27",
        status="approved",
        annual_income_declared=Decimal("400000"),
        cpi_at_apply=Decimal("8.5"),
    )


# ---------------------------------------------------------------------------
# check_review_slas tests (UC-SPACS-024, BR-SPACS-013)
# ---------------------------------------------------------------------------

class TestCheckReviewSlas:

    def test_no_pending_apps_returns_zero(self):
        """Zero escalations when no pending applications exist (UC-SPACS-024)."""
        result = task_svc.check_review_slas()
        assert result == 0

    def test_overdue_app_queues_escalation(self, submitted_app):
        """Overdue application generates SLA escalation notification (UC-SPACS-024, BR-SPACS-013)."""
        with patch("modules.spacs.services.notifications.enqueue") as mock_enqueue:
            mock_enqueue.return_value = True  # simulate enqueue success
            result = task_svc.check_review_slas()
        assert result == 1
        assert mock_enqueue.called
        call_kwargs = mock_enqueue.call_args.kwargs
        assert call_kwargs["topic"] == "sla.escalation"
        assert submitted_app.application_number in call_kwargs["subject"]

    def test_fresh_app_does_not_escalate(self, fresh_submitted_app):
        """Application submitted today is not overdue — no escalation (UC-SPACS-024)."""
        with patch("modules.spacs.services.notifications.enqueue") as mock_enqueue:
            mock_enqueue.return_value = True
            result = task_svc.check_review_slas()
        assert result == 0
        assert not mock_enqueue.called

    def test_duplicate_escalation_prevented(self, submitted_app):
        """Running check_review_slas twice with same date deduplicates (UC-SPACS-024)."""
        from modules.spacs.services import notifications
        # First call actually queues
        notifications.enqueue(
            topic="sla.escalation",
            dedupe_key=f"sla.escalation:{submitted_app.pk}:{timezone.now().date().isoformat()}",
            subject="SLA test",
            body="Test body",
            recipient_user_id=9,
        )
        # Second call should return 0 (dedupe_key already exists)
        result = task_svc.check_review_slas()
        assert result == 0

    def test_explicit_now_parameter(self, submitted_app):
        """check_review_slas accepts explicit now for deterministic testing (UC-SPACS-024)."""
        past_now = timezone.now() - datetime.timedelta(days=1)
        with patch("modules.spacs.services.notifications.enqueue") as mock_enqueue:
            mock_enqueue.return_value = True
            result = task_svc.check_review_slas(now=past_now)
        # submitted_app is overdue even one day ago
        assert result == 1


# ---------------------------------------------------------------------------
# send_renewal_reminders tests (UC-SPACS-025, BR-SPACS-017)
# ---------------------------------------------------------------------------

class TestSendRenewalReminders:

    def test_no_approved_apps_returns_zero(self):
        """Zero reminders when no approved renewable applications (UC-SPACS-025)."""
        result = task_svc.send_renewal_reminders()
        assert result == 0

    def test_app_in_renewal_window_queues_reminder(self, approved_renewable_app):
        """Approved app in 7-day renewal window gets reminder (UC-SPACS-025, BR-SPACS-017)."""
        with patch("modules.spacs.services.notifications.enqueue") as mock_enqueue:
            mock_enqueue.return_value = True
            result = task_svc.send_renewal_reminders()
        assert result == 1
        assert mock_enqueue.called
        call_kwargs = mock_enqueue.call_args.kwargs
        assert call_kwargs["topic"] == "renewal.reminder"
        assert call_kwargs["recipient_user_id"] == approved_renewable_app.user_id

    def test_app_outside_renewal_window_no_reminder(self, catalogue_entry):
        """Approved app with renewal window far in future does not trigger reminder (UC-SPACS-025)."""
        today = timezone.now().date()
        far_version = CatalogueVersion.objects.create(
            entry=catalogue_entry,
            version_number=3,
            academic_year="2027-28",
            policy_reference="REF/FAR/01",
            valid_from=today,
            valid_to=today + datetime.timedelta(days=365),
            is_renewable=True,
            renewal_window_start=timezone.now() + datetime.timedelta(days=60),
            renewal_window_end=timezone.now() + datetime.timedelta(days=90),
            sla_threshold_days=7,
            status="published",
        )
        ScholarshipApplication.objects.create(
            user_id=2004,
            application_number="SPACS-TEST-FAR-001",
            catalogue_entry=catalogue_entry,
            catalogue_version=far_version,
            academic_year="2027-28",
            cycle="2027-28",
            status="approved",
            annual_income_declared=Decimal("400000"),
            cpi_at_apply=Decimal("8.0"),
        )
        with patch("modules.spacs.services.notifications.enqueue") as mock_enqueue:
            mock_enqueue.return_value = True
            result = task_svc.send_renewal_reminders()
        assert result == 0

    def test_non_renewable_scheme_skipped(self, catalogue_entry):
        """Non-renewable scheme approved app never gets renewal reminder (UC-SPACS-025)."""
        today = timezone.now().date()
        non_ren_version = CatalogueVersion.objects.create(
            entry=catalogue_entry,
            version_number=4,
            academic_year="2026-27",
            policy_reference="REF/NR/01",
            valid_from=today,
            valid_to=today + datetime.timedelta(days=365),
            is_renewable=False,
            status="published",
        )
        ScholarshipApplication.objects.create(
            user_id=2005,
            application_number="SPACS-TEST-NR-001",
            catalogue_entry=catalogue_entry,
            catalogue_version=non_ren_version,
            academic_year="2026-27",
            cycle="2026-27",
            status="approved",
            annual_income_declared=Decimal("400000"),
            cpi_at_apply=Decimal("8.0"),
        )
        result = task_svc.send_renewal_reminders()
        assert result == 0

    def test_duplicate_reminder_prevented(self, approved_renewable_app):
        """Running twice deduplicates by dedupe_key (UC-SPACS-025)."""
        from modules.spacs.services import notifications
        v = approved_renewable_app.catalogue_version
        notifications.enqueue(
            topic="renewal.reminder",
            dedupe_key=f"renewal.reminder:{approved_renewable_app.pk}:{v.academic_year}",
            subject="Renewal reminder",
            body="Test body",
            recipient_user_id=approved_renewable_app.user_id,
        )
        result = task_svc.send_renewal_reminders()
        assert result == 0


# ---------------------------------------------------------------------------
# reassign_pending_tasks tests (UC-SPACS-026, BR-SPACS-022)
# ---------------------------------------------------------------------------

class TestReassignPendingTasks:

    def test_reassign_spacs_assistant_role(self, catalogue_version):
        """Reassigns pending applications from old assistant to new one (UC-SPACS-026)."""
        app = ScholarshipApplication.objects.create(
            user_id=2006,
            application_number="SPACS-TEST-RA-001",
            catalogue_entry=catalogue_version.entry,
            catalogue_version=catalogue_version,
            academic_year="2026-27",
            cycle="2026-27",
            status="submitted",
            assigned_assistant_id=100,
            annual_income_declared=Decimal("400000"),
            cpi_at_apply=Decimal("8.0"),
        )
        result = task_svc.reassign_pending_tasks("spacs_assistant", 100, 200)
        assert result == 1
        app.refresh_from_db()
        assert app.assigned_assistant_id == 200

    def test_reassign_non_spacs_role_returns_zero(self):
        """Unrecognised role code returns 0 without error (UC-SPACS-026)."""
        result = task_svc.reassign_pending_tasks("other_role", 100, 200)
        assert result == 0

    def test_reassign_does_not_touch_terminal_applications(self, catalogue_version):
        """Approved/rejected apps are not reassigned (UC-SPACS-026, BR-SPACS-022)."""
        app = ScholarshipApplication.objects.create(
            user_id=2007,
            application_number="SPACS-TEST-RA-002",
            catalogue_entry=catalogue_version.entry,
            catalogue_version=catalogue_version,
            academic_year="2026-27",
            cycle="2026-27",
            status="approved",
            assigned_assistant_id=100,
            annual_income_declared=Decimal("400000"),
            cpi_at_apply=Decimal("8.0"),
        )
        result = task_svc.reassign_pending_tasks("spacs_assistant", 100, 200)
        assert result == 0
        app.refresh_from_db()
        assert app.assigned_assistant_id == 100  # unchanged


# ---------------------------------------------------------------------------
# Celery task wrapper tests (tasks.py)
# ---------------------------------------------------------------------------

class TestCeleryTaskWrappers:

    def test_deliver_notifications_celery_task(self):
        """deliver_notifications() calls notifications.deliver_pending() and returns str."""
        from modules.spacs import tasks as celery_tasks
        with patch("modules.spacs.services.notifications.deliver_pending") as mock_deliver:
            mock_deliver.return_value = type("R", (), {"__str__": lambda s: "sent=0 failed=0 capped=0 deferred=0"})()
            result = celery_tasks.deliver_notifications()
        assert isinstance(result, str)
        mock_deliver.assert_called_once()

    def test_check_review_slas_celery_task(self):
        """check_review_slas() celery task returns 'escalated=N' string (UC-SPACS-024)."""
        from modules.spacs import tasks as celery_tasks
        with patch("modules.spacs.services.tasks.check_review_slas") as mock_check:
            mock_check.return_value = 3
            result = celery_tasks.check_review_slas()
        assert result == "escalated=3"
        mock_check.assert_called_once()

    def test_send_renewal_reminders_celery_task(self):
        """send_renewal_reminders() celery task returns 'reminded=N' string (UC-SPACS-025)."""
        from modules.spacs import tasks as celery_tasks
        with patch("modules.spacs.services.tasks.send_renewal_reminders") as mock_remind:
            mock_remind.return_value = 5
            result = celery_tasks.send_renewal_reminders()
        assert result == "reminded=5"
        mock_remind.assert_called_once()


# ---------------------------------------------------------------------------
# Management command tests (R1-17)
# ---------------------------------------------------------------------------

class TestManagementCommands:

    def test_spacs_check_slas_command_runs(self):
        """spacs_check_slas management command executes without error (R1-17, UC-SPACS-024)."""
        from django.core.management import call_command
        with patch("modules.spacs.services.tasks.check_review_slas") as mock_check:
            mock_check.return_value = 0
            out = StringIO()
            call_command("spacs_check_slas", stdout=out)
        output = out.getvalue()
        assert "escalated" in output.lower() or "0" in output

    def test_spacs_send_renewal_reminders_command_runs(self):
        """spacs_send_renewal_reminders management command executes (R1-17, UC-SPACS-025)."""
        from django.core.management import call_command
        with patch("modules.spacs.services.tasks.send_renewal_reminders") as mock_remind:
            mock_remind.return_value = 0
            out = StringIO()
            call_command("spacs_send_renewal_reminders", stdout=out)
        output = out.getvalue()
        assert "reminded" in output.lower() or "0" in output

    def test_spacs_deliver_notifications_command_runs(self):
        """spacs_deliver_notifications management command executes (R1-17)."""
        from django.core.management import call_command
        with patch("modules.spacs.services.notifications.deliver_pending") as mock_deliver:
            mock_deliver.return_value = type("R", (), {"__str__": lambda s: "sent=0 failed=0 capped=0 deferred=0"})()
            out = StringIO()
            call_command("spacs_deliver_notifications", stdout=out)
        output = out.getvalue()
        assert "sent" in output.lower() or "0" in output

    def test_spacs_check_slas_dry_run(self):
        """spacs_check_slas --dry-run runs without sending notifications (R1-17)."""
        from django.core.management import call_command
        out = StringIO()
        call_command("spacs_check_slas", dry_run=True, stdout=out)
        output = out.getvalue()
        assert "dry" in output.lower() or "0" in output or "escalated" in output.lower()
