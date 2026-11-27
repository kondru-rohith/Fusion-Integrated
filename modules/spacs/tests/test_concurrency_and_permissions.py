"""Concurrency and permission verification tests (R1-09, R1-10).

Covers:
- R1-09: User without spacs.application.review receives HTTP 403 on VerificationFindingCreateView
- R1-10: Threading barrier concurrency tests for race condition and duplicate prevention
"""

from __future__ import annotations

import threading
from decimal import Decimal

import pytest
from django.db import connection
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.spacs.models import (
    CatalogueEntry,
    CatalogueVersion,
    NotificationOutbox,
    ScholarshipApplication,
)
from modules.spacs.services import notifications

pytestmark = pytest.mark.django_db(transaction=True)


def _client(stub_iam, uid: int, perms: tuple[str, ...], roles: tuple[str, ...] = ("student",), kind: str = "student"):
    stub_iam(
        make_session(
            user_id=uid,
            kind=kind,
            modules=("spacs",),
            permissions=perms,
            roles=roles,
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Token token_{uid}")
    return c


@pytest.fixture()
def scholarship_version():
    today = timezone.now().date()
    entry = CatalogueEntry.objects.create(
        code="conc-scholarship",
        title="Concurrency Scholarship",
        kind="scholarship",
        status="active",
        allow_multiple_applications=False,
    )
    return CatalogueVersion.objects.create(
        entry=entry,
        version_number=1,
        academic_year="2026-27",
        policy_reference="REF/CONC/01",
        valid_from=today,
        valid_to=today + timezone.timedelta(days=365),
        application_window_start=timezone.now() - timezone.timedelta(days=5),
        application_window_end=timezone.now() + timezone.timedelta(days=25),
        status="published",
    )


# ---------------------------------------------------------------------------
# R1-09: Permission Tests for VerificationFindingCreateView
# ---------------------------------------------------------------------------

def test_user_without_p_app_review_receives_403_on_verification_finding(stub_iam, scholarship_version):
    """User without spacs.application.review permission gets HTTP 403 on VerificationFindingCreateView (R1-09)."""
    # Create application in under_verification
    app = ScholarshipApplication.objects.create(
        user_id=5001,
        application_number="SPACS-PERM-01",
        catalogue_entry=scholarship_version.entry,
        catalogue_version=scholarship_version,
        academic_year="2026-27",
        cycle="2026-27",
        status="under_verification",
        annual_income_declared=Decimal("300000"),
        cpi_at_apply=Decimal("8.0"),
    )

    # 1. Student without review permission -> 403 Forbidden
    student_client = _client(
        stub_iam, uid=5001, perms=("spacs.application.view_self",), roles=("student",)
    )
    res = student_client.post(
        f"/api/v1/spacs/verification/{app.pk}/finding/",
        {"action": "verified", "comments": "Self verification attempt"},
        format="json",
    )
    assert res.status_code == 403

    # 2. Staff user with unrelated permission (e.g., only catalogue.view) -> 403 Forbidden
    unauthorized_staff = _client(
        stub_iam, uid=5002, perms=("spacs.catalogue.view",), roles=("staff",), kind="staff"
    )
    res2 = unauthorized_staff.post(
        f"/api/v1/spacs/verification/{app.pk}/finding/",
        {"action": "verified", "comments": "Staff without review permission"},
        format="json",
    )
    assert res2.status_code == 403

    # 3. Authorized assistant WITH spacs.application.review -> 200 OK
    authorized_assistant = _client(
        stub_iam, uid=5003, perms=("spacs.application.review",), roles=("spacs_assistant",), kind="staff"
    )
    res3 = authorized_assistant.post(
        f"/api/v1/spacs/verification/{app.pk}/finding/",
        {"action": "verified", "comments": "Authorized verification finding"},
        format="json",
    )
    assert res3.status_code in (200, 201)


# ---------------------------------------------------------------------------
# R2-01: View-Layer Permission Tests for Decision Approval Endpoints
# ---------------------------------------------------------------------------

def test_user_without_p_app_approve_receives_403_on_decision_views(stub_iam, scholarship_version):
    """User without spacs.application.approve receives HTTP 403 on DecisionQueueView and DecisionOutcomeCreateView (R2-01)."""
    app = ScholarshipApplication.objects.create(
        user_id=5004,
        application_number="SPACS-PERM-DEC-01",
        catalogue_entry=scholarship_version.entry,
        catalogue_version=scholarship_version,
        academic_year="2026-27",
        cycle="2026-27",
        status="verified",
        annual_income_declared=Decimal("300000"),
        cpi_at_apply=Decimal("8.0"),
    )

    # 1. Student without approval permission -> 403 on decision queue
    student_client = _client(
        stub_iam, uid=5004, perms=("spacs.application.view_self",), roles=("student",)
    )
    res_queue = student_client.get("/api/v1/spacs/decisions/queue/")
    assert res_queue.status_code == 403, "Student without P_APP_APPROVE must be denied with 403"

    # 2. Student without approval permission -> 403 on decision outcome POST
    res_post = student_client.post(
        f"/api/v1/spacs/decisions/{app.pk}/outcome/",
        {"decision": "approved", "sanction_order_ref": "SANCTION/001"},
        format="json",
    )
    assert res_post.status_code == 403, "Student without P_APP_APPROVE must be denied with 403"

    # 3. Assistant with review permission but NO approval permission -> 403
    assistant_client = _client(
        stub_iam, uid=5005, perms=("spacs.application.review",), roles=("spacs_assistant",), kind="staff"
    )
    res_queue2 = assistant_client.get("/api/v1/spacs/decisions/queue/")
    assert res_queue2.status_code == 403, "Assistant without P_APP_APPROVE must be denied with 403"

    res_post2 = assistant_client.post(
        f"/api/v1/spacs/decisions/{app.pk}/outcome/",
        {"decision": "approved", "sanction_order_ref": "SANCTION/002"},
        format="json",
    )
    assert res_post2.status_code == 403, "Assistant without P_APP_APPROVE must be denied with 403"

    # 4. Convener WITH spacs.application.approve -> 200 OK
    convener_client = _client(
        stub_iam, uid=5006, perms=("spacs.application.approve",), roles=("spacs_convener",), kind="staff"
    )
    res_queue3 = convener_client.get("/api/v1/spacs/decisions/queue/")
    assert res_queue3.status_code == 200
    assert len(res_queue3.json()) >= 1


def test_decision_views_permission_classes_mutation_resistance():
    """Mutation probe test: verifies views declare HasPermission(P_APP_APPROVE) directly (R2-01)."""
    from modules.spacs.api.permissions import P_APP_APPROVE
    from modules.spacs.api.views import DecisionOutcomeCreateView, DecisionQueueView

    def has_approve_perm(view_cls):
        for perm in getattr(view_cls, "permission_classes", []):
            codes = getattr(perm, "codes", ())
            if P_APP_APPROVE in codes:
                return True
        return False

    assert has_approve_perm(DecisionQueueView), (
        "DecisionQueueView must declare HasPermission(P_APP_APPROVE) in permission_classes"
    )
    assert has_approve_perm(DecisionOutcomeCreateView), (
        "DecisionOutcomeCreateView must declare HasPermission(P_APP_APPROVE) in permission_classes"
    )


# ---------------------------------------------------------------------------
# R2-09: Unauthenticated (401) and Missing Module Grant (403) Tests
# ---------------------------------------------------------------------------

def test_unauthenticated_request_receives_401():
    """Unauthenticated HTTP request to SPACS endpoint returns HTTP 401 (R2-09)."""
    client = APIClient()
    res = client.get("/api/v1/spacs/catalogue/")
    assert res.status_code == 401, f"Expected 401 for unauthenticated request, got {res.status_code}"


def test_user_without_spacs_module_grant_receives_403(stub_iam):
    """Authenticated user without 'spacs' module grant returns HTTP 403 (R2-09)."""
    # User only has placement module grant, not spacs
    stub_iam(
        make_session(
            user_id=5099,
            kind="student",
            modules=("placement",),
            permissions=("placement.application.view",),
            roles=("student",),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token token_no_spacs")

    res = client.get("/api/v1/spacs/catalogue/")
    assert res.status_code == 403, (
        f"Expected 403 for user missing spacs module grant, got {res.status_code}"
    )



# ---------------------------------------------------------------------------
# R1-10: Concurrency Synchronization with threading.Barrier
# ---------------------------------------------------------------------------

def test_concurrent_notification_enqueue_prevents_duplicate():
    """Two concurrent threads enqueueing same dedupe_key: exactly one succeeds (R1-10)."""
    barrier = threading.Barrier(2)
    results = []
    errors = []
    dedupe_key = f"concurrent.test:{timezone.now().timestamp()}"

    def worker(worker_id):
        try:
            connection.close()
            barrier.wait(timeout=5)
            row = notifications.enqueue(
                topic="application.submitted",
                dedupe_key=dedupe_key,
                subject=f"Submission from worker {worker_id}",
                body="Body",
                recipient_user_id=7001,
            )
            results.append(row is not None)
        except (RuntimeError, OSError) as exc:
            errors.append(exc)
        finally:
            connection.close()

    t1 = threading.Thread(target=worker, args=(1,))
    t2 = threading.Thread(target=worker, args=(2,))
    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)

    assert not errors, f"Thread errors: {errors}"
    assert len(results) == 2
    # Exactly one succeeded (True) and one failed due to dedupe_key uniqueness (False)
    assert results.count(True) == 1
    assert results.count(False) == 1

    # Verify only 1 row exists in DB
    rows = NotificationOutbox.objects.filter(dedupe_key=dedupe_key).count()
    assert rows == 1


def test_concurrent_notification_claiming_prevents_double_send():
    """Two concurrent workers attempting to claim the same pending notification (R1-10)."""
    row = NotificationOutbox.objects.create(
        topic="application.verified",
        dedupe_key=f"claim.test:{timezone.now().timestamp()}",
        subject="Claim Test",
        body="Body",
        recipient_user_id=7002,
        status="pending",
    )

    barrier = threading.Barrier(2)
    claim_results = []
    errors = []

    def worker():
        try:
            connection.close()
            barrier.wait(timeout=5)
            claimed = notifications._claim(row)
            claim_results.append(claimed)
        except (RuntimeError, OSError) as exc:
            errors.append(exc)
        finally:
            connection.close()

    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=worker)
    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)

    assert not errors, f"Thread errors: {errors}"
    assert len(claim_results) == 2
    # Exactly one worker successfully claimed the row
    assert claim_results.count(True) == 1
    assert claim_results.count(False) == 1
