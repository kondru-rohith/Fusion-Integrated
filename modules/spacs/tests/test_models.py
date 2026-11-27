"""Model tests: database constraints, relationships, and audit immutability."""

import pytest
from django.db import IntegrityError
from django.utils import timezone

from modules.spacs.models import (
    ApplicationTransition,
    CatalogueEntry,
    CatalogueVersion,
    ScholarshipApplication,
    SpacsAuditLog,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def catalogue_version():
    today = timezone.now().date()
    entry = CatalogueEntry.objects.create(
        code="director-silver-medal",
        title="Director Silver Medal",
        kind="award",
        status="active",
    )
    return CatalogueVersion.objects.create(
        entry=entry,
        version_number=1,
        academic_year="2026-27",
        policy_reference="REF/2026/DSM/01",
        valid_from=today,
        valid_to=today + timezone.timedelta(days=365),
        application_window_start=timezone.now(),
        application_window_end=timezone.now() + timezone.timedelta(days=30),
        status="published",
    )


def test_catalogue_version_unique_constraint(catalogue_version):
    """Cannot have duplicate version numbers for the same catalogue entry."""
    today = timezone.now().date()
    with pytest.raises(IntegrityError):
        CatalogueVersion.objects.create(
            entry=catalogue_version.entry,
            version_number=1,
            academic_year="2026-27",
            policy_reference="REF/DUP",
            valid_from=today,
            valid_to=today + timezone.timedelta(days=365),
            status="draft",
        )


def test_prevent_duplicate_active_applications(catalogue_version):
    """Students cannot submit duplicate active applications for same cycle (BR-SPACS-002)."""
    ScholarshipApplication.objects.create(
        user_id=101,
        catalogue_entry=catalogue_version.entry,
        catalogue_version=catalogue_version,
        cycle="2026-27",
        application_number="SPACS-2026-00001",
        status="submitted",
    )

    with pytest.raises(IntegrityError):
        ScholarshipApplication.objects.create(
            user_id=101,
            catalogue_entry=catalogue_version.entry,
            catalogue_version=catalogue_version,
            cycle="2026-27",
            application_number="SPACS-2026-00002",
            status="submitted",
        )


def test_allow_reapplication_after_rejection(catalogue_version):
    """Terminal states (rejected/withdrawn) do not block re-applying in future cycles."""
    ScholarshipApplication.objects.create(
        user_id=102,
        catalogue_entry=catalogue_version.entry,
        catalogue_version=catalogue_version,
        cycle="2025-26",
        application_number="SPACS-2025-00001",
        status="rejected",
    )

    # Allowed in a new cycle
    app2 = ScholarshipApplication.objects.create(
        user_id=102,
        catalogue_entry=catalogue_version.entry,
        catalogue_version=catalogue_version,
        cycle="2026-27",
        application_number="SPACS-2026-00003",
        status="submitted",
    )
    assert app2.pk is not None


def test_audit_log_immutability():
    """Audit log rows and application transitions cannot be modified or deleted (BR-SPACS-012)."""
    log = SpacsAuditLog.objects.create(
        actor_id=9,
        actor_role="spacs_convener",
        action="award.cycle_opened",
        target_type="AwardCycle",
        target_id=1,
        details={"status": "opened"},
    )

    # Cannot update existing log
    log.action = "tampered"
    with pytest.raises(RuntimeError, match="append-only"):
        log.save()

    # Cannot delete existing log
    with pytest.raises(RuntimeError, match="cannot be deleted"):
        log.delete()

    # Bulk update and delete via QuerySet are blocked
    with pytest.raises(RuntimeError, match="append-only"):
        SpacsAuditLog.objects.filter(pk=log.pk).update(action="tampered")

    with pytest.raises(RuntimeError, match="cannot be deleted"):
        SpacsAuditLog.objects.filter(pk=log.pk).delete()


def test_transition_log_immutability(catalogue_version):
    """Application transitions are strictly append-only."""
    app = ScholarshipApplication.objects.create(
        user_id=103,
        catalogue_entry=catalogue_version.entry,
        catalogue_version=catalogue_version,
        cycle="2026-27",
        application_number="SPACS-2026-00004",
        status="draft",
    )
    transition = ApplicationTransition.objects.create(
        application=app,
        from_status="none",
        to_status="draft",
        actor_user_id=103,
        actor_label="Student",
        reason="Created draft",
    )

    with pytest.raises(RuntimeError, match="append-only"):
        transition.reason = "Modified reason"
        transition.save()

    with pytest.raises(RuntimeError, match="cannot be deleted"):
        transition.delete()

    with pytest.raises(RuntimeError, match="append-only"):
        ApplicationTransition.objects.filter(pk=transition.pk).update(reason="Hacked")

    with pytest.raises(RuntimeError, match="cannot be deleted"):
        ApplicationTransition.objects.filter(pk=transition.pk).delete()
