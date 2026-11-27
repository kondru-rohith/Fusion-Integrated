"""HTTP-level end-to-end journey tests for SPACS (R1-12).

Covers multi-role journeys:
- Student applies -> Assistant verifies -> Convener approves (BW-SPACS-01, BW-SPACS-03, UC-SPACS-001, 002, 006)
- Student applies -> Assistant requests correction -> Student edits & resubmits (BW-SPACS-02, UC-SPACS-003)
- Student withdraws submitted application (BW-SPACS-05, UC-SPACS-004)
- Award cycle lifecycle: Open -> Pool Prep -> Evaluation -> Publish (CW-SPACS-03, UC-SPACS-017..020)
- Scholarship renewal journey: Approved award -> Renewal application -> Approval (CW-SPACS-02, UC-SPACS-007, BR-SPACS-017)
"""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from fusion_auth.client import UserRef
from modules.spacs.models import (
    ApplicationDocument,
    AwardCycle,
    CatalogueEntry,
    CatalogueVersion,
    ScholarshipApplication,
)
from modules.spacs.registry import ROLE_GRANTS

pytestmark = pytest.mark.django_db


@pytest.fixture()
def scholarship_scheme():
    today = timezone.now().date()
    entry = CatalogueEntry.objects.create(
        code="e2e-mcm",
        title="E2E Merit Scholarship",
        kind="scholarship",
        status="active",
    )
    return CatalogueVersion.objects.create(
        entry=entry,
        version_number=1,
        academic_year="2026-27",
        policy_reference="REF/JOURNEY/MCM",
        valid_from=today,
        valid_to=today + datetime.timedelta(days=365),
        application_window_start=timezone.now() - datetime.timedelta(days=5),
        application_window_end=timezone.now() + datetime.timedelta(days=25),
        renewal_window_start=timezone.now() - datetime.timedelta(days=5),
        renewal_window_end=timezone.now() + datetime.timedelta(days=25),
        is_renewable=True,
        eligibility_criteria={
            "min_cpi": 7.0,
            "income_ceiling": 600000,
            "allowed_programmes": ["B.Tech"],
            "max_backlogs": 0,
        },
        required_documents=["income_certificate"],
        status="published",
    )


def test_journey_apply_verify_approve(stub_iam, scholarship_scheme):
    """Journey 1: Student submits, Assistant verifies, Convener approves (BW-SPACS-01, 03)."""
    student_user = UserRef(
        user_id=3001,
        username="u3001",
        display_name="Student 3001",
        kind="student",
        programme="B.Tech",
    )
    student_session = make_session(
        user_id=3001,
        kind="student",
        modules=("spacs",),
        permissions=ROLE_GRANTS["student"],
        roles=("student",),
    )
    assistant_session = make_session(
        user_id=3002,
        kind="staff",
        modules=("spacs",),
        permissions=ROLE_GRANTS["spacs_assistant"],
        roles=("spacs_assistant",),
    )
    convener_session = make_session(
        user_id=3003,
        kind="staff",
        modules=("spacs",),
        permissions=ROLE_GRANTS["spacs_convener"],
        roles=("spacs_convener",),
    )

    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token e2e_token")

    # 1. Student drafts and submits application
    fake = stub_iam(student_session, users={3001: student_user})
    fake.standings = {3001: {"cpi": 8.5, "active_backlogs": 0, "category": "GEN"}}

    res = c.post(
        "/api/v1/spacs/applications/",
        {
            "catalogue_version_id": scholarship_scheme.pk,
            "cycle": "2026-27",
            "submission_data": {"bank_account": "9876543210", "ifsc": "SBIN0001"},
            "annual_income_declared": 450000,
        },
        format="json",
    )
    assert res.status_code == 201
    app_id = res.json()["id"]

    # Attach document
    ApplicationDocument.objects.create(
        application_id=app_id,
        user_id=3001,
        doc_type="income_certificate",
        title="Income Certificate",
        original_filename="income.pdf",
        drive_url="https://drive.google.com/doc1",
        drive_file_id="drv-3001",
        verification_status="valid",
    )

    # Submit application
    sub_res = c.post(f"/api/v1/spacs/applications/{app_id}/submit/", format="json")
    assert sub_res.status_code == 200
    assert sub_res.json()["status"] == "submitted"

    # 2. Assistant reviews and verifies
    stub_iam(assistant_session)
    ver_res = c.post(
        f"/api/v1/spacs/verification/{app_id}/finding/",
        {"action": "verified", "comments": "Documents verified and clear"},
        format="json",
    )
    assert ver_res.status_code in (200, 201)

    app = ScholarshipApplication.objects.get(pk=app_id)
    assert app.status == "verified"

    # 3. Convener sanctions award
    stub_iam(convener_session)
    dec_res = c.post(
        f"/api/v1/spacs/decisions/{app_id}/outcome/",
        {
            "decision": "approved",
            "sanction_order_ref": "SANCTION/2026/E2E/01",
            "rationale": "Merit confirmed by committee",
        },
        format="json",
    )
    assert dec_res.status_code in (200, 201)
    app.refresh_from_db()
    assert app.status == "approved"


def test_journey_correction_and_resubmit(stub_iam, scholarship_scheme):
    """Journey 2: Student -> Correction Required -> Resubmit (BW-SPACS-02, UC-SPACS-003)."""
    student_session = make_session(
        user_id=3004,
        kind="student",
        modules=("spacs",),
        permissions=ROLE_GRANTS["student"],
        roles=("student",),
    )
    assistant_session = make_session(
        user_id=3005,
        kind="staff",
        modules=("spacs",),
        permissions=ROLE_GRANTS["spacs_assistant"],
        roles=("spacs_assistant",),
    )

    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token e2e_token")

    # 1. Application under verification
    app = ScholarshipApplication.objects.create(
        user_id=3004,
        application_number="SPACS-CORR-01",
        catalogue_entry=scholarship_scheme.entry,
        catalogue_version=scholarship_scheme,
        academic_year="2026-27",
        cycle="2026-27",
        status="under_verification",
        annual_income_declared=Decimal("400000"),
        cpi_at_apply=Decimal("8.0"),
    )
    ApplicationDocument.objects.create(
        application=app,
        user_id=3004,
        doc_type="income_certificate",
        title="Income Certificate",
        original_filename="income.pdf",
        drive_url="https://drive.google.com/doc1",
        drive_file_id="drv-3004",
        is_active=True,
        verification_status="resubmission_needed",
    )

    # 2. Assistant requests correction
    stub_iam(assistant_session)
    corr_res = c.post(
        f"/api/v1/spacs/verification/{app.pk}/finding/",
        {
            "action": "correction_required",
            "comments": "Income certificate blur, re-upload",
            "correction_fields": ["income_certificate"],
        },
        format="json",
    )
    assert corr_res.status_code in (200, 201)
    app.refresh_from_db()
    assert app.status == "correction_required"

    # 3. Student updates submission data and resubmits
    stub_iam(student_session)
    edit_res = c.put(
        f"/api/v1/spacs/applications/{app.pk}/",
        {"submission_data": {"bank_account": "11223344", "remark": "Updated document link"}},
        format="json",
    )
    assert edit_res.status_code == 200

    resub_res = c.post(
        f"/api/v1/spacs/applications/{app.pk}/resubmit/",
        {"comments": "Fixed blurry upload"},
        format="json",
    )
    assert resub_res.status_code == 200
    app.refresh_from_db()
    assert app.status == "resubmitted"


def test_journey_student_withdraw(stub_iam, scholarship_scheme):
    """Journey 3: Student withdraws submitted application (BW-SPACS-05, UC-SPACS-004)."""
    student_session = make_session(
        user_id=3006,
        kind="student",
        modules=("spacs",),
        permissions=ROLE_GRANTS["student"],
        roles=("student",),
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token e2e_token")

    stub_iam(student_session)
    app = ScholarshipApplication.objects.create(
        user_id=3006,
        application_number="SPACS-WITHDRAW-01",
        catalogue_entry=scholarship_scheme.entry,
        catalogue_version=scholarship_scheme,
        academic_year="2026-27",
        cycle="2026-27",
        status="submitted",
        annual_income_declared=Decimal("400000"),
        cpi_at_apply=Decimal("8.0"),
    )

    w_res = c.post(
        f"/api/v1/spacs/applications/{app.pk}/withdraw/",
        {"reason": "Accepted external fellowship"},
        format="json",
    )
    assert w_res.status_code == 200
    app.refresh_from_db()
    assert app.status == "withdrawn"


def test_journey_convocation_award_cycle(stub_iam):
    """Journey 4: Convener opens cycle, prepares pool, records evaluation, publishes (CW-SPACS-03)."""
    convener_session = make_session(
        user_id=3007,
        kind="staff",
        modules=("spacs",),
        permissions=ROLE_GRANTS["spacs_convener"],
        roles=("spacs_convener",),
    )
    committee_session = make_session(
        user_id=3009,
        kind="faculty",
        modules=("spacs",),
        permissions=ROLE_GRANTS["award_committee_member"],
        roles=("award_committee_member",),
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token e2e_token")

    entry = CatalogueEntry.objects.create(
        code="e2e-directors-medal",
        title="Director Gold Medal",
        kind="award",
        status="active",
    )
    today = timezone.now().date()
    version = CatalogueVersion.objects.create(
        entry=entry,
        version_number=1,
        academic_year="2026-27",
        policy_reference="REF/MEDAL/01",
        valid_from=today,
        valid_to=today + datetime.timedelta(days=365),
        candidate_source="system_generated",
        status="published",
    )

    # 1. Open award cycle
    stub_iam(convener_session)
    open_res = c.post(
        "/api/v1/spacs/awards/cycles/",
        {
            "catalogue_version_id": version.pk,
            "convocation_year": 2026,
            "convocation_date": (today + datetime.timedelta(days=30)).isoformat(),
        },
        format="json",
    )
    assert open_res.status_code == 201
    cycle_id = open_res.json()["id"]

    # 2. Prepare pool
    prep_res = c.post(
        f"/api/v1/spacs/awards/cycles/{cycle_id}/prepare-pool/",
        {"candidates": [{"user_id": 4001, "cpi": 9.5}, {"user_id": 4002, "cpi": 9.2}]},
        format="json",
    )
    assert prep_res.status_code == 200
    cycle = AwardCycle.objects.get(pk=cycle_id)
    candidate = cycle.candidates.first()

    # 3. Record committee evaluation
    stub_iam(committee_session)
    eval_res = c.post(
        f"/api/v1/spacs/awards/candidates/{candidate.pk}/evaluate/",
        {"score": 98.0, "remarks": "Top academic thesis"},
        format="json",
    )
    assert eval_res.status_code == 200

    # 4. Finalize approved and publish
    stub_iam(convener_session)
    outcome_res = c.post(
        f"/api/v1/spacs/awards/cycles/{cycle_id}/record-outcome/",
        {
            "candidate_outcomes": [{"candidate_id": candidate.pk, "outcome": "winner"}],
            "approval_ref": "SENATE/2026/AWARDS/01",
        },
        format="json",
    )
    assert outcome_res.status_code == 200

    pub_res = c.post(f"/api/v1/spacs/awards/cycles/{cycle_id}/publish/", format="json")
    assert pub_res.status_code == 200
    cycle.refresh_from_db()
    assert cycle.status == "published"


def test_journey_renewal_application(stub_iam, scholarship_scheme):
    """Journey 5: Approved scholarship renewed for subsequent cycle (CW-SPACS-02, BR-SPACS-017)."""
    student_session = make_session(
        user_id=3008,
        kind="student",
        modules=("spacs",),
        permissions=ROLE_GRANTS["student"],
        roles=("student",),
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token e2e_token")
    stub_iam(student_session)

    # Parent approved application
    parent_app = ScholarshipApplication.objects.create(
        user_id=3008,
        application_number="SPACS-PARENT-01",
        catalogue_entry=scholarship_scheme.entry,
        catalogue_version=scholarship_scheme,
        academic_year="2025-26",
        cycle="2025-26",
        status="approved",
        annual_income_declared=Decimal("400000"),
        cpi_at_apply=Decimal("8.8"),
    )

    # Apply for renewal
    ren_res = c.post(
        "/api/v1/spacs/applications/renew/",
        {
            "parent_application_id": parent_app.pk,
            "cycle": "2026-27",
            "submission_data": {"grade_sheet_url": "https://drive.google.com/grades"},
            "annual_income": 400000,
        },
        format="json",
    )
    assert ren_res.status_code == 201
    ren_id = ren_res.json()["id"]

    ren_app = ScholarshipApplication.objects.get(pk=ren_id)
    assert ren_app.is_renewal is True
    assert ren_app.parent_application_id == parent_app.pk
    assert ren_app.status == "renewal_submitted"
